---
title: 不改变注意力，改变数据的旅行：FlashAttention 与 FlashAttention-2 精读
source: FlashAttention 指定核心节与两段证明选读；FlashAttention-2 指定核心节、背景及讨论；固定2026 A2的阅读推荐与相关任务段落。
source_version: arXiv 2205.14135v2；arXiv 2307.08691v1
license: 自主中文问题组织、数学分析与评论，不是论文译文或逐段替代；原文署名、许可及勘误见页底。
status: 指定核心范围已读；重要算法页与测量口径已视觉核对；非两篇全文精读，未复现实验。
---

# 不改变注意力，改变数据的旅行

## 1. 两篇论文分别回答什么问题？

**FlashAttention 的问题**：能否仍然计算同一个精确 attention，却不把巨大的分数矩阵、概率矩阵反复搬进搬出显存？

**FlashAttention-2 的问题**：已经减少了显存 IO，为什么计算单元仍然没有充分忙起来？能否进一步减少昂贵的非矩阵乘工作，并改善线程块和 warp 的分工？

这不是从“二次复杂度算法”变成“线性时间算法”的故事，而是从单一 FLOP 账本走向**运算、存储、通信、并行度共同约束**的故事。本页是这两篇论文的唯一精读正文。

- softmax 从零推导、小数值例子及反向不变量，见[FlashAttention 数学专题](#/c/stanford-cs336-2026/lec/ext05?v=notes)。本页只保留理解论文算法所需的不变量，不重做逐步算例。
- 具体张量的容量/FLOP 账本见[Attention 资源专题](#/c/stanford-cs336-2026/lec/ext04?v=notes)；GPU 编程模型见[L06](#/c/stanford-cs336-2026/lec/lec06?v=notes)；如何采集可靠证据见[性能分析专题](#/c/stanford-cs336-2026/lec/ext06?v=notes)。
- [A2 指导](#/c/stanford-cs336-2026/lab/a2-systems?v=guide)负责作业接口、调试顺序和硬件边界，本页不提供可提交实现。

### 三种“要读”不能混用

| 身份 | 固定来源实际要求 |
|---|---|
| 官方强烈推荐 | A2 §4.2.2 p.23 强烈推荐先读原始 FlashAttention；p.24 推荐两篇论文帮助建立直觉 |
| 官方实现任务 | A2 要求 FA2 前向及指定后向；**实现必做不等于论文全文必读**；p.28 的 Triton backward 明确选做 |
| 编者核心范围 | 本页底部列出的精确论文节号，由本课程编者选定，不冒充官方逐节指定 |

## 2. “精确”究竟保留了什么？

先省去 batch 和 head，统一按行存 token：

$$
Q,K,V\in\mathbb R^{N\times d}.
$$

令 $\tau=1/\sqrt d$，$A$ 为允许处0、禁止处 $-\infty$ 的加性 mask：

$$
\begin{aligned}
S&=\tau QK^\top+A,\\
P&=\operatorname{softmax}_{\rm row}(S),\\
O&=PV\in\mathbb R^{N\times d}.
\end{aligned}
$$

两篇为简化叙述常暂时省去 $\tau$ 和 mask；FlashAttention 附录 B.3–B.4 再完整纳入缩放、mask、dropout。不能因此在实际目标中漏掉缩放。

**精确 attention**指不以稀疏、低秩或核近似替换这个目标。它不承诺不同浮点实现逐位相同：加法次序、累加精度、指数实现和 Tensor Core 路径都可能带来舍入差异。dropout 下还必须固定同一个随机 mask 才能比较同一次计算。

按一次乘加记2 FLOPs，两个稠密前向矩阵乘的主项为：

$$
\begin{aligned}
QK^\top &: 2N^2d,\\
PV &: 2N^2d,\\
F_{\rm fwd}&\approx4N^2d.
\end{aligned}
$$

因此，固定 $d$ 时仍是二次 FLOPs。因果 attention 跳过上三角，主项约减半，却仍然是 $\Theta(N^2d)$。FlashAttention 的反向还重算部分前向量，FLOPs 可以比保存完整 $P$ 的算法更多。

真正被移除的是**在 HBM 中物化完整 $N\times N$ 中间矩阵的必要性**，而不是所有 query–key 交互。论文另讨论的 block-sparse 扩展改变可见连接，不能拿它的复杂度替代稠密精确版本。

## 3. 为什么一个很小的状态能代替整行概率？

### 3.1 状态必须足以合并，而不是只记局部平均

对固定查询行 $i$，已处理键集合为 $J$。用三个量描述过去：

$$
\begin{aligned}
m_i&=\max_{j\in J}s_{ij},\\
\ell_i&=\sum_{j\in J}e^{s_{ij}-m_i},\\
u_i&=\sum_{j\in J}e^{s_{ij}-m_i}v_j.
\end{aligned}
$$

这里 $m_i,\ell_i$ 是标量，$u_i\in\mathbb R^d$。局部输出为 $o_i=u_i/\ell_i$。只保存 $o_i$ 不够：两个局部均值对应的未归一化质量不同，不能直接平均。

新来一块键 $B$ 时，先统一指数坐标：

$$
\begin{aligned}
m_i'&=\max\bigl(m_i,\max_{j\in B}s_{ij}\bigr),\\
\alpha_i&=e^{m_i-m_i'},\\
\ell_i'&=\alpha_i\ell_i+\sum_{j\in B}e^{s_{ij}-m_i'},\\
u_i'&=\alpha_i u_i+\sum_{j\in B}e^{s_{ij}-m_i'}v_j.
\end{aligned}
$$

关键检查是 $m_i'\ge m_i$，所以 $0<\alpha_i\le1$（已有有限最大值时）。**最大值升高，旧贡献应缩小，不应放大。**这条不变量比背伪代码可靠，也能检查固定 FA2 v1 中的排版错误。

### 3.2 FA1 与 FA2 保存的输出状态不同

FlashAttention Algorithm 1 每次合并后保存已经归一化的 $O$，因此下一次要把旧 $O$ 乘回旧归一化质量，再按新分母归一化。其论文级遍历是：外层取一块 K/V，内层扫过各 Q 块，并读写对应 $O,m,\ell$。

FA2 Algorithm 1 改为为一个 Q 块保留**尚未除以 $\ell$ 的累加器 $U$**，扫过所有 K/V 块后只归一化一次。两者在实数算术中得到同一个结果；“un-scaled output”不是不做最大值修正，而是不在每次迭代都做分母归一化。

FA2 最后保存：

$$
\begin{aligned}
O_i&=U_i/\ell_i,\\
L_i&=m_i+\log\ell_i.
\end{aligned}
$$

$L_i$ 是整行的 logsumexp。反向恢复局部概率时，$P_{ij}=e^{S_{ij}-L_i}$，不再需要把 $m_i$ 和 $\ell_i$ 两个统计量都写回用于反向。

论文的 $O(N)$ 额外存储说的是输入、输出之外的行统计量等；输入输出本身是 $O(Nd)$。片上 tile 工作区、寄存器和已经列作输入输出的梯度不能凭这句话消失。

### 3.3 mask 和 dropout 是状态契约的一部分

- mask 在指数与分母归约前生效。整个不合法块可以跳过；跨越因果边界的块才需要逐元素区分。
- 对方形、对齐的 self-attention tile，完全处于对角线下方的块可不施加 causal mask；完全处于上方的块跳过；对角块检查 $j\le i$。非方形 tile 不应机械套用“每行只一个边界块”。
- dropout 作用于归一化概率；用未归一化权重进行线性累加时可以等价施加同一个缩放随机 mask，但**softmax 分母不能改成 dropout 后的和**。
- 一个尚未见过合法键的空块，不应触发 $-\infty-(-\infty)$。完全没有合法键的查询行则需要调用方明确无效行语义；它不是普通 softmax 的有效输入分布。

## 4. 反向为何“多算一次”反而可能更快？

**原文定位：FlashAttention B.4，Algorithms 3–4；FA2 §3.1.2，Algorithm 2。**

暂不考虑 dropout。令 $G=\partial\mathcal L/\partial O$，先看依赖关系：

$$
\begin{aligned}
\partial V&=P^\top G,\\
\partial P&=GV^\top,\\
D_i&=\sum_jP_{ij}(\partial P)_{ij},\\
(\partial S)_{ij}&=P_{ij}\bigl((\partial P)_{ij}-D_i\bigr).
\end{aligned}
$$

有一个消除长行归约的恒等式：

$$
\begin{aligned}
D_i
&=\sum_jP_{ij}(G_i\cdot V_j)\\
&=G_i\cdot O_i.
\end{aligned}
$$

于是 $D\in\mathbb R^N$ 可由两个 $N\times d$ 张量逐行点积得到。反向只需按 tile 重建 $S,P$，随后累计：

$$
\begin{aligned}
\partial Q&=\tau(\partial S)K,\\
\partial K&=\tau(\partial S)^\top Q.
\end{aligned}
$$

$\partial S$ 在这里是对**已经缩放的 logits**的梯度，因此 $\tau$ 出现在传播到 Q/K 的边上。$\partial K$ 的维度是 $(N\times N)(N\times d)=N\times d$；不能倒写成 $Q(\partial S)^\top$。

与普通反向相比，FA 需要重算一次 $QK^\top$，但不需要从 HBM 读回完整 $P$。论文的核心主张不是“重计算总比保存快”，而是：**在这些 GPU、attention 形状和内存访问模式下，增加片上算术可以节省更昂贵的 HBM 流量。**

dropout 情况下设 $Z$ 为取0或 $1/(1-p)$ 的随机 mask，则 $O=(P\odot Z)V$，$\partial P=(GV^\top)\odot Z$，上述 $D_i=G_i\cdot O_i$ 仍成立。B.4 保存伪随机发生器状态、反向再生 mask；这要求前反向对同一元素使用同一随机选择，不能理解成“再随便抽一次”。

FA2 的论文后向按 K/V 列块分工，每个块独占自己的 $\partial K,\partial V$，却对多个 $\partial Q$ 块贡献，因此 §3.2 使用 atomic add。固定2026 A2 的**选做** Triton 后向另用分别计算 $\partial Q$ 和 $\partial K,\partial V$ 的组织、重复重建 $P$ 来避开跨块原子操作；不要把不同版本的任务算法混写成论文原算法。

## 5. IO 定理究竟证明了多强的结论？

### 5.1 先读假设和单位

FlashAttention Theorem 2 的模型中：$N$ 为序列长度，$d$ 为 head dimension，$M$ 为片上快速存储可容纳的标量规模，满足 $d\le M\le Nd$。HBM accesses 按搬运元素量计；换成 bytes 时必须加入元素字节宽度，并考虑实际混合精度缓冲。

论文比较的是指定 Algorithm 0 与 Algorithm 1：

$$
\begin{aligned}
\operatorname{IO}_{\rm standard}
&=\Theta(Nd+N^2),\\
\operatorname{IO}_{\rm FA}
&=\Theta\!\left(\frac{N^2d^2}{M}\right).
\end{aligned}
$$

其直观计数不是“Q/K/V 都只读一次”：K/V 块约有 $\Theta(Nd/M)$ 个；FA1 每个 K/V 块引发对 Q 及行状态的一遍访问，每遍主项 $\Theta(Nd)$，乘起来得到上式。Theorem 5 给出相同阶的后向 IO 结论。

在 $N\gg d$、$M\gg d^2$ 的适用范围内，FA 相对物化 $N^2$ 矩阵能显著减少流量。**固定 GPU，即固定 $M,d$，只让 $N$ 增长时，上式对 $N$ 仍然是二次的。**原文的 sub-quadratic 叙述不能被改写成不带参数条件的“HBM IO 对长度严格次二次”。更不能把 SRAM 的 KB 数值直接与 $d^2$ 个元素比较。

这是两层内存模型的算法分析，不是对每种缓存命中、数据类型、寄存器占用、实际矩阵乘实现的精确流量预言。尤其不能把定理里的 SRAM 容量当成每个线程块都能独占的全部硬件资源。

### 5.2 下界的量词不能倒过来

Proposition 3 的意思是：不存在一个精确算法，能在区间 $M\in[d,Nd]$ 的**所有 $M$** 上都做到

$$
o\!\left(\frac{N^2d^2}{M}\right)
$$

的 HBM 访问量。其证明取 $M=\Theta(Nd)$：此时要想优于 $\Theta(Nd)$，连输入输出必要的数据访问都无法满足。

这不是“对每一个固定 $M$，作者都证明了完全匹配的最强下界”。原文明确把更细的参数化下界留作后续问题。因此“在所有 SRAM 容量、所有算法中逐点最优”超出了该命题。

### 5.3 图中的证据支持什么，不支持什么？

Figure 2 左侧给出一个具体 A100 测量：GPT-2 medium attention，$N=1024,d=64$、16 heads、batch64，前向加后向的 FLOPs 从66.6增到75.2 GFLOPs，HBM 读写从40.3降到4.4 GB，时间从41.7降到7.3 ms。这里的 GB 是**累计传输量**，不是峰值占用；这些是作者数据，不是本课程复测。

同图中间还显示，块增大到一定程度后，流量继续降低不再等价于同幅度降时延。算术、片上资源或其他瓶颈会接手。图表支持特定配置下的 IO 解释，不支持“attention 无条件 memory-bound”或“tile 越大越快”。

## 6. FA2 的三个改进为什么不能合成一句“更好的分块”？

### 6.1 少做非矩阵乘工作

§3.1 引用 A100 的理论峰值：低精度矩阵乘312 TFLOP/s，普通 FP32 运算19.5 TFLOP/s，约16倍差异。这解释了为什么即使非 matmul 的 FLOPs 数占比不大，重复缩放、归约等仍值得优化。

这里不是“每条标量指令的实测延迟都是矩阵乘指令的16倍”：两者比较的是不同执行路径与精度的峰值吞吐，指数、除法、归约、访存也不具有统一单位成本。FA2 延迟 $U/\ell$、只保存 $L$，是在保持数学结果的前提下减少低吞吐路径上的工作，而不是删掉 softmax。

### 6.2 增加可调度线程块，不只依赖 batch × heads

FA1 的原始实现主要沿 batch 和 head 并行；当长序列迫使 batch 变小，$B\times H$ 个线程块可能不足以填满 GPU。FA2 前向外层沿 Q 的行块并行，线程块数进一步乘上 $\lceil N/B_r\rceil$。

独立性的原因是：每个输出行只需要自己的 softmax 状态；多个行块可以读取同一 K/V，而不互相合并输出。它不是把一个查询行拆成若干互不通信的局部 softmax。

![前向按查询行块独占输出；后向按键列块独占键值梯度、共同累加查询梯度](assets/paper-attention-ownership.svg)

*编者原创依赖图，表达的是读写所有权，不是论文图的截图或实测 trace。后向的共享写不能从前向的行独立性推出不存在。*

更多线程块也不保证更快：tile 太小会增加调度与加载开销；寄存器/共享内存太多会限制同时驻留的线程块。论文用 occupancy 概括资源利用问题，实际分析应区分“可用工作量太少”“驻留 warp 受资源限制”和“有驻留 warp 但执行单元仍在等待”。

### 6.3 改变 warp 之间谁拥有输出

§3.3 的关键不是再扩大线程块，而是改变块内工作划分：

- **split-K**：多个 warp 沿键位置拆分工作，为相同输出行产生部分和，需经共享内存写入、同步和合并。
- **split-Q**：warp 拥有不同查询行，共用所需 K/V，分别生成自己的输出行，避免上述输出部分和的跨 warp 合并。

这里的“前向无需 warp 间通信”针对这种部分和合并；不代表整个 kernel 没有协同加载、同步或共享内存访问。论文明确说后向依赖更复杂，仍有同步。

tile 变大可能减少某些加载，却增加寄存器与共享内存需求；溢出寄存器会引入 spill，资源超限则无法启动。论文列出的64/128尺寸调优是当时实现经验，不是对 B200 或任意 head dimension 的最优答案。

## 7. 怎样读速度数字，而不把指标换掉？

### 7.1 kernel 吞吐与整模型 MFU 分开

FA2 §4.1 的主要微基准使用单张 A100 80GB SXM4：序列512到16k，总 token 数固定16k，hidden dimension2048，head dimension64或128，有/无 causal mask分别测量。改变序列长度时 batch 随之改变，不能当成固定 batch 的纯长度实验。

论文写出的前向主项 $4N^2dH$ 是每条序列的 matmul 计数；若计量整个 batch，维度完整的账本为：

$$
F_{\rm batch,fwd}\approx4BHN^2d.
$$

这是编者显式补出 batch 轴，不是声称原文公式印有 $B$。该微基准对 causal 计数约除2，后向则按5次主要 matmul 与前向2次的关系乘2.5，包含重计算。它不是整个模型的训练 FLOPs。

§4.2 的端到端实验使用8张 A100、1.3B/2.7B GPT-style 模型、2k/8k context。其每序列模型 FLOPs 约定为：

$$
F_{\rm model}=6N\Psi+12n_{\rm layer}hN^2,
$$

其中 $\Psi$ 为模型参数数，$h$ 为模型隐藏维度。作者为保持与所引文献一致，**没有将此处 causal attention 项减半**。所以不同文章的 MFU 或 TFLOP/s 若采用不同 FLOP 分子，不能直接按百分比排名。

### 7.2 v1 的自比较原文必须留下痕迹

固定 v1 §4.2 p.11 印有短语 **“compared to FlashAttention-2”**，使句子变成“FA2 比 FA2 快1.3倍”。这确实存在于原 PDF，不是提取错。

**编者注**：同文 §4 引导段写的是相对 FlashAttention；Table 1 又把 FlashAttention 与 FA2 分成不同列。例如2.7B、8k那一行分别为175和225 TFLOP/s/GPU，$225/175\approx1.29$。因此本页将它解读为相对 FA1 的约1.3倍，并显式保留笔误说明，不静默替换固定原文。相对无 FA 基线的同一行是 $225/80\approx2.81$；不同基线不能互换。Table 1 的1.3B、8k行另为220对72，这也提醒我们：正文概括数并非每一行比值的严格最大值，本页不把“2.8倍”升级为全表上界。

作者报告的“最高约225 TFLOP/s/GPU、72% MFU”只属于上述实验与计数约定；不能成为本机、2026 B200 作业、任意 decoder 或短序列推理的保证。v1 的 H100 图还属于不同硬件条件；其进一步使用新指令的加速设想是未来工作，不是已实现结果。

## 8. 固定 FA2 v1 的公式应怎样带着勘误读？

以下均已打开原 PDF 对应页视觉核对。**原文保持不动，本页数学按已定义的不变量独立推导。**详细初等推导仍见 ext05。

| 原文位置 | 原文问题与本页采用的判断 |
|---|---|
| p.3 §2.2 梯度式 | 原式把 $\partial K$ 写成 $Q(\partial S)^\top$；按行向量约定应为 $(\partial S)^\top Q$，恢复缩放时再乘 $\tau$ |
| p.3 脚注2 | “typically by 1/d”确在 PDF；标准 scaled dot-product attention 使用 $1/\sqrt d$，与 FA1 B.3 及固定 A2 一致 |
| p.4 §2.3.1 标准输出展开 | 第二个块贡献缺少显式共同分母；应先把两个未归一化贡献相加，再统一除 $\ell$ |
| pp.4–5 在线更新式 | 旧输出系数中的逆号及缺失的最大值修正不能直接照抄；已归一化旧输出应乘 $\alpha\ell_{\rm old}/\ell_{\rm new}$；未归一化旧贡献应乘 $\alpha$ |
| p.6 两块推导及 Algorithm 1 step10 | 原 PDF 的 $\operatorname{diag}(e^{m_{\rm old}-m_{\rm new}})$ 外印有逆号；本页采用直接乘 $\alpha$，不取逆；否则最大值升高会放大旧贡献，且初始状态也出现问题 |
| p.6 causal masking 第2点 | 原文把免 mask 区域的行/列不等关系写反；正确免 mask 区域满足该块所有键列索引不大于查询行索引；上三角应跳过 |
| p.7 Algorithm 2 step4 | $D$ 的空间印为 $\mathbb R^d$，但它逐行归约，实际应为 $\mathbb R^N$；随后按 $B_r$ 切分也支持此判断 |
| p.11 §4.2 | 自比较措辞按上一节保留来源注，不把“自己比自己快”当事实 |

勘误的意义不是绕过论文，而是说明**读懂算法需要检查维度、归一化与所有权，不能只照着排版录入**。本页没有据此宣称作者实现存在同样错误，也未审计论文代码。

## 9. 自测：能否保住结论的条件？

1. 没有保存 $N\times N$ 的 $P$，为什么 FLOPs 仍然二次？
2. 新块最大值比旧最大值大，旧累加器该乘大于1还是小于等于1的数？
3. $O(N)$ 额外存储是否意味着整个 attention 总共只占 $O(N)$ bytes？
4. 固定 $M,d$ 时，$N$ 翻倍，论文 IO 主项怎样变化？Proposition 3 是否证明每个 $M$ 上逐点最优？
5. FA2 为什么沿查询行切线程块，而不是独立计算各键块的局部 softmax 后直接相加？
6. 为什么后向不同 K/V 块会争用 $\partial Q$，却能独占各自 $\partial K,\partial V$？
7. 看到“225 TFLOP/s”和“230 TFLOP/s”，能否直接判断哪个模型训练更快？

### 答案与提示

1. 稠密版本仍遍历 query–key 交互；省掉的是显存物化和反复搬运，不是交互集合。
2. 乘 $e^{m_{\rm old}-m_{\rm new}}\le1$；如果取逆，归一化坐标改变的方向就错了。
3. 不意味着。它排除输入输出，且元素数与 bytes还差数据类型；输入输出为 $O(Nd)$，片上工作区另计。
4. 约4倍；不证明逐点最优，命题排除在整个容量区间上统一取得所述 little-o 改进的算法。
5. 输出行彼此独立，键块之间却共享该行的归一化分母与最大值；局部概率不能直接拼成完整分布。
6. 每个键块影响所有查询；不同键块对相同查询梯度贡献需求和，而键值梯度行由该键块独占。
7. 不能。先检查 kernel/整模型、前后向、batch/head、causal、硬件、FLOP 分子和计时范围。

## 原文导航、署名与编写边界

页码为固定 PDF 的1起始物理页码。以下精确核心节号是**编者选定**；A2的官方推荐不指定这些节号。

| 阅读问题 | 固定原文定位 |
|---|---|
| 硬件约束、物化成本 | FlashAttention §2.1–2.2，pp.3–4 |
| 在线状态、tiling、重计算 | FlashAttention §3.1，pp.4–5，Algorithm 1、Theorem 1 |
| IO 与量词 | FlashAttention §3.2，pp.5–6，Theorem 2、Proposition 3、Figure 2；选读 Appendix C 的 Proposition 3 / Theorem 5 证明，p.24 |
| mask、dropout、完整前后向 | FlashAttention B.3–B.4，pp.19–21，Algorithms 2–4、Theorem 5 |
| GPU 执行模型 | FA2 §2.1，p.2；选读 §2.2–2.3，pp.3–5 |
| 非 matmul、行统计量 | FA2 §3.1–3.1.2，pp.5–7，Algorithms 1–2 |
| 线程块与 warp 分工 | FA2 §3.2–3.3，pp.7–9，Figures 2–3 |
| 微基准与整模型口径 | FA2 §4.1–4.2，pp.10–11，Figures 4–7、Table 1（表实际在p.12）；选读 §5，pp.11–12 |

- **FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness**：Tri Dao、Daniel Y. Fu、Stefano Ermon、Atri Rudra、Christopher Ré；固定 [arXiv:2205.14135v2](https://arxiv.org/abs/2205.14135v2)，2022-06-23，PDF题头另印 June 24，[固定 PDF](https://arxiv.org/pdf/2205.14135v2)。指定核心全部实际阅读；另读题名、摘要、§1以及 Appendix C 中上述两段证明。未完整精读 B.1–B.2、C其余证明、§4全部实验及 D/E；不以摘要中的速度声明代替实验条件。
- **FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning**：Tri Dao；固定 [arXiv:2307.08691v1](https://arxiv.org/abs/2307.08691v1)，2023-07-17，PDF题头另印 July 18，[固定 PDF](https://arxiv.org/pdf/2307.08691v1)。指定核心及选读 §2.2–2.3、§5 已实际阅读；重要公式页和 Table 1 已核对，Figures 4–7只核对坐标、设定和代表性数据，不是逐数据点审计，参考文献未完整精读。
- **课程来源**：[固定2026 A2 PDF](https://github.com/stanford-cs336/assignment2-systems/blob/ca8bc81a59b70516f7ebb2da4808daade877c736/cs336_assignment2_systems.pdf)，Spring 2026 v26.1.3，§4.2.2 pp.23–24 的推荐与概念段、pp.27–28 的后向及选做边界。本文只针对上述阅读身份与算法版本差异查阅，不声称在本分片读完48页作业。
- **权利**：两篇固定版各自的许可链接均为 [arXiv 非独占分发许可](https://arxiv.org/licenses/nonexclusive-distrib/1.0/)。它授权 arXiv 分发，不等于授予公众完整翻译权。本页按独立问题组织，不逐段翻译或改写成论文替代品；没有搬用论文插图或整张实验表。A2、论文代码的许可不向论文全文传递。
- **视觉与执行边界**：实际查看 FA1 pp.5–6、20–21及 FA2 pp.3–13 的本地渲染页，按上述目标核对；不是全部34/14页逐式审校。页图仅本地留作取证，不随正文发布。原创依赖图不是课堂截图；没有运行官方作业、benchmark、训练或付费计算。精确行范围、源哈希与阅读记录见 `sources/p4-papers/`。
