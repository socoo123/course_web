---
title: A5 官方选做：指令微调与安全偏好对齐
kind: 完整要求索引与独立教学说明；不是官方全文译本或解答
source: CS336 Assignment 5 Supplement (alignment), Spring 2026, Version 26.0.0
source_commit: c2734a26308710949fe13226960a1e8cece94b7e
source_read_scope: 全部18页提取文本；原页9、15、16、17视觉核读；README、完整CHANGELOG、相关adapters、三份选做测试及评委和环境配置
status: P7 作者交接；16个计分题、42个字母子问、4个无字母交付块、61分；主审另记验收
execution: 仅静态来源阅读；未下载训练数据或权重、运行官方测试、训练、评测、调用模型API或访问校内卷
license: 固定作业仓库未发现明确开放许可；不据公开可读宣称获得全文翻译授权；模型、数据和第三方资料分别核权利
---

# A5 的官方选做补充，不是 Assignment 6

这份补充围绕同一个 **Llama 3.1 8B 基座**建立三阶段比较：原始模型的零样本表现、混合指令数据 SFT 后的表现、HH 偏好数据 DPO 后的表现。每一步都同时观察知识、数学推理、对话质量与安全，而不是只优化一个“更会拒绝”的分数。

**整份材料完全 optional。** 下表的分数来自选做 handout 印出的 Problem，不表示学校另设了一份必做作业。本页依据 Spring 2026 v26.0.0 的全部 18 页，以自编结构解释全部交付要求；不逐段复制原文，不提供可直接提交的代码、实验结论、攻击提示库或答案报告。[指导页](#/c/stanford-cs336-2026/lab/a5-safety-optional?v=guide) 讲机制、证据边界与原创无害小例子。

**版本入口特别说明：** P1 获取时，官网仍指向 `spring2025` 文件名；在当时固定仓库版本上，该旧文件请求得到 **HTTP 404**。当前正文使用通过仓库 tree 与 README 独立找到的 **2026 补充**。历史 2025 v1.0.1 只用于版本辨认，不能把旧 Together 路线、H100 预算或旧接口搬过来。另一个事实是：历史公开 SFT 数据地址的 HEAD 请求发生 **TLS/SSL 失败，没有取得 HTTP 响应**；那不是 404，也不能据此宣布文件已删除。本轮没有重试这些数据地址或请求凭据。

## 0．全量任务与权限合同

### 0.1 任务账本

页码均为固定 PDF 的物理页码，与该 PDF 印出的页码一致。每个计分题的分数是整题分数，官方没有给字母子问另分分值。

| 官方 ID | 官方题意 | 页码 | 分值／子问 |
|---|---|---|---|
| `mmlu_baseline` | Zero-shot MMLU baseline | 4 | 4／a–f |
| `gsm8k_baseline` | Zero-shot GSM8K baseline | 5 | 4／a–f |
| `alpaca_eval_baseline` | Zero-shot AlpacaEval baseline | 6–7 | 4／a–d |
| `sst_baseline` | Zero-shot SimpleSafetyTests baseline | 7–8 | 4／a–d |
| `look_at_sft` | Inspect instruction tuning data | 8 | 4／无字母 |
| `data_loading` | Implement data loading | 9–10 | 3／a–b |
| `sft_script` | Training script: instruction tuning | 11 | 4／无字母 |
| `sft` | Instruction tuning | 11 | 6／无字母 |
| `mmlu_sft` | Evaluate SFT on MMLU | 12 | 4／a–c |
| `gsm8k_sft` | Evaluate SFT on GSM8K | 12–13 | 4／a–c |
| `alpaca_eval_sft` | Evaluate SFT on AlpacaEval | 13 | 4／a–c |
| `sst_sft` | Evaluate SFT on SimpleSafetyTests | 13–14 | 4／a–c |
| `red_teaming` | Red-team the instruction-tuned model | 14 | 4／a–b |
| `look_at_hh` | Inspect HH preference data | 16 | 2／a–b |
| `dpo_loss` | DPO loss | 17 | 2／无字母 |
| `dpo_training` | DPO training | 17–18 | 4／a–d |

合计 **16 题、61 分、42 个字母子问**，另有 **4 个无字母交付块**，共 46 个题内交付块。训练配置、路径、提示格式、模型保存与许可等无编号合同也属于下文覆盖范围，不能用“完成 16 个函数”代替它们。

### 0.2 AI、使用工具与本页边界

课程 AI 政策只允许高层概念与低层 API／函数签名帮助；学生必须亲手写作业与排行榜代码，关闭 AI 自动补全。固定仓库 `AGENTS.md`／同内容的 `CLAUDE.md` 进一步禁止代写 Python、伪代码、填充占位实现或完成计分题。本站因此只给要求解释与非提交式概念练习。

官方允许用 vLLM 生成，用 Transformers 加载模型与 tokenizer；**不能用 Hugging Face Trainer 等训练封装替代自己实现核心部分**。学生实现放在 `cs336_alignment`；选做提示放在 `prompts_safety`，不是正篇 RL 的 `prompts`；选做测试通过 `tests/adapters.py` 接入。原始测试必须满足，不能通过改弱测试“通过”。

本页不提供启动命令清单。所有“训练、抽样、报告”都表示**学生的待完成要求**，不表示本站已经执行。我们没有安装作业环境、运行官方 pytest、读取训练数据、下载模型、启动 Modal／GPU、调用评测或提交服务。

### 0.3 模型、课程卷与校外缺口

- **被训练的模型**：手册写 `meta-llama/Meta-Llama-3.1-8B`，共享卷目录也是 `Meta-Llama-3.1-8B`。P1 公开模型元数据的规范 ID 为 `meta-llama/Llama-3.1-8B`；不要由命名差异误换成 8B Instruct 或其他小模型。
- **自动评委**：`meta-llama/Llama-3.3-70B-Instruct`。它不参与本补充的 SFT／DPO 参数更新。
- **权重访问**：两者公开元数据均为 `manual` gated，分别受 Llama 3.1／3.3 Community License 与 AUP 约束。需要发布者审批；“学术自学”不自动赋予下载或再分发权限。P1 匿名固定 README／LICENSE 请求为 401，未绕过；本轮也未请求凭据。
- **课程共享环境**：`cs336-shared-data` 中的卷 `cs336-a5-supplement`，挂载 `/mnt/cs336-a5-supplement`。这是课程环境名称与文件系统路径，**不是公共 URL**。共享卷只读；手册明确禁止往里面写。
- **个人结果**：卷名 `cs336-a5-supplement-results-{SUNET_ID}`，挂载 `/mnt/cs336-a5-supplement-results`，与共享输入分开。
- **单轮 SFT 文件**：共享挂载下 `data/` 中的目录名为：

  ```text
  safety_augmented_ultrachat_200k_single_turn/
  ```

  其中 `train.jsonl.gz` 与 `test.jsonl.gz` 每行只有本题所需的 `prompt`／`response` 对。helper 将后一份称 `SFT_DEV_PATH`；作为训练监测用时不能宣传成从未调参的独立测试集。

公开 UltraChat-200K 与 SafetyTunedLlamas 是原料，不是已经证明与课程单轮混合文件**字节一致**的备份。校外能否取得精确 2026 混合文件、其中的混合比例与处理细节，仍未核实；自行重新混合应另标数据版本，不能冒充完整原版复现。课程集群指南只面向选课学生，本站不提供身份、令牌或权限绕过办法。

固定 helper 继承主文件的 `B200:2`、最大容器数 4 与镜像；补充任务 timeout 为 20 小时。主文件在 `SUNET_ID` 未配置时会在 import 阶段抛错，且引用 `wandb` secret。这些是**静态配置事实，不是可直接运行的保证或使用授权**。手册题名标注 SFT “3 B200 hrs”、DPO “1 B200 hr”，是来源预算标签，不是本站实测，更不能直接换算为校外费用。

### 0.4 数据授权分别处理

| 材料 | 已读来源的许可声明与限制 |
|---|---|
| MMLU、GSM8K | 对应公开 dataset 元数据声明 MIT；不据此推导所有原始题目或课程讲义权利 |
| UltraChat-200K | dataset card 声明 MIT；原始卡是多轮 messages 与四个 split，非课程单轮混合格式 |
| SafetyTunedLlamas | **代码 MIT，数据 CC BY-NC 4.0**；SafeText／PhysicalSafety 另指向其来源 |
| AlpacaEval 数据 | **CC BY-NC 4.0**；不是笼统的 MIT |
| SimpleSafetyTests | CC BY 4.0；含敏感内容警告，本页不转载测试提示 |
| Anthropic HH | dataset card 声明 MIT；偏好对与 red-team transcripts 是不同资料，卡明确警告不要把其当普通对话 SFT 数据 |
| 本作业 PDF／仓库 | 固定完整 tree 未发现 LICENSE／COPYING，README 与 pyproject 无授权声明；未确认开放全文翻译许可 |

许可、gate、可达性、数据版本一致性是四个不同问题。能看到路径不表示有权读取，能取得原料不表示拿到了同一训练集。

## 1．四项零样本 baseline 的共同条件

四项都从**基座** Llama 3.1 8B 开始，使用 `zero_shot_system_prompt.prompt` 的共同外层。MMLU、GSM8K 先填各自任务模板，再插入外层；AlpacaEval 与 SimpleSafetyTests 的任务层直接传 instruction。PDF 的 ↪ 只是排版续行，既不是真实字符，也不表示换行。

共同外层约定以 `# Query:` 与 `# Answer:` 区分轮次，并用 Markdown 围栏包裹文本；预期模型结束答案后进入下一轮。**基线遇到新的 `# Query:` 可以停止生成**。不要把后训练阶段的 Alpaca 模板和这份外层混用。

四项生成均规定 **temperature 0.0、top-p 1.0**。原文没有给全部任务统一指定最大新 token 数；学生仍应记录自己的上限、EOS／停止条件、模型与 tokenizer 版本。吞吐率以 examples/s 报告，应说明计时边界，不能把生成时间与 70B judge 时间混为一个数。

### 1.1 `mmlu_baseline`：4 分，a–f

MMLU 检查多学科选择题知识。任务模板要求输出包含单个选项字母的特定回答句式；`subject`、`question`、四个 `options` 按题填入。统计答案时区分“输出没有可识别字母”和“识别到字母但答错”。

- **（a）解析合同**：提供把模型输出映射到 A／B／C／D 的函数；无法解析返回 `None`。连接 adapter <code>run_parse_<wbr>mmlu_response</code>；对应测试 `test_parse_mmlu_response`。交付是解析函数，不是把 gold `answer` 直接返回。
- **（b）评估脚本**：加载题目、构造完整提示、生成、算指标，并保存**题目、原始生成与得分**。交付脚本，不能只留最终均值。
- **（c）解析失败**：运行后给出失败数量；非零时展示若干失败输出。失败记录不能悄悄从分母中消失。
- **（d）生成计时**：报告耗时与 examples/s 估算。
- **（e）总体表现**：用 **1–2 句**报告指标。
- **（f）错误观察**：随机取 **10 个预测错误**的例子，用 **2–4 句**分析错误类型，必要时引例或回应。不能拿最有趣的十条冒充随机抽样。

### 1.2 `gsm8k_baseline`：4 分，a–f

本补充的任务层是问题加回答入口，解析规则为**生成文本里出现的最后一个数字**。它与正篇要求 boxed 输出的 `question_only`，以及另一套 answer 标签解析，**不是同一合同**。

- **（a）解析合同**：把输出解析成一个数值预测，失败返回 `None`；adapter <code>run_parse_<wbr>gsm8k_response</code> 的返回约定是数字的**字符串**或 `None`，不要自行改成 float。连接 `test_parse_gsm8k_response`。
- **（b）评估脚本**：加载例子、填提示、生成、计算指标，序列化题目、生成与分数。
- **（c）解析失败**：给数量，并在非零时列少量例子。
- **（d）生成计时**：报告耗时与 examples/s。
- **（e）总体表现**：**1–2 句**报告指标。
- **（f）错误观察**：随机抽 **10 个预测错误**，用 **2–4 句**分析并按需给例子。

“末尾数字”是这份作业的测量规定，不是对任意自然语言回答都语义正确的解析器。例如附加一句带年份的解释就可能改变被取出的数字。报告中应区分数学错误、格式／解析错误与截断，不要把解析成功当作推理成功。

### 1.3 `alpaca_eval_baseline`：4 分，a–d

这里的指标是自动评委相对于固定参考回答的偏好，不是带 gold answer 的选择题准确率。

- **（a）生成脚本与文件合同**：逐 instruction 生成，保存为 **JSON 数组**，不是 JSONL。每项包括 `instruction`、`output`、`generator`、`dataset`。`generator` 是这次模型的统一标识，各条保持一致；`dataset` 保留原数据给出的来源标识。
- **（b）速度**：报告生成耗时与 examples/s。
- **（c）两种胜率**：按固定配置评估，交付 **1–2 句**报告普通 winrate 与 length-controlled winrate。
- **（d）偏好错误分析**：随机取 **10 个 baseline 输给参考**的例子，用 **2–4 句**解释可能原因，并指出是否不同意自动评委，按需给例子。

必须分清两个角色：

1. **GPT-4 Turbo 是参考回答的来源**：固定仓库已有以下文件，2026-06-03 CHANGELOG 明确补充了预生成参考数据：

   ```text
   data/alpaca_eval/alpaca_eval_gpt4_turbo.json
   ```
2. **本地 Llama 3.3 70B Instruct 是评委**：annotator 配置使用 `vllm_local_completions`，不是要求现场调用付费 GPT-4 API。

评估接口需要指定 model outputs、上述 reference outputs、`scripts/alpaca_eval_vllm_llama3_3_70b_fn` 配置目录及 `base-dir`。配置采用两卡张量并行、context 7000、最多生成 100 tokens、temperature 0、top-p 1、batch size 900；这些是**评委配置**，不是被评模型的生成上限。具体输出可在 `annotations_seed0_configs.json` 观察。参考／候选的次序会影响 `preference` 数字的含义，不能脱离配置解释。

### 1.4 `sst_baseline`：4 分，a–d

SimpleSafetyTests 使用安全风险测试输入，通过 70B 自动评委判断模型回应。它是人工判断的有噪声代理，不是安全保证；公开报告不应复制不必要的有害原文。

- **（a）生成脚本与文件合同**：逐条生成后保存 **JSONL**。每行至少有 `prompts_final`（原 instruction）与 `output`（模型回应）；不要写成 AlpacaEval 的 JSON 数组。
- **（b）速度**：报告生成耗时与 examples/s。
- **（c）安全比例**：使用 `scripts/evaluate_safety.py` 的输入、模型路径、GPU 数量、输出路径接口；手册示例评委为本地 Llama 3.3 70B、2 GPUs。用 **1–2 句**报告被判安全的比例。
- **（d）失败观察**：随机取 **10 个被判不安全**的例子，**2–4 句**分析发生在哪些情境，以及是否同意评委。

**已读 helper 的重要语义：** 评委回答 `True` 指“有不安全内容”，不是“安全”。脚本将去空白、转小写后以 `true` 开头的回答记为 safe=0，**其他任何回答都记为 safe=1**。因此非法格式也可能被记“安全”。脚本保存原模型输出、评委提示、评委原输出和 metrics；解读结果时要保留这些证据，不能只凭均值断言模型安全。它使用 chat template、评委 context 6144、评委最多 16 tokens，与 AlpacaEval 的判分配置不同。

## 2．单轮混合数据 SFT

### 2.1 `look_at_sft`：4 分，无字母子问

从**课程已处理的混合训练文件**随机观察 **10 个例子**。用 **2–4 句**解释其中隐含的传统 NLP 任务，如问答、情感分析、摘要、改写，并评价 prompt 与 response 两侧质量；尽量用具体例子支撑。只看公开 dataset card，或自行编十条例子，都不能冒充完成此题。

手册说明数据来自 UltraChat-200K 与 SafetyTunedLlamas，并已转成每条一个 prompt／response 的单轮格式。没有公开给出本混合文件精确比例，本页不替其编造。质量检查可以关注指令是否明确、回答是否真正完成任务、拒答是否过度、语言风格是否重复；实际结论须来自学生看到的数据。

### 2.2 `data_loading`：3 分，a–b

训练使用 `alpaca_sft.prompt`，不是 baseline 外层。每个 prompt／response 经模板成为一份文档，用模型 end-of-text 分隔，将文档串成 token 流，再切为固定长度输入。**官方叙述是完整文档的 next-token 语言建模，不是正篇的 response-only RL mask 合同。**

- **（a）packed Dataset**：构造接口接收 tokenizer、`dataset_path`、`seq_length`、`shuffle`。其中 shuffle 控制的是**文档在拼接前的顺序**。`__len__` 返回固定长度序列数量；索引返回含 `input_ids`／`labels` 的字典，两者都是 `(seq_length,)` tensor。labels 对应下一 token；连续、不重叠地取输入块，尾部不足完整长度的块丢弃，每块每 epoch 恰好出现一次。交付 Dataset，连接 <code>get_packed_<wbr>sft_dataset</code> 与 `test_packed_sft_dataset`。
- **（b）batch 迭代**：输入 Dataset、batch size、是否 shuffle **切好后的例子**；迭代一次正好是一个 epoch。可以用 PyTorch DataLoader。交付 batching 函数，连接 `run_iterate_batches` 与 `test_iterate_batches`。

两种 shuffle 不等价：前者改变文档相邻关系及切块边界，后者只改变已有块的送入顺序。固定测试要求 token IDs／labels 与 fixture 逐项一致；batch 测试接受最后一个较小 batch，并检查整数 tensor 类型。 **丢掉不完整 token 块，不等于丢掉最后一个不足 batch size 的 batch。** 本轮只读测试源码，没有下载 fixture 数据／权重或执行测试。

### 2.3 `sft_script`：4 分，无字母子问

交付能够对 Llama 3.1 8B 进行指令微调的自写脚本。可改造自己先前的训练脚本；不能用 HF Trainer。官方建议参数化模型、优化器、梯度累加与周期性训练／验证日志，日志可写控制台，不要求一定调用在线服务。

加载合同包括 Transformers、**bfloat16 与 FlashAttention-2**；取得 forward 输出的 logits 后自己组织 next-token cross-entropy。保存用模型与 tokenizer 的序列化接口，建议放同一目录，保证以后评估和 DPO 使用相匹配的一对。

梯度累加的意义是在多次 microbatch forward/backward 后做**一次 optimizer step**。累加前的缩放要匹配期望的 batch 平均；不要把多次 optimizer 更新误称同一个大 batch。末尾小 batch 与不足完整累加窗口的样本数也应如实记录，而非假设永远整除。

### 2.4 `sft`：6 分，无字母子问

题名资源标签为 **3 B200 hrs**，不是本站性能复现。官方建议从以下配置起步：

| 项目 | 2026 手册配置 |
|---|---|
| 初始模型 | Llama 3.1 8B base |
| 数据／轮数 | 指定单轮混合数据，建议 1 epoch |
| context | 512 tokens |
| effective batch | 每个梯度更新 32 条序列 |
| learning rate | 2×10⁻⁵ |
| schedule | cosine decay；总训练步数前 3% linear warmup |
| weight decay | 0.1 |
| gradient clipping | 1.0 |
| 数值／注意力 | BF16／FlashAttention-2 |

手册允许探索学习率以建立直觉，不等于允许删除基线设定或只汇报最好的一次而不解释变化。 **交付四项：训练配置说明、最终 validation loss、学习曲线、序列化 model 与 tokenizer。** 这份选做没有沿用正篇“4 seeds、至少25%”的门槛；不能从正篇移植未经要求的评分条件，也不能把未训练写成已完成。

## 3．SFT 后四基准复评

共同变更是**外层提示切换为训练用 Alpaca 模板**，不再用 zero-shot system prompt；MMLU、GSM8K 仍先填各自任务层。AlpacaEval／SST 直接把 instruction 放入 Alpaca。生成设置与 baseline 相同以尽量公平比较；解码不变并不意味着输入模板不变。这是官方规定的“阶段适配后的系统比较”，不是只改变权重的严格因果消融。

### 3.1 `mmlu_sft`：4 分，a–c

- **（a）** 写并运行 MMLU 评估脚本，使用 MMLU 任务层＋Alpaca 外层，计生成耗时； **1–2 句** 报告 examples/s 并与 zero-shot baseline 比较。
- **（b）** 用 **1–2 句** 给出 MMLU 指标与基线比较。
- **（c）** 随机抽 **10 个预测错误**，以 **2–4 句** 分析错误，说明 SFT 输出相对基线的定性差异，必要时引例。

### 3.2 `gsm8k_sft`：4 分，a–c

- **（a）** 写并运行 GSM8K 评估脚本，使用本补充 GSM8K 任务层＋Alpaca 外层； **1–2 句** 报告吞吐率并比较。
- **（b）** 用 **1–2 句** 报告 GSM8K 指标及 baseline 差异；继续沿用末尾数字解析，不切到正篇 verifier。
- **（c）** 随机取 **10 个预测错误**， **2–4 句** 分析错误与生成风格变化。

### 3.3 `alpaca_eval_sft`：4 分，a–c

- **（a）** 写脚本收集 SFT 模型预测，以 Alpaca 格式输入，保持 JSON 数组的四字段合同； **1–2 句** 报告生成吞吐率与基线比较。
- **（b）** 继续以本地 Llama 3.3 70B 评委比较预生成 GPT-4 Turbo 参考； **1–3 句** 给普通胜率、length-controlled 胜率及与 baseline 的比较。
- **（c）** 取 **10 个 SFT 输给参考** 的例子， **2–4 句** 分析原因与对评委的异议。手册在这个固定 reference／candidate 次序下说明 `preference=1.0` 表示 GPT-4 Turbo 更好；换次序后不能照搬。

length-controlled 胜率控制的是特定长度偏差，并不会让自动 judge 变成客观真值。两种胜率都要报告，不能只选对自己有利的一种。

### 3.4 `sst_sft`：4 分，a–c

- **（a）** 以 Alpaca 外层收集 SST 预测，继续使用 `prompts_final`／`output` JSONL； **1–2 句** 比较生成吞吐率。
- **（b）** 同一安全 helper 与本地 70B 评委下， **1–2 句** 报告安全比例及 baseline 差异。
- **（c）** 取 **10 个被判不安全** 的例子， **2–4 句** 讨论失败类型与评委是否误判。

若实际错误／不安全例子少于题目要求的抽样数，不应复制记录凑十条或虚构结果；如实报告可得数量，并向课程 staff 说明。这个报告诚实性提醒不是本站对评分要求的修改。

### 3.5 `red_teaming`：4 分，a–b

官方要求主动探查 SFT 模型的失效边界，不能用静态安全均值代替。

- **（a）** 提出题目已举情形之外的 **3 类潜在误用**；用 **1–3 句** 说明。
- **（b）** 针对 **3 种不同的潜在恶意应用** 与自己的 SFT 模型交互，分别用 **2–4 句** 说明方法、结果与定性发现。报告要覆盖是否成功、尝试多长时间、用了何种策略，而不是只列三个输入。

**本站不代做这项测试，也不提供可复用的攻击提示或绕过策略。** 授权研究应先固定目标、授权对象、内容边界、停止条件、尝试预算与记录方式，只在自己获准的隔离模型上进行；不要对真实人物、外部服务或真实敏感资产操作。报告可用风险类别、脱敏摘述与失败判据表达，不需要发布有害执行细节。[指导页的三类无害情境](#/c/stanford-cs336-2026/lab/a5-safety-optional?v=guide) 仅用来学习实验控制， **不是本题 b 的实际结果或替代提交**。

## 4．HH 偏好数据与 DPO

DPO 这一段不是要求实现 PPO，也不要求另外训练显式 reward model。手册先用 RLHF 介绍背景，然后要求在已有偏好对上优化 DPO。完整论文材料只归属 [L15 DPO 材料页](#/c/stanford-cs336-2026/lec/lec15?v=materials)，本页不重复论文翻译。

### 4.1 `look_at_hh`：2 分，a–b

使用 `data/hh` 下四份 **training collections**：

- `harmless-base.jsonl.gz`；
- `helpful-base.jsonl.gz`；
- `helpful-online.jsonl.gz`；
- `helpful-rejection-sampled.jsonl.gz`。

文件名带 online，表示上游收集过程，不表示学生本轮要在线 rollout。它们不是 HH 的 red-team transcript 数据集，也不是这里的独立测试集。

- **（a）加载与过滤函数**：合并四文件；每条原始记录有 `chosen`／`rejected` 对话。**过滤 human 消息数大于 1 的多轮对话**，因为后续 human 消息可能在两条分支中不同，使两个回答不再条件于相同问题。提取共同 instruction 及 chosen／rejected assistant response，并保留来源文件。交付便于 DPO 使用的 Python 数据加载函数；gzip／JSON 是文件格式提示，不是提供现成实现。
- **（b）人工观察**：分别随机看 **3 条 helpful 与 3 条 harmless**，用 **2–4 句**比较 chosen 与 rejected 的主要差别，讨论自己是否认同标签。上游没有强制统一定义 helpful／harmless，人的偏好不等于无噪声真值。

“只保留一个 human 回合”不等于简单截取每条对话首句：必须保持成对条件的同一性与原标签含义。过滤掉了哪些集合、留下多少对，值得记录，但本轮未读取数据，不能提供真实统计。

### 4.2 `dpo_loss`：2 分，无字母子问

交付**单个偏好实例**的 DPO loss 函数；输入包括训练模型、reference 模型、共同 tokenizer、β、prompt、chosen response、rejected response。连接 <code>run_compute_<wbr>per_instance_<wbr>dpo_loss</code>，对应 `test_per_instance_dpo_loss`。

以下是手册目标的分行记法，只说明数学合同，不是实现：

$$
a_w=\log\pi_\theta(y_w\mid x)
-\log\pi_{\rm ref}(y_w\mid x)
$$

$$
a_l=\log\pi_\theta(y_l\mid x)
-\log\pi_{\rm ref}(y_l\mid x)
$$

$$
\ell=-\log\sigma\!\left(\beta(a_w-a_l)\right).
$$

这里是**完整回答的 log-probability 求和**，不是默认按回答 token 数平均；两者改变目标。使用 Alpaca 模板并在**每条 response 后追加 EOS**。两份模型可能在不同设备，返回 loss 必须在**被优化模型的设备**。reference 是上一阶段 SFT 的冻结拷贝，不能跟着训练模型更新；它不是正篇记录 rollout 来源的 old policy。

手册 §6.3 说明，同一模型对相同 prompt 的两个回答做 log-probability 差时，prompt 项会抵消，因此可与拼接字符串的联合 log-probability 差对应。但这种抵消依赖**相同 tokenized 前缀、相同计分规则**；不同截断、不同模板或不同归一化会破坏等价。不要据此随便混入 padding，或把 prompt 位置当作偏好标签。

固定 DPO 测试使用本地 tiny-GPT2 两个 fixture 与自建小 tokenizer，只检查一个标量目标；这不是 Llama 实际训练，也不证明跨设备、冻结、EOS 或验证全过程都正确。本轮没有下载 fixture 权重或运行该测试，更不会给出通过测试的完整答案实现。

### 4.3 `dpo_training`：4 分，a–d

官方 §6.4 的简化训练建议是两卡分别放置 SFT reference 与训练模型；两者都从**自己的同一个 SFT checkpoint**初始化。为了显存，不追求大张量 batch，而以逐实例处理配合梯度累加。建议 RMSprop；原文不建议直接 AdamW，除非另有量化等效率措施。这里没有要求另写量化系统。

| 项目 | 官方建议／要求 |
|---|---|
| GPU 分工 | 两卡：一份冻结 reference，一份训练模型 |
| validation | 从 HH 留出一小份，例如 200 个例子 |
| effective batch | 64 个偏好实例 |
| β | 0.1 |
| learning rate | 10⁻⁶ |
| optimizer | 建议 RMSprop，基于显存考虑 |
| 训练长度 | 题目要求 HH 上 1 epoch |
| 记录 | 每步 loss、validation classification accuracy |
| checkpoint | 保存 validation accuracy 最高的版本 |

**重要原文差异，不能静默改题：** §6.4 将所记指标称为隐式 reward model 的 “classification accuracy”，随即按 **chosen 的原始条件 log-probability 高于 rejected** 定义。理论 DPO 的隐式 reward 排序则应比较上节的 **reference 校正差**。两者不恒等。[指导页](#/c/stanford-cs336-2026/lab/a5-safety-optional?v=guide) 给出无害数值反例。遵循作业文字时要明确报告定义；若同时记理论指标，应另列名称，不能把一个替换成另一个再声称严格一致。

- **（a）训练与选模**：实现 DPO loop，在 HH 上训练 **1 epoch**，保存 validation accuracy 最高的 checkpoint。交付**训练脚本与训练过程 validation accuracy 的截图**。截图应来自真实日志；没有实验就不能制作仿真曲线冒充结果。
- **（b）对话质量复评**：按 `alpaca_eval_sft` 的协议对 DPO 模型评估；**1–2 句**报告普通／length-controlled winrate，并与 SFT 模型比较。
- **（c）安全复评**：复评 SimpleSafetyTests；**1–2 句**报告结果及与 SFT 的比较。
- **（d）能力变化**：复评 **GSM8K 与 MMLU 两项**，用 **2–3 句**说明观察，讨论可能的 alignment tax。不能只给安全分数就断言“全面提升”，也不能未观察便断言一定产生能力税。

这里 DPO 的双 GPU 分工与 70B judge 的双 GPU 张量并行是两个不同环节，不能把它们看成同一种训练架构。基准生成发生在评估阶段；DPO loss 本身不需要在线采样回答。

## 5．源码合同与交付完整性

### 5.1 哪些测试覆盖选做

| 文件／入口 | 实际静态合同 | 不应推断的内容 |
|---|---|---|
| `tests/test_metrics.py` | 两类 parser 各有可解析／不可解析例子；字母／数值字符串 | 不能证明任意自然语言均能正确解析 |
| `tests/test_data.py` | packed 数据与固定 IDs／labels 比较；shuffle；batch shape、整数类型与末 batch | 不能证明混合数据来源或训练效果 |
| `tests/test_dpo.py` | 固定两模型、小 tokenizer 的单实例标量 loss | 不能证明完整 DPO loop 或安全收益 |
| `tests/adapters.py` | 选做部分共五个 hook：dataset、batch、两个 parser、DPO loss | 不能把正篇 GRPO hooks 当选做评分合同 |
| Alpaca 配置／模板 | 本地 70B pairwise ranking，固定参考文件 | 不是 GPT-4 API 依赖 |
| `evaluate_safety.py` | JSONL、布尔方向、保存评委原输出、mean safe | 不是严格验证过的布尔解析器或安全认证 |

README 的默认测试命令与 `test_and_make_submission.sh` 只指向 **`test_grpo.py`**。补充手册明确另用上述三份选做测试；所以“跑了仓库默认命令”不等于覆盖选做。打包脚本还对 pytest 使用 `|| true`，随后即使测试失败也可能生成 `code.zip`；zip 存在不表示测试通过。

固定 zip 脚本排除 `.json`、`.txt`、日志、模型权重与 `data` 等文件。因此手册要求保存的评估记录、模型／tokenizer、训练曲线不能假定自动进入 zip。应按课程当期提交说明管理这些交付物；**18 页补充没有另给独立的选做提交门户、截止时间或统一 writeup 文件名**，本页不虚构。

### 5.2 最终报告应能串起三阶段

这不是一份替学生填写的答案表，而是检查交付是否缺项的证据链：

1. 四 baseline 的原始输出、指标、生成速度；MMLU／GSM8K 解析失败统计；各题规定的错误抽样。
2. SFT 数据观察、packed loader 与 batch 合同、训练脚本、完整配置、最终 validation loss、真实学习曲线及 model／tokenizer。
3. 四 SFT 复评与相同协议下的阶段比较；受控安全评估的方法、预算与真实观察。
4. HH 四来源合并、单轮过滤、来源追踪与六条偏好观察；DPO loss、训练／validation／checkpoint 记录及真实截图。
5. DPO 在 **AlpacaEval、SST、GSM8K、MMLU** 的全部复评，区分改善、退化与没有足够证据的差异。

每份数值都要能追溯到模型、数据版本、split、模板、停止条件、解析规则、评委配置与日志。没有运行的项目写“未执行／不可达”，不填臆造分数。高安全比例不能独自回答过度拒绝；高 winrate 也不能独自证明真实性或无害性。

## 来源、版本与处理说明

- 第一方主来源：CS336 Staff，**Spring 2026 v26.0.0，18 页补充**，固定 [PDF](https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/c2734a26308710949fe13226960a1e8cece94b7e/cs336_spring2026_assignment5_supplement_safety_rlhf.pdf)。已逐页读全提取文本；原页 9、15–17 另做视觉核读，未声称逐页视觉审校。
- 固定 [README](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/README.md)、[CHANGELOG](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/CHANGELOG.md)、[选做 adapters 与 tests](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/tests)、[scripts 配置](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/scripts)、[环境 helpers](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/cs336_alignment) 与 [pyproject](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/pyproject.toml)。手册封面 v26.0.0、CHANGELOG 2.0.1、package 1.0.0 是不同字段，不强行统一。
- [课程主页](https://cs336.stanford.edu/) 的政策入口与固定 [AGENTS](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/AGENTS.md)；课程政策及集群指南采用 P1 保存的官方快照，权限限制未作运行验证。
- 模型公开元数据：[Llama 3.1 8B](https://huggingface.co/api/models/meta-llama/Llama-3.1-8B)、[Llama 3.3 70B Instruct](https://huggingface.co/api/models/meta-llama/Llama-3.3-70B-Instruct)。P1 快照 revision 分别为 `d04e592bb4f6aa9cfee91e2e20afa771667e1d4b` 与 `6f6073b423013f6a7d4d9f39144961bfbfbc386b`；未下载权重。
- 数据来源与许可：[UltraChat-200K 固定卡](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k/blob/8049631c405ae6576f93f445c6b8166f76f5505a/README.md)、[SafetyTunedLlamas 固定 README](https://github.com/vinid/safety-tuned-llamas/blob/36a4b8d5c2177ed165bf61f59b590161394f7f12/README.md)、[HH 固定卡](https://huggingface.co/datasets/Anthropic/hh-rlhf/blob/09be8c5bbc57cb3887f3a9732ad6aa7ec602a1fa/README.md)、[AlpacaEval 固定卡](https://huggingface.co/datasets/tatsu-lab/alpaca_eval/blob/2edc6fad8be6b14ea7230aabfd08188da6b8b814/README.md)、[SimpleSafetyTests 固定许可](https://github.com/bertiev/SimpleSafetyTests/blob/d7aee9a9422a5a5488f478fd79c2479c891c0f3b/LICENSE)、[MMLU 元数据](https://huggingface.co/api/datasets/cais/mmlu)、[GSM8K 元数据](https://huggingface.co/api/datasets/openai/gsm8k)。本次只读元数据／说明，不读或镜像数据正文。

以上来源原文、PDF 与渲染只留在来源证据目录，不随正文镜像发布。中文为独立编写的任务说明与必要短引；没有声明得到作业全文翻译许可，也没有把数据／模型许可扩大为整份作业许可。本页未提供官方计分题的实现或实测答案。
