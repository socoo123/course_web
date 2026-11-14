---
title: "位置编码与长上下文：先对齐坐标，再谈外推"
lectureId: ext03
kind: "编者专题，非官方讲次"
sourceVersion: "RoFormer 2104.09864v5；Attention 1706.03762v7；A1 Spring2026 v26.0.3；L03讲义 @ de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e"
sourceManifest: "sources/p3-extensions/manifest-fragment.json"
readingScope: "按页底范围核对位置性质、实验长度与限制；论文唯一精读正文在lec03 materials，本页不重复推导。"
license: "RoFormer固定版CC BY-NC-ND 4.0，不公开翻译改编；本文为独立分析、实验设计与原创图。"
status: "独立标量坐标微例、原创SVG与未执行的模型实验设计；不代表官方作业实现、模型训练或长上下文能力验证。"
mediaStatus: "无独立官方录像，仅notes，不另建draft或materials。"
---

# 位置编码与长上下文：先对齐坐标，再谈外推

## 1. “支持4096”究竟是哪一层承诺

模型能够接收长度4096的张量，不等于训练见过4096的位置，更不等于能可靠使用相距4095个token的信息。讨论长上下文前，至少写下四个量：

| 量 | 具体含义 | 容易混淆的对象 |
| --- | --- | --- |
| 训练长度分布 | 训练样本有多长、长样本出现多少 | 只写一个最大长度 |
| 推理可见长度 | 本次预测实际可访问多少有效token | 分配的buffer容量、padding槽位 |
| 位置坐标范围 | 本次传入的位置ID及其最大值 | 当前张量序列轴长度 |
| 有效任务距离 | 必需证据距当前查询有多远 | 文档总长度 |

例如训练最大长度128，但几乎全是32以内的样本，与持续在128长度训练不是同一分布。推理时只有1个新增token，其位置ID仍可以是2048：**当前输入长度1，不表示它位于整段上下文的第0位。**

