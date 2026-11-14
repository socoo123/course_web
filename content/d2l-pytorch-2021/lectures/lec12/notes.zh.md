---
draftStatus: "not_required_by_user"
source: "《动手学深度学习》中文第二版4.5全文，重点核对PyTorch分支；固定提交e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照；另读PyTorch2.5优化器API指定节。"
video: "https://www.bilibili.com/video/BV1UK4y1o7dy"
license: "教材仓库Apache-2.0不外推视频；视频copyright=1/no_reprint=0，0不代表开放许可，未取得开放转载许可。算例与图为编者自拟。"
status: "教材导读；3P公开字幕均为空，课堂未核实，课堂逐段整理不另作；1个普通SGD机制片段CPU核对通过，非完整正则化实验。"
title: "权重衰减：把损失约定、参数分组与更新公式对齐"
lectureId: lec12
kind: "教材导读 / 编者笔记"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
codeExecution: "1个Python机制片段CPU核对通过，见sources/p2-shared/notes-smoke.json；未运行高维回归或Adam/AdamW实验。"
---

# 权重衰减：把损失约定、参数分组与更新公式对齐

## 1. 不删除特征，给大权重定一个价格

当训练样本少、可调参数多时，模型可能沿着对训练数据影响很小的方向，把权重推得很大，却在新样本上产生大误差。权重衰减给“拟合数据”和“保持权重较小”一个连续折中，不需要立刻删掉整列特征或整层网络。

对$B$个样本、$d$维特征，记$X\in\mathbb R^{B\times d}$，$w\in\mathbb R^{d\times1}$，$b$为标量，$y,\hat y\in\mathbb R^{B\times1}$，$\hat y=Xw+b$。本页明确采用：

$$
\begin{aligned}
L_B(w,b)&=\frac1B\sum_{i=1}^{B}\frac12(\hat y_i-y_i)^2,\\
J_B(w,b)&=L_B(w,b)+\frac\lambda2\|w\|_2^2.
\end{aligned}
$$

$\lambda\ge0$是用验证集选择的超参数；本例不惩罚$b$。$\|w\|_2^2=\sum_jw_j^2$是**平方范数**，不是带平方根的$\|w\|_2$。矩阵参数用各元素平方和，即Frobenius范数平方。

自拟小例：$w=[3,4]^\top$，范数为5，平方范数为25；若$\lambda=0.2$，惩罚项为2.5，惩罚梯度是$[0.6,0.8]^\top$。较大分量承受较大拉回力，但一般不会像某些稀疏惩罚那样把大量坐标精确变成零。

“权重更小”也不是不依赖单位的真理。把特征$x$放大100倍，同时把其权重缩小100倍，预测不变，惩罚却变为原来的万分之一。因此输入尺度、仅在训练集拟合的标准化、哪些参数被惩罚，都是这个方法的一部分。

## 2. 为什么它在普通SGD里叫“衰减”

令数据损失梯度为$g_w=\nabla_wL_B$，学习率为$\eta$。普通SGD的一步为：

$$
\begin{aligned}
w^+&=w-\eta(g_w+\lambda w)\\
   &=(1-\eta\lambda)w-\eta g_w,\\
b^+&=b-\eta\nabla_bL_B.
\end{aligned}
$$

两个贡献分别是沿数据梯度移动，以及沿原点方向缩小旧权重。它们都使用**同一个旧参数点**计算，不能先更新权重，再重新计算不同点的梯度后还称为同一个代数式。

![同一个普通SGD更新的两条等价计算路线](assets/sgd-decay-equivalence.svg)

图为编者自拟算例：$w=[2,-1]$、$g_w=[0.5,-0.5]$、$\eta=0.1$、$\lambda=0.2$。惩罚梯度为$[0.4,-0.2]$，总梯度为$[0.9,-0.7]$；下一步为$[1.91,-0.93]$。如果不加惩罚，则是$[1.95,-0.95]$。

当只剩惩罚梯度时，$0<\eta\lambda<1$表示不改变符号地向零缩小；$\eta\lambda=1$一步归零；更大的乘积可能翻转符号，甚至放大幅值。**正则强度不是越大越保险。** 有数据梯度时，某个权重仍可增大，权重范数也不保证每一步下降。

### 等价关系的准确范围

