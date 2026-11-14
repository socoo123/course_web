---
title: 优化与全课程工程总结实验指导
kind: 思路骨架、局部提示与排查，不是完整答案
source: 原四任务；PyTorch 2.5官方API；P1–P10保留记录；P11主agent真实小训练证据
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
status: worker未执行数值；已读取并在末节整合主agent独立数值证据；浏览器和构建由主agent统一验收；课堂学习与竞赛仍独立记账
license: 自主讲解；教材、数据、预训练权重和视频授权互不替代
---

# 优化与全课程工程总结实验指导

## 从一条训练状态链开始

先拿纸写出“数据身份→初值→本轮排列→下一批→梯度→更新→调度→下一步”的状态链，再把已有模型放回这条链。你要解释的不是哪个API名字更高级，而是哪些状态会影响下一步，以及怎样证明比较条件一致。

[实验说明](#/c/d2l-pytorch-2021/lab/optimization-capstone?v=zh)保留四任务原文及完整交付合同。本指导只给分解、局部公式和排查路径；不提供可复制运行的完整训练/恢复脚本。通用xv6命令框不适用。

## 任务1路线：先查控制变量，再读优化曲线

### 1. 用一个真实小模型，避免换题

复用Fashion-MNIST小划分，不下载另一个同名镜像，不拿合成标签替代真实衣物类别。冻结一个小MLP的结构和预处理，逐项核对输入、标签、logits与loss：

| 节点 | 需自己给出的检查 |
|---|---|
| 图像 | `B×1×28×28`；像素量纲与dtype |
| 展平 | 保留B轴，得到`B×784`；不是将全batch拉成一维 |
| 隐层 | 线性映射、ReLU；有无dropout明确 |
| 输出 | `B×10`未归一化logits；类别轴明确 |
| 标签 | `B`个0至9的long整数，不是float独热向量 |
| 损失 | 每样本CE；求平均用于更新，汇总时保留样本数 |

结构一旦定下，不要为某个优化器偷偷增加宽度、改激活、调裁剪或延长训练。`state_dict()`返回的是引用相关张量的字典；保存“初始状态”时应形成独立快照或立即序列化，不能拿仍随训练变动的引用当共同起点。

让三份优化器各自绑定自己的模型参数，参数组顺序固定。若模型使用dropout，初始化RNG、采样Generator和dropout所用全局RNG最好分开管理。每个run都从相同状态重新开始；验证过程用`eval`且不意外消耗训练随机序列。

### 2. 只手推足以辨别实现的两步

令$g_t$为当前batch的平均损失梯度，以下不含weight decay、不用Nesterov，动量的dampening为0：

$$
\theta_t=\theta_{t-1}-\eta_t g_t
$$

普通SGD的学习历史体现在参数里；无动量时通常没有每参数动量buffer，但当前参数组LR和scheduler仍可能需要恢复。

PyTorch动量SGD使用：

$$
b_t=\mu b_{t-1}+g_t
$$

$$
\theta_t=\theta_{t-1}-\eta_t b_t
$$

首步buffer取首步梯度。在这里dampening为0时，与从零buffer开始的首步结果一致；不要推广到所有变体。PyTorch把学习率放在参数更新处，不是存进buffer；调度发生时，混用另一种速度定义会改变行为。

Adam在一、二阶矩为零的初态下：

$$
m_t=\beta_1m_{t-1}+(1-\beta_1)g_t
$$

$$
v_t=\beta_2v_{t-1}+(1-\beta_2)g_t^2
$$

$$
\begin{aligned}
\hat m_t&=m_t/(1-\beta_1^t)\\
\hat v_t&=v_t/(1-\beta_2^t)
\end{aligned}
$$

$$
\theta_t=\theta_{t-1}
-\eta_t\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}
$$

平方逐元素计算；第二步即使梯度相同，历史状态和偏差修正也不能丢。这里是普通Adam，不是AdamW；主比较weight decay为0，避免混入耦合/解耦正则化的另一问题。公式能解释状态字段，但不是要求你发布完整优化器实现。

局部练习：自选二维初值和两个不同方向的梯度，分别记录两步后的参数、buffer/矩与step，用float64小张量和API对照。不要只测一步，因为那常常看不出历史状态错误。其他优化方法去教材按需对照，不追加必做训练或必读论文。

