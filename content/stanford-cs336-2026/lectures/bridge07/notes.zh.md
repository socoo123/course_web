---
title: "浮点数与数值稳定性：装得下，不等于算得准"
lectureId: bridge07
kind: "编者先修桥接，非官方讲次"
sourceVersion: "L02 recording trace @ de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e；PyTorch 2.9 文档快照"
sourceManifest: "sources/p2-bridge-systems/manifest-fragment.json"
status: "两个 API 微例已在 PyTorch 2.5.1 CPU 执行并按容差核对；格式边界仍须区分设备行为。"
mediaStatus: "本桥接无独立官方录像；仅 notes，不制作 draft 或 materials。"
---

# 浮点数与数值稳定性：装得下，不等于算得准

## 1. 节省一半存储，究竟牺牲了什么

一个 FP32 元素占4字节，FP16 和 BF16 各占2字节，但两个16位格式不是同一种取舍：

- **动态范围**：能表示多大、多小的数，主要由指数位决定。
- **精度**：在某个数量级附近，相邻可表示数有多密，主要由有效数字位决定。

把 dtype 变小不是“所有数多一点误差”这么简单：数可能溢出成无穷，可能舍入成零，也可能仍非零但丢掉有用的小增量。本页补足理解 L02 混合精度与资源账本的门槛，不展开训练配方或后续系统优化。

## 2. 指数管范围，有效数字管间距

对正常数（normal number），二进制格式可写成：

$$
(-1)^s(1.f)_2\,2^e.
$$

符号位决定正负；指数决定数量级；小数部分 $f$ 决定这个数量级里的细分。前面的1是隐含位，因此正常数的有效二进制位数比“小数位数”多1。

| 格式 | 总位数 | 指数位 | 小数位 | 1附近向上的间距 `eps` |
| --- | --- | --- | --- | --- |
| FP32 | 32 | 8 | 23 | $2^{-23}\approx1.19\times10^{-7}$ |
| FP16 | 16 | 5 | 10 | $2^{-10}\approx9.77\times10^{-4}$ |
| BF16 | 16 | 8 | 7 | $2^{-7}=0.0078125$ |

`eps` 不是所有数都适用的固定绝对误差。在区间 $[2^e,2^{e+1})$ 内，正常数的间距是 $2^{e-p}$，其中 $p$ 是小数位数：数值越大，绝对间距越大。

### 手算：为什么加1可能没有变化

FP16 在 $[2048,4096)$ 内的间距为 $2^{11-10}=2$，2048的下一个更大数是2050。若采用常见的“舍入到最近值，恰在中点时取偶数尾位”，$2048+1$ 落在中点，会舍入回2048。BF16 在256附近就已经出现间距2。

所以 BF16 的指数多，不代表它在1附近更细；它比 FP16 更早丢掉小增量。反过来，FP16 在1附近更精细，却不能容纳 BF16 那么大的数量级。

## 3. 最大有限数、最小正常数、最小非零数要分开

| 格式 | 最大有限正数 | 最小正常正数 `tiny` | 理论最小次正常正数 |
| --- | --- | --- | --- |
| FP32 | $\approx3.40\times10^{38}$ | $2^{-126}\approx1.18\times10^{-38}$ | $2^{-149}\approx1.40\times10^{-45}$ |
| FP16 | $65504$ | $2^{-14}\approx6.10\times10^{-5}$ | $2^{-24}\approx5.96\times10^{-8}$ |
| BF16 | $\approx3.39\times10^{38}$ | $2^{-126}\approx1.18\times10^{-38}$ | $2^{-133}\approx9.18\times10^{-41}$ |

表中次正常数（subnormal）是格式层面的理论能力；部分设备或算子会把次正常数冲刷为零，不能保证所有后端都保留它们。

- `torch.finfo(dtype).max` 是最大有限数。
- `tiny`/`smallest_normal` 是最小**正常**正数，不是最小非零正数。
- `finfo.min` 是最负的有限数，通常为 `-max`，也不是“最小正数”。

**BF16 与 FP32 有相同的指数位数和正常指数范围，不等于每个边界值完全相同。** 它们的最大有限值略有差别，次正常范围和精度也不同。

### 三类失败，不要统称“精度不够”

1. **Overflow（上溢）**：FP16 可以存40000，但数学上的 $40000\times2=80000$ 超过65504，存回 FP16 时无法保留有限结果。事后 `.float()` 只能把已有的 `inf` 转成 FP32 的 `inf`，不能找回80000。
2. **Underflow（下溢）**：$10^{-8}$ 比 FP16 最小次正常数的一半还小，按通常舍入会变成0；BF16 能表示这个数量级，但仍有舍入误差。不是所有小于 `tiny` 的数都会立刻变0。
3. **舍入与吸收**：数还在范围内，但小增量没有跨过相邻表示点；前面的2048加1就是例子。

`NaN` 则常来自未定义的计算，例如 `inf / inf`、`0 / 0`。它不是一种“很大的数字”。遇到非有限结果应定位第一个出问题的输入或中间量，而不是默认用替换 `NaN` 的办法掩盖问题。