这里的“L2惩罚等价于乘法衰减”要求：

- 使用无动量、无自适应缩放的普通SGD，且优化方向为最小化。
- 两边使用相同损失归约、相同batch、相同学习率与参数集合；梯度未被不同地裁剪或改写。
- 惩罚是$\lambda\|w\|^2/2$，不是$\lambda\|w\|^2$；后者梯度是$2\lambda w$。
- 不在loss里手加一次，又给优化器配置一次同样的惩罚。

PyTorch的带动量SGD仍可把L2梯度加进动量缓冲，这与“对同一正则目标使用同一种动量算法”相符；但不能再把完整更新简化为上面只含当前$g_w$的两项公式。

## 3. 最容易悄悄改变实验的，是mean和sum

| 写法 | 对应惩罚梯度（未考虑额外梯度缩放） |
| --- | --- |
| `data_loss.mean() + lam * w.square().sum() / 2` | $\lambda w$ |
| `data_loss.mean() + lam * w.square().sum()` | $2\lambda w$ |
| `(data_loss + lam * w.square().sum() / 2).sum()` | $B\lambda w$，其中逐样本loss共有$B$项 |
| 上一行，随后自写SGD把全部梯度除以$B$ | 恢复为$\lambda w$ |

教材从零实现把惩罚广播到每个样本的loss后求和，再由`d2l.sgd`按batch数归一化。若改用已经接收平均梯度的标准优化器，却原样保留这段sum，就放大了惩罚。反过来，先mean后又除一次batch size，则会缩小全部更新。最后不足一个batch时，还要使用真实样本数，而不是固定名义batch size。

另一个精确边界：本页数据损失含$1/2$，而PyTorch `MSELoss`默认是平方误差均值，不含$1/2$。教材4.5从零实现使用`d2l.squared_loss`，简洁实现使用`MSELoss`，两条路线的数值约定不能自动视为完全一致。若用普通MSE替代半MSE又保持相同$\lambda$，数据梯度相对惩罚翻倍；想比较严格等价的一步，先把数据损失统一，而不是只抄同一个学习率。

下面用线性标量损失构造固定数据梯度，**只检查一步机制，不是训练任务答案**：

```python
import torch

w0 = torch.tensor([2.0, -1.0], dtype=torch.float64)
g = torch.tensor([0.5, -0.5], dtype=torch.float64)
eta, lam = 0.1, 0.2
w_loss = w0.clone().requires_grad_()
w_opt = torch.nn.Parameter(w0.clone())
objective = (w_loss * g).sum() + lam * w_loss.square().sum() / 2
objective.backward()
with torch.no_grad():
    w_loss -= eta * w_loss.grad
opt = torch.optim.SGD([w_opt], lr=eta, weight_decay=lam, momentum=0)
(w_opt * g).sum().backward()
opt.step()
print(w_loss.detach(), w_opt.detach())
# 两边解析预期均为[1.91, -0.93]。
```

## 4. 参数分组决定“谁被拉回零”

对所有`model.parameters()`统一设置`weight_decay`，不会自动排除偏置。若实验约定只衰减权重，应显式为权重和偏置建立不同参数组；每个参数恰好出现一次，偏置组衰减为0。此处先掌握这一规则，后续遇到归一化层时再明确其参数策略，不把某套经验当成全网络通则。

为什么偏置可能不惩罚？在线性回归里，平移所有标签会主要改变截距；惩罚截距意味着同时偏好输出靠近0，这与“限制输入敏感度”不是同一件事。并非禁止惩罚偏置，而是需要把建模选择写清楚。

日志建议拆成三个量：训练数据损失$L_B$、惩罚值$\lambda\|w\|^2/2$、总目标$J_B$；验证曲线使用相同定义的数据损失。否则加大$\lambda$后总目标上升，不能据此断言预测变差。模型选择仍看验证指标，不看权重是否足够小。

## 5. 不把SGD结论外推给Adam和AdamW

这是必要的API边界补充，不要求读额外论文或在本讲实现优化器。

在PyTorch 2.5中：

- `Adam(weight_decay=lam)`把$\lambda w$加到梯度，再参与一阶、二阶矩估计与自适应缩放。惩罚不再表现为所有坐标统一乘$1-\eta\lambda$。
- `AdamW(weight_decay=lam)`把权重衰减与自适应梯度更新分开，衰减不混入梯度矩估计。
- 所以“Adam+L2”和“AdamW衰减”不是换个类名就数值相同，不能直接复用调好的强度并承诺相同结果。