### 3. 选学习率要回答“在比较哪个问题”

同一个数值LR不代表同样的参数移动：动量会累积方向，Adam还会按坐标缩放。若三组都设0.01，应把结论限制为“这组同数值LR配置下的有限对照”，不说它们已公平调到最好。若自主做等预算LR搜索，应先登记候选集合/预算/验证指标与最终选择规则，不能事后只为落后者追加预算。

记录loss时，区分下面三个量：

- 在线batch loss：前向时模型尚未做本批更新，也可能启用dropout。
- 固定训练子集的评估CE：同一checkpoint、`eval`、整组样本聚合。
- 验证CE：同一评估时点，但来自未参与梯度更新的固定验证子集。

同一轮包含不同大小的batch，聚合公式是：

$$
L=\frac{\sum_b n_b L_b}{\sum_b n_b}
$$

这里$L_b$必须是batch均值，$n_b$是实际样本数。对尾批1和正常批64直接取均值，会把尾批影响放大。对于语言任务，用有效token数代替$n_b$，不能机械沿用样本数。

曲线应标明横轴、评估模式、学习率策略和实际数据点。准确率与CE可能方向不同：预测类别相同但置信度变化也会改变CE；不要删去非单调片段。单seed、小划分、同数值LR不支持总体算法排名。

## 任务2路线：把恢复点定义成一个状态切面

### 1. 先写清调度单位

以每20次**已完成更新**将LR乘0.5为例，第一次更新用初始LR。`optimizer.step()`完成后推进scheduler，于第20次更新后改变下一次所用LR。下表是这一约定的时序解释，不是对任何调度器默认行为的泛化：

| 完成更新数 | 刚完成更新所用LR | 若继续，下一步LR |
|---|---|---|
| 19 | 初始LR | 初始LR |
| 20 | 初始LR | 初始LR×0.5 |
| 21 | 初始LR×0.5 | 初始LR×0.5 |

日志应同时保留`lrUsed`与`nextLR`，避免把更新后的LR画到刚完成的更新上。`last_epoch`是状态字段名；每步调用时它跟随调用计数，而不是数据epoch。不要把恢复后的`global_step`直接塞进这个字段却不恢复其余状态。

构造恢复对象时先有model，再让optimizer绑定它，再构造scheduler；随后按保存对象恢复model、scheduler及optimizer状态，核对当前参数组LR和scheduler状态相容。关键是**不要在装好optimizer之后又用新scheduler初始化覆盖其LR**。恢复后不为“对齐计数”多调用一次step，也不重新手动衰减。

### 2. 稳定交叉熵的关键是先移动坐标

对单个样本logits $z$，取$a=\max_j z_j$：

$$
\operatorname{LSE}(z)=a+\log\sum_j e^{z_j-a}
$$

$$
\ell(z,y)=\operatorname{LSE}(z)-z_y
$$

两项抵消公共偏移，因此所有类别同时加常数不改变理论CE。直接算`exp(z)`可能先溢出；把已经非有限的概率再取log不能补救。实际训练直接把logits交给`CrossEntropyLoss`，而不是先softmax再套CE。

局部提示：用相差1但整体很大的两个logits和一个很小的logit，比较稳定计算与朴素计算；同时检查梯度，不只看loss。另用正常幅度输入验证两个计算在容差内一致。这个合成例子只说明数值实现，不证明真实训练发生过爆炸。

排查非有限值按顺序缩小边界：输入/标签→logits→loss→backward梯度→裁剪→optimizer状态→更新后参数。优先定位第一个出错张量与算子，检查输入量纲、标签范围、过大学习率和分母。不要跳过坏batch来制造“全部正常”。

### 3. 采样器不仅是随机种子

设当前epoch的样本排列为$\pi$，游标$c$指向下一未消费位置。下一batch取这张排列的一段；用完以后，才用shuffle Generator产生下一张排列。中途保存时，仅保存Generator的当前状态可能只能重现**下一轮**排列，无法恢复已经生成但消费了一半的当前排列。

最小合同：`epoch`采用从0开始的当前轮编号；`cursor`是当前排列已消费样本数；`global_step`是已完成参数更新数。尾批不足B时照实消费，不虚构重复样本凑整。把当前排列、游标、shuffle RNG一起保存，并说明游标到达末尾时是先换轮还是等下一次取批才换轮。