## 4. 为什么数学恒等式会给出不同结果

实数加法满足结合律，浮点加法通常不满足。考虑 FP32 的三个数：

$$
a=2^{24}=16777216,\quad b=1,\quad c=-2^{24}.
$$

在 $2^{24}$ 向上相邻数间距为2，按最近偶数舍入：

$$
(a+b)+c=16777216-16777216=0,
$$

但 $b+c=-16777215$ 可以精确表示，所以：

$$
a+(b+c)=1.
$$

这不是随机性造成的；即使 seed 相同，改变求和树、分块方式或后端也可能改变舍入路径。并行归约通常不是 Python 从左到右逐项相加。比较两个实现时要先约定 dtype、尺度和合理容差，而不是一律要求逐位相同；容差也不能放大到掩盖形状或算法错误。

## 5. 稳定 softmax：消掉巨大的共同偏移

对有限输入 $x_1,\ldots,x_n$：

$$
p_i=\frac{e^{x_i}}{\sum_j e^{x_j}}.
$$

直接求指数可能在真正得到概率之前就溢出。取 $m=\max_jx_j$，分子分母同时除以 $e^m$：

$$
p_i=\frac{e^{x_i-m}}{\sum_j e^{x_j-m}}.
$$

因为 $x_i-m\le0$，指数项都不超过1，至少一项等于1。这消除了“输入整体很大”造成的指数上溢，但不是对任意 dtype、任意长度和非有限输入的万能保证。

### 手算：输入是1000，不等于概率计算必须爆掉

令 $x=(1000,1001,999)$，取 $m=1001$：

$$
\begin{aligned}
x-m&=(-1,0,-2),\\
Z&=e^{-1}+1+e^{-2}\\
&\approx1.503215.
\end{aligned}
$$

因此：

$$
p\approx(0.244728,\ 0.665241,\ 0.090031).
$$

FP32 直接计算 $e^{1000}$ 会越界，但这些最终概率都很普通。**最终结果可表示，不保证朴素的中间计算也可表示。**

平移也有边界：

- 极小概率仍可能下溢成0；这不等于算法给所有尾部概率都提供高相对精度。
- 若输入一开始已是 `inf`/`NaN`，平移不能还原原值；`inf-inf` 仍是 `NaN`。
- 若某行全部为 `-inf`，没有有限最大值可作这个推导的起点，也没有正常的概率归一化。应由上游数据/掩码契约处理，不临时编造分布。
- 很长的低精度归约仍需要关心累积与输出 dtype。

### logsumexp：不要先把巨大的指数算出来

$$
\operatorname{LSE}(x)=\log\sum_j e^{x_j}
=m+\log\sum_j e^{x_j-m}.
$$

同一个例子得到 $1001+\log(1.503215)\approx1001.407606$。若需要对数概率，应使用稳定的 `log_softmax`，而不是先形成可能含0的 softmax 再取 `log`；后者可能得到本可避免的 `-inf`。

下面只调用库 API 观察三个数，没有实现作业中的 softmax 或损失函数：

```python
import torch
import torch.nn.functional as F

x = torch.tensor([1000.0, 1001.0, 999.0], dtype=torch.float32)
p = F.softmax(x, dim=0, dtype=torch.float32)
lse = torch.logsumexp(x, dim=0)
print(p, lse)
# 数学参照：p 约为 [0.244728, 0.665241, 0.090031]
# lse 约为 1001.407606；实际显示位数由 dtype 和打印设置决定。
```

`logsumexp` 没有这里所用的 `dtype=` 参数；想用 FP32 计算低精度输入时，应在调用前明确转换，例如 `torch.logsumexp(x.float(), dim=0)`。转换不能追回低精度输入中已经丢失的信息。

## 6. 求和、均值与累积 dtype

讨论低精度计算时，至少要区分：**输入存储 dtype、内部运算/累积精度、输出 dtype**。三者不一定相同。

对 `torch.sum` 和 `torch.mean`，显式传入 `dtype=torch.float32` 的 API 契约是先按指定 dtype 处理输入，并用该 dtype 返回结果。不要仅凭输入 dtype 猜内部实现，也不要把“某矩阵乘常用 FP32 累积”推广成所有算子都永远如此；后端还可能允许降低精度的归约步骤。

### 微例：平均值能装下，总和却装不下

四个 FP16 的40000相加，数学总和是160000，平均值是40000。直接求和后若结果必须写回 FP16，就会超出它的有限范围。

```python
z = torch.full((4,), 40000.0, dtype=torch.float16)
s_bad = z.sum()
s32 = z.sum(dtype=torch.float32)
mean32 = z.mean(dtype=torch.float32)
print(s_bad, s32, mean32)
# 推演：s_bad 为 inf；s32 为 160000；mean32 为 40000。
# s_bad.float() 仍为 inf，不能修复已经发生的溢出。
```

