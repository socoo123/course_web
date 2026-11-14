---
title: A1 从零构建 Transformer：完整实验说明
kind: 固定 2026 官方第一方要求的中文重述；不是解答或可提交实现
source: CS336 Assignment 1 (basics), Spring 2026, Version 26.0.3
source_commit: a158843b20107949f1a8d7df1b05cd33b9166712
source_read_scope: 全部 47 页提取文本及 README、LICENSE、pyproject、CHANGELOG 全文；未逐页视觉审校
status: P3 完整说明；覆盖 38 个 Problem 及其子问，文档完整不表示实验完成
execution: 未安装依赖、执行官方测试、实现作业、下载数据、训练或使用付费计算
license: 第一方软件和相关文档按 MIT 使用；完整版权、许可和修改声明见页底
---

# A1 要交付什么

本实验把文本处理、神经网络和实验纪律连成一条完整链路：自行训练 byte-level BPE 分词器，编码语料，自行构建 Transformer、交叉熵、AdamW 与训练循环，保存和恢复状态，生成文本，最后在 TinyStories / OpenWebText 上比较训练设置与架构修改。

本页完整保留固定版 **38 个计分 Problem 的要求、全部子问、分值、交付与验收入口**，并补齐它们依赖的接口、规则和资源条件；不照搬讲义的第三方文本示例、论文插图或可提交代码。如何理解合同、定位错误、组织对照，读 [A1 概念与调试指导](#/c/stanford-cs336-2026/lab/a1-basics?v=guide)。这里的分值属于原讲义，所有“验收”都是读者应完成的工作，不是本站通过记录。页码采用 PDF 印刷页码。

## 0．版本、行为规则与提交

### 固定版本

以页底固定提交的 PDF 封面 **Spring 2026 / Version 26.0.3** 为准。README 标题残留 Spring 2025，包版本是 `26.0.0`，版权年份是 2025；三者不能替代讲义版次。26.0.0 修正 AdamW 衰减次序，26.0.3 将排行榜时限从 90 分钟改为 **45 分钟**。

README 使用 `uv`；固定 `pyproject.toml` 要求 Python `>=3.12,<3.14`、PyTorch `~=2.11.0`。各作业应独立管理环境；`uv run` 在需要时会解析并准备环境，不能视为无下载动作。公共环境和权限说明统一见[课程资料](#/c/stanford-cs336-2026)。本文不声称任何设备已通过依赖兼容性验证。

### 从零实现与 AI 政策

- 实质实现写在 `cs336_basics/`。`tests/adapters.py` 仅把测试接口接到自己的代码，不放实质算法逻辑；不能修改测试迁就实现。
- 总则禁止直接使用 `torch.nn`、`torch.nn.functional`、`torch.optim` 中现成定义，明确例外是 `torch.nn.Parameter`、`torch.nn` 容器类（如 Module、ModuleList、Sequential）与 `torch.optim.Optimizer` 基类。其他 PyTorch 定义可用；有疑义应问课程 staff。
- 后文明确允许的特例仍有效：§3.3.1 的 `torch.nn.init.trunc_normal_`，SwiGLU 的 `torch.sigmoid`，以及 checkpoint 部分的状态保存/加载 API。不能将这些例外扩张为可用现成 Linear、Embedding、RMSNorm、Attention、AdamW 或 loss 实现。
- **AI 只允许概念问答与底层 API / 函数签名查询；禁止实现作业的任何部分，包括排行榜代码、coding agent 和 AI 自动补全。**官方要求 agent 使用仓库提供的 AGENTS.md 提示，聊天机器人也应带上相应提示；鼓励关闭 AI 自动补全，普通函数名补全不受此限制。本页不代写实现、不提供短答答案或资源题数值解答。

### 提交与完成的证据

课程提交物为排版后的 `writeup.pdf`（回答全部书面题）与 `code.zip`（自己的代码）。官方 `make_submission.sh` 用来打包；大数据和 checkpoint 等不应混入提交包，按脚本排除规则处理。排行榜按其仓库 README 提交 PR，和 Gradescope 是两条提交流程；公开阅读仓库不保证获得提交资格或课程算力。

完整完成必须同时有：功能代码、要求的书面答复、分词及数据资产、真实实验曲线、生成结果、预算与路线记录。测试通过不代替实验，说明文档写完更不代表这些工作已经做过。

## 1．分词：字符、资产和数据

### 1.1 训练与编码的共同合同（§2.1–2.6，pp.3–12）

Unicode 码点、UTF-8 bytes 和 token ID 是不同表示。byte-level BPE 从全部 **256 个字节值**开始，训练时在 pre-token 内反复合并最常见的相邻 token 对；最终词表大小上限包含基础字节、合并项和特殊 token。频次相同时，选**字节串二元组按字典序较大者**，不是比较显示出来的 Unicode 字符，也不是只比较拼接结果。

正式 pre-tokenization 使用固定讲义 §2.4 p.6 指定的 GPT-2 正则（见固定原文），不是示例里的简单空格切分。其行为涉及缩写、字母、数字、标点和空白；Python 的 `regex` 支持所需 Unicode 属性。原文建议迭代匹配，避免额外物化全部 pre-token。该外部来源正则不在本页复制。

特殊 token 有两项不同职责：训练时按它切断文本、排除其自身的 merge 统计，不能删除后把左右正文拼起来；编码时将它保留为一个固定 ID。普通 pre-token 的边界也不能跨越。并行预分词应在特殊 token 开头切分；原文允许使用仓库的 chunk-boundary 示例，且本作业不用处理“巨大语料完全没有 `<|endoftext|>`”这一边界。增加进程是优化选择，不改变规则。

训练输出的有序 merges 随后冻结；编码按训练顺序应用可用合并，不在待编码文本上重训。解码先取得各 ID 对应 bytes，再整体恢复 Unicode；非法 UTF-8 以 U+FFFD 替换。流式编码须保持语义，不能因任意分块截断可合并 token。先小语料开发、再 profiling，之后才考虑全语料；局部 pair 计数更新和系统语言加速是优化方向，不是允许省略正确性要求。

### 01 · unicode1（1 分；§2.1，pp.3–4）

- **(a)** `chr(0)` 返回什么 Unicode 字符？交一整句回答。
- **(b)** 该字符的 `__repr__()` 字符串表示和打印表示有什么不同？交一整句回答。
- **(c)** 该字符出现在文本中会怎样？可分别观察它自身、打印它、将它夹在两个普通字符串中以及打印拼接结果；交一整句观察。

验收是三项真实观察与解释，不以截图代替回答。

### 02 · unicode2（3 分；§2.2，pp.4–5）

- **(a)** 为何本分词器更适合在 UTF-8 bytes 上训练，而非 UTF-16 / UTF-32？可比较不同输入的编码，交 1–2 句。
- **(b)** 原文给出的错误解码函数把每一个 byte 独立构造成单字节 bytes、分别按 UTF-8 解码，再拼接字符串。指出错误，并给一个会产生错误结果的输入 byte string；交反例与一句解释。原文中普通英文输入能运行不构成正确性证明。
- **(c)** 给一个无法解码成 Unicode 字符串的两字节序列，交该序列及一句解释。

本页只重述问题，不代给反例或结论。

### 03 · train_bpe（15 分；§2.5，p.9）

编写训练函数，至少接收：`input_path: str`（训练文本路径）、`vocab_size: int`（最终词表最大值）、`special_tokens: list[str]`。按 1.1 的边界和 tie-break 规则训练，返回：

- `vocab: dict[int, bytes]`：token ID 到 token bytes 的映射。
- `merges: list[tuple[bytes, bytes]]`：每个二元组记录一次合并，严格按产生顺序排列。

交付自己的训练实现；接通 `run_train_bpe`，验收入口为 `uv run pytest tests/test_train_bpe.py`，包括特殊 token 边界要求。可选用 C++ / Rust 重写瓶颈，但须提供构建说明或仅靠 pyproject 即可构建；注意跨语言复制成本与正则支持，不能要求评测者猜构建步骤。

### 04 · train_bpe_tinystories（2 分；§2.5，pp.9–10）

- **(a)** 在 TinyStories 训练集上训练最大 **10,000** 词表，加入 `<|endoftext|>`；将词表与 merges 序列化。回答实际耗时、内存、最长 token 是什么及其是否合理，交 1–2 句。
- **(b)** 对实现做 profiling，指出训练过程最耗时的部分，交 1–2 句。

同时保留实际资产和测量依据。原文资源包络 **≤30 分钟、≤30 GB RAM、无需 GPU**；“可通过并行预分词做到两分钟以内”是原文优化提示，不是本文实测，也不是人人必达的设备保证。

### 05 · train_bpe_expts_owt（2 分；§2.5，p.10）

- **(a)** 在提供的 OpenWebText 训练集上训练最大 **32,000** 词表，序列化词表和 merges；说明最长 token 及其合理性，交 1–2 句。
- **(b)** 比较 TinyStories 与 OpenWebText 得到的 tokenizer，交 1–2 句。

原文资源包络 **≤12 小时、≤100 GB RAM、无需 GPU**。它是全规模工作的上限式参考，不是最低配置承诺。

### 06 · tokenizer（15 分；§2.6，pp.11–12）

实现从已有词表和 merges 构造的 Tokenizer，支持用户特殊 token；若特殊 token 不在词表中，需补入。建议接口全部保留：

- `__init__(vocab, merges, special_tokens=None)`：接收 `dict[int, bytes]`、有序 bytes 对列表和可选字符串列表。
- 类方法 `from_files(vocab_filepath, merges_filepath, special_tokens=None)`：使用训练时自己的序列化格式，返回 Tokenizer。
- `encode(text: str) -> list[int]`：文本到 ID。
- `encode_iterable(iterable: Iterable[str]) -> Iterator[int]`：如从文件句柄读取，惰性产出 ID，不把整个大文件放入内存。
- `decode(ids: list[int]) -> str`：按 1.1 处理 bytes 与非法 UTF-8。

验收入口：`get_tokenizer` → `uv run pytest tests/test_tokenizer.py`。往返可读并不足够，还必须满足已训练 merges 的顺序、特殊 token 原子性、分块语义与内存要求。

### 07 · tokenizer_experiments（4 分；§2.7，pp.12–13）

- **(a)** 两个语料各抽样 **10 个文档**，分别用对应的 10k / 32k tokenizer 编码；计算各自 **bytes/token** 压缩率，交 1–2 句。
- **(b)** 改用 TinyStories tokenizer 编码 OWT 样本，比较压缩率和/或定性变化，交 1–2 句。
- **(c)** 实测 tokenizer 吞吐（如 bytes/s），外推编码 **825 GB Pile** 需多长时间，交 1–2 句。这里要求估算，不要求下载 Pile。
- **(d)** 分别编码两语料各自的训练/开发集，保存 token ID 数组供后续训练；原文推荐 NumPy `uint16`，回答为什么合适，交 1–2 句。

验收需要真实测量和四份编码数据，不只是 tokenizer 单元测试。训练 tokenizer、调试样本和最终验证数据的用途应分清，不能把验证数据上训练过的调试资产当成未泄漏的正式资产。

## 2．模型：从模块合同到完整前向

### 2.1 全局架构与初始化（§3.1–3.3，pp.13–19）

模型接收 `(batch, sequence)` 的 token ID，经过 embedding、多个 pre-norm block、最终 RMSNorm、LM head，输出 `(batch, sequence, vocab_size)` 的 **logits**。原文概述图画出概率端点，但 `transformer_lm` 的代码合同明确要求未归一化 logits；softmax 由使用方按训练或采样需要处理。

每个 block 先对输入归一化后进入注意力，再残差相加；第二个子层同样先归一化、再 SwiGLU、再残差相加。batch、位置、attention head 等前导维不能意外参与特征约简。数学列向量记号不是更改张量物理存储顺序的要求。

初始化要求：Linear 权重零均值、方差 `2 / (d_in + d_out)` 的截断正态，截断在正负三倍标准差；Embedding 为零均值、方差 1 的截断正态，范围 `[-3,3]`；RMSNorm gain 全 1。明确允许使用 `torch.nn.init.trunc_normal_`。以下模块都应尊重构造时的 device / dtype，权重用 Parameter 注册。

### 08 · linear（1 分；§3.3.2，p.18）

实现继承 `nn.Module` 的 Linear，调用父类构造器；构造参数为 `in_features`、`out_features`、可选 `device` / `dtype`，`forward(x)` 做无 bias 的线性变换。权重按 **`(out_features, in_features)`** 存储为 W，而不是 W 的转置；初始化按 2.1。不得用现成 `nn.Linear` 或 functional linear。

`run_linear` 适配器应装载给定权重（可用 `load_state_dict`）；验收 `uv run pytest -k test_linear`。

### 09 · embedding（1 分；§3.3.3，pp.18–19）

实现继承 Module、调用父类构造器的 Embedding。构造参数：`num_embeddings`、`embedding_dim`、可选 device / dtype。Parameter 矩阵形状为 `(vocab_size, d_model)`；`forward(token_ids)` 按整数 ID 查表，特征维留在末轴；初始化按 2.1。不得用现成 Embedding 或 functional embedding。

交付模块；`run_embedding` → `uv run pytest -k test_embedding`。

### 10 · rmsnorm（1 分；§3.4.1，pp.19–20）

实现 RMSNorm Module，参数 `d_model`、`eps=1e-5`、可选 device / dtype。对每个位置的末维向量，用“平方的均值加 epsilon 后开平方”作分母，并乘可学习的逐特征 gain；不减均值，不额外加入 bias。输入输出形状均为 `(batch, sequence, d_model)`。

**先将输入升到 float32，再平方并归一化，最后把结果转回输入 dtype**；仅把归约结果转 float32 不满足此防溢出意图。gain 初始化为 1。`run_rmsnorm` → `uv run pytest -k test_rmsnorm`。

### 11 · positionwise_feedforward（2 分；§3.4.2，pp.21–22）

实现无 bias 的 SwiGLU FFN：一条投影分支经过 SiLU，与另一条线性投影逐元素相乘，再投影回 `d_model`。SiLU 定义为输入乘 sigmoid。两个向内投影矩阵为 `(d_ff,d_model)`，输出矩阵为 `(d_model,d_ff)`。`d_ff` 约为 `8/3 × d_model`，并取邻近的 **64 的倍数**。明确允许用 `torch.sigmoid` 改善稳定性。

交付 FFN；`run_swiglu` → `uv run pytest -k test_swiglu`。

### 12 · rope（2 分；§3.4.3，pp.22–23）

实现 RotaryPositionalEmbedding。构造参数 `theta`、`d_k`、`max_seq_len`、可选 device。`forward(x, token_positions)` 接收 `x: (..., seq_len, d_k)` 与位置张量 `(..., seq_len)`，返回同形状张量；支持任意前导 batch 维，按给定位置索引使用 sin/cos，不能总是假设从零连续排列。

原文把相邻两维视作一个二维旋转对；若位置为 i、配对编号 k 从 1 开始，角度为 `i / theta^((2k−2)/d_k)`，旋转采用通常的 cos/负 sin、sin/cos 约定。没有可学习参数，不要求构造完整稠密旋转矩阵。跨层共享或预计算 buffer 是可选优化，不是额外必交题。

`run_rope` → `uv run pytest -k test_rope`。原理推导不在这里重复，见 [L03 精读材料](#/c/stanford-cs336-2026/lec/lec03?v=materials)。

### 13 · softmax（1 分；§3.4.4，p.24）

编写接收张量和归一化维度的 softmax 函数，输出同形状、指定维度上的概率分布。必须沿该维减去最大值以避免指数溢出，不能把别的 batch 项并入归一化。

`run_softmax` → `uv run pytest -k test_softmax_matches_pytorch`。

### 14 · scaled_dot_product_attention（5 分；§3.4.4，pp.24–25）

实现由 Q/K 点积、`sqrt(d_k)` 缩放、softmax、对 V 加权构成的 attention。Q/K 为 `(batch, ..., seq_len, d_k)`，V 为 `(batch, ..., seq_len, d_v)`，输出末维为 `d_v`，保留前导维。前面的数学定义允许 query 和 key 长度不同；题目基本接口使用相同 seq_len，不要因此把 key 特征维与 value 特征维混同。

支持可选布尔 mask `(seq_len, seq_len)`：**True 表示允许关注，False 表示禁止**。对每个 query，允许位置的概率合计为 1，禁止位置概率为 0；原文要求在 softmax 前排除禁止 logits。一般意义下整行没有可用 key 就没有合法归一化分布，本文不额外规定一个伪造的“均匀 fallback”；标准因果 mask 含对角线，不会造成这种行。

`run_scaled_dot_product_attention` 对接三维 `test_scaled_dot_product_attention` 与四维 `test_4d_scaled_dot_product_attention`；各入口使用 `uv run pytest -k <测试名>`。

### 15 · multihead_self_attention（5 分；§3.4.5，pp.25–26）

实现 causal multi-head self-attention Module，至少接收 `d_model` 与 `num_heads`，每头 `d_k=d_v=d_model/num_heads`。包含 Q/K/V 投影、多头独立 attention、拼接及输出投影；正常批处理下 Q/K/V 总共用三个矩阵乘法，不为每个 head 单独 Python 循环投影。把三者融合为一次投影只是脚注 stretch goal。

位置 i 只能访问 `j≤i`，包含自身；**RoPE 只施加到 Q/K，不施加到 V**，head 作为 batch 维，各头使用同样的位置旋转规则。`run_multihead_self_attention` → `uv run pytest -k test_multihead_self_attention`。

### 16 · transformer_block（3 分；§3.5，p.26）

组装 2.1 所述 pre-norm attention / SwiGLU 两子层和残差，至少接收 `d_model`、`num_heads`、`d_ff`；输入输出的残差流形状保持不变。交付通过官方测试的 block；`run_transformer_block` → `uv run pytest -k test_transformer_block`。

### 17 · transformer_lm（3 分；§3.5，pp.26–27）

组装 embedding、`num_layers` 个 block、最终 RMSNorm 和 LM head；除了 block 参数，还至少接收 `vocab_size`、`context_length`、`num_layers`，其中 context_length 用于位置缓存的长度边界。输出 logits，不提前 softmax。

交付完整 LM Module；`run_transformer_lm` → `uv run pytest -k test_transformer_lm`。基线不默认把输入/输出 embedding 权重绑定；weight tying 是后面的自选修改方向。

### 18 · transformer_accounting（5 分；§3.5，pp.27–28）

使用**本作业架构**的 GPT-2 XL-shaped 配置，而不是历史 GPT-2 的参数表：词表 50,257，context 1,024，48 层，`d_model=1600`，25 头，`d_ff=4288`。

- **(a)** 计算可训练参数数目；参数均为 float32 时，仅装载这些参数需要多少内存？交 1–2 句。
- **(b)** 列出一个 context-length 输入的前向中全部矩阵乘法、用途及总 FLOPs。
- **(c)** 哪些部分消耗最多 FLOPs？交 1–2 句。
- **(d)** 对 small（12 层 / 768 维 / 12 头）、medium（24 / 1024 / 16）、large（36 / 1280 / 20）重做分析；给每个模型各组件占总前向 FLOPs 的比例，再用 1–2 句解释尺寸变大后的比例变化。仍沿用本作业的 FFN 规则和未另改的设定。
- **(e)** XL 的 context 改成 **16,384** 时，总前向 FLOPs 与组件相对占比怎样变化？交 1–2 句。

原文核算约定：`(m,n)` 乘 `(n,p)` 计约 `2mnp` FLOPs。列清每个矩阵的轴与重复次数；本文不填数值答案。

## 3．损失与参数更新

### 19 · cross_entropy（1 分；§4.1，pp.28–29）

接收预测 logits 和 next-token target ID，计算目标的负对数概率，并对所有前导 batch-like 维取平均，词表留在最后一维。必须减最大值以保持稳定，并尽可能抵消 log / exp，而不是先形成易下溢的概率再取对数。

`run_cross_entropy` → `uv run pytest -k test_cross_entropy`。验证时还要能报告 perplexity，它是平均 token loss 的指数；不要先对逐项 perplexity 做算术平均，也不要把后文 loss 阈值写成 perplexity 阈值。

### 20 · learning_rate_tuning（1 分；§4.2.1，pp.29–31）

使用固定讲义修正后的 SGD 小例：对随机参数的平方均值求 loss，使用每步按迭代计数衰减的 SGD。分别把学习率改为 **1e1、1e2、1e3**，各运行 **10 次迭代**，观察 loss 更快/更慢下降还是发散。交 1–2 句真实观察。

这是原文小实验，不是 §7 的完整 LM 学习率搜索；本页不复制训练代码，也不预报答案。Optimizer API 的参数组、每参数状态和可选 closure 概念可查官方 API，但实现仍须自己完成。

### 21 · adamw（2 分；§4.3，pp.31–32）

实现 `torch.optim.Optimizer` 子类；构造器接受学习率、两个 beta、epsilon 与权重衰减系数。用基类 `self.state` 为每个 Parameter 保留一、二阶矩等状态，不能在每次 step 重置。

**固定 2026 Algorithm 1 的合同**：迭代 t 从 1 起；在当前参数上取得梯度，计算偏差修正的步长，先对旧参数施加解耦 weight decay，再更新矩估计、施加矩调整后的梯度更新。衰减使用基础学习率 alpha，而非偏差修正后的步长。其偏差修正步长和分母分别是：

$$
\begin{aligned}
\widetilde\alpha_t
&=\alpha\frac{\sqrt{1-\beta_2^t}}{1-\beta_1^t},\\
\text{更新分母}&=\sqrt{v_t}+\epsilon.
\end{aligned}
$$

epsilon 在平方根外；如果选择其他等价写法，必须连 epsilon 的缩放含义一起核对，不能只凭“也叫 AdamW”替换公式。2026 更改的是衰减/梯度更新次序，不是要求对衰减后的参数重新计算一份梯度。`get_adamw_cls` → `uv run pytest -k test_adamw`。

### 22 · adamw_accounting（2 分；§4.3，pp.32–33）

所有张量按 float32，`d_ff=8/3 × d_model`（本题的代数假设）。

- **(a)** 分开推导参数、激活、梯度、优化器状态的内存表达式及总量；自变量为 batch_size、vocab_size、context_length、num_layers、d_model、num_heads。激活只按题设计：block 内各 RMSNorm；attention 的 Q/K/V 投影、QK 转置乘法、softmax、V 加权和、输出投影；SwiGLU 的 W1/W2/W3 投影、gate 的 SiLU、逐元素乘积；最终 RMSNorm、输出 embedding、logits 上的 cross-entropy。
- **(b)** 代入 XL-shaped 配置，写成 `a × batch_size + b`，给 a、b 的数值以及可放入 **80 GB** 的最大 batch。
- **(c)** 给一次 AdamW step 的 FLOPs 代数式与简短依据。
- **(d)** 按题设单 **H100**、495 TFLOP/s、50% MFU，反向 FLOPs 是前向的两倍，估算 XL、batch 1024、400K 步所需小时数并解释。

这些 H100 / 80 GB 条件只用于纸笔题，不替换 2026 实训 B200 参考。MFU 比较时须把 tokens/s 经模型 FLOPs/token 换算为 FLOPs/s 后再除硬件峰值，不能直接拿不同单位相除。

### 23 · learning_rate_schedule（1 分；§4.4，pp.33–34）

编写函数，接收当前迭代 t、最大/最小学习率、warmup 步数 Tw、余弦结束步 Tc。合同三段：

- `t<Tw`：线性 warmup，从零按 `t/Tw` 增长到最大值。
- `Tw≤t≤Tc`：在最大和最小值之间作半个余弦周期插值，相位是 `(t−Tw)/(Tc−Tw) × π`，权重是 `(1+cos(相位))/2`。
- `t>Tc`：保持最小值。

接通 `get_lr_cosine_schedule`，验收 `uv run pytest -k test_get_lr_cosine_schedule`。明确三段边界，不能恢复 checkpoint 后把调度计数偷偷重置。

### 24 · gradient_clipping（1 分；§4.5，p.34）

接收参数列表和最大整体 L2 范数 M，原地修改各参数梯度。先把所有参数梯度视作一个整体计算范数；小于阈值则不变，否则按 `M / (整体范数 + epsilon)` 缩放。使用 `epsilon=1e-6`。不是每个张量各用一份 M，也不是裁参数值；时点在 backward 后、optimizer step 前。

`run_gradient_clipping` → `uv run pytest -k test_gradient_clipping`。

## 4．数据、checkpoint 与训练闭环

### 25 · data_loading（2 分；§5.1，pp.34–35）

接收 NumPy 整数 token 数组、batch_size、context_length、设备字符串；随机抽取输入片段和对应**右移一个 token**的目标，两者均为 `(batch_size, context_length)`，都放到指定设备。窗口最后一个输入之后还要有一个 token 作目标。数据可将带 EOS 分隔的文档连成单条序列；题目不要求按文档逐条 padding。

大数据必须用与保存格式匹配的 `np.memmap`，或 `.npy` 对应的 `np.load(..., mmap_mode='r')`，并匹配 dtype。核对映射后 ID 未超词表范围；CPU / Apple Silicon 分别使用相应 cpu / mps 设备，模型也须一致。

`run_get_batch` → `uv run pytest -k test_get_batch`。

### 26 · checkpointing（1 分；§5.2，pp.35–36）

交付两个函数：

- `save_checkpoint(model, optimizer, iteration, out)`：保存模型状态、优化器状态与迭代数；out 支持字符串路径、PathLike 或二进制 file-like 对象。
- `load_checkpoint(src, model, optimizer)`：从同类路径/对象恢复给定 model 与 optimizer，返回保存的 iteration。

可用双方的 `state_dict` / `load_state_dict` 与 `torch.save` / `torch.load`。格式自定，但必须能完整往返。**最低合同不只是权重**；AdamW moments 与调度所需迭代数不可漏。随机状态、数据采样状态等属于“逐步完全复现续训”这一更强主张需要的额外证据，不应擅自说成原题已强制列出的字段。

`run_save_checkpoint`、`run_load_checkpoint` → `uv run pytest -k test_checkpointing`。

### 27 · training_together（4 分；§5.3，pp.36–37）

交付接受用户输入的训练脚本，支持至少以下能力：

1. 配置模型和优化器的各项超参数，便于多次改配置实验。
2. 内存高效地加载大训练集与验证集。
3. 向用户给定路径序列化 checkpoint。
4. 周期性记录训练和验证表现，控制台或外部日志服务均可。

组合模型、loss、优化器、调度、裁剪和 batch 采样，形成可运行闭环。原文没有指定“一个集成测试通过即可完成整题”的入口；验收是脚本功能与后续真实训练证据。外部日志服务是选项，不要求购买服务或把凭据写进代码。

## 5．生成

### 28 · decoding（3 分；§6，pp.37–38）

交付 LM 解码函数，四项能力均要有：

1. 接收用户 prompt，逐个生成续写，遇 `<|endoftext|>` 停止。
2. 允许设置最多生成多少 token，并据此停止。
3. 按用户 temperature 对最后位置 logits 缩放后取 softmax，再采样；不是对所有历史位置一起抽一个 token。
4. 支持用户阈值的 nucleus / top-p sampling：在按概率从大到小排列的候选中取累计质量达到阈值的最小前缀，保留跨过阈值的那一项，并在保留集合上重新归一化。

每一步把新 token 纳入下一步上下文。temperature 趋近零的数学极限不等于直接在程序里除以零；超出模型上下文容量的处理应明确且与位置语义一致。原文未指定独立单测入口；功能验收与“生成文本流畅”是两件事。

## 6．真实训练、对照与交付

### 6.1 TinyStories 基线和路线选择（§7.1–7.2，pp.38–42）

标准基线：词表 **10,000**、context **256**、`d_model=512`、`d_ff=1344`、**4 层 / 16 头**、RoPE theta **10,000**；总训练 token 约 **327,680,000**，即 batch × 总步数 × context。学习率、warmup、AdamW betas/epsilon/weight decay 需自己试验。讲义不同段对“约 17M”口径表述不完全一致；不要把这一近似说明当成资源题答案，应从实际模块逐项统计。

标准正确高效实现的单 B200 单次训练参考 **20–30 分钟**，不是全作业总工时。明显偏慢应检查数据加载、验证、checkpoint 和批处理是否成为瓶颈。建议先过拟合一个 minibatch、检查中间形状与激活/权重/梯度范数，再进入完整 run。

| 路线 | 数据预算与目标 | 适用边界 |
| --- | --- | --- |
| 标准 TinyStories | 约 327.68M tokens；验证 per-token loss **≤1.45** | 标准计分任务的参考；不是本文已达到的成绩 |
| 官方 CPU/MPS 低资源 | 约 40M tokens；目标可放宽为 **≤2.00** | 明确减量路线，不等同于原规模 |
| 更小的概念调试 | 自造小样本或小张量 | 只证明局部机制，不算官方低资源训练完成 |

低资源框的 staff 示例为 **32 × 5000 × 256 = 40,960,000 tokens**，M4 Max / 36 GB RAM，CPU **82 分钟**、MPS **36 分钟**、loss **1.80**。这些是官方报告，不是本站测量。p.3 “MPS 不到五分钟、CPU 约三十分钟”只描述另一个小模型可行性，不保证完成本题全部预算。

缩短总步数时，原文建议令余弦衰减恰在最终步结束。CPU 可考虑 compile；MPS 的 TF32/compile 警告是原文 **torch 2.9.0** 的历史经验：不要照搬 CUDA 的 high matmul precision 设置，原文 MPS 建议 aot_eager，称当时不支持 Inductor。固定仓库依赖已是 2.11 系列，本页未重测，不能声称这些兼容性结论已重新验证。

### 29 · experiment_log（3 分；§7.1，pp.38–39）

建立训练/评估实验追踪设施，同时记录 loss 对**梯度步数**和对**墙钟时间**的关系。交付日志基础设施代码，以及覆盖本节所有尝试的实验记录文档和学习曲线，包括失败/发散尝试，不能只留下最佳 run。应在长训练开始之前接入日志。

### 30 · learning_rate（3 分；§7.2.3，pp.40–41；探索标注 2 B200 小时）

- **(a)** 对多个学习率做搜索，报告最终 loss，发散的标明发散；交相应曲线与搜索策略。交一个在明确所选路线下达到验证目标的模型：标准 **≤1.45**，官方 CPU/MPS 减量路线 **≤2.00**。
- **(b)** 检验“最佳学习率位于稳定边缘”的经验说法：逐步提高学习率，曲线须包含**至少一次发散 run**，分析发散边界与收敛速度/最佳学习率的关系。

不能用单个 minibatch 的近零训练 loss 代替验证集目标，也不能把读取参考 loss 写作自己的实验结果。

### 31 · batch_size_experiment（1 分；§7.2.3，p.41；探索标注 1 B200 小时）

从 batch **1** 一直探索到 GPU 显存所能容纳的边界，中间至少尝试几种大小，包含典型的 **64、128**。如有必要，重新优化学习率。交不同 batch 的学习曲线及数句发现。

比较时记录 batch、步数、token 预算与墙钟，不可把固定步数却不同 token 数的实验说成等 token 对照。低资源读者应如实声明硬件无法覆盖的范围，不伪造 GPU 上限。

### 32 · generate（1 分；§7.2.3，p.42）

使用自己的 decoder 与训练 checkpoint，按需要调整 temperature / top-p；交**至少 256 tokens** 的生成文本，或在第一个 `<|endoftext|>` 出现时提前停止。简评流畅度，并指出至少 **两个**影响质量的因素。低资源模型不必伪装成与标准预算一样流畅；原文第三方/示范故事不在本文复刻，交付必须是自己的真实生成。

### 33 · layer_norm_ablation（1 分；§7.3，p.42；探索标注 0.5 B200 小时）

从 Transformer 中去掉**所有 RMSNorm**，先用原先最优学习率训练，观察结果；再调查降低学习率能否恢复稳定。交去掉 RMSNorm 后的曲线、该变体最佳学习率的曲线，以及数句关于 RMSNorm 影响的讨论。不是只删一层或保留最终 RMSNorm 后声称“全部去掉”。

### 34 · pre_norm_ablation（1 分；§7.3，p.43；探索标注 0.5 B200 小时）

把基线 pre-norm block 改为 post-norm：attention 子层先将原输入与 attention 输出相加再 RMSNorm；FFN 子层同样先残差相加再 RMSNorm。训练该变体，交与 pre-norm 的对照学习曲线。说明自己对 block 外最终 norm 的处理，避免未记录的额外变化；原题给出的明确变更是这两个 block 内公式。

### 35 · no_pos_emb（1 分；§7.3，p.43；探索标注 0.5 B200 小时）

去掉显式位置嵌入信息，比较 RoPE 基线与 NoPE 的学习曲线。**保留 decoder-only 的因果 mask**；NoPE 不是去掉因果性，也不是让模型获得未来 token。原文讨论因果结构可能隐含位置信息，是研究动机，不是要求预先写出“NoPE 必好/必坏”的答案。

### 36 · swiglu_ablation（1 分；§7.3，pp.43–44；探索标注 0.5 B200 小时）

将门控 SwiGLU 对比非门控 SiLU FFN：后者使用输入投影、SiLU、输出投影，内宽设 **`4 × d_model`**；前者约 **`8/3 × d_model`**。这样近似匹配参数量，而不是只删除门控分支仍保持原内宽。交两者学习曲线及数句发现。

四项消融各自从同一可追踪基线出发，不累加成一个混合变体。报告预算、初始化/随机性和必要重调范围；固定 token、固定 step、固定墙钟分别回答不同问题，不得互换标签。

### 37 · main_experiment（2 分；§7.4，pp.44–45；探索标注 2 B200 小时）

在提供的 OpenWebText 上训练，使用与 TinyStories **相同模型架构、相同总训练迭代次数**；必要时重调学习率或 batch，换用匹配的 OWT tokenizer / 数据资产。交：

1. OWT 学习曲线，并描述与 TinyStories 的 loss 差异及应如何解释。
2. 与 TinyStories 生成相同格式的文本，讨论流畅度，以及为何相同模型/预算下输出质量可能更差。

“相同架构”不表示把 10k 的词表硬套到 32k tokenizer；词表相关输入/输出维需要匹配数据资产。若调整 batch，明确报告因此改变的 token/FLOPs 预算，不把“同迭代”夸大为严格同算力。不同数据/tokenizer 的 per-token loss 不能脱离单位直接排序模型能力。

**p.44 的校外低资源例外**：在线自学且 GPU 有限者，原文建议继续在 TinyStories 上测试修改，以验证 loss 比较，而不强求耗时的 OWT 流畅训练；该提示将随后排行榜提交描述为可选。必须标注这是数据替代路线，不能声称已完成标准 OWT 实验，更不能把例外推广为全体选课学生可免交计分题。

### 38 · leaderboard（6 分；§7.5，pp.45–46；探索标注 10 B200 小时）

在规则内自行改进，尽量降低验证 loss。**两种预算必须分开**：

- 题名 **10 B200 小时**是探索标注，不是一次最终训练的时限。
- 最终 run **最多 45 分钟、单 B200，即 0.75 B200-hours**。交付要求曲线以墙钟为横轴，清楚显示少于 45 分钟的记录；不要沿用旧 90 分钟。
- **只用提供的 OWT 训练数据**。目标至少超过 naive baseline 的 loss **5.0**，即获得更低的验证 loss。

交最终验证 loss、合时限的墙钟学习曲线、方法描述，并按官方排行榜仓库流程提交。Llama/Qwen、NanoGPT speedrun、weight tying 是研究选题参考，不是必须照搬的清单；可先在 TinyStories 或 OWT 小子集探索，但不能把它们当最终 OWT 计分数据。小规模排行榜有效的改动不保证可推广到大规模。

本题是标准路线的 **6 分计分题**，不是普遍选做；校外有限 GPU 的可选提交措辞仅限上一节 p.44 例外。开放改进空间也不撤销官方 AI 禁止代写作业/排行榜实现的政策。

## 7．资源、验收与学习路线

BPE 主要消耗 CPU / 主存，LM 训练还需设备显存与矩阵计算；原文资源上限、staff 时间、探索标注都不是最低硬件保证或预算赠送。README 给出 TinyStoriesV2-GPT4 与 `stanford-cs336/owt-sample` 公共文件入口；本文不复制整套下载脚本，不下载全量数据，不把仓库 MIT 当作数据许可审查结果。

校内 Modal workspace 只面向正式选课学生，需要 Stanford Google 登录与邀请；个人账号不自动带课程额度。只使用自己的环境/代码，不在代码中存放 keys。课程指南建议同时不超过三张 GPU，不能因服务易并发就批量启动搜索。本文不购买、申请或启动任何付费资源。

学习依赖可沿以下顺序推进，但日志设施应提前就位：

| 阶段 | 必要证据 | 下一步前应排除的问题 |
| --- | --- | --- |
| 规则 → 分词 | 01–07 的答复、资产、编码数据与官方接口测试 | 字节/字符混淆、边界污染、训练/验证混用 |
| 模块 → 完整 LM | 08–18 的模块测试和资源账 | 轴、dtype、因果性、RoPE 位置、参数漏注册 |
| loss → 更新 | 19–24 的测试、观察与资源分析 | 非稳定计算、AdamW 旧次序、调度边界、局部裁剪 |
| 数据 → 生成 | 25–28 的 batch/checkpoint 合同、训练入口与解码功能 | target 错位、状态不全、无效采样分布 |
| 基线 → 消融 → OWT | 29–37 的真实日志、曲线、生成与路线说明 | 不公平预算、静默换多个因素、loss 单位不一致 |
| 排行榜 | 38 的最终 loss、预算曲线、方法及提交记录 | 探索/单次预算混淆、数据越界、资格未确认 |

这些验收项如何逐层诊断，统一进入[概念与调试指导](#/c/stanford-cs336-2026/lab/a1-basics?v=guide)。本页没有可执行代码块；列出的 pytest 命令只是官方验收导航，未运行。

## 固定来源、修改声明与许可

1. CS336 Staff，[A1 固定 PDF](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)，Spring 2026 / 26.0.3，47 页。本页完整阅读其提取文本，不声称逐页目视审校公式/插图；参考文献列表已读不等于所引论文全文已读。
2. 同提交 [README](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/README.md)、[pyproject](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/pyproject.toml)、[CHANGELOG](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/CHANGELOG.md)、[LICENSE](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/LICENSE)。固定源码和测试路径是导航；本页未审阅全部测试源码、未执行它们。
3. [Spring 2026 集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit)，仅独立概括本次实际读取的资格、安全与并发范围，不适用 A1 MIT 的自动授权。排行榜提交入口：[官方仓库](https://github.com/stanford-cs336/assignment1-basics-leaderboard)；本文没有核实账号资格或提交。
4. **修改声明**：本页将官方第一方实验要求重新组织为中文完整说明，保留全部 Problem、子问、分值和合同，加入范围澄清与本站学习链接；不提供答案，不复制第三方示例故事、论文引文/图片或第三方正则源码，不是 Stanford 官方中文版本。第一方 MIT 不自动涵盖第三方论文、数据集、依赖、外部服务。原始获取时间、完整哈希、阅读范围见 `sources/p3-a1/manifest-fragment.json`，逐题证据见 `sources/p3-a1/task-coverage.json`；P2 历史任务索引未改。

以下保留原仓库完整版权与许可条件：

> Copyright 2025 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