一个不需要完整Adam公式的反例直觉：若某优化步骤先给梯度每个坐标乘不同系数$a_j$，加L2后坐标更新含$-\eta a_j\lambda w_j$；统一衰减则含$-\eta\lambda w_j$。只要$a_j$不同，这两个操作就不相同。Adam还会让这些系数依赖历史，因此差异不仅在当前一步。

## 6. 工程排查与自测

发现“正则化没用”时，先问：验证划分是否独立？数据损失的mean/sum是否统一？是否正则了同一批参数？是否重复添加？训练预算和学习率是否改变？最后才讨论该任务是否需要更强或更弱的约束。

<details>
<summary>若数据梯度为零，w=2、学习率0.1、lambda=0.2，下一步是多少？能否推出有数据梯度时范数也总下降？</summary>

下一步为$(1-0.02)2=1.96$。不能推出总下降，因为数据梯度可能把参数推离零。

</details>

<details>
<summary>把半MSE改成普通MSE，怎样保持整个目标仅放大两倍？</summary>

数据项翻倍，惩罚系数也应翻倍，得到$J'=2J$。对普通SGD若还想保持相同一步更新，再把学习率减半。只改其中一项不算严格等价；此推理不直接外推到自适应优化器。

</details>

<details>
<summary>训练误差增加、验证误差降低，是否说明权重衰减失败？</summary>

不是。它可能牺牲训练拟合来改善留出预测；应在公平的指标口径下比较验证性能，同时关注重复实验波动。若两边都明显变差，可能过强或还有优化问题。

</details>

<details>
<summary>L2能修复标签泄漏、错误切分或计算溢出吗？</summary>

不能把它当作这些问题的修复。先恢复正确的数据权限与数值计算，再评估正则化；不要靠调lambda掩盖流水线错误。

</details>

## 来源、版本与视频覆盖边界

- 全文审阅[固定源码4.5 权重衰减](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_multilayer-perceptrons/weight-decay.md)，含练习，重点核对PyTorch从零实现、广播与归约、简洁实现参数组。它是当前中文第二版固定源码，非2021教材快照。未运行20样本/200特征的教材实验，未声称复现书中曲线。
- 编者API补充：PyTorch2.5的[SGD](https://pytorch.org/docs/2.5/generated/torch.optim.SGD.html)、[Adam](https://pytorch.org/docs/2.5/generated/torch.optim.Adam.html)、[AdamW](https://pytorch.org/docs/2.5/generated/torch.optim.AdamW.html)，已读各自更新伪代码、参数及相关说明，未审阅全部状态钩子API或论文。这里不新增论文阅读任务。
- [原视频](https://www.bilibili.com/video/BV1UK4y1o7dy)：平台标题《12 权重衰退【动手学深度学习v2】》，作者“跟李沐学AI”，发布于2021-04-17 17:26:29 UTC（北京时间次日01:26:29）。2026-11-13核实全部分P；保留平台“衰退”标题，不据此改写课程术语。

| P | 平台标题 | cid | 时长（秒） | 公开player字幕 |
| --- | --- | --- | --- | --- |
| 1 | 权重衰退 | 325655483 | 782 | 请求成功，空列表 |
| 2 | 代码实现 | 325680074 | 754 | 请求成功，空列表 |
| 3 | QA | 325655537 | 695 | 请求成功，空列表 |

此表不是讲授时间线。未下载/观看媒体、未取得字幕，不能核实课堂代码或QA；中文原课通过页头观看，本课不另作课堂逐段整理；不编造时间码。空列表不证明其他字幕形式不存在，未重复请求。必要定位已在本页，`materials=not_required`。

教材`.txt`、精简视频元数据、逐项清单在`sources/p2-lec12/`。根Apache-2.0、setup包MIT-0字段均不外推视频；平台copyright=1/no_reprint=0，0也不代表开放许可。一步普通SGD片段CPU核对通过，两条路线均输出`[1.91,-0.93]`，见`sources/p2-shared/notes-smoke.json`；不代表高维回归、Adam/AdamW或完整学生作业已经执行。
