---
title: "Attention资源账本：二次的是哪一笔？"
lectureId: ext04
kind: "编者拓展，非官方讲次"
sourceVersion: "FlashAttention arXiv:2205.14135v2；FlashAttention-2 arXiv:2307.08691v1；PyTorch 2.9文档"
sourceManifest: "sources/p4-attention-profiling/manifest-fragment.json"
readingScope: "固定论文选读与官方API文档；本页为独立资源推导，不复述论文实验或提供作业实现。"
status: "全部数值是给定假设的算术例，不是GPU测量；未执行A2。"
---

# Attention资源账本：二次的是哪一笔？

## 1. 先把“Attention太贵”拆成四个问题

1. **容量**：哪些独立storage同时存活，能不能装进显存？
2. **计算**：做了多少乘加，重算又增加多少？
3. **搬运**：哪些数据在HBM与片上存储之间来回走？
4. **时间**：上述工作在目标硬件、形状和调度下实际花多久？

四者相关，却不能互相代替。完整的 $S\times S$ 注意力矩阵可以**不落到HBM**，但全局精确attention仍须处理所有允许的query–key配对。反过来，KV缓存只随历史长度线性增长，也不表示每一步都不必读取历史。

本页沿用[L02的乘加计数](#/c/stanford-cs336-2026/lec/lec02?v=notes)和[bridge08的字节、存活峰值与实验口径](#/c/stanford-cs336-2026/lec/bridge08?v=notes)，不重讲分配器。MHA/GQA/MQA及历史表示回到[L04](#/c/stanford-cs336-2026/lec/lec04?v=notes)。这里新增的是一张可逐项审计的attention账单；论文叙事、算法逐读和性能证据统一放在[L06材料](#/c/stanford-cs336-2026/lec/lec06?v=materials)。

## 2. 固定形状，才有账本

先讨论一个层的attention核心，不含投影、位置编码、残差或FFN。记：

| 符号 | 含义 |
| --- | --- |
| $B$ | batch大小 |
| $H_q,H_{kv}$ | query头数、物理保存的KV头数 |
| $S_q,S_k$ | 本次query长度、可访问key长度 |
| $d_k,d_v$ | 每头key/query维度、value维度 |
| $b_X$ | 张量 $X$ 每元素字节数 |

采用头轴在长度轴之前的逻辑形状：

$$
\begin{aligned}
Q&:(B,H_q,S_q,d_k),\\
K&:(B,H_{kv},S_k,d_k),\\
V&:(B,H_{kv},S_k,d_v),\\
O&:(B,H_q,S_q,d_v).
\end{aligned}
$$

对query头 $h$，由 $g(h)$ 指向它使用的KV头。单头计算是：

$$
\begin{aligned}
A_{ij}&=\frac{q_i^\mathsf T k_j}{\sqrt{d_k}}+M_{ij},\\
P_{ij}&=\operatorname{softmax}_{j}(A_{ij}),\\
o_i&=\sum_j P_{ij}v_j.
\end{aligned}
$$

这里用 $A$ 表示score，避免与序列长度符号混淆。softmax沿**key轴**；每个query行分别归一化。分组共享只改变 $g(h)$ 和物理KV存储，不能把 $H_q$ 擅自换成 $H_{kv}$ 来数全部score。

## 3. 三张不能混在一起的表

### 3.1 逻辑载荷表：某个张量若真的存下来，要多少字节？

| 对象 | 独立保存时的逻辑载荷 |
| --- | --- |
| $Q$ | $BH_qS_qd_kb_Q$ |
| $K$ | $BH_{kv}S_kd_kb_K$ |
| $V$ | $BH_{kv}S_kd_vb_V$ |
| $O$ | $BH_qS_qd_vb_O$ |
| 完整score $A$ | $BH_qS_qS_kb_A$ |
| 完整概率 $P$ | $BH_qS_qS_kb_P$ |
| 每query行一个logsumexp | $BH_qS_qb_{\rm LSE}$ |

“score有这些元素”是逻辑计算描述；“分配了这样大的张量”是实现事实，二者不能画等号。即使接口中写出了矩阵符号，融合kernel也可能只保留一个小tile。

还要额外问四件事：

- **mask是否物化？** 因果条件可由索引判断，不一定有完整布尔矩阵；broadcast view也不等于分配每个batch和head的副本。
- **是否复制KV？** GQA可以按索引复用；若先显式重复到 $H_q$ 个头，临时副本必须入账，不能继续声称实际分配只按 $H_{kv}$ 计算。
- **精度是否一致？** BF16输入不保证score、softmax归约和输出都为BF16；累加器通常需要单独考虑，不能从输入dtype推断一切。
- **反向保存什么？** eager分解、融合attention和重算策略保存的集合不同。不能只看数学式猜autograd的实际存活对象。

### 3.2 同时存活表：张量名之和不是峰值

假设一个**特意简化的分解前向**：$Q,K,V$ 已在显存；score单独分配，softmax另分配 $P$；计算 $O$ 时 $A$ 仍被某个引用持有。此时六份对象可同时存在。若实现及时释放 $A$，或者原地/融合处理，峰值便不同。

因此下面的和只能用于这个声明过的存活条件：

$$
\begin{aligned}
M_{\rm shown}&=M_Q+M_K+M_V\\
&\quad+M_O+M_A+M_P.
\end{aligned}
$$

它不含参数、梯度、其他层的激活、运行时、allocator预留空间或库workspace。它既不是实测峰值，也不是所有attention实现的下界。

### 3.3 传输表：一份256 MiB张量可以不止搬256 MiB

在“score写出→softmax读入→概率写出→乘value读入”的分解模型中，若两份矩阵都必须经过所讨论的慢存储层，至少出现：

$$
Q_{A,P}=2M_A+2M_P.
$$

这里的 $Q_{A,P}$ 是**这个理想化分解的读写流量**，不是Q张量。缓存命中、重复加载、实现融合、内存事务粒度都会改变实际HBM字节；不能拿分配量直接当硬件计数器结果。FlashAttention主要避免这两张大矩阵的完整HBM物化和往返，不保证输入永远只读一次。片上tile、寄存器压力与调度见[L06](#/c/stanford-cs336-2026/lec/lec06?v=notes)。

## 4. 原创算例：16 MiB的输入输出，如何遇上512 MiB的中间矩阵？

取单层MHA：

$$
\begin{aligned}
B&=2,\qquad H_q=H_{kv}=8,\\
S_q&=S_k=2048.
\end{aligned}
$$

$$
d_k=d_v=64.
$$

设 $Q,K,V,O$ 均为BF16；**另外明确假设**完整score和概率都以FP32存储。这是为看清比例而设的账本，不是宣称某个PyTorch后端必然如此。

| 项目 | 元素数或计算式 | 逻辑字节换算 |
| --- | --- | --- |
| 每份 $Q/K/V/O$ | $2\times8\times2048\times64$ | 4 MiB |
| 四份合计 | $4\times4$ MiB | 16 MiB |
| 每份 $A/P$ | $2\times8\times2048^2$ 个FP32 | 256 MiB |
| 两份大矩阵 | $2\times256$ MiB | 512 MiB |
| 每行一个FP32 LSE | $2\times8\times2048$ 个FP32 | 128 KiB，即0.125 MiB |

在上一节声明的全部同时存活条件下，小计为 **528 MiB**。若输入输出不变而 $A,P$ 改为BF16，两份大矩阵共256 MiB，小计272 MiB；**仅改存储dtype不等于证明数值误差可接受**。

若序列长度翻倍到4096，其余不变：

- $Q,K,V,O$ 合计由16变为32 MiB：乘2。
- 每份FP32大矩阵由256 MiB变为1 GiB：乘4。
- 两份大矩阵与四份输入输出合计为2080 MiB。
- LSE由128变为256 KiB，仍按query行数增长。

这说明为什么优化中间量往往比压缩一个小常数项更有价值。但不能把“去掉512 MiB中间量”报告成“整个训练进程只剩16.125 MiB”：还有没列出的模型状态、保存集合、其他层和临时工作区。

## 5. FLOPs：内存省掉了，配对工作未必省掉

按一个乘法加一个加法记2 FLOPs，只计主导矩阵乘。先考虑无mask或完整稠密求值：

$$
\begin{aligned}
F_{QK^\mathsf T}&\approx2BH_qS_qS_kd_k,\\
F_{PV}&\approx2BH_qS_qS_kd_v.
\end{aligned}
$$

于是：

$$
F_{\rm core,fwd}\approx
2BH_qS_qS_k(d_k+d_v).
$$

softmax的比较、指数、归约、除法，以及scale和mask处理另列；这些操作的硬件吞吐不能直接用Tensor Core峰值替代。这里的近似是**逻辑乘加主项**，不是精确指令数。

上一节中 $d_k=d_v=64$，得到：

$$
\begin{aligned}
F_{\rm core,fwd}
&\approx4\times2\times8\times2048^2\times64\\
&=17{,}179{,}869{,}184\ \mathrm{FLOPs}.
\end{aligned}
$$

即约17.18 GFLOPs，而不是17.18 GFLOP/s。它没有任何计时分母。

### 因果mask的两种“减半”

同长度、自注意、包含对角线时，每头允许的配对数是：

$$
E=\sum_{i=1}^{S}i=\frac{S(S+1)}2.
$$

若求值机制确实跳过所有不允许的配对，主项可以用 $E$ 替代 $S^2$。上述例子为约8.594 GFLOPs。有限长度下是 $S(S+1)/2$，并非精确 $S^2/2$。

但“先算完整矩阵，再把上三角mask掉”的实现并没有省去这些矩阵乘。块级跳过也可能保留对角tile内的额外工作。报告必须分清：

1. 模型允许的有用配对数；
2. 按tile取整后实际处理的位置；
3. 硬件实际执行的指令工作。

三者选一个稳定口径，不要为了抬高吞吐分子而临时换算。

### 前向、普通反向和重算反向

若 $Q,K,V$ 都求梯度，保存 $P$ 的普通反向有四个矩阵乘主项：$P^\mathsf T G$、$GV^\mathsf T$、$dA K$、$dA^\mathsf T Q$。因此：

$$
F_{\rm core,bwd}\approx
4BH_qS_qS_k(d_k+d_v).
$$

反向若不保存 $P$，而从 $Q,K$ 重算score，再恢复概率，额外增加：

$$
F_{\rm remat,QK}\approx2BH_qS_qS_kd_k,
$$

以及softmax相关工作。对 $d_k=d_v=d$，前向、普通前后向合计、含一次score重算的前后向合计分别是：

$$
\begin{aligned}
F_{\rm fwd}&\approx4BH_qS_qS_kd,\\
F_{\rm fwd+bwd}&\approx12BH_qS_qS_kd,\\
F_{\rm with\ remat}&\approx14BH_qS_qS_kd.
\end{aligned}
$$

这是给定计算路径的主项账本，不是所有内核精确操作数。**多做乘加却少花时间并不矛盾**：若省下的搬运足够大，墙钟时间仍可能降低；是否降低必须测，不能由FLOPs或论文标题保证。反向数学见[ext05](#/c/stanford-cs336-2026/lec/ext05?v=notes)。

## 6. 把投影放回来：为什么参数估算会漏掉长序列项？

以MHA、$D=Hd$、$d_k=d_v=d$ 为例，四个无偏置投影是 $Q,K,V$ 投影和输出投影。每个有 $D^2$ 个权重，每个前向约 $2BSD^2$ FLOPs：

$$
F_{\rm projections}\approx8BSD^2.
$$

非因果attention核心为：

$$
F_{\rm core}\approx4BS^2D.
$$

所以两者之比是：

$$
\frac{F_{\rm core}}{F_{\rm projections}}
\approx\frac{S}{2D}.
$$

当本例 $D=512,S=2048$ 时，核心的矩阵乘主项是四个投影的2倍。投影约8.59 GFLOPs，核心约17.18 GFLOPs；尚未加入FFN和其他算子。

这一比值只在上述MHA、完整稠密前向口径下成立。GQA的KV投影宽度较小，因果跳过改变核心系数，FFN还可能占据重要份额。它的用途是提醒：**仅按参数量乘token数的粗估无法自动包含所有 $S^2$ 交互**，不是给全网设统一“attention占比”。

## 7. KV缓存、prefill与decode：名字里有attention，不代表同一账本

[L04](#/c/stanford-cs336-2026/lec/lec04?v=notes)已经说明共享KV与改变历史表示的区别。这里仅在同一张表中对齐资源口径。

| 阶段/对象 | 当前query长度 | 关键账项 |
| --- | --- | --- |
| 训练或整段prefill | 通常 $S_q=S_k=S$ | 核心配对主项随 $S^2$ 增长；是否保存反向激活另看模式 |
| 单token decode | $S_q=1,S_k=T$ | 当前核心主项随历史长度 $T$ 增长 |
| KV缓存 | 不是score矩阵 | 保存历史 $K,V$，供未来query读取 |

若一层缓存key/value的dtype相同、每元素 $b$ byte，则：

$$
M_{\rm KV,layer}
=BH_{kv}T(d_k+d_v)b.
$$

若每层配置相同，$L$ 层缓存乘 $L$；分页、预分配空槽、元数据、量化scale和对齐另算。这是缓存数据载荷，不是训练激活总量。

用 $B=2,H_q=8,T=2048,d_k=d_v=64,b=2$：MHA每层KV为8 MiB；改为 $H_{kv}=2$ 时为2 MiB。与此同时query仍有8个头，每个仍访问2048个key，核心逻辑配对数没有随KV头数缩为四分之一。实际读取能否复用，仍看kernel。

单token那一步对 $T$ 是线性的；从空历史逐token生成到长度 $T$，如果每步都访问已有全部历史，则累计配对数含 $1+2+\cdots+T$，仍是二次量级。不要把**每步**与**全段累计**的复杂度混写。

## 8. FlashAttention到底改了什么？

![注意力的逻辑配对、物化和缓存分账](assets/attention-ledger.svg)

*编者原创机制图；方块不是实际显存占比，也不是某次profiler截图。*

- **保持**允许位置上的softmax attention数学定义，不靠删掉softmax或低秩近似换答案。
- **改变**中间量驻留方式：块内score和概率用完即消费，不把完整二次矩阵保存在HBM里。
- **保留**行级归一化信息与必要输入输出；反向按需重建局部概率。
- **不承诺**全局精确attention计算复杂度变成线性、消除KV缓存、或所有输入形状都更快。

“exact”指没有引入那类算法近似，不表示不同归约顺序在浮点下逐bit相同。若用户要求把所有head的完整attention权重作为返回结果，输出本身就有 $BH_qS_qS_k$ 个元素；省去这份输出的前提已经被接口改变了。

从资源账本走向测量，继续看[ext06：GPU性能分析方法](#/c/stanford-cs336-2026/lec/ext06?v=notes)。从“能不存概率吗”走向证明，继续看[ext05：逐行不变量](#/c/stanford-cs336-2026/lec/ext05?v=notes)。

## 9. 自测与答案

<details>
<summary>1. 序列翻倍，为什么KV缓存乘2而完整score乘4？</summary>

固定其他维度，缓存按历史位置保存向量，是 $T(d_k+d_v)$；完整自注意score枚举query和key两个长度轴，是 $S^2$。两者不是同一个张量。单token decode的score只有一行，也不应套整段 $S\times S$ 分配量。

</details>

<details>
<summary>2. BF16输入能否推出score只占128 MiB？</summary>

不能。还需知道score是否物化以及它的存储dtype。本例若真的物化BF16 score，是128 MiB；若FP32，是256 MiB；融合实现可能根本没有这份完整分配。

</details>

<details>
<summary>3. 把上三角置为负无穷，FLOPs就一定减半吗？</summary>

不一定。计算完整矩阵后mask并未省掉被遮位置的乘加。只有跳过工作才改变执行账本；对角tile和padding还可能产生额外工作。

</details>

<details>
<summary>4. 反向重算增加FLOPs，怎么可能更快？</summary>

FLOPs不是秒数。如果减少了慢存储往返，额外计算可能比被省掉的搬运更便宜。这个解释给出机制，不给无条件性能保证；仍需一致测量边界和实际证据。

</details>

<details>
<summary>5. GQA把KV头数从8改到2，什么可按四分之一算？</summary>

固定其他条件，物理KV缓存载荷和对应KV投影输出载荷可按四分之一计；query头数、完整score逻辑元素数、每个query对全部历史的配对工作不能照搬这个比例。若实现显式复制KV，还须把副本另外入账。

</details>

<details>
<summary>6. “融合attention使用线性内存”能直接写成“整个训练线性内存”吗？</summary>

不能。先说明对哪个变量线性、包括哪些输入输出和辅助状态。其他层、参数、优化器、保存的激活、要求返回的attention权重以及实现workspace都可能改变总账本。

</details>

## 来源、版本与边界

- [FlashAttention v2](https://arxiv.org/pdf/2205.14135v2)：§2.2、§3.1及Theorem 1；Appendix B.1–B.2，B.3开头与B.4的重算说明。只用于核对标准物化路径、线性辅助状态与反向重算机制。
- [FlashAttention-2 v1](https://arxiv.org/pdf/2307.08691v1)：§2.2–2.3、§3.1选读，及MQA/GQA段落。原版可疑公式不照抄；来源勘误、算法完整逐读和实验结论唯一归属[L06材料](#/c/stanford-cs336-2026/lec/lec06?v=materials)。
- [PyTorch 2.9 CUDA semantics](https://docs.pytorch.org/docs/2.9/notes/cuda.html)：Memory management开头，用于区分载荷、allocated与reserved；[Numerical accuracy](https://docs.pytorch.org/docs/2.9/notes/numerical_accuracy.html)开头，用于浮点非逐bit等价的限制。文档版本不等于课程依赖版本。
- 本页表格、算例、资源拆分与SVG为独立教学组织，不是官方讲次或论文全文翻译。论文开放全文翻译授权未确认，不发布本地原件或转载论文图。
- [公共资料与AI政策](#/c/stanford-cs336-2026)规定作业及排行榜实现由学生手写。本页没有A2实现；[A2概念指导](#/c/stanford-cs336-2026/lab/a2-systems?v=guide)另页承接任务。所有算例是条件计算，没有GPU延迟、吞吐或显存实测结论。精确实际阅读范围、完整哈希与未做事项见来源分片。
