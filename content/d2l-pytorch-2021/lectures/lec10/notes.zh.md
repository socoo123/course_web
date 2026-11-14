---
draftStatus: "not_required_by_user"
title: "感知机与MLP：非线性不是多写一个Linear"
lectureId: lec10
source: "中文第二版4.1–4.3固定源码全文，PyTorch分支；提交e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照。感知机算法与XOR证明为明确标注的编者解释，不伪称教材独立章节或课堂内容。"
video: "https://www.bilibili.com/video/BV1hh411U7gn"
license: "教材仓库Apache-2.0，不外推视频。视频copyright=1/no_reprint=1，未发现开放转载许可；算例与SVG为编者自拟。"
status: "教材导读/编者笔记；4P公开字幕均为空，未观看视频。两种MLP实现共用P3原样保留，内容映射未核实，课堂逐段整理不另作。2个独立代码块CPU核对通过，不代表MLP训练通过。"
kind: "教材导读 / 编者笔记"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
acquiredOn: "2026-11-13"
codeExecution: "2个代码块CPU核对通过，见sources/p2-shared/notes-smoke.json；未运行教材Notebook或完整MLP训练。"
---

# 感知机与MLP：非线性不是多写一个Linear

## 1. 感知机：先理解一条分界线能做什么

**本节为编者解释。** 原课表单列“感知机”，但没有给这一行独立教材链接；已读的4.1主要讲MLP、隐藏层与激活。这里用自拟公式与小例补足概念，不声称它们出现在尚未审阅的视频里，也不增设一篇必读论文。

二分类标签用$y\in\{-1,+1\}$，分数为$s=w^\top x+b$。设预测规则为$s>0$判正，否则判负；$s=0$时本页固定判负，但训练时将边界样本也视为需要处理的样本。分界面$s=0$在二维是直线，在高维是超平面。

**经典感知机更新的一种约定：**当$ys\leq0$时，执行

$$
w\leftarrow w+\eta yx,\qquad b\leftarrow b+\eta y;
$$

其余情况不更新。$ys$是带符号间隔：正数表示方向正确，负数表示方向错误，0在边界。感知机并不输出校准概率，也不是把离散的`sign`函数拿去普通反向传播；它有显式纠错更新。若使用$\max(0,-ys)$作感知机损失，在严格误分类处求导可得到这个方向，零点采用上述更新约定。

手算：$x=[2,-1],y=+1,w=[0,0],b=0,\eta=0.5$。边界触发更新后$w=[1,-0.5],b=0.5$，新分数为3。更一般地，这一次更新让当前样本的带符号间隔增加：

$$
y(s_{\mathrm{new}}-s_{\mathrm{old}})
=\eta(\|x\|^2+1)>0.
$$

它纠正的是当前样本方向，可能同时影响其他样本。线性可分、有限训练集等条件下的感知机收敛结论，**不意味着任意带噪数据都能分开，也不意味着得到最大间隔或最优概率**。工程上遇到永不停止的误分类，先检查模型的表达限制和标签冲突，不要只把轮数加大。

## 2. XOR：不是学习率没调好，而是模型做不到

自拟异或任务：输入只有两个0/1特征，恰好一个为1时标签为1。

| $x_1$ | $x_2$ | XOR标签 |
| --- | --- | --- |
| 0 | 0 | 0 |
| 1 | 0 | 1 |
| 0 | 1 | 1 |
| 1 | 1 | 0 |

假设单个仿射分数$s=a x_1+c x_2+b$能按上一节规则分类。两个正例要求$a+b>0,c+b>0$，相加得到$a+c+2b>0$。两个负例要求$b\leq0,a+c+b\leq0$，相加却得到$a+c+2b\leq0$，矛盾。

这不是训练失败的统计观察，而是对这四个点的直接证明。增加单层线性模型训练轮数、改变SGD学习率，都不能解除表达能力的限制。

![两层线性仍可合并，加入ReLU后可构造XOR特征](assets/nonlinearity-xor.svg)

图：编者自绘。下方两个隐藏特征分别检测$x_1>x_2$与$x_2>x_1$的部分；它们相加在四个布尔输入上恰好得到XOR。

## 3. 只有层数，没有非线性，仍是一个仿射模型

用$N,d,h,C$分别表示批大小、输入维数、隐藏宽度、输出数。没有激活时：

$$
H=XW_1+b_1,\qquad Z=HW_2+b_2.
$$

把第一式代入第二式：

