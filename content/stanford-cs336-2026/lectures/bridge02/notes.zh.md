---
title: "概率与语言建模：从条件概率走到困惑度"
lectureId: bridge02
kind: "编者先修桥接；非 Stanford 官方讲次"
before: lec01
sourceVersion: "CS336 L01 de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e；A1 a158843b20107949f1a8d7df1b05cd33b9166712，Spring 2026 / 26.0.3"
status: "独立概率算术片段已在 Python 3.11.8 执行；不提供 A1 损失函数实现。"
---

# 概率与语言建模：从条件概率走到困惑度

## 学习门槛与出口

需要会分数、求和、乘积，以及 $\ln(ab)=\ln a+\ln b$、$\exp(\ln a)=a$。不要求已经学过 Transformer。

本文解决一个问题：**给定一段已经切成 token 的文本，怎样把模型对每个真实后继 token 的判断汇总成一个有明确定义的分数？** 学完应能区分概率、负对数似然、交叉熵与困惑度，并知道什么时候两个分数根本不能直接比较。

## 1. 条件概率先规定“已经知道什么”

对事件 $A,B$，若 $P(B)>0$，

$$
P(A\mid B)=\frac{P(A\cap B)}{P(B)}.
$$

例如十个样本中有四个满足 $B$，其中三个同时满足 $A$，则 $P(A\mid B)=3/4$，不是 $3/10$。分母变成了“已知满足 $B$ 的样本”。

语言模型里的条件是已见前缀。设词表为 $V$，前缀为 $h$，模型输出 $p_\theta(v\mid h)$，要求

$$
p_\theta(v\mid h)\geq 0,\qquad
\sum_{v\in V}p_\theta(v\mid h)=1.
$$

归一化是对**同一个前缀下所有候选 token**求和，不是把不同位置的真实 token 概率加到 1。原始分数 logits 还不是概率；这里只讨论已经得到的合法概率，不展开 logits 到损失的作业实现。

## 2. 链式分解不需要独立性假设

由条件概率定义，$P(A\cap B)=P(B)P(A\mid B)$。反复应用就得到序列链式法则：

$$
p_\theta(x_{1:T}\mid c)
=\prod_{t=1}^{T}p_\theta(x_t\mid c,x_{<t}).
$$

$c$ 是固定的起始上下文；没有外部上下文时，可省略 $c$，第一项就是 $p_\theta(x_1)$。公式在有关前缀概率为正时直接由定义得到；模型通常直接规定各前缀的条件分布。

- **精确恒等式：** 每一步保留完整过去，不是在假设 token 彼此独立。
- **另加的近似：** 如果只保留最近几个 token，这是上下文截断或建模限制，不是链式法则本身。
- **计分边界：** 若要给“以此处结束的完整文本”计分，通常还要明确结束符如何处理；给定长度的一段序列与包含终止事件的文本不是同一个计分对象。

自拟三步例子，表格只列真实 token 对应的概率，其余词表概率未展开：

| 位置 | 已知上下文 | 真实 token 的条件概率 |
| --- | --- | --- |
| 1 | 起始上下文 $c$ | $1/2$ |
| 2 | $c,x_1$ | $1/4$ |
| 3 | $c,x_1,x_2$ | $4/5$ |

这条序列的条件概率为 $\frac12\cdot\frac14\cdot\frac45=\frac1{10}$。逐步概率可以上升或下降；新增的乘法因子不会大于 1，所以某个前缀再延长后的联合概率不会增大。

## 3. 负对数似然：把乘积变成可加的代价

真实 token 概率越高越好。取负自然对数后，定义每个被计分位置的损失

$$
\ell_t=-\ln p_\theta(x_t\mid c,x_{<t}).
$$

于是总负对数似然（negative log-likelihood，NLL）与平均损失分别为

$$
\mathrm{NLL}=\sum_{t=1}^{N}\ell_t,
\qquad
\bar\ell=\frac{\mathrm{NLL}}{N}.
$$

这里 $N>0$ 是**实际参与计分的目标 token 数**，不是字节数，也不是无条件等于存储张量元素数。提示前缀、填充位置、特殊符号是否计分，都必须由评估规则明确。

