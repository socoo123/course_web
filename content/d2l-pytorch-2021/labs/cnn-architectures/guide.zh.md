---
title: CNN实验：形状、状态与恢复的排错路线
kind: 编者指导（不是官方解答或完整程序）
source: 固定中文第二版6.5–6.6、7.1–7.6正文与PyTorch节选；LEC16–17、19–21及P2/P3证据
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 未依据课堂音视频、演示或问答制作
license: 教材源码Apache-2.0；PyTorch与Fashion-MNIST授权独立；局部解析为编者自主整理
status: 主agent已完成独立CPU机制、小基线与恢复验收；本页仍只给路线与局部解析，精确运行范围见公共资料，不提供完整答案
version_boundary: 当前中文第二版不是2021快照；PyTorch语义按2.5.1
---

# CNN实验：形状、状态与恢复的排错路线

## 先做局部正确，再做一次训练

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

[实验说明](#/c/d2l-pytorch-2021/lab/cnn-architectures?v=zh)规定四任务的输入、配置、本地记录与执行边界。本页只给路线、不变量与局部答案；没有可直接复制的完整网络加训练循环，也不要求先刷论文。本地使用Python/PyTorch练习。

保持少量普通部件：模型构造、已有训练一步/评估、shape记录、状态快照与比较。别先写通用框架。依次过五道门：**轴的含义 → 局部值 → 参数与梯度 → 模式及buffer → 连续/恢复两路比较**。遇到不一致，回到第一个不同的边界，而不是先增大网络或训练轮数。

## 任务1：计算图和注册结构是两份合同

### 建议顺序

1. 先单测自定义仿射层：输入`(2,3,4,4)`，输出同形，gamma/beta各3个标量，固定offset用buffer。把通道参数视图变为`(1,3,1,1)`再广播，不要误沿宽度广播。
2. 初始化gamma=1、beta=0、offset=0时输出应等于输入。再为每个通道给不同值，用一个位置手算；否则所有通道相等容易掩盖错轴。
3. 损失用带不同位置权重的输出加权和，检查输入、gamma、beta的梯度；固定offset默认不需要梯度。不要在forward里对参数使用`.data`、`detach`或重新包装张量。
4. 模块组合先用单路，再加共享层。列出`named_parameters()`与`state_dict()`，分别回答“优化器管理几个唯一对象”和“状态字典有哪些路径”。共享参数可能出现在多个状态路径，不能用key数当唯一参数数。
5. 先把模型迁移到目标device，再绑定优化器。保存并重建模型时严格检查missing/unexpected keys；不要以`strict=False`掩盖结构错配。

<details>
<summary>局部推导：逐通道仿射层的梯度沿哪些轴求和？</summary>

设$Y_{nchw}=\gamma_cX_{nchw}+\beta_c+o_c$，上游梯度为$G$，则

$$
\begin{aligned}
\frac{\partial L}{\partial X_{nchw}}&=G_{nchw}\gamma_c,\\
\frac{\partial L}{\partial\gamma_c}&=\sum_{n,h,w}G_{nchw}X_{nchw},\\
\frac{\partial L}{\partial\beta_c}&=\sum_{n,h,w}G_{nchw}.
\end{aligned}
$$

每通道共享的标量收集该通道所有位置的贡献，不是对通道轴再求和。三个gamma和三个beta共6个训练标量；buffer的3个值不计入可训练参数量。

</details>

<details>
<summary>为什么存了state_dict，继续训练后“旧模型”也变了？</summary>

`state_dict()`给出浅层映射，里面的张量引用模型状态；不是历史快照。需要独立副本或立即序列化到自己的可信文件/内存字节流。两路恢复比较也不能让模型共享参数、buffer或优化器历史存储。P3已经验证过这种状态管理思路，但你仍须检查新CNN的全部状态。

</details>

<details>
<summary>CPU实验怎么验收“设备迁移”，又不假装测过GPU？</summary>

显式选择CPU，检查参数、持久buffer和输入device；检查输入float32、标签long。展示Tensor的`.to()`返回值需要接住，而Module的`.to()`会修改注册对象。没有实际GPU运算就只报告CPU路径；可用性探测不能替代迁移计算。不要故意在无CUDA设备上运行以制造“教材错误”。

</details>

## 任务2：把空间、通道、参数三本账分开

### 先写小整数，再写大随机张量

复用P3互相关夹具时，明确输入按行是0/1/2、3/4/5、6/7/8，核按行是1/2、3/4，stride1、无padding。先圈左上2×2窗口，逐位置相乘求和。非对称padding用同一份原输入，`F.pad`参数顺序为`(left,right,top,bottom)`；补点之后再执行不额外padding的卷积，避免重复补点。

多通道卷积可以理解为：对每个输出通道，分别拿它对应的每个输入通道核做互相关，然后沿输入通道求和，最后只加一次该输出通道的bias。**batch之间不求和**。1×1卷积只混合同一位置的通道，并不自动扩大空间感受野。

<details>
<summary>解析核对：P3互相关和非对称padding应该得到什么？</summary>

原始互相关输出两行分别为`[27,37]`、`[57,67]`，左上值是$0\times1+1\times2+3\times3+4\times4=27$。左1、右0、上0、下2、stride=(2,1)时输出两行是`[12,27,37]`、`[12,20,23]`。这里复用P3已保存机制证据，不把它说成本次重新执行结果。

</details>

<details>
<summary>解析核对：3输入通道、4输出通道的形状题</summary>

输入`(2,3,8,10)`、kernel=(3,5)、padding=(1,2)、stride=(2,3)：高度为4、宽度为4，输出`(2,4,4,4)`；权重`(4,3,3,5)`、bias`(4,)`，共184个参数。若漏了输入通道求和，会把每个输出通道误当成一个独立单通道核。

1×1、stride1、无padding时输出`(2,4,8,10)`，参数$4\times3+4=16$。将通道移到末轴后逐位置右乘转置权重，再移回，才可与Conv2d的NCHW输出比较；不能直接把NCHW当作最后一轴是通道。

</details>

### 池化的padding不是统一规则

负值图能区分“最大池化隐式负无穷”与“先手工补0再最大池化”。平均池化还要写清有效输入计数、padding计数和分母；三种情况不可混为一谈。

<details>
<summary>解析核对：负值2×2图，kernel3/stride1/padding1</summary>

原图两行为`[-1,-2]`和`[-3,-4]`。四个输出窗口都覆盖这四个原值，输出shape仍为`(1,1,2,2)`。MaxPool每个输出都是-1；若错误补0会得到0。AvgPool包含padding时每个输出为$-10/9$；不包含padding时为$-10/4=-2.5$。两通道时分别操作，不把两个通道的八个值一起平均。

这些是解析预期，不是本页运行日志。使用浮点比较，不要求$-10/9$在二进制浮点中精确表示。

</details>

<details>
<summary>解析核对：5×5、kernel2、stride2，floor和ceil有何不同？</summary>

无padding时floor模式每轴2个输出，ceil模式每轴3个。最后一个窗口只包含边界内的真实元素；PyTorch会忽略从右/下padding区开始的窗口，不能把所有输出都解释成完整2×2真实输入。请分别画出最后窗口，再查你所用Max/AvgPool的分母规则；本题数值主验收仍采用显式floor、显式padding的负值夹具。

</details>

## 任务3：所有架构保留，只把训练预算分层

### LeNet先检查Flatten边界

28输入经过第一层带padding卷积、平均池化、第二层不带padding卷积和平均池化，空间依次为28→14→10→5。通道依次为6、16；Flatten只合并非batch轴，因此每样本400个特征，而不是把整个batch展成一条向量。分类头120→84→10，隐藏层Sigmoid；输出层不接Sigmoid/Softmax。

训练排错优先级：先确认每步更新计数、labels/损失、参数梯度；再看数据顺序、初始化、学习率；最后才谈模型容量。B64的257张必须消费64+64+64+64+1，共5次更新；不要让日志打印逻辑的除法对小数据集产生除0，也不直接照抄教材辅助训练器。

<details>
<summary>局部核对：这版LeNet有多少个参数？</summary>

两卷积分别为156与2416，三个线性层为48120、10164、850，总计61706（均有bias）。Sigmoid、AvgPool与Flatten没有可训练参数。相同网络改变batch不会改变参数量；一张28图的像素数也不是这个网络的参数数。

</details>

### 前向shape跟踪不能执行分支的错误顺序

AlexNet/VGG/NiN外层是单路序列，可以按层记录；GoogLeNet的Inception内部是四路并行，不能把四路排成一个Sequential。可用临时forward hook收集**shape字符串**，完成后移除；不要把所有带计算图的激活存进列表，更不要为了记录而额外执行一次train前向，污染BN统计。

- **AlexNet**：224经过11×11/s4/p1成为54，池化为26；第二卷积保持26，池化为12；三个3×3保持12，末池化为5。展平输入是256×5×5=6400，不是torchvision不同实现可能给出的其他值。
- **VGG-11**：五块末空间112/56/28/14/7；“11”计8卷积+3线性，不是11个卷积块。缩通道可省参数，但把4096分类头保留时仍可能很大；预算表应分别列卷积区与分类头参数量。
- **NiN**：首层padding0使224变54；后续最大池化空间同样26/12/5。每个NiN块里的两个1×1层及ReLU仍保留；最后10通道特征图经GAP变`(N,10,1,1)`，Flatten变`(N,10)`。
- **GoogLeNet**：96输入，stem两段后24、12；前两Inception后池化到6，中间五个后到3，最后两个后GAP。检查9个块都存在，不能仅测一个Inception就说整网完成。

<details>
<summary>Inception局部题：输入(2,8,11,13)，四路怎么拼？</summary>

自拟小块的四路输出通道取2、4、3、2：第一路1×1；第二路1×1降到3再3×3/p1到4；第三路1×1降到2再5×5/p2到3；第四路3×3/s1/p1最大池化再1×1到2。每路H/W都是11/13，沿dim=1拼接得到`(2,11,11,13)`。

通道数11与高度11恰好相等，不能仅凭某轴数值判断轴语义。先写N/C/H/W名字，再比较。若误按dim=2拼接，其他轴的通道数又不同，不能靠reshape“修好”。

</details>

<details>
<summary>为什么不要直接用torchvision同名模型取代教材？</summary>

同名实现可能有不同输入通道、padding、分类数、辅助分类头、BN或自适应池化。直接替换会让shape与参数量账目改变。先按固定教材完成这份合同；torchvision可以作为注明版本与差异的扩展，但不是无说明替代。无需下载预训练权重，也不以随机初始化前向的accuracy比较网络优劣。

</details>

## 任务4：模式开关与随机状态要分别管

### BN只沿N/H/W聚合，不沿C聚合

对每个通道，令$m=N H W$，训练前向为：

$$
\begin{aligned}
\mu_c&=\frac1m\sum_{n,h,w}X_{nchw},\\
v_c&=\frac1m\sum_{n,h,w}(X_{nchw}-\mu_c)^2,\\
Y_{nchw}&=\gamma_c
\frac{X_{nchw}-\mu_c}{\sqrt{v_c+\epsilon}}+\beta_c.
\end{aligned}
$$

gamma和beta各有C个标量；不要把它们写成每个像素独立的参数。eval默认用running mean/var，它们是历史批次的估计，不是自动重新计算全训练集精确统计。

| 组合（默认跟踪running统计） | 用哪种统计 | 更新running buffers | 记录参数梯度图 |
|---|---|---|---|
| train，梯度开启 | 当前batch | 是 | 是，若参数需要梯度 |
| train + no_grad | 当前batch | 是 | 否 |
| eval，梯度开启 | running统计 | 否 | 是，若参数需要梯度 |
| eval + no_grad | running统计 | 否 | 否 |

**不要照搬教材从零BN的模式判断**：该教学实现用`torch.is_grad_enabled()`选择统计路径，而且moving统计是普通张量属性；它与标准`nn.BatchNorm2d`的train/eval、持久buffer语义不同。本实验用标准模块；若自行实现BN，应显式依赖`self.training`并注册buffer，不能以关闭autograd代替eval。

<details>
<summary>解析核对：[1,3]在新建BatchNorm2d中第一次训练前向</summary>

输入shape`(1,1,1,2)`，$m=2$，均值2、有偏方差1、无偏方差2。默认gamma=1、beta=0，输出是$[-1,1]/\sqrt{1+10^{-5}}$。momentum=0.1，running mean从0变0.2，running var从1变1.1，num_batches_tracked从0变1。

同一初始状态的eval输出则用均值0、方差1，即$[1,3]/\sqrt{1+10^{-5}}$，不是训练输出。train+no_grad仍更新统计。这里输出方差因为epsilon并非严格1；别把这个小差异判为公式错误。

</details>

<details>
<summary>尾批只有1个样本，为什么小ResNet可以训练而BN分类头可能失败？</summary>

小ResNet末stage仍有4×4空间，每通道统计数量为1×4×4=16；早期层更多。若GAP后又接BN，输入变成`(1,C,1,1)`或Flatten后`(1,C)`，每通道仅1个元素，训练时会报错。说明书刻意不在分类头加BN，不靠`drop_last=True`丢样本隐藏问题。

若你的其他架构确实需要BN1d且会遇单样本尾批，应事先选择合并尾批等明确的数据策略，并重新记录batch和更新次数；不能静默改合同。更大的batch也不自动保证统计质量，空间像素并不一定独立。

</details>

### 残差不是拼接

Inception把通道加宽；残差是对应元素相加，输出通道不会自动翻倍。降采样块两条路都要把7×7变4×4：主路3×3/p1/s2，投影1×1/p0/s2。奇数尺寸按公式向下取整后的结果是4，不是把7除以2后随意写3。

<details>
<summary>置零残差支路时，输出是否一定等于X？</summary>

本实验教材式块输出$\operatorname{ReLU}(F(X)+S(X))$。当$F=0$且$S(X)=X$，输出是ReLU(X)：对非负X等于X，对负值会截断。若捷径有投影，就不是恒等捷径。测试时确保残差支路最后实际输出为0；仅将某层weight置0但留着bias/BN beta，不一定满足条件。

</details>

### 恢复检查分四层，不只看一张预测图

1. **静态层**：记录架构配置，严格加载参数与持久buffer。比较每个state key的dtype/shape/device；浮点用容差，计数用精确相等。
2. **预测层**：两路都eval+no_grad，同输入比较logits与预测；eval不得修改BN buffers。
3. **随机/顺序层**：恢复torch CPU RNG和独立shuffle generator；恢复后的下一随机数、下一批索引要与不中断路线一致。若采用DataLoader，构造迭代器也可能消耗generator，须约定在同一时间点保存和恢复；优先在epoch边界做本实验。
4. **训练层**：两路各自从同一快照启动，切train，用同一下一batch，各做一次zero_grad→forward→loss→backward→step。比较loss、各参数梯度、参数、BN统计和优化器历史。不要先在其中一路多跑一次train预测。

只保存seed不能替代当前RNG状态，因为seed描述随机流起点，不描述已经取了多少次。此小ResNet无Dropout，固定batch的一步可能根本不取随机数；因此不能以loss一致推断RNG正确。单独检查下一随机样本，或另设小Dropout机制夹具，不把Dropout偷偷加入基线架构。

<details>
<summary>为什么要先重建并加载，再恢复RNG？</summary>

构造卷积/线性层会初始化并消耗随机数；若先恢复RNG再构造模型，接下来的随机流已被推进。两条路线比较时，顺序和状态恢复时间点必须相同；创建完模型、优化器及必要对象，加载状态后，在下一次随机操作之前恢复RNG。保存时机还须约定在一次step完成之后；若在梯度累积中途保存，仅state_dict不能恢复尚未应用的梯度。

</details>

<details>
<summary>只恢复权重，Adam的下一步为何不同？</summary>

Adam用历史梯度的一阶/二阶矩和step计数计算更新及偏差修正。新建优化器把这些历史清空，即使输入、权重和本次梯度一样，更新也可能不同。预测阶段不调用优化器，所以“预测相等”无法排除这一错误。故障对照要在优化器至少已有一次更新后进行，并报告实际差值，不保证任意特殊梯度都一定产生差异。

</details>

## 排错只改变一个条件

| 现象 | 优先检查 | 不要做 |
|---|---|---|
| Linear矩阵维度不匹配 | 实际Flatten前C/H/W、是否把batch压掉 | 随手reshape成想要的形状 |
| 大网络空间归零 | 首卷积kernel/stride/padding、每次池化、输入尺寸 | 删除关键层还声称原架构通过 |
| 负输入池化突然出现0 | 是否手工补0代替MaxPool隐式padding | 把所有输入取绝对值躲掉反例 |
| 验证后训练异常变化 | 是否恢复train；验证是否错误更新BN | 只加no_grad就当eval |
| BN训练报单值错误 | 每通道N×H×W或BN1d的实际统计轴 | 关闭错误检查、静默丢尾批 |
| Inception无法cat | 四分支N/H/W与拼接轴 | 把不匹配分支裁掉 |
| 残差能加但含义不对 | 两路shape是否严格相等、有无广播 | 仅凭没有异常就通过 |
| 恢复预测不一致 | state keys、BN buffers、eval、输入预处理 | 先换随机seed |
| 预测一致、下一步不一致 | optimizer历史、模式、数据顺序、RNG、快照别名 | 只放宽浮点容差 |
| CE不下降 | labels、梯度、step数、初值、lr，再考虑预算 | 换验证子集或删失败日志 |

## 来源与范围

教材作者、八节入口、固定提交、API与数据许可见[实验说明页底](#/c/d2l-pytorch-2021/lab/cnn-architectures?v=zh)。本页实际依据固定中文第二版中PyTorch代码及相关正文，不依赖未取得的课堂字幕；不是官方解答译文，不造课堂时间轴。

现代行为补充来自PyTorch v2.5.1的[池化源码](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/modules/pooling.py)、[BN定义](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/modules/batchnorm.py)、[批量退化检查](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/nn/functional.py)、[CPU RNG接口](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/random.py)，并复用LEC16已审读的模块/存取API。PyTorch源码节选遵循其独立LICENSE，不以教材Apache-2.0覆盖。

公式、小整数夹具、状态分层、CPU配方和自测为编者补充；无完整答案程序。本文没有执行课程代码或学生完整任务。P3历史通过项与本次解析预期分开登记；本次主agent独立验收结果以课程状态/公共资料为准，不外推CUDA/MPS、旧Notebook、全量Fashion训练或原论文成绩。