若你使用数据增强或多worker预取，进程内已生成但未消费的batch会成为额外状态。先在无增强、worker0的合同闭合恢复，不把这项小验收扩展为分布式数据管线已经支持任意断点。

### 4. 新进程应拿到哪些东西？

只列接口和不变量，自行组织代码：

| 阶段 | 输入/输出合同 | 最常漏掉的状态 |
|---|---|---|
| 准备 | 数据/配置身份→模型、optimizer、scheduler | 参数组顺序、模型buffer、dtype |
| 保存 | 更新与调度结束→磁盘状态包 | 当前LR、scheduler计数、CPU RNG |
| 进程退出 | 仅磁盘文件与独立配置可用 | 不能依赖全局变量或内存对象 |
| 重建 | 新对象加载同状态 | 初始化消耗RNG，恢复RNG要放在其后 |
| 下一批 | 当前排列与游标→同一批ID | 只恢复seed却重新shuffle |
| 下一步 | 同模式与随机输入→同loss/梯度/更新 | dropout RNG、Adam矩和step |

一般还需要Python/NumPy实际用到的随机源、设备RNG、scaler或梯度累积状态；**未使用**的组件应写不适用，不伪称恢复过。训练模式不是仅靠参数字典就能完整表达的运行意图，恢复后显式确定`train`/`eval`。

只装可信的本地checkpoint，采用张量/基础容器的状态字典并显式`weights_only=True`；不要为了载入来源不明的文件关闭限制。当前文档示例并不保证旧环境默认值一样。恢复之前核数据与配置身份，缺字段应解释并停止对应验收，而不是悄悄以默认值继续。

### 5. 怎样证明真的恢复了？

先对齐离散对象：batch原始ID、epoch、游标、global_step、参数组LR。再比较同一步的loss、梯度与更新后参数；最后比较optimizer、scheduler、RNG和采样状态。只看预测相同、最终accuracy相近或load没有报错都不够。

负对照应只漏你声称研究的状态。比如若漏整个optimizer字典，既丢了Adam矩，也可能丢了当前LR；此时观察到差异只证明“漏整个optimizer破坏续接”，不能归因为单独的矩。若要隔离矩，需另保持参数组LR、其他状态和输入一致，不能偷换结论。

## 任务3路线：用同一问法复盘不同模型

每条路线都问六个问题：预测单位是什么？哪些轴不能交换？loss除以谁？验证时能看到什么？哪条证据真的运行过？资源代价来自哪里？下面是填写方向，不是替你写好的个人总结。

