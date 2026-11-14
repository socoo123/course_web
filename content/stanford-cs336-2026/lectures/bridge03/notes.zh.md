---
title: "反向传播与自动微分：沿路径相乘，在汇合处相加"
lectureId: bridge03
kind: "编者先修桥接；非 Stanford 官方讲次"
before: lec03
sourceVersion: "PyTorch 2.9 版本文档快照；独立概念/API补充，不代表课程依赖版本"
sourceManifest: "sources/p3-bridges/manifest-fragment.json"
status: "独立的一阶自动微分与CPU机制例子；非官方作业实现或训练，来源阅读范围见分片清单。"
mediaStatus: "无独立官方录像；仅 notes，不制作 draft 或 materials。"
---

# 反向传播与自动微分：沿路径相乘，在汇合处相加

## 学习门槛与出口

会对 $x^2$ 求导，能读懂向量内积和张量轴即可；形状记法可先看 [bridge01](#/c/stanford-cs336-2026/lec/bridge01?v=notes)。本页要回答：**一个参数被许多位置使用后，为什么最后只得到一份梯度，这份梯度究竟加了什么？**

反向传播不是更新参数的算法，而是计算导数的算法。自动微分负责把实际执行的可微运算连接起来；优化器使用所得梯度决定如何更新。先把这两步分开，才能定位“导数没算到”与“更新没发生”。

## 1. 链式法则传回的是敏感度，不是原来的数

设 $u=f(x)$、$L=g(u)$。对很小的扰动，局部线性近似为

$$
\begin{aligned}
\Delta u&\approx f'(x)\Delta x,\\
\Delta L&\approx g'(u)\Delta u,\\
\frac{dL}{dx}&=g'(u)f'(x).
\end{aligned}
$$

前向传递数值，反向传递“损失对这个数有多敏感”。把 $\bar u=\partial L/\partial u$ 称为上游梯度，则当前节点只需做 $\bar x=\bar u f'(x)$，不必重新展开后面所有函数。

例如 $u=x^2$、$L=3u$，在 $x=2$ 时：前向 $u=4,L=12$；反向从 $\bar L=1$ 开始，得到 $\bar u=3$，再得 $\bar x=3\times4=12$。这里 $L$ 和导数恰好同为12只是数值巧合，两者不是同一个量。

自动微分也不是有限差分：它组合各个算子的导数规则，不靠给每个参数加一个微小扰动重跑前向。有限差分适合在小问题上交叉核对导数，但会受步长、舍入和不可微点影响。

## 2. 一个值走了两条路，回来的贡献必须相加

考虑一个真正共享的中间量：

$$
\begin{aligned}
u&=x^2,\\
a&=3u,\qquad b=u^2,\\
L&=a+b.
\end{aligned}
$$

在 $x=2$ 时，$u=4,a=12,b=16,L=28$。反向分成两条贡献：

$$
\begin{aligned}
\bar u_{\text{经 }a}&=1\times3=3,\\
\bar u_{\text{经 }b}&=1\times2u=8,\\
\bar u&=3+8=11,\\
\bar x&=11\times2x=44.
\end{aligned}
$$

![共享节点先汇总两条反向贡献，再继续向输入传递](./assets/shared-node-vjp.svg)

*图：编者自拟计算图。实线表示前向依赖；框内注明反向贡献。共享节点 $u$ 收齐3和8后，才能把11传向更早的节点。不是课堂原图。*

关键是“加到已有贡献上”，不是“后到的覆盖先到的”。同一个参数在不同 token、不同 batch 样本或不同分支中复用，都服从这个规则。**参数共享不是复制出多个独立参数；这些使用处的导数最后汇回同一个参数。**

残差连接 $y=x+F(x)$ 也包含两条路径。给定上游向量 $\bar y$，回到 $x$ 的结果是

$$
\bar x=\bar y+J_F(x)^\top\bar y.
$$

第一项来自直通路径，第二项来自变换路径。这说明残差提供了额外梯度通路；却不能保证总梯度永不消失或爆炸，因为两项仍可能抵消或放大。

## 3. 向量输出不等于自动得到整个 Jacobian

令 $x\in\mathbb R^n$、$y=f(x)\in\mathbb R^m$，定义

$$
J_{ij}=\frac{\partial y_i}{\partial x_j},
\qquad J\in\mathbb R^{m\times n}.
$$

如果后面的标量损失传回 $\bar y\in\mathbb R^m$，那么

$$
\begin{aligned}
\bar x_j&=\sum_{i=1}^{m}\bar y_iJ_{ij},\\
\bar x&=J^\top\bar y\in\mathbb R^n.
\end{aligned}
$$

这里把梯度写成列向量；写成行向量就是 $\bar y^\top J$，因此称为 **vector–Jacobian product，VJP**。两种方向约定表达同一个收缩，不能在推导中突然换约定。

反向过程通常直接计算这个乘积，不先分配一个巨大的 $m\times n$ Jacobian。训练的最终目标通常是标量，所以从 $\bar L=1$ 出发的一次反向就能得到所需的参数梯度。

### 一个非全1的种子向量

设

$$
\begin{aligned}
y_1&=x_1x_2,\\
y_2&=x_1+x_2^2.
\end{aligned}
$$

在 $x=(2,3)$ 时，

$$
J=\begin{bmatrix}3&2\\1&6\end{bmatrix}.
$$

选择种子 $v=(2,-1)$，就是询问标量 $2y_1-y_2$ 对输入的敏感度：

$$
J^\top v=(5,-2)^\top.
$$

选择全1种子则是在对 $y_1+y_2$ 求导，得到 $(4,8)$，**不是得到整个 Jacobian**。对非标量输出调用 `backward(gradient=v)`，或调用 `autograd.grad(..., grad_outputs=v)`，都必须明确这个种子的含义与输出形状。

## 4. 广播的反向是归约，因为同一个输入被复用了

令 $X:[B,T,D]$，特征偏置 $b:[D]$，前向为

$$
Y_{btd}=X_{btd}+b_d.
$$

此处下标 $b$ 表示 batch 索引，粗体意义的偏置由 $b_d$ 表示；为避免程序命名混淆，代码中可叫 `bias`。给定 $G=\partial L/\partial Y$，则

$$
\begin{aligned}
\frac{\partial L}{\partial X_{btd}}&=G_{btd},\\
\frac{\partial L}{\partial b_d}&=\sum_{b=1}^{B}\sum_{t=1}^{T}G_{btd}.
\end{aligned}
$$

偏置没有 batch/time 独立副本；每个使用处都对同一个 $b_d$ 贡献，所以要沿这两根轴相加。反向结果的形状必须回到原输入的 `[D]`。

一般地：前向广播新增或扩展的轴，反向需要把相应贡献求和，再恢复原输入形状。前向 `sum` 则反过来把上游梯度分发给被求和的每个元素；前向 `mean` 还要乘上那个均值的分母倒数。

**广播反向不会擅自平均。** 若损失已经除以有效 token 数，$G$ 里面就已经含有这一因子；再除一次会把梯度缩小错一遍。若损失用总和，就保留总和尺度。损失分母和张量尺寸不能靠猜。

## 5. 计算图、叶子与 `.grad` 是三件事

以下限定普通实数张量和默认梯度模式：

| 对象或操作 | 应怎样理解 |
| --- | --- |
| 直接创建且 `requires_grad=True` 的输入 | 通常是叶子，`grad_fn` 为 `None` |
| 由可微运算得到的结果 | 通常是非叶子，`grad_fn` 记录反向入口 |
| `requires_grad=False` 的张量 | 按 API 约定视为叶子，不表示它会得到梯度 |
| `loss.backward()` | 默认把贡献累加到参与计算且需要梯度的叶子的 `.grad` |
| 非叶子的 `.grad` | 默认不保留；需要观察时，在反向前调用 `retain_grad()` |
| `autograd.grad` | 返回请求的 VJP，不把结果累加进这些输入的 `.grad` |

非叶子的 `.grad` 没有被保存，**不表示梯度没有经过它**。反向仍需要经过中间节点，才能得到更早输入的梯度；是否把中间结果留给用户查看，是另一项存储决定。

反过来，“我在 Python 里给它起了名字”不使它成为叶子。例如对需要梯度的张量执行改变 dtype 的转换，转换结果可以是非叶子。应该观察 `is_leaf`、`requires_grad`、`grad_fn`，而不是依变量名判断。

### 图的生命周期与梯度缓冲区的生命周期不同

每次前向按实际执行的运算创建新图；通常反向后会释放再次反向所需的保存内容。第二次对同一旧图反向可能报错，不能把 `retain_graph=True` 当成所有错误的万能补丁。

- `retain_graph=True`：保留该图再次反向所需的内容，不会清空梯度。
- `create_graph=True`：对导数计算本身构图，用于更高阶导数；不是普通训练的必需开关。
- `retain_grad()`：让指定非叶子保留自己的 `.grad`；与以上两个参数无关。
- 新一次前向得到新图：不自动清掉参数旧的 `.grad`。

保存训练日志时只需要损失数值，不要长期保存每一步仍连着图的损失张量。内存与 `detach()` 共享存储的区别见 [bridge05](#/c/stanford-cs336-2026/lec/bridge05?v=notes)；切断求导关系不是创建独立数据快照。

## 6. 两个独立 CPU 机制微例

下面不包含模型层、损失函数或训练循环的作业实现，只观察自动微分 API。使用已有 CPU PyTorch 即可，不需要模型、数据或 GPU。

### 微例 A：同一图内的共享，与不同反向之间的累积

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
u = x.square()
u.retain_grad()
loss = 3 * u + u.square()
loss.backward()
print(u.grad.item(), x.grad.item())

# 重新前向得到新图，但沿用 x 的梯度缓冲区。
(5 * x).backward()
print(x.grad.item())

x.grad = None
(5 * x).backward()
print(x.grad.item())
```

手算预期三行依次为 `11.0 44.0`、`49.0`、`5.0`。第一行的相加来自**同一图的多条路径**；第二行的44加5来自**两次反向共用叶子梯度缓冲区**。这是两种不同的累积，不能混成“反向自动平均”。

真实训练通常在一个有效批次开始前清梯度，并允许这个批次的所有微批贡献累积后再更新。每个微批都清零会丢掉前面的贡献；跨有效批次从不清零则会混入旧梯度。具体分母和裁剪顺序见 [ext01](#/c/stanford-cs336-2026/lec/ext01?v=notes)。

### 微例 B：VJP 种子与广播回收

```python
import torch

x = torch.tensor([2.0, 3.0], requires_grad=True)
y = torch.stack((x[0] * x[1], x[0] + x[1].square()))
v = torch.tensor([2.0, -1.0])
(g,) = torch.autograd.grad(y, x, grad_outputs=v)
print(g.tolist(), x.grad is None)

bias = torch.tensor([0.5, -0.5], requires_grad=True)
base = torch.zeros((2, 2, 2))
upstream = torch.tensor([[[1.0, 2.0], [3.0, 4.0]],
                         [[10.0, 20.0], [30.0, 40.0]]])
(base + bias).backward(upstream)
print(bias.grad.tolist())
```

手算预期为 `[5.0, -2.0] True`，以及 `[44.0, 66.0]`。第二个输出逐特征沿 batch 和 time 相加；没有沿特征轴相加，也没有除以4。

## 7. `None`、零和非有限值不要混诊

- **`grad is None`**：可能尚未反向、刚清为 `None`、该参数没有参与当前路径，或图被切断；也可能你在观察未 `retain_grad()` 的非叶子。
- **梯度是零张量**：可能是真正的局部零导数，也可能是抵消、掩码、饱和或低精度丢失；单凭“零”不能确定原因。
- **梯度为 `NaN`/`inf`**：需要定位数学定义、前向中间量和反向奇点，不能简单称作“没训练到”。

`zero_grad(set_to_none=True)` 与把梯度填零并不处处等价：PyTorch 优化器通常跳过没有梯度的参数，而零梯度参数仍可能因优化器已有状态或衰减发生变化。更新规则的详细动态归 [ext02](#/c/stanford-cs336-2026/lec/ext02?v=notes)，这里不重复展开。

`model.eval()` 不关闭求导；`no_grad()` 不自动切换模型的训练/评估行为。二者在训练闭环中如何配对，见 [bridge06](#/c/stanford-cs336-2026/lec/bridge06?v=notes)。

## 8. 自测

<details>
<summary>1. 上面的共享节点例子若把 b 改成 −u²，在 x=2 时梯度是多少？</summary>

两条贡献变为3和−8，$\bar u=-5$，所以 $\bar x=-5\times4=-20$。直通或共享路径存在，不代表梯度贡献一定同号。

</details>

<details>
<summary>2. 向量 y 传入全1种子，为什么不是获得完整 Jacobian？</summary>

因为得到的是各输出导数之和，即 $J^\top\mathbf1$，等价于对所有输出的和求导。完整 Jacobian 要保留“哪个输出”这一维，单个 VJP 已经沿输出轴收缩了它。

</details>

<details>
<summary>3. Y = X + bias，X 是 (2,3,4)，bias 是 (4,)，若损失是 Y 全部元素的均值，bias 的每个梯度是多少？</summary>

共有24个元素，上游每项为 $1/24$。每个偏置复用6次，因此每个梯度是 $6/24=1/4$。不是 $1/24$，也不是在此基础上再除以6。

</details>

<details>
<summary>4. 非叶子 u.grad 是 None，参数 x.grad 却正确，这矛盾吗？</summary>

不矛盾。反向通过 $u$ 计算了必要的中间导数，但默认没有把它保留在 `u.grad` 供用户查看。需要观测时应在反向前 `u.retain_grad()`，而不是认定自动微分漏算。

</details>

<details>
<summary>5. 为第二次反向加 retain_graph=True，会把旧参数梯度清掉吗？</summary>

不会。保留计算图与清梯度缓冲区是不同操作。应先判断你是需要对同一次前向多次求导，还是应重新前向；再独立决定哪些贡献应累加、何时清空。

</details>

## 回到课程与来源

回到 [L03：模型架构与超参数](#/c/stanford-cs336-2026/lec/lec03?v=notes)，读残差、归一化和共享权重时，分别画出前向依赖与反向贡献。本文只建立一阶求导语义；稳定性诊断归 ext01，优化器规则归 ext02。

本页是自主教学，推导、数值、SVG 和微例均为编者自拟，不是官方讲次、文档译本或 A1 可提交实现。补充 API 依据是 **PyTorch 2.9 版本文档快照**；页面部分源码链接指向 v2.9.1，不把它谎称成统一 v2.9.0 运行环境。

- [Autograd mechanics](https://docs.pytorch.org/docs/2.9/notes/autograd.html)：实际读图的记录与保存张量、不可微点/除零、梯度开关、训练/评估模式、原地操作及检查，未读后续多线程、复数和 hooks 专题。
- [Tensor.is_leaf](https://docs.pytorch.org/docs/2.9/generated/torch.Tensor.is_leaf.html)、[Tensor.backward](https://docs.pytorch.org/docs/2.9/generated/torch.Tensor.backward.html)、[autograd.grad](https://docs.pytorch.org/docs/2.9/generated/torch.autograd.grad.html)、[Optimizer.zero_grad](https://docs.pytorch.org/docs/2.9/generated/torch.optim.Optimizer.zero_grad.html)：实际读完整 API 正文；本文只使用一阶、单进程普通张量语义。
- [广播说明，v2.9.0](https://github.com/pytorch/pytorch/blob/v2.9.0/docs/source/notes/broadcasting.rst) 与 [detach](https://docs.pytorch.org/docs/2.9/generated/torch.Tensor.detach.html)：复用 P2 本地原件，实际读正文。广播反向的求和由本页链式法则推导；空尺寸边界不在本文讨论范围。
- PyTorch 第一方上游 [BSD 三条款许可](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE) 已读；不外推第三方资产、课程讲义或录像。原始文档留本地，逐源获取时间、哈希与实际范围见本页 `sourceManifest`。
