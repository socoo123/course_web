---
title: "线性代数与张量形状：让每根轴都有名字"
lectureId: bridge01
kind: "编者先修桥接；非 Stanford 官方讲次"
before: lec02
sourceVersion: "PyTorch v2.9.0；CS336 L02 当前讲义 de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e，非 recording 版本"
status: "独立形状微例已在 PyTorch 2.5.1 CPU 执行并核对；不是官方作业环境验收。"
---

# 线性代数与张量形状：让每根轴都有名字

## 学习门槛与出口

需要会向量加法、内积，以及 Python 的列表和索引。不需要先学注意力机制或反向传播。

目标不是记住一串 `reshape`，而是能从一个输出元素的定义推出整个张量形状，再设计一个**即使形状合法也能抓出轴错误**的小例子。本文只讨论逻辑形状；存储、步幅、视图和复制另属内存语义。

## 1. 形状是尺寸，轴名才是含义

约定：

| 轴 | 含义 | 索引 |
| --- | --- | --- |
| $B$ | 批次中的样本数 | $b$ |
| $T$ | 每个样本的位置数 | $t$ |
| $D$ | 每个位置的输入特征数 | $d$ |
| $K$ | 输出特征数 | $k$ |

因此 $X\in\mathbb R^{B\times T\times D}$ 的元素 $X_{btd}$ 表示“第 $b$ 个样本、第 $t$ 个位置的第 $d$ 个特征”。`X.shape == (2, 3, 4)` 只证明尺寸，不能证明轴依次是 batch、time、feature；注释、接口约定与测试值负责补上语义。

三条术语边界：

- 张量的阶数/rank 在这里是**轴数**，不是线性代数里的矩阵秩。
- 标量张量形状为 `()`，一维向量为 `(D,)`，显式列向量为 `(D, 1)`；它们不是可以随意互换的记法。
- Python 维度索引从 0 开始；对三维张量，`dim=-1` 是特征轴，`dim=-2` 是位置轴。负数索引只有连同当前轴约定一起看才有意义。

**推荐写法：** 先在纸上写 `X: [batch, time, in_feature]`，再填具体大小；不要从“这个 shape 正好乘得上”倒推业务含义。

## 2. 矩阵乘法：收缩一根轴，留下另外两根

对 $A\in\mathbb R^{M\times D}$、$W\in\mathbb R^{D\times K}$，

$$
Y_{mk}=\sum_{d=1}^{D} A_{md}W_{dk},
\qquad Y\in\mathbb R^{M\times K}.
$$

输入特征轴 $d$ 被求和消去；行索引 $m$ 和输出特征索引 $k$ 保留。`A * W` 是逐元素乘法（可能广播），不是这个定义。

批次中的每个位置使用同一矩阵时，

$$
Y_{btk}=\sum_{d=1}^{D}X_{btd}W_{dk}.
$$

这不是把批次也求和了，而是为每个 $(b,t)$ 独立计算同一个映射。

PyTorch `matmul`/`@` 的最小形状表：

| 输入形状 | 输出形状 | 含义 |
| --- | --- | --- |
| `(D,) @ (D,)` | `()` | 两向量内积 |
| `(M,D) @ (D,)` | `(M,)` | 矩阵乘向量 |
| `(D,) @ (D,K)` | `(K,)` | 向量乘矩阵 |
| `(M,D) @ (D,K)` | `(M,K)` | 矩阵乘法 |
| `(B,M,D) @ (B,D,K)` | `(B,M,K)` | 批次逐一对应 |
| `(B,M,D) @ (D,K)` | `(B,M,K)` | 共享矩阵 |

双方至少二维时，最后两轴执行矩阵乘法，前面的轴按广播规则对齐。不要把 `(B,D)` 的一批向量当成一个带独立 batch 语义的特殊类型：在 `@` 看来它就是二维矩阵；想要的逐样本操作必须明确写出轴对应关系。

### 一个能逐元素核对的手算例

设 $B=2,T=2,D=3,K=2$，两个样本为

$$
\begin{aligned}
X_0&=\begin{bmatrix}1&2&4\\3&5&7\end{bmatrix},\\
X_1&=\begin{bmatrix}10&20&40\\30&50&70\end{bmatrix},\\
W&=\begin{bmatrix}1&0\\0&1\\1&-1\end{bmatrix}.
\end{aligned}
$$

对任意输入行 $[a,b,c]$，输出是 $[a+c,b-c]$。所以

$$
Y_0=\begin{bmatrix}5&-2\\10&-2\end{bmatrix},
\qquad
Y_1=\begin{bmatrix}50&-20\\100&-20\end{bmatrix}.
$$

例如 $Y_{0,1,0}=3\times1+5\times0+7\times1=10$。输入不全是 1、不同 batch 数值相差十倍，才能辨认“算了哪一行、用了哪个样本”。

## 3. 广播：从右对齐，不会识别你的轴名

以下只考虑各轴长度为正的普通张量；空张量边界不在本页范围。逐元素运算的广播规则是：

