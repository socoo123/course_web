---
title: A2 概念与调试指导：先证明等价，再证明更快
kind: 编者原创概念与证据指导；不提供作业实现、伪代码、计分短答或排行榜方案
source: Spring 2026 A2 v26.1.3 与固定接口；完整要求见实验说明
source_read_scope: 48 页 handout 提取文本全文、固定测试及政策全文；未逐页视觉审校
status: P4 指导正文；不是官方测试通过、GPU 性能或排行榜完成记录
execution: 未运行官方代码、训练、benchmark、依赖安装或付费计算
license: 原创教学组织；引用第一方要求按 MIT 保留页底完整声明；第三方权利另计
---

# 为什么“结果一样”和“跑得快”要分开证明

A2 最容易出现的错误不是公式写错，而是**证明对象悄悄变了**：测到的是派发时间而不是完成时间；GPU 前向省了显存，但后向又物化大矩阵；两个 rank 的 loss 相近，却没有在优化同一个全局目标；热缓存很快，但正式冷启动超时。

本页把这些问题组织成一条证据链。完整配置、27 个计分题及子问见 [实验说明](#/c/stanford-cs336-2026/lab/a2-systems?v=zh)，本页不代给这些题的答案，不给 Python、伪代码、可提交 kernel 或排行榜优化方案。所有小例都是**独立教学量纲检查**，不是测量记录。

## G0．先给每个结论写一个“适用标签”

一个结果至少需要四项身份：

1. **语义：**输入、参数、loss reduction、梯度、更新后的参数，究竟哪个一致？
2. **工作量：**forward、backward、optimizer，还是完整训练步？是否含通信、重算与清梯度？
3. **环境：**硬件型号/数量、backend、dtype、软件版本、缓存与预热状态。
4. **证据：**纸笔推导、小例、单元测试、端到端计时，还是 profiler trace？

![正确性、性能和完成度的三条证据链](assets/evidence-lanes.svg)

例如，“CPU/Gloo 上两 rank 与单进程基线逐步一致”是有价值的正确性证据，但它对 NCCL 带宽、CUDA stream 重叠和 B200 latency 没有直接证明力。反过来，一个漂亮的 GPU trace 不能证明梯度正确。页面内容齐全更不能替代任何一条执行证据。

### G0.1 环境边界不是需要掩盖的失败

没有 GPU 时可以理解形状、自动微分生命周期、通信组语义和并行纸笔模型。若实际自行调试 CPU/Gloo，应把结论限定在那里；Triton GPU 测试 skip 必须写 skip，不能写 passed。MPS 是另一后端，不拥有同等 Triton/NCCL/Nsight 合同。官方提示 Triton interpreter buggy，不应把 interpreter 的行为当 GPU 编译器的最终判据。

校内 Modal 访问需要资格，不是公开源码附赠的服务。并发 ≤3 GPU 的通用建议与题目的 6 GPU 设置需要 staff 协调；不购买算力、不启动实验也能完成本文的学习导航，但不能因此称作业的硬件测量已经完成。

### G0.2 版本比“网上搜到同名作业”更重要

本页只对应 2026 固定 A2，PDF v26.1.3、package v26.1.4。旧版 bucketed DDP 已移除，activation checkpointing 和 FSDP 是当前范围；必做后向是编译 PyTorch，Triton 后向是选做；排行榜测两 B200 上完整模型一步，不是旧 H100 attention。

官方 AI 政策还限定学习方式：允许概念与 API 帮助，不允许 AI 写实验、实现、伪代码或计分解答。遇到不确定时，可拿自己的观察与问题向 staff 询问，而不是要求 agent 补全代码。

## G1．计时：你究竟让时钟覆盖了什么

对应实验说明题 01、02、07、08、11、12、14、15、17、19、27。

### G1.1 三条时间轴，而不是一个“耗时”

GPU 工作至少有三个时间概念：CPU 提交调用、GPU 实际执行、CPU 得到可用完成结果。异步执行使 CPU 可以提前提交工作，这是吞吐优势；也使普通函数调用返回时间不能直接代表 GPU 完成时间。

**独立例：**假设 CPU 用 0.2 ms 提交一项工作，设备执行需要 3 ms。若只包住 CPU 调用，得到约 0.2 ms，不能宣称设备吞吐提高了 15 倍。这是题设数字，不是某种硬件的实际性能。将同步放在目标区间末尾能覆盖待完成工作，但若区间开头已有未完成任务，仍会把别人的工作计入。因此要解释计时边界前的设备状态。

还要分清两种问题：

- **程序正确性的依赖：**下一个消费者能否安全使用结果？涉及 stream、event、collective handle 等语义。
- **计时完成性：**被测工作是否已全部完成？CPU 计时需要合适的设备完成边界。

“同步 collective”中的同步通常不意味着 CPU 已等到 GPU 的物理执行结束。`async_op=False` 也不免除官方 CUDA 计时同步要求；`handle.wait()` 对正确依赖很重要，但不能无条件等同 CPU 看见所有设备工作结束。

### G1.2 预热不是删除坏数据

第一次调用可能包含初始化、内存池扩张、库选择、编译和通信建连。预热的作用是定义你要测量的稳态，而不是把不喜欢的样本抹掉。应先固定规则，再收集数据：何时开始，多少样本，是否重新分配输入，哪一步包含编译。

题 01 要比较 0 / 1 / 2 / 5 步预热，这正是在观察状态如何稳定。不要预先写“5 次必定足够”；那是题目测量设置或一般经验，真正波动仍需报告。Nsight 下的 wall-clock 与无 profiler 的基准不同，也不能直接归因于模型退化。

建议记录的不是一张“最快时间”表，而是一张实验身份表：模式、shape、dtype、硬件、预热数、样本数、统计量、cache 状态、异常/OOM。若需要解释不稳定，可观察各样本顺序，寻找首次 optimizer state 分配、特定 shape 重编译或其他进程影响，而不是只报最小值。

### G1.3 三种 attention 计时不是可随意拼接的数字

单独 forward、单独 backward、端到端 forward-backward 各有执行状态。独立后向需要合法的前向图或自定义 backward 输入；重复使用图、是否清梯度、是否保留缓存、是否重建输入都会影响比较。不能把一张图的首次 backward 与另一实现的稳态后向当同一条件。

端到端延迟也未必等于两次独立 benchmark 的数值和：缓存、内存分配与调度边界可能不同。解释差异时先查实验边界，不急于推断某个 kernel “神奇加速”。

题 07 的 batch8、固定五种序列，与题 11 的 batch1、单 B200、causal、128…65536 扫描不是同一实验。将结果放入同一图时必须明确标签；不要按相似题名合并表格。

### G1.4 compile：两本账一起存在

`torch.compile` 改变的是执行图与生成的代码。它可能融合点运算、改变 launch 数量和 saved tensors，也可能因动态图或输入变化触发额外编译。需要同时保留：

- 冷启动总耗时：初始化、编译、autotune、正式测量何时发生。
- 固定 shape / dtype 稳态：每步实际执行成本。

A2 排行榜同时约束两者：空 PyTorch/Triton cache 下整个 run ≤10 min，完整训练步优于 baseline。一个测量协议若只报告热缓存最快 kernel，就没有回答官方问题。

**自检：**一个函数调用耗时 1 ms，但同步后的区间是 7 ms，应把哪个写成 GPU 完成时间？

**答：**若同步区间确实只包含该工作，7 ms 才覆盖完成；仍须说明区间前没有遗留工作。1 ms 可能只是 host 提交成本。

## G2．Profiler：把“哪里慢”变成可定位的证据

对应题 02、05、17、21；完整方法见 [ext06 性能分析](#/c/stanford-cs336-2026/lec/ext06?v=notes)，硬件限制见 [L05](#/c/stanford-cs336-2026/lec/lec05?v=notes)。

### G2.1 累计 kernel 时间、墙钟和关键路径不同

CUDA Kernel Summary 的累计时间回答“这些执行区间总共有多长”，wall-clock 回答“外部经过了多久”。不同 stream 上的区间可能重叠，因此累计值不应机械相加当总时间。

对一个时间占比结论，先问：分母是什么？是 forward GPU kernel 累计时间，还是整步 wall-clock？是否把 host gap、同步等待、通信也纳入？前向占比和完整一步占比用不同分母很正常，但要注明。

kernel 名称也不等于源码算子。一个 Python 操作可能调用多个 kernel，多个 Python 操作也可能被融合成一个 kernel。要借 NVTX 关联**语义区间**，再看实际 GPU 执行；不能看到名字包含 matmul 就认定所有 FLOPs 都在那里，更不能用调用次数代替时间。

### G2.2 FLOPs 少不代表快

一个点运算可能只有很少算术，却需读写大量字节、启动多个 kernel。矩阵乘法则可能重复利用片上数据并使用专门硬件。这里的关键不是“低 FLOP 算子必慢”，而是**不同操作的限制不同**。

独立的量纲检查：若一操作有 F 次浮点运算、实际移动 Q bytes，算术强度是 F/Q，单位 FLOP/byte。若设备有效算力为 C FLOP/s、有效带宽为 W bytes/s，则两个理想下界是 F/C 与 Q/W，单位都为秒。它们说明应查什么证据，不是预测精确 latency 的万能公式；launch、访存模式、并发与 occupancy 都可能拉开差距。

### G2.3 找重叠时要看消费者，不只看相交色块

在 DDP 中，你希望看到后面仍有 backward 计算时，前面已经产生的梯度在通信。观察通信条与计算条相交只是起点，还要确认最后 optimizer 没有提前读未完成的梯度。

在 FSDP 中，更重要的是某次 all-gather **完成时刻相对权重首次使用时刻**。没有明显空洞不一定代表安全，可能只是异步竞争尚未暴露；有 gap 也不一定都是通信，可能是 host 调度或编译。

保存截图时应让读者能识别模型阶段、rank / device、时间尺度及关键依赖。截一个没有坐标的放大色块不够支持“完全隐藏通信”的结论。

**自检：**增加回溯选项后模型整体慢了，能否断言该版本模型退化？

**答：**不能。先与相同 instrumentation 条件比较；profiler 开销和模型本身成本必须分开。

## G3．显存：区分所有权、生命周期和峰值

对应题 03–06、07、19、21、27；资源全账见 [ext04](#/c/stanford-cs336-2026/lec/ext04?v=notes)。

### G3.1 元素数是第一步，存活时间才决定峰值

独立教学张量 shape `[2,3,5]` 有 30 元素；FP32 数据载荷 120 bytes、BF16 为 60 bytes。这只数载荷，不包含 allocator 元数据、padding、其他引用或设备库 workspace。这里刻意不用题 05(d) 的 xl 配置，以保留你的推导任务。

在训练中，至少分开：

- 参数与可能存在的 FP32 master 副本；
- 当前梯度；
- optimizer 状态；
- backward 所需 saved tensors；
- 临时中间量、通信与 gather buffers；
- allocator 保留但暂未被活跃张量占用的空间。

峰值是这些项目**某个时刻同时存活**的和，不能把各项目各自历史最大值相加当真实峰值，也不能只看训练步结束的占用。optimizer 的状态可能直到第一次 step 才建立，所以“初始化后没有状态显存”并不反常。

### G3.2 saved tensor 事件不是唯一分配清单

`saved_tensors_hooks` 能告诉你 autograd 保存或取回了哪些 tensor 引用。相同 storage 的不同 view、同一张量多次被保存、参数与激活共享引用，都可能让逐事件 `numel×element_size` 的加和不同于 allocator 的独占字节。

因此有三种不同问题：

1. **反向依赖什么？**看保存事件、shape、grad_fn 与算子。
2. **实际分配了什么？**看 allocator snapshot、stack trace 与活跃区间。
3. **为什么峰值在这里？**把生命周期与当前阶段结合起来。

不要为让三者数值相等而删掉“多余项”。它们本来就在回答不同问题。fusion 可改变保存策略，但不能凭“事件减少了”直接宣称总 peak 按同倍率下降。

### G3.3 反向的净下降不是释放量

假设一个独立示例中某阶段释放了 100 个单位的 saved activations，同时产生 70 个单位的 gradients，其他内存不变，观察到的净变化是下降 30。你不能据下降 30 得出“只释放了 30”。这只是守恒账，不是题 05(f) 的实验答案。

真实 profile 还可能同时创建 workspace 或保留通信 buffer。推断梯度大小前，先找证据确认其他部分是否相对稳定；无法确认时就写假设，不给过度精确的解释。

### G3.4 混合精度不是把总显存除二

autocast 控制不同算子的运行 dtype，不一定永久改变模型参数存储，更不保证梯度、optimizer state、归约和所有 residuals 都半精度。必须逐项看实际 dtype 与存活时间。

FP16 的范围问题与 BF16 的有效位问题不同。“BF16 与 FP32 指数范围相同”不代表精确度相同，也不代表所有归约都可以安全降精度。累加到较大数时，小增量可能低于可表示间隔；先把低精度值转回 FP32，也不能恢复它此前已经丢掉的表示信息。题 03 要用实际输出解释这两种误差来源，本页不给四组结果。

题 04 的 loss dtype 还依赖 loss 算子与是否位于 autocast 区域。先确定运算，不要把“loss”这个变量名当作有固定 dtype 的 API。

### G3.5 OOM 也是一个有配置的观测

写清 OOM 出现在模型构造、forward、backward、optimizer、compile 还是 gather。记录 shape、dtype、已分配/保留状态和是否有上一次失败遗留引用。缺少这些信息，“这个模型放不下”只是不可复现的口号。

不要静默缩小 batch、截短 sequence 或关闭 causal 来让结果表好看。可以另建缩小的机制实验，但原要求的该行应保留 OOM / 未执行及原因。

**自检：**同一参数通过两个 module 名称可见，显存核算一定数两份吗？

**答：**不一定；名称不等于 storage。先确定是否为同一参数/共享存储，并区分真实复制和别名。

## G4．Checkpointing：不是“把激活删掉”

对应题 06。机制原理参考 [L06](#/c/stanford-cs336-2026/lec/lec06?v=notes)，这里不解最优 checkpoint 策略。

### G4.1 对重算提三个问题

checkpoint 能工作，因为反向需要的中间量可由保存的边界输入重建。讨论一个 checkpoint 区域时，应问：

- 边界保留了什么，保留多久？
- 反向重建时，哪些中间量会再次同时存活？
- 重建函数是否仍代表原来那次 forward？

最后一问涉及随机性、状态、副作用及 dtype。一个重算区域如果在第二次调用时观察到不同状态，不能只因 output shape 一样就认为梯度仍等价。检查逻辑时先从确定性、无副作用的机制入手，再明确正式模型中的状态管理。

### G4.2 前向结束的最低占用不是全步最低峰值

checkpoint 经常大幅减少前向结束时保存的激活，但 backward 会短暂恢复一部分内部 residuals。完整判断必须覆盖这个重建阶段。如果只截前向末尾，就会把短期内存从账中消失。

可以将峰值来源按“长期边界”和“短期重建”分类，但题 06 的最优分块、渐近计算量与嵌套策略要由你在官方假设下推导。特别注意：忽略 compute 的 (a) 与只允许一次重算、禁止嵌套的 (b) 是不同优化问题，不能拿同一个方案不加说明回答两问。

### G4.3 让相邻配置成为证据，而不是装饰

题 06(b) 明确要求比较所选 block size 的更小与更大邻居。其目的不是提交三张任意曲线，而是检验你声称的平衡点是否真的在附近。各配置要保持模型、dtype、batch、sequence、编译状态和测量区间一致，记录完整一步 peak。

手册单 block 示例使用 16 头，而 Table 1 xl 为 32 头。不要把示例打印的 MiB 数值当自己的标准 xl 实验。先写清采用的配置，再解释观察。

**自检：**checkpoint 版本的 forward 更省显存，足以说明它的整个训练步 peak 更低吗？

**答：**不够；还必须看反向重建、梯度与临时工作区同时存活的时刻。

## G5．FlashAttention：从形状合同到数值不变量

对应题 07–11 及选做 Triton backward。完整算法证据只在 [L06 论文材料](#/c/stanford-cs336-2026/lec/lec06?v=materials)，online-softmax 的原创数学小例在 [ext05](#/c/stanford-cs336-2026/lec/ext05?v=notes)；本页专注问题定位，不复制一套可提交算法。

### G5.1 先拆开四个层次

1. **数学 attention：**按正确缩放、mask 和归约轴计算。
2. **分 tile 的同一数学：**改变计算顺序，不改变目标值。
3. **Triton 内存访问：**程序负责的 tile、指针和 stride 与数学索引一致。
4. **autograd 合同：**前向保存反向真正需要的量，输出/梯度/非张量参数位置一致。

纯 PyTorch tiled 前向在本题中的价值是提供第 2 层的参考，不是要比库实现快。若 Triton 错了，先确定第 2 层是否正确；否则同时调数学与指针，会失去定位依据。

### G5.2 用形状检查区分轴错和精度误差

省略 batch 后，Q `[Nq,d]` 与 K `[Nk,d]` 对应 score `[Nq,Nk]`；softmax 沿 Nk；O `[Nq,d]`；L `[Nq]`。L 的一行对应一个 query 的 logsumexp。batch 不是额外的 key 归约轴。

独立教学检查：设 Nq=3、Nk=5、d=2，则 score 是 3×5，而 L 有 3 个值。这不属于官方“至少 16、2 次幂”的测试配置，仅用于纸上区分维度。若你得到 5 个 L，问题是轴，而不是 BF16 的微小误差。

同理 Bq×Bk 不必是正方形；文中“square mask”不能盖过实际维度。一个 tile 的局部索引 0…Bq−1 也不等于全局 query 位置；第二个 tile 开始才出现错误，经常提示应检查 index / offset 合同，而不是先扩大容差。

### G5.3 online 并不是每块独立 softmax 后相加

softmax 的分母跨完整 key 轴。不同 tile 的局部归一化结果若各自和为 1，直接拼接或相加并不是原 attention。在线计算的核心是不丢失跨块的共同归一化信息；running maximum 改变时，旧累计量也必须保持相同的数值尺度。

调试时可以观察“处理了哪些 key 后，本行累积量代表什么”，而不只看最终误差。这里的不变量解释见 ext05；A2 需要你自己把该不变量落实为 PyTorch/Triton 操作。

### G5.4 数值稳定与题目 mask 必须分开谈

原题 causal 指定有限值 **−1e6**，固定测试以它替换被屏蔽 score，而 handout 文字说加它；理想数学的 −∞ 是另一个概念。有限大负数是否完全排除某项，依赖其他数值与 dtype；极端输入下“加”和“替换”也不等价。

因此应同时保留两个层次：按固定题目和测试理解预期行为；在解释中注明有限 mask 的数值条件。不要因为数学讲义常用 −∞ 就悄悄改写官方要求，也不要把正常随机测试通过扩张为任意 score 范围下的严格恒等。

对于普通 causal self-attention，每个有效 query 至少有可见位置。若某行全被屏蔽或出现 NaN，先核对全局索引、包含对角线的约定和实际 shape。若设计额外的全屏蔽边界实验，明确那是自己的扩展，不是官方未明示的必做项。

### G5.5 autograd 接口里“计算 L”不等于“返回 L”

官方要求 forward 返回 O，并保存 L、Q、K、V、O 供 backward；测试从 saved tensors 查找唯一 `[batch,Nq]` 的 L。返回 `(O,L)` 会改变接口，即使两者数值都正确也不满足合同。

adapter 需要类对象；测试自行用 `.apply`。别把“函数能调用”和“符合 autograd.Function 测试入口”混为一谈。布尔 causal flag 也需跨 forward/backward 保持，但它不是需要梯度的浮点输入。

测试 tolerances 是 FP32/BF16 与执行次序的合理误差边界，不是遇到错误时自动放宽的许可证。更有用的是定位误差模式：只错 causal、只错第二个 batch、只错某个 tile、只有梯度错。每种模式都能收窄应检查的合同层次。

### G5.6 前向内存优势不能自动外推到整步

必做 backward 允许使用 regular PyTorch + compile 的重算公式，这与选做 tiled Triton backward 的实现空间不同。如果 profiler 看到完整 `[Nq,Nk]` 的临时张量，不能仅凭前向名为 FlashAttention 就否认它。

同理，完整模型还有 logits、MLP、optimizer 与通信缓冲。attention 前向快了，不代表所有阶段都按同倍率加速；避免将局部 speedup 直接当作排行榜成绩。

**自检：**仅在 `is_causal=True` 时梯度错误，而非 causal 前后向都正确，下一步最值得核对哪类合同？

**答：**前后向 mask 是否一致、causal flag 是否保存并被使用、全局 query/key 索引是否正确；先定位语义，不先扩大精度容差。

## G6．DDP：让多进程仍优化同一个目标

对应题 12–17；系统原理见 [L07](#/c/stanford-cs336-2026/lec/lec07?v=notes)，通信成本见 [ext07](#/c/stanford-cs336-2026/lec/ext07?v=notes)。

### G6.1 同一目标需要四种一致

- 起点一致：参数与 optimizer 状态。
- 数据合同一致：各 rank 拿到全局 batch 的哪一份，是否不重叠、权重是否一致。
- 梯度语义一致：局部 loss 是 mean 还是 sum，通信做 sum 还是 average。
- 更新依赖一致：梯度归约结果可用后才更新，各 rank 用同一更新规则。

独立例：一个 rank 有 2 个样本，另一个有 6 个样本。若各算局部 mean，再简单平均两 rank，两个样本组权重各一半，并不等于八个样本等权。A2 的等分 batch 条件避免了这个问题，但报告不能因此忽略 global / local batch 和 reduction 的定义。

验证时比较**同一个全局目标的单进程基线**比“各 rank 彼此一致”更强：所有 rank 也可能一起少除一次或多除一次 world size，彼此相同却优化错误。

### G6.2 参数名、参数对象与梯度就绪不同

tied weights 可能在网络中用多次，但本质上是同一参数。某次局部梯度贡献出现，不代表其所有使用位置的贡献都已累计完。官方指出 `register_post_accumulate_grad_hook`，就是让你关注累计完成的语义，而不是只抓最早出现的梯度片段。

不可训练参数则没有普通梯度路径，但仍可能属于模型状态。固定测试含冻结参数和 shared weights，不能把“每个 named module 各有一个独立可训练张量”当隐藏假设。

这里只提示你要证明的对象，不给 hook 注册与去重方案。实现细节由你自己完成，并用多步比较观察状态是否持续一致。

### G6.3 collective 顺序是一份分布式合同

同一组中的参与者须以兼容的次序、shape、dtype 和调用集合进入 collective。一个 rank 因本地条件跳过某参数通信，而其他 rank 继续，不一定产生清楚的 shape 错误，也可能挂住或在后面才报异常。

遇到 hang，先用每 rank 的“最近到达的语义阶段”定位谁没到场；日志顺序本身不保证真实全局先后。不要靠添加随意 sleep 来“修复”顺序：那通常只是改变竞态暴露概率。

Gloo 能帮助检查多进程逻辑，但 NCCL 的 stream 与设备绑定是另一层；CPU 成功后仍需真实 GPU 依赖证据，不能跳过。

### G6.4 flatten 与 overlap 改的是不同成本

把全部梯度合并，主要改变 collective 次数与消息大小，同时可能增加拼接/恢复或额外 buffer 成本。逐参数重叠则改变通信开始时刻，目标是利用仍在继续的 backward 时间。一个方案降低总通信工作，另一个方案可能只是降低关键路径上的暴露部分；不要混为同一效果。

独立理想例：计算区间 8 个时间单位、通信区间 3 个，串行是 11，完全重叠的理想下界是 8；不是通信从 3 变成 0。真实网络可能争用设备资源，故这只是时间线账，不是性能保证。

题 17 的截图需要把这个区别可视化。代码中存在 async 标志不是重叠的充分证据；若所有 gradient 都到 backward 结束才提交，再异步也没有可隐藏的前面计算。

**自检：**所有 rank 参数相同，但与单进程全局 batch 基线不同，说明广播正确就够了吗？

**答：**不够。应检查全局目标、loss reduction、梯度平均和更新语义；“彼此相同”与“结果正确”是两个命题。

## G7．优化器分片与 FSDP：谁拥有可更新状态

对应题 18–21。ZeRO 的论文推导只在 [L08 材料](#/c/stanford-cs336-2026/lec/lec08?v=materials)；恢复问题见 [ext08](#/c/stanford-cs336-2026/lec/ext08?v=notes)。

### G7.1 状态分片先问更新权，而非先问广播

优化器状态与其负责的参数更新绑定。在简化 optimizer sharding 中，每 rank 仍有模型副本，但只有一部分参数的 optimizer state 由本地负责；更新之后，需要让其他模型副本看见新值。

检查的概念问题包括：每个需要更新的参数是否恰有合法 owner？非 owner 是否误创建状态？param groups 的学习率等超参数是否保留？训练期间新增组是否仍有定义？closure / step 的 API 是否仍符合被包裹 optimizer 的合同？

固定测试通过不自动覆盖所有公共 API，尤其 `add_param_group` 是 handout 明确要求，不得因测试恰好只传参数 iterable 就删掉。

题 19(c) 要比较本方案与 ZeRO stage1，不能因为二者都“分片 optimizer”就断言通信完全一样。带着**状态是否复制、梯度如何归约、更新值如何发布**三张账去读论文，自己的 2–3 句比较应来自具体证据，而不是引用名称。

### G7.2 FSDP 的“完整权重”通常是临时物化结果

FSDP 常驻的权重 shard 与为某层运算 gather 的完整权重，拥有不同生命周期。你应能回答：

- optimizer 看见的是哪份 FP32 master 参数？
- forward/backward 使用的是哪份 compute dtype 完整权重？
- 完整权重何时不再需要、是否真的释放引用？
- reduce-scatter 后的梯度形状是否对应本地 shard？

如果把完整权重一直保留，就可能保留正确数值却失去题目要证明的内存性质；如果释放太早，autograd 仍需要它时会产生错误或重新分配。将两份存储都称作“weight”会掩盖这类问题。

### G7.3 prefetch 有显存预算，不是越早越好

手册要求：某层的 gather 只能在其前面第 2 层完成 forward 后开始。这是给预取窗口设界限，让通信尽量提前、又不把所有完整权重同时放进显存。

考察一个 schedule 不必先优化它，可以先写出每份临时权重的“允许开始、必须完成、最后使用、可以释放”四个时刻，再看实际 trace 是否符合。这里不给排程代码或 hook 方案；这四个语义标签用于你解释自己的实现。

当 all-gather 没赶上当前层计算，应先分清传输真的太慢、启动太晚，还是依赖阻止其运行。不能只把预取深度无限扩大，因为这会违反题目的窗口及峰值目标。

### G7.4 混合精度的通信位置会改变带宽账

A2 要求给定 compute_dtype 时在通信前转换，master weights 与更新保留 FP32。若先传 FP32 再转 BF16/FP16，可能数值正确，却没有满足指定的通信策略。

同步后的 gradient 还要与 optimizer 所见 master 参数的 shape / dtype 兼容。固定测试覆盖 `compute_dtype=None` 与 FP16，检查这一接口；正式排行榜 BF16 又是另一配置，不能用 FP16 测试代替 BF16 性能证据。

复制的小层不等于“不参与分布式训练”。norm 虽不分片，其 gradient 仍代表各 rank 数据的一部分，必须保持正确的全局语义。一个实现如果只处理 Linear / Embedding 而完全遗忘复制参数，可以在主要大矩阵看似正确时持续漂移。

### G7.5 理论省下的 bytes 与实测 peak 不应强行一致

题 21(a) 允许忽略 all-gather 预分配 buffers，是纸笔模型的明确假设。真实 profile 不会替你忽略它们；双缓冲、预取窗口、临时完整权重、通信 workspace 都可能抵消部分理论节省。

写解释时先用同一口径分解，再说明差额来自哪个已观察的生命周期。不要把所有差额归为“框架开销”却不给 trace / snapshot 依据。

**自检：**FP32 master 和 BF16 compute 权重都存在，参数显存能否只算其中一个？

**答：**若它们是同时存活的不同 storage，就都要算；是否常驻与是否在峰值时共存决定统计口径。

## G8．并行计算题：先做单位和轴的审校

对应题 22–26；不在这里提供计分表达式、最优 N 或 TP backward 方程。深入原理见 [L07](#/c/stanford-cs336-2026/lec/lec07?v=notes)、[L08](#/c/stanford-cs336-2026/lec/lec08?v=notes) 与 [ext07](#/c/stanford-cs336-2026/lec/ext07?v=notes)。

### G8.1 用四列表拆开每个阶段

在自己的纸上，对每个矩阵乘法或 collective 写四列：输入的**本地 shape**、输出的**本地 shape**、沿哪个轴归约、最终由谁拥有。shape 不清时不要直接写通信时间。

常见混淆是把全局 B 当 local B，或把参数 shard 大小当 all-gather 的完整 S。DP 切 batch，TP 切特征/权重轴，FSDP 同时改变常驻权重所有权；相同 N 因切的轴不同，不意味着每个 tensor 都缩小 N 倍。

在 TP 中，本地同 shape 输出可能是“不同特征片”或“同位置的不同部分和”。前者拼接、后者求和的语义不同。这不是由 shape 自动决定，要回到对应的矩阵乘法收缩轴。

### G8.2 FLOPs 不是 FLOP/s

独立教学 matmul `[7,11]×[11,13]` 按 2abc 口径有 2002 FLOPs；除以设备有效 FLOP/s 才得到秒。这个小例不属于 A2 FFN 的计分配置。

通信也一样：元素数乘 bytes/element 得到 byte；每 rank 发送的 byte 除该 rank 出站 bytes/s 才得到秒。全局总发送量用于网络总工作量，而不能直接除单卡 W 假装 wall-clock。

原题所有权重和激活均 FP16，是分析假设，不是“所有实际系统梯度必须 FP16”的宣言。现实 FSDP 的 FP32 master / 混合 dtype 账与 §8 理想题设要分开。

### G8.3 让极限情形暴露错误

不代入官方要你求的最终答案，也能审校推导：

- N=1 时，应没有跨设备通信成本。
- 若某式代表设备计算时间，单位应为秒，而不是 byte 或 FLOP。
- 如果增加设备减少 local 工作量，却没有改变全局目标，检查你是否误把每卡量又乘了一次 world size。
- 若 FSDP backward 的通信列表没有重新 gather，检查是否无声假设完整权重一直保留；那不是本节题设。
- 若 all-reduce 推导只包含一个 reduce-scatter 阶段，检查各 rank 是否真的拿到了完整结果。

这些是结构自检，不保证你的系数正确；每个系数仍需回到操作清单逐项论证。

### G8.4 2D 的 max 与 sum 来自资源假设

两个通信轴若可独立同时推进，理想完成时间由更长的一条决定；若共享同一瓶颈资源、不能重叠，两个成本不能再无条件取 max。题 26 专门让你分别优化这两种情况。

这不是代数技巧，而是系统假设。不要把 (b)/(c) 的独立网络假设带进 (d)，也不要擅自把所有通信强制串行来回答允许重叠的子问。理论中的 max 还不代表真实硬件一定具有独立链路，需要拓扑和 trace 才能确认。

### G8.5 数学上连续的设备数与实际配置不同

题 26(d) 明确不用整数截断，是连续优化问题。现实部署还需整数 rank、维度可分、拓扑匹配和进程组安排。纸笔上限应写出原假设，不把它包装为“在某集群上一定能扩到这么多卡”。

**自检：**全局发送总量除以单卡带宽得到了很大的时间，这个式子一定代表通信 wall-clock 吗？

**答：**不是。并行发送时应先明确每卡负载、关键链路及资源并发；全局 wire bytes 与单卡时间是不同口径。

## G9．排行榜：完整工作量与冷启动是双重合同

对应题 27。完整配置不在此复制，见实验说明第 8 节；本页不提供优化组合或调参答案。

### G9.1 最小的有效结论也必须覆盖完整一步

官方计时包括清梯度、forward、loss、backward、AdamW。省掉 loss、用无更新的 optimizer 占位、只测 attention、以 inference mode 替代训练，都会改变问题。模型随机初始化和随机输入是允许的，但不能因此跳过数值等价与梯度语义。

所谓“保持 I/O 行为”还需要理解 reduction：官方 timing 示例用 cross-entropy 后 sum。把 sum 变为 mean 会改变梯度尺度，即使 logits 一样；冻结部分参数或改变 causal 也不是纯系统优化。

### G9.2 最快数字应附一份可复现合同

正式记录至少说明：模型配置未改变；两 B200；BF16 causal；随机输入如何准备；哪部分在计时区间；rep=30000 ms 与 warmup=10000 ms；空缓存起算总 run 是否在 10 min 内；编译/autotune 假设；代码快照和依赖锁。

这两个 do_bench 数值是时间预算而不是次数。若开发时缩短了，标明开发测量，不能直接当官方最终结果。冷启动 cache 不只是一句“第一次运行”，还需清楚说明是哪种 PyTorch/Triton 缓存状态。

榜单 PR 与 Gradescope 是两条交付链；非 Stanford 学生须按独立 global 表及维护者验证规则提交。任何不能复现的领先结果都不是完成证据。本站没有执行或提交记录。

### G9.3 性能提升不要只讲故事

一个优化解释可以简洁，但应连上可观察证据：工作量有没有保持，peak 在何处变化，kernel / communication 的关键路径如何变化，端到端收益是否与局部变化相符。

若 attention latency 降了一半、完整 step 却几乎没变，首先看 attention 原本占总时间的比例及新瓶颈，而不是编造“测量噪声”。若降低显存却更慢，也可能是合法的计算换内存，需对照目标而非一概判错。

## G10．交付前的证据审阅，不是代做检查清单

本页没有运行任何下列工作。它们是读者/主审在自己的成果上应核对的事项：

| 范围 | 不能少的证据 | 不能替代它的东西 |
|---|---|---|
| benchmark / mixed precision | 全配置、测量边界、均值/波动与 dtype 观察 | 网上硬件峰值 |
| profiler / memory | 原始 trace / snapshot、要求截图、分配来源 | 示意图或理论显存 |
| checkpointing | 对应预算的推导、完整步 peak、相邻块大小 | 只看 forward 末尾 |
| FA2 | O/L/梯度、causal、两条 adapter 路径、真实 B200 表 | CUDA skip 或仅 forward 正确 |
| DDP | 单进程等价、多步、共享/冻结参数、重叠截图 | rank 彼此一样或 async 标志 |
| optimizer sharding | 参数组/step 合同、状态账、时序与 ZeRO 比较 | 只看参数最终相同 |
| FSDP | gather/release/grad shape-dtype、复制参数同步、预取窗口 | 只调用了 all-gather |
| DP / FSDP / TP / 2D | 所有子问、变量/单位/每卡口径、假设 | 仅写最终不等式 |
| leaderboard | 完整 step、两 B200、冷缓存 ≤10 min、复现快照 | attention 微基准或估算成绩 |

证据最好让另一个人可以从“结论”退回“配置和原始观测”。编译器、框架和硬件都会变化，六个月后仍可信的不是某个漂亮数字，而是你明确了自己当时测的是什么。

## 来源与完整许可

本指导为编者原创教学组织，依据 [固定 A2 handout 与仓库](https://github.com/stanford-cs336/assignment2-systems/tree/ca8bc81a59b70516f7ebb2da4808daade877c736) 的任务语义、实际 adapters / tests 与 [官方 AI 政策](https://docs.google.com/document/d/1SZAlExB1qAc9izHt54gwunNpjKE6wXb8Y7yA_e-baK8/edit) 确定边界；实际全读范围、版本与哈希见 `sources/p4-a2/manifest-fragment.json` 和 `review.txt`。本文没有使用外部答案或现成作业实现，没有推定 GPU 性能。原创 SVG 只表达证据关系，不是课堂截图或 profiler 截图。

政策/资源导航：[官方课程](https://cs336.stanford.edu/)、[集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit)、[排行榜固定 README](https://github.com/stanford-cs336/assignment2-systems-leaderboard/blob/df82f2f05c43273096bedffced4d7a035bcbf1fc/README.md)。这些独立页面不自动继承作业仓库 MIT；仅作有限独立归纳。FlashAttention / FA2 / ZeRO 的版本和第三方权利分别保留在 [L06 材料](#/c/stanford-cs336-2026/lec/lec06?v=materials)、[L08 材料](#/c/stanford-cs336-2026/lec/lec08?v=materials)，没有在此复制第三方插图或翻译全文。

第一方要求中保留的概念和接口说明，适用以下原仓库完整 MIT 声明；中文组织、示例与调试问题为本站修改，非官方解答：

> Copyright 2025 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