三步例子的各项损失为 $\ln2,\ln4,\ln(5/4)$，因此

$$
\begin{aligned}
\mathrm{NLL}&=\ln10\approx2.302585,\\
\bar\ell&=\frac{\ln10}{3}\\
&\approx0.767528\ \text{nats/token}.
\end{aligned}
$$

总 NLL 通常随计分长度增加，因此比较不同长度文本时，不能只看“谁的总损失小”。概率为 1 时损失为 0；真实事件被赋予概率 0 时，数学损失为 $+\infty$，不是“忽略这一项”。

## 4. 交叉熵为什么会等于这里的 NLL？

对同一候选集合上的目标分布 $q$ 和预测分布 $p$，交叉熵定义为

$$
H(q,p)=-\sum_{v\in V}q(v)\ln p(v).
$$

若这个位置观察到的真实 token 是 $y$，用 one-hot 目标 $q(y)=1$、其余为 0，就只剩

$$
H(q,p)=-\ln p(y).
$$

所以每个位置的 one-hot 交叉熵就是该次观察的 NLL；再对被计分位置平均，就得到平均 token 交叉熵。**目标分布和预测分布是两件事**：不是对模型自己的概率取平均，也不是只取概率最大的那个类别。

用一个不涉及模型训练的分布例子区分它们：若 $q=(3/4,1/4)$、$p=(1/2,1/2)$，则 $H(q,p)=\ln2$。若预测改成 $p=q$，则交叉熵为

$$
H(q,q)=-\frac34\ln\frac34-\frac14\ln\frac14
\approx0.562335.
$$

$H(q,q)$ 是目标分布自身的熵。语言模型实际损失则是在**各自前缀对应的分布**上计分；不能先统计全语料 token 频率，再把它当成所有前缀共同的目标分布来替代条件损失。

## 5. 困惑度：几何平均意义上的“等效选择数”

使用自然对数时，困惑度（perplexity，PPL）定义为

$$
\begin{aligned}
\mathrm{PPL}&=\exp(\bar\ell)\\
&=\left(\prod_{t=1}^{N}\frac1{p_t}\right)^{1/N},\\
p_t&=p_\theta(x_t\mid c,x_{<t}).
\end{aligned}
$$

若每一步都在 $K$ 个候选中均匀分配概率，则真实 token 的概率为 $1/K$，平均损失为 $\ln K$，PPL 为 $K$。这是“等效选择数”的直觉，**不是说一般模型每一步真的列出了 PPL 个候选**，也不意味着 PPL 必须为整数。

三步例子得到 $\mathrm{PPL}=10^{1/3}\approx2.154435$。它是**真实 token 概率的几何平均的倒数**，不是概率算术平均的倒数，也不是每个位置倒数的算术平均。

仅核对定义的独立算术片段；概率直接给定，不处理 logits、张量或官方适配器：

```python
import math

probabilities = [0.5, 0.25, 0.8]
nll = sum(-math.log(p) for p in probabilities)
mean_nll = nll / len(probabilities)
print(f"{nll:.6f} {mean_nll:.6f} {math.exp(mean_nll):.6f}")
```

执行输出为 `2.302585 0.767528 2.154435`，与上述解析值一致。

### 合并批次时先合并分子、分母

一批有 $N_1$ 个有效 token、平均损失 $L_1$，另一批有 $N_2$ 个、平均损失 $L_2$，全体平均损失应为

$$
L=\frac{N_1L_1+N_2L_2}{N_1+N_2},
\qquad \mathrm{PPL}=\exp(L).
$$

除非有效 token 数相同，否则“两个 batch loss 直接平均”就是另一种权重。更不能先把各批 PPL 算出来，再取算术平均。对数若用以 2 为底的版本，损失单位变成 bits/token，反变换必须用 $2^L$，不能再用 $\exp(L)$。

## 6. Tokenization 不同，PPL 不能直接排大小

想象同一段原始文本 `ab`，采用两种确定的切分，忽略其他计分边界差异：

