---
title: A5 推理强化学习：完整任务与实验合同
kind: 固定官方任务的完整索引与原创教学解读；非全文翻译、非答案
source: CS336 Assignment 5 (alignment), Reasoning RL, Spring 2026, Version 26.0.0
source_commit: c2734a26308710949fe13226960a1e8cece94b7e
source_read_scope: 全部39页提取文本；原PDF物理页11、21、28、29、35、36、38视觉核对；README、CHANGELOG、相关helpers/adapters/tests/config静态阅读
status: P7 作者交接；28个计分任务、11个正式字母子问、90分；不代表最终验收
execution: 未安装作业环境、执行官方测试、训练、评测、下载数据或模型、启动GPU或Modal、访问提交服务
license: 固定仓库未发现整体LICENSE；不主张全文翻译许可；局部grader与模型及数据许可分别核验
---

# 从会续写的基座到可比较的推理 RL 实验

A5 正篇研究 **OLMo-2-0425-1B 在 GSM8K 上的推理强化学习**。工作不是单独实现一个名为 GRPO 的 loss，而是贯通提示、生成、答案解析、梯度估计、训练同步和多随机种子比较。一个解析错误可以伪装成能力不足；一个归一化错误可以伪装成算法进步；一个只展示最好 seed 的图可以伪装成稳定改进。

