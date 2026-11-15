---
title: A2 硬件与训练系统：完整实验说明
kind: 固定 2026 官方第一方要求的中文重述；不是解答或可提交实现
source: CS336 Assignment 2 (systems), Spring 2026, Version 26.1.3
source_commit: ca8bc81a59b70516f7ebb2da4808daade877c736
source_read_scope: 全部 48 页提取文本；README、LICENSE、pyproject、CHANGELOG 与固定测试接口全文；未逐页视觉审校
status: P4 完整说明；27 个计分 Problem 及全部子问；文档完整不表示实验完成
execution: 未执行官方代码、测试、GPU benchmark、训练、付费计算或依赖安装
license: 第一方软件与相关文档按 MIT 使用；完整版权与许可见页底；第三方材料另计
---

# A2 要交付什么

A2 的主线不是“把 attention 跑快一点”，而是先建立可信的时间与显存证据，再用重算、kernel 和分布式执行改变完整训练步的成本。你要自行完成性能测量工具、activation checkpointing、FlashAttention-2、DDP、优化器状态分片与 FSDP，并分析 DP / FSDP / TP / 2D 并行的边界，最后测量两块 B200 上的 **8B-shaped 完整训练步**。

本页保留固定版 **27 个计分 Problem 的所有要求、字母子问、分值、配置和交付物**；不代写实现、计分题答案或排行榜方案。概念与证据排查见 [A2 指导](#/c/stanford-cs336-2026/lab/a2-systems?v=guide)。原文页码均为 PDF 印刷页码；这里的“测试”“提交”是读者的待完成合同，不是本站执行记录。

## 0．版本、政策、硬件与公共配置

### 0.1 固定版本与工作目录

以页底固定提交的 **Spring 2026 / PDF v26.1.3 / 48 页**为准。外层 `cs336-systems` 包为 **26.1.4**，内含 `cs336-basics` 包为 **26.0.4**；包版号不能替代 PDF 版号。CHANGELOG 26.0.0 新增 activation checkpointing 和 FSDP、将排行榜改成双 B200 完整训练步、移除 bucketed DDP；26.1.3 修订双遍后向的记号，26.1.4 放宽分片测试的前导维度选择。不要用 2025 H100 attention 排行榜或 bucketed DDP 任务替换本页要求。

- `cs336-basics/` 提供课程 staff 的 A1 基础模型，可直接导入；也允许换成自己的 A1 实现，修改外层依赖路径。
- `cs336_systems/` 是自己的系统实现所在模块；`tests/adapters.py` 接通测试要求的入口。
- 可以增加调试测试，但最后必须满足**原始提供测试**，不能靠修改断言“通过”。
- README 使用 `uv`。固定依赖要求 Python `>=3.12,<3.14`、PyTorch `~=2.11.0`；`uv run` 可能准备环境和下载依赖，不是无副作用的版本查询。本文没有安装或兼容性通过记录。

### 0.2 AI、现成代码与提交规则

官方 AI 政策允许高层概念与底层 API / 函数签名查询，**禁止 AI 实现任何作业部分，包括排行榜、实验脚本、coding agent 和 AI 自动补全**。仓库 AGENTS.md 进一步要求不给 Python、伪代码或计分题直接解答；本页因此仅解释要求、API 合同与验证思路。不要修改官方 AGENTS.md；在线聊天按政策带上它，关闭 AI 自动补全。现成第三方实现不得查阅或复制，除非 handout 明确允许；课程自带基础模型是明确许可的起点。学习小组仍须各自理解和完成，按官网注明成员。

Gradescope 交排版后的 `writeup.pdf`（全部书面题）与自己的代码包 `code.zip`。handout 指向 `test_and_make_submission.sh`。**固定脚本实际产生名字含 spring2024 的 zip**，README 却称 gzipped tarball；这是旧命名/描述残留，不是本作业变成 2024。脚本还会在测试失败后继续打包，且排除 `.txt/.json/.pickle/.pt` 等文件，因此“生成包”不是测试通过，也不能假定原始性能证据自动包含在包中。按课程平台的实际文件要求交付，保存测试报告与独立结果证据。

### 0.3 硬件与可达范围

官方允许先在 CPU 检查正确性，分布式可先用 **Gloo 多进程**。但 CPU/Gloo 只能证明机制，不替代 CUDA/Triton kernel、NCCL 多 GPU 性能或 Nsight GPU trace；Apple MPS 也不是等效后端。Triton 的 `TRITON_INTERPRET=1` 被 handout 明确警告为 buggy，不能当可靠通用替代。

- FA2 基准：**单块 B200**；完整训练排行榜：**两块 B200**。
- all-reduce 测量：2 / 4 / 6 GPU 或进程设置，最高 6 GPU；每次 benchmark run 应小于 5 分钟。
- 多项 xl DDP、优化器分片、FSDP 性能题：单节点双 GPU。
- 校内 Modal workspace 仅正式选课学生，须 Stanford Google 登录、邀请和个人环境；公开账号不等于获得课程资源。通用指南建议同时不超过 3 GPU，而题目要求有 6 GPU 设置，应向 staff 协调，不擅自缩题或声称已获配额。
- 没有官方统一 CPU 核数、主机 RAM 最低值，也没有“某个显存容量保证全题可跑”的承诺；naive attention 的部分设置本来就可能 OOM。
- 性能题允许随机权重、随机 batch，**无需下载预训练 8B checkpoint**。本次没有申请、购买或启动任何算力。

共享环境与访问入口见[课程资料](#/c/stanford-cs336-2026)。缺 GPU 时，书面分析和 CPU 机制工作应单独标注；缺测量项留“未执行”，不能填估算值冒充测量。

### 0.4 全局模型配置（§2.1.2，pp.2–3）

除排行榜及后文明确覆盖项，词表 **10,000**、batch **4**、默认 context **512**。

| 名称 | d_model | d_ff | 层数 | 头数 |
|---|---:|---:|---:|---:|
| small | 768 | 3072 | 12 | 12 |
| medium | 1024 | 4096 | 24 | 16 |
| large | 1280 | 5120 | 36 | 20 |
| xl | 2560 | 10240 | 32 | 32 |
| 10B | 4608 | 12288 | 50 | 36 |

建议由结果表自动生成论文表格，避免手工转录。分布式报告另写清 global batch 与 per-rank batch；不要把全局 batch 4 偷换成每卡 4。

## 1．端到端计时、计算与显存（§2）

### 01 · benchmarking_script（4 分；pp.3–4）

- **(a)** 写端到端脚本：按给定超参数初始化基础 Transformer；生成随机 batch；先运行可配置的 **w 次 warm-up**，再测 **n 步**。参数须选择三种模式：仅 forward、forward + backward、forward + backward + optimizer step。可以用 `timeit` 或 `timeit.default_timer()`；每一步后调用 `torch.cuda.synchronize()`。**交付：**支持全部三种模式与配置的脚本。
- **(b)** 测 0.4 所有模型大小的 forward、backward、optimizer step。固定 **5 步预热 + 10 步测量**，报告均值和标准差；回答 forward / backward 多久、波动是否显著。**交付：**计时数据与 1–2 句回答。
- **(c)** 改成无预热重复分析，解释变化，再试 1 或 2 步预热并解释为何仍可能不同。**交付：**2–3 句。

CUDA 调用异步返回；CPU 调用耗时不能直接当 GPU 完成耗时。计时区域应清楚区分初始化、预热和测量，不能把异步派发误当执行。

### 02 · nsys_profile（5 分；pp.4–6）

使用 Nsight Systems 分析 forward、backward 和 optimizer。选 Table 1 中 **两种模型大小**，以及 **三个大于 128 的 2 次幂 context 长度**；最大长度应为能放进显存的最长值。选有信息量的组合，对每份 profile 回答：

- **(a)** forward 总时间多少，与 Python 计时相符吗？交 1–2 句。
- **(b)** forward 中累计 GPU 时间最长的是哪个 CUDA kernel？单次 forward 调用几次？加入 backward 后是否还是它？交 1–2 句。
- **(c)** 除矩阵乘法，还有哪些 kernel 占用不可忽略的 forward 时间？交 1–2 句。
- **(d)** 用自己的 AdamW profile **forward → loss → backward → optimizer** 完整一步。矩阵乘法时间占比相对仅 forward 如何变化？其他 kernel 呢？交 1–2 句。
- **(e)** 比较 self-attention 中 softmax 与矩阵乘法的运行时间，时间差与 FLOP 差是否一致？交 1–2 句。

工具合同：通过 `nsys profile` 包裹原脚本；在本机 Nsight 桌面应用查看报告，以 CPU CUDA API 与 GPU kernel 对应关系定位工作。可记录 cuda/cudnn/cublas/osrt/nvtx、PyTorch function / autograd 标签、回溯与 GPU utilization。trace 本身会减速，尤其回溯，不应无条件把所有选项打开。使用 NVTX 范围及 `--nvtx-capture` **排除预热**，分别标记 forward、backward 和 attention 子操作；查看 CUDA GPU Kernel Summary / Stats System View。`torch.compile` 可能改变归因粒度，应说明测量时的编译及标签边界。

### 03 · mixed_precision_accumulation（1 分；pp.7–8）

运行原题的四组累加实验并评论精度：每组从标量 0 开始，循环 **1000 次**，每次加 **0.01**。四组分别为 FP32 累加器 + FP32 加数；FP16 累加器 + FP16 加数；FP32 累加器 + FP16 加数；先将 FP16 加数显式转成 FP32 再加到 FP32 累加器。**交付：**基于真实运行结果的 2–3 句回答。本页不提供结果数字。

### 04 · benchmarking_mixed_precision（2 分；pp.8–9）

- **(a)** 原题 ToyModel 的结构是：无 bias Linear 从 `in_features` 到 10 → ReLU → LayerNorm(10) → 无 bias Linear 从 10 到 `out_features`。GPU 上初始参数 FP32、autocast 选择 FP16。分别给出 autocast 内**参数、第一层 Linear 输出、LayerNorm 输出、最终 logits、loss、梯度**的 dtype。**交付：**六项 dtype。题面没有定义 loss 函数，答复应陈明自己所依据的 loss 运算与 autocast 规则，而不是把所有 loss 一概而论。
- **(b)** LayerNorm 哪些部分对混合精度敏感？换 BF16 后还需要区别对待吗、为什么？交 2–3 句。
- **(c)** 让 benchmark 可选 BF16 混合精度；对 Table 1 所有模型大小比较启用/禁用时的 forward 和 backward 时间，讨论随模型大小变化的趋势。可参考 `nullcontext` 管理禁用分支。交计时与 2–3 句解释。

混合精度不是把一切永久转成低精度；autocast 对算子选 dtype，累加/归约的精度选择要独立观察。原文 B200 吞吐数字用于动机说明，不是保证实际 kernel 或整模型达到峰值。

### 05 · memory_profiling（4 分；pp.9–10）

使用 Table 1 **xl**，context **128 和 2048**，覆盖完整训练步。

- **(a)** 增加 memory profiler 选项，记录 xl 仅 forward 与完整一步的显存时间轴，判断峰形与阶段关系。**交付：**来自 PyTorch memory_viz 的两张 Active memory timeline 图：forward、完整一步各一张，加 2–3 句。
- **(b)** 两种 context 下，forward 峰值、完整一步峰值分别多少？**交付：**每个 context 两个数字的表。
- **(c)** 再测混合精度下 xl 的 forward 与完整一步峰值，是否显著变化？交 2–3 句。
- **(d)** 按参考超参数，推导 xl residual stream 的单个 FP32 激活张量大小，以 **MiB = bytes / 1024²** 表示。交推导和 1–2 句。
- **(e)** 在 forward Active memory timeline 降低 Detail，找到最大分配尺寸，并用 stack trace 判断来源。交 1–2 句。
- **(f)** 使用 Nsight 内存标记与 PyTorch NVTX 标签，测量**单个 TransformerBlock 为 backward 保存的 tensors / residuals**；列出五个最大贡献算子及其占总量百分比。backward 同时释放 saved tensors 和产生 gradients；结合 forward 分配量与 backward 每 block 的净变化，估计该 block 产生的梯度张量内存并与预期比较。**交付：**Nsight 截图与 1–2 段回答。

官方记录流程为预热后开启 `torch.cuda.memory` 命名空间的 `_record_memory_history`，参数设为 `max_entries=1000000`；在目标区域结束后调用 `_dump_snapshot`，再关闭记录；将 snapshot 拖入 [memory_viz](https://pytorch.org/memory_viz)。API 属带下划线的工具入口，按固定环境核对，不把 snapshot 文件误当普通文本或把缓存保留量等同活跃张量量。

## 2．单卡重算（§3，pp.10–15）

### 2.1 要理解和观察的非计分前置

用 `torch.autograd.graph.saved_tensors_hooks` 观察 autograd 保存/取回的 shape、dtype、grad_fn；原例是 FP32 RMSNorm，输入 `[4,512,2560]`。融合前后对照说明 saved tensors 数量不等于算子数量，也不等于唯一 storage 分配量。`torch.compile` 融合 RMSNorm 是观察工具，不是要求抄写其实现。

接着观察融合 TransformerBlock 与四个顺序 block：checkpoint 在前向保留输入、抑制内部保存，在反向重跑前向再反传。原示例使用 `use_reentrant=False`。长期存在的 checkpoint 与重算期间短期存在的 residuals 都影响峰值；仅记录前向结束的 saved bytes 不是 peak memory。

**原文配置差异须保留：**§3.2 p.12 的单 block 演示称 xl，但代码写 `num_heads=16`、context 2048；Table 1 的 xl 是 **32 头**。演示输出（如单 block 3651.31 MiB、四 block checkpoint 后前向保存 160 MiB）只是原文特定脚本结果，非本站测量，也不能不加说明地用作 Table 1 标准配置实测。

### 06 · gradient_checkpointing（4 分；p.15）

考虑顺序堆叠的 **N 个相同 Transformer blocks**，无 checkpoint 时同时保存 N 份 residuals，峰值 activation memory 为 O(N)。可以任意包裹、嵌套 checkpoint。

- **(a)** **忽略计算代价**，什么策略最小化峰值 activation memory？说明 checkpoint 如何安排，给出随 N 变化的渐近峰值内存与计算量；假设单 block residuals 比每个 checkpoint 的 bookkeeping 占主导。**交付：**3–5 句说明、渐近量与自己写的短代码草图。本页不提供草图或最优解。
- **(b)** 使用 **xl、batch 4、sequence 2048**。若预算只允许一遍重算、**不可嵌套 checkpoint**，怎样选择最优分块降低峰值？用 profile 验证，并比较相邻的更小、更大 checkpoint block size。**交付：**3–5 句推理及测得峰值。记录采用 Table 1 还是复现 §3.2 演示的头数，不能无声混用。

## 3．Attention 与 GPU kernel（§4）

### 07 · pytorch_attention（2 分；p.16）

只有 **(a)**，其中六项均须保留：

1. batch 固定 **8**，去掉 multihead 的 head 维。
2. 扫描笛卡尔积：head embedding dimension **16、32、64、128**；sequence length **256、1024、4096、8192、16384**。原题把此维写为 d_model，这里明确它是本题无 head 维 attention 的特征维。
3. 生成相应尺寸的随机 Q、K、V。
4. 计时 **100 次 forward**。
5. 测量 backward 开始前使用的内存，计时 **100 次 backward**。
6. 做预热，每次 forward / backward 后同步 CUDA。

报告所有设置的时间或 OOM；指出开始 OOM 的尺寸，从遇到的较小 OOM 配置中选一个做 attention 内存核算；解释 saved-for-backward 内存如何随序列变化，并提出消除此成本的方向。**交付：**计时表、内存计算、1–2 段回答。OOM 是原题预期的一类真实结果，不应伪造一项时延补齐表格。

### 08 · torch_compile（2 分；pp.16–17）

- **(a)** attention benchmark 加上 `torch.compile` 版本，按题 07 的**同一配置集合**与未编译版本比较。交 forward / backward 时间对照表。
- **(b)** 编译完整 Transformer，比较 forward、合并 forward + backward + optimizer step 的性能。交 vanilla / compiled 模型对照表。

编译可能融合点操作，但不会自动证明实现具有 FlashAttention 的内存布局和渐近存储性质。编译代价与稳态耗时分开记录。

### 3.1 Triton 前置与共同 attention 合同（§4.2.1–4.2.2，pp.17–25）

weighted-sum 教学例不是新增计分题。它说明：Triton program instance 处理一个 tile；用 pointer、shape、stride、offset、block_shape、order 指定访问；tile 尺寸为编译期常量；launch grid 决定 program 索引；显式 load/store、边界检查、advance 与局部归约；用 `autograd.Function` 连接 PyTorch，反向参数次序对应前向输入。示例的跨 tile 权重梯度需要进一步归约。本页不复制课程代码或生成实现。

本题 attention 的语义是缩放的 QKᵀ、适当 mask、沿 key 维 softmax，再乘 V。省略 batch 时：Q 为 `[Nq,d]`，K/V 为 `[Nk,d]`，O 为 `[Nq,d]`，L 为 `[Nq]`。L 是逐 query 的 score **logsumexp**，不是 softmax 值或其和。Algorithm 1 沿 query/key 两轴分 tile，不分 hidden d；逐 query tile 维护 FP32 的 running maximum、归一化和与未归一化输出，最终写 O 和 L。具体算法以固定原文 pp.24–25 为准；数学解释在 [FlashAttention 专题](#/c/stanford-cs336-2026/lec/ext05?v=notes)，论文论断与版本在 [L06 论文材料](#/c/stanford-cs336-2026/lec/lec06?v=materials)。

官方强烈推荐原始 FlashAttention，并推荐 FA2 取得直觉；这不是“所有引用论文全文强制必读”。原文还推荐 online normalizer 与 GPU 性能文章。本页不转译第三方论文全文或插图。

### 09 · flash_forward（15 分；pp.26–27）

- **(a) 纯 PyTorch：**写 `torch.autograd.Function` 子类，用普通 PyTorch、**不用 Triton**实现 Algorithm 1 前向。输入 Q/K/V 与可选 `is_causal=False`；此子问可暂忽略 causal。计算 O 和 L，**通过 context 保存 L、Q、K、V、O，但函数只返回 O**。forward 的首参为 ctx；中间开发阶段 backward 可暂抛未实现异常，最终仍须完成题 10。tile 至少 **16×16**，官方测试维度为至少 16 的 2 次幂，题面称无需担心越界；自行选 tile 时仍须尊重实际尺寸。**交付：**子类；通过第9节接口总表中的 PyTorch FA2 adapter 接入，adapter 返回**类对象**，不是实例或 `.apply`；测试筛选 `test_flash_forward_pass_pytorch`。
- **(b) Triton：**另写子类，以单个 fused Triton kernel 调用 Algorithm 1。launch grid 为 **(Tq, batch_size)**；一个 program 只处理一个 batch 和一个 query tile，内层只有遍历 key tiles 的循环，循环末尾推进 block pointers。按原文提供的 kernel 接口传 Q/K/V/O/L 指针、每个张量各轴 stride、N_QUERIES/N_KEYS、scale，以及编译期 D、Q_TILE_SIZE、K_TILE_SIZE；scale 为 1/√d。片上 O、l、m buffer 使用 FP32；矩阵乘法可用 `tl.dot` 的 acc；P̃ 在乘 V 前转为 V 的 dtype，O 写回前转为输出 dtype。可逐 tile 对照 (a) 调试。**交付：**Triton 前向子类；测试筛选 `test_flash_forward_pass_triton`。
- **(c) causal：**autograd 函数最后增加布尔参数，**默认 False**；Triton 对应参数必须注解 `is_causal: tl.constexpr`。构造 query / key 的索引向量，形成 **Bq×Bk** mask，比较真实序列位置；对屏蔽位置，原文指定给 score **加 −1e6**，并以 `ctx.is_causal` 保存标志用于 backward。**交付：**含可选 causal 的 Triton 前向，旧非 causal 测试仍通过。

**固定源码校正：**handout (b) 写 `get_flash_autograd_function_triton`，实际入口为第9节接口总表中的 **Triton FA2 adapter**，名称比题面多了 `attention`。测试会从 saved tensors 找到唯一一个 `[batch,Nq]` 的 L，并比较 O/L；Triton 前向覆盖 causal False/True，缺 CUDA 时测试会 skip，skip 不等于通过 GPU 验收。

**mask 数值边界：**上述 −1e6 是原题具体合同；固定参考测试用“替换为 −1e6”，题面文字用“加 −1e6”。两者在任意极端输入下并非数学恒等，也都不等同普遍意义的 −∞ mask。正常随机测试下按误差容限比较；不要把数值 caveat 改写成另一套题目要求。官方文本称其为 square mask，但 Bq 与 Bk 不必相等，真实 shape 是 Bq×Bk。

### 10 · flash_backward（5 分；p.28）

**必做后向是 PyTorch + `torch.compile`，不是强制 Triton。**给自己的 FlashAttention autograd 函数补全后向：接收 Q、K、V、O、dO、L，计算并使用 D 向量，以原文式 (13)–(19) 的重算关系返回 dQ、dK、dV。causal 前后向语义必须一致，布尔输入不是可微张量。**交付：**后向实现，测试筛选 `test_flash_backward`，包括纯 PyTorch及 Triton-wrapper 路径。

adapter docstring 对 Triton 类称前后向均用 custom kernel，但不能据此把明确的必做 PyTorch 后向升级为强制 Triton 后向；手册 §4.2.3 明确选做。必做编译后向也不自动保证整个图始终具有 tiled 前向的峰值内存优势，须真实测量。

### 11 · flash_benchmarking（5 分；p.28）

只有 **(a)**：用 `triton.testing.do_bench` 比较**自己的部分 Triton FA2（Triton 前向 + 编译 PyTorch 后向）**与普通 PyTorch attention，后者不能偷换成库内 FlashAttention。

- **单 B200，batch 1，始终 causal。**随机输入在 benchmark 开始前生成。
- sequence：128 到 65536 的 2 次幂；head embedding dimension：16 到 128 的 2 次幂；精度：FP32 与 BF16，扫描笛卡尔积。
- 必须分别给 **forward、backward、端到端 forward-backward** 时延；必要时按输入调整 tile。
- **交付：**两种实现、全部上述设置和三类时延的表。不要把题 07 的 batch8 / 序列列表与此表混用。

### 3.2 明确选做：Triton backward（§4.2.3，pp.28–29）

希望练习 Triton 或改进排行榜时，可以把 Algorithm 2 的 tiled 后向实现为 Triton。固定版算法分别计算 dK/dV 和 dQ，两遍重算 P，以避免跨 block 同步/原子累加；它不是必做题 10 的替代标题，也没有独立新增分值。参考文中 Algorithm 2，不使用旧版单遍记号。本站不提供 kernel、launch 调参答案或可提交算法代码。

## 4．分布式通信与 DDP（§5）

### 4.1 共同通信语义（pp.30–32）

node 是机器，world size 是 process group 内 worker 数；本题 worker 与进程一一对应。global rank 在全组唯一，local rank 是节点内编号；只有单节点时它们才可等同。每 rank 绑定不同 GPU，初始化相同通信组与 rendezvous；Gloo 用于无 GPU 本地调试，正式 GPU 训练采用 NCCL。

应尽量在同一机器比较，先 warm-up（原文说一般 5 次足够），CUDA 计时要同步，**即使 collective 的 `async_op=False` 也不例外**。可以用 all-gather 汇总各 rank 时间。异步返回 handle 不代表通信已完成；等待依赖与测量设备完成是不同问题。多 CUDA stream 需考虑额外依赖，不能依赖打印次序证明同步。

### 12 · distributed_communication_single_node（5 分；p.32）

写单节点多进程 all-reduce benchmark，改变：

- FP32 数据张量大小：**1 MB、10 MB、100 MB、1 GB**；报告实际 byte 数及采用的单位，不把 MB 与 MiB 混写。
- GPU / 进程数：**2、4、6**。
- 资源上限：最多 6 GPU；每次 benchmark run **少于 5 分钟**。

**交付：**比较各设置的图和/或表，加 2–3 句结果与因素交互分析。CPU/Gloo 与 GPU/NCCL 结果分表，不能用前者冒充后者。

### 13 · naive_ddp（5 分；p.33）

实现朴素 DDP：开始时从 rank0 广播参数；全局 batch 分成每 rank **不重叠、等大小**的数据（设备数应整除 batch）；各自前后向后，**逐参数 all-reduce 梯度并平均**，然后执行本地 optimizer step。每 rank 的初始模型与 optimizer 状态须一致。

**交付：**在 backward 结束后逐参数通信的实现。连接 `get_ddp` 与按需 `ddp_on_after_backward`；验收入口 `tests/test_ddp.py`。测试包括 tied weights、不可训练参数与同一全局 batch 的单进程基线；不是只检查 loss 非 NaN。

### 14 · naive_ddp_benchmarking（3 分；p.33）

用 **1 node × 2 GPUs，Table 1 xl** 测量朴素 DDP。报告每训练步总时间、梯度通信耗时与所占比例。**交付：**benchmark 设置描述、每步时间和通信时间；保留与后续策略的同配置基线。

### 15 · minimal_ddp_flat_benchmarking（2 分；p.34）

将全部参数梯度拼成一个平坦张量，做**一次 batched all-reduce**；可查 `torch._utils._flatten_dense_tensors` / `_unflatten_dense_tensors`。同样 **1 node × 2 GPUs，xl**，对照逐参数通信。

**交付：**合并后每训练步总时间、梯度通信时间，及 1–2 句比较。这是“全部梯度一次合并”的题，不是已移除的 bucketed DDP。

### 16 · ddp_overlap_individual_parameters（5 分；pp.35–36）

写容器类包装任意 `nn.Module`，训练前广播权重，使每个参数的梯度**一就绪便异步通信**，从而将通信与 backward 计算重叠。建议接口：

- 构造接收 `module`，负责跨 rank 梯度同步。
- `forward(*inputs, **kwargs)` 透传位置与关键字参数。
- `finish_gradient_synchronization()` 等待异步通信依赖满足；必须在 optimizer 使用梯度前完成。

原文建议查 `register_post_accumulate_grad_hook`；collective 的 async 返回 request handle，须管理后续等待。**交付：**重叠 DDP 容器，连接 `get_ddp`、按需 `ddp_on_after_backward`，使用 `tests/test_ddp.py`。官方建议重复运行（如 5 次）检查可靠性；本次未运行。

### 17 · 逐参数重叠 DDP 计时（1 分；p.36）

原题 ID（可横向滚动复制）：

```text
ddp_overlap_individual_parameters_benchmarking
```

- **(a)** 仍用 **1 node × 2 GPUs，xl**，测重叠版每训练步时间，与逐参数朴素版和单次全平坦通信版比较。**交付：**每步时间与 1–2 句。此子问不强制另算通信总时间；重叠区间不能简单相加。
- **(b)** 同设置下用 Nsight 对比最初 DDP 与重叠版。**交付：**两张截图，各一张，直观看到通信是否与 backward 重叠。仅有 `async_op=True` 代码或更短总时间不替代 trace。

## 5．优化器状态分片（§6）

### 18 · optimizer_state_sharding（15 分；p.37）

写类包装任意 PyTorch optimizer 类型，只让各 rank 的本地 optimizer 管理约 1/world_size 的参数和相应状态；step 后把各 rank 更新的参数广播给其余 rank，使模型副本重新一致。这里是简化方案，不能直接称为与 ZeRO stage 1 完全相同。

接口合同：

- 构造接收 `params`（参数 iterable 或含不同超参数的 param groups）、`optimizer_cls` 及转发给其构造函数的 kwargs；调用 `torch.optim.Optimizer` 父类构造。
- `step(closure, **kwargs)` 将 closure 与 kwargs 转交被包裹 optimizer，更新后同步参数。
- `add_param_group(param_group)` 负责新增组与参数归属；父类构造期间会调用，也可能在训练中用于逐步解冻，不能只支持初始化的静态参数列表。

**交付：**分片 optimizer 容器与 `get_sharded_optimizer`；测试 `tests/test_sharded_optimizer.py`，官方建议重复如 5 次检查可靠性。固定测试含普通和 tied-weight 模型；测试覆盖不能缩小上述公共接口合同。

### 19 · optimizer_state_sharding_accounting（5 分；p.38）

- **(a)** 写脚本 profile 有/无 optimizer-state sharding，标准配置 **1 node × 2 GPUs，xl**。分别报告**模型初始化后、optimizer step 紧前、step 紧后**的峰值内存，拆分参数、状态等组成，是否符合预期？交峰值和构成及 2–3 句。
- **(b)** 同配置比较有/无状态分片的每 iteration 时间，交时间和 2–3 句。
- **(c)** 比较本题简化方案与 ZeRO stage 1，即论文 **ZeRO-DP P_os**，特别是内存和通信量。交 2–3 句。这是必须针对性查阅的题，不是把 ZeRO 当无关参考书目。见 [L08 ZeRO 材料](#/c/stanford-cs336-2026/lec/lec08?v=materials)。

## 6．FSDP（§7，pp.38–39）

### 20 · fsdp（15 分）

写容器包装任意完整 `nn.Module`，对其中 **Linear / Embedding** 做 hook 或包装，分片权重、all-gather 所需完整权重并 reduce-scatter 梯度。norm 等过小层应保持不分片；这些复制参数的梯度仍须同步。

- 构造接口接收 `module` 与可选 `compute_dtype: torch.dtype | None`。
- 前向权重必须在使用前到位；为限制显存，**某层的 gather 只能在它前面第 2 层完成 forward 后才开始**，不是提前 gather 全模型，也不是等当前层结束才启动。
- backward 也要及时 all-gather；梯度就绪后 reduce-scatter 到对应 rank。**完整 gathered weights 使用后释放**。
- 给定 compute_dtype 时，**通信之前**就把权重转换为该计算 dtype；master weights 和 optimizer 更新仍为 FP32。
- `forward(*inputs, **kwargs)` 透传；`finish_gradient_synchronization()` 等待异步通信依赖，之后才允许 optimizer 使用梯度。
- 每个 shard 必须兼容 A1 的标准 AdamW。

**交付：**FSDP 容器；handout 指定 `get_fsdp`，固定测试还需要 **`fsdp_on_after_backward`** 和 **`fsdp_gather_full_params`**。后者返回按原参数名映射到完整未分片张量的 state dictionary，复制参数原样返回。测试 `tests/test_fsdp.py`，建议多次运行（如 5 次）找 race。

固定测试使用基础包自定义 Linear / Embedding（不是只识别 `torch.nn.Linear`）、FP32 与 FP16 compute 两条路径，逐步比较非并行基线；同步后梯度 shape / dtype 必须与本地 master 参数一致，非分片梯度须跨 rank 一致。固定测试用 SGD 检验等价性，不能据此删去手册的 AdamW 兼容要求。

### 21 · fsdp_accounting（5 分；p.39）

- **(a)** 接续 §6 分析，预计 FSDP 相对峰值能省多少内存？此纸笔题**允许忽略预分配 all-gather buffers**。交 2–3 句。
- **(b)** **两 GPU 的 xl** profile 中，权重 all-gather 能否赶在 forward 使用前完成？交测得时间、2–3 句与 Nsight 截图。纸笔排除 buffer 的假设不适用于实测峰值删账。

## 7．并行策略分析（§8，pp.39–46）

### 7.1 全部计算题共同题设

这里只分析单个门控 FFN，不是全 Transformer，也不是让你实现 TP/2D 系统。PP、EP 在原文列为其他轴，但没有本节新增实现题。

输入 x 为 `[B,D]`；W₁/W₂ 为 `[D,D_FF]`，W₃ 为 `[D_FF,D]`。前向为 x₁=xW₁、x₂=xW₂、z=f(x₁)⊙x₂、y=zW₃；f 是逐元素函数，如 SiLU。非分片 backward 的完整参考式在 handout (24)–(30)，后续题可按它标注本地形状与归约轴。

N 个设备，任意两设备有链路；每设备**出站**带宽 W bytes/s，单设备计算能力 C FLOP/s。权重和激活均 **FP16，2 bytes/element**，只算矩阵乘法，`[a,b]×[b,c]` 为 2abc FLOPs。ring all-gather / reduce-scatter 对总张量 S bytes 的单卡时间均为 `(N−1)S/(NW)`，ring all-reduce 是两者串联。这里的 S 是完整张量，不是初始 shard 大小；不把所有设备的发送量总和除单卡带宽。

题设理想化忽略启动延迟、拓扑和调度损失；计算与通信可重叠时，以通信耗时超过计算耗时为瓶颈条件。题 26 对两通信轴是否可重叠另给两套假设。理论不等式不是 B200 实测规模上限。

### 22 · alternate_ring_all_reduce（1 分；p.41）

不要使用 reduce-scatter + all-gather，而是每设备先保留自身完整输入作为累加值；在 **N−1 轮**中，把来自依次前驱 rank 的**完整原始张量**继续传给右邻居、接收左邻居的下一份完整输入并累加。第 t 轮，设备 i 发送原始输入编号 `(i−t+1) mod N`，接收编号 `(i−t) mod N`；每份大小 S。

在每设备出站带宽 W 的题设下，这个替代算法要多久？**交付：**含 S、N、W 的表达式与一句理由。本页只保留算法题设，不代给答案。

### 23 · data_parallel_calcs（3 分；p.42）

DP 将 batch 切成 `[B/N_DP,D]`，每卡保留全权重，本地 backward 后 all-reduce 全部权重梯度。

- **(a)** backward 多少 FLOPs？忽略非 matmul。交含 B、D、D_FF、N_DP 的式子与一句理由。
- **(b)** backward 通信多久？交上述参数及 W 的适当子集的式子与一句理由。
- **(c)** 其他参数固定，N_DP 多大前仍不被通信卡住？交 N_DP 独居一侧、另一侧用 B、D、D_FF、C、W 的不等式与一句理由。

### 24 · fsdp_calcs（3 分；pp.43–44）

FSDP 仍切 batch，每个权重也分片（每矩阵每卡 `D D_FF/N_FSDP` 元素）。前向前 all-gather 权重；用后丢弃；backward 再 all-gather，最后对完整权重的局部梯度做 reduce-scatter，保留自己 shard 的完整归约结果。**reduce-scatter 的输入是 full-weight partial sums，输出才是 sharded-weight full sums**，上标 i 在两边不是同一种切法。

- **(a)** 分别计算 backward、forward FLOPs；交两式、两句理由。
- **(b)** 分别计算 backward、forward 通信时间；交两式、两句理由。
- **(c)** 分别求 backward、forward 不受通信瓶颈约束的 N_FSDP 上限；交两不等式、两句理由。

所有变量沿用 7.1；不得漏掉 backward 重新 gather。

### 25 · tp_calcs（4 分；pp.44–45）

本题 TP：W₁/W₂ 沿输出维切，shape `[D,D_FF/N_TP]`；W₃ 沿输入维切，shape `[D_FF/N_TP,D]`。输入 x 在 TP 组内复制；中间门控激活保留 feature shard，不必先 all-gather；各卡的 y 部分和最终 all-reduce。

- **(a)** 给定 dy `[B,D]`，写这一布局的完整 backward。允许引用非分片式 (24)–(30)，须使用 dy、三个权重 shard、保存的 x/x₁/x₂/z/y、必要中间量和通信原语，最终产生每卡三个 dW shards 与 dx。**交付：**完整方程组。本页不展开该计分解答。
- **(b)** forward、backward FLOPs；交两式、两句理由。
- **(c)** forward、backward 通信时间；交两式、两句理由。
- **(d)** backward、forward 各自不受通信瓶颈的 N_TP 上限；交两不等式、两句理由。

变量和 FP16 假设不变。“row/column parallel”以本节 xW 的权重形状定义，不能机械套用把权重存成转置的库命名。

### 26 · fsdp_tp_calcs（6 分；pp.45–46）

2D 网格设备坐标 `(i,j)`：i 为 TP rank，j 为 FSDP rank，总数 `N=N_TP N_FSDP`。先按题 25 做 TP，再沿未切的权重轴做 FSDP；输入 batch 沿 j 切。

- W₁/W₂ 本地 shape `[D/N_FSDP,D_FF/N_TP]`。
- W₃ 本地 shape `[D_FF/N_TP,D/N_FSDP]`。
- 输入 x⁽ʲ⁾ 为 `[B/N_FSDP,D]`。固定 i 沿 j gather，得到一个完整 TP shard；按 TP 前向计算，固定 j 沿 i all-reduce 输出，结果仍是 batch-sharded。
- 本题只聚焦 forward；原文鼓励自己推 backward，但没有新增计分子问。

四个子问：

- **(a)** 2D forward 的 FLOPs。交含 B、D、D_FF、N_FSDP、N_TP 的式子与一句理由。
- **(b)** 两通信轴可相互重叠时，forward 通信多久？**原题提示结果为 FSDP 与 TP 两项成本的 max**。交表达式与一句理由。
- **(c)** 最优选择两轴大小时，N 最大能到多少而 forward 尚未通信受限？交 N 独居一侧的不等式、若干句与方程论证。
- **(d)** 改成两个轴共享网络、collectives **不能重叠**，重新优化两轴并求 N 上限；**不用把两轴截断为整数**。交不等式、若干句与方程论证。

批量和模型大小被题设给定，不允许通过增大 batch 偷换优化问题；原文 critical batch size 只是解释为什么它们不能任意放大。

## 8．完整训练步排行榜（§9，pp.46–48）

### 27 · leaderboard（10 分）

**目标：完整一步 forward + loss + backward + AdamW 更新的 wall-clock time，不是 attention 前向，不是仅 forward-backward。**实现必须保持 `cs336_basics` 模型的输入输出行为、通过常规实现相同测试，代码必须自己写，不得使用/复制现成实现。

| 固定项 | 要求 |
|---|---|
| GPU | 两块 B200 |
| global batch | 2 |
| context | 32768 |
| vocab | 151936 |
| d_model / d_ff | 4096 / 11008 |
| layers / heads | 34 / 32 |
| dtype / mask | BF16 / causal |
| 完整 step | 清梯度（set_to_none）、forward、cross-entropy 后 sum、backward、AdamW |
| 正式计时 | `do_bench` 的 rep=30000 ms，warmup=10000 ms |
| 冷启动总预算 | **空 PyTorch / Triton cache 起算，整个 benchmark run ≤10 分钟** |
| baseline 目标 | 优于朴素 **10 秒 / step** |

labels、targets 用词表范围内的随机整数构造；两份张量各为 `[batch,context]`，模型及 optimizer 在计时的 train-step 外创建。**30000 / 10000 是毫秒预算，不是训练步数。**开发测试时允许缩短它们，但正式记录应恢复并说明；10 分钟包括冷缓存编译和 autotune，不能只报热缓存 kernel 的时间。

原文给出的可选优化方向须与必做任务区分：调 tile / Triton autotune 与编译配置；fused AdamW；避免物化 `[batch,seq,vocab]` 全 logits 的 LM head / cross-entropy 融合（可连反向融合）；改进 FlashAttention 或选做 Triton backward；分开 dQ 与 dK/dV 两遍；causal 跳过全屏蔽 tile、区分非屏蔽与对角 tile；使用原文所述硬件上的 TMA；仅在需要时用 activation checkpointing 以计算换显存。它们是候选方向，**不等于可复制的方案、推荐调参答案或全部硬性要求**。

**交付：**最佳完整训练步 wall-clock 时间，并到 [官方排行榜](https://github.com/stanford-cs336/assignment2-systems-leaderboard) 提交结果。handout 说将验证前 5–10 名的正确性与性能。

补充读取的排行榜 README 固定快照进一步要求：PR 把结果按毫秒升序加入表；描述完整一步时间、做了什么，以及编译/autotune/cache/硬件复现假设；保留最佳代码快照，无法复现或不合法条目会移除。非 Stanford 学生使用**第二张 global 表**；要保持前五须验证，邀请指定维护者 `marcelroed` 访问含 `pyproject.toml`、`uv.lock`、`main.py` 的最小 uv 项目，能够在两 B200 通过 `uv run main.py` 复现。该 README 与 A2 手册是不同固定提交，不能借旧 2025 单 H100 表替代 2026 规则。本站未提交排行榜。

## 9．接口、交付与相关学习入口

### 必要接口总表

| 能力 | 固定 tests/adapters.py 入口 | 返回 / 行为 |
|---|---|---|
| PyTorch FA2 | get_flashattention_autograd_function_pytorch | autograd.Function **类** |
| Triton FA2 | get_flashattention_autograd_function_triton | autograd.Function **类** |
| DDP | get_ddp | 包装模块实例 |
| DDP 反向后 | ddp_on_after_backward | optimizer 前完成所需同步 |
| 分片 optimizer | get_sharded_optimizer | optimizer 实例，保留参数组语义 |
| FSDP | get_fsdp | 接收 compute_dtype 的模块实例 |
| FSDP 反向后 | fsdp_on_after_backward | optimizer 前同步 |
| FSDP 重建 | fsdp_gather_full_params | 原参数名到完整参数张量的字典 |

最终材料应包括：所有实现和原始测试记录；完整 27 题书面答复；计时/显存/通信表；要求的 Nsight 与 memory_viz 图；冷/热缓存口径、硬件与版本；排行榜完整一步及复现说明。测试正确、性能测量和页面正文完整是三种不同状态，不能互相替代。

- 硬件/roofline：[L05](#/c/stanford-cs336-2026/lec/lec05?v=notes)；kernel/编译：[L06](#/c/stanford-cs336-2026/lec/lec06?v=notes)。
- 同步训练语义：[L07](#/c/stanford-cs336-2026/lec/lec07?v=notes)；并行权衡：[L08](#/c/stanford-cs336-2026/lec/lec08?v=notes)。
- 资源与测量：[Attention 账本](#/c/stanford-cs336-2026/lec/ext04?v=notes)、[性能分析](#/c/stanford-cs336-2026/lec/ext06?v=notes)。
- 通信与恢复：[集合通信](#/c/stanford-cs336-2026/lec/ext07?v=notes)、[分片训练与恢复](#/c/stanford-cs336-2026/lec/ext08?v=notes)。

## 来源、修改与完整许可

本页基于下列第一方固定来源作中文任务重述、结构重排、接口校正与边界说明，非官方中文版，未转录 staff 解答或生成可提交代码。已实际全读 48 页提取文本，未声称逐页视觉核对；原文公式排版歧义、配置和 adapter 差异已注明。完整逐题映射及实际阅读范围在 `sources/p4-a2/task-coverage.json`、`review.txt` 与 `manifest-fragment.json`，哈希保留在来源记录，不占用移动端正文。

1. [固定 A2 仓库](https://github.com/stanford-cs336/assignment2-systems/tree/ca8bc81a59b70516f7ebb2da4808daade877c736)、[48 页 handout](https://github.com/stanford-cs336/assignment2-systems/blob/ca8bc81a59b70516f7ebb2da4808daade877c736/cs336_assignment2_systems.pdf)、[实际 adapters](https://github.com/stanford-cs336/assignment2-systems/blob/ca8bc81a59b70516f7ebb2da4808daade877c736/tests/adapters.py)。同提交 README、LICENSE、pyproject、CHANGELOG、四个测试文件及 common、提交脚本均已阅读。
2. [排行榜 README 固定快照](https://github.com/stanford-cs336/assignment2-systems-leaderboard/blob/df82f2f05c43273096bedffced4d7a035bcbf1fc/README.md)：独立补充规则，不从作业仓库继承许可。
3. [官方课程](https://cs336.stanford.edu/)、[AI 政策](https://docs.google.com/document/d/1SZAlExB1qAc9izHt54gwunNpjKE6wXb8Y7yA_e-baK8/edit)、[校内集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit)：独立归纳政策和访问限制，未声称公开全文翻译许可。

MIT 仅涵盖作业仓库第一方软件与相关文档；引用的 FlashAttention / ZeRO 论文、外部文章、Lightning 图、软件依赖及服务不因此成为 MIT。本站未复制这些第三方图文；论文各自权限与独立精读边界见其唯一归属页。

> Copyright 2025 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