$$
\begin{aligned}
Z&=X(W_1W_2)+(b_1W_2+b_2)\\
 &=XW_{\mathrm{eff}}+b_{\mathrm{eff}}.
\end{aligned}
$$

$W_1:(d,h)$乘$W_2:(h,C)$得到$(d,C)$，偏置也能合并。即使有很多层，只要中间全是仿射操作，输出仍是输入的仿射函数。参数化和优化过程可以不同，但不会因此表示XOR；当隐藏宽度很窄时，还可能给合并矩阵加上秩的限制。

加非线性后：

$$
\begin{aligned}
A&=XW_1+b_1,\\
H&=\phi(A),\\
Z&=HW_2+b_2.
\end{aligned}
$$

$\phi$在隐藏层按元素作用。对ReLU，输入空间被不同“哪些单元大于0”的模式分区；每一区域内是仿射函数，整体却可以形成折线/折面。**不是层数这个数字制造能力，而是可学习变换与非线性的组合。** 输入层不含可训练计算；一个隐藏层加一个输出层，通常叫两层网络。

## 4. 用两颗ReLU构造一个可手算的XOR

令

$$
\begin{aligned}
h_1&=\operatorname{ReLU}(x_1-x_2),\\
h_2&=\operatorname{ReLU}(x_2-x_1),\\
q&=h_1+h_2.
\end{aligned}
$$

在这四个0/1点上，$q$依次为$0,1,1,0$。按$q>0.5$判断类别就得到XOR。对于任意实数输入，这个函数实际是$|x_1-x_2|$，**并不是声称所有实数都有同一种布尔XOR语义**。

```python
import torch

X = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
W1 = torch.tensor([[1.0, -1.0], [-1.0, 1.0]])
H = torch.relu(X @ W1)
score = H.sum(dim=1)
print(H.tolist())  # 解析预期：[[0,0], [1,0], [0,1], [0,0]]
print((score > 0.5).long().tolist())  # 解析预期：[0,1,1,0]
```

这段权重是人为设计的，只证明模型**可以表示**，不证明SGD从任意随机初值都能学到。通用近似的类似结论也有函数、区域、激活与宽度等条件；“存在一组好参数”不是“有限数据和有限优化预算一定找到”。

## 5. 激活函数：值的变化与梯度通道一起看

| 函数 | 定义/值域 | 导数 | 本讲要识别的风险 |
| --- | --- | --- | --- |
| ReLU | $\max(0,a)$，非负 | $a<0$时0，$a>0$时1 | 单元长期落在负半轴时，该路径梯度为0 |
| sigmoid | $\sigma(a)=1/(1+e^{-a})$，$(0,1)$ | $\sigma(a)(1-\sigma(a))$ | 绝对值很大时饱和，最大导数仅1/4 |
| tanh | $\tanh(a)$，$(-1,1)$ | $1-\tanh^2(a)$ | 两端同样饱和，零附近导数为1 |

ReLU在0不可导；教材约定此处用0，框架的具体原语在并列值处可能采用不同次梯度规则。手写`max`与内置ReLU做梯度对照时，不能只验证前向；避开折点检查一般机制，再单独解释折点约定。输入恰好为0并不罕见，不能用“浮点永远不会等于0”略过工程边界。

只补回本讲需要的链式法则。若损失反向传到隐藏层的梯度为$G_H$，则

$$
G_A=G_H\odot\phi'(A),\qquad
\nabla_{W_1}L=X^\top G_A.
$$

$\odot$表示逐元素相乘。对ReLU，门关闭的位置将这一条局部梯度通道归零，不等于整个网络所有参数都没梯度。输出层的logits通常不再经过ReLU：它们需要表达相对分数，直接交给稳定交叉熵。不要因为“网络应该有激活”就给每层结尾机械地加同一种函数。

## 6. Fashion-MNIST上的MLP：结构改变，训练协议不变

教材4.2/4.3使用784输入、256隐藏单元、10输出。形状链为：

| 对象 | 从零形状 | 高层对应 |
| --- | --- | --- |
| 输入图像 | `(N,1,28,28)` | `nn.Flatten()`后`(N,784)` |
| $W_1,b_1$ | `(784,256)`、`(256,)` | `Linear(784,256)`的weight为`(256,784)` |
| $A,H$ | `(N,256)` | 线性层后接`nn.ReLU()` |
| $W_2,b_2$ | `(256,10)`、`(10,)` | `Linear(256,10)`的weight为`(10,256)` |
| $Z$ | `(N,10)` | logits |
| $y$ | `(N,)` long | `CrossEntropyLoss`索引标签 |