不能由此断言 `z.mean()` 一定溢出：均值 API 的实际计算策略可能不同于 `z.sum() / z.numel()`。即使数学表达等价，也不能擅自把两段程序的中间值、求和顺序和 dtype 契约视为相同。要让这里的意图清楚，可直接声明均值 dtype。

还有一个与舍入无关的常见错误：**均值的均值不一定是全体均值。** 一组2个数均值为1，另一组6个数均值为3；简单平均两个均值得2，而全体均值是 $(2\times1+6\times3)/8=2.5$。归约前先确认计数和权重，再讨论数值精度。

混合精度的含义是为不同角色选择合适精度，而不是全局无差别 `.half()`。本页只要求你能解释为什么长期累积状态、归约或敏感变换可能需要更高精度；具体训练策略留给相应课程内容。

## 7. 自测

<details>
<summary>1. FP16 和 BF16 都是2字节，为什么一个能表示更小的数，另一个在1附近更精细？</summary>

BF16 给指数8位、小数7位；FP16 给指数5位、小数10位。前者覆盖更广数量级，后者在相同正常数量级里有更细的表示间距。存储量相同不代表范围与精度相同。

</details>

<details>
<summary>2. 某数小于 finfo.tiny，就一定被存成0吗？</summary>

不一定。`tiny` 是最小正常正数，更小的次正常数仍可能可表示；但再小会舍入成0，某些硬件/算子也会冲刷次正常数。还应注意 `finfo.min` 是最负有限数，而不是最小正数。

</details>

<details>
<summary>3. 给 softmax 所有输入加1000，实数概率不变；浮点朴素实现为什么可能变成 NaN？</summary>

朴素实现先计算指数，可能将分子、分母变成 `inf`，再做 `inf/inf` 得到 `NaN`。先减有限最大值可消掉共同偏移，避免这类指数上溢。它仍不能修复已经非有限的输入或保证所有尾部概率精确。

</details>

<details>
<summary>4. FP16 求和产生 inf 后，转 FP32 与求和前指定 FP32 一样吗？</summary>

不一样。事后转换保留已有的 `inf`；事先指定 FP32 可以在更大范围内进行归约并保存结果。本页四个40000的例子中，两者分别是 `inf` 与160000。

</details>

<details>
<summary>5. 把求和分成若干块，seed 没变却得到末位差异，能直接判定实现错误吗？</summary>

不能。块划分改变舍入顺序，浮点加法不满足结合律；要用明确 dtype、尺度与容差比较。但若差异来自少算元素、错误广播或不等长组均值直接平均，则是算法错误，不能用“浮点误差”开脱。

</details>

回到 [L02：PyTorch、einops 与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)，把 dtype 同时看成“每元素字节数”和“有限的数值能力”；资源账本继续见 [bridge08](#/c/stanford-cs336-2026/lec/bridge08?v=notes)。

## 来源、阅读范围与边界

- 课程锚点：[L02 recording 讲义](https://cs336.stanford.edu/lectures/?trace=lecture_02_recording)，固定提交 `de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e` 内嵌 `lecture_02.py` 的 `tensors_memory`，包括 FP16 小数下溢、BF16 范围与混合精度动机。本页格式表、稳定变换推导、结合律和归约小例为**编者补充**，不是课堂逐句翻译。
- PyTorch **2.9**：[Type Info](https://docs.pytorch.org/docs/2.9/type_info.html)（`finfo` 的 `eps/max/min/tiny` 定义与次正常数说明）；[Numerical accuracy](https://docs.pytorch.org/docs/2.9/notes/numerical_accuracy.html)（正文，重点为非结合、极端中间值及低精度归约）；[sum](https://docs.pytorch.org/docs/2.9/generated/torch.sum.html)、[mean](https://docs.pytorch.org/docs/2.9/generated/torch.mean.html)、[softmax](https://docs.pytorch.org/docs/2.9/generated/torch.nn.functional.softmax.html)、[logsumexp](https://docs.pytorch.org/docs/2.9/generated/torch.logsumexp.html)（完整 API 正文）。数值表由格式位宽推导，理论边界不等于所有设备的次正常数行为。
- 格式事实交叉核对：Wikipedia contributors，[Bfloat16 floating-point format，固定修订1384316605](https://en.wikipedia.org/w/index.php?title=Bfloat16_floating-point_format&oldid=1384316605) 的 FP16/BF16/FP32 位分配、指数编码及最大有限值说明。条目文本适用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)；本页只据此核对数值事实并独立推导，没有复制条目段落、位图或图表，不把它当 PyTorch 算子行为规范。
- PyTorch 上游 [v2.9.0 LICENSE](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE) 为 BSD 三条款式许可；不外推课程录像或第三方资产。课程讲义开放翻译许可未确认，本文不发布原文全文或完整翻译。
- 原始文件、SHA256、UTC 和精确阅读范围见 `sources/p2-bridge-systems/manifest-fragment.json`。两个 API 微例及非结合性检查已在 PyTorch 2.5.1 CPU 执行，结果见 `sources/p2-shared/cpu-example-check.json`；没有下载媒体、截帧或核音，不得把微例当作官方 A1 实现或训练完成证据。