| 回看入口 | 用自己的旧记录回答 |
|---|---|
| [MLP与泛化](#/c/d2l-pytorch-2021/lab/mlp-generalization?v=guide) | 表格预处理是否仅fit训练折？回归目标变换为何影响指标？合成MLP与真实Ames证据是否分开？ |
| [CNN结构](#/c/d2l-pytorch-2021/lab/cnn-architectures?v=guide) | 逐层空间尺寸、残差相加条件、BN模式；LeNet/小ResNet不同参数量不构成纯优化器对照。 |
| [CV迁移](#/c/d2l-pytorch-2021/lab/cv-transfer?v=guide) | 冻结参数是否同时冻结BN统计？随机初始化前向不是预训练迁移；树叶、CIFAR、Dogs缺口不补成已训练。 |
| [密集预测](#/c/d2l-pytorch-2021/lab/cv-dense-prediction?v=guide) | 检测框、分割像素、风格图像的预测对象不同；banana零检测和VOC近背景是有价值的失败，而非应删数据。 |
| [RNN语言模型](#/c/d2l-pytorch-2021/lab/recurrent-language-model?v=guide) | 时间切片如何对齐标签？状态在哪detach？PPL有改善时实际生成是否仍重复？ |
| [seq2seq与Attention](#/c/d2l-pytorch-2021/lab/seq2seq-attention?v=guide) | 源mask和目标loss mask各管什么？自由生成是否读了真实目标长度？attention图不自动等于正确对齐。 |
| [Transformer](#/c/d2l-pytorch-2021/lab/transformer?v=guide) | 多头轴、causal mask、位置offset和重复beam父节点如何处理？self-KV缓存正确不等于已测提速。 |
| [BERT](#/c/d2l-pytorch-2021/lab/bert-pretrain-finetune?v=guide) | MLM/NSP分母、特殊token及SNLI标签映射；小词表预训练与加载60,005词预训练包是两条独立证据。 |
| [计算性能](#/c/d2l-pytorch-2021/lab/training-performance?v=guide) | 端到端与算子计时是否混淆？RSS是否包含框架？逻辑PS或通信算术是否被误称多机实测？ |

保持旧记录的真实层次：P2真实Fashion线性分类、P3真实Ames小型折内预处理/重训导出、P4真实Fashion CNN、P7 banana/VOC/两图风格、P8真实语言模型、P9真实英法GRU、P10真实Transformer/WikiText小训练及预训练BERT迁移。它们没有因P11没重跑而变成“从未运行”，也没有自动升级为你已完成每个学生任务。

P6的随机ResNet18机制与P7真实预训练ResNet18迁移分开；P7 VGG19风格优化与P10教材BERT权重也是不同资产。P5确有有限CPU计时，仍无CUDA/MPS、多GPU或网络通信实测。P9/P10没有保留下来的自训checkpoint；工程复盘引用日志即可，不发明可加载文件。

### 视频完成状态不能用教材笔记抵扣

给LEC73另写“是否实际学习、学习日期、自己的三个收获、仍需回看的问题”。没有读到课堂内容时写未完成；不要填伪时间码。当前LEC71获奖方法、LEC72课堂逐节覆盖、LEC73讲者实际总结均不能由自主导读反推。

牛仔竞赛身份与公开条款已有证据，认证数据/规则接受、实际scorer、`image_id`与`id`以及像素xyxy仍未核。工程地图中应保留这一行，而不是绕认证下载、擅改COCO字段或用banana训练结果宣称完成牛仔比赛。

## 任务4路线：把“准备好了”变成可观察动作

你的清单每行写能力、证据、当前独立程度、下一次最小练习，不抄一个“全完成”列表。

1. **训练循环**：闭卷画出一次更新的顺序，说清为什么eval不等于禁用梯度、为什么恢复需要optimizer；对应本实验一次真实恢复记录。
2. **token/mask**：给一条带EOS/PAD的短序列手工写输入右移、标签和有效位置，再说明causal与padding布尔值是否与所用API一致。用旧短例即可，不另收集文本。
3. **Transformer**：从`(B,T,d)`追踪到每头再还原；解释LayerNorm只沿特征轴与前缀独立性的关系。区分P10编码器—解码器翻译与后续自回归语言建模。
4. **性能**：自行读一份旧CPU测量记录，说清warmup、重复次数、同步、样本/秒或token/秒分母、峰值内存口径。没有GPU就保留“未测”，不新增硬件采购门槛。
5. **数据评估**：指出训练/验证/test分离、train-only词表、重复文本/文档泄漏与数据许可。既报告聚合loss，也给固定错误样例；测试集不能兼任调参集。

数学随上述问题就地补：梯度链式法则、向量范数、softmax/logsumexp、矩阵维度、指数移动平均。论文路线不是本阶段验收，也不额外要求完整预训练。后续CS336的具体课程要求应另核，不能把这里的自主清单说成官方先修清单。

## 常见偏差与定位顺序

| 观察 | 先检查什么 | 不应怎样修饰结果 |
|---|---|---|
| 三组第一步loss不同 | 初值、第一批ID、dropout RNG和训练模式 | 仅凭同seed宣称已控制随机性 |
| CE下降但accuracy不升 | 置信度、类别分布、小样本及评估时点 | 把两个指标挑一个作为唯一胜负 |
| 尾批处loss跳动 | 实际batch大小、在线/评估量混用 | 删除尾批或改平均口径不说明 |
| 恢复下一批不同 | 保存排列、cursor、换轮边界 | 用新的batch继续却说数值可复现 |
| 下一批同但loss不同 | dropout RNG、buffer、train/eval、dtype | 重设seed代替恢复当前RNG状态 |
| loss和梯度同但参数不同 | LR、optimizer矩、step与参数绑定 | 只看预测类别没变就判通过 |
| 过一段恢复才偏离 | scheduler推进单位、下一轮shuffle RNG | 只展示恢复后的第一步 |
| GPU似乎很快 | 是否同步、预热、数据/验证是否计时 | 用CPU机制验证代替GPU实测 |

## 主agent实际观测：有限配对训练与磁盘恢复

以下是主agent在2026-11-14实际运行后保存的观测，不是worker执行、不是完整答案、也不代表四项个人任务全部完成。worker最初的“未运行数值”历史保留；此处单独整合新增证据。

### 运行条件

Python3.11.8、torch2.5.1，CPU单线程float32；CUDA设备0，MPS仅探测未运行。官方训练gzip的MD5重新核对；seed2021对60,000个原始ID生成一次固定随机排列，排列前5,000位置为验证候选、其余55,000位置为训练候选，分别取候选开头73/257个。这些是**排列位置，不是原IDX连续ID区间**。完整选中ID保留于证据JSON，未读官方测试集；预处理和同一数据张量在三组间一致。

新MLP为784→32→10，中间ReLU与Dropout0.1，Xavier初始化、零bias，共25,450参数。init2041、shuffle2042、dropout2043，三组加载同一初始参数，逐批顺序与随机策略配对。B64、尾批1、12轮、每组60更新；没有weight decay、裁剪、增强、AMP或多worker。

三组初始LR都为0.01；动量0.9，Adam使用betas=(0.9,0.999)、eps=1e-8。共同StepLR每完成20次更新乘0.5，每次先optimizer后scheduler。因此更新1–20用0.01、21–40用0.005、41–60用0.0025；第60次完成后状态中下一LR是0.00125，但没有执行第61步。**这是同数值LR的机制对照，没有逐算法调优，不是最优质量排名或统计显著性结论。**

### 实测曲线点

表中每格是“训练集评估CE / 验证CE”，均为固定checkpoint的评估量，保留全部每5更新采样点，四舍五入到四位小数；不是在线batch loss。表可横向滚动，未用示意图替代数据。

| 已完成更新 | SGD | 动量SGD | Adam |
|---|---|---|---|
| 0 | 2.3304 / 2.3175 | 2.3304 / 2.3175 | 2.3304 / 2.3175 |
| 5 | 2.2163 / 2.2250 | 2.0626 / 2.1151 | 1.3578 / 1.4678 |
| 10 | 2.2049 / 2.2493 | 1.8935 / 1.9556 | 1.2708 / 1.3285 |
| 15 | 2.0126 / 2.0837 | 1.5891 / 1.7923 | 1.2159 / 1.5061 |
| 20 | 1.9326 / 2.0309 | 1.5640 / 1.8682 | 0.9937 / 1.2407 |
| 25 | 1.9022 / 2.0068 | 1.3806 / 1.6358 | 0.9164 / 1.0727 |
| 30 | 1.8771 / 1.9882 | 1.2655 / 1.4724 | 0.8240 / 1.0015 |
| 35 | 1.8519 / 1.9723 | 1.1871 / 1.3988 | 0.7606 / 0.9674 |
| 40 | 1.8199 / 1.9296 | 1.1300 / 1.3487 | 0.6906 / 0.8980 |
| 45 | 1.8134 / 1.9285 | 1.1036 / 1.3172 | 0.6545 / 0.8314 |
| 50 | 1.7972 / 1.9194 | 1.0909 / 1.3118 | 0.6289 / 0.8033 |
| 55 | 1.7841 / 1.8998 | 1.1015 / 1.3334 | 0.6704 / 0.8892 |
| 60 | 1.7754 / 1.8956 | 1.0701 / 1.2645 | 0.5978 / 0.8032 |

| 末点（60更新） | 验证正确数 |
|---|---|
| SGD | 21/73 |
| 动量SGD | 43/73 |
| Adam | 49/73 |

初始正确数均为6/73。只在这份单seed小划分、固定预算与LR策略下，Adam末点CE较低且正确数较多；没有证明换模型、数据规模或合理调优后仍是这个顺序。Adam第55步和动量第20/55步的回升保留，不以“应当单调下降”改写日志。末点是预先固定的60步，不是从验证曲线挑最好点。

### 磁盘、新进程与状态一致性

三组分别在第23更新后保存：epoch=4（从0开始）、cursor=192，边界位于update、scheduler和梯度清零完成后。实际写盘、另起进程显式`weights_only=True`读取，再继续22步至45；与不中断路径逐项对照。

| 优化器 | 临时checkpoint字节数 | 22步对照 | 参数最大差 |
|---|---|---|---|
| SGD | 597,328 | batch ID、loss、梯度、LR完全相同 | 0 |
| 动量SGD | 700,610 | batch ID、loss、梯度、LR完全相同 | 0 |
| Adam | 803,474 | batch ID、loss、梯度、LR完全相同 | 0 |

模型、optimizer、scheduler、torch CPU RNG、独立shuffle RNG、当前排列、cursor、epoch与global_step均相同；跨越25/30/35/40更新处的换轮边界以及第40更新的LR调度边界。实际随机源仅为CPU dropout和独立shuffle Generator；Python/NumPy RNG未用于训练，故不宣称验证过其恢复。无AMP、梯度累积、多worker/预取或分布式状态。

这些字节数是完整状态包大小，不是纯模型参数内存，不能拿它们当算法内存开销的精确隔离测量。临时文件已经销毁；**有过真实磁盘证明，不等于现在保留了可复用checkpoint**。本结果不外推跨设备、跨版本或任意长度的恢复。

### 有意遗漏状态的反例

四项均从同一个本地Adam第23步checkpoint出发，继续至45；不是额外的模型质量竞赛。

| 故意遗漏 | 下一批相同？ | LR序列相同？ | 第45步参数最大差 |
|---|---|---|---|
| 整个optimizer状态 | 是 | 否 | 0.161723 |
| scheduler状态 | 是 | 否 | 0.007743 |
| torch CPU RNG状态 | 是 | 是 | 0.049921 |
| 采样游标恢复 | 否 | 是 | 0.106562 |

第一项同时丢失当前LR与Adam历史，不能声称只隔离了Adam矩。其余反例说明“装了权重”不足以继续相同训练轨迹；不能由其中一个反例反推所有模型都使用相同随机源。

### 合成机制与尚未执行项

主agent另核三优化器float64两步解析对照；大logits的稳定CE为0.3132616579、梯度有限，朴素指数路径非有限。这是合成稳定性证据，不是观察到上述真实Fashion训练发生爆炸；真实比较没有启用裁剪。

未执行：逐优化器LR搜索、多seed质量排名、完整Fashion测试评估、GPU/MPS或性能基准、所有学生实现/扩展、旧模型重训、课堂总结视频学习、历史竞赛认证/训练/提交。任务1/2的有限主验证与任务3/4的个人工程复盘分别记账。

## 引用与来源

- PyTorch 2.5：[优化器与调度调用顺序](https://docs.pytorch.org/docs/2.5/optim.html)、[SGD](https://docs.pytorch.org/docs/2.5/generated/torch.optim.SGD.html)、[Adam及state_dict参数映射](https://docs.pytorch.org/docs/2.5/generated/torch.optim.Adam.html)、[optimizer装载](https://docs.pytorch.org/docs/2.5/generated/torch.optim.Optimizer.load_state_dict.html)、[StepLR](https://docs.pytorch.org/docs/2.5/generated/torch.optim.lr_scheduler.StepLR.html)。实际审阅的API范围归档于本实验source-index，不声称逐行读过全部优化器源码。
- [可复现性](https://docs.pytorch.org/docs/2.5/notes/randomness.html)、[当前保存/加载教程](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)、[CrossEntropyLoss](https://docs.pytorch.org/docs/2.5/generated/torch.nn.CrossEntropyLoss.html)、[logsumexp](https://docs.pytorch.org/docs/2.5/generated/torch.logsumexp.html)：RNG、state_dict、logits/reduction及稳定性依据。当前教程与2.5版API分开标记。
- [Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist)：复用P2原数据身份与许可归档，P4划分合同；未重新发布数据或模型。
- [教材优化章](https://zh.d2l.ai/chapter_optimization/index.html)是原练习对照范围；本页推导为自主讲解，固定中文第二版源码提交不是2021全书快照，目录链接不证明课堂逐节覆盖。
- 新主数值原件：`sources/p11-shared/optimization-smoke.json`；旧运行复用范围、API审阅摘记及合同：`sources/p11-optimization-capstone/`。长摘要和样本ID留在JSON，不复制成手机不可换行段落。worker未执行任何数值/tests/build/lint/formatter，未提交；主验只支持上列范围。
