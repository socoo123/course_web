---
title: 模块工程、卷积与现代CNN
kind: 编者阶段练习（非官方编号 Lab）
source: 固定中文第二版6.5–6.6、7.1–7.6的正文与PyTorch节选；复用LEC16–17、19–21及P2/P3证据
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 不依据课堂音视频、演示或问答编写，不是官方课堂作业转录
license: 教材源码根LICENSE为Apache-2.0；PyTorch与Fashion-MNIST许可分别处理；本文为自主练习改编
status: 四任务合同与指导已编写；主agent独立CPU机制、六种教材架构前向、LeNet和小ResNet小基线及恢复验收通过，精确范围见公共资料；个人练习进度不由agent追踪
version_boundary: 中文第二版固定源码不是2021快照；现代API按PyTorch2.5.1
---

# 模块工程、卷积与现代CNN

## 用同一套接口保留整条CNN路线

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

这次练习四项：**模块与状态 → 卷积和池化机制 → LeNet训练及四个网络前向 → BN、残差与恢复训练**。不要删去AlexNet、VGG、NiN或GoogLeNet，也不要求在CPU上把所有大网络完整训练一遍。

先复用[LEC16模块工程](#/c/d2l-pytorch-2021/lec/lec16?v=notes)、[LEC17设备](#/c/d2l-pytorch-2021/lec/lec17?v=notes)、[LEC19卷积](#/c/d2l-pytorch-2021/lec/lec19?v=notes)、[LEC20填充步幅](#/c/d2l-pytorch-2021/lec/lec20?v=notes)、[LEC21通道](#/c/d2l-pytorch-2021/lec/lec21?v=notes)和前三项实验的工具；不用重写已经正确的数据读取、指标累计器和基础训练步骤。本页给新任务合同，[指导页](#/c/d2l-pytorch-2021/lab/cnn-architectures?v=guide)给局部提示，不提供整套架构加训练循环。

> 本地练习使用自己的Python/PyTorch环境。没有官方Lab分数或统一成绩门槛。

## 共用CPU、数据与记录合同

- 环境沿P2/P3：Python3.11.8、torch2.5.1、torchvision0.20.1、NumPy1.26.4，CPU、float32、1线程，`num_workers=0`。先确认自己的环境实际可用，不照搬旧Notebook依赖；不安装d2l也可完成。CUDA/MPS仅作可选扩展，后端探测不等于计算通过。
- 数据沿[线性训练实验](#/c/d2l-pytorch-2021/lab/linear-training?v=zh)的官方Fashion-MNIST：官方训练集60000张，图像单通道28×28，标签0–9。复用已核MD5/SHA-256的运行时cache；路径失效时按页底官方HTTPS来源重取并核对，不改成随机图片或其他数据集。
- 固定划分：独立CPU generator种子2021产生`randperm(60000)`；前5000为验证候选，后55000为训练候选；基础取训练候选前257、验证候选前73。保存索引/哈希和类计数，两个集合无交集。官方测试集不用于训练、调参或本次小基线选择。
- 图像转float32后除以255，保持`(N,1,28,28)`；标签long、形状`(N,)`。不加增广、标准化拟合或label smoothing。输出`(N,10)`为logits，交给mean交叉熵，不能先做softmax。
- 参数初始化随机种子2022，训练顺序用独立generator种子2023；明确记录构造、初始化顺序。卷积/线性权重用Xavier uniform，偏置置0；BN的gamma=1、beta=0，running mean=0、running var=1。每个模型独立从头开始，不共享可变快照。
- B64、`drop_last=False`：257张每轮5步，末批1张；10轮50次更新。验证73张为64+9，累计loss乘实际batch大小再除总数，accuracy用总正确数/总样本数。禁止平均两个batch的accuracy冒充全体accuracy。
- 每轮记录训练过程中优化损失，以及冻结该轮模型后`eval()+no_grad()`重评的训练/验证CE与accuracy。记录epoch0、各轮、参数变化、非有限值、样本数、更新次数；曲线可交文本表。训练之后必须恢复`train()`再继续更新。

这里的257/73是**流程与机制小基线**，不是泛化排名。推荐Adam，lr=0.003、betas=(0.9,0.999)、eps=1e-8、weight_decay=0、amsgrad=False，10轮；这是编者CPU配方，区别于教材SGD配方。应观察固定模型训练CE相对epoch0有下降；若没有，保留失败、逐项排查，不删日志、不保证每轮单调、不规定必须达到教材全量准确率。需要增加样本时，在原候选集合上固定扩到2048/512并单独登记，不能把两个规模结果混在一条曲线里。

## 任务1：模块、自定义层、参数、存取与设备

**任务id：`cnn-architectures-1`**

### 输入与实现边界

用`(2,3,4,4)`输入，创建一个自定义逐通道仿射层：每通道一个可训练缩放和偏移，再加一个固定的、形状可广播的通道偏置buffer。规定输出与输入同形；训练参数6个，固定buffer不计入训练参数。用简单的已知整数输入和固定参数核对一个位置，再以非均匀上游权重构造标量损失检查梯度，不要只用一个会意外抵消梯度的对称例子。

把它组合进一个小块，分别使用`Sequential`和自定义`Module`；需要列表时用注册容器。保留一个“同一层被调用两次”的共享参数夹具，证明优化器只管理一份参数、梯度累计来自两次调用。

### 本地记录与自检

1. 参数名、shape、`requires_grad`、唯一参数量、buffer名、state keys及device表。普通张量属性与buffer的差别用观察说明，不把所有张量都设成Parameter。
2. 自定义层输出/梯度的局部比较；复制参数数值而非重新seed后假定相等。局部float64建议`atol=1e-10, rtol=1e-8`。
3. 保存`state_dict`，新建同构模型、严格加载，再用相同输入以eval模式比较输出；参数及持久buffer也逐项比较。共享关系由构造代码重建，不靠state_dict自动创造。
4. 明确CPU设备路径，模型参数、buffer、输入和标签设备兼容；先迁移模型再创建优化器。无GPU也能完成本任务，额外GPU路径如未执行要标明。
5. 说明“预测恢复”比“完整训练恢复”少了什么，任务4再扩展检查点。自己产出的可信检查点可显式用`map_location='cpu'`、`weights_only=True`加载；不加载未知pickle。

**验收**：前向/梯度/注册/共享/保存加载五条各有证据，不能以“没有报错”代替。P3已有参数共享、持久buffer、模型+动量优化器恢复的独立机制证据，可作参照，不冒称你新写的模块已自动通过。

## 任务2：卷积、填充、步幅、通道和池化

**任务id：`cnn-architectures-2`**

先手算，再程序核对；小整数夹具用float64。沿用LEC19–21的互相关、多通道求和与1×1矩阵乘法夹具，不重写整套卷积教程。框架`Conv2d`做互相关，不翻转卷积核。

### 四张检查表

| 夹具 | 输入与设置 | 本地记录 |
|---|---|---|
| 互相关与非对称填充 | 复用P3的3×3输入、2×2核；另用左1/右0/上0/下2，stride=(2,1) | 至少一个窗口乘加过程、全部输出、与框架差值；明确`F.pad`顺序是左右上下 |
| 多通道形状和参数 | `(2,3,8,10)`；Conv2d输出4通道，kernel=(3,5)，padding=(1,2)，stride=(2,3)，dilation=1，groups=1，bias=True | 输出shape、权重shape、参数量；一个输出值如何跨输入通道求和 |
| 1×1卷积 | 同一输入，3→4通道，stride1、padding0、bias=True | 与每个位置同一个仿射矩阵等价；解释为何不是空间平均 |
| 池化 | 单通道2×2负值图，按行`[-1,-2]`、`[-3,-4]`；kernel3、stride1、padding1 | MaxPool、AvgPool的含/不含padding两种分母，逐窗口输出；再复制成两通道，证明不混合通道 |

高度公式中$p_t,p_b$分别是上下补点数量；宽度同理。默认floor模式下：

$$
\begin{aligned}
k_{\rm eff}&=d_h(k_h-1)+1,\\
H_{\rm pad}&=H+p_t+p_b,\\
H_{\rm out}&=\left\lfloor
\frac{H_{\rm pad}-k_{\rm eff}}{s_h}
\right\rfloor+1,\\
P&=C_{\rm out}(C_{\rm in}k_hk_w+1).
\end{aligned}
$$

参数式仅适用于本题groups=1且有bias。N、H、W不改变卷积参数量；池化没有可训练核。普通`padding=(p_h,p_w)`表示每侧各补$p_h,p_w$，不是上下/左右总量。

### 必须覆盖的边界

- MaxPool的隐式padding按负无穷处理，不是补0；负输入正好能揭露错误实现。
- AvgPool隐式补0，`count_include_pad=True/False`改变分母；手工先`F.pad`的0会成为真实输入，不能再要求池化自动辨认哪些原来是padding。
- 池化stride省略时默认等于kernel size，不是1。先显式设`ceil_mode=False`；另以5×5输入、kernel2、stride2比较ceil模式，报告末端窗口和输出形状。ceil不等于任意保留全padding窗口。
- 空间shape一致不证明值一致；至少完成一个负值padding反例和一个多通道求和核验。容差先按dtype确定，不能为了过关盲目调大。

**验收**：手算、张量结果、框架参数统计三者相互印证，错误反例给出原因。局部解析提示在指导页折叠区，不提供整套程序。

## 任务3：LeNet小训练与四种CNN前向

**任务id：`cnn-architectures-3`**

### A. 训练教材形状的LeNet

用28×28单通道输入；保留教材两层5×5卷积（6、16通道，第一层padding2、第二层padding0）、Sigmoid、两次2×2/stride2平均池化，以及120/84/10三层分类头。它是**教材Fashion-MNIST版LeNet**，不是原论文全部历史细节的复刻。不要为了更好看把ReLU/MaxPool版本混称同一基线。

自己推导每一级shape，重点检查Flatten之前每个样本有多少元素；N=1与N=64都要保留batch轴。按共用257/73、Adam、10轮配方完成50更新，保存实际曲线、参数量、至少一层梯度范数和末轮eval预测。可在独立对照中只换激活或池化，但不得覆盖原记录。

### B. 四个网络各有一个完整前向记录

**教材完整前向**与**小规模训练**是两条不同预算。默认按固定教材PyTorch定义，单通道、10类、float32、B1、CPU、`eval()+no_grad()`，逐个构造和释放，避免同时持有几个大模型。只打印shape、参数统计和少量摘要，不保留所有激活张量。

| 网络 | 默认输入 | 不能删除的机制 | 关键检查点（其余逐层自己补） |
|---|---|---|---|
| AlexNet | `(1,1,224,224)` | 5卷积、3最大池化、ReLU、3线性层与2处Dropout | 第一卷积11×11/s4/p1，末池化后256×5×5；分类头4096/4096/10 |
| VGG-11 | `(1,1,224,224)` | 五块卷积数1/1/2/2/2，每块末池化；3线性层、ReLU/Dropout | 通道64/128/256/512/512；空间每块减半，末块512×7×7 |
| NiN | `(1,1,224,224)` | 每块空间卷积后两个1×1/ReLU；3最大池化、Dropout、最后10通道NiN块、全局平均池化 | 第一卷积11×11/s4/p0；最后普通池化后384×5×5；没有大线性分类头 |
| GoogLeNet | `(1,1,96,96)` | 教材stem、9个Inception块（2+5+2）、块间池化、GAP和10类线性头 | 每个Inception四分支H/W一致，沿C拼接；第一个块192输入→256输出 |

四个模型最终均为`(1,10)`且有限；不要给NiN最后额外接一个大MLP。教材本就为Fashion做了改编，因此“教材完整”不等于原论文ImageNet训练复现。

内存不足时仍需保留每个家族的结构：AlexNet可缩通道为12/32/48/48/32、隐藏全连接为256/256；VGG通道16/32/64/128/128、隐藏层256/256；NiN前三块宽24/64/96、最后仍10。**空间输入仍保留224**，池化、卷积数量、1×1层与Dropout不删，展平输入按实际通道重新计算。此时记录名称必须写“编者缩通道前向”，另保留教材完整结构的手算shape表，标明完整宽度未运行，不能把缩版登记为完整宽度验收。GoogLeNet优先保留96输入和教材宽度，不用删分支降成本。

**验收**：LeNet真实训练记录 + 四家族逐层/块shape表 + 参数量/运行模式/输入尺寸 + 各自机制解释，缺一家就不算完成本任务。不要求AlexNet/VGG/NiN/GoogLeNet全量CPU训练，也不比较只做前向的随机模型准确率。

## 任务4：BatchNorm、残差与小ResNet恢复

**任务id：`cnn-architectures-4`**

### A. BN统计与模式实验

用`BatchNorm2d(1, eps=1e-5, momentum=0.1)`，默认affine=True、track_running_stats=True，输入`(1,1,1,2)`、数值[1,3]。从新建层开始，分别记录train、train+no_grad、eval、eval+no_grad的输出、running mean/var、`num_batches_tracked`和是否产生计算图。四组从相同初始状态分支，而不是连续改同一层后误比。

训练统计按每通道的N×H×W元素计算。训练前向用有偏方差，running var更新用无偏估计；momentum=0.1表示新统计占0.1，不是旧统计占0.1。gamma/beta是参数，running统计和计数是buffer。

再比较输入`(1,2,2,2)`和`(1,2,1,1)`。第一种每通道4个元素，可以训练；第二种每通道只有1个元素，PyTorch2.5.1训练会报错。不能笼统写“N=1的BN都不合法”。eval默认使用已保存的运行统计，可以处理单值通道，但这不表示未训练的初始统计可靠。若`track_running_stats=False`，eval也用当前批统计，不能沿用“eval总是冻结统计”的结论。

### B. 残差块局部核验

先用`(2,8,7,7)`检查同通道stride1，再用8→16、stride2检查降采样块。主支保持教材两个3×3卷积及BN，第一次BN后ReLU；第二次BN之后与捷径相加，再ReLU。变通道或变步幅时捷径用1×1投影，并与主支使用匹配stride；本配方投影不另加BN，保持教材定义。

记录相加前两条支路的shape，严格相等才相加，不能依赖广播“恰好可算”。以非负输入把残差支路输出置0检查恒等捷径；负输入还会被相加后的ReLU截断，不能误称块对任意输入都是恒等函数。再检查损失能回传到主支与投影参数。

### C. 小ResNet训练

CPU训练使用**编者小ResNet**：3×3/s1/p1卷积stem，宽8，后接BN/ReLU，不用教材7×7/s2+池化stem；四个stage宽8/16/32/64，每stage两个完整基本残差块。stage1不降采样；stage2–4首块stride2并带1×1投影，其余stride1。末尾GAP、Flatten、10类线性层；不额外添加Dropout或分类头BN。

输入28×28；stem和stage1保持28，随后14→7→4，末stage有16个空间位置，因此B1尾批仍满足BN统计量数量要求。保留八个残差块、BN、三次投影和GAP，不能把只含一个块的网络称为这套配方。按共用配置完成10轮50更新；记录初始/逐轮训练验证指标、各stage形状、BN统计是否更新、末轮预测。

教材完整宽度ResNet-18可另做B1、96×96、eval前向（64/128/256/512，各两块，7×7/s2/p3 stem与3×3/s2/p1池化），输出`(1,10)`。它与28输入的小训练模型分开记录，既不声称小模型是原ImageNet架构，也不要求完整宽度全训。

### D. 从预测一致推进到下一步训练一致

至少在完成一次参数更新后保存，最好选epoch边界，避免还需恢复半轮游标。检查点包含：

| 状态 | 为什么需要 |
|---|---|
| 模型state_dict | 参数和所有BN running mean/var、计数等持久buffer |
| 优化器state_dict | Adam一阶/二阶矩、step计数、参数组超参数；只加载模型不等于继续同一优化轨迹 |
| 模型/预处理/数据配置 | 结构、数据校验、划分索引、归一化约定、版本、dtype/device |
| 进度与模式 | 已完成epoch/更新数；train/eval不是state_dict中的自动恢复项 |
| 随机状态和数据顺序 | torch CPU RNG；独立shuffle generator状态；若用了Python/NumPy/其他设备随机源，也分别保存 |

恢复时新建同构模型和绑定它的新优化器，加载模型与优化器后再恢复随机态；构造模型本身会消耗随机数。可信本地检查点采用张量/基本类型字典，显式限制加载方式。若额外引入scheduler、AMP scaler或随机增广，其状态也必须随之保存，本CPU基线不使用它们。

先用同一固定输入验证eval预测与BN buffers一致；再从独立快照分出“不中断”和“恢复”两路，以**同一下一batch、相同模式和随机态**完成一步训练，比较loss、梯度、更新后的全部模型状态与优化器状态。float32建议`atol=1e-6, rtol=1e-5`，整数计数与索引要求精确相等。恢复前后的下一随机数及下一批索引也要比较；本模型没有Dropout，单次loss相同不足以证明RNG恢复正确。

最后做故障对照：只恢复模型、重建空Adam，下一步通常不再一致；漏BN buffers可能使预测先不一致。故障应定位到丢失了哪种状态，而不是靠放宽容差掩盖。检查点暂存自己的运行目录，或可信内存字节流；不可只持有浅层`state_dict()`引用后继续训练再说那是旧快照。

## 本地记录与自检

在本地保存四个task id对应的配置/证据，自己实现而非复制整套答案。每条结果区分**手算预期、实际执行、未执行**。报告网络名称、是否缩版、输入与每层shape、参数量、实际样本数/更新数、模式、数据来源/哈希、失败分析及恢复检查。训练成功不证明泛化优秀；前向成功不证明反向、训练或原论文复现。

<details>
<summary>自检：为什么不是“所有网络都先换成28×28”就能省算力？</summary>

AlexNet/NiN的11×11大步幅卷积和多次池化会很快耗尽空间；VGG五次池化也会使28输入的空间归零。删池化或删块是在换结构，不是原结构验证。保留224前向、缩batch/通道，并把真实执行范围写清更诚实。

</details>

<details>
<summary>自检：模型权重与预测一样，恢复验收就结束了吗？</summary>

没有。必须比较BN buffers、优化器历史、下一随机数/数据顺序和下一次更新。eval预测一致只证明较窄的推理路径，不能证明训练轨迹继续一致。

</details>

## 来源、版本、许可与验收边界

本实验为本站自主组织的中文练习，非官方编号Lab译文；无对应英文稿，不生成英文占位。中文第二版固定提交为`e6b18ccea71451a55fcd861d7b96fddf2587b09a`，不是2021教材快照。实际审读的正文/代码节选、URL、SHA-256及复用证据见`sources/p4-cnn-architectures/manifest-fragment.json`。

- 张阿斯顿、李沐、扎卡里·C.立顿、亚历山大·J.斯莫拉，《动手学深度学习》：[6.5汇聚层](https://zh.d2l.ai/chapter_convolutional-neural-networks/pooling.html)、[6.6 LeNet](https://zh.d2l.ai/chapter_convolutional-neural-networks/lenet.html)、[7.1 AlexNet](https://zh.d2l.ai/chapter_convolutional-modern/alexnet.html)、[7.2 VGG](https://zh.d2l.ai/chapter_convolutional-modern/vgg.html)、[7.3 NiN](https://zh.d2l.ai/chapter_convolutional-modern/nin.html)、[7.4 GoogLeNet](https://zh.d2l.ai/chapter_convolutional-modern/googlenet.html)、[7.5 BN](https://zh.d2l.ai/chapter_convolutional-modern/batch-norm.html)、[7.6 ResNet](https://zh.d2l.ai/chapter_convolutional-modern/resnet.html)。网页便于导航，实际依据固定仓库源码；本页不复制第三方架构图。
- 教材固定仓库[根LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)为Apache-2.0；setup.py的MIT-0字段独立记录，不替代根许可，不外推视频/数据。来源源码以`.txt`保存，正文、题目、配方与解析例为编者改编。
- 现代语义按[PyTorch v2.5.1 pooling](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/modules/pooling.py)、[BatchNorm2d](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/modules/batchnorm.py)、[functional训练批量检查](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/functional.py)、[CPU随机态](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/random.py)实读节选；PyTorch自身[LICENSE](https://github.com/pytorch/pytorch/blob/v2.5.1/LICENSE)单独保留。模块/检查点API复用LEC16的PyTorch2.5审读记录。
- Fashion-MNIST来自[Zalando官方仓库](https://github.com/zalandoresearch/fashion-mnist)，MIT许可与官方四个gzip的校验沿P2。数据只在运行时cache；本页不重复发布数据。校验值和IDX头见`sources/p2-shared/dataset-acquisition.json`，许可原件见`sources/p2-linear-training/fashion-mnist-LICENSE.txt`。
- 已有P3证据只覆盖当时的小型模块/共享/卷积/动量恢复，不证明本次CNN已执行。本文预期不是运行日志；本次独立数值、LeNet与小ResNet小基线、构建和浏览器验收由主agent记录到课程状态/公共资料，不能倒推为学生四任务全部完成。
- 没有据完整课堂音视频或字幕编写本实验，不造时间轴、课堂演示或官方评分；原视频由学习者自行观看，不设置课堂补稿要求。不创建draft/materials占位。