| 切分 | 对规范 token 序列给出的概率 | 计分 token 数 | PPL |
| --- | --- | --- | --- |
| `[a, b]` | $0.5\times0.5=0.25$ | 2 | 2 |
| `[ab]` | $0.25$ | 1 | 4 |

即使两边给这段文本的规范编码序列分配了相同概率，PPL 仍不同，因为平均的单位不同。不能据此断言第一种模型“预测能力好一倍”。本例比较的是固定编码路径上的分数，不是在求所有可能 token 路径的概率和。

若要跨切分讨论，可考虑把总负对数概率按同一原始文本的字节数 $M$ 归一化，例如

$$
\mathrm{bits/byte}=\frac{\mathrm{NLL}}{M\ln2}.
$$

上例原始 UTF-8 文本有两个字节，两边均为 1 bit/byte。但这个换算**不是公平比较的万能补丁**：还必须固定原始文本、文本规范化、起始上下文、上下文窗口策略、文档边界、结束符与计分范围。若 tokenizer 丢弃信息或把不同文本合成同一个未知符号，分数的对象也变了。

## 7. 自测：先写出分母，再算数

<details>
<summary>自测 1：把每一步都当作独立事件，链式分解还精确吗？</summary>

完整链式分解本来不需要独立性。把 $p(x_t\mid x_{<t})$ 换成 $p(x_t)$ 才额外加入独立性假设；一般语言序列不满足它。例如前一个 token 改变时，后继分布可能大幅改变。

</details>

<details>
<summary>自测 2：两步真实 token 概率为 1/4、1/4，平均 NLL 和 PPL 是多少？</summary>

总 NLL 是 $2\ln4$，平均 NLL 是 $\ln4\approx1.386294$，PPL 是 4。联合概率是 $1/16$，但 PPL 不是联合概率的简单倒数 16，而是其倒数的二次方根。

</details>

<details>
<summary>自测 3：两 token 的批次平均损失为 ln 2，一 token 的批次为 ln 8，合并后的 PPL 呢？</summary>

平均损失是 $(2\ln2+\ln8)/3=5\ln2/3$，PPL 是 $2^{5/3}\approx3.174802$。若不按 token 数加权，得到的平均损失是 $\ln4$，PPL 为 4；若直接平均两批 PPL，又会错误地得到 5。

</details>

<details>
<summary>自测 4：模型甲 PPL=10，模型乙 PPL=12，足以宣布甲更好吗？</summary>

不足。至少核对评估语料、tokenizer/词表、计分 token 集合、上下文和边界处理是否相同。条件一致时，较低 PPL 表明对这一计分目标的平均 NLL 较低；它仍不是所有下游能力、事实正确性或生成质量的完整排序。

</details>

## 回到课程

回到 [L01：tokenization 与语言建模对象](#/c/stanford-cs336-2026/lec/lec01?v=notes)，把“词表、切分长度、模型概率”视作共同决定计分单位的约定。本文只建立概率语义，不提供可提交的 A1 交叉熵实现。

## 来源与处理范围

- Stanford CS336 [L01 固定讲义](https://github.com/stanford-cs336/lectures/blob/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e/lecture_01.py#L579-L673)：实际阅读 token 序列的概率对象、编码往返、字节/token 长度等段落。固定版晚于学期；没有拿它当作录像逐字内容。讲义开放翻译许可未确认。
- CS336 Staff，[A1 固定讲义](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)，**Spring 2026 / 26.0.3，§4.1，印刷页 28–29，式 (16)–(18)**：实际阅读本地文本提取的交叉熵、one-hot 解释、PPL 及相邻任务约束；未将它升级为整份讲义已读或已完成作业。第一方文档适用 [MIT](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/LICENSE)，不外推第三方材料。
- 条件概率推导、三步小数值、跨切分反例与自测均为编者自拟，用来解释上述定义；不是官方指定的额外阅读，也不是课堂译稿。未处理录像、未截帧、未核音。
- 逐源版本、SHA-256、获取时间、实际阅读范围及本页归属见 `sources/p2-bridge-foundations/manifest-fragment.json`。