1. 从最后一轴开始对齐；较少轴的形状在左侧补 1。
2. 每对尺寸须相同，或其中一个为 1。
3. 对齐后，每轴输出采用较大的尺寸。

例子：

```text
X:       (2, 3, 4)
bias:          (4)  -> 按 (1, 1, 4) 对齐，输出 (2, 3, 4)
scale:   (2, 1, 1)  -> 每个 batch 一个系数，输出 (2, 3, 4)
weights:    (3, 1)  -> 按 (1, 3, 1) 对齐，输出 (2, 3, 4)
```

若 `scale` 只写成 `(2,)`，它对齐的是最后一轴，而不是自动识别为 batch。此处因 2 与 4 冲突会报错；如果恰巧 $D=B=2$，程序反而能跑，却会按特征缩放。

**最危险的不是报错，而是合法的笛卡尔积。** 预测值形状 `(2,1)`，目标形状 `(2,)`：

$$
\begin{bmatrix}10\\20\end{bmatrix}-[1,2]
=\begin{bmatrix}9&8\\19&18\end{bmatrix}.
$$

它比较了每个预测与所有目标，输出 `(2,2)`。若需要逐样本相减，应把目标明确成 `(2,1)`，结果才是 $[9,18]^\top$。因此对应元素的误差计算应先断言**实际形状相同**，不能仅检查最终结果是有限数。

## 4. Reduction：明确哪根轴不再独立

归约（reduction）把指定轴上的多个数汇成一个数，例如 `sum`、`mean`。对 $X:[B,T,D]$：

| 操作 | 输出形状 | 输出元素含义 |
| --- | --- | --- |
| `X.sum(dim=-1)` | `[B,T]` | $\sum_d X_{btd}$ |
| `X.sum(dim=1)` | `[B,D]` | $\sum_t X_{btd}$ |
| `X.sum(dim=0)` | `[T,D]` | $\sum_b X_{btd}$ |
| `X.sum()` | `[]`，即标量 | 所有元素的总和 |
| `X.sum(dim=-1, keepdim=True)` | `[B,T,1]` | 数值同第一行，但保留长度为 1 的轴 |

手算例中，沿特征求和得到 $\begin{bmatrix}7&15\\70&150\end{bmatrix}$；沿时间求和得到 $\begin{bmatrix}4&7&11\\40&70&110\end{bmatrix}$。二者不能用“都是求和”混为一谈。

`keepdim=True` 不是保留原来全部元素，而是保留**轴的位置**。若想把每个位置的特征均值从该位置所有特征中减去，应先取得 `[B,T,1]` 的均值，再与 `[B,T,D]` 相减。若得到 `[B,T]` 就直接相减，广播会从右对齐，可能报错，也可能碰巧错着跑通。

`mean` 还隐含了分母。对某个轴求均值，分母是该轴参与计算的元素数；如果有无效位置，必须另外明确哪些元素计入，不能把填充值当作真实观察。本页不实现掩码损失。

## 5. Einsum：把求和定义直接写在接口里

PyTorch 使用单个字母标记轴，推荐总是显式写输出：

```text
torch.einsum("btd,dk->btk", X, W)
```

读法是：`X` 的轴依次是 $b,t,d$，`W` 的轴是 $d,k$；输出保留 $b,t,k$，输入中未保留的 $d$ 被求和。这正是 $Y_{btk}=\sum_dX_{btd}W_{dk}$。

| 表达式 | 输出 | 含义 |
| --- | --- | --- |
| `btd,dk->btk` | `[B,T,K]` | 同一线性映射作用于每个位置 |
| `btd->bt` | `[B,T]` | 对特征求和 |
| `btd->bd` | `[B,D]` | 对位置求和 |
| `btd,bsd->bts` | `[B,T,S]` | 同一个 batch 内，两组位置向量逐对内积 |

注意两种常见误读：

- 同一个字母出现在两份输入中，**不自动意味着求和**。`b` 在两份输入和输出中都出现时，batch 被保留；是否求和由显式输出决定。
- `btd,dk->tk` 没有输出 `b`，因此连 batch 一起求和，已经不是原任务。`->bkt` 则改变输出轴顺序，不是相同的接口。

同名轴尺寸必须相容；在不同输入之间，PyTorch 允许尺寸为 1 的广播。若同一输入内部重复同一字母，则涉及取对角线且要求对应尺寸相等；本页的普通例子不使用这一特殊规则。这里用的是 `torch.einsum` 单字母接口，**不是**课堂中 `einops.einsum` 的多词轴名语法，不能混着调用。

## 6. 不只检查 shape：故意制造“相同大小的错误轴”

前面的手算例特意取了 $B=T=2$。交换 batch 与 time 后，`X.transpose(0,1)` 的形状仍是 `(2,2,3)`；再乘 $W$，结果形状仍是 `(2,2,2)`。但原来的 `Y[0,1]` 应为 `[10,-2]`，交换后却成了 `[50,-20]`。

因此设计微型测试时需要两层：

1. 用不相等的轴长（例如 $B=2,T=3,D=5$）尽早暴露轴交换。
2. 再用某些相等轴长与非均匀值，验证索引语义；仅检查 shape 无法通过这一关。

