---
title: A3 缩放律：完整实验说明
kind: 固定 2026 官方第一方要求的中文重述；非解答
source: CS336 Assignment 3 (scaling), Spring 2026, Version 26.0.5
source_commit: 03e9372992e913061b9e78b5cfcb62ad8a87de35
source_read_scope: 全部 8 页提取文本；README、LICENSE、CHANGELOG、相关配置/模型/训练/API/客户端源码；未逐页视觉审校
status: P5 作者交接；2 个计分 Problem、2 个字母子问、5 个报告讨论项；页面验收待主审
execution: 未执行官方代码或实验，未调用训练 API，未安装依赖或获取凭据、模型、训练数据
license: 第一方软件与相应文档为 MIT；完整版权和许可见页底；第三方材料与服务不在此授权内
---

# A3 要交付什么

你要在有限预算下判断：该训练更大的模型，还是让较小的模型看更多 token？A3 将这个问题拆成两个**不可互相替代**的任务：先用公开合成结果练习 IsoFLOPs，再用真实训练 API 的小规模实验预测大规模训练。

| 任务 | 分值 | 可用证据与预算 | 最终目标 |
|---|---:|---|---|
| `chinchilla_isoflops` | 5 | 72 条公开合成 run；9 档 FLOPs | 外推模型规模与数据规模；各交图和预测 |
| `scaling_laws` | 50 | 单 B200 真实训练 API；累计 12 小时探索硬上限 | 预测单 B200 训练 48 小时的最优配置与 validation loss |

