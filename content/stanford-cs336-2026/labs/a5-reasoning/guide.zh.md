---
title: A5 推理 RL 指导：先核合同，再解释曲线
kind: 原创概念教学、分阶段决策与独立算例；非实现、非提交答案
source: 固定2026 A5主篇39页及相关源码合同
source_commit: c2734a26308710949fe13226960a1e8cece94b7e
source_read_scope: 全部手册提取文本；7个原PDF选页视觉检查；README、CHANGELOG、helpers、adapters、主篇tests、fixtures定义与配置静态阅读
execution: 未执行官方测试或实验；算例是编者原创数学期望值，待主审独立复核，不是模型结果
license: 原讲义全文翻译许可未核实；本页采用原创教学解释与有限接口引用
---

# 一条 reward 曲线，至少有六层解释

读[完整任务说明](#/c/stanford-cs336-2026/lab/a5-reasoning?v=zh)确认28题、90分与每题交付。本页帮助你决定**现在能提出什么判断、下一步该检查哪一层证据**，不替你实现函数、解答计分推导题、提出自拟 estimator 或编写报告。

正式实验对象固定为 **OLMo-2-0425-1B＋GSM8K**。本页没有模型运行、官方单测结果、学习曲线或训练前后样例；以下小概率／标量／掩码案例均为独立原创，不含官方 fixtures，也不能满足作业的实验交付。

![同一rollout批的一次更新与多次更新](assets/policy-clock.svg)

## 1．先分清“我在优化什么”与“我拿什么估计它”

### 1.1 三个分布，不能全叫 model

**任务分布 $\rho$** 决定抽到什么题。 **行为策略 $\pi_0$** 决定本次 rollout 的 token 从哪里来。 **当前策略 $\pi_\theta$** 是此刻接受梯度更新的模型。

目标是当前策略在任务分布上的期望奖励：

$$
J(\theta)=\mathbb E_{x\sim\rho}\left[\mathbb E_{y\sim\pi_\theta}[r(x,y)]\right].
$$

写这个目标不等于任意一个以 reward 加权的 loss 都在无偏优化它。你还要回答：样本由谁产生？优势是否基于同一组样本？是否除长度／std？是否使用过时的 prefix？每个修改都可能改变估计器的期望、尺度或方差。

本正篇的 old policy 是**每次生成时的临时快照**。它不是 DPO 中长期冻结的 reference，也不是用来估计人类偏好的 reward model。作业没有要求加入 KL penalty；不要看到论文中的 GRPO 名字就把论文完整目标的所有项搬来。DPO 与更一般后训练目标可回链[后训练目标专题](#/c/stanford-cs336-2026/lec/ext14)，论文细节见[RLVR 材料页](#/c/stanford-cs336-2026/lec/lec16?v=materials)。

### 1.2 一张 gradient-path 清单

- 采样得到的 token、外部 grader reward、group baseline／normalizer 是本次更新使用的观察值；不要让梯度穿过 parser 或凭空穿过离散采样。
- **当前** policy 的 teacher-forced log-probs 保留梯度。
- **旧** policy 的 log-probs 固定，不随 optimizer step 更新，不参与梯度。
- importance ratio 中当前分子是目标的一部分；把整个 ratio detach，再仍使用以 ratio 本身为目标的形式，会改变梯度。反过来，某些“梯度权重形式”的写法需要 stop-gradient 才不多出项。不能只比数值相同就判断实现等价。
- metadata 的记录通常不应长期持有整张训练图；但为了打印而提前把训练 loss 变成 Python 数字，也会丢失可反传路径。

**自查：** 两个 scalar loss 在某个参数点值完全相同，能否推出更新相同？不能。检查的是目标对参数的依赖关系，不只是当前数值。官方 train-step snapshot 因而同时比较 loss 与更新后的参数。

### 1.3 把 source contract 看作分层证据

手册给数学语义和交付；adapter 给形状与参数名；test 给选定输入下的可观察要求；helper 给真实服务请求行为。这四者互补，不互相替代。

例如手册写 top-p=1，但固定 helper 请求没有转发 top_p；这并不能推出“实验用了不同 top-p”，也不能推出“调用者设什么都生效”。严谨说法是： **必须核实际服务版本的默认／请求设置，当前静态证据只能证明该字段未显式发送。** 同理，test 的 cliprange=0.1 不是正式实验推荐0.2；test 的小模型不是正式能力对照。

## 2．阶段A：奖励看起来为零，先别动学习率

### 2.1 一次生成失败有三种不同含义

1. **能力失败：** 输出形成了可提取答案，但答案错误。
2. **表达／截断失败：** 模型可能产生相关推理，却没完成规定标签或 boxed；或者达到512 token 截断。
3. **解析失败：** 人可理解的正确答案没有被固定 parser 识别，或严格格式门拒绝了它。

三者在训练中都可能获得0，但对应干预不同。T01 要求分别统计三个 format／correctness 类别，并人工看误判，目的就是防止把这三类全部叫“模型不会算”。

**决定是否进入训练的门槛：** 不是必须先有很高 baseline，而是你能追溯一条输出为何得到这个 reward。保留原始文本、finish_reason、对应 prompt、真值抽取方式和 parser 身份，才能解释低起点。

### 2.2 格式契约是字节级的，不是图形上相似

固定 r1 grader 检查字面 `</think> <answer>`，中间是一个空格；提示已提供 `<think>`。不要先对输出做额外空白改写，再将“修改后的评分”与原 baseline 混为一谈。two r1 prompts 使用同一类 parser，question-only 使用 boxed parser；安全选做的“取最后数字”不属于本合同。

ground truth 是数据 answer 字段 `####` 后的答案，不是整段 rationale。若把整段解释送进 matcher，后面再调 loss、cliprange 都不能补救错误监督。

**概念自查（非 grader 执行）：** 文本含有正确数字，但没有所需结构，能否说它应在本作业获得1？不能；本作业 reward 同时受到可解析性约束。可以另列人工判读结果说明 verifier 漏报，却不能偷偷替换训练奖励后仍宣称同一实验。

### 2.3 format 不加分，仍必须记录

format reward 与 total reward 分开记录可帮助判断：模型是先学会协议，还是算术正确性也提高？若格式提升而 total 不动，不能写“数学推理显著进步”。若 total 上升、响应长度极端变长，也应检查增加的采样计算、截断与答案检查器的局限。

该 grader 只判断最终答案相容性，**不证明推理链每一步可靠**。规范化、符号规则、容差、超时和严格结构都可能产生误差。reward hacking 既可能是“投机让错误内容获奖”，也可能表现为优化某种输出协议而非解决原任务；需要人工观察来限定结论，不能以“可验证”三字免除审计。

## 3．阶段B：先画出 label 位置，再谈 loss

### 3.1 prompt mask 不是 attention mask

prompt token 仍是预测 response 的条件；不在其上计 loss，不意味着禁止模型看见它。**response_mask 决定哪些目标 token 贡献损失**；attention mask 决定哪些输入位置可被注意。二者功能不同，不能以同一个 mask 的名称概括全部。

分别分词 prompt 和 response 的合同使边界可追溯；若先连接字符串分词，子词边界可能合并，长度与标签归属会改变。作业明确禁止人为插 EOS／BOS／separator；不要按其他 SFT 作业习惯自动追加。

### 3.2 独立案例：移位后的边界

设原创 token 序列中的 prompt 是 `[11,12,13]`，response 是 `[21,22]`。忽略批间 padding：

| 预测位置 | 输入token | label | label是否来自response |
|---|---:|---:|---:|
| 1 | 11 | 12 | 0 |
| 2 | 12 | 13 | 0 |
| 3 | 13 | 21 | 1 |
| 4 | 21 | 22 | 1 |

**自查答案：** 首个 response token 的预测输入仍是最后一个 prompt token，所以把 input 属于 response 的位置作为 loss mask 会漏掉它。这是位置概念例子，不是 tokenizer 实现或官方测试输出。

再给一条较短序列右侧 padding，新增 label 位置的 response_mask 应为0。token ID 恰好等于某个特殊值，不足以单独判断该位置是真实 response 还是补齐；需要保留长度／来源语义。

### 3.3 三种 token 量不要混用

- **log-prob：** 在完整上下文条件下，指定 label token 的对数概率。
- **surprisal：** 该指定 token 的负 log-prob。
- **entropy：** 对该位置整个词表分布求期望的不确定性。

独立三结果分布 $(0.5,0.25,0.25)$ 中，选择第一个结果的 surprisal 是约 **0.693147 nats**；分布 entropy 是约 **1.039721 nats**。二者不同，也不是实现错误。若日志声称是 entropy，却只平均采样 token 的 surprisal，需要明确它是样本估计，不应冒充接口返回的每位置完整分布熵。

训练中先保存逐位置量，再按 response mask 解释统计分母。包括 prompt 的 entropy 曲线可能主要反映重复的提示语，而非被优化的 response 行为。

## 4．阶段C：四个开关，各自回答一个问题

### 4.1 reward 到 advantage：比较对象是谁

group 是**同一道题的多条 response**。它不是任意八条相邻训练样本，也不是八个不同 prompt。把数据打乱后再按每八条求 mean，会得到形状正确、语义错误的优势。

baseline 控制“与什么参照相比”；advantage normalizer 控制“这个组整体有多大权重”；loss reduction 控制“response／token 如何分配贡献”；importance reweighting 控制“旧采样与当前策略的差异如何处理”。这四轴必须分别登记。

例如标准 GRPO 改为 GRPO_constant 只改变 loss reduction；Dr_GRPO 在此基础上取消 std，RFT 进一步不减 baseline；作业 MaxRL 改用 group mean 作分母。把它们统称“是否归一化”会掩盖不止一个因素的变化。

### 4.2 有限样本与极限论证是两套问题

手册在背景中给 group-mean baseline 的有限组缩放；T17 则明确要求 $G\to\infty$。同组包含自身 reward，因此不能不加条件地套用动作独立 baseline 的结论。有限组中观测均值为0也不证明真实成功概率为0。

std 的实践合同是默认 torch.std 样本校正，并在分母加 epsilon。对于 $G>1$ 的全同 reward 组，中心化分子为0；epsilon 是避免0分母的数值约定，不会凭空创造探索信号。$G=1$ 的样本 std 未定义是另一种问题。不要凭“加了epsilon”宣称所有 NaN 来源已被覆盖。

这里不列出 T02 的方差解或 T17 三个难度权重。完成你自己的推导后，先标出哪些变量在期望中随机、哪些量 stop-gradient、何时取极限，再讨论它能否解释只有8条采样的真实运行。

### 4.3 sequence 与 constant：不是相差一个永恒学习率

设第 $i$ 条有效长度为 $L_i$、每 token 的标量贡献为 $u_{it}$，共 $N$ 条。两种聚合的语义是：

$$
S_i=\sum_{t=1}^{L_i}u_{it},
\qquad m_i=S_i/L_i.
$$

$$
U_{\rm seq}=\frac1N\sum_i m_i,
\qquad U_{\rm const}=\frac{\sum_i S_i}{Z}.
$$

前者每条 response 先得到同等聚合权重；后者每个 token 同样经过固定 $Z$。若长度随训练或 reward 改变，两者的相对尺度和样本权重也改变，通常不能仅用一个固定 LR 换算消除。

**独立案例：** 三条 response 的 token 标量分别是 `[2,4]`、`[1,1,3,3]`、`[−2]`。各序列均值为3、2、−2，sequence 聚合为 **1**；总和12，若固定 $Z=14$，constant 聚合为 **6/7**。这些是抽象标量，不是从任何模型取得的 loss。

**自查：** 若第二条只被 padding 到更长，结果应否改变？不应。若真实重复更多 token，则 constant 与 sequence 可能变化不同；这正是两种目标的差异，不应“修正”成同一个数。

## 5．阶段D：把一次大更新拆小，不要把算法拆错

### 5.1 三个 batch，两个时钟

- rollout batch：一次推理产生多少 responses。
- train batch：一次 optimizer update 使用多少 responses。
- microbatch：一次驻留显存的前／反向输入。

默认 on-policy：256 responses、32次微批累积、最后1次更新。默认 off-policy：同一256 responses 分32个 train batch，每个8、累积1、各更新一次。二者即使一次前向的8条完全相同，也不是同一个算法。

**独立计数案例：** 假设一次 rollout 产生30 responses。方案甲拆成6个 microbatch、最后只更新1次；方案乙拆成6个 train batch、各更新1次。甲只有1个 optimizer step，乙有6个，其中 **后5次** 面对相对于当前策略已过时的数据。这里只是计数关系，不保证两引擎数值完全一致，也不是官方实验参数。

### 5.2 尾批权重是最容易静默出错的地方

用上一节三条序列，先处理前两条、再处理最后一条：微批的 sequence 均值分别为2.5与−2。按序列数占比聚合得到

$$
(2/3)\cdot2.5+(1/3)\cdot(-2)=1.
$$

若不看大小而把两微批均值各占一半，会得到0.25。这不是浮点精度差异，而是改变了目标。固定 $Z$ 的总和则要检查全 batch 每个 token 最终是否恰好贡献一次 $1/Z$；不要又除累积步数又重复使用全局 $Z$，也不要每个微批按自己的 token 数重定义 $Z$。

官方问题中的 train step 要求在累计完成后 clip norm、更新一次、清梯度；在每个微批先裁剪再相加通常不同于对总梯度裁剪。日志也应明确是总梯度裁剪前 norm，而非最后一微批 norm。

### 5.3 零 advantage 剪枝：可省计算，不能改分母

T20 要求不把零 advantage 序列送进训练模型，但必须保持原数学对象。先在原始组上确定 advantage，再谈剪枝；不能删除错误样本之后重新计算 group mean。

**独立案例：** 五条序列的已聚合贡献为 `[3,0,7,0,0]`，固定 $Z=20$。全部计算与只保留非零贡献都应得到 **0.5**；改用存活序列数2作分母会得到5，已经不是同一目标。若 sequence 平均模式去掉零项，也必须保留原序列总数的权重含义。

**全零 batch 的问题不是一句“跳过就好”。** 本批梯度可能为零，但 AdamW 的历史动量／权重衰减、step 计数、清梯度、日志和调度器是否前进，是不同状态问题。应先写清你要等价于哪一个未剪枝过程，再检查对应状态；不要把节约算力当作无条件改变更新次数的许可。

## 6．阶段E：old policy 必须可追溯

### 6.1 同一行 token，分子分母必须同义

令 $\ell_t$ 为当前 log-prob，$\ell^0_t$ 为行为策略 log-prob，则 token ratio 由二者差值决定：

$$
\Delta_t=\ell_t-\ell^0_t,
\qquad w_t=e^{\Delta_t}.
$$

三项都应针对**同一 token、同一 prefix、同一 label 移位、同一 response 区域**。把 generation 输出的另一种分词结果同 teacher-forced 张量错配，常表现为 ratio 无故极端；这时不能只缩小 cliprange 处理症状。

推荐保存逻辑上的 rollout-policy 版本、样本顺序与 old-score 版本，便于追溯；不是要求额外创建一个 DPO reference 模型。更新后将 old scores 重算为 current scores 会让 ratio 接近1，但那是抹去 stale 信息，不是证明训练稳定。

### 6.2 noclip 不等于 naive；token ratio 不等于完整纠偏

naive 继续拿旧数据配当前分数、不做 importance 权重；noclip 使用逐 token ratio、没有 clipping。完整 sequence 比值是 token ratios 的乘积；它可以把轨迹分布作整体变换，但长度增加容易导致方差爆炸。

token reweighting 只校正一个条件概率，其他位置仍依赖旧采样策略。即便无 clipping，它也不自动变成当前策略期望奖励的无偏估计。GSPO 对完整乘积取长度次方根，缓和量级，却引入新的偏差。不能在报告中把任意“用了 ratio”统称为“纠正所有 off-policy 偏差”。

T22 要求学生独立推导 pairwise surrogate；本页不写其解。可用概念问题自审：你所写 surrogate 的每个时间位置到底由谁采样？如果答案只有“旧／新模型都参与”，描述还不够精确。

### 6.3 PPO clipping 具有 advantage 符号方向

固定目标比较“未经截断的优势加权 ratio”和“截断后的优势加权 ratio”，取较保守的一支。因此正 advantage 过度上调被限制，负 advantage 过度下调被限制；不能用不带符号分析的“所有越界 ratio 都不传梯度”解释。

**独立案例：** $\epsilon=0.2$，优势绝对值0.7：

| advantage | ratio | 未clip乘积 | 保守目标值 |
|---:|---:|---:|---:|
| +0.7 | 1.4 | 0.98 | 0.84 |
| −0.7 | 0.6 | −0.42 | −0.56 |
| +0.7 | 0.6 | 0.42 | 0.42 |
| −0.7 | 1.4 | −0.98 | −0.98 |

表中是上升目标；交给下降 optimizer 的 loss 符号相反。后两行虽然 ratio 在区间外，保守目标仍选未截断一支。故 **ratio 越界比例与实际被剪去目标梯度的比例不同**。本例不处在边界，避免借自动微分在 min／clip 折点的约定作额外结论。

clipping 是 surrogate 的局部机制，不是严格保证所有 token ratio、KL 或参数变化都被硬限制在边界内。共享参数的一次更新仍会改变其他 token；clip fraction 低也不单独证明稳定。

### 6.4 GSPO 的长度进入了权重和梯度

只在 response 有效 token 上定义

$$
\bar\Delta=\frac{1}{L}\sum_{t=1}^{L}\Delta_t,
\qquad s=e^{\bar\Delta}.
$$

这就是几何平均 ratio。 **独立案例：** 两个有效 token ratios 为1.44与0.64：乘积0.9216、几何平均 **0.96**、算术平均1.04。若 padding 位置随便放了一个 ratio=100，只要 mask 正确，它不应改变0.96。

GSPO 的同序列共享权重经过链式法则本身带有长度因子。若你把“一个 sequence loss”扩展成重复的 token tensor，再由既有 sequence reducer 合并，应能说明最后仍是手册 p36 的目标；重复多除一次长度会额外压低长 response。optional constant-GSPO 需要重新检查指数和 reduction 的组合，而不只是改一个字符串参数。

标准 token clipping 默认0.2与 GSPO 默认0.0003作用于不同统计量，不能把数值差解释为“GSPO严格了约667倍”。报告 clip fraction 时同时交代 mask、token／sequence 分母、优势符号与具体计数定义。

## 7．阶段F：把比较做成可以反驳的实验

### 7.1 先确定比较轴，再看曲线

同样200 rollout steps 的 on-policy 与 off-policy，optimizer steps 不同；同样 wall time，可能生成 tokens 不同；同样 responses 数，prompt 长度／response 长度也可能不同。若目标是速度，至少同时记录时间与达到的 reward；若目标是 sample efficiency，记录生成预算，不能只画 optimizer step 后宣称更省样本。

不要把 “B200 hrs” 题目估时当本站实测。双 GPU 的壁钟时间与 GPU-hours 也不是同一个单位。由剪枝省下的训练前向，不等于省下已经完成的 rollout 生成。

### 7.2 四 seed 是比较的起点，不是置信魔法

T10 标准实验、T21 四种 on-policy、T27 四种 off-policy 都明确**每个方法四 seeds**；T11 根据已观测方差决定次数，T12 要 few seeds，T28 要 multiple seeds。报告不能把这五种要求统一缩成“一次跑通”，也不能捏造未规定的具体 seed 编号。

图至少展示均值与跨运行散布；有发散 seed 不应静默删除。手册给的1.96倍标准误区间是近似展示选择，四次运行很难充分刻画重尾或多模态 RL 轨迹。配对同一组 seed 可以帮助比较，但 GPU 非确定性意味着同 seed 不保证两运行完全同一随机过程；保存真实运行标识比声称“严格复现”重要。

若用 baseline 调好的 LR 直接评价候选，结论是**这个调参预算与配置下的表现**。候选落后不证明充分调参后仍落后；候选领先也不能抹去多重尝试／选择最好方案带来的偏差。T28 要有只差一个因素的已做方法作为直接对照，具体新 estimator 必须由你提出。

### 7.3 独立案例：为什么不能只留均值

两组原创假想统计值分别为 `[0.20,0.24,0.28,0.32]` 与 `[0.25,0.26,0.26,0.27]`，均值都为 **0.26**；样本方差分别约 **0.002666667** 与 **0.000066667**。只报告均值无法表达稳定性差异。这是人工构造的统计教学数据，**不是任何 A5 seed 的 accuracy**，不作达成25%门槛的证据。

### 7.4 validation 就叫 validation

原题允许将 `test.jsonl` 用作验证。反复查看并据此选 LR／prompt／estimator 后，它已经参与模型选择。保留文件名，但报告用途叫 validation；不要写“从未参与决策的 test accuracy”。若另外做独立评测，也要区分与作业规定指标，但本站不扩展任务或索取额外数据。

最终25%门槛针对标准实验的**最终验证 accuracy 跨 seed 均值**。不允许换成单 seed 最大值、训练 reward、pass@8 或挑选的中间 checkpoint。没有运行时，诚实状态只能是“未验证达到”，不是用讲义预期代替结果。

## 8．常见现象：先找能区分解释的证据

| 现象 | 先问什么 | 尚不能推出什么 |
|---|---|---|
| reward 长期为0 | 真值是否只取最终答案？格式门／停止串／截断是否匹配？各组有无不同reward？ | 不能立即断言LR太小 |
| loss接近0但参数在变 | 正负项是否抵消？loss是surrogate还是实数目标？optimizer是否有状态？ | loss值小不等于梯度小 |
| entropy掉得很快 | 只算response吗？是否用surprisal冒充entropy？reward／长度／重复是否同步变化？ | 不等于推理能力增强 |
| 增加累积步数就变轨迹 | 总batch是否保持？尾批权重／constant是否重复缩放？裁剪位置是否变化？ | 不应归因于“GRPO天生随机”而不检查 |
| 剪枝后效果剧变 | group是否在剪枝前确定？分母／日志总体是否保持？全零批状态如何处理？ | 不等于稀疏计算本身更好 |
| ratio一开始已极端 | 两引擎权重、token、prefix、温度、old-score版本是否一致？ | 不能仅用更小clip掩盖对齐错误 |
| 所有ratio总是1 | old分母是否被current不断刷新？更新是否真实发生？ | 不能直接宣布完全on-policy |
| GSPO平均ratio合理但坏样本被吞没 | 几何平均是否掩盖不同位置的正负log-ratio？统计是否含padding？ | 均值接近1不保证逐token接近 |
| 一个算法四次中一次很高 | 是否展示全部运行／发散？比较预算与调参是否对称？ | 最好seed不代表平均提升 |

这些是概念性排错问题，不是针对学生代码的自动修复。官方 `AGENTS.md` 要求学习者独立实现；若需要帮助，携带自己观察到的 shape、边界、数学预期与误差，而不是请求代理写完整循环。

## 9．回到交付：什么证据允许什么结论

1. **静态读源码**只允许说“接口／实现这样规定”，不允许说“已运行通过”。
2. **独立数学算例**只验证概念关系，不能替代官方测试或实际模型训练。
3. **单步测试通过**不验证 vLLM 权重同步、题库划分、parser、长程稳定性与多 seed 对照。
4. **训练 reward 上升**不自动证明验证提升；验证提升也只针对给定 verifier／模型／数据和预算。
5. **完整实验报告**需要真实配置、曲线、方差、失败和观察，不是从论文复制预期趋势。

书面数学题请自行完成 T02、T17、T22；思考题自行形成论证；T28 方案自行提出。本页刻意不提供这些提交用答案。完整正式题设、评分、比较与所有未编号要求回到实验说明逐项核对。

## 来源与非执行声明

- [固定39页讲义](https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/c2734a26308710949fe13226960a1e8cece94b7e/cs336_spring2026_assignment5_alignment.pdf)：§3奖励、§4训练、§5算法开关、§6off-policy、§7对照要求。
- [固定 grader](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/cs336_alignment/drgrpo_grader.py)、[vLLM helper](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/cs336_alignment/vllm_utils.py)、[adapters／tests](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e/tests)：接口和真实源码边界，均仅静态阅读。
- [固定 AI policy 文件](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/AGENTS.md)：允许概念／API帮助，禁止代做代码和计分答案。

原讲义没有已核实的整体全文翻译授权；本站不以 grader 的 Apache-2.0 或模型／数据许可覆盖讲义。所有算例与图为原创概念材料，未调用官方作业函数、reward服务、模型、GPU、Modal或付费接口。原文、渲染图、哈希和范围保留在 sources，不作为正文镜像发布。
