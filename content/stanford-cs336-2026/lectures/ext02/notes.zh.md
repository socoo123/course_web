---
title: "优化器与训练动态：把历史、步长和预算分开"
lectureId: ext02
kind: "编者专题，非官方讲次"
sourceVersion: "A1 Spring 2026 v26.0.3 @ a158843b20107949f1a8d7df1b05cd33b9166712；Attention 1706.03762v7；PyTorch 2.9 文档快照"
sourceManifest: "sources/p3-extensions/manifest-fragment.json"
readingScope: "按页底限定范围阅读固定作业、论文和官方API；没有新增Adam/AdamW论文精读。"
license: "自主教学与概念解释，不是来源全文翻译；A1第一方文档MIT，第三方材料权利另计。"
status: "独立CPU预算算术微例；不是优化器或官方作业实现，不代表训练、GPU性能或课程实验验收。"
mediaStatus: "无独立官方录像，仅notes，不制作draft或materials。"
---

# 优化器与训练动态：把历史、步长和预算分开

## 1. 梯度相同，下一步也可能不同

两个训练过程具有相同参数、相同当前梯度，AdamW仍可能给出不同更新：它们之前看过的数据不同，保存的梯度统计也不同。**优化器不是只接收当前梯度的无记忆函数，而是训练状态的一部分。**

