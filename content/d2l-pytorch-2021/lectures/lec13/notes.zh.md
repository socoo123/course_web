---
source: "《动手学深度学习》中文第二版4.6全文，重点核对PyTorch分支；固定提交e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照；另读PyTorch2.5 Dropout API。"
video: "https://www.bilibili.com/video/BV1Y5411c7aY"
license: "教材仓库Apache-2.0不外推视频；视频copyright=1/no_reprint=0，0不代表开放许可，未取得开放转载许可。算例与图为编者自拟。"
status: "教材导读；3P公开字幕均为空，课堂未核实，draft阻塞；2个独立机制片段CPU核对通过，非Dropout网络训练。"
title: "Dropout：保持期望，不是保持每次输出"
lectureId: lec13
kind: "教材导读 / 编者笔记"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
codeExecution: "2个Python机制片段CPU核对通过，见sources/p2-shared/notes-smoke.json；未运行教材Dropout训练实验。"
---

# Dropout：保持期望，不是保持每次输出

## 1. 丢掉的是本次激活，不是永久删除参数

设一批隐藏表示$H\in\mathbb R^{B\times d}$：$B$是batch样本数，$d$是隐藏维度。普通逐元素Dropout在训练前向中生成同形状掩码$M$，暂时把部分激活置零。下一次前向重新采样，网络的参数数量、张量形状和可训练参数身份并没有因此变化。

为什么可能有用？后续层不能总依赖某一个隐藏激活出现，需要在不同扰动下仍给出有用预测。这是正则化的建模选择，不是“丢得越多越强”，也不是保证泛化提升的定理。若模型本来欠拟合，加入过强扰动可能更难学。

**本页$p$表示丢弃概率，$q=1-p$才是保留概率。** API名字相似时也要核对含义，不能把“keep probability”直接当作$p$传入。

## 2. 为什么保留下来的数要除以1-p

先固定一个激活$h$，让$M\sim\mathrm{Bernoulli}(q)$，即$M=1$的概率为$q$、$M=0$的概率为$p$。对$0\le p<1$，反向缩放Dropout（inverted dropout）定义为：

$$
\widetilde h=\frac{M}{q}h,
\qquad
\mathbb E[\widetilde h\mid h]=\frac{\mathbb E[M]}q h=h.
$$

“无偏”是指在**固定输入激活、对掩码取期望**的意义下，单个激活的平均值不变；一次前向没有义务等于原值。

自拟例子：$h=3,p=0.25,q=0.75$。训练输出以$1/4$概率为0、以$3/4$概率为4，期望为3。二阶矩为$12$，方差为$12-9=3$。一般地：

$$
\mathbb E[\widetilde h^2\mid h]=\frac{h^2}{q},\qquad
\operatorname{Var}(\widetilde h\mid h)=\frac{p}{1-p}h^2.
$$

所以增大$p$会增大扰动方差，不是只把一个向量“缩稀疏一点”。当$p$接近1，偶尔保留的激活会被放大很多，数值与优化都可能困难。

![固定激活经过不同掩码的输出、均值与推理恒等路径](assets/dropout-expectation.svg)

图为编者自拟解析分支，不是随机运行截图。三条概念必须同时记住：训练随机、训练已缩放、推理不再缩放。

### 期望不能随便穿过非线性网络

若后面紧接固定线性层$W\widetilde H+b$，可以把期望移到线性运算里面；但对于一般非线性函数$f$：

$$
\mathbb E[f(\widetilde h)]\ne f(\mathbb E[\widetilde h]).
$$

取刚才的$h=3,p=0.25$和自拟后续函数$f(z)=z^2$，训练分支的平均输出是12，而对不加Dropout的输入计算$f(3)$为9。因此推理时关闭Dropout，不代表精确求出了所有随机子网络最终输出的平均值；“集成直觉”不能冒充逐层非线性后的等式。

下面穷举这个标量的两个分支，而不是靠大量随机样本碰近似均值：

