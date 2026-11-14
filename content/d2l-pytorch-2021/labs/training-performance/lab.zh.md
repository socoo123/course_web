---
title: 计算性能与多设备训练
kind: 编者阶段练习（非官方编号 Lab）
source: 固定中文第二版12.4–12.7正文及PyTorch代码；12.2异步计时为编者补充；PyTorch2.5.1官方源码
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 未依据课堂音视频、字幕、演示或问答编写
license: 教材源码根LICENSE为Apache-2.0；PyTorch许可独立；本文为自主练习改编
status: 四任务合同已编写；个人练习自行安排，实际独立验收范围见课程公共资料
version_boundary: 当前中文第二版固定源码不是2021全书快照；现代API按PyTorch2.5.1核对
---

# 计算性能与多设备训练

## 学习问题：更快的是哪一段，正确性又由谁保证？

本实验只对应[LEC31硬件](#/c/d2l-pytorch-2021/lec/lec31?v=notes)、[LEC32专用硬件](#/c/d2l-pytorch-2021/lec/lec32?v=notes)、[LEC33多GPU原理](#/c/d2l-pytorch-2021/lec/lec33?v=notes)、[LEC34实现](#/c/d2l-pytorch-2021/lec/lec34?v=notes)和[LEC35分布式](#/c/d2l-pytorch-2021/lec/lec35?v=notes)。图片竞赛、预训练迁移和比赛成绩不在本实验内。

四个问题依次是：**时间花在哪里 → batch改变了什么 → 聚合后是不是同一个梯度 → 通信为什么可能抵消计算收益**。先完成CPU基线，再决定是否有真实多GPU资源；没有多卡也能学完数学和系统推演，不能把它改名为“多GPU实测”。[指导页](#/c/d2l-pytorch-2021/lab/training-performance?v=guide)只提供排错路线和局部提示，没有整套训练、计时或分布式答案。

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

> 本地练习使用自己的Python/PyTorch环境。没有官方Lab分数或统一成绩门槛。

## 共用实验记录与资源边界

### CPU基础：用可控工作负载测流程，不重训上一实验

- 推荐Python3.11、PyTorch2.5.1，CPU、float32、单计算线程；记录真实OS、CPU型号、版本、线程数和运行日期。CUDA/MPS可用性检查不等于运行通过；基础路径不调用CUDA同步或显存API。
- 编者最小基线是`784 → 64 → 10`的两层MLP，中间ReLU，无BN、Dropout、数据增广、编译或混合精度；输入`(B,784)`、float32，标签`(B,)`、long，输出`(B,10)`为logits。使用mean交叉熵及普通SGD；记录实际学习率、初始化和种子，momentum/weight_decay均为0。
- 输入是**提前生成并驻留CPU内存的合成张量**。记录生成分布、标签规则、样本数和随机种子；数据生成、模型创建和import在计时区间外。它用于流程计时，不是Fashion-MNIST训练或分类质量验收，更不能报告真实数据准确率。
- `DataLoader`基础用`num_workers=0`、无shuffle、`pin_memory=False`，固定顺序，准备足够样本使热身与测量无需重启迭代器。这个“加载”主要是取样、拼批与Python开销，**不测磁盘读取、JPEG解码、网络下载或后台多进程加载**。在真实数据上另测时必须另列配置，不能覆盖此基线。
- 每个batch设置独立进程，从同一初始模型数值与生成规则开始；10个完整训练步热身，随后30步测量。热身仍会更新参数，所以记录此事实，不把不同batch后的参数或精度当成同一训练轨迹。
- 计时日志先保存在内存，打印、绘图、写盘、读取标量loss和额外正确性扫描放在测量区间外。每次测量都应有真实前向、反向及一次更新，不保留旧计算图反复冒充训练。

模型可复用此前自己写的基础组件，不要求完整训练LeNet/ResNet来完成性能基线。换模型、数据、精度或线程数时，建立新记录组；本基线的耗时结论不能直接外推CNN或生产服务。

### 必须保留的配置表

| 项目 | 最少记录 |
|---|---|
| 环境 | OS、CPU/实际加速器型号及数量、Python/torch版本、线程数、后台负载说明 |
| 工作负载 | 模型层形状、参数量、train/eval、dtype、数据来源/生成规则、随机种子 |
| 更新 | loss的reduction、优化器全部非默认设置、清梯度位置、实际更新次数 |
| 采样 | batch、实际样本数、尾批策略、DataLoader设置、热身/测量步数 |
| 时间 | 时钟、单位、同步设备/边界、逐步原始值、median、IQR和总时长 |
| 内存 | 指标名称、API/工具、单位、采样或高水位范围、是否含子进程 |
| 未运行 | CUDA、MPS、多GPU、真实网络、磁盘/解码等逐项填写，不用“支持”替代“运行” |

## 任务1：分阶段计时，先定义边界

**任务id：`training-performance-1`**

先用B64完成一份时间账，再在任务2复用。用单调高精度墙钟，例如`time.perf_counter`。基础CPU常规张量运算在调用返回时已完成，不需要`torch.cuda.synchronize()`。

### 四段主账与端到端旁账

| 段 | 起止边界 | 不要混淆 |
|---|---|---|
| data | 调用`next(iterator)`前，到取得X、y后 | 内存数据加载，不是全数据管线 |
| forward | 模型前向开始，到构造标量CE完成 | 本实验把loss计算包含在前向段 |
| backward | 调用该步loss的backward前后 | 梯度累加而非自动覆盖；每步须清梯度 |
| update | SGD step开始，到随后zero_grad完成 | 明确包括清梯度，统一`set_to_none`设置 |

第一步前先清一次梯度；之后用“更新并清梯度”的边界避免漏清或重复计入。每个完整步另记录从取batch前到更新清梯度后的总时长。内层打点和Python管理也有成本，四段之和不必恰好等于外层时间；解释残差，不强行让它归零。

### 异步硬件扩展：没有设备就只写方案

真正使用CUDA时，在待测工作开始前排空相关设备既有工作，结束后再次等待完成，再读结束时刻。多卡必须明确所有参与设备；无参数的`torch.cuda.synchronize()`只同步当前设备，不自动同步每一张卡。若有CPU→GPU搬运，单列transfer段或明确计入data段；不能悄悄删去搬运时间后仍称端到端。

**诊断分段计时**可以在每段边界同步，但会破坏原本的重叠。**吞吐计时**另用只在整个测量区间前后同步的运行，保留其内部正常调度。两者不直接相加或互换。CUDA Events可作为设备区间补充，却不替代包含DataLoader和Python的墙钟端到端时间。MPS须使用对应后端方法另行核对，不能照抄CUDA调用或本CPU结果。

### 可观察验收

1. 30步原始四段时间与总时间均为有限正数；报告各段median及IQR（Q3−Q1），注明分位数算法，热身不混入。
2. 日志显示实际样本数、30次更新、参数确有变化，loss/参数有限。合成标签不设准确率或loss单调下降门槛；另作短正确性检查，不把它塞进被计时段。
3. 解释哪个阶段占比大、取样与计算是否包含在总时间内；所有结论带上当前CPU/模型/输入口径。若计时粒度或噪声主导，诚实报告，不捏造稳定排名。
4. 明确“CPU已测”和“异步设备未运行”；没有GPU时不提交伪造的CUDA耗时表。

## 任务2：batch、吞吐与内存，分开三本账

**任务id：`training-performance-2`**

基础比较B16、B64、B128，使用前述同模型、同设备、同精度、同线程、同生成规则的独立进程；每项10热身+30测量步。设置足够数据避免尾批，记录实得batch大小；额外尾批实验应使用实际大小计数，不能用配置B代替。

吞吐以**实际处理样本总数/对应区间总墙钟秒数**计算，而不是平均每步吞吐，更不是`B / median(data时间)`。报告单步median、IQR、总步数、总样本数、总秒数及samples/s。

$$
\begin{aligned}
N_{\rm measured}&=\sum_{t=1}^{T}B_t,\\
q&=N_{\rm measured}/t_{\rm total}.
\end{aligned}
$$

固定30步下，各B处理的样本总数不同。这是**固定步数的吞吐微基准**，不是同样数据量、同样更新次数下的模型收敛比较。若要比较处理固定样本数所需时间，另建实验，记录尾批、总更新数；若要比较达到同样质量所需时间，则需要真实数据与质量标准，本实验不承担该结论。

### 内存合同

- CPU推荐记录独立进程的峰值RSS及获取方法。例如调用`resource.getrusage`，传入`resource.RUSAGE_SELF`，读取返回值的`ru_maxrss`字段：这是进程生命周期高水位，macOS通常以bytes报告，Linux通常以KiB报告；保存原始值、OS和换算规则，不能跨平台默认同单位。若用其他工具，写明是瞬时采样还是峰值。
- RSS包含解释器、框架、本机库、数据、分配器缓存等驻留页，**不是活跃张量内存，也不是前向激活峰值**。进程高水位包含import、数据构造和热身；不能通过“减去两个高水位”得到严格的某阶段新增内存。独立进程防止此前更大batch的历史峰值污染下一项，但不消除系统噪声。`RUSAGE_SELF`也不自动统计DataLoader子进程；本基础没有这类子进程。
- 另给可解释的**理论账**：输入X的字节数为`B × 784 × 4`，标签为`B × 8`；模型参数与同dtype梯度按元素数计算。不要将这些简单相加宣称完整运行峰值；激活、算子工作区、共享存储与分配器状态仍未完整统计。
- 真CUDA扩展才记录各设备的allocated/reserved及峰值：热身完成后，在明确边界重置峰值统计，运行后同步再读。`max_memory_allocated`与`max_memory_reserved`不同，且都不等于整个设备的所有显存。不要调用它们给CPU伪造“显存0”。

### 可观察验收

记录三行batch结果及原始记录；吞吐可由总样本数和总秒数重算，内存列有单位/工具/范围，理论输入字节数随B变化。解释“大batch单步更慢但吞吐可能更高”，也允许实测不满足这种趋势；不得以“必须提速”作为通过标准。OOM不是吞吐为0的正常样本，应保存失败配置并标为未完成该测量，不靠偷偷换模型或精度过关。

## 任务3：读懂从零与简洁实现，再决定是否扩展到多GPU

**任务id：`training-performance-3`**

### A. CPU必做：同一目标函数的等价性

设总batch有N个样本，第i个逻辑worker拿到$n_i$个，$N=\sum_i n_i$。$\ell_j$是单样本标量损失，模型参数为$\theta$。比较三条路线：

$$
\begin{aligned}
L&=\frac{1}{N}\sum_{j=1}^{N}\ell_j,\\
g_i^{\rm sum}&=\sum_{j\in S_i}\nabla_\theta\ell_j,\\
g&=\frac{1}{N}\sum_i g_i^{\rm sum}.
\end{aligned}
$$

局部mean路线必须按样本数加权：

$$
g=\sum_i\frac{n_i}{N}g_i^{\rm mean}.
$$

使用无BN/Dropout的小线性模型、float64，所有副本从相同的独立参数快照开始。全batch直接求梯度作为参照；分别做两等分与不等分。建议六样本拆为3+3及2+4，输入二维，输出一维，单样本损失用二分之一平方误差。自己给出不对称的固定小数值，让两片局部mean梯度确实不同。

对照全batch梯度、局部sum聚合后除N、局部mean按$n_i/N$加权三者；再用同学习率、无动量/权重衰减的SGD更新一次，比较每个参数和bias。float64建议`atol=1e-10, rtol=1e-8`，记录最大绝对差；不能只比较loss或参数范数。另记录“将不等分片局部mean等权平均”的错误反例，说明错在哪里。

**不变量**：分片样本无重无漏、X与y索引一致；所有副本起点相同但不共享可变存储；每份局部梯度只计一次；归一化只做一次；每个同步轮只做一次全局更新。CPU上将多个逻辑worker顺序执行，只验证这些数学性质，不证明并行、GPU通信或加速。

### B. 阅读映射必做

| 教材路径 | 需要解释的责任 |
|---|---|
| 12.5从零 | 参数副本、scatter数据与标签、逐片loss求和、backward、梯度allreduce求和、用全局batch归一化后更新 |
| 12.6简洁 | `nn.DataParallel`拆输入、复制模块、收集输出和反向归并；示例在收集后的logits上计算全局mean CE |
| PyTorch2.5.1边界 | 基础模块参数及buffer须先放到首设备；优化器管理基础模型参数；副本梯度求和由并行包装/自动微分承担，不是SGD本身负责网络通信 |

解释教材的两条实现如何得到同一全局目标，而不是机械搜寻“哪里除以GPU数”。不要照搬CPU回退来模拟多个GPU：同一CPU上的`.to('cpu')`可能返回同一对象，不能作为独立参数复制方法；`nn.DataParallel`在无设备时的普通前向也不是多卡验证。

### C. 有真实多GPU才运行的扩展

1. 记录至少两张实际CUDA设备的型号、显存、设备索引与互连；模型、输入、标签都检查device。先在无BN/随机层的小模型上做单卡/多卡同一个global batch的一步梯度与更新对照，再跑性能。
2. 按12.5完成从零同步链条，按12.6完成简洁路径的阅读和实际运行；独立核查初始化设备与同步边界，不照搬旧示例计时。教材12.6的改写ResNet-18含BN，局部batch统计与全batch统计不自动相同，因此不能把其训练态输出不等价一律判成allreduce错误。
3. **固定global batch**比较单卡与多卡端到端吞吐；另列**固定每卡batch**的扩展，此时global batch变大，不是同一优化轨迹。所有设备使用相同dtype、模型与数据规则。热身后同步计时，不要求必然加速，报告通信/复制开销可能超过计算收益。
4. DataParallel是本教材阅读对象；PyTorch2.5.1官方推荐实际多GPU优先考虑DistributedDataParallel。本实验不提供DDP启动器或完整分布式程序，也不把CPU逻辑worker包装成DDP实测。

**验收**：CPU等/不等分片的逐参数数值证据、一步更新对照、错误反例、两条实现责任表齐全。没有多卡时明确写“真实多GPU扩展未运行：缺少至少两张可用CUDA设备”，保留方案但不给性能数值；基础学习与硬件扩展分开标记。

## 任务4：CPU多worker与参数服务器通信推演

**任务id：`training-performance-4`**

这里worker是逻辑计算角色，**不是DataLoader的num_workers**。用CPU小张量模拟三个worker与一个参数服务器，可以顺序执行，不要求启动网络服务。

### A. 一轮同步协议

每条消息标记`(step, worker, parameter_key, sample_count)`，并说明value保存局部sum梯度还是局部mean梯度。选择一个参数向量及三个不对称梯度，手算与张量计算对照：收齐本轮贡献 → 归一化 → 服务器执行一次SGD → 所有worker取得同版本新参数。

在本地保存一张事件表，记录旧版本、到达顺序、收到的worker集合、累计样本数、聚合值、更新次数及新版本。交换到达顺序应在浮点容差内得到同一同步结果；不要宣称浮点求和逐位可交换。故意遗漏一个worker的贡献时，本轮不应被当作“全体同步完成”；重复消息或旧step消息也不能悄悄重复累计。本任务要求解释协议不变量，不要求实现容错网络系统。

### B. 只在纸上和CPU标量上做通信算例

编者统一设置：4个worker，每个完整梯度/参数向量S=160 MB；MB用十进制，链路R=16 GB/s为**可用单方向带宽**。忽略消息启动、协议、计算和争用，先画清谁发给谁，再算以下三种情形：

- **中心为一个worker**：其余3个依次上传，再依次广播回去，根节点端口串行。
- **独立参数服务器**：4个worker都要上传、都要取回；服务器共享端口按上传阶段、下载阶段串行处理，无计算通信重叠。
- **理想分块环**：reduce-scatter与all-gather各3轮，每轮每节点发S/4；各链路可同时传输，忽略不同链路争用。

分别记录总发送字节数、关键端口/每节点发送字节数、理想时间与假设；不要只给一个“带宽除一下”的答案。环并未消除总数据搬运，它改变同时可用的路径和瓶颈。再给启动延迟$\alpha$加入环的阶段模型，解释小消息、多节点和慢worker会怎样改变结论。

### C. 归因短答

用任务1–2证据或明确标为假设的例子，各写一条：CPU取样/调度、GPU算子计算/显存带宽、专用矩阵硬件的形状及精度匹配、跨机带宽/同步等待可能如何成为瓶颈。专用硬件峰值算力不能直接当训练吞吐；CPU结果也不能验证GPU、TPU或互连产品规格。

**验收**：逻辑worker事件表、逐参数聚合与同步更新结果、消息口径、三种通信算例及局限说明完整。CPU只证明张量代数与预算算术，没有发送这些MB级网络消息，更没有测得“通信耗时”。

## 本地记录与自检

四个任务id保留不变，在本地保存简短记录和自己的代码：配置表、原始时间序列、batch结果表、内存口径、梯度/更新差值、错误反例、通信事件表及未运行范围。文档中的计算例子属于解析预期，不是你的运行日志。

<details>
<summary>自检：CPU可完成什么，哪些必须保持未运行？</summary>

可完成内存合成数据计时、batch吞吐/RSS对照、梯度与一次更新的代数验证、逻辑参数服务器事件和通信预算。没有真实多GPU就不能声称验证多卡算子、设备间同步、NCCL、吞吐或加速；没有网络实验就不能声称测过参数服务器通信。没有真实分类数据就不能得出模型质量结论。

</details>

## 来源、许可与覆盖边界

- 《动手学深度学习》中文第二版，固定提交[`e6b18ccea714`](https://github.com/d2l-ai/d2l-zh/commit/e6b18ccea71451a55fcd861d7b96fddf2587b09a)：[12.4硬件](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/hardware.md)、[12.5多GPU训练](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/multiple-gpus.md)、[12.6简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/multiple-gpus-concise.md)、[12.7参数服务器](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/parameterserver.md)。实际读取正文及PyTorch段；12.4/12.7以系统概念为主，并不存在可据此声称跑通的PyTorch训练程序。
- 编者计时补充：[12.2异步计算](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computational-performance/async-computation.md)。12.3只存在于早期索引，本实验未新读其正文，不宣称覆盖其完整内容。
- 现代API核对：PyTorch v2.5.1 [DataParallel类及实现](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/parallel/data_parallel.py#L52-L217)、[CUDA synchronize](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/cuda/__init__.py#L944-L954)、[CUDA memory统计](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/cuda/memory.py#L328-L470)，只读相关原始行并归档节选，未运行CUDA。
- 教材固定版本不是2021全书快照；设备数字是历史例子，不是当前采购建议。许可分别见[教材根LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)与[PyTorch LICENSE](https://github.com/pytorch/pytorch/blob/v2.5.1/LICENSE)，不外推到视频、图片或数据。

实验合同、CPU配方、错误反例、同步协议和通信假设为编者设计，不是官方作业、课堂转录或官方参考答案。不制作无来源英语原文、视频draft或重复materials。来源原件、逐文件哈希及实际阅读范围保存在本实验manifest；主agent独立运行和页面验收以[课程公共资料](#/c/d2l-pytorch-2021)为准，不等于学生四任务已经完成。
