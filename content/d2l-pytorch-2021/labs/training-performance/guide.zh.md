---
title: 性能实验指导：先守住边界，再解释瓶颈
kind: 编者指导（不是官方答案或完整程序）
source: 固定中文第二版12.4–12.7正文及PyTorch段；12.2为异步计时补充；PyTorch2.5.1官方源码
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 未依据课堂音视频、字幕或问答制作
license: 教材源码Apache-2.0；PyTorch许可独立；提示和小例为编者自主整理
status: 主agent已完成有限CPU微基准和梯度机制验收；本页仅提供路线与局部解析，个人练习进度不由agent追踪
version_boundary: 当前中文第二版不是2021快照；不宣称GPU、MPS或网络实测通过
---

# 性能实验指导：先守住边界，再解释瓶颈

## 学习问题：一个看似更快的结果，可能错在哪一步？

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

先读[实验说明](#/c/d2l-pytorch-2021/lab/training-performance?v=zh)的配置、四任务id及验收边界。建议顺序是：**一个正确CPU训练步 → 明确计时区间 → batch受控对照 → 分片梯度等价 → 参数服务器推演**。本页没有可直接复制的完整训练/计时循环、allreduce实现或分布式启动程序；本地使用Python/PyTorch练习。

CPU能运行不表示课程的多GPU代码在本机被验证。把报告分成“CPU实际执行”“解析推演”“真实硬件未运行”三栏，比拼出一张漂亮加速比图更重要。主agent的有限验收见[课程公共资料](#/c/d2l-pytorch-2021)，不能代替你的运行记录。

## 任务1：沿四个边界找第一个错误

对应`training-performance-1`。

### 第一道门：确实在训练

先不计时，观察一个小batch的输入、logits、标量loss、每个参数的梯度和更新前后差值。检查`train()`、autograd启用、mean CE直接接logits、普通SGD参数绑定正确。无BN/Dropout的MLP仍应明确模式，不能因为这次两模式恰巧相同就省略配置。

清梯度的位置属于测量合同，而不只是代码风格。本实验把SGD step和随后zero_grad算作update段；第一步前额外清一次。若在backward前又清一次，既增加开销又让阶段定义变化；若没有清梯度，第二步测的是另一种算法。选择`set_to_none=True/False`后保持一致，并写入日志。

<details>
<summary>局部提示：为什么不该把loss.item()放在forward打点之前？</summary>

在CUDA上，取得Python标量需要等待对应计算结果，隐式等待可能被计入“前向”而让其他阶段看上去异常便宜。CPU上它也会增加被测路径以外的Python开销。基础微基准在计时区间外读需要的标量；测量内只做合同中的工作。不是为了隐藏错误：在独立正确性检查及测量后仍要确认loss、梯度或参数有限。

</details>

### 第二道门：四段与整步是不同统计量

单步按data、forward+CE、backward、update+zero_grad分界；外面再包一个完整步区间。原始时间序列先保留，不要只保留一次最快值。30步适合有限流程验收，不足以保证生产性能排序；如果IQR很宽，先查后台任务、温度/频率、线程数和第一次执行开销，不立即换网络。

阶段中位数之和**不等于**整步中位数，因为中位数不是线性运算。更合理的检查是在每一步比较四段之和与该步外层时间，再解释计时调用、取时和Python空隙。用总样本数除整段总时间算吞吐，不能把各阶段median分别倒数再相加。

<details>
<summary>局部例子：单步由0.2ms变成0.4ms，吞吐一定下降吗？</summary>

不一定。若batch同时从16增到64，单步延迟翻倍而每步样本增至四倍，理想化样本吞吐会提高。这里只是单位推演，不是本机实测，也不证明每个样本的响应延迟或模型质量更好。必须说明实际分母包含哪些工作。

</details>

### 第三道门：异步设备要等到哪里？

把CPU想成提交者、GPU想成实际执行者。只量提交函数的返回时间可能漏掉队列工作，导致“删除同步后模型变快”的假象。PyTorch2.5.1的`torch.cuda.synchronize(device)`等待指定CUDA设备所有stream上的kernel；省略device仅使用当前设备，多卡不能只在最后同步默认卡。

诊断时的边界同步会把重叠拆开，帮助定位但改变了真实调度；端到端吞吐测量只在整个测量区间起止同步相关设备。若你用两种方法，分开命名为“同步诊断时间”和“自然流水吞吐”，不要求前者逐段相加精确复原后者。

<details>
<summary>没有CUDA设备，能用sleep或者CPU同步函数模拟“GPU计时验证”吗？</summary>

不能。你可以画提交与完成边界并解释等待条件，但那是机制说明。CPU sleep既不产生GPU kernel也不验证stream语义；CPU张量运算不要求CUDA同步。未运行硬件扩展直接写未运行，不用假实现补齐表格。

</details>

## 任务2：每次只改变batch这一项

对应`training-performance-2`。

### 建议路线

1. 在独立进程中分别跑B16/B64/B128。模型、dtype、线程、优化器、输入生成规则一致；实际种子与初始参数快照记录下来。
2. 每项10步热身后测30步。预先准备足够数据，避免迭代器耗尽和尾批悄悄改变测量。独立保存原始样本数与总墙钟秒数。
3. 先核对每一行自己的吞吐恒等式，再比较各行，不先看哪行“赢”。固定步数意味着不同B处理的数据量不同，更新轨迹也不同，不比较它们的最终准确率来证明batch更好。
4. CPU RSS与理论输入张量字节数分别成列。不要用“RSS增量≈输入增量”作硬性通过条件；工作区、缓存、框架初始化和系统驻留状态可能淹没这个小差值。

### 单位与形状提示

本基线X为`(B,784)`的float32，y为`(B,)`的int64。`numel × element_size`只核算这个张量的逻辑元素字节；对视图、共享存储或别名求和会重复计数。模型参数、梯度与优化器状态另列；此处SGD无动量，不可套用Adam两份状态的估算。

$$
\begin{aligned}
M_X&=784B\times4\ \text{bytes},\\
M_y&=B\times8\ \text{bytes}.
\end{aligned}
$$

这两个式子不包含隐藏层激活、反向临时量、Python对象、分配器预留或原始驻留数据集。若提前生成的总数据量随B变大，RSS也会被它影响；应在配置中明确，不能将差异全部归因于单步激活。

<details>
<summary>为什么大batch跑完后再测小batch，ru_maxrss可能一点不降？</summary>

`ru_maxrss`是进程历史最高驻留内存，不是此刻用量。它不会因删张量自动变成新的较低峰值。不同batch使用独立进程避免共享这段历史，但每个新进程仍包含import、构造和热身的峰值。两个峰值相减不等于严格的某阶段新增内存；macOS与Linux还必须核对不同单位。

</details>

<details>
<summary>CUDA allocated、reserved、nvidia-smi读数为什么不相同？</summary>

allocated描述框架张量占用，reserved描述缓存分配器管理的内存，未使用缓存可能仍保留；nvidia-smi还可能看到设备上下文等更广范围。因此分别报告各设备的指标、峰值重置位置及同步边界。不能用CPU的RSS代替其中任意一个，也不能把没有CUDA设备时的空结果填成显存0MB。

</details>

### 排错顺序

- 吞吐异常高：先查是否只测`next`/提交、遗漏backward或更新、重复使用旧图、将毫秒当秒。
- B不同但样本数一样：先确认是否实际上固定样本数，若是就改写测量合同而非隐去差别。
- RSS近乎相同：可能被解释器/框架主导，不是“batch不占内存”的证明。
- 第一项显著更慢：确认每项同样热身与独立进程，初始化在区间外；别只删除不满意的慢样本。
- DataLoader是瓶颈：当前只能得出内存取样/拼批路径的结论；没有磁盘/解码工作时不能建议“买SSD就能快”。

## 任务3：先查归一化，再查通信

对应`training-performance-3`。

### 同一目标函数是唯一参照

全batch目标为每个样本等权的平均损失。把样本分成若干片没有改变这个目标；聚合的是**相同参数点上的梯度**。如果某个worker先本地做了几步SGD，再把梯度平均，参数点已经不同，不能期待等于同步一步。

先以无BN/Dropout、float64的小线性模型过局部检查。输入二维、输出一维使梯度矩阵和bias都能逐项检查；平方误差明确是否有二分之一，分母是样本数还是所有元素数。该夹具只用于代数，不代替任务1的float32 MLP性能基线。

<details>
<summary>局部推导：等分片时成立的平均法为什么会在尾批失败？</summary>

两片大小为$n_1,n_2$，局部mean梯度为$g_1,g_2$。全局mean必须是

$$
g=\frac{n_1}{n_1+n_2}g_1
 +\frac{n_2}{n_1+n_2}g_2.
$$

例如两片各含2、4个样本，局部mean梯度分别为标量1、3，则正确全局值为$7/3$，等权平均得到2。这个小标量例子揭露分母错误，不是完整线性层答案。实际夹具还要逐参数比较并完成一次SGD更新。

</details>

### 三条路线的核对清单

- **全batch**：从初始独立快照计算mean loss及所有梯度，保存数值参照。
- **局部sum**：每片先sum，聚合各片sum梯度，再除全局实际样本数一次；不要再除worker数。
- **局部mean**：每片先mean，按该片样本占比加权；等分只是这个式子的特例。

梯度正确后，用相同学习率更新一次再比较；不是比较训练十轮后的曲线。所有副本的起点、SGD选项与更新次数必须相同。只比较loss没有意义：不同梯度也可能在某个点恰好有同样loss；只比较参数范数也会漏掉方向错误。

<details>
<summary>CPU参数副本为什么不能只写p.to('cpu')？</summary>

设备和dtype已经相同时，`.to()`可能返回原对象。把它装进两个列表不等于两个独立worker；一边更新可能改动另一边，梯度也可能混到同一个对象。CPU逻辑推演需要独立存储、正确的叶子张量和清梯度边界；仅作为局部提示，可从`p.detach().clone().requires_grad_()`理解独立可求导副本的意图。不要将它扩展成整套训练答案或对已有参数随意断图。

</details>

### 对应教材12.5与12.6

12.5从零路线明确局部损失求和、聚合梯度、全局batch归一化。其示例`allreduce`是先归到一处再复制回去的教学实现，不是高效环通信/NCCL实现。代码名字相同不表示拓扑、性能或容错语义相同。

12.6使用`nn.DataParallel`。包装器将输入沿batch轴分发、产生模型副本、收集输出；反向时将副本梯度归到基础模块。教材在收集后的logits上计算全局mean CE，于是这个全局分母已经进入自动微分。若改成每个副本内部返回局部mean loss，就必须重新推导缩放，不能再机械取这些标量的平均。

PyTorch2.5.1要求原模块的参数和buffer先在`device_ids[0]`；随后再创建对应优化器。多卡时不要依赖单卡路径可能做的自动迁移。**SGD负责使用梯度更新参数，不负责跨设备通信**；这是对教材小结的现代语义澄清。

<details>
<summary>为什么CPU线性层等价通过，不保证含BN的ResNet单卡/多卡一步完全一样？</summary>

BN训练态的均值方差取决于参与统计的batch。多卡各副本的局部batch与全batch不是同一组统计；DataParallel也不是自动的全局同步BN。其首设备副本与基础模块共享参数/buffer存储，不代表所有卡的running statistics都被平均。Dropout随机掩码、浮点归约顺序也会造成差别。先用简单确定模型隔离聚合问题，再分析真实网络的状态，不通过放大容差掩盖定义差异。

</details>

### 真实硬件扩展前的停止条件

如果没有至少两张可用CUDA设备，就停在CPU数学验证与阅读表，不尝试把两个CPU device对象伪装成两张卡。有硬件时先过同global batch的小模型正确性，再做教材路径与性能；保留初始化迁移、每卡内存、同步位置和全部实际设备信息。

官方v2.5.1 DataParallel文档建议多GPU优先使用DistributedDataParallel。该建议用于辨认现代工程路线，**本页没有读完并交付DDP训练教程**，也没有将教程阅读包装成DDP实测。实际选择DDP时须另核其数据切分、进程、损失缩放和通信后端合同。

## 任务4：先画消息账，再写时间式

对应`training-performance-4`。

### 逻辑参数服务器：更新一次，不是收到一次就更新一次

先给每个参数分配key，再给一轮同步分配step。三个worker都从$\theta_t$出发。事件表应能回答：收到的是谁、哪个参数、哪一轮、多少样本的梯度？哪些贡献仍未到达？服务器是否已经更新过？广播回去的是聚合梯度，还是更新后的参数？

实验采用“服务器归一化并更新一次，再分发新参数”合同。教材也讨论pull聚合值的接口；二者都可以形成协议，但不能一个worker以为拿到梯度，另一个以为拿到新权重。将局部sum与局部mean混在同一个key下也无法正确归一化。

<details>
<summary>为什么接收顺序改变可以接受，缺失或重复worker不可以？</summary>

同一版本、同一参数、同一批贡献的实数加法可交换；浮点实现允许小的顺序舍入差，而不是要求逐位相同。缺失贡献改变了训练目标，重复贡献改变了样本权重，旧版本贡献在不同参数点计算，都不是舍入误差。同步方案必须收齐本轮规定贡献后更新；这只是CPU事件推演，不等于实现了可靠网络投递或崩溃恢复。

</details>

### 通信算例的局部提示

设n为worker数，S为单个完整梯度/参数向量bytes，R为题设有效单方向bytes/s；消息中梯度与新参数都按S计算。以下是理想模型，未执行任何真实传输。

中心就是一个worker时，它无需给自己上传和回传；按题设根端口串行：

$$
T_{\rm root}=\frac{2(n-1)S}{R}.
$$

独立参数服务器不在worker中，所有worker都要往返；按题设上传与下载阶段串行：

$$
T_{\rm PS}=\frac{2nS}{R}.
$$

理想分块环每阶段n−1轮，每轮单节点发送S/n；各链路同时工作：

$$
\begin{aligned}
T_{\rm ring}&=\frac{2(n-1)S}{nR},\\
T_{\rm ring,\alpha}&=2(n-1)\alpha+T_{\rm ring}.
\end{aligned}
$$

自行代入实验的n=4、S=160 MB、R=16 GB/s，列出每轮消息大小、关键端口与全系统总发送量。只数发送bytes，避免把同一消息在发送端和接收端重复当成两条网络消息。参数服务器与根worker聚合不能共用同一个n−1因子；环的每节点量不能误标为全系统量。

<details>
<summary>局部单位核对：160 MB经过16 GB/s，一次传输是多少？</summary>

按题设十进制单位，一次完整向量传输是0.01s，也就是10ms。若把16 Gb/s误当16 GB/s，会相差8倍。题设已经将R定义成可用单方向带宽，不能再擅自乘2或除2。真实链路的标称双向、协议开销与共享端口必须重新核查，不能套用本题假设。

</details>

### 预算不等于预测，更不是实测

- 这些式子忽略框架启动、拷贝、序列化、协议、PCIe/网卡争用、梯度产生时间与计算通信重叠。它们展示瓶颈假设，不承诺真实硬件一定达到该时间。
- 小S时，启动延迟项可能主导；n变大时每消息虽更小，轮数也增加，因此“环时间与节点数完全无关”不成立。
- 同步训练受慢worker约束；服务器即使收到大多数梯度，也不能冒充全体都完成。多参数服务器分片可分散端口/状态压力，但不是免费消除带宽和一致性问题。
- 数据并行每个worker保留完整模型，不自动让过大的模型装进单卡。CPU、GPU、专用矩阵硬件的峰值算力不是互相替代的速率单位；形状、精度、算子支持、访存和通信都会限制利用率。

## 最后自测

<details>
<summary>分阶段同步后吞吐更低，是代码错了吗？</summary>

不一定。诊断同步破坏了阶段重叠，可能降低吞吐。先检查两份结果的计时边界与实际工作量，再比较。若只是未同步的“提交时间”更低，则不能据此宣布真实工作更快。

</details>

<details>
<summary>不等分片的全局梯度错了，先修改学习率能补救吗？</summary>

不能普遍补救。错误等权平均改变不同样本组的权重，通常改变梯度方向而不只是统一倍数。先按实际样本数恢复目标函数；只有明确是整体缩放错误时才能分析等效学习率，但也不能以此掩盖归一化合同。

</details>

<details>
<summary>CPU三份张量聚合和理想环15ms的算例，合起来算多GPU通信通过吗？</summary>

不算。前者是CPU张量代数，后者是理想拓扑预算。它们没有执行GPU kernel、真实设备传输或网络协议。报告必须分别标为CPU执行与解析估算；真实多GPU与网络仍是未运行。

</details>

## 来源与边界

实际阅读的固定版本来源：[12.4硬件](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/hardware.md)、[12.5从零多GPU](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/multiple-gpus.md)、[12.6简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/multiple-gpus-concise.md)、[12.7参数服务器](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/parameterserver.md)；[12.2异步计算](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/async-computation.md)为编者计时补充。它们是当前中文第二版固定源码，不是2021全书快照。

现代API局部核对来自PyTorch v2.5.1：[DataParallel](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/parallel/data_parallel.py#L52-L217)、[synchronize](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/cuda/__init__.py#L944-L954)、[memory统计](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/cuda/memory.py#L328-L470)。读取源码不等于运行CUDA；未复刻旧Notebook环境，不把教材中MXNet/Paddle分支当成PyTorch验证。许可见[教材LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)及[PyTorch LICENSE](https://github.com/pytorch/pytorch/blob/v2.5.1/LICENSE)，不涵盖视频或第三方媒体。

CPU基线、RSS口径、标量反例和同步事件合同为编者补充；未制作英文原文、课堂译稿、时间轴或完整学生答案。本页未执行实验；主agent独立验收的确切范围集中在[课程公共资料](#/c/d2l-pytorch-2021)，不外推GPU/MPS、真实网络、磁盘吞吐或分类质量。