RoPE的旋转构造、配对维度与内积性质统一见[L03材料精读](#/c/stanford-cs336-2026/lec/lec03?v=materials)；现代架构取舍见[L03笔记](#/c/stanford-cs336-2026/lec/lec03?v=notes)。本页只把数学性质变成坐标契约、检查方法和可证伪实验，不再完整推导RoPE，也不进入缓存调度、分页或kernel等系统专题。

## 2. 三种坐标，不能因为都叫index就混用

一个token至少可能有三种编号：

1. **张量槽位**：它在当前输入数组里的下标。
2. **逻辑位置**：位置编码应当使用的序列坐标。
3. **缓存槽位**：某个旧状态现在存在哪里。

无padding、从头整段计算时，三者可能恰巧相等；分块、padding或增量计算后通常不再相等。实现规范必须以逻辑位置为准，而不是凭当前shape猜位置。

![同一个新增token的局部槽位与逻辑位置](assets/position-index-contract.svg)

*图：编者自拟5-token情境。已处理位置0–3后，新token局部槽位是0、逻辑位置是4。图仅解释正确性，不展示或实现缓存系统；不来自论文原图。*

### 2.1 一个offset错误足以伪装成长上下文失败

设旧key的逻辑位置为 $n=1$，新query为 $m=4$。沿用材料页的约定，位置项应依赖 $n-m=-3$；如果把新query误当成局部位置0，就变成 $1-0=1$。

对一个固定角频率 $\omega$，相位差只是：

$$
\begin{aligned}
\Delta\phi&=(n-m)\omega,\\
(n+c)-(m+c)&=n-m.
\end{aligned}
$$

第二行说明**共同平移**不会改变相对位移；只重置query而保留旧key的位置不是共同平移。这是坐标一致性结论，不是长距离任务能力结论。

下面仅用标量计算三个相位差；没有向量旋转、attention、模型或作业模块实现：

```python
import math

omega = 0.2
cases = [(4, 1), (104, 101), (0, 1)]  # (query位置, key位置)
for query_pos, key_pos in cases:
    delta = (key_pos - query_pos) * omega
    print(round(delta, 6), round(math.cos(delta), 6))
```

解析预期依次约为 `-0.6 0.825336`、`-0.6 0.825336`、`0.2 0.980067`。余弦只是观察相位的标量探针，**不是完整attention得分或注意力权重**。前两项相同只能支持共同平移一致性，不能支持模型外推成功。

### 2.2 缓存必须携带什么语义

若缓存保存的是已按原位置旋转的key，就不应在每次追加时再对这些key旋转一次；若保存未旋转key，则读取时必须仍能恢复其正确位置。两种契约都可被讨论，不能混用。

- 新块含 $C$ 个token、前面已有 $P$ 个位置时，逻辑位置通常是 $P$ 到 $P+C-1$，不是每块重新从0开始。
- 有padding的batch应逐样本维护有效位置，不能直接把张量总宽当作所有样本的已处理长度。
- 旧状态若被移到别的物理槽位，逻辑位置不因此改变。若要统一重标坐标，所有相关key/query表示必须一致，不能只改一个计数变量。
- 丢掉旧上下文会改变模型能看到的信息。即使位置处理完全正确，也不能要求它与保留完整历史时的输出一样；这不是单纯的“缓存位置修复”。

这些是语义检查项，不是缓存实现教程；也不表示官方A1要求实现完整增量缓存。

## 3. padding、分块与mask：长度以外还有条件

### padding不是新的文本

给相同文本分别做左padding和右padding，在确定性计算、相同有效token位置、相同可见性和正确输出对齐的条件下，有效token的预测应一致到合理浮点容差。需要逐项问：

- padding是否被排除在key可见集合和有效loss之外？
- 位置ID按有效token编号，还是包含padding的张量槽位？约定有没有跨路径变化？
- 最后一个有效token在数组哪一列？“取最后一列”未必是取文本末尾。
- 有没有一行全被mask，从而制造无定义的softmax归一化？该问题见[ext01](#/c/stanford-cs336-2026/lec/ext01?v=notes)，不能拿位置编码背锅。

不要把“RoPE对共同平移不敏感”用来免除这些检查。只有纯相对位置路径、相同内容与可见图等前提满足时，共同平移结论才足够；其他绝对位置特征、边界处理或错误mask都可能破坏条件。

### 分块处理与切断上下文不是同一实验

对同一条序列，仅改变处理分块而保留所需历史，理论上应与整段因果计算对齐。若每个块都被当成独立样本、重新置零位置且禁止跨块访问，那已经改变了模型条件分布，不能再把差异当作缓存实现错误。

同理，将多篇文档打包到一个张量里，是否允许跨文档attention、是否重置位置、文档边界怎样计loss，属于数据/模型契约。位置重置本身不会自动阻止跨文档信息泄漏；mask与边界约定仍需明确。训练样本与目标对齐见[bridge06](#/c/stanford-cs336-2026/lec/bridge06?v=notes)。

## 4. 四层检查：先证明“同一计算”，再观察“新长度”

不要用一个loss数字同时证明数学、工程和任务能力。按成本由低到高分层：

| 层次 | 固定什么、比较什么 | 能证明到哪里 |
| --- | --- | --- |
| 代数 | 固定内容向量与频率；检查旋转保范数、共同平移的内积 | 局部位置变换的一致性，不涉及学习 |
| 索引 | 固定token；比较不同offset、块边界、padding下的逻辑位置与可见集合 | 坐标/mask契约是否自洽 |
| 模型 | 固定权重，关闭dropout；整段因果前向与逐步/分块计算比较对应有效位置logits | 两条计算路径是否等价到容差 |
| 泛化 | 固定已通过检查的模型与评测协议，改变未训练长度和距离 | 此模型在此分布与任务上的经验能力 |

模型层检查须使用同样的前缀、位置、mask、dtype及参数；不同浮点归约顺序可能产生末位差异，不能要求所有后端逐位相同，也不能把足以改变任务结果的大差异一概叫浮点误差。若失败只出现在第二块第一个token，优先查offset、因果mask对齐和旧key是否重复旋转，而不是立刻调RoPE频率。

检查逻辑上允许的**完整前缀**即可；若比较对象删去了历史或改变了文档边界，不再具备等价前提。通过这些检查也只说明计算实现与声明相符，没有证明长上下文泛化。

## 5. 为什么“相对位置”不自动等于“任意外推”

### 5.1 公式能定义的位置，不等于训练覆盖的位置

学习式绝对位置表常有显式索引上限；固定正弦或RoPE的公式可以继续计算更大位置，但“有定义”只是代数性质。训练时模型仍只在有限的相位组合、相对距离、竞争key数量和内容分布上学习过。

对RoPE而言，即使单个旋转保持范数，attention中每个query需要区分的候选key仍会随长度增加。相同的一个logit，放进更大的softmax归一化集合，得到的权重也未必相同。因此“向量没有变大”不能推出“整网长期稳定且准确”。

### 5.2 长程衰减不是每一对token的单调定律

RoFormer讨论多频率旋转和相应上界结构，并观察长程衰减趋势。这不表示任意内容向量的每个内积、绝对内积或softmax权重都随距离逐点单调下降。

**多频率结构的趋势或上界分析，不是对所有向量、所有距离的单调保证。** 具体反例统一见[L03材料页§8.1](#/c/stanford-cs336-2026/lec/lec03?v=materials)，这里直接进入任务含义与评测方法。

而且“远处关联被压低”与“远处证据仍能被正确提取”本来是不同目标。长距离任务可能恰好需要保留一个远端关键信息，不能用衰减性质代替任务验证。

### 5.3 论文实验还要问：是否已经训练过更长序列

固定RoFormer v5的中文实验采用过最长1536的分阶段预训练，再比较512与1024截断的下游任务。这不是“只在512训练、不做适配、直接零样本外推到1024”的证据；预训练阶段、任务和长度必须一并说明。论文§4.5.5也明确保留了为何更快收敛、为何长文本表现更好的解释限制。

本页不重述论文所有实验结果，完整核心材料仍回到[L03材料页](#/c/stanford-cs336-2026/lec/lec03?v=materials)。同样，Attention论文§3.5对正弦编码可外推使用的是动机性表述，不能扩写成任意长度的保证。

## 6. 一个能区分“长”与“远”的独立实验设计

以下是**未执行的编者实验协议**，不要求下载大模型、训练语料或购买GPU，不是官方A1训练任务或可提交实现。若开展训练，须自行编写代码并明确其与课程AI政策的边界；先跑上节无训练的一致性检查更有信息价值。

### 6.1 先把问题变成可测假设

假设：在坐标与mask正确时，一份只在长度不超过128上训练的微型模型，能否读取更长输入中唯一的键值关联？

可用自拟的离散键值查询任务：若干互不重复的key各对应一个随机value，末尾给出一个key，要求返回其对应value；填充项不重复目标key，不泄露答案。训练和验证的键值组合及随机种子分开，保持value分布平衡，防止只靠记忆某个key的常见答案。token化和分隔符规则固定，长度用**实际token数**而非字符数。

- 训练长度分布可明确为64和128，最大128；必须公布两者比例，而非只报最大值。
- 推理长度取64、128、256、512；前两档是域内对照，后两档才测试长度外推。
- 在每个长度下，分别把目标证据放在近、中、远位置；记录证据到query的真实token距离。
- 最初固定所有模型参数和位置频率；不在看到测试集成绩后逐档调参，否则不是同一个零样本外推实验。

### 6.2 两条轴要拆开

| 对照 | 保持不变 | 改变 | 主要排查 |
| --- | --- | --- | --- |
| 长度轴 | 目标证据距query固定 | 在更早处增加无关内容 | 候选数量、干扰内容与总长度效应 |
| 距离轴 | 总长度固定 | 移动目标证据，其他填充同步调整 | 真正的远程关联能力 |
| 坐标轴 | 内容、可见图与相对距离固定 | 所有逻辑位置共同平移 | 索引一致性与大坐标数值问题 |
| 路径轴 | 模型与完整前缀固定 | 整段与分块/增量处理 | 正确性，不是泛化 |

增加无关内容仍会改变模型输入分布，因此第一行不是“纯代数不变量”；它只是让目标距离不再与长度完全混在一起。频率组合也可能产生周期性表现，不能只挑一个恰好成功的长度。

### 6.3 什么结果值得报告

1. **主任务指标**：按长度×距离分桶的精确答案准确率、样本数、重复seed离散度。不要只报告混合平均值；答案位置固定也要防止“只预测最后一项”的捷径。
2. **必要对照**：确认证据确实唯一且可见；用按定义查表的任务oracle核查数据；删除目标证据或打乱对应关系，看任务是否仍可被捷径解决。oracle只是任务定义的正确性参照，不是模型表现。
3. **域内指标**：检查64/128长度的能力，避免把从未学会任务的模型称为“外推失败”。若做语言建模，再报告相同token化与计分区间下的验证NLL；NLL不能替代上述检索任务准确率。
4. **资源与预算**：记录训练有效token、更新次数、验证开销、实测时间和峰值内存的口径。改变序列长度时，同token预算也未必同attention计算量；比较配方的方法见[ext02](#/c/stanford-cs336-2026/lec/ext02?v=notes)，基础账本见[L02](#/c/stanford-cs336-2026/lec/lec02?v=notes)。
5. **结论边界**：合成键值成功说明该分布下的查询能力，不等于长文理解、复杂推理或所有自然语言任务成功；单次失败也不证明某种位置编码原理不可能外推。

## 7. 若考虑改变位置尺度，先说明改变了哪个问题

在不展开额外研究方法的前提下，仍可区分两类普通操作：

- **不改编码，直接给更大位置和距离**：保持原模型计算规则，测试未见范围；这是直接外推评测。
- **把逻辑位置压缩后再编码**：例如把坐标按比例缩小，改变了相位差和相邻token的分辨尺度，不再是原规则不变的外推。它可能让某些相位落回熟悉范围，也可能降低邻近位置的区分，必须重新评测。

若进一步用长样本训练或微调，则训练分布已经改变，应称长度适配，而不是“无训练外推”。如果采用依赖当前长度的频率规则，还须解释旧缓存表示与新规则是否兼容；不能在同一个序列中途换规则却不处理旧状态。

本页不列未实际阅读的长上下文论文名，也不给所谓万能缩放参数。每项新方案都应重新过一致性、域内能力和长距离任务三关，再谈收益。

## 8. 自测

<details>
<summary>1. 输入shape的序列轴长为1，位置ID一定为0吗？</summary>

不一定。若前面已有2048个逻辑位置，该新增token可位于2048。当前张量槽位0、逻辑位置2048、缓存存储槽位是三个不同概念。

</details>

<details>
<summary>2. 所有query/key位置同时加100与只把新增query重置为0，为什么不能混为一谈？</summary>

共同平移保持相对位移；只重置query改变它与所有旧key的位移。只有在其他内容、mask和位置路径也一致时，前者才提供等价性检查。

</details>

<details>
<summary>3. 保范数、相对旋转、长程衰减三件事，哪一件能单独保证任意长上下文任务成功？</summary>

都不能。它们约束局部表示或分析结构，不保证训练覆盖、候选竞争、数值精度和任务所需的远端信息利用；单个内容内积还可能随距离振荡。

</details>

<details>
<summary>4. 训练阶段最长1536，下游用1024，能说证明了“只在512训练后直接外推到1024”吗？</summary>

不能。训练历史包含更长序列；还需区分任务训练、预训练阶段、微调与推理设置。长度数字脱离其阶段就失去证据含义。

</details>

<details>
<summary>5. 分块与整段计算不一致时，为何不应先调整RoPE频率？</summary>

先确认它们是否真的计算同一前缀、mask和逻辑位置，检查offset、重复旋转、padding与dropout。改频率会改变模型，可能掩盖原来的坐标错误；一致性通过后才能讨论泛化。

</details>

## 来源、阅读范围与边界

- Su、Lu、Pan、Murtadha、Wen、Liu，*RoFormer: Enhanced Transformer with Rotary Position Embedding*，[arXiv:2104.09864v5](https://arxiv.org/abs/2104.09864v5)。本片实际读取提取文本248–377行（§3.2.2–3.3及邻接内容）、507–556行（§3.4.3和实验开头）、590–609行（§4.2）、697–790行（§4.5及结论开头）。核心与选读边界按reading-map：§3.4.3、§4.2、§4.5是编者选读；本文按实验问题局部核对，不新增第二份论文精读正文。没有逐图视觉审校或全文阅读声明。
- 该固定RoFormer版本采用[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)，不允许据此共享翻译改编。本页独立讨论概念、批评过强推断并设计新例子，不沿原文章节逐段译述，不搬原图、原表或实验曲线。论文完整核心讲解只在[L03 materials](#/c/stanford-cs336-2026/lec/lec03?v=materials)。
- Vaswani等，*Attention Is All You Need*，[arXiv:1706.03762v7](https://arxiv.org/abs/1706.03762v7)，实际读§3.5、§4、§5.1–5.3及邻接文本；本页仅使用§3.5的固定正弦位置动机，未把它解释成外推定理。arXiv非独占分发许可不是公众全文翻译授权。
- 固定[L03讲义](https://raw.githubusercontent.com/stanford-cs336/lectures/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e/lecture_03.pdf)：本片只读提取文本330–420行的位置编码/RoPE部分；提交晚于学期，未与录像核音对齐，不能按其内容编造视频时间。讲义开放全文翻译许可未确认。
- CS336 Staff，[A1固定讲义](https://raw.githubusercontent.com/stanford-cs336/assignment1-basics/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)，Spring2026 v26.0.3：实际读§3.4.3至§3.4.4开头，核对Q/K位置、显式 `token_positions` 契约。本页不提供RoPE、attention或缓存实现；缓存offset讨论是编者正确性分析，不冒充官方新增任务。作业职责见[A1指导](#/c/stanford-cs336-2026/lab/a1-basics?v=guide)。
- 上述标量微例、SVG和实验设计为编者原创；没有执行模型训练或报告任务分数。官方AI政策的概念/API辅助与禁止AI代写作业边界见[课程资料](#/c/stanford-cs336-2026)。完整阅读、原获取时间与哈希登记于 `sources/p3-extensions/manifest-fragment.json`；全文证据仅本地留存。

### A1第一方文档许可保留

本页只对A1位置接口作概念定位，缓存及实验方法为独立补充，不代表Stanford官方。第一方文档MIT不延伸到所引论文、第三方图像、数据或服务。

Copyright 2025 Stanford University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
