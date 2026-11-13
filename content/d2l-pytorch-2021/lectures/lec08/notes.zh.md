---
title: "线性回归：让损失、梯度与一次更新对得上"
lectureId: lec08
source: "中文第二版3.1–3.3固定源码全文；提交e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照；实现解读以PyTorch分支为准。"
video: "https://www.bilibili.com/video/BV1PX4y1g7KC"
license: "教材仓库Apache-2.0；setup包MIT-0字段不替代根许可，均不外推视频。视频copyright=1/no_reprint=1，未发现开放转载许可。图与短例为编者自拟。"
status: "教材导读/编者笔记；5P公开字幕均为空，未观看视频，draft阻塞。2个独立代码块已在共享CPU环境执行，输出与解析预期一致；不是完整训练复现。"
kind: "教材导读 / 编者笔记"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
acquiredOn: "2026-11-13"
codeExecution: "2个代码块CPU核对通过，见sources/p2-shared/notes-smoke.json；未运行教材Notebook或完整学生作业。"
---

# 线性回归：让损失、梯度与一次更新对得上

## 1. 先分清四件事

线性回归不仅是拟合一条线，它是第一次把训练系统的四个接口接起来：**数据提供事实，模型给出预测，损失定义好坏，优化器改变参数**。自动求导只连接损失与梯度，不会自动选数据、学习率或停止条件。

| 接口 | 本讲约定 | 不负责什么 |
| --- | --- | --- |
| 数据 | 一行一个样本，特征`X`、连续标签`y` | 不把测试集变成训练集 |
| 模型 | `X @ w + b` | 不定义预测误差 |
| 损失 | 每个样本的半平方误差，再按实际样本数平均 | 不更新参数 |
| 优化器 | 朝负梯度方向走一步 | 不证明模型能泛化 |