独立 CPU 机制片段，仅在已有 PyTorch 环境中运行即可；不要求为了本文安装环境：

```python
import torch

x = torch.tensor([[[1, 2, 4], [3, 5, 7]],
                  [[10, 20, 40], [30, 50, 70]]])
w = torch.tensor([[1, 0], [0, 1], [1, -1]])
expected = torch.tensor([[[5, -2], [10, -2]],
                         [[50, -20], [100, -20]]])
y = x @ w
assert torch.equal(y, expected)
assert torch.equal(torch.einsum("btd,dk->btk", x, w), expected)
assert torch.equal(x.sum(dim=-1), torch.tensor([[7, 15], [70, 150]]))
assert x.sum(dim=-1, keepdim=True).shape == (2, 2, 1)
wrong = x.transpose(0, 1) @ w
assert wrong.shape == y.shape
assert not torch.equal(wrong, y)
prediction = torch.tensor([[10], [20]])
target = torch.tensor([1, 2])
assert (prediction - target).shape == (2, 2)
assert torch.equal(prediction - target[:, None], torch.tensor([[9], [18]]))
print(y[0, 1].tolist(), wrong[0, 1].tolist())
```

执行输出为 `[10, -2] [50, -20]`，全部断言通过。全部是整数运算，数值很小，避免把浮点误差引入这次轴语义检查；不训练模型，不提供官方作业组件。

## 7. 自测：从单个元素反推形状

<details>
<summary>自测 1：X 为 (2,3,4)，W 为 (4,5)，X @ W 的形状？对哪根轴求和？</summary>

输出为 `(2,3,5)`，对长度为 4 的输入特征轴求和。单个输出为 $Y_{btk}=\sum_{d=1}^{4}X_{btd}W_{dk}$；batch 与 time 都保留。

</details>

<details>
<summary>自测 2：(2,3,4) 能与 (3,) 直接逐元素相加吗？若想每个位置加一个数呢？</summary>

不能，最后一轴的 4 与 3 不相容。每个位置一个数应明确为 `(1,3,1)`，也可用 `(3,1)` 左侧补 1，广播后输出 `(2,3,4)`。这是一种位置偏置，不是特征偏置。

</details>

<details>
<summary>自测 3：把 btd,dk->btk 改成 btd,dk->tk，手算例第一位置的输出是什么？</summary>

batch 被求和。第一位置把 `[5,-2]` 与 `[50,-20]` 相加，得到 `[55,-22]`；整个结果形状是 `(2,2)`，第一轴此时是 time，不是 batch。

</details>

<details>
<summary>自测 4：为什么全 1 张量和方阵常让错轴测试“通过”？</summary>

尺寸相同的轴交换后 shape 不变；全 1 的数值在交换后也不变，因此测试根本没有观察到差异。应使用非均匀输入、可辨认的 batch/位置数值，并逐元素核对手算结果。`reshape` 只重新解释元素排列，不能作为语义上的任意轴交换；要交换轴，应明确用转置/置换并检查索引对应。

</details>

## 回到课程

回到 [L02：张量与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)，先为每个张量标出轴名，再讨论元素数和计算量。若一项资源估算连输出形状都没有确定，后面的乘法数字就没有可靠基础。

## 来源与处理范围

本页为编者桥接，不是官方第三讲或课堂译稿。算例、错误案例与自测均为自拟；未使用录像、未截帧、未核音。

- Stanford CS336 [L02 当前固定讲义](https://github.com/stanford-cs336/lectures/blob/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e/lecture_02.py#L89-L110)，以及同文件 `einops_motivation`、`einops_einsum`、`einops_reduce`、`einops_rearrange` 段落。**此处仅作概念关联，读的是当前 handout，不是 `lecture_02_recording`，不参与录像对齐。** 固定提交晚于学期；讲义开放翻译许可未确认。
- PyTorch 官方源文档，固定 **v2.9.0**：[matmul](https://github.com/pytorch/pytorch/blob/v2.9.0/torch/_torch_docs.py#L7575-L7657)、[sum](https://github.com/pytorch/pytorch/blob/v2.9.0/torch/_torch_docs.py#L10829-L10884)、[einsum](https://github.com/pytorch/pytorch/blob/v2.9.0/torch/functional.py#L176-L222)、[广播说明](https://github.com/pytorch/pytorch/blob/v2.9.0/docs/source/notes/broadcasting.rst)。实际阅读上述定义与相关例子，不是把源码文件下载视为全部 API 已读。广播说明中的空尺寸边界不用于本页正尺寸规则。
- PyTorch 第一方源码及文档的 [BSD-3-Clause 许可](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE) 已读取；本文是自主讲解，不发布完整文档译文。补充版本不代表已核实课程运行环境恰为 2.9.0。
- 精确读取行范围、来源 SHA-256 与获取时间见 `sources/p2-bridge-foundations/manifest-fragment.json`；本批微例使用既有 Python 3.11.8 / PyTorch 2.5.1 CPU 环境，结果记录在 `sources/p2-shared/cpu-example-check.json`，不等于2.9文档环境或A1固定依赖验收。