本页回答三个问题：状态如何改变更新、学习率按哪只时钟变化、怎样比较两条训练曲线。反向传播见[bridge03](#/c/stanford-cs336-2026/lec/bridge03?v=notes)，数据到损失到更新的完整闭环见[bridge06](#/c/stanford-cs336-2026/lec/bridge06?v=notes)；浮点表示与资源字节账分别回到[bridge07](#/c/stanford-cs336-2026/lec/bridge07?v=notes)、[bridge08](#/c/stanford-cs336-2026/lec/bridge08?v=notes)。这里不重讲它们，也不提供优化器、调度器或官方实验实现。

## 2. 从SGD到momentum：先约定状态的单位

令 $g_t$ 是在参数 $\theta_{t-1}$ 上计算的当前批均值梯度，$\eta_t$ 是第 $t$ 次更新的学习率，$t$ 从1开始。普通SGD没有额外逐参数历史：

$$
\theta_t=\theta_{t-1}-\eta_t g_t.
$$

“stochastic”来自批抽样，不是说更新公式还要额外加一次随机数。全批梯度也能代入同一形式。

本文用无dampening、无Nesterov的momentum约定：

$$
\begin{aligned}
b_0&=0,\\
b_t&=\mu b_{t-1}+g_t,\\
\theta_t&=\theta_{t-1}-\eta_t b_t.
\end{aligned}
$$

$b_t$保存带衰减的梯度和，**不是参数位移**。连续同向的梯度会累积，频繁反向的梯度可能抵消；这既可能减轻抖动，也可能在目标方向改变时造成滞后。不能说“加动量必然更稳定”。

另一个常见写法是指数移动平均 $u_t=\mu u_{t-1}+(1-\mu)g_t$。在相同零初始化下，$u_t=(1-\mu)b_t$；若直接沿用相同学习率，它们的更新量不同。还有把学习率乘进历史状态的写法：学习率随时间改变时，旧梯度携带的是旧学习率，不能再简单视为本文写法的别名。PyTorch文档专门提示了这种差别；本页不是要为所有框架规定同一种“动量”。

### 记忆长度是“步”，不是“token”

距今 $k$ 步的梯度对指数平均的权重与 $\beta^k$ 成正比。常用数量级 $1/(1-\beta)$ 是记忆尺度，不是硬截断窗口：$\beta=0.9,0.99,0.999$ 分别约对应10、100、1000次更新。更精确的半衰期满足 $\beta^h=1/2$。

同样的 $\beta$、每步多看4倍token，就意味着历史覆盖的token尺度也约大4倍。只改batch而声称“优化器动态完全不变”，遗漏了这只时钟。

## 3. AdamW：两个状态分别在记什么

先单独看Adam的两个逐坐标统计，乘方与除法均逐元素进行：

$$
\begin{aligned}
m_t&=\beta_1m_{t-1}+(1-\beta_1)g_t,\\
v_t&=\beta_2v_{t-1}+(1-\beta_2)g_t^2,\\
m_0&=v_0=0.
\end{aligned}
$$

- $m_t$记方向和符号，是梯度的一阶原始矩。
- $v_t$记梯度平方的尺度，是二阶原始矩；**不是已减去均值平方的方差**。
- 两者都与参数同形；再加计步状态。状态dtype和实际字节量需另外声明，不能从算法名字推出固定显存占用。

### 3.1 偏差校正纠正的是零初始化

若为了分析暂时假定梯度的一阶矩恒为 $\bar g$，则：

$$
\begin{aligned}
\mathbb E[m_t]
&=(1-\beta_1)\sum_{i=1}^t\beta_1^{t-i}\bar g\\
&=(1-\beta_1^t)\bar g.
\end{aligned}
$$

于是使用：

$$
\hat m_t=\frac{m_t}{1-\beta_1^t},\qquad
\hat v_t=\frac{v_t}{1-\beta_2^t}.
$$

它移除了这个平稳矩假设下的零起点偏差，**不会消除梯度噪声，也不保证跟上非平稳训练中的最新尺度**。$t=0$会让校正分母为0，所以状态计数和调度器从0还是从1开始，必须分开说明。

**独立手算，不是作业答案。** 给第一步梯度 $g_1=2$，取 $\beta_1=0.5,\beta_2=0.75$，则 $m_1=1,v_1=1$；校正后 $\hat m_1=2,\hat v_1=4$。忽略epsilon时，归一化方向是1，不是原始梯度2。这说明“梯度大两倍，所以Adam更新必大两倍”并不成立。后续若梯度改变，不能把这个第一步结论推广成每步固定长度。

### 3.2 epsilon不是装饰项，也不是机器精度

以下先采用PyTorch文档所示的**校正矩约定**，用它定义自适应方向：

$$
a_t=\frac{\hat m_t}{\sqrt{\hat v_t}+\varepsilon}.
$$

这里 $\varepsilon$ 与梯度尺度同单位，不等于 `finfo.eps`，更不等于“把所有NaN修好”。当 $\sqrt{\hat v_t}\gg\varepsilon$ 时它影响较小；当分母尺度接近或小于它时，更新明显被抑制。把它挪进平方根会改变量纲和行为。

若整个梯度序列乘正数 $c$，忽略epsilon时，分子乘 $c$、平方根分母也乘 $c$，二者可抵消；保留epsilon则相当于改变了 $\varepsilon/c$。因此把loss从均值改成求和，不是一个永远能由Adam自动抵消的无害改动；数值范围、裁剪和衰减的相对作用也会变。

**A1的确切约定要另看。** 固定v26.0.3把偏差校正折入步长，分母使用未校正的 $\sqrt{v_t}+\varepsilon_A$。换写成校正矩形式，其有效epsilon是：

$$
\varepsilon_{\rm effective}(t)
=\frac{\varepsilon_A}{\sqrt{1-\beta_2^t}}.
$$

所以两种写法使用**相同数值**的epsilon时并不严格等价。它们在epsilon可忽略的范围可能很接近，但不能因此替换作业规范或断言逐项相同。本文只比较数学约定，不给该作业的优化器实现。

## 4. decoupled decay：不要把参数收缩塞进历史梯度

若对目标加 $\lambda\|\theta\|^2/2$，梯度会增加 $\lambda\theta$。普通无动量SGD中，这与同一步先收缩旧参数、再减去数据梯度等价；但在自适应优化器里，新增项会进入 $m,v$，随后被历史尺度重加权，不再等于统一比例的参数收缩。

AdamW将这件事分开。沿用上节自适应方向 $a_t$，可写为：

$$
\begin{aligned}
\theta_t
&=(1-\eta_t\lambda)\theta_{t-1}\\
&\quad-\eta_t a_t.
\end{aligned}
$$

“解耦”表示衰减项不混入数据梯度的矩估计，**不是说衰减与学习率完全无关**。如果梯度贡献始终为0且状态也为0，纯衰减给出：

$$
\theta_T=\theta_0\prod_{t=1}^{T}(1-\eta_t\lambda).
$$

在 $0\le\eta_t\lambda\ll1$ 时，乘积约为 $\exp(-\lambda\sum_t\eta_t)$。同一个 $\lambda$，更新次数和学习率曲线不同，累计收缩也不同。更不能把任意大的 $\eta_t\lambda$ 仍称为温和收缩。

另外，先对旧参数衰减与先做梯度更新、再把整个结果衰减并不相同；后者还会缩小刚刚的梯度位移。固定A1 v26.0.3先对旧参数做decay。报告中还应说明哪些参数组参与衰减；不能偷偷改变bias或归一化参数的规则，再把结果差异归给优化器名称。

## 5. warmup和调度：先画横轴，再讨论形状

warmup是在训练初期逐渐增加学习率，避免用最终大步长直接作用于尚未适应的数据尺度、参数和历史统计。它是训练配方中的控制手段，**不是偏差校正的替代品，也不能修复错误标签、掩码或非有限输入**。存在warmup需求不等于已经识别其唯一成因。

| 调度形状 | 应检查的含义 | 不应作的推断 |
| --- | --- | --- |
| 常数 | 整个预算用同一标量步长 | Adam逐坐标实际位移因此恒定 |
| warmup后反平方根 | 随更新次数渐进下降，没有有限终点自然落到底 | 直接等同余弦调度 |
| warmup后余弦 | 预先声明衰减区间与最终学习率 | 提前停跑也相当于完成了原预算 |

Attention论文§5.3使用Adam、线性warmup后反平方根衰减；固定A1 §4.4则规定warmup后余弦及区间结束后的最小学习率。它们不是同一实验配方。论文原方案的解释统一见[L03材料精读](#/c/stanford-cs336-2026/lec/lec03?v=materials)。

### 三只不能混用的时钟

1. **microbatch次数**：做过多少次局部前后向。
2. **优化器更新次数 $t$**：参数和矩状态真正更新过多少次。
3. **累计有效训练token $U_t$**：参与目标且按约定计数的token次数。

梯度累积8次后更新一次，不是给moment状态和步调度器推进8次。若某步因非有限梯度未更新，也要明确调度是否推进，不能默默把“尝试步数”当成“成功更新数”。变长序列应记录每步有效token数，不能用张量槽位数替代。

对按token比较的实验，可用归一化进度 $r=U/U_{\rm budget}$描述warmup和衰减完成比例；这是比较协议，不是擅自改写官方A1以iteration定义的接口。实际更新前后的学习率、计步索引和端点值必须能从日志对应起来。

## 6. batch公平比较：同step不等于同训练量

若每步包含 $B$ 条长度 $S$ 的序列，全部 $S$ 个预测目标都有效，经过 $K$ 次更新，则：

$$
\begin{aligned}
U&=KBS,\\
U&=\sum_{t=1}^{K}n_t\quad\text{（变长情形）}.
\end{aligned}
$$

这里的 $B$ 是累积后的有效batch；padding、被排除标签或跨边界目标要按真实loss契约扣除。重复看到同一个token也再次计入训练量；去重数据量是另一个字段。

**编者预算例。** 长度128、每条128个有效目标：batch8更新1000次，处理1,024,000个token；batch32只需250次更新就达到同样token量。若仍跑1000步，后者看了4倍数据。若两边warmup都为100步，它们在warmup里处理的token量也相差4倍。

```python
# 只做CPU整数预算算术；不是训练、调度器或优化器实现。
length = 128
budget = 8 * length * 1000
for batch in (8, 32):
    tokens_per_update = batch * length
    updates = budget // tokens_per_update
    print(batch, tokens_per_update, updates, 100 * tokens_per_update)
```

解析预期为 `8 1024 1000 102400` 与 `32 4096 250 409600`。本例不需要PyTorch、GPU或数据下载。

公平不是只有一种定义，至少区分：

- **固定token预算**：研究统计效率；更新次数可以不同，调度进度应有可比较解释。
- **固定估算计算量**：模型或序列长度改变时，仅相同token不够。长序列attention的额外成本也要计入，不能机械套 $6ND$。
- **固定墙钟预算**：研究给定硬件上的实际收益；允许处理token数不同，但要同时报告它。
- **固定调参预算**：每个候选有相当的搜索机会，比较多次seed与验证指标，不能只给一方精调再宣布另一方失败。

增大batch会改变梯度噪声、更新频率、状态记忆的token跨度与硬件效率。独立同分布假设下均值噪声方差可随样本数下降，但语言token彼此相关；“batch翻倍，学习率必翻倍”不是普遍定律。若改变batch，重新评估学习率、warmup和验证表现，比套固定缩放口诀更可靠。

## 7. 用可区分原因的日志，而不是只看loss

下面的数值和现象是**诊断情境，不是本机实测**。梯度是否正确及裁剪细节见[ext01](#/c/stanford-cs336-2026/lec/ext01?v=notes)；本页关心梯度如何被历史状态转换为位移。

| 观察 | 优先核对 | 一个能区分原因的比较 |
| --- | --- | --- |
| 梯度有限且量级接近，warmup末端loss突跳 | 实际学习率、更新量、端点计数、当批数据 | 在相同输入与相同状态下，只改变峰值学习率；不要同时换batch |
| 梯度已变号，参数短时仍沿原方向走 | $m_t$与当前梯度的符号、$\beta_1$历史 | 对照当前方向与历史方向，先判断惯性而非直接断言反向错误 |
| 梯度尖峰后很久更新偏小 | 尖峰是否抬高 $v_t$、$\beta_2$记忆时间 | 看平方梯度尺度及实际位移恢复过程；一次尖峰不证明永久停训 |
| 恢复检查点后曲线突然变样 | 矩、计数、学习率、调度、数据位置是否恢复 | 不只比较权重；重新初始化状态是一次新的优化轨迹 |
| batch更大时按step曲线更好 | 累计有效token、调参预算和验证集 | 先重画同token横轴，再比较同墙钟；两种结论可能不同 |

可按参数组记录 $\|g_t\|$、$\|m_t\|$、$\sqrt{v_t}$的分位数、学习率和真实 $\|\Delta\theta_t\|$。一个量级提示是：

$$
\rho_t=\frac{\|\Delta\theta_t\|}{\|\theta_{t-1}\|}.
$$

只有参数范数非零时才这样解释；近零参数另报绝对位移。不同层尺度不宜混成一个全局比率，“合适的更新比”也没有通用阈值。若同时含decay，要分清总体位移与数据驱动位移，避免把正常收缩误读成梯度变大。

## 8. 自测

<details>
<summary>1. 当前参数和当前梯度都相同，为什么恢复时遗漏优化器状态仍会改变下一步？</summary>

momentum依赖历史梯度，AdamW依赖一、二阶矩和计数。遗漏它们会改变方向、逐坐标尺度及偏差校正；只恢复参数不是恢复同一训练状态。

</details>

<details>
<summary>2. 偏差校正已经把第一步的矩校正回来，为什么还可能需要warmup？</summary>

偏差校正针对零初始化的统计偏差；warmup控制实际步长轨迹。非平稳梯度、模型敏感性等不会由那两个校正分母自动消失。

</details>

<details>
<summary>3. Adam的v是方差吗？epsilon能随意从根号外搬到里面吗？</summary>

$v$是未中心化的二阶矩，不是方差。根号外epsilon和梯度同尺度，根号内则须与梯度平方同尺度；相同数字移位会改变算法。把偏差校正移到学习率时也须追踪epsilon的变换。

</details>

<details>
<summary>4. AdamW的decay已与梯度解耦，为什么相同lambda、不同调度仍可能收缩不同？</summary>

每步的收缩因子为 $1-\eta_t\lambda$；累计效果是这些因子的乘积。解耦指不进入矩估计，不指脱离学习率和更新次数。

</details>

<details>
<summary>5. batch增大4倍、总token不变，哪些东西不能同时保持原值并声称动态等价？</summary>

更新次数变为四分之一；相同warmup步数覆盖的token增加4倍，相同beta的记忆token跨度也改变，累计decay与梯度噪声可能变化。它们可以作为受控实验变量，但必须明确，而非假装所有条件相同。

</details>

## 来源、版本与使用边界

- 课程锚点：L02 recording固定讲义内嵌源码 `lecture_02.py` 613–666行，讲优化器历史与状态分账；本片只读该段原始源码，另完整读过本课程[L02笔记](#/c/stanford-cs336-2026/lec/lec02?v=notes)及有限译述、bridge07/08。没有新增全片字幕阅读或核音声明。固定[recording原件](https://raw.githubusercontent.com/stanford-cs336/lectures/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e/var/traces/lecture_02_recording.json)来自学期后提交，不能混作当前同名源码。讲义开放翻译许可未确认。
- CS336 Staff，[A1固定讲义](https://raw.githubusercontent.com/stanford-cs336/assignment1-basics/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)，Spring2026 v26.0.3：实际读取§4.2开头与接口说明、§4.3算法及任务契约、§4.4、§5.3恢复状态相关段和§7.2 batch实验段。不是整份A1或所引Adam论文的新精读；作业次序与epsilon约定以上述固定版本为准。相关任务回到[A1指导](#/c/stanford-cs336-2026/lab/a1-basics?v=guide)。
- Vaswani等，*Attention Is All You Need*，[arXiv:1706.03762v7](https://arxiv.org/abs/1706.03762v7)：本片实际读取§3.5、§4、§5.1–5.3及邻接文本；这里只用于辨别原论文的batch/Adam/warmup方案。§5.3是编者指定核心，§5.1–5.2为选读，不扩称官方全文必读。唯一材料精读正文为[L03 materials](#/c/stanford-cs336-2026/lec/lec03?v=materials)；arXiv分发许可不授权公众全文翻译。
- PyTorch团队，[SGD 2.9](https://docs.pytorch.org/docs/2.9/generated/torch.optim.SGD.html)、[AdamW 2.9](https://docs.pytorch.org/docs/2.9/generated/torch.optim.AdamW.html)：2026-11-14快照，实际读取构造接口、公式、参数说明及SGD动量差异说明；另读显示范围内的恢复状态说明。页面链接源码为v2.9.1，不称为课程依赖版本。未读取所链接的AdamW原论文，也不把API默认超参数当通用推荐。复用并全文读取[v2.9.0 LICENSE](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE)以说明上游BSD式许可，不能由此外推所有文档站资产的许可。
- 本文公式解释、预算算例与诊断表由编者自主组织；不是来源逐段翻译或实验结果。官方AI政策仅允许概念/API辅助，禁止AI实现作业及排行榜代码；公共入口见[课程资料](#/c/stanford-cs336-2026)。本页没有优化器、scheduler、模型或训练循环实现。
- 逐源URL、SHA256、原获取UTC、实际阅读范围见 `sources/p3-extensions/manifest-fragment.json`；完整原件只留本地，不公开未授权全文。本文未执行官方训练，CPU预算微例也不构成任何课程验收。

### A1第一方文档许可保留

本文对A1仅作概念定位与约定对照，增加的独立解释不代表Stanford官方。MIT适用于第一方软件及associated documentation，不覆盖引用论文、数据、第三方图像或云服务。

Copyright 2025 Stanford University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