本页忠实保留题目、子问、接口约束和交付要求，不提供拟合结果、最优超参数、计分题答案或可提交代码。概念、实验设计和诊断见 [A3 指导](#/c/stanford-cs336-2026/lab/a3-scaling?v=guide)。文中的“提交”“训练”均为学生待完成事项，不是本站执行记录。

## 0．版本、政策与访问范围

### 0.1 固定 2026 版本，不混用预算

本页依据 **Spring 2026、PDF v26.0.5、8 页**；仓库 Python package 的版本仍为 **26.0.2**。它们是不同对象的版号，不互相覆盖。

- CHANGELOG **26.0.0 / 2026-04-29**：从离线模型训练 API 改为在线真实训练。
- **26.0.1 / 2026-05-01**：增加 AI 政策及 agent 指导。
- **26.0.2 / 2026-05-04**：移除训练配置的最大 runtime 上界，以容纳 48 小时最终提交；不是移除探索预算。
- **26.0.3–26.0.4 / 2026-05-05**：增加打包脚本，随后改名为 `make_submission.sh` 并去掉 pytest。
- **26.0.5 / 2026-05-08**：训练依赖改为可选依赖。

旧 CHANGELOG 的 **2024 / 2e18 FLOPs**、离线回归器及历史日期不是本题的 2026 API 预算。2026 handout 仍有 “FLOPs budget” 和 “25% of our big run FLOPs budget” 的措辞残留；本部分明确的预算单位是 **B200-hours，即单 B200 的训练 wall-clock 时间**。12 小时相当于 48 小时目标的四分之一时间，不能据此承诺任何固定 FLOPs 总量。

### 0.2 AI 政策与独立完成

官方允许 AI 回答**高层概念**或提供**底层 API / 函数签名文档**，禁止 AI 实现任何作业部分，包括排行榜、实验脚本、coding agent 与 AI 自动补全。关闭 AI 自动补全；普通函数名补全不在禁止范围内。不得修改仓库 `AGENTS.md`，使用在线聊天时按官方要求带上该文件内容。

固定 `AGENTS.md` 进一步明确：不给 Python 或伪代码，不替学生写报告、解数学题、填作业实现或提供完成方案。本页是教学资料的要求重述，不是学生的 `writeup.pdf`；指导页只解释概念与检查问题。**拟合脚本、实验决策、数学回答、图与报告须由学生自己完成。**

### 0.3 学生 API 与非学生自建是两条路线

正式课程学生按题设**只通过 API 训练**，仓库训练代码供参考。API 需课程已登记用户的 **8 位 Stanford ID** 作为 `X-API-Key`，并处在 Stanford 网络内，必要时用 VPN。服务端会查已登记用户表；任意八位数字、普通 GitHub 账号或仅有 Stanford 身份都不等于获准访问。

README 的学生环境使用 `uv sync`，客户端从自己的环境变量 `A3_API_KEY` 读取 ID。不要把 ID、请求头、密钥、私人名册贴入报告或提交包。本站不获取凭据，不打开带身份的接口，不检查当前余额或服务存活。

固定包要求 Python **≥3.12**；基础依赖为 `pydantic≥2.8`、`requests≥2.32`、`rich≥14.0`，训练／服务栈放在 `server` extra。handout 建议的拟合工具不等于基础客户端依赖已全部包含。`uv sync` 可能安装或下载环境，本次未执行，也不承诺本机兼容性已验证。

非学生 README 另列 `server` 可选依赖、自建数据和 API 路线。**公开代码不等于校内训练额度，也不等于开箱即用的 standalone 训练程序。**具体静态矛盾和依赖见第 6 节。

## 1．Part 1：IsoFLOPs 合成数据练习

### 1.1 方法与输入（§2–2.1，pp.2–3）

训练计算量的课程近似为：

$$
C \approx 6ND,
$$

其中 $N$ 为模型参数量，$D$ 为训练 token 数，$C$ 为 FLOPs。同一预算下，增大模型会减少能训练的 token 数。很小的模型受容量限制；很大的模型又可能没有足够训练步。因此固定预算的 loss profile 常出现中间较好、两端较差的形状。

题目要求学生**自行写脚本**，用仓库 `data/isoflops_curves.json` 重现 handout 描述的 IsoFLOPs 缩放律方法。该文件是 **合成数据**，不是课程 API 的历史真实训练记录：

- 共 **72 条 run**，每档预算 8 条，共 **9 档**。
- 预算依次为 `6e18`、`1e19`、`3e19`、`6e19`、`1e20`、`3e20`、`6e20`、`1e21`、`3e21` FLOPs。
- 每条记录含 `parameters`、`compute_budget`、`final_loss`；这里最后一项是**最终训练 loss**。
- 根据预算与参数量的关系得到相应训练数据规模。这里的数据规模单位是 **token**，不是文档数、字节数或 epoch。

论文用每条 profile 的二次拟合寻找最低点；**本题建议直接采用每个预算中观察到训练 loss 最低的那条 run**。它是离散已观测点的最小值，不应悄悄替换为平滑曲线的连续极小值。随后用各预算下的模型／数据规模点拟合幂律并外推。

handout 提到 `scipy`，尤其 `scipy.optimize.curve_fit` 可能有用，但允许任意曲线拟合方法，不强制库或某种回归算法。论文原理可回看 [Chinchilla 精读](#/c/stanford-cs336-2026/lec/lec09?v=materials)；题目方法以本节特定要求为准。

### 1.2 Problem：chinchilla_isoflops（5 分）

**(a) 模型规模。**展示外推的 compute-optimal model size，连同所用的 $\langle C_i,N_{\mathrm{opt}}(C_i)\rangle$ 点。回答预算分别为 **$10^{23}$ 和 $10^{24}$ FLOPs** 时，预测的最优模型参数量是多少。

**交付：**一幅模型规模随计算预算变化的缩放律图，显示用于拟合的数据点，且外推范围**至少达到 $10^{24}$ FLOPs**；再用一句话给出这两个预算下的模型规模预测。

**(b) 数据规模。**展示外推的 compute-optimal dataset size，连同从训练 run 得到的 $\langle C_i,D_{\mathrm{opt}}(C_i)\rangle$ 点。回答预算分别为 **$10^{23}$ 和 $10^{24}$ FLOPs** 时，预测的最优训练 token 数是多少。

**交付：**一幅数据规模随计算预算变化的缩放律图，显示用于拟合的数据点，且外推范围**至少达到 $10^{24}$ FLOPs**；再用一句话给出这两个预算下的数据规模预测。

**完整性边界：**两幅图、两个模型规模预测、两个数据规模预测均不可遗漏。这里不要求重新训练那 72 个模型；也不能拿完成此题冒充完成下一个 50 分任务。本站未运行该数据的回归或生成它的计分答案。

## 2．Part 2：真实训练设置与搜索空间

### 2.1 任务目标（§3，pp.3–4）

用真实 API 实验拟合缩放律，选择预期能在**单 B200、48 小时**内取得最低 validation loss 的模型规模和超参数，并预测其最终 validation loss。拟合阶段累计最多使用 **12 B200-hours**；这是 API 强制的探索硬上限。应在消耗预算前安排实验，并研究小规模设置中超参数对 validation loss 的影响。

开篇用“最低 training loss”引入 compute-optimal 概念；但此处 API 返回、最终预测及排行榜使用的是 **validation loss**。不能把 Part 1 的训练 loss 列当作 Part 2 的验证观测。

### 2.2 固定的模型与数据语义

| 项目 | 固定要求或已读源码事实 |
|---|---|
| 训练硬件 | 每次 run 是单 B200；不是 12 卡跑 1 小时的自由替换承诺 |
| 模型实现 | 与 A1 架构大体相似，但实际为 **JAX / Equinox**，不是直接执行学生 A1 PyTorch 模型 |
| 架构细节 | 因果 attention、RoPE、pre-RMSNorm、SiLU 门控 MLP；Q/K 在每头维度还有 RMSNorm；无 dropout |
| tokenization | DCLM 数据；固定 Llama-2 tokenizer 语义，32,000 词表；源码名称为 `NousResearch/Llama-2-7b-hf`，不是要求下载 7B 模型权重 |
| 序列长度 | `seq_len = 512`，API 固定；不作为提交字段改长 |
| 训练数据上限 | `total_train_tokens` 最多 **500,000,000,000**，无 epoching |
| 数据顺序 | 不同配置消耗相同的确定性 token 顺序；不是各 run 随机换一份数据 |
| 随机种子 | `model_seed` 只控制模型初始化，不控制数据顺序 |
| 探索验证集 | 每次验证用 **$2^{18}=262,144$ token**；最终 leaderboard 用更多 token，具体数量 handout 未给出 |
| loss | 512-token 序列上的平均 next-token cross-entropy；固定批次内没有另一个可调 dropout 目标 |
| 优化器 | AdamW 或 SGD，均为 warmup-cosine 学习率调度 |

数据生成器准备的验证 token 池默认为 $2^{29}$；这**不是**探索 run 的验证用量。训练配置的 $2^{18}$ 才是 API 每轮评估大小。固定源码的数据预处理含确定性打乱；“固定顺序”不表示原始文档从未被打乱，也不表示把 `model_seed` 换掉就获得独立数据样本。

### 2.3 architecture_config：完整字段与限制

| 字段 | 作用与边界 |
|---|---|
| `attention_bias` | attention 线性投影是否使用 bias |
| `head_dim` | 每头维度；正整数，且为偶数以满足 RoPE |
| `hidden_size` | 模型宽度；正整数，必须等于头数乘每头维度 |
| `intermediate_size` | 门控 MLP 的中间宽度；正整数，且不得小于模型宽度 |
| `num_attention_heads` | attention 头数；正整数 |
| `num_hidden_layers` | Transformer 层数；正整数 |
| `num_key_value_heads` | KV 头数；正整数；**当前验证器要求等于 attention 头数** |
| `rms_norm_eps` | RMSNorm 的正数 epsilon |
| `rope_theta` | RoPE 的正整数 theta |
| `tie_word_embeddings` | 是否共享输入 embedding 与输出投影权重 |
| `dtype` | 仅 `float32` 或 `bfloat16` |
| `vocab_size` | 词表维度；使用固定 32k tokenization。源码只作正数检查，不代表可随意更换数据词表 |

handout 写“attention 头数须能被 KV 头数整除”，但固定源码进一步要求**两者相等，明确不支持 GQA**。不能只根据字段存在或整除条件就承诺 GQA 可用。`dtype` 控制模型构造使用的 dtype；不能由一个字段推断所有中间结果、统计量、优化器状态都使用同一种精度。

### 2.4 optimizer_config：支持的字段与约束

两种优化器都有 `lr_scheduler` 与 `grad_clip_norm`。调度器的四个字段：

- `peak_value`：峰值学习率，必须大于 0。
- `init_value`：初始学习率，不小于 0。
- `warmup_frac`：warm-up 占总 optimizer steps 的比例，范围 $[0,1)$。
- `final_lr_frac`：终点学习率相对峰值的比例，范围 $[0,1]$。

源码 warm-up 步数取 `int(总步数 × warmup_frac)`，cosine 调度长度依据**计划的总 optimizer steps**。不是按服务器等待时间调度。`grad_clip_norm` 为正数或 `None`；若启用，使用全局梯度范数裁剪。

AdamW 另外接受 `weight_decay`、`beta1`、`beta2`、`eps`、`eps_root`：weight decay 不小于 0；两个 beta 均在 $[0,1)$；`eps > 0`，`eps_root ≥ 0`。SGD 配置没有另行开放 momentum 或 weight decay 字段，不要照搬其他库完整 SGD 参数表。

**官方示例／默认值，不是推荐最优答案：**峰值学习率 `3e-4`、初始值 `0`、warm-up 比例 `0.05`、末尾比例 `0.1`；AdamW 的 weight decay `0.01`、betas `0.9 / 0.95`、`eps = eps_root = 1e-8`、梯度裁剪 `1.0`。示例只说明接口，不构成 48 小时配置建议。

### 2.5 顶层训练字段与整除约束

除了上述两个配置对象，请求还包括：

| 字段 | 意义与验证条件 |
|---|---|
| `train_batch_size` | 每个 optimizer step 的序列数，正整数 |
| `val_batch_size` | 验证 batch 的序列数，正整数 |
| `n_evals` | 正整数；训练分为这么多 chunk，默认 16 |
| `total_train_tokens` | 正整数，不超过 500B |
| `max_runtime_seconds` | 预留的最大训练 wall-clock 秒数，至少 1 秒；探索还须不超过剩余 12 小时预算 |
| `model_seed` | 非负初始化种子，默认 0 |

还必须同时满足：

1. 总训练 token 数能被 `512 × train_batch_size` 整除。
2. 总 optimizer steps 能被 `n_evals` 整除，保证各训练 chunk 的步数一致。
3. $2^{18}$ 能被 `512 × val_batch_size` 整除。
4. 第 2.3–2.4 节的架构、调度和优化器条件全部满足。

每 chunk 训练 `total_train_tokens / n_evals` 个 token，再评估一次。`seq_len` 与验证 token 数是类级固定值，不是可覆写的请求项；配置模型拒绝额外字段。请求合法不代表显存一定足够，也不保证能在时限内完成。

handout 的完整请求示例采用宽度 448、中间宽度 1280、9 层、7 个 attention/KV 头、每头 64、无 attention bias、RMSNorm epsilon `1e-6`、RoPE theta `1,000,000`、不共享 embedding、BF16、32k 词表；训练／验证 batch 为 128／32，16 次评估、1,048,576 个训练 token、30 秒上限、种子 0。这里只保留原例的字段含义和数值，**不附可执行请求，也不把例子标作最优配置或已验证训练记录**。

## 3．API 合同、预算与结果状态

### 3.1 六个 method/path 接口（§3.2，pp.4–7）

所有请求都使用 `X-API-Key`。下表是接口说明，不是让读者在无资格时尝试服务的命令。

| 方法与路径 | 输入／用途 | 返回与注意事项 |
|---|---|---|
| `POST /submit` | 完整 TrainingConfig，排队一个探索实验 | `experiment_id` 与 `budget_summary`；真实消耗或预留探索预算 |
| `GET /budget` | 查看自己预算 | `used_seconds`、`remaining_seconds`、`total_budget_seconds` |
| `GET /experiments` | 列出自己的实验 | 每项含 ID、提交配置、状态 |
| `GET /experiment/{experiment_id}` | 查询自己的一次实验 | 与列表元素相同的结构；用于观察直至终态 |
| `POST /final_submission` | `training_config` 和 `predicted_final_loss` | 保存最终预测；重复提交以最新一次覆盖旧值 |
| `GET /final_submission` | 查当前最终预测 | 配置、预测 loss、提交时间；尚未提交为 `None`／JSON `null` |

共 **5 个不同 path、6 个 method/path 组合**；最终提交路径分别支持 GET 与 POST。

### 3.2 预算不是“看到 completed 才扣”

探索总预算为 **43,200 秒 = 12 小时**。

- `queued` 和 `running` 都按完整 `max_runtime_seconds` **预留**预算。
- `completed` 或 `failed` 后，按报告的实际 runtime 重新计算，收费范围截在 **至少 1 秒、至多该 run 的最大 runtime**。
- 如果预留 30 分钟而 12 分钟完成，18 分钟归还。超时失败按该 run 上限计费。
- 上限超过当前剩余预算，`/submit` 返回 **400**；相同训练配置再次提交，handout 规定 **409**，不重复预留。源码先检查余额再检查重复，不能把 409 当作任意余额下必定先出现的状态。
- `used_seconds` 包括已用和仍预留的时间；同时排队多个实验也可能耗尽可预留余额。

训练 worker 在数据准备、模型构造和编译之后才启动训练计时，计时区间包含训练 chunk 和评估。API 的 `running` 状态还包含启动与抢占等等待，持续时间可能长于请求上限。**排队／状态显示的日历时间、API 结算秒数、纯训练 kernel 时间不是同一量。**此处依据静态代码，不是服务端实测。

### 3.3 什么算可用的最终 loss

| `status_type` | 含义 | 分析边界 |
|---|---|---|
| `queued` | 排队等待 | 只有配置与预留，不是完成结果 |
| `running` | 已派发，可能正在启动／恢复／训练 | `val_losses` 是目前观测序列，不是完整 run 的最终值 |
| `completed` | 计划训练完成 | 含 `used_runtime_seconds`、`val_losses`、`completed_at`；用 loss 列表**最后一个**作为该 run 最终 validation loss |
| `failed` | 崩溃或超时 | 不作为完成 run；可以检查失败原因与超时前局部验证记录 |

handout 的概要把 timeout 的局部结果称 `partial_val_losses`；固定 schema 的精确位置是 **`status.reason.partial_val_losses`**，且 timeout 分支的 `reason` 为 `timeout`。普通 unexpected failure 则给失败文字，不保证有局部 loss。不能对失败状态无条件读取 `status.val_losses`，也不能将最后一次局部评估假装成计划终点。

### 3.4 最终预测提交不是 48 小时探索接口

最终提交包含完整训练配置和一个正的 `predicted_final_loss`。`POST /final_submission` 在已读源码中是保存／覆盖预测记录，**不会像 `/submit` 那样加入探索队列、预留 48 小时或返回一次可反复试的 48 小时结果**。它与提交后的官方最终评测是两个层次。

共享 TrainingConfig 只有 runtime 下界，没有 12 小时的字段级上界；探索上限由 `/submit` 的余额检查约束。最终目标仍是题目规定的 **48 小时**，不能因此提交任意长时限并称符合题意。固定 worker 的 Modal 装饰器仍设 12 小时 timeout；本次已读源码没有证明完整 48 小时最终评测部署如何另行启动，故不声称最终训练已可在该默认 worker 中运行。

## 4．Problem：scaling_laws（50 分；§3.3，pp.7–8）

构建缩放律，选择预期在 **48 B200-hours** 内达到最低 validation loss 的模型规模与超参数，并预测该 loss。拟合使用的真实 API 实验累计不得超过 **12 B200-hours**。所有 run 均为单 B200。

handout 称最终超参数“基本不作限制”，意思是学生需要自行研究广泛的搜索空间；仍受已提供模型/API 的字段、数据、整除条件与固定训练协议约束，不等于可换任意架构、词表、上下文或多卡环境。

### 4.1 报告必须解释的五项决策

1. **实验选择：**在固定 12 B200-hours 预算内，怎样决定查询哪些 run？说明选择依据，而不只给最终最好的一个结果。
2. **拟合方法：**采用了什么具体方法或多个方法？handout 建议熟悉 Kaplan 与 Hoffmann 的方法；不能只写“拟合了一条曲线”。
3. **拟合质量：**缩放律与实验数据吻合得怎样？呈现能支持自己判断的证据。
4. **外推结果：**对题设 48 B200-hours 目标，预测最优模型规模是多少，预测 loss 是多少？保留时间预算口径，不把它改成旧版 FLOPs 数字。
5. **超参数落地：**若训练预测参数量的模型，具体使用什么超参数？handout 给出的**非 embedding 参数量近似**为：

$$
N_{\mathrm{nonembed}}
\approx 12\,n_{\mathrm{layer}}\,d_{\mathrm{model}}^2.
$$

这是题目提供的估算，不是任意 FFN 比例、共享方式和 bias 设置下的精确总参数数。报告应说明采用的参数统计口径，不能把非 embedding 近似、含 embedding 总数、实际模型构造结果混成一列。

### 4.2 本题的完整交付

- **排版后的完整书面报告**：说明缩放律构建、拟合与外推的整个方法和预测数值；解释具体设计决策，详细到能够复现自己的方法与结果；包括上面的五项讨论。
- **API 最终记录**：提交预测最优超参数／训练配置，以及预测的最终 validation loss。可以覆盖最终记录，但这不产生额外探索额度。
- 成绩的一部分取决于**所预测最优模型的实际表现**。本页不捏造评分阈值、排行榜基准、通过线或自己的成绩。

Part 2 未像 Part 1 那样指定必须交几幅图；拟合质量、预测与复现性必须有足够证据，具体呈现由学生决定。不要凭空把“固定三图”或某种回归器写成官方评分条件。

## 5．统一提交与完整性清单

提交到 Gradescope：

1. **`writeup.pdf`**：Part 1 的两幅图与四个预测数值，以及 Part 2 的完整方法、五项决策讨论、预测规模／配置／loss。说明足以复现结果。
2. **`code.zip`**：学生自己编写的缩放律拟合与估计代码，保留实际用到的方法；不是只交最后一张图或只有 API 配置。
3. **另外在 API 保存最终配置与预测 loss**，不是拿 Gradescope 的文件替代接口记录。

固定 `make_submission.sh` 产生 `cs336-assignment-3-submission.zip`；脚本里“tar.gz”的注释是残留，实际使用 zip。它不运行 pytest，而且排除 `.json`、`.txt`、`.log` 等格式及若干缓存／权重文件。因此**“有 zip”不等于结果正确或证据齐全**；不要假定 JSON 实验记录、文本分析或图表原始数据会自动进入包。按课程最终平台要求检查包内容；不把 ID、密钥、环境文件或不必要的大型数据一起提交。

### 5.1 任务到证据的对应

| 原题位置 | 必须保留的内容 | 本页位置 |
|---|---|---|
| pp.1–2，Overview / AI | 两类交付、API 最终提交、政策 | §0.2、§5 |
| pp.2–3，Problem 1(a) | 模型规模点、幂律图、外推至少至 $10^{24}$、两个预测 | §1.1–1.2 |
| p.3，Problem 1(b) | 数据规模点、幂律图、相同外推范围、两个预测 | §1.2 |
| pp.3–4，§3–3.1 | 12 小时探索、48 小时目标、固定数据与训练语义 | §2、§3.2–3.3 |
| pp.4–7，§3.2 | 所有请求字段、预算、状态、最终记录的读写 | §2.3–2.5、§3 |
| pp.7–8，Problem 2 | 完整方法、五个讨论项、配置／loss 预测与实际表现评分 | §4 |
| 固定源码与 README | GQA 禁止、精确 schema、自建路线边界、打包差异 | §2.3–2.5、§3、§5–6 |

完整逐项映射（含每个接口、配置字段与整除条件）保存在来源证据 `p5-a3/task-coverage.json`。这份映射证明的是**说明覆盖**，不是作业答案或实验执行覆盖。

## 6．非学生自建：公开，但并非已验证可直接运行

README 写出非学生路线：`uv sync --extra server` 准备服务／训练依赖，用 Modal 数据脚本准备数据，以训练脚本直接运行，或配置 PostgreSQL 与内部 API key 后启动 FastAPI 和 dispatcher。这里仅说明其存在与边界，不提供一键执行步骤。

### 6.1 direct-run 与 Modal call ID 的静态矛盾

证据链来自同一个固定版本：

1. README 将运行 `cs336_scaling/training/run.py` 称为直接训练。
2. 该文件 `__main__` 调用 `run_training.local(...)`。
3. `run_training` 一开始调用 `modal.current_function_call_id()`；若没有 Modal function call ID，立即抛出 `ValueError`，说明不能在 Modal function call 之外运行。

**静态推断：**README 的普通本地命令与函数的 Modal 上下文前置条件冲突，不能写成“装完就能 standalone 训练”。本次没有执行该命令，因此不把静态推断冒充实际复现报错。文件另有 Modal remote 入口；有远程入口也不意味着账户、数据和服务都已准备好。

### 6.2 自建必须独立承担的外部依赖

- 自己有权使用的 GPU、CPU／RAM、磁盘和数据来源；服务端依赖含 JAX 0.9.1，Linux 使用 CUDA 13 分支、Equinox、Optax、Flash-Hog 等。源码存在 CPU attention 分支，**不证明完整训练流程能在普通 CPU 环境开箱运行**。
- 自己的 Modal workspace、app 与 volumes。代码含 staff namespace，dispatcher 直接查找 `scaling-brunborg`，不能以默认字符串当作可借用校内服务；配置里写 `launch_mode` 也不是已经实现的独立本地 worker 路线证明。
- 默认 W&B entity 为 `hashimoto-group`，以及课程 project；使用源码不能自动获得其记录权限。
- 训练 worker 会回报内部 API；客户端使用内部 key、可选 Tailscale 地址及本地 1080 端口代理。Modal secrets 声明涉及 HF、W&B、Tailscale 与内部 API 凭据；这些配置名公开不代表凭据可索取或共享。
- 自建 API 还需自己的 PostgreSQL、用户登记与服务／dispatcher 配置。不得获取或复用课程私人学生名册。

### 6.3 数据准备不是轻量下载例子

默认数据生成脚本并行处理 **3,333 个 shard**，`max_containers = 100`。token 数据使用 `uint16`；**按默认 500B tokens 推算，仅 token 载荷约 1 TB（十进制）**，还没有包括原始文档、序列长度、验证池、填充、shuffle 中间副本和运行缓存。这是量纲估算，不是下载量或峰值磁盘实测。

源码默认每个最终 token chunk 为 $2^{29}$ 个 token，预处理 workers 为 32，并有大型临时磁盘申请；这些是实现默认值，不是承诺最低机器规格。源数据 URL 使用 `@main`，tokenizer 名称也未在该处固定 revision；固定代码提交不等于重建时的远端数据／tokenizer 字节快照已固定。

本次没有运行任何数据、模型、tokenizer 下载，没有启动 Modal、训练或付费资源，也没有核验第三方数据完整授权或当前服务可用性。校外可以阅读协议、学习方法；没有正式 API 和真实训练证据时，**不能声称完成原 50 分 Part 2**。CPU 分析合成数据仅能对应 Part 1／独立概念练习。

## 7．延伸阅读、来源与许可

### 7.1 阅读路径

- [L09：缩放律（一）](#/c/stanford-cs336-2026/lec/lec09)：理解固定计算量的模型／数据权衡。
- [L11：缩放律（二）](#/c/stanford-cs336-2026/lec/lec11)：理解实验外推与更复杂的缩放问题。
- [ext12：缩放律的统计方法](#/c/stanford-cs336-2026/lec/ext12)：拟合假设、残差、不确定性与可识别性。
- [Chinchilla 唯一精读页](#/c/stanford-cs336-2026/lec/lec09?v=materials)：方法背景，不在 A3 重复论文正文。
- [ext04：资源账本](#/c/stanford-cs336-2026/lec/ext04) 与 [ext06：性能测量](#/c/stanford-cs336-2026/lec/ext06)：区分参数、计算量、显存与时间。

handout 引用 Kaplan（2020）、Hoffmann（2022）、Yang 的 Tensor Programs V（2022），允许 Part 2 参考其他方法，并建议熟悉前两者。A3 的必做方法练习是 handout 自包含的 IsoFLOPs；这不等于指定三篇论文全文必读。DCLM 是数据来源提及，也不自动构成 DataComp-LM 论文必读。

### 7.2 固定来源与本次实际阅读

- [官方固定仓库](https://github.com/stanford-cs336/assignment3-scaling/tree/03e9372992e913061b9e78b5cfcb62ad8a87de35)、[8 页 handout](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/cs336_assignment3_scaling.pdf)、[README](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/README.md)、[CHANGELOG](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/CHANGELOG.md)。
- 本次重新通读全部 8 页提取文本、README／LICENSE／CHANGELOG、完整相关配置、模型、训练循环／worker、公共 API、客户端、认证、预算、schema 与自建服务耦合源码。token 数据生成器实际细读第 1–243 行的来源、格式与默认规模；未将其余外部排序实现称作全文复核。
- [TrainingConfig](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/cs336_scaling/training/training_config.py)、[worker 与入口](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/cs336_scaling/training/run.py)、[公共 API](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/cs336_scaling/api/public.py)、[模型](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/cs336_scaling/training/model/basic_model.py)。
- [官方 AI 政策](https://docs.google.com/document/d/1SZAlExB1qAc9izHt54gwunNpjKE6wXb8Y7yA_e-baK8/edit)、[固定 AGENTS](https://github.com/stanford-cs336/assignment3-scaling/blob/03e9372992e913061b9e78b5cfcb62ad8a87de35/AGENTS.md)。API 文档地址为 `http://hyperturing.stanford.edu:8000/docs`；此处登记来源，不表示已连通。
- 来源存档与新取文本的日期、SHA256、实际阅读范围及加工方式见 `p5-a3/manifest-fragment.json`；逐项覆盖见 `p5-a3/task-coverage.json`。作者完成、页面验收、正式实验执行是不同状态。

### 7.3 第一方 MIT 完整声明

本页对官方第一方作业文档作中文重述，并增加独立的配置／访问边界说明。下列 MIT 授权只适用于仓库第一方软件和相应文档，**不扩展到论文、第三方图表、DCLM／tokenizer 数据、模型、软件依赖、Stanford／Modal／W&B 服务或访问资格**。

> Copyright 2026 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