参数总数为$784\times256+256+256\times10+10=203530$。单层softmax只有$784\times10+10=7850$个参数。增加模型能力也增加需要估计的自由度、计算和过拟合风险；不是“层数越多就一定更适合有限数据”。隐藏宽度是超参数，并非数学上必须是2的幂。

两实现的逐项对应：

- **从零**：自己维护$W_1,b_1,W_2,b_2$，写矩阵乘、偏置广播和激活。教材PyTorch分支使用`nn.Parameter`，不意味着必须手工写反向；仍用autograd和稳定交叉熵。
- **简洁**：`Sequential(Flatten, Linear, ReLU, Linear)`负责组合和参数注册，`net.parameters()`交给优化器。
- **相同部分**：数据划分、标签格式、损失归约、清梯度、反向、更新、评估规则。不要因为多一个隐藏层就重写一份互不一致的训练系统。
- **对照前提**：两层权重都要转置复制，偏置也要一致。教材简洁实现的初始化函数只改Linear权重；默认偏置不自动等于从零版的零偏置，所以独立照抄两段并不构成严格同起点对照。

### 一个局部梯度对照，不提供训练作业答案

用$2\to2\to1$微型网络，输出先当连续分数，仅用平方目标检查梯度接口；这不是Fashion-MNIST分类器。输入特意避开ReLU折点。

```python
import torch
from torch import nn

X = torch.tensor([[2.0, 0.0], [0.0, 2.0]])
W1 = nn.Parameter(torch.tensor([[1.0, -1.0], [-1.0, 1.0]]))
b1 = nn.Parameter(torch.zeros(2))
W2 = nn.Parameter(torch.ones(2, 1))
b2 = nn.Parameter(torch.zeros(1))
net = nn.Sequential(nn.Linear(2, 2), nn.ReLU(), nn.Linear(2, 1))
with torch.no_grad():
    net[0].weight.copy_(W1.T)
    net[0].bias.copy_(b1)
    net[2].weight.copy_(W2.T)
    net[2].bias.copy_(b2)
manual = torch.relu(X @ W1 + b1) @ W2 + b2
module = net(X)
manual.square().mean().backward()
module.square().mean().backward()
print(manual.flatten().tolist())  # 解析预期：[2, 2]
print(torch.allclose(manual, module))  # 解析预期：True
print(torch.allclose(W1.grad.T, net[0].weight.grad))  # True
print(torch.allclose(b1.grad, net[0].bias.grad))  # True
print(torch.allclose(W2.grad.T, net[2].weight.grad))  # True
print(torch.allclose(b2.grad, net[2].bias.grad))  # True
```

参数若只放进普通Python列表，不会因此自动注册到某个`nn.Module`；显式把参数列表交给优化器是一条路径，在模块内使用`Parameter`属性或子模块注册是另一条路径。不要一边前向用旧张量，一边优化器更新另一份参数。

也别把“权重乘0.01”随意放在创建需梯度叶张量之后：运算结果可能是非叶，`.grad`与优化器行为会不同。教材用`nn.Parameter`包装明确参数角色；独立实现也可以先得到初值，再启用求导。正常初始化和复制用`no_grad`，不靠`.data`绕过检查。

## 7. 如何判断问题在表达、训练还是评估

| 观察 | 先问的问题 |
| --- | --- |
| 线性模型在XOR上始终分不开 | 是不是表达能力根本不够，而非学习率问题？ |
| MLP与线性模型没有区别 | 是否漏了激活？训练数据范围内激活是否一直处于同一线性区域？ |
| 两实现前向一样、梯度不同 | 损失归约、权重布局、ReLU折点、梯度是否清零 |
| 隐藏层梯度长期为0 | 预激活是否全为负？是否被detach/no_grad切断？ |
| 深一点训练反而差 | 初始化尺度、梯度传播、优化难度；不能只归因于容量 |
| 训练好、验证差 | 数据量与模型容量、数据泄漏、正则化；接续泛化相关讲次 |

本讲的完成标志不是下载一个现成训练脚本，而是你能给每个张量标形状、证明两层线性可合并、解释一条梯度为何被ReLU截断，并独立接上上一讲的训练协议。完整MLP作业仍由学习者完成；AI可检查某个局部不变量，不代写全部实验。

## 8. 自测