```python
import torch

values = torch.tensor([0.0, 4.0], dtype=torch.float64)
probs = torch.tensor([0.25, 0.75], dtype=torch.float64)
mean = (probs * values).sum()
variance = (probs * (values - mean).square()).sum()
second_moment = (probs * values.square()).sum()
print(mean.item(), variance.item(), second_moment.item())
# 解析预期：3.0 3.0 12.0。
```

## 3. 训练与推理，是行为开关；梯度是另一个开关

| 设置 | `nn.Dropout`行为 | 是否记录梯度 |
| --- | --- | --- |
| 模块`train()`，通常梯度模式 | 采样并缩放 | 若输入/参数需要梯度，通常记录 |
| 模块`eval()`，通常梯度模式 | 原样传递 | 仍可能记录 |
| 模块`train()`，`torch.no_grad()` | 仍采样并缩放 | 不记录该上下文的梯度 |
| 模块`eval()`，`torch.no_grad()` | 原样传递 | 不记录该上下文的梯度 |

`eval()`不会冻结参数，也不会代替`no_grad()`；`no_grad()`不会自动关闭Dropout。评估时两者通常配合使用，评估完继续训练要切回`train()`。模块模式会影响其已注册子模块，因此不要把Dropout临时写成一个不受父模块管理的新对象。

反向时掩码不是可学习参数；对固定的本次掩码，$\partial\widetilde h/\partial h=M/q$。被丢弃的激活在**这一条路径、这一次前向**不传梯度；这不等于对应参数本轮总梯度一定为零：其他样本、其他路径可能仍有贡献。下一轮重采样后，它也可能重新参与。

## 4. 边界要单独想，不能让公式除以零

| 情况 | 训练行为 | 推理行为 |
| --- | --- | --- |
| $p=0$ | 恒等映射，输入梯度系数1 | 恒等映射 |
| $0<p<1$ | $M\odot H/(1-p)$ | 恒等映射 |
| $p=1$ | 对有限输入全部置零，不执行除零 | 恒等映射 |

$p=1$是专门定义的边界，不满足对一般非零$h$的“输出期望等于$h$”。它也不是$p\to1$时缩放公式可直接代入的数值实现。在隐藏层把全部激活置零会切断该路径信号，但下游偏置或其他路径仍可能得到梯度。

下面用确定掩码检查局部导数，再用模块检查端点和评估行为。不实现完整Dropout网络，也不规定随机采样应输出哪几个元素：

```python
import torch

h = torch.tensor([2.0, -4.0], requires_grad=True)
mask = torch.tensor([1.0, 0.0])
y = h * mask / 0.5
y.sum().backward()
print(y.detach().tolist(), h.grad.tolist())
# 解析预期：[4.0, -0.0]（或0.0）与[2.0, 0.0]
x = torch.tensor([1.0, -2.0])
print(torch.nn.Dropout(0.0)(x).tolist())  # [1.0, -2.0]
print(torch.nn.Dropout(1.0)(x).tolist())  # 两个零，符号不作要求
layer = torch.nn.Dropout(0.75)
layer.eval()
print(layer(x).tolist())                # [1.0, -2.0]
# 不以随机种子替代统计机制解释。
```

## 5. 接进MLP时，先检查五个问题

1. **位置是否明确？** 本节教材在隐藏层ReLU之后使用Dropout，再交给下一层线性变换。普通Dropout保持$(B,d)$形状；没有删除矩阵列，不能拿它直接当作结构剪枝或计算加速。
2. **训练是否重复缩放？** `nn.Dropout`已完成训练期$1/(1-p)$缩放，推理再乘$q$会错误缩小信号；自己实现时也不能先缩放再调用模块。
3. **模式是否正确？** 手写函数若无条件采样，即使父模型调用`eval()`也未必有效；应由明确的训练标志控制。优先使用模块接口降低状态错误。
4. **掩码设备和dtype是否一致？** 教材从零例子用`torch.rand(X.shape)`构造CPU掩码，直接移植到其他设备可能不匹配。现代实现应围绕输入的设备与浮点类型构造掩码；本页只给CPU机制例，不宣称GPU/MPS兼容性已验证。
5. **训练曲线是否可比较？** 有Dropout的训练损失含扰动，验证损失通常不含。训练损失高于验证并不自动表示泄漏；在同一参数快照、`eval()`模式、相同预处理下重算两边，才适合讨论泛化差距。