本页保留固定官方讲义的**每个计分任务、正式字母子问及未编号约束**，用独立结构组织要求，不镜像或逐段翻译整篇讲义。所有“实现、运行、提交”都是**学生尚须独立完成的要求**，不是本站执行记录。[概念与排错指导](#/c/stanford-cs336-2026/lab/a5-reasoning?v=guide) 不提供可提交实现、数学题答案或实验结论。安全／SFT／DPO 补充是[另一份完全选做作业](#/c/stanford-cs336-2026/lab/a5-safety-optional)，不是 A5 正篇的额外必做部分。

## 0．先固定版本、权限与实验对象

### 0.1 版本不是一个数字

- 本页依据 **Spring 2026、handout v26.0.0、39 物理页**，仓库提交固定为页头 SHA。
- CHANGELOG 最新已发布条目是 **2.0.1（2026-06-03）**；2.0.0（2026-05-20）加入 MaxRL、GSPO、three-shot、四 seed 与数学题，并将旧 Qwen/MATH 组合换成 OLMo/GSM8K。`pyproject.toml` 的 package version 仍为 **1.0.0**，不拿它覆盖手册封面版本。
- 必做测试是 `tests/test_grpo.py`，经 `tests/adapters.py` 的七个主篇入口调用学生代码。测试中 tiny GPT-2 只是接口／梯度夹具，**不是允许替代正式实验基座**。
- `cs336_alignment` 是学生实现位置；staff 提供 vLLM 生命周期／权重同步、模型加载器、数学 grader 和三种提示文件。可写自己的调试检查，但不能修改原始测试来制造通过。

### 0.2 提交与 AI 政策

向 Gradescope 提交排版后的 **`writeup.pdf`** 和本人所写代码 **`code.zip`**。固定 `test_and_make_submission.sh` 会运行必做 pytest 后打包；其中测试调用带 `|| true`，所以 zip 出现不代表测试通过。脚本排除数据目录、权重、`.txt`、`.json`、日志等，不能假定你的实验配置和复现证据已经自动进入提交包。本站没有运行该脚本。

官方 AI 政策只允许高层概念问答、函数签名／库 API 辅助。**禁止 AI 实现任何作业或排行榜代码，包括 coding agent 和 AI 自动补全**；实验也须本人编写。固定 `AGENTS.md` 进一步排除代写 Python／伪代码、填实现、给计分题答案和替学生完成工程。不要修改该政策文件，在线求助须附其内容，关闭 AI 自动补全。本页只提供任务导航与概念检查，不是作业解答。

### 0.3 权利与访问边界

完整固定 tree 没有整体 LICENSE／COPYING；公开可读不等于授权全文翻译。本站采用完整要求索引、有限必要接口名和原创解释，不发布原讲义镜像。`drgrpo_grader.py` 自带 Garena 2025 **Apache-2.0** 文件头；OLMo 模型卡标注 **Apache-2.0**，GSM8K 数据卡标注 **MIT**。这三项都不能推导出讲义或整个仓库的许可。

正式基座为 **`allenai/OLMo-2-0425-1B`**，不是 SFT／Instruct 版本。它经历约 4T tokens 的预训练与中期训练；课堂自己训练的小模型通常不足以成为此数学实验的等价起点。数据使用仓库 `data/gsm8k/train.jsonl` 与 `test.jsonl`，后者按题设作 **validation**，会被调参与观察，因此不能称从未使用的独立测试集。数据卡 main 划分为 7,473／1,319 条；手册建议使用其中 6,400／1,024 条，而非声称全数据恰有这些数量。此处只读文档与路径，未读取题库内容或下载权重。

固定环境要求 Python **≥3.12、<3.13**，GPU extra 指向 vLLM **0.19.1**、CUDA 12.9／Torch 索引和指定 FlashAttention wheel。README 的两阶段 `uv sync` 是来源说明，不是本机已适配证明。模型加载器用 BF16，CPU 走 eager、GPU 走 FlashAttention-2；正式训练路线为训练与推理分置两 GPU。`modal_utils.py` 指定 **B200:2、最多4容器、每任务1小时**，未填 SUNET_ID 时顶层抛错，并依赖 Wandb secret。不要把公开源码、课程账户、云配额或私人目录混为一谈；不索取凭据、不绕过权限、不在本站启动这些服务。

原 §4.2.1 也允许学生自行实现模型与预训练权重加载器，但架构必须匹配指定 OLMo 基座；不是借机更换模型。模型名或目录均可作为加载位置，后者通常来自模型与 tokenizer 的 `save_pretrained` 输出。这里保留加载／保存路径合同，不提供加载器实现，也不下载或保存真实权重。

## 1．评分与交付导航

**28 个 Problem，共 90 分；11 个正式字母子问**。字母子问只有 T01 的 a–b、T02 的 a–c、T10 的 a–c、T17 的 a–c。T24 文中的 (a)(b)(c) 是三种待比较方法，不是另三道子题。下面的 T 编号是本站索引，官方 ID 保留在每题。

| 本页 | 内容 | 分值 | 原物理页 |
|---|---|---:|---:|
| T01 | 三种 prompting baseline | 5 | 7 |
| T02 | baseline 与估计器方差 | 5 | 10–11 |
| T03 | prompt／response 分词 | 1 | 14–15 |
| T04 | response log-prob 与 entropy | 1 | 15–16 |
| T05 | rollout reward | 1 | 16–17 |
| T06 | GRPO 组归一化 | 1 | 17–18 |
| T07 | on-policy token loss | 1 | 19–20 |
| T08 | sequence loss reduction | 0.5 | 20 |
| T09 | 标准 on-policy train step | 5 | 22–24 |
| T10 | 标准 GRPO 实验 | 10 | 25 |
| T11 | 学习率扫描 | 3 | 26 |
| T12 | prompt 消融 | 3 | 26 |
| T13 | 长度归一化思考 | 1 | 27 |
| T14 | Dr. GRPO advantage 开关 | 0.5 | 27 |
| T15 | constant reduction | 0.5 | 27 |
| T16 | RFT 思考 | 2 | 28 |
| T17 | 难度重加权推导 | 6 | 29 |
| T18 | advantage normalizer 思考 | 2 | 29–30 |
| T19 | MaxRL advantage 开关 | 0.5 | 30 |
| T20 | on-policy 变体 train step | 2.5 | 30–31 |
| T21 | 四种 on-policy 变体实验 | 10 | 31–32 |
| T22 | pairwise surrogate 推导 | 2 | 34 |
| T23 | off-policy token ratio loss | 1 | 35 |
| T24 | importance reweighting 思考 | 2 | 36 |
| T25 | GSPO sequence ratio loss | 1 | 37 |
| T26 | off-policy train step | 2.5 | 37 |
| T27 | 四种 off-policy 实验 | 10 | 38 |
| T28 | 自拟单因素估计器 | 10 | 38 |

## 2．提示与评分：先知道奖励在测什么

### T01．三种 baseline（5 分）

官方 ID：`prompting_baselines`。原 §3、p7；前置约束在 pp4–6。

**（a）运行与错误分类。** 学生编写评估脚本，在正式基座／GSM8K 上分别使用 zero-shot `question_only`、zero-shot `r1_zero`、few-shot `r1_zero_three_shot`。每种提示分别统计三类生成：①format=1 且 correctness=1；②format=1、correctness=0；③format=0、correctness=0。**至少观察十条第②类**，核实其中多少其实正确但解析失败；第③类也须检查这种现象。提交几句分析、评估指标、若干实际 prompt／response 示例；不能拿人工编造示例充作运行输出。

**（b）行为分析。** 比较模型是否只是回答问题，还是续写其他角色、题目、说明等；解释 zero-shot CoT 与 three-shot 如何改变输出行为。提交几句有实际示例支撑的评论。不要将模型卡的 **8-shot** 成绩当作本题 three-shot／zero-shot 对照。

**全体 prompting 实验合同：** temperature=1、top-p=1、最多生成512 tokens。两种 r1 提示使用 `</answer>` 停止串并保留该串到输出；`question_only` 不用这个 stop。r1 提示的开头 `<think>` 已在 prompt 内，生成应完成后续结构；question-only 虽名字“只给问题”，仍要求 boxed 最终答案。three-shot 文件提供固定三例，不能偷偷换成自己挑出的更有效示例再称原 baseline。

**评分合同：** `r1_zero_reward_fn` 服务于两种 r1 提示；`question_only_reward_fn` 寻找 boxed 答案，不能用选做作业的“最后一个数字”解析器替代。`ground_truth` 仅取 GSM8K answer 字段 `####` 后的最终答案并去空白。总 reward **等于 binary answer reward**，format 只记录、不加分。

固定源码比“有标签就算格式正确”更严格：r1 检查字面子串 `</think> <answer>` 及 `</answer>`，从最后一个 `<answer>` 之后抽取，再去关闭标签；若内部还有 boxed 则继续抽取。换行替换那一个空格也可能不通过格式门。question-only 走最后一个 boxed 及括号匹配；不能把任意包含答案数字的文本当正确。grader 默认 `fast=True`，使用规范化匹配／符号检查，不自动运行较慢的 math-verify 路线；格式失败直接得到全零，格式成功也可能答案解析失败。**“验证奖励”不是无误的数学真值，也没有验证每步推理。**

### T02．baseline 方差分析（5 分）

官方 ID：`baseline_calcs`。原 pp10–11，式18–19。

题设二元动作 $A\in\{0,1\}$，$p=\sigma(\theta)$，奖励为动作1的指示函数，$n$ 个动作独立同分布取自该策略。按题设分别完成：

- **（a）** 无 baseline 的样本均值 policy-gradient 估计器方差：给出以 $n,p$ 表示的表达式及推导。
- **（b）** 减去常数 baseline $b$ 后的估计器方差：给出以 $n,b,p$ 表示的表达式、推导和讨论。
- **（c）** 代入 population-mean baseline $b=p$，与未调整估计器比较；判断是否始终更低／更高，或依赖 $p$。

本题不是“baseline 一定降方差”的背诵题；本站不提供这三个提交用结论。背景 §4.1 还区分动作无关 baseline 与包含自身样本的 group mean：后者在有限组下有手册明确写出的缩放，不能直接套前者的严格无偏论证。

## 3．从 token 合同到一次正确更新

这一阶段只实现标准 **on-policy**：每个 rollout batch 完成 **一次 optimizer step**。把它分成多个 microbatch 并累计梯度仍是一次更新；把每个 microbatch 都更新一次则已经改变算法。

### T03．分词与 response mask（1 分）

官方 ID：<code>tokenize_<wbr>prompt_<wbr>and_<wbr>output</code>。原 pp14–15。

交付同名函数，接受 prompt／output 字符串列表和 tokenizer。**分别分词、不添加 special tokens**，然后直接连接，不插 EOS、BOS 或 separator。设批内拼接后最大长度为 $M$，三个返回张量均为 `(batch_size, M−1)`：`input_ids` 去掉末 token，`labels` 去掉首 token；`response_mask` 与 **labels** 对齐，只在标签来自 response 时为1，prompt 与 padding 为0。这不同于先连接字符串再分词，也不同于按 input 位置标 response。

对接 adapter `run_tokenize_prompt_and_output`；官方选择器 `test_tokenize_prompt_and_output`。本站未执行。

### T04．log-prob 与可选 entropy（1 分）

官方 ID：`get_response_log_probs`。原 pp15–16。

交付同名函数，输入 model、对齐的 input_ids／labels 和 `return_token_entropy`。返回每位置指定 label 的条件 log-prob，shape 为 `(batch_size, sequence_length)`；开关为真时另返回同形状 `token_entropy`，为假时不要求该键。entropy 是**该位置整个 next-token 分布**的熵，不是已采样 token 的负 log-prob，也不是整条 response 的平均。

调用者负责模型设备与是否需要梯度；训练的当前 policy 分数必须保留梯度，不能因“评分”二字一律关闭 autograd。对接 `run_get_response_log_probs`，选择器同名去 `run_`、加 `test_`。

### T05．rollout rewards（1 分）

官方 ID：`compute_rollout_rewards`。原 pp16–17。

交付同名函数，输入 reward_fn、rollout responses 与按组重复的 ground truths。列表长度都是 **responses 数**，即 prompt 数乘 group size。返回未归一化 `raw_rewards`，shape `(rollout_batch_size,)`，以及 metadata；**至少含整 rollout batch 的平均 total reward 和 format reward**。必须保持 prompt、response、答案的对应关系。

对接 `run_compute_rollout_rewards`；选择器 `compute_rollout_rewards`。通用函数按 reward_fn 返回值工作；测试夹具含分数奖励，不能因为真实 GSM8K 为二元奖励就硬编码所有测试输入只有0／1。

### T06．标准 GRPO 组归一化（1 分）

官方 ID：<code>compute_<wbr>group_<wbr>normalized_<wbr>rewards_<wbr>grpo</code>。原 pp17–18。

交付 `compute_group_normalized_rewards`：输入 flattened rewards、group_size、baseline、epsilon、normalizer；输出同样 flattened 的 advantages 及自选统计。此阶段支持 **baseline="mean"、advantage_normalizer="std"**，其余模式可暂不支持。按每个 prompt 的 group 计算，不能按整个 rollout batch 统计。

epsilon 默认 **1e−6**，加在 std 分母上。手册推导式用 population std，但 **p11 明确要求实现用默认 `torch.std` 的样本校正**；不要为贴公式而改成 population 分母。零方差组与 group_size=1 也不是同一情况：epsilon 能处理前者，不能自动修复样本 std 在后者的未定义值。正式设置 group_size=8。

对接 `run_compute_group_normalized_rewards`；选择器 `compute_group_normalized_rewards_grpo`。

### T07．on-policy per-token loss（1 分）

官方 ID：<code>compute_<wbr>policy_<wbr>gradient_<wbr>loss_<wbr>on_<wbr>policy</code>。原 pp19–20。

交付 `compute_policy_gradient_loss`：输入 shape `(batch_size,)` 或 `(batch_size,1)` 的 reward／advantage，以及 `(batch_size,sequence_length)` 的 policy log-probs；返回同形状逐 token loss 与 metadata。此阶段只需 **importance_reweighting_method="none"**，忽略 old-log-probs／clip 参数；损失须采用梯度下降对应目标上升的符号。不要在此提前吞掉 token 维度，后续 reduction 单独负责。

它是产生指定梯度的 surrogate，不保证像监督学习 loss 一样单调下降。对接 `run_compute_policy_gradient_loss`；测试选择器：

```text
test_compute_policy_gradient_loss_on_policy
```

### T08．sequence reduction（0.5 分）

官方 ID：<code>aggregate_<wbr>loss_<wbr>across_<wbr>microbatch_<wbr>sequence</code>。原 p20。

交付 `aggregate_loss_across_microbatch`，接受 per-token loss、mask、normalization 模式与可选 constant。此阶段实现 **sequence**：在每条 response 的有效 token 上求平均，再对序列求平均，返回可 backward 的标量。不是把全批所有有效 token 混在一起平均；padding 不能进入分子或分母。

对接 `run_aggregate_loss_across_microbatch`；测试选择器：

```text
test_aggregate_loss_across_microbatch_sequence
```

### T09．标准 on-policy train step（5 分）

官方 ID：<code>grpo_<wbr>train_<wbr>step_<wbr>standard_<wbr>on_<wbr>policy</code>。原 pp22–24；累积说明 p21。

交付 `grpo_train_step`，接收 model、tokenizer、optimizer、累积数、max_grad_norm、reward_fn、重复 prompt／ground-truth、responses、group_size 和前述算法开关。本阶段组合为 **mean baseline＋std advantage＋none importance＋sequence loss**。

必需行为：

1. 对同一训练 batch 分 microbatch 做前／反向，但总梯度与整 batch 目标一致；**每个 microbatch 平均的贡献须按所含序列数占全 batch 的比例计入**，不能平均“若干平均数”而忽略尾批。
2. 累积结束后、optimizer.step 前按 max_grad_norm 裁剪梯度；该参数为 None 时不裁剪。记录的是**裁剪前 norm**。
3. 一次更新后清空梯度；返回已正确计入累积权重的 batch scalar loss 与 metadata。
4. 至少记录 loss、gradient norm、token entropy、train total／format rewards。额外 pass@k（首 k 条中至少一条正确的 prompt 比例，k≤group_size）可选，不能冒充单样本 accuracy。

对接 `run_grpo_train_step`；选择器 `test_grpo_train_step_standard_on_policy`。固定测试不仅比较 loss，还比较一步更新后的全部参数，且要求结束后所有 `param.grad is None`；metadata 不在该 snapshot 内，**不代表可不记录规定指标**。

## 4．标准实验：建立可信参照再做消融

### 4.1 全局默认配置与日志合同

下表是原 p24 **建议起点**；各题另外明确的硬性比较／seed 要求仍须满足。

| 项 | 起点 |
|---|---|
| 训练／验证题数 | 6,400／至少1,024 |
| rollout steps | 200 |
| 学习率 | 1e−5 |
| rollout／train batch | 各256 **responses** |
| group size | 8，即每 rollout batch 32 prompts |
| gradient accumulation | 32，即典型 microbatch 8 responses |
| 采样 | temperature=1，top-p=1，max512 |
| 梯度裁剪 | max norm=1 |
| optimizer | AdamW，betas=(0.9,0.95)，weight_decay=0 |
| 验证频率 | 建议每10个 rollout batches |
| 保存观察用 rollout | 建议每40个 rollout batches |

训练循环须加载模型和数据、初始化日志／vLLM／optimizer，每次生成前同步当前权重，采样、更新、周期验证并保存生成。HF 训练与 vLLM 推理分置两 GPU；先初始化 NCCL 同步组，helper 的同步过程暂停推理、传输参数、清 prefix cache 再恢复。旧 cache 不是新 policy 的证据。

固定 helper 的 completion 请求传递 temperature、max_tokens、n、seed 和可选 stop；**源码没有显式转发 top_p**。手册要求 top-p=1；记录实际服务版本与默认／请求语义，不能声称仅在调用字典里填 top_p 就已发送到服务端。它按 choice index 排序输出，返回 text、token_ids、finish_reason；对接时核对多 prompt／多样本顺序，而不是假定任意重排仍保持 group。

四 seed 图不能只画均值。原文容许：均值加每条运行曲线、均值加逐步区间，或均值加 min／max。原文给出近似区间 $\mu\pm1.96\sigma/\sqrt n$；它不是以四次运行证明稳健性的保证。允许固定 seed 不完全可复现时独立运行四次，但须如实记录；**没有指定必须是0、1、2、3**。实际 seed／运行标识由学生记录。

### T10．标准 on-policy GRPO 实验（10 分）

官方 ID：<code>grpo_<wbr>experiments_<wbr>standard_<wbr>on_<wbr>policy</code>。原 p25，标注 **2 B200 hrs**，不是本站计时或费用承诺。

- **（a）脚本。** 接受模型名、prompt、训练／验证文件路径、sampling 和 training 超参；完整覆盖初始化、权重同步、rollout、训练 batch 更新、验证和生成日志。提交正式模型／任务的标准 on-policy 脚本。
- **（b）约50步排错阶段。** 观察验证 reward 改善及 rollout 合理性。奖励最初接近0、若干步才采到正例并不必然是错误。提交让你相信脚本正确的**实际证据**，不是“测试都过了”一句话。
- **（c）正式四次运行。** 使用上表超参、zero-shot r1_zero、四随机种子／四独立运行。逐项画出 loss、gradient norm、token entropy、train total／format reward、validation total／format reward、validation average response length，以及其他排错指标；每图体现跨运行差异。定期检查生成，提交训练前后实例、几句趋势与方差评论，以及 **最终 validation accuracy 跨 seed 平均至少25%** 的过程。不能以最高 seed、训练集 accuracy 或最好中间 checkpoint 偷换“最终跨 seed 平均”。

### T11．学习率扫描（3 分）

官方 ID：`grpo_learning_rate`。原 p26，标注 **4 B200 hrs**。

从建议配置出发，至少试一个**低于1e−5**与一个**高于1e−5**的学习率，报告最终 validation reward，发散也须记录。依据 T10 已观察到的方差自行决定每点运行多少 seeds；**原题没有统一硬写四 seed**，也不是允许无说明地每点只挑一次好结果。提交 final validation reward 对 LR 的图和几句分析。后续题允许使用自己调好的 LR。

### T12．prompt 消融（3 分）

官方 ID：`grpo_prompt_ablation`。原 p26，标注 **4 B200 hrs**。

用 question_only 与 r1_zero_three_shot 各跑 **a few random seeds**，对比 T10 zero-shot r1_zero：平均 reward、跨运行方差、其他日志中系统性差异、依据方差能有多大信心。提交被引用指标的图与评论。换 prompt 时必须一起匹配对应 grader／stop 合同；否则比较混入解析错误。保留不同提示造成的 token 开销，不把额外 demonstration 当零成本。

## 5．on-policy 算法开关：每次说明改变了哪一层

| 名称 | baseline | advantage normalizer | loss reduction |
|---|---|---|---|
| 标准 GRPO | mean | std | sequence |
| GRPO_constant | mean | std | constant |
| Dr_GRPO | mean | none | constant |
| RFT | none | none | constant |
| MaxRL（作业版） | mean | mean | constant |

这里所有 importance 模式仍是 none。constant 的典型全训练 batch 分母是 **训练 responses 数 × 最大生成长度**，即 $Z=BG L_{\max}$；默认 on-policy 为256×512。它是固定常数，不是实际有效 token 数，也不是“只剩非零 advantage 的样本数”。**原 MaxRL 论文使用 batch token 数归一化；本作业故意换成 constant，以隔离 group mean normalization 的影响**，不要以论文实现覆盖作业合同。

### T13．长度归一化思考（1 分）

官方 ID：<code>think_<wbr>about_<wbr>length_<wbr>normalization</code>。原 p27。

在实验前，比较逐序列除自身长度与统一 constant 的优缺点，讨论具体适用情境／例子；交付几句讨论。区分“每条 response 权重”和“每个有效 token 权重”，本站不代写判断。

### T14．Dr. GRPO group normalization（0.5 分）

官方 ID：<code>compute_<wbr>group_<wbr>normalized_<wbr>rewards_<wbr>drgrpo</code>。原 p27。

扩展组归一化函数支持 **advantage_normalizer="none"**；虽然 Dr_GRPO 使用 mean baseline，此题还必须支持 **baseline="none"**。对接既有 group adapter，选择器 `compute_group_normalized_rewards_drgrpo`；不是另写一份并行函数。

### T15．constant loss aggregation（0.5 分）

官方 ID：<code>aggregate_<wbr>loss_<wbr>across_<wbr>microbatch_<wbr>constant</code>。原 p27。

扩展既有 aggregation 函数支持 **loss_normalization="constant"**：masked 总和除给定 normalization_constant。该参数此模式必需，不能偷偷用当前 sequence length 代替。对接既有 aggregation adapter；测试选择器：

```text
test_aggregate_loss_across_microbatch_constant
```

手册 p21 提醒：constant 模式的梯度累积缩放不能照搬 sequence 平均公式。

### T16．RFT 与 Dr. GRPO（2 分）

官方 ID：`think_about_rft`。原 p28，式35–36。

在题设二元 reward、**当前 policy 采样、固定 constant** 下，比较保留正确 rollout 的 RFT 目标梯度与减 group mean 的 Dr. GRPO 估计器：期望是否相同、预期方差关系、什么情况下偏好哪一个。交付几句讨论。不要换成固定离线 SFT 数据或每轮按保留 token 数重新平均后，仍声称比较的是题设目标；有限 group 与无限 group 的结论也不可混用。本站不提供本题答案。

### T17．难度重加权推导（6 分）

官方 ID：<code>derive_<wbr>difficulty_<wbr>reweightings</code>。原 p29，式39–43。

共同设定：prompt 来自 $\rho$，reward 表示正确性，目标 surrogate 对 prompt 施加依赖当前 policy、但 **stop-gradient** 的权重；将 constant 设为 $Z=G$，取 **$G\to\infty$**。每个子问都要给出题设参数子集构成的 $w$ 表达式及数句理由。

- **（a）** Dr. GRPO（减 group mean、不除 std）的重加权。
- **（b）** constant-normalized GRPO（再除 group std）的重加权。
- **（c）** MaxRL（改除 group mean）的重加权。

保持上述极限与 stop-gradient 前提，不把有限8样本、带 epsilon 的运行张量直接当成极限证明。本页只保留题设，不公开三个权重答案。

### T18．advantage normalization 思考（2 分）

官方 ID：<code>think_<wbr>about_<wbr>advantage_<wbr>normalization</code>。原 pp29–30。

在实验前比较除 group std、除 group mean、完全不除的优缺点，以及可能适合的具体设置／例子；交付几句讨论。baseline subtraction 与 normalizer 是两个不同开关，不能把“去归一化”误写成“去 baseline”。

### T19．MaxRL group normalization（0.5 分）

官方 ID：<code>compute_<wbr>group_<wbr>normalized_<wbr>rewards_<wbr>maxrl</code>。原 p30。

扩展既有函数支持 **advantage_normalizer="mean"**，同 std 模式一样在分母加 advantage_eps。对接既有 group adapter，选择器 `compute_group_normalized_rewards_maxrl`。不能借此改成按 batch token 数的另一种 MaxRL。

### T20．on-policy train-step variants（2.5 分）

官方 ID：<code>grpo_<wbr>train_<wbr>step_<wbr>variants_<wbr>on_<wbr>policy</code>。原 pp30–31。

扩展 train step，覆盖 baseline 两种、advantage normalizer 三种、loss reduction 两种，importance 仍为 none；**避免让零 advantage 序列通过模型**。mean baseline 下同组 reward 全相同会全零；none baseline 下零 reward 序列为零。可以相应减少累积步数、保持 microbatch 大小，但必须保证剪枝前后梯度等价，不能按存活样本重定义分母。全零批也须清晰区分“没有本批策略梯度”和 optimizer 既有状态的语义。

对接 `run_grpo_train_step`；选择器 `test_grpo_train_step_variants_on_policy`。测试具体参数化四种命名变体；函数合同的开关范围不应被缩成四个硬编码分支。

### T21．on-policy 算法比较（10 分）

官方 ID：<code>grpo_<wbr>experiments_<wbr>variants_<wbr>on_<wbr>policy</code>。原 pp31–32，标注 **8 B200 hrs**。

固定与标准 GRPO 对照相同超参（LR 可用此前选择），统一 zero-shot r1_zero。对上表 **GRPO_constant、Dr_GRPO、RFT、作业版 MaxRL 各跑四 seeds**；对照为已有标准 GRPO。分析谁的平均表现更好、方差更低、哪些方法可能需要更多调参，以及方差如何限制信心；所有引用指标用图支持。

报告须说明 RFT 可省略错误样本的前／反向，而不是因此增加生成预算。原 p31 专门讨论调参不对称：只给 baseline 调 LR 后，候选失败不证明其最佳性能更差；候选成功也应限定在实际预算／模型／数据上，不扩张成普遍最优。本站没有这些实验曲线或胜负结论。

## 6．off-policy：缓存的 rollout 不是当前 policy

同一批256 responses 分为32个 train batch、每批8 responses，并**各做一次 optimizer step**。第一次更新之后，旧 rollout 相对于当前 policy 就是 stale。行为策略记 $\pi_0$，当前策略记 $\pi_\theta$；本正篇没有额外冻结的 DPO reference model，也没有要求偷偷加入 KL 正则。

old_log_probs 必须来自**生成该批 rollout 的行为策略**，在更新前固定，并与同一 token／mask 对齐；训练期间不能用当前分数不断刷新分母。完整 sequence importance ratio 可做分布变换，但长序列乘积会带来高方差。token ratio 只改一个位置的条件分布，未完全校正旧 prefix／suffix；GSPO 的几何平均也不是完整 sequence ratio。这些偏差—方差区别是本节任务的一部分。

### T22．pairwise surrogate（2 分）

官方 ID：<code>derive_<wbr>surrogate_<wbr>objectives</code>。原 p34，式55。

题设从 stale $\pi_0$ 采样，将每对相邻位置 $(2t-1,2t)$ 的两个 importance ratios 相乘，再配合这两个条件概率乘积的 log-gradient；长度 $L$ 按题设配对。推导该估计器优化的 surrogate objective，提交参数表达式和推导。依据原 pp33–34 区分 token／pair／完整 sequence 改变了哪些采样位置；本站不提供配对目标答案。

### T23．token off-policy loss（1 分）

官方 ID：<code>compute_<wbr>policy_<wbr>gradient_<wbr>loss_<wbr>off_<wbr>policy</code>。原 p35。

扩展既有 loss 支持 **noclip** 和 **grpo**，使用行为策略 old_log_probs；grpo 另需 cliprange。noclip 是 token-level reweighting，不是“直接使用旧数据、不加权”的 none。grpo 使用 PPO 式两分支目标，不是无条件把 ratio clamp 后乘优势；返回**负目标**给梯度下降。训练脚本还必须取得并保存 old_log_probs。

对接 `run_compute_policy_gradient_loss`；测试选择器：

```text
test_compute_policy_gradient_loss_off_policy
```

测试 cliprange=0.1 是夹具，不覆盖正式实验默认0.2。

### T24．importance 策略思考（2 分）

官方 ID：<code>think_<wbr>about_<wbr>importance_<wbr>reweighting</code>。原 p36。

比较三种方案：**（a）不做 importance reweighting；（b）PPO／GRPO clipped token ratio；（c）GSPO clipped sequence geometric mean**。讨论偏差—方差取舍及可能适合的情境，交付几句评论。这三项是同一讨论题中的比较维度，不是额外分配分值的子题。

### T25．GSPO loss（1 分）

官方 ID：<code>compute_<wbr>policy_<wbr>gradient_<wbr>loss_<wbr>off_<wbr>policy_<wbr>gspo</code>。原 p37；定义 p36 式62–65。

扩展 loss 支持 **gspo**，输入 old_log_probs、cliprange 和 response_mask。按 **有效 response tokens** 的 log-ratio 平均构造几何平均，避免先乘许多概率造成数值溢出；同一条 response 共享 sequence-level weight，再执行 clipping，返回负目标。不能把 padding／prompt 放进平均，也不能把几何平均误写成 ratio 算术平均。

返回接口仍是逐 token tensor，后续 reduction 须与 p36 的 sequence-level objective 一致，不能重复多除一次长度。对接既有 loss adapter；测试选择器：

```text
test_compute_policy_gradient_loss_off_policy_gspo
```

将 GSPO 推广到 constant-normalized 算法属于原文注明的可选探索，须连指数／整体 reduction 一起解释，不能只切一个 reduction 开关便称完全相同的目标。

### T26．off-policy train step（2.5 分）

官方 ID：<code>grpo_<wbr>train_<wbr>step_<wbr>off_<wbr>policy</code>。原 p37。

扩展 train step 支持 importance method、old_log_probs、cliprange，至此须支持完整参数范围；保留此前梯度累积、裁剪、mask、logging、清梯度和返回合同。对接 `run_grpo_train_step`；选择器 `test_grpo_train_step_off_policy`，其参数化包含 noclip、grpo、gspo。

### T27．off-policy 实验（10 分）

官方 ID：<code>grpo_<wbr>experiments_<wbr>off_<wbr>policy</code>。原 p38，标注 **8 B200 hrs**。

相对标准 GRPO 固定其他超参／所选 LR，统一 zero-shot r1_zero；允许选此前最喜欢的 RL variant，但必须明确基线与 reduction 一致性。设置 **rollout batch=256、train batch=8、gradient accumulation=1**，即每次 inference batch 32次更新，不是32个 microbatch 最后只更新一次。

各运行 **四 seeds**：

| 方法 | importance 模式 | 正式默认 cliprange |
|---|---|---:|
| offpolicy_naive | none | 不适用 |
| offpolicy_noclip | noclip | 不适用 |
| offpolicy_clip | grpo | 0.2 |
| offpolicy_gspo | gspo | 0.0003 |

可以自行调 cliprange，但须如实注明搜索与公平性。除原日志外**必须记录 clip fraction**，明确分母是有效 tokens 还是 sequences、是越界比例还是实际被 PPO 分支截去梯度的比例；两者不可不加说明地比较。

与 fully on-policy 对照，报告性能、训练速度问题的实际证据、稳定性、跨 seed 方差、两种 clipping 的 clip fraction 差异与稳定性、可能受益于进一步调参的方法、结论信心；引用指标均给图。32倍 updates **不意味着32倍 wall-clock 提速**，不能把题设目标写成实测结论。

### 未计分可选探索

原 pp35–36 允许尝试 **CISPO** 并与其他 clipping 比较；其梯度估计器直接 upper-bound clip 权重，与 PPO 达到单侧边界后对对应项产生零梯度不同。它不是必做第五个 off-policy 实验。p36 还允许探索 constant-normalized GSPO；这些内容不取代任何必做题。外部论文正文精读统一回链[RLVR 材料页](#/c/stanford-cs336-2026/lec/lec16?v=materials)，本页不重复翻译论文。

## 7．自拟估计器与最终报告

### T28．只改变一个因素（10 分）

官方 ID：`try_your_own`。原 §7、p38。

学生提出自己的 policy-gradient estimator；原题给的方向包括 advantage estimator／prompt 重加权、importance 策略、reward baseline，但**具体创意和方案由学生提出**。必须存在至少一个此前已做方法作为直接对照，与你的方法**只差一个因素**。在相同 OLMo-2-0425-1B／GSM8K 场景、固定其他问题参数、**多个随机种子**下比较已有 baselines。

报告改变的理论依据／直觉、是否胜过基线、图支持的观察；有助说明时可附数学推导。原题这里要求 multiple seeds，**没有写死四个**；应依据已有噪声选择并说明数量。不能一面换 baseline，一面换 LR、prompt、group size，再把变化归因于一个新 estimator。本站不提供一个可直接采用的作业创意或结论。

### 7.1 提交前的证据账本

每个实验记录：固定源码／依赖版本、准确模型与 tokenizer 身份、数据子集／划分、三种提示之一及 grader、seed／独立运行编号、实际采样参数、rollout／train／microbatch 大小、所有算法开关、normalization constant、old policy 版本、停止原因／截断、验证频率、生成预算、耗时和失败。图表写清横轴是 rollout step、optimizer step、tokens 还是墙钟时间。

逐项交付书面推导／思考题、全部正式实验图、跨 seed 波动、真实 prompt／response 观察、25% 门槛的实际计算、源码与可复现配置。没有运行就明确写未运行，不补造 accuracy、学习曲线、训练前后样例或论文式“稳定超过”措辞。

## 来源与阅读边界

- [固定39页官方讲义](https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/c2734a26308710949fe13226960a1e8cece94b7e/cs336_spring2026_assignment5_alignment.pdf)：全文提取文本已读；选页视觉核对不等于逐页视觉审校。
- [固定仓库与 README](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e)、[CHANGELOG](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/CHANGELOG.md)、[AGENTS](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/AGENTS.md)：版本、政策与运行边界。
- [固定 helpers／prompts](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/cs336_alignment)、[adapters 与测试](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/tests)、[配置](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/pyproject.toml)：静态源码阅读，未执行；未下载 fixtures、snapshot binaries 或题库。
- [OLMo 模型卡](https://huggingface.co/allenai/OLMo-2-0425-1B)、[GSM8K 数据卡](https://huggingface.co/datasets/openai/gsm8k)：复用P1固定快照的许可／划分证据，不声称下载模型或数据。

非官方原创中文教学整理。外部原件、哈希、精确阅读范围、任务映射与权限证据保留在本课程 `sources/p7-a5-reasoning`；原件和渲染图不作为公开正文资源。作者未运行官方代码或任何模型实验。