权重与偏置是**参数**，通过数据更新；学习率、批量大小、训练轮数是**超参数**，由实验设计决定。先用CPU小矩阵解释一次更新，再进入[线性训练实践](#/c/d2l-pytorch-2021/lab/linear-training)。不需要另学一门优化课。

## 2. 符号和形状先落到纸面

用$N$表示这一批实际样本数，$d$表示每个样本的特征数。本页统一把回归标签保留为列矩阵，避免广播歧义。

| 对象 | 数学符号 | PyTorch形状 |
| --- | --- | --- |
| 特征 | $X$ | `(N, d)` |
| 权重 | $w$ | `(d, 1)` |
| 偏置 | $b$ | `(1,)` |
| 预测、标签、残差 | $\hat y,y,r$ | 均为`(N, 1)` |
| 平均损失 | $L$ | 标量`()` |

$$
\hat y=Xw+b,\qquad r=\hat y-y.
$$

例如$X$的两行分别是$[1,2]$和$[3,0]$，$w=[2,-1]^\top,b=1$，预测就是$[1,7]^\top$。偏置给每一行加同一个数，不是给每个样本训练一个独立偏置。

严格说，含偏置的模型是**仿射变换**；“线性回归”是习惯名称。这里的线性指对参数和当前特征的这种组合方式，不代表现实数据必须毫无噪声地落在直线上。

**最隐蔽的错误：**`(N, 1) - (N,)`会广播成`(N, N)`，把每个预测同所有标签相减，而不是逐样本比较。先确认样本顺序一致，再显式统一形状；不要靠`reshape`掩盖数据错位。

## 3. 半平方、平均、求和：三个缩放不能混为一谈

本页定义单样本损失和批损失为：

$$
\ell_i=\frac12(\hat y_i-y_i)^2,\qquad
L=\frac1N\sum_{i=1}^{N}\ell_i.
$$

$1/2$使求导后的系数更干净。独立同方差高斯噪声下，最小化平方误差也等价于最大化条件似然；这是一个建模解释，不是“任何数据噪声一定高斯”的事实。大残差被平方放大，因此离群标签会有很大影响。

| 写法（本讲单输出） | 损失 | 对预测的梯度 |
| --- | --- | --- |
| `0.5 * (pred-y).square().mean()` | $\frac1{2N}\sum r_i^2$ | $r_i/N$ |
| `nn.MSELoss()` | $\frac1N\sum r_i^2$ | $2r_i/N$ |
| `0.5 * (pred-y).square().sum()` | $\frac12\sum r_i^2$ | $r_i$ |

教材3.2的从零函数包含$1/2$，3.3的PyTorch `MSELoss`没有。它们可能有同一个最优点，但**相同初值、相同学习率下，一步更新并不相同**。要做严格对照，可统一使用`0.5 * MSELoss(...)`；或者只在纯SGD且其他设置一致时按比例调整学习率。不要把这条缩放关系不加条件地搬到带正则项或其他优化器的实验里。

另一个边界：`MSELoss(reduction='mean')`除以的是**全部元素数**。若将来预测形状是`(N, K)`，它除以$NK$，不是只除以$N$。先说清“一个样本多个输出”的损失如何归约，再比较结果。

## 4. 手算一次SGD，而不是先写一整页循环

链式法则给出：

$$
\nabla_wL=\frac{X^\top r}{N},\qquad
\frac{\partial L}{\partial b}=\frac1N\sum_i r_i.
$$

梯度指向局部增长最快的方向，梯度下降取负号：

$$
w\leftarrow w-\eta\nabla_wL,\qquad
b\leftarrow b-\eta\frac{\partial L}{\partial b}.
$$

自拟一维例子：两条记录$(x,y)=(1,2),(2,3)$，初值$w=b=0$，学习率$\eta=0.1$。

1. 预测$[0,0]$，残差$[-2,-3]$，$L=(4+9)/4=3.25$。
2. $\nabla_wL=(1\times(-2)+2\times(-3))/2=-4$，$\nabla_bL=-2.5$。
3. 更新后$w=0.4,b=0.25$，预测变为$[0.65,1.05]$。
4. 新损失为$(1.35^2+1.95^2)/4=1.40625$。

```python
import torch

X = torch.tensor([[1.0], [2.0]])
y = torch.tensor([[2.0], [3.0]])
w = torch.zeros((1, 1), requires_grad=True)
b = torch.zeros(1, requires_grad=True)
loss = 0.5 * (X @ w + b - y).square().mean()
loss.backward()
print(loss.item(), w.grad.item(), b.grad.item())  # 解析预期：3.25, -4, -2.5
with torch.no_grad():
    w -= 0.1 * w.grad
    b -= 0.1 * b.grad
    after = 0.5 * (X @ w + b - y).square().mean()
print(w.item(), b.item(), after.item())  # 约0.4, 0.25, 1.40625
```

这只是一个批次的一次机制检查，不是完整训练答案。若继续下一步，必须清空梯度并重新前向；不要重复反向旧损失。

![两条记录的一次更新，以及尾批次分母的区别](assets/sgd-normalization.svg)

图：编者自绘。上半部把公式对应到可手算的更新；下半部提醒批次的实际长度不是配置里的最大长度。

### 为什么不是每一步都降

- **全批量GD**：用整个训练集的梯度，每步计算多、方向确定；合适步长下可降低该训练目标。
- **单样本SGD**：每步只取一个样本，计算少、噪声大。
- **小批量SGD**：在二者之间折中；矩阵运算能利用批内并行，但批量变大不自动保证更好的泛化或更短总训练时间。

随机抽样或每轮打乱后分批能减少顺序偏差；不是说每一批都代表总体，更不是说每一次更新后全训练损失必须下降。学习率过大可能跨过低点甚至发散，过小会进展慢。特征单位差异巨大也会让同一步长难以兼顾各方向。

## 5. 尾批次：一个会悄悄改变学习率的细节

假设5条数据，配置`batch_size=2`，不丢尾批次，则一轮实际批大小依次为`2, 2, 1`。若最后一批的梯度**和**为$g$：

- 正确的实际批均值更新是$-\eta g/1$；
- 仍除配置值2，就变成$-\eta g/2$，缩小了一半。

教材3.2演示的1000条数据能被批大小10整除，所以直接传配置值没有暴露问题；迁移到任意样本数时，必须用当前`X.shape[0]`。

归一化只能做一次：

| 反向目标 | 更新器做什么 | 对应批均值SGD吗 |
| --- | --- | --- |
| `per_sample.sum()` | 除当前实际$N$ | 是 |
| `per_sample.mean()` | 不再除$N$ | 是 |
| `per_sample.mean()` | 又除$N$ | 否，额外缩小$N$倍 |

`drop_last=True`会改变一轮使用的数据，不是修补分母错误的办法。记录整轮损失时也应累加每批损失总和、最后除总样本数；直接平均批均值会让小尾批次获得过高权重。

## 6. 从零与简洁实现：同一张计算图，两套接口

| 职责 | 从零实现 | PyTorch组件 |
| --- | --- | --- |
| 数据迭代 | 打乱索引并切片 | `TensorDataset`、`DataLoader` |
| 参数 | 需梯度叶张量`w,b` | `nn.Linear(d, 1)`注册参数 |
| 前向 | `X @ w + b` | `layer(X)` |
| 损失 | 明确半平方与归约 | `criterion = nn.MSELoss()`，再取`0.5 * criterion(pred, y)` |
| 梯度 | `backward()` | 仍然是`backward()` |
| 更新 | `no_grad`中减去学习率乘梯度 | `torch.optim.SGD(...).step()` |
| 清梯度 | 设置为`None`或清零 | `optimizer.zero_grad()` |

`nn.Linear`保存的权重形状为`(out_features, in_features)`，计算$XA^\top+b$。因此本页手写的列权重$w$要转置后复制进去。初始化也必须一致：默认`Linear`的权重和偏置不是教材手写的“正态权重、零偏置”。只设随机种子而独立初始化两份模型，不足以证明两实现同起点。

```python
import torch
from torch import nn

X = torch.tensor([[1.0, 2.0], [3.0, 0.0]])
w = torch.tensor([[2.0], [-1.0]])
b = torch.tensor([1.0])
layer = nn.Linear(2, 1)
with torch.no_grad():
    layer.weight.copy_(w.T)
    layer.bias.copy_(b)
manual = X @ w + b
print(manual.flatten().tolist())  # 解析预期：[1, 7]
print(torch.allclose(manual, layer(X)))  # 解析预期：True
```

对照实验依次比**初始前向 → 相同损失 → 梯度 → 一次更新后参数**，不要只比较若干轮后都下降的曲线。线性回归是凸问题，但若特征列相关，参数最优解不一定唯一；教材中的逆矩阵公式要求设计矩阵满列秩。工程上不该把显式求逆当成所有回归问题的默认实现，本讲保留SGD是为了建立可迁移的训练流程。

## 7. 排错与独立练习

| 现象 | 优先检查 |
| --- | --- |
| 梯度恰好相差2倍 | 是否一边用了$1/2$，另一边用了原始MSE |
| 改批大小后步长巨变 | sum/mean、优化器是否重复除批长 |
| 训练很顺但误差矩阵巨大 | `pred.shape == y.shape`是否成立 |
| 只有最后一步变化异常 | 当前批长与配置批长是否不同 |
| 高层版结果对不上 | 权重转置、偏置初始化、样本顺序、损失归约 |
| 参数不动 | 是否漏掉更新、误用旧参数对象、训练前向关闭了求导 |

自己完成数据生成与完整循环；AI可帮你解释某个梯度或定位形状错位，不代写整份训练作业。先固定数据、种子与损失定义，再单独改变学习率或批大小，记录一次改动与可观察结果。

## 8. 自测

1. 两条记录的手算例若去掉$1/2$，初始损失和两个梯度各是多少？
2. 尾批次只有1条时，为什么`mean`之后不再除配置批大小？
3. `(4,1)`的预测与`(4,)`的标签相减得到什么？
4. 为什么两份代码都写`lr=0.03`，不能说明训练过程相同？
5. 训练集平方误差最低，是否意味着新数据误差也最低？

<details>
<summary>展开答案与推理</summary>

1. 损失6.5，梯度分别为$-8,-5$。极小点不变，一步更新的距离加倍。
2. `mean`已经按当前元素数归约；本讲单输出时就是实际样本数。再次相除改变了目标对应的步长。
3. `(4,4)`；每个预测被减去全部4个标签，属于错误的任务。
4. 还取决于初值、数据顺序、损失常数、sum/mean、尾批次及优化器设置。
5. 不意味着。模型可能拟合噪声，验证数据才帮助判断泛化；不能反复用测试集挑超参数。

</details>

## 来源、视频分P与缺口

- **教材依据**：阿斯顿·张、李沐、扎卡里·C. 立顿、亚历山大·J. 斯莫拉，《动手学深度学习》中文第二版，固定提交`e6b18ccea71451a55fcd861d7b96fddf2587b09a`。已读[3.1线性回归](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression.md)、[3.2从零实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-scratch.md)、[3.3简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-concise.md)全文，代码解释以PyTorch与通用分支为准；不是2021教材快照。基础SGD由3.1/3.2支撑，不冒称核实了视频优化算法段。
- **API定点补充**：已读PyTorch 2.5 [Linear](https://docs.pytorch.org/docs/2.5/generated/torch.nn.Linear.html)的公式、形状、默认初始化，及[MSELoss](https://docs.pytorch.org/docs/2.5/generated/torch.nn.MSELoss.html)的损失和归约定义。不是新增论文必读；没有另建重复materials。
- **许可**：[固定仓库LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)为Apache-2.0；setup包MIT-0字段单独记录，不外推视频、数据或第三方素材。本文为独立讲解与自拟短例。
- **视频身份**：[08 线性回归 + 基础优化算法](https://www.bilibili.com/video/BV1PX4y1g7KC)，上传者“跟李沐学AI”，发布于2021-03-28 08:51:25（UTC+8）；课表标注3月27日，二者不是同一种日期，不改历史课表。

| 分P入口 | 实际元数据标题 | 时长 | 已核实边界 |
| --- | --- | --- | --- |
| [P1](https://www.bilibili.com/video/BV1PX4y1g7KC?p=1) | 线性回归 | 14分57秒（897秒） | 元数据；非内容时间线 |
| [P2](https://www.bilibili.com/video/BV1PX4y1g7KC?p=2) | 基础优化算法 | 8分24秒（504秒） | 元数据；非内容时间线 |
| [P3](https://www.bilibili.com/video/BV1PX4y1g7KC?p=3) | 线性回归的从零开始实现 | 15分20秒（920秒） | 演示未核实 |
| [P4](https://www.bilibili.com/video/BV1PX4y1g7KC?p=4) | 线性回归的简洁实现 | 6分42秒（402秒） | 演示未核实 |
| [P5](https://www.bilibili.com/video/BV1PX4y1g7KC?p=5) | QA | 24分21秒（1461秒） | 问答未核实 |

2026-11-13查询view及全部5个cid的标准公开player接口：均HTTP 200、业务码0，字幕列表为空；未重复刷空接口，未下载或观看媒体，未绕登录/风控。空列表不排除烧录字幕或其他访问条件下的字幕。因此没有真实课堂时间轴、演示核验或问答整理，draft保持阻塞且不创建占位。`copyright=1/no_reprint=1`不是开放授权。源快照、请求摘要与代码清单见`sources/p2-lec08/`；本页两个独立代码块CPU核对通过，输出见`sources/p2-shared/notes-smoke.json`，不代表完成回归训练作业。
