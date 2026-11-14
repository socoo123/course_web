---
title: A1 从零训练语言模型：P2 任务拆解与来源导航
kind: 编者任务地图；不是完整实验指导、作业解答或讲义全文翻译
source: CS336 Assignment 1 (basics), Spring 2026, Version 26.0.3
source_commit: a158843b20107949f1a8d7df1b05cd33b9166712
source_read_scope: 已连续阅读固定 PDF 的全部 47 页提取文本（含参考文献）；未逐页目视校验公式与图片
status: P2 来源与任务拆解已写；A1 实现、实验和完整指导均未完成
license: 第一方讲义与仓库文档按 MIT 使用；完整版权与许可见页底；第三方材料不继承 MIT
execution: 本页未执行安装、测试、训练、数据下载或收费计算；所列验收方式是读者后续工作，不是通过记录
---

# 先认清 A1 的三条流水线

A1 不是“搭出一个能输出文字的网络”就结束，而是把三个不同层次连起来：

1. **文本 → tokenizer 资产 → token ID 数据集**：词表和有序 merges 是训练出来、随后冻结的独立资产。
2. **token ID → logits → loss → 参数更新**：网络前向、损失、优化器与数据加载各有自己的合同。
3. **checkpoint → 生成与可比较实验**：能恢复状态、能记录训练预算，才有条件讨论学习率、消融和数据差异。

本页只帮助你找到每项任务、确定依赖与产物、安排工作顺序。**P2 没有提供完整 `lab.zh.md`，也没有完成 A1 实验或每题实现指导。**下面保留讲义的真实 `Problem` 标识；这些标识比中文简称更适合回到固定原文定位。页码均指 PDF 印刷页码。

## 现在可以启动什么