随机种子用于复现一次试验，不用于保证“每次都丢恰好$p$比例”。有限张量的实际丢弃个数是随机的；输入原本有零，也不能仅靠输出零的数量准确估计掩码丢弃率。统计检查应选非零输入、报告样本数和误差容忍，而非要求有限样本平均恰好相等。

调$p$仍然要依靠独立验证集，固定数据划分、训练预算与其他超参数，记录多次试验波动。与L2叠加不保证收益相加，二者都过强可能造成欠拟合；本讲不把调参任务改成完整实验答案。

## 6. 自测

<details>
<summary>h=2，p=0.5时，输出分布、期望、方差分别是什么？</summary>

0和4各一半概率；期望2；二阶矩8；方差4。一次输出不可能等于2，但长期平均可以趋近2。

</details>

<details>
<summary>为什么同一个样本在eval()模式下不需要再乘0.5？</summary>

本页采用训练时已经除以保留概率的inverted dropout。推理恒等传递才能与该约定配套，再乘0.5是重复补偿。

</details>

<details>
<summary>p=1时“保持期望”的证明在哪一步失效？</summary>

$q=0$使$M/q$没有定义。实现必须单独全置零，此时非零输入的期望变成0。不能既要求全丢弃又要求保持非零期望。

</details>

<details>
<summary>使用no_grad()验证，却没有eval()，会发生什么？</summary>

不会记录反向图，但Dropout仍可能随机改变输出。验证不再是通常的确定性推理；若不是明确设计的随机推理实验，就是模式错误。

</details>

## 来源、版本与视频覆盖边界

- 全文审阅[固定源码4.6 暂退法](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_multilayer-perceptrons/dropout.md)，含概念、小结、练习，重点核对PyTorch掩码、两个边界分支、`self.training`和简洁模块实现。固定的是当前中文第二版，不是2021教材快照；未运行完整Fashion-MNIST实验。
- 已读[PyTorch2.5 Dropout API](https://pytorch.org/docs/2.5/generated/torch.nn.Dropout.html)正文、参数与形状说明，用于核对训练缩放和推理恒等。方差、非线性反例、模式表与固定掩码例为编者推演；不把教材提及的论文升级为必读，也未声称审阅论文原文。
- [原视频](https://www.bilibili.com/video/BV1Y5411c7aY)：《13 丢弃法【动手学深度学习v2】》，作者“跟李沐学AI”，发布于2021-04-17 18:25:49 UTC（北京时间次日02:25:49）。2026-11-13核实全部分P：

| P | 平台标题 | cid | 时长（秒） | 公开player字幕 |
| --- | --- | --- | --- | --- |
| 1 | 丢弃法 | 325656869 | 719 | 请求成功，空列表 |
| 2 | 代码实现 | 325657525 | 736 | 请求成功，空列表 |
| 3 | QA | 325666689 | 1492 | 请求成功，空列表 |

只核实时长和分P，不是课堂内容时间表。未下载或观看媒体，未核实讲授、演示和QA，不生成draft、时间码或占位文件。空字幕列表不排除烧录字幕或其他合法访问条件下字幕，未重复刷接口。必要阅读已在本页，`materials=not_required`。

证据在`sources/p2-lec13/`，原始教材只存`.txt`。根Apache-2.0与setup包MIT-0字段均不外推视频，平台copyright=1/no_reprint=0，0也不代表开放授权。两段机制代码CPU核对通过，涵盖期望、方差、掩码梯度及端点，见`sources/p2-shared/notes-smoke.json`；没有运行教材Dropout网络训练，图示不是训练结果。