1. 感知机更新为什么能提高当前被纠错样本的带符号间隔？是否保证其他样本也改善？
2. 两层线性含偏置时，合并后的权重和偏置分别是什么？
3. XOR自拟构造中，输入`[1,1]`的两个隐藏值是什么？为什么输出不是2？
4. `Linear(784,256)`的weight形状是什么？为何与手写$W_1$相反？
5. ReLU前向为0，是否一定说明参数没有任何梯度？
6. 手工构造XOR成功，能否证明随机训练一定成功？

<details>
<summary>展开答案与推理</summary>

1. 增量为$\eta(\|x\|^2+1)>0$；同一次参数改变可能损害其他样本，不保证全局逐步改善。
2. $W_1W_2$和$b_1W_2+b_2$。输入维到输出维仍是一次仿射变换。
3. 两个都是0；它们计算两个输入的差，不是直接复制两个输入，因此相加为0。
4. `(256,784)`；`Linear`计算`X @ weight.T + bias`，手写式是`X @ W1 + b1`。
5. 不能笼统这样说。该位置的局部路径可能被关掉，但同一参数在其他样本、其他路径上仍可能有贡献。
6. 不能。表达能力与优化可达性是两件事，初始化、数据与优化设置会影响训练。

</details>

## 来源、视频分P与缺口

- **教材依据**：《动手学深度学习》中文第二版，阿斯顿·张、李沐、扎卡里·C. 立顿、亚历山大·J. 斯莫拉。已读固定提交[4.1多层感知机](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_multilayer-perceptrons/mlp.md)、[4.2从零实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_multilayer-perceptrons/mlp-scratch.md)、[4.3简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_multilayer-perceptrons/mlp-concise.md)全文；实现说明取PyTorch和通用分支。当前源码不是2021课程教材快照；感知机算法、XOR矛盾证明及两颗ReLU例子是本文编者解释，非“已核实原课讲授”。
- **API定点依据**：已读PyTorch 2.5 [Linear](https://docs.pytorch.org/docs/2.5/generated/torch.nn.Linear.html)的权重布局、仿射公式与默认初始化；[CrossEntropyLoss](https://docs.pytorch.org/docs/2.5/generated/torch.nn.CrossEntropyLoss.html)的logits/target契约。它们不是新增必读论文。
- **许可边界**：[固定仓库LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)为Apache-2.0；setup包MIT-0字段不外推教材之外的素材，更不外推视频。未归档课堂媒体或截图，自绘图并非课堂画面。
- **视频身份**：[10 多层感知机 + 代码实现](https://www.bilibili.com/video/BV1hh411U7gn)，上传者“跟李沐学AI”，发布于2021-04-11 06:50:40（UTC+8），课表日期为4月10日。2026-11-13核实完整view页列表如下。

| 分P入口 | 实际元数据标题 | 时长 | 内容状态 |
| --- | --- | --- | --- |
| [P1](https://www.bilibili.com/video/BV1hh411U7gn?p=1) | 感知机 | 13分52秒（832秒） | 讲授未核实 |
| [P2](https://www.bilibili.com/video/BV1hh411U7gn?p=2) | 多层感知机 | 22分39秒（1359秒） | 讲授未核实 |
| [P3](https://www.bilibili.com/video/BV1hh411U7gn?p=3) | 代码实现 | 8分26秒（506秒） | 两实现的实际覆盖与边界未核实 |
| [P4](https://www.bilibili.com/video/BV1hh411U7gn?p=4) | QA | 26分48秒（1608秒） | 问答未核实 |

### 两种实现都链接P3：能得出什么，不能得出什么

原课表row021“[多层感知机的从零开始实现](https://www.bilibili.com/video/BV1hh411U7gn?p=3)”与row022“[多层感知机的简洁实现](https://www.bilibili.com/video/BV1hh411U7gn?p=3)”确实共用`?p=3`，两个入口均原样保留。真实页列表只有一个名为“代码实现”的P3，P4名为“QA”。这支持“原课表共用一个代码分P入口”的描述，**不能证明P3内两种实现都讲完了、各从何时开始，更不能凭顺序把简洁实现改成P4**。

全部4个cid的标准公开player请求均HTTP 200、业务码0，字幕列表为空。没有合法可核实的新字幕来源，未下载或观看音视频，不猜时间码、不编问答；空列表不证明不存在烧录字幕等其他情况。中文原课通过页头观看，本课不另作课堂逐段整理，materials为not_required、不另造重复阅读。视频`copyright=1/no_reprint=1`不是开放转录许可。审计证据在`sources/p2-lec10/video-metadata.json`及manifest；两个Python机制片段已在CPU核对输出与梯度对应关系，记录见`sources/p2-shared/notes-smoke.json`。完整MLP训练与教材Notebook未运行。