- 学完 [L01：课程导论与分词](#/c/stanford-cs336-2026/lec/lec01?v=notes)，可进入 §2 的 Unicode、UTF-8、BPE 与 tokenizer 合同，先在自造小文本上理解边界，再自行实现、对接官方测试。L01 不意味着整套 tokenizer 已经实现或验证。
- 学完 [L02：PyTorch、einops 与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)，可开始 §3.2 的轴与批处理练习、§3.3 的 Linear/Embedding，预先列出参数、梯度、优化器状态和激活四类资源账目。
- **从 §3.4 的完整架构到 §4–7 的闭环训练与实验，本站路线安排在 L03 以后、P3 展开。**本页仅提供索引与验收边界，不把 L01/L02 当成掌握 RMSNorm、SwiGLU、RoPE、AdamW 与消融设计的证明。这是编者学习顺序，不是官方禁止提前阅读讲义。

准备不足时，按需补 [Python 实验工程](#/c/stanford-cs336-2026/lec/bridge04?v=notes)、[概率与信息论](#/c/stanford-cs336-2026/lec/bridge02?v=notes)、[张量形状](#/c/stanford-cs336-2026/lec/bridge01?v=notes)、[PyTorch 内存语义](#/c/stanford-cs336-2026/lec/bridge05?v=notes)、[数值稳定性](#/c/stanford-cs336-2026/lec/bridge07?v=notes)和[资源估算与实验纪律](#/c/stanford-cs336-2026/lec/bridge08?v=notes)。

## 阶段 0：先固定规则，而不是先下载数据

**原文：§1，pp.1–3；README；pyproject。依赖：无。输入：固定仓库和讲义。产物：你自己的版本、环境、资源与任务记录。**

- 使用本页页底的固定提交；PDF 内文是 **Spring 2026 / 26.0.3**。README 标题遗留的 “Spring 2025”、LICENSE 的 2025 版权年份、包版本 `26.0.0` 都不能代替讲义版次。
- 当前 `pyproject.toml` 声明 Python `>=3.12,<3.14`、PyTorch `~=2.11.0`，README 使用 `uv`。环境应独立于其他作业；本页没有安装或证明当前平台兼容。README 的 `uv run` 会在需要时解析、准备环境，不等于零下载操作。
- 自己写的实质逻辑放在 `cs336_basics/`；`tests/adapters.py` 只负责把接口接到自己的实现，不能把实质逻辑塞进适配器。**不要改测试去适配错误实现。**
- §1 限制直接调用 `torch.nn`、`torch.nn.functional`、`torch.optim` 的现成组件；列出的例外是 `Parameter`、容器类和 `Optimizer` 基类。后续 §3.3.1 明确允许用 `torch.nn.init.trunc_normal_` 初始化，SwiGLU 任务明确允许 `torch.sigmoid`。不能只看总则漏掉这些显式例外，也不能据此扩大成允许现成 Linear/Attention/AdamW。
- **官方 AI 政策允许概念层面问答与底层 API 文档查询，不允许 AI 实现任何作业部分，包括排行榜代码和自动补全。**本页没有可提交实现；不要要求助手补齐 adapters、训练器或各题答案。

**阶段验收**：能说清哪些是自己实现、哪些库调用被明确允许；区分“接口测试通过”“实验达到目标”和“教学页写完”。选课学生按官方要求提交 `writeup.pdf` 与 `code.zip`；个人自学记录不等于已获 Gradescope 或课程算力权限。

## 阶段 1：分词资产与编码数据

**原文：§2.1–2.7，pp.3–13。依赖：L01、Python 字符串/bytes/迭代器。输入：小文本，随后是相应训练语料；词表上限与特殊 token 列表。产物：词表、有序 merges、编码/解码接口、train/valid token 数组、资源与压缩率记录。**

| 顺序与定位 | 真实任务名 | 应留下的证据 |
| --- | --- | --- |
| 1 · §2.1 p.3；§2.2 pp.4–5 | `unicode1` — Understanding Unicode；`unicode2` — Unicode Encodings | 按各小问提交短答、反例与解释，不把码点、字符数、UTF-8 字节数混为一谈 |
| 2 · §2.5 p.9 | `train_bpe` — BPE Tokenizer Training | 从文本路径、最大词表大小和特殊 token 得到 `dict[int, bytes]` 与按产生顺序排列的 merges |
| 3 · §2.5 pp.9–10 | `train_bpe_tinystories` — BPE Training on TinyStories；`train_bpe_expts_owt` — BPE Training on OpenWebText | 分别保存 10,000 / 32,000 上限词表与 merges；记录时间、内存、最长 token、profiling 或语料对比的题目要求 |
| 4 · §2.6 pp.11–12 | `tokenizer` — Implementing the tokenizer | 从已有词表/merges 加载；支持 encode、decode、延迟产出 ID 的 encode_iterable 与特殊 token |
| 5 · §2.7 pp.12–13 | `tokenizer_experiments` — Experiments with tokenizers | 两语料各抽样 10 个文档；压缩率、跨语料分词对比、吞吐外推；分别编码 train/valid 并解释存储 dtype |

**工作顺序**：先理解 §2.3–2.4 的训练规则 → 小输入验证训练器 → tokenizer 正确性 → 小规模资源测量 → 再决定是否运行完整语料训练与编码。工程上可用小词表先开发 tokenizer，不必等大型 OWT BPE 结束才继续。

**验收入口**：讲义给出 `tests/test_train_bpe.py`、`tests/test_tokenizer.py`，适配器分别是 `run_train_bpe`、`get_tokenizer`。除此之外，还要保留实验短答和资产；只跑单元测试不能替代 §2.7。

三个易混边界决定后续数据是否可信：

- 特殊 token 在 BPE 训练时是硬分界，**不参与 merge 统计，也不能跨它合并**；编码时则应保留为单一 token。普通 pre-token 边界同样不能被 merge 穿过。
- 训练得到的 merges 有固定顺序，编码不是重新在当前输入上统计频次、再训练一次。
- 流式编码必须处理切块边界；不能仅凭“每块都能编码”断言与整体编码一致。验证集小样本可按讲义用于开发调试，但不能把在验证集上训练过的调试 tokenizer 冒充独立验证的正式资产。

§2.7(c) 对 825 GB Pile 的问题是**吞吐估计**，不是要求下载 Pile。C++/Rust 重写是 §2.5 明确列出的可选优化，不是完成 BPE 的先决条件。

## 阶段 2：从轴合同进入最小模块

**原文：§3.1–3.3，pp.13–19。依赖：L02、张量形状与参数注册。输入：token ID 或末维为输入特征的张量；给定权重。产物：Linear、Embedding 及明确的输入/输出轴合同。**

| 定位 | 真实任务名 | 产物与验收 |
| --- | --- | --- |
| §3.3.2 p.18 | `linear` — Implementing the linear module | 无 bias 的自定义模块；`run_linear` → `test_linear` |
| §3.3.3 pp.18–19 | `embedding` — Implement the embedding module | token ID 查表，embedding 维在末轴；`run_embedding` → `test_embedding` |

**工作顺序**：先读 §3.2 与 §3.2.1 的 batch-like dimensions / 数学记号 → 记录权重与激活的轴名 → 按 §3.3.1 初始化 → 对接测试。形状相同并不证明轴语义正确；“数学采用列向量”也不是“必须在内存中列优先存储”的指令。

**阶段验收**：能解释 token ID 的 `(B,T)` 如何变成 `(B,T,d_model)`，以及 Linear 保留哪些前导维。此处不实现完整 Transformer，也不提前填出资源核算题的数值答案。

## 阶段 3：架构组件与完整前向（L03 以后）

**原文：§3.4–3.5，pp.19–28。依赖：阶段 2、注意力/残差/归一化概念。输入：权重、激活、位置和掩码。产物：各组件、pre-norm block、输出 logits 的 Transformer LM，以及资源核算书面结果。**

| 推荐顺序与定位 | 真实任务名 | 讲义验收入口 / 交付 |
| --- | --- | --- |
| 1 · §3.4.1 pp.19–20 | `rmsnorm` — Root Mean Square Layer Normalization | `run_rmsnorm`；`test_rmsnorm` |
| 2 · §3.4.2 pp.21–22 | `positionwise_feedforward` — Implement the position-wise feed-forward network | SwiGLU；`run_swiglu`；`test_swiglu` |
| 3 · §3.4.3 pp.22–23 | `rope` — Implement RoPE | `run_rope`；`test_rope` |
| 4 · §3.4.4 pp.23–25 | `softmax`；`scaled_dot_product_attention` | `run_softmax` / `run_scaled_dot_product_attention`；softmax 及三维、四维 attention 测试 |
| 5 · §3.4.5 pp.25–26 | `multihead_self_attention` — Implement causal multi-head self-attention | `run_multihead_self_attention`；对应测试 |
| 6 · §3.5 pp.26–27 | `transformer_block`；`transformer_lm` | 对应 `run_transformer_block` / `run_transformer_lm` 与测试 |
| 7 · §3.5 pp.27–28 | `transformer_accounting` — Transformer LM resource accounting | 五组小问：参数/装载内存、前向矩阵乘法/FLOPs、主要开销、模型大小和上下文长度的变化 |

**工作顺序**：独立组件 → 带因果约束的多头注意力 → block → LM → 基于实际架构核算。不能用一个 loss 下降的端到端 run 代替组件验收。

**阶段验收要点**：LM 的训练接口输出 **logits**，不是已经做过 softmax 的概率；本讲义 attention mask 的 `True` 表示允许关注；RoPE 施加于 Q/K，而非 V。`transformer_accounting` 的 “GPT-2 XL-shaped” 使用**本作业架构**，不是照抄历史 GPT-2 的参数账。融合 QKV 投影是脚注 stretch goal，不是必做条件。

## 阶段 4：损失与更新规则（L03 以后）

**原文：§4.1–4.5，pp.28–34。依赖：阶段 2–3、自动微分、数值稳定性。输入：logits/目标 ID、参数/梯度、优化器状态与步数。产物：稳定 loss、AdamW、调度与裁剪，以及两项书面/观察任务。**

| 定位 | 真实任务名 | 验收方式 |
| --- | --- | --- |
| §4.1 pp.28–29 | `cross_entropy` — Implement cross-entropy | `run_cross_entropy` → `test_cross_entropy` |
| §4.2.1 pp.29–31 | `learning_rate_tuning` — Tuning the learning rate | 在讲义 SGD 小例子上观察指定学习率，提交真实观察短答；这不是后面的完整模型学习率搜索 |
| §4.3 pp.31–32 | `adamw` — Implement AdamW | `get_adamw_cls` → `test_adamw` |
| §4.3 pp.32–33 | `adamw_accounting` — Resource accounting for training with AdamW | 分开参数、激活、梯度、优化器状态；完成四个资源小问 |
| §4.4 pp.33–34 | `learning_rate_schedule` — Implement cosine learning rate schedule with warmup | `get_lr_cosine_schedule` → `test_get_lr_cosine_schedule` |
| §4.5 p.34 | `gradient_clipping` — Implement gradient clipping | `run_gradient_clipping` → `test_gradient_clipping` |

**工作顺序**：先各自验证 loss 与更新规则 → 再接调度/裁剪 → 最后进入训练循环。核对固定版 AdamW 的更新顺序，不混入旧版讲义；裁剪针对所有参数梯度组成的整体范数，不是逐张量各裁一次。资源题中的 80 GB/H100 是纸笔题设，不能据此把 2026 实训基准改成 H100。

## 阶段 5：数据、恢复与训练闭环（L03 以后）

**原文：§5.1–5.3，pp.34–37。依赖：分词数据、模型、优化器。输入：磁盘 token 数组、配置、恢复文件或初始状态。产物：成对训练 batch、可恢复 checkpoint、可配置训练入口与日志。**

| 顺序与定位 | 真实任务名 | 验收方式 |
| --- | --- | --- |
| 1 · §5.1 pp.34–35 | `data_loading` — Implement data loading | 输入与右移一位目标均为 `(batch_size, context_length)`，放在指定设备；`run_get_batch` → `test_get_batch` |
| 2 · §5.2 pp.35–36 | `checkpointing` — Implement model checkpointing | 保存/恢复模型、优化器与 iteration；`run_save_checkpoint` / `run_load_checkpoint` → `test_checkpointing` |
| 3 · §5.3 pp.36–37 | `training_together` — Put it together | 可配置超参数、内存映射数据、checkpoint 路径、周期性训练/验证记录；讲义没有为整套脚本指定单个通过即完成的测试 |

**工作顺序**：先验证一个 batch 的对齐与范围 → checkpoint 往返 → 独立的小规模训练闭环 → 再考虑长 run。训练样本需要输入窗口之外的下一个 token 作为最后一个目标；mmap 文件的 dtype 与格式必须和写入时匹配。

**阶段验收**：保存权重不等于恢复训练。至少按讲义恢复 AdamW 状态和步数；若额外声称“续训逐步完全复现”，还要定义并保存相应随机/采样状态，那是比本页任务地图更强的工程承诺。不要把测试 checkpoint 往返通过写成完整断点续训实验已复现。

## 阶段 6：生成接口（L03 以后）

**原文：§6，pp.37–38。依赖：tokenizer、完整 LM、可加载 checkpoint。任务：`decoding` — Decoding。输入：prompt、生成长度上限、temperature、top-p。产物：遇 `<|endoftext|>` 或达到长度上限时停止的续写。**

**工作顺序**：先确认取的是最后一个位置的 next-token 分布 → 再处理逐 token 生成与停止条件 → 再比较采样参数。这里只列接口，不给采样实现。

**验收方式**：逐项检查讲义要求的四项功能；之后由 §7.2 的 `generate` 交付训练模型的实际生成文本。一个接口能生成 ID，不证明模型学会语言；只展示一段好看的样本，也不替代验证 loss。

## 阶段 7：先建立可比较的 TinyStories 基线（L03 以后）

**原文：§7.1–7.2，pp.38–42。依赖：阶段 1–6。输入：固定数据/词表、训练配置、资源预算。产物：实验日志、曲线、checkpoint 与实际生成样本。**

| 顺序与定位 | 真实任务名 | 必须留下的实验记录 |
| --- | --- | --- |
| 先于长训练 · §7.1 pp.38–39 | `experiment_log` — Experiment logging | 追踪实现和实验记录；loss 对梯度步数、对墙钟时间的曲线 |
| §7.2.2–7.2.3 pp.39–41 | `learning_rate` — Tune the learning rate | 多个学习率的曲线与搜索策略、目标验证 loss；包含至少一次发散的稳定边界观察 |
| §7.2.3 p.41 | `batch_size_experiment` — Batch size variations | 从 batch 1 到可用显存边界的多组对照，包含典型 64/128；必要时重调学习率，报告发现 |
| §7.2.3 p.42 | `generate` — Generate text | 至少 256 tokens，或在首个 EOS 处停止；评价流畅度并说明至少两个影响因素 |

**工作顺序**：日志设施应在基线 run 前就接入。§7.2.3 推荐单 minibatch 过拟合作为调试手段；通过这种调试不等于达到独立验证集目标。比较 batch 时记录 `batch × steps × context`，不能只说“都跑了同样步数”就忽略 token 预算改变。

**阶段验收**：以你选择并明确标注的标准/低资源路线判断目标，下面两者不能混写。loss 是每 token 验证交叉熵；perplexity 是其指数，不能把 loss 的 1.45/2.00 当作困惑度阈值。

## 阶段 8：结构消融，再到 OWT（L03 以后）

**原文：§7.3–7.4，pp.42–45。依赖：可复用的 TinyStories 基线与日志。输入：基线配置；每次明确改变的架构因素或数据集。产物：对照曲线、描述与生成结果。**

| 定位 | 真实任务名 | 要比较什么 |
| --- | --- | --- |
| §7.3 p.42 | `layer_norm_ablation` — Remove RMSNorm and train | 去除所有 RMSNorm；原最佳学习率与重新寻找的稳定设置 |
| §7.3 p.43 | `pre_norm_ablation` — Implement post-norm and train | post-norm 对 pre-norm |
| §7.3 p.43 | `no_pos_emb` — Implement NoPE | 无位置嵌入对 RoPE |
| §7.3 pp.43–44 | `swiglu_ablation` — SwiGLU vs. SiLU | 近似匹配参数量后的门控/非门控 FFN，不是仅删掉一条分支就宣称公平对比 |
| §7.4 pp.44–45 | `main_experiment` — Experiment on OWT | 按讲义保留与 TinyStories 相同架构和总训练迭代次数，必要时重调学习率/batch；提交 OWT 曲线、loss 解释与生成文本 |

**工作顺序**：先记录基线，再分别做可解释的单因素对照；不要把四种消融累计叠在同一个模型上。OWT 使用与其匹配的 tokenizer/数据资产，不能在不知道词表和文本分布不同的情况下直接给两个语料的 loss 排名。

**阶段验收**：每个实验都能回溯修改、预算与结果。低资源框明确允许校外有限 GPU 学习者继续在 TinyStories 上研究修改；如此完成的是标注过的数据替代路线，**不是已经完成 OWT 标准实验**。

## 阶段 9：排行榜是独立的预算合同

**原文：§7.5，pp.45–46。依赖：前述基线、实验纪律与可用 B200。任务：`leaderboard` — Leaderboard。输入：官方提供的 OWT 训练集、自己的改进。产物：最终验证 loss、墙钟曲线、方法描述和按官方仓库流程提交的记录。**

- 固定版最终 run **最多 45 分钟 / 单 B200，即 0.75 B200-hours**，不是旧版的 90 分钟；题目标题的 **10 B200 hrs** 是探索预算提示，不是最终一次训练可跑 10 小时。
- 只允许使用提供的 OWT 训练数据；期望超过 naive baseline loss 5.0，即得到更低的验证 loss。曲线必须显示符合时限的墙钟横轴。
- 这是标准讲义中 **6 分的计分题**，不能笼统标为所有学生都可省略。另一方面，p.44 的低资源提示对校外学习者把 leaderboard submission 描述为可选，并建议留在 TinyStories。本文清楚保留这两个适用范围，不代课程 staff 修改要求。
- 模型改进方式可自行研究；weight tying、NanoGPT speedrun 等是选题建议，不是额外必做清单。排行榜小尺度有效的修改，不自动推广到大规模预训练。

**阶段验收**：真实运行证据、预算与数据约束同时成立。本页没有申请或消费 GPU、访问排行榜提交权限，也没有提供排行榜代码。

## 资源与权限：先选路线，再作承诺

### 标准参考与官方低资源路线不是同一项成绩

| 路线 | 原文条件与目标 | 不能推断成什么 |
| --- | --- | --- |
| TinyStories 标准参考 | §7.2.1：词表 10,000、context 256、`d_model=512`、`d_ff=1344`、4 层/16 头、RoPE Θ=10,000；处理约 **327.68M tokens**；`learning_rate` 验证 **loss ≤ 1.45**；正确且高效实现的单 B200 参考单次约 20–30 分钟 | 本页实测、最低显存要求，或包括所有搜索/消融在内的总完成时间 |
| 官方 CPU/MPS 低资源 | pp.40–41：降到约 **40M tokens**，目标可放宽到 **loss ≤ 2.00**；staff 示例是 `32 × 5000 × 256 = 40,960,000` tokens，M4 Max / 36 GB 上 CPU 82 分钟、MPS 36 分钟，loss 1.80 | 与标准任务等效，或任何笔记本都能复现相同速度/loss |
| 更小的机制练习 | 自造短文本、少量张量或纸笔预算，只核对一个明确机制 | 官方低资源训练已经完成，或已经具备生成质量 |

p.3 的“不到五分钟 MPS / 约三十分钟 CPU”是短小可行性陈述，不是完整 A1 时间保证；不能拿它覆盖 p.40 的具体 40M-token 实验。p.40–41 对 MPS 的 TF32/编译警告注明了当时 PyTorch 2.9.0 经验，当前固定依赖声明为 2.11 系列；本页没有重新测平台行为。

### BPE 主要需要 CPU 和主存，但不能凭包络保证能跑

§2.5 给出的资源包络是：TinyStories 10k BPE **≤30 分钟、≤30 GB RAM，无 GPU**；OWT 32k BPE **≤12 小时、≤100 GB RAM，无 GPU**。这些上限式描述**不是保证的最低配置**，也不是“内存够了便一定能达到时限”。实现效率、进程数、数据结构与 I/O 都会影响结果；讲义没有给完整 LM 的普遍最低主存/CPU 核数。

先做小规模 profiling，量出自己的峰值主存和吞吐，再判断完整运行是否在预算内。不要把小样本完成写成全语料 BPE 完成，不要把磁盘大小当成训练时主存峰值。

### 公开资料不等于免费校内算力

官方 README 提供 TinyStoriesV2-GPT4 与 `stanford-cs336/owt-sample` 的公共下载入口；本页没有下载数据，也没有单独完成数据集许可审查。校内 Modal workspace 只面向选课学生，需 Stanford Google 登录与邀请，使用自己的环境；公开自学 Modal 账号不会自动获得课程 workspace 或预算。不要在代码里放 API keys，也不要读取他人代码。

校外可以选择自己的本地资源和明确标注的低资源路线；本页不发起云端作业、不购买资源，也不承诺 Gradescope、课程 Slack 或排行榜资格。先完成环境/组件理解，并不要求立即下载全量数据或启动 GPU。

## 阅读与完成状态

- **本页实际依据**：固定 47 页 PDF 的全部提取文本，包含任务、资源框与参考文献；README、LICENSE、pyproject、CHANGELOG 全文；仓库树的完整文件路径/大小清单；集群指南开头至并发说明和 GPU 段开头。
- **没有声称做过**：PDF 公式/图片逐页目视校验、引用论文全文精读、官方测试源码逐项审查、依赖安装、数据下载、任何 A1 实现或训练。教学页面验收与课程实验执行分开记录。
- **P3 的接续资产**：`sources/p2-a1/task-index.json` 登记全部 38 个计分 Problem 及其子问、节页、依赖、输入产物和验收入口。它是任务索引，不是完成记录；所有实现和实验状态保持未执行。

## 固定来源、修改说明与许可

1. **CS336 Staff，A1 第一方讲义**：[Spring 2026 / Version 26.0.3 PDF](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)。固定 commit：`a158843b20107949f1a8d7df1b05cd33b9166712`；PDF完整 SHA256 见 `sources/p2-a1/manifest-fragment.json`。本页以节号、Problem ID、页码导航，不复刻原文全篇或第三方示例文本。
2. 同一固定提交的 [README](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/README.md)、[pyproject](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/pyproject.toml)、[CHANGELOG](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/CHANGELOG.md)、[仓库树](https://github.com/stanford-cs336/assignment1-basics/tree/a158843b20107949f1a8d7df1b05cd33b9166712)。测试名称来自讲义，文件路径由已保存树定位；不是本页执行结果。
3. [CS336 Spring 2026 集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit)，复用 2026-11-14 的 P1 快照，仅自主概括资格、安全边界；该文档未发现明确再利用许可，不继承 A1 的 MIT。
4. 第一方文档许可：[固定 LICENSE](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/LICENSE)。**修改声明**：本页由编者重新组织为中文任务地图，压缩任务要求并加入学习顺序、状态区分与资源警示；不是 Stanford 官方中文发布，不包含解答。MIT 只覆盖相应第一方软件和文档，不自动覆盖引用论文、第三方图片、数据集、依赖包或外部服务。全部原始文件路径、获取时间、SHA256、实际读范围见 `sources/p2-a1/manifest-fragment.json`；沿用 P1 采集时间和哈希，不把本次阅读日期当成重新采集。

以下保留原仓库完整版权与许可：

> Copyright 2025 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
