---
title: "集合通信：同一个结果，为什么有不同的路程"
lectureId: ext07
kind: "编者专题，非 Stanford 官方讲次"
sourceVersion: "NCCL 2.32.3 文档快照；NCCL 2.4 双树技术文章（2019-02-04）；PyTorch 2.9 文档；ZeRO 1910.02054v3"
sourceManifest: "sources/p4-distributed/manifest-fragment.json"
readingScope: "集合语义、进程组顺序与异步语义、双树原理；ZeRO只核对通信口径，完整精读归lec08 materials。"
status: "原创算法推演、通信账本与理论时间模型；未执行通信程序或GPU性能实验。"
mediaStatus: "无独立官方录像，仅notes；图示均为原创。"
---

# 集合通信：同一个结果，为什么有不同的路程

## 学习问题与边界

读完应能回答：

1. All-reduce 与 reduce-scatter 的**结果归属**有什么不同？
2. Ring 为什么需要两段各 $p-1$ 轮，却不在每一轮发送整个张量？
3. “通信量是两倍模型大小”究竟是每卡发送、每卡收发合计，还是全体？
4. Tree 的轮数少，为什么不能据此断言任何张量都更快？
5. 有了正确通信公式，为什么仍可能挂起、越界或测出假加速？

同步训练为何需要归约、梯度如何加权，先读 [L07](#/c/stanford-cs336-2026/lec/lec07?v=notes)。本页只研究**已经确定要执行的集合操作如何搬运数据**，不提供 A2 DDP、分片优化器或 FSDP 的实现。

## 1. 先确定结果，再讨论线路

设进程组有 $p$ 个 rank，每个 rank 的输入向量有 $n$ 个元素，每元素 $b$ byte，完整向量大小为 $M=nb$ byte。这里 rank 是**组内逻辑编号**，不是 GPU 的固定物理编号。

| 操作 | 输入与输出的契约 | 是否做元素归约 |
| --- | --- | --- |
| All-reduce | 每 rank 输入 $n$ 个元素，每 rank 得到同一个 $n$ 元素结果 | 是 |
| Reduce | 同上，但结果只交给指定 root | 是 |
| Broadcast | root 的 $n$ 元素复制给所有 rank | 否 |
| Reduce-scatter | 每 rank 输入 $n$ 元素，归约后每 rank 只得到规定的一段 | 是 |
| All-gather | 每 rank 提供自己的一段，所有 rank 得到按 rank 顺序拼接的整体 | 否 |
| All-to-all | 每 rank 按目的地切分输入，分别发往各 rank；接收端按来源组织 | 否 |

以下默认 sum，且 $n$ 可被 $p$ 整除。于是：

$$
\begin{aligned}
y[j]&=\sum_{r=0}^{p-1}x_r[j],\\
\operatorname{AllReduce}
&=\operatorname{AllGather}\circ\operatorname{ReduceScatter}.
\end{aligned}
$$

最后一式是**结果语义等价**，不表示 API 内部必然调用了另外两个公开 API，也不保证不同算法的浮点归约顺序逐位相同。Sum 还不是平均；训练目标所需的归一化由上层契约决定。

另一个等价分解是 reduce 到 root，再 broadcast。两条分解都正确，但通信负载分配可以很不同。

> **尺寸陷阱：**谈 reduce-scatter 时，本页的 $M$ 是每 rank 的完整输入；谈随后 all-gather 时，$M$ 是拼接后的完整输出，而每 rank 的输入只有 $M/p$。不先说这一点，两张正确的通信表也会看起来相差 $p$ 倍。

## 2. Ring：把完整向量拆成同时流动的块

把向量分为 $p$ 块，逻辑环为 $0\to1\to\cdots\to p-1\to0$。每轮每个 rank 向后继发送一块，同时从前驱接收一块。

### 2.1 Reduce-scatter：移动的是“带着部分和的块”

用4个 rank 和4块说明。记 $x_r^{(c)}$ 为 rank $r$ 对块 $c$ 的输入。只追踪块0：

| 轮次 | 块0的流向 | 接收后持有的部分和 |
| --- | --- | --- |
| 1 | rank0 → rank1 | $x_0^{(0)}+x_1^{(0)}$ |
| 2 | rank1 → rank2 | 再加 $x_2^{(0)}$ |
| 3 | rank2 → rank3 | 再加 $x_3^{(0)}$，块0归约完成 |

同一轮，块1从 rank1 开始、块2从 rank2 开始、块3从 rank3 开始，按同样方式流水移动。因此3轮后不是“只有块0算好了”，而是所有块都完成了，只是分别位于不同 rank。

这个教学调度结束时，rank0、1、2、3分别拥有完整归约后的块1、2、3、0。若公开 reduce-scatter 契约要求 rank $r$ 持有块 $r$，可在**起始块编号与调度设计**中消除这个循环偏移；不能把内部方便的编号直接当成 API 输出顺序。

### 2.2 All-gather：移动的是“已经完成的块”

从各自持有的最终块开始，再沿环转发3轮。此阶段只复制，不再求和。每轮获得一个新块，最终每 rank 都有全部4块。

![四卡环的归约与广播账本](assets/ring-two-phases.svg)

*原创图：只高亮块0的路径；另外三块在相同轮次交错流动。每段3轮，每轮每卡发送的是四分之一向量。不是 NCCL trace，也不表示真实库只使用一个环或一个 channel。*

为什么足够？一个块最初已有1个 rank 的贡献，经过 $p-1$ 次“传递并加上接收者贡献”，便含全部 $p$ 份输入。随后经过 $p-1$ 次纯转发，可到达其余所有 rank。每一份贡献只加一次，是比“最后数值差不多”更有用的不变量。

### 2.3 数值例：别把块大小当成整向量大小

4个 rank，每 rank 输入128 MiB。每块32 MiB：

- Reduce-scatter：每 rank 发送 $3\times32=96$ MiB，也接收96 MiB。
- All-gather：每 rank 再发送96 MiB、接收96 MiB。
- 整个 all-reduce：每 rank **发送192 MiB，接收192 MiB**。
- 每 rank 收发合计384 MiB；全体发送合计768 MiB。

这里 $1\text{ MiB}=2^{20}$ byte。数值是算法推导，不是网卡计数器或显存带宽测量。

## 3. 一张表固定三种通信口径

理想均匀 ring，不含协议头、重传、对齐和控制消息：

| 阶段 | 每 rank 发送 byte | 每 rank 接收 byte | 全体发送 byte |
| --- | --- | --- | --- |
| Reduce-scatter | $\frac{p-1}{p}M$ | $\frac{p-1}{p}M$ | $(p-1)M$ |
| All-gather | $\frac{p-1}{p}M$ | $\frac{p-1}{p}M$ | $(p-1)M$ |
| All-reduce | $2\frac{p-1}{p}M$ | $2\frac{p-1}{p}M$ | $2(p-1)M$ |

**全体发送 = 全体接收**，因为同一次逻辑传输在发送端和接收端各出现一次。将两者相加是端点流量之和，会把同一次传输计两遍；它可以是有用的统计量，但不是新的逻辑有效载荷。

还应区分：

- **端点注入量**：从 rank 发出的 byte，本页主表采用此口径。
- **物理链路 byte-hop**：一条消息若跨过多段交换链路，每段都可能计数；不能从端点总量直接推出。
- **显存读写量**：通信 kernel 可能读写临时缓冲并进行归约，不等于网络有效载荷。
- **跨节点量**：只计穿过节点边界的传输，不把本节点 NVLink 流量也算成 NIC 流量。

当 $p$ 很大，每 rank 发送约 $2M$。这正是常见“大张量 all-reduce 两倍大小”的一种口径；若报**发送加接收**则接近 $4M$。ZeRO 的 $2\Psi/3\Psi$ 通信分析采用元素量与大规模近似，不能不换算 dtype 与计数口径就当成全局 byte。论文的精确解释统一见 [ZeRO 材料](#/c/stanford-cs336-2026/lec/lec08?v=materials)。

## 4. Tree：减少依赖轮数，但不自动均衡每个端点

### 4.1 一个完整的8-rank二项树调度

下面是**整向量、非流水、单端口教学模型**。每次传输大小都是 $M$。

归约向 root0 汇集：

1. 第1轮：$1\to0$、$3\to2$、$5\to4$、$7\to6$；接收者加入本地输入。
2. 第2轮：$2\to0$、$6\to4$；每个发送者已经代表两个 rank。
3. 第3轮：$4\to0$；root 得到全部8份贡献。

广播反向展开：先 $0\to4$，再 $0\to2$ 与 $4\to6$，最后 $0\to1$、$2\to3$、$4\to5$、$6\to7$。总计6个依赖轮。

树有 $p-1$ 条边，每条边归约时传 $M$、广播时再传 $M$，故全体发送仍是 $2(p-1)M$，与 ring 相同。然而 root0 接收3次 $M$、发送3次 $M$；叶子只发送和接收各一次 $M$。**同样的全局总量，不意味着同样的最忙端点。**

### 4.2 不要把三种“树形”方法混成一个公式

| 方法 | 最重要的结构差别 | 教学模型中的后果 |
| --- | --- | --- |
| 上述 reduce + broadcast 树 | 整向量沿树边上行、下行 | 轮数对数，但沿关键路径多次传完整 $M$ |
| Recursive doubling all-reduce | 每轮与另一子群交换完整部分和 | $p=2^q$ 时 $q$ 轮，每 rank 发送 $qM$ |
| Recursive halving + doubling | 先逐轮缩小负责块，再逐轮扩张已归约块 | $p=2^q$ 时各 $q$ 轮，理想每 rank 总发送 $2(p-1)M/p$ |

NCCL 2.4 的**双二叉树**又不是上表的简单整向量树：把数据分成两半，安排两个互补的树，让某棵树的内部节点在另一棵树上尽量为叶子，配合分块流水减轻热点。官方2019年文章解释这一设计的对数延迟与带宽动机；它不能被简化为“把单树轮数除以二”，其历史性能曲线也不是本页的新测量。

### 4.3 六个 rank 并不会使集合通信失去定义

Ring 对任意 $p\ge2$ 都可以组织，等大小块还要求元素数可整分；不整分时须有不等块或 padding 等明确处理，不能默默丢尾部。

树也可以不是满树。例如6个 rank 的归约：第一轮 $1\to0$、$3\to2$、$5\to4$；第二轮 $2\to0$；第三轮 $4\to0$。不存在的6、7号 rank 不参与。广播沿真实边返回即可。

真正受限制的是**特定的简洁调度公式**：无修改的二进制 XOR 配对、每轮严格等半划分，通常假设 $p=2^q$。$p=6$ 时不能直接把 $\log_2 6$ 当成轮数，也不能对不存在的伙伴发消息。通用实现可先折叠部分 rank、处理非均匀子群，或选择别的算法；这些会改变轮数、流量与负载分布。NCCL/PyTorch 的集合语义不要求 world size 必须为二次幂。

## 5. 延迟与带宽：先写单位，再比较

设每个依赖轮有启动成本 $\alpha$ 秒，单方向有效链路带宽为 $B$ byte/s；假设发送和接收可并行、所有边同速、无争用，且暂时忽略归约计算和内存成本。

Ring 的理论时间：

$$
\begin{aligned}
T_{\rm ring}
&\approx 2(p-1)\alpha\\
&\quad+\frac{2(p-1)M}{pB}.
\end{aligned}
$$

上述整向量树在 $p=2^q$ 时：

$$
T_{\rm tree}\approx2q\left(\alpha+\frac{M}{B}\right).
$$

**自拟模型参数**：$p=8$，$\alpha=5\,\mu s$，$B=20$ GB/s，且 GB 使用十进制 $10^9$ byte。它们不是任何特定 GPU 的实测值。

| 完整向量大小 $M$ | Ring 模型 | 整向量树模型 |
| --- | --- | --- |
| 4 KiB | 约70.36 μs | 约31.23 μs |
| 1 MiB | 约161.75 μs | 约344.57 μs |

小消息时启动轮数主导；大消息时每轮载荷和流水效率重要。这只比较**已声明的两个模型**，不能据此预测现代 NCCL 双树、NVSwitch 或网络内归约的实际交叉点。

如果收发共享同一半双工瓶颈，或者多个逻辑 channel 共用一条 NIC，上式的 $B$ 就不能直接填硬件宣传的双向总带宽。若每个元素还需本地加法，可另加归约计算项；不能把网络模型当作完整 kernel 模型。

## 6. 拓扑：同一个逻辑环，可能走完全不同的路

考虑8个 rank，两个节点各4卡，节点内快、节点间共享一条较慢链路。一个层次化分解是：

1. 节点内 reduce-scatter：每张卡得到本节点贡献的 $M/4$ 一段。
2. 两节点对应段之间 all-reduce：形成4个二卡组，每组处理 $M/4$。
3. 节点内 all-gather：恢复完整全局结果。

若第二步对每段只互换一次节点部分和，则每个节点向外发送合计 $4(M/4)=M$，也接收 $M$。四个组共用一条 NIC 时，不能各自都按整条 NIC 的峰值带宽并行完成。

相比之下，按节点连续排 rank 的单环有两条跨节点有向边；理想 ring 每条这样的边承担 $2(p-1)M/p=1.75M$。这个自拟拓扑说明：**优化慢链路上的流量，与减少全体总量不是同一问题。**层次化还引入本地阶段与启动开销，不能无条件称它更快。

现实中还要问：GPU 与 NIC 的亲近关系、PCIe 根节点、NVLink/NVSwitch 域、网络超售、多个作业争用、channel映射。算法名称只描述逻辑通信，不保证物理路径和带宽。

## 7. 正确性先于“异步”：一份通信契约清单

- **组一致**：参与的是哪一个 process group？组内 rank 与全局 rank 有没有混用？
- **顺序一致**：各 rank 对同一组调用相容的操作序列；某 rank 的条件分支跳过一个 collective，可能让其他 rank 永久等待。
- **签名一致**：归约类型、dtype、元素数和输出布局相容。All-to-all 的不等 split 需要逐来源—目的地匹配，不是所有 rank 的总元素数相同就够。
- **数据就绪**：发送前生产者完成；读取结果前通信完成；缓冲区不能被提前改写或释放。
- **stream一致**：CUDA API 返回不等于设备已执行完。PyTorch 2.9 的 `Work.wait()` 建立相应 CUDA stream 的依赖，不应被想象成“CPU必然等到所有GPU空闲”。跨 stream 消费须建立正确依赖。
- **缩放一致**：sum 与平均、微批累积与不同有效 token 数的权重，属于训练语义，不由 ring 自动修正。

通信和计算重叠不是把时间简单相减。只有没有数据依赖的计算才能隐藏通信；通信 kernel、计算 kernel 还可能争用 SM、显存和链路。独立测通信、测完整 step、看时间线三者回答不同问题，方法见 [性能分析专题](#/c/stanford-cs336-2026/lec/ext06?v=notes)。

## 8. 自测与答案

<details>
<summary>1. 六个rank、每rank完整输入120 MiB，理想ring每rank发送多少？</summary>

每块20 MiB；每阶段5轮、发送100 MiB。两个阶段共发送200 MiB，也接收200 MiB；每rank收发合计400 MiB，全体发送1200 MiB。六个rank不需要补成八个，但等分输入和调度必须明确。

</details>

<details>
<summary>2. Ring和整向量树的全体发送总量相同，能推出耗时相同吗？</summary>

不能。依赖轮数、最忙端点、关键路径上载荷、拓扑、流水及争用都不同。全体byte只是一笔总账，不是时间线。

</details>

<details>
<summary>3. Reduce-scatter后每卡只有一段梯度，是不是丢了其余梯度？</summary>

不是。完整归约结果按所有者分布在组内。若优化器只更新本rank负责的参数段，这正是所需结果；若每卡仍需要完整结果，才继续all-gather。所有权设计见ext08。

</details>

<details>
<summary>4. 两个rank调用同样大小的all-reduce，但顺序分别是A、B和B、A，会自动按张量名字匹配吗？</summary>

不会按Python变量名匹配。即使shape相同而没有挂起，也可能把不同语义的张量归约到一起，产生错误结果。通信顺序和数据身份必须由程序契约保证。

</details>

<details>
<summary>5. 换成树后输出末位改变，是否必然是通信错误？</summary>

不必然。浮点加法不满足实数意义的结合律，不同归约顺序可产生末位差异。应先用可精确检查的小整数、布局不变量和明确浮点容差排除错误；同一次all-reduce各rank应得到相同归约结果，但不同算法运行之间不保证逐位相同。

</details>

## 来源、版本与处理边界

- NVIDIA，[Collective Operations](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html)：取得时页题为 **NCCL 2.32.3**；实际读集合正文全部定义及布局说明。它是补充文档快照，不是2026课堂或A2依赖版本的声明。新API是否存在必须查安装版本，本文不依赖当前原生all-to-all入口写实现。
- Sylvain Jeaugey，[Massively Scale Your Deep Learning Training with NCCL 2.4](https://developer.nvidia.com/blog/massively-scale-deep-learning-training-nccl-2-4/)，2019-02-04：实际读文章正文，使用双树与层次环解释；不使用后来插入的AI摘要作证据，不搬历史性能图或将其归为本页测量。
- PyTorch [Distributed communication package](https://docs.pytorch.org/docs/2.9/distributed.html)，**2.9文档快照，页面源码链接为v2.9.1**：实际选读后端、初始化、Groups、同步/异步语义，以及all-reduce、reduce-scatter、all-to-all接口契约。未全读3323行文档或审计后端实现。
- Rajbhandari等，[ZeRO固定v3](https://arxiv.org/abs/1910.02054v3)：核对§3–5与§7相关段落；大规模近似、状态分片推导和论文评议仅在[L08材料](#/c/stanford-cs336-2026/lec/lec08?v=materials)。不把论文的历史硬件结果当作当前性能预测。
- 本文算法调度、数值、表格和SVG为原创；没有复制来源图、翻译完整来源或提供作业代码。补充站点文档的全文翻译授权未据此确认；ZeRO的arXiv非独占分发许可也不是公开全文翻译许可。完整URL、获取日期、SHA256与实际阅读范围在 `sourceManifest`。
- 官方AI政策仅允许概念/API辅助，不允许AI实现作业或排行榜；[A2指导](#/c/stanford-cs336-2026/lab/a2-systems?v=guide)与[共享资料](#/c/stanford-cs336-2026)统一保留执行边界。本文未运行CPU/Gloo或GPU/NCCL，理论数值不冒充完成记录。
