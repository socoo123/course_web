---
source: "《动手学深度学习》中文第二版自动微分；固定提交 e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照；另读PyTorch 2.5 API，链接见文末。"
video: "https://www.bilibili.com/video/BV1KA411N7Px"
license: "教材仓库Apache-2.0，不外推视频。视频copyright=1、no_reprint=1，未取得开放转载许可；本文自拟算例与自绘图。"
status: "教材导读/编者笔记；视频内容未核实，全部3P公开字幕列表为空；未生成draft。本页5个Python代码块已在共享CPU环境执行并核对梯度，非课堂演示复现。"
title: "自动求导：把梯度、计算图与训练状态分开"
lectureId: lec07
kind: "教材导读 / 编者笔记"
sourceBoundary: "已读固定提交中文教材自动微分全文及PyTorch 2.5指定API文档；未核实视频讲授、演示或QA。短例和图均为编者自拟。"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
textbookVersion: "当前中文第二版固定提交，非2021课程快照"
acquiredOn: "2026-11-13"
codeExecution: "5个独立代码块的实际输出与解析预期一致；见sources/p1-shared/notes-smoke.json，不代表已完成训练循环或学生作业。"
---

# 自动求导：把梯度、计算图与训练状态分开

## 1. 自动求导替你做什么，不替你做什么

上一讲把链式法则写成“沿路相乘、多路相加”。反向自动微分把它机械化：**前向时记录实际执行的运算关系，反向时传递局部导数，最终得到指定目标对参数的梯度。** 它不是有限差分，不会逐个扰动参数；也不是把Python程序变成一份符号推导。

对工程使用者，先记住三个不同对象：

| 对象 | 含义 | 由什么改变 |
| --- | --- | --- |
| 参数值，如 `x` | 当前模型状态 | 参数更新 |
| 计算图与反向所需中间值 | 这一次前向如何得到输出 | 重新前向；反向后通常释放已保存中间值 |
| 梯度缓冲，如 `x.grad` | 已累加的损失对参数的导数 | `backward()`累加；显式清零或设为`None` |

**清空梯度不等于重建计算图，反向传播也不等于更新参数。** 这句话能解释很多训练循环错误。

## 2. 一个能手算完的计算图

自拟两参数例子：$x=[1,2]$，$u=3x_0-x_1=1$，$L=u^2/2=0.5$。依链式法则：

$$
\nabla_xL=\begin{bmatrix}3u\\-u\end{bmatrix}
=\begin{bmatrix}3\\-1\end{bmatrix}.
$$

```python
import torch

x = torch.tensor([1.0, 2.0], requires_grad=True)
u = 3 * x[0] - x[1]
loss = 0.5 * u.square()
loss.backward()
print(x.grad)  # 解析预期：tensor([ 3., -1.])
```

只需要CPU与PyTorch；环境安装说明统一见[课程公共资料](#/c/d2l-pytorch-2021)的“环境与版本”。这里的独立小片段用于解释机制，不是阶段实验的完整实现。

| 张量 | 形状 | `requires_grad` | `is_leaf` | 反向后默认是否保存`.grad` |
| --- | --- | --- | --- | --- |
| `x` | `(2,)` | True | True | 是，`(2,)` |
| `u` | `()` | True | False | 否 |
| `loss` | `()` | True | False | 否 |

在这个例子里，`x` 是直接创建、需要求导的叶张量，没有创建它的 `grad_fn`；`u` 和 `loss` 有运算历史，是非叶张量。**非叶不保存`.grad`，不等于它没有参与求导。** 反向仍需经过它们传导梯度。学习调试若确实要保留某个中间张量的梯度，可在反向前调用其 `retain_grad()`；这不是训练循环的默认必需项。

普通反向默认将梯度累加到参与计算且 `requires_grad=True` 的叶张量；`requires_grad=False` 的输入也可能作为常量影响其他参数的梯度。要把求导开关设在前向之前，事后才打开不能追回已经丢失的运算历史。

![自动求导中参数、前向图、反向梯度和下一次迭代的关系](assets/autograd-lifecycle.svg)

图：编者自绘。图中的“释放”指反向所需的已保存中间数据通常被释放，不意味着Python中的输出变量立即消失。

## 3. 标量输出与向量输出：你到底想求谁的导数

标量损失只有一个目标。对实数、单元素输出，`backward()`可省略起始梯度，等价于从1开始反传；上例损失形状是 `()`。一个形状为 `(1,)` 的单元素张量也能使用这个隐式起点；**单元素**才是API判断的重要条件，不要只凭维数分类。

若 $y$ 有多个元素，单说“对 $y$ 求梯度”不够：你想让每个输出贡献多大？本讲沿用上一讲雅可比约定，$J_{ij}=\partial y_i/\partial x_j$。传入与输出同形状的种子 $v$，反向得到的是

$$
J^\top v=\nabla_x(v^\top y),
$$

这里将 $v$ 看作固定权重；这是向量—雅可比乘积的列向量写法，不是整张雅可比矩阵。

### 自拟向量例子

令 $y=[x_0^2,\,x_0x_1]$，$x=[2,3]$，则

$$
y=[4,6],\qquad
J=\begin{bmatrix}4&0\\3&2\end{bmatrix}.
$$

不同的反向种子，代表不同目标：

| 目标 | 种子 $v$ | 解析预期梯度 |
| --- | --- | --- |
| $y_0$ | $[1,0]$ | $[4,0]$ |
| $y_0+y_1$ | $[1,1]$ | $[7,2]$ |
| $(y_0+y_1)/2$ | $[0.5,0.5]$ | $[3.5,1]$ |
| $2y_0-y_1$ | $[2,-1]$ | $[5,-2]$ |

```python
import torch

x = torch.tensor([2.0, 3.0], requires_grad=True)
y = torch.stack((x[0].square(), x[0] * x[1]))
y.backward(torch.tensor([2.0, -1.0]))
print(x.grad)  # 解析预期：[5, -2]
```

`y.sum().backward()`等价于以全1为种子；`y.mean().backward()`还除以元素数。**两者不是无关紧要的写法差异**：梯度尺度不同，学习率与损失归约必须配套理解。直接对上述两个元素的 `y` 调用无参数 `backward()`会报错；框架不能替你猜目标。

## 4. 累积、清零与重新前向：三件事分别处理

下面继续使用第一例的 $L=(3x_0-x_1)^2/2$，但独立创建变量，可以单独执行。

```python
import torch

x = torch.tensor([1.0, 2.0], requires_grad=True)
for _ in range(2):
    loss = 0.5 * (3 * x[0] - x[1]).square()  # 每轮重新前向
    loss.backward()
print(x.grad)  # 解析预期：[6, -2]，两次梯度相加

x.grad = None
loss = 0.5 * (3 * x[0] - x[1]).square()      # 清梯度后仍要重新前向
loss.backward()
print(x.grad)  # 解析预期：[3, -1]
```

- `backward()`默认**相加，不是覆盖**。有意识地跨多个小批次累积可以有用，但要正确处理损失缩放；无意累积就是训练错误。
- `x.grad = None`移除当前梯度缓冲；下一次反向重新得到梯度。`x.grad.zero_()`把已有缓冲内容清成0，但首次反向前通常是 `None`，不能直接调用它。
- 优化器中的 `zero_grad(set_to_none=True)`是常见用法。`None`与全0对简单的再次反向都能避免旧值累加，但不完全相同：未参与该轮计算的参数可能保持 `None`，优化器通常跳过无梯度参数；0梯度则仍可能触发动量或权重衰减相关处理。不要把两者视为任何场景都等价。
- 一次普通反向后，像平方这样的操作所保存的中间值通常已释放。直接重复对同一个旧 `loss` 反向会报“second time”相关错误；把 `.grad` 清零不能修复它。
- 正常训练下一轮应**重新前向**，尤其在参数更新以后。`retain_graph=True`会保留更多内存，不应作为每轮例行“修复”；多次复用同一图是另一个有明确需求才使用的场景。

### 参数更新放在哪里

反向只写梯度。若自己展示一个更新步骤，应在反向之后、下次前向之前，用 `no_grad` 更新已有叶参数，避免把优化器运算记入求导图。不要在正常记录模式下随手原地改动需梯度叶张量，也不要在反向前覆盖图保存的中间值。

本讲不提供完整训练循环；到后面的线性回归实践，再把“清梯度 → 前向 → 损失 → 反向 → 更新”接成完整过程。

## 5. `detach`：值留下，某条历史路径不再参与

自拟标量例子：$x=2$，先计算 $u=3x$。比较两种目标：

1. 不分离：$L=ux=3x^2$，梯度 $6x=12$。
2. 用 `u.detach()`作为常量：当前 $u$ 的数值是6，反向时目标局部视为 $L=6x$，梯度为6。

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
u = 3 * x
loss = u.detach() * x
loss.backward()
print(x.grad)  # 解析预期：6，而不是12
```

`detach()`没有修改原来的 `u`，也没有让所有涉及 `x` 的计算都失效；它只返回一个脱离原求导历史的张量，后续用它的路径不再追溯到 `u` 的创建过程。若要比较不分离的梯度，应另建变量或重新前向，并清除旧梯度。

**分离不是拷贝**：返回张量与原张量共享存储。原地改其中一个可能影响另一个，并破坏反向需要的值。需要独立数值快照时可使用 `detach().clone()`；只需切断梯度路径时，不要为了“保险”无条件额外复制。不要用 `.data`绕过自动求导检查。

## 6. `no_grad`：这一块运算不录入图

`detach`从一个已有张量切断历史；`torch.no_grad()`则让代码块内的普通张量运算不记录求导历史。

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
with torch.no_grad():
    fixed = 3 * x
loss = fixed * x  # 回到正常记录模式；x到loss的直接路径仍存在
loss.backward()
print(x.grad)    # 解析预期：6
```

这里 `fixed`由普通乘法产生，不需要梯度；`x`本身的 `requires_grad`没有被永久关闭。离开代码块后，新的正常运算仍可建图。带显式 `requires_grad` 参数的张量工厂有例外，不要把“块内所有对象都变成不求导”当成规则。

两者都可以有意阻断梯度；若误把训练前向整体包进 `no_grad()`，仅由该块产生的损失就无法按原路反传。另一方面，`model.eval()`只是切换某些层的训练/推理行为，**不等于关闭梯度**；评估时这两个开关各管一件事。

## 7. 动态图不意味着所有Python决定都可求导

教材演示了条件与循环。框架记录这一次实际执行的分支，因此不同输入、不同迭代可以产生不同图。它不自动对Python的分支选择条件求导，也不能使不可微的跳变变得可微。

把需要求导的值用 `.item()`变成Python数，再用这个数重新建张量，会丢失该路径的图。日志中读取标量值可以，别把读出来的Python数误接回训练损失并期待梯度自动恢复。

## 8. 排错表

| 现象 | 分析顺序 |
| --- | --- |
| `.grad`为`None` | 是否先开`requires_grad`？是不是叶？是否参与目标？路径是否经过detach/no_grad/Python数转换？ |
| 梯度比预期大一倍 | 是否重复反向未清零？目标是sum还是mean？同一参数是否有两条贡献路径？ |
| 非标量反向报错 | 明确要聚合的标量目标，或提供与输出匹配的反向种子 |
| 第二次反向失败 | 是否复用了旧图？重新前向，不靠清零梯度重建历史 |
| 梯度正确但参数没动 | 是否只有backward，没有参数更新？ |
| 原地修改相关报错 | 是否覆盖了反向需要保存的值，或直接修改需梯度叶张量？ |
| 数值梯度检查不通过 | 除代码外，也检查损失定义、有限差分步长和不可微点 |

## 9. 自测与答案

这些是编者概念题，不是官方实验答案。

1. 第一例在不更新参数的前提下，重新前向反向两次，且不清梯度，得到什么？若第二次前清为`None`呢？
2. 在向量例子中，为什么 `y.sum().backward()`不给出形状 `(2, 2)` 的雅可比？
3. 对 $x=2,u=3x$，`u*x`与`u.detach()*x`数值相同吗？梯度呢？
4. 已经计算出损失之后才给输入打开 `requires_grad`，能恢复历史吗？
5. 为什么 `loss.backward()`之后做 `x.grad = None`，再对旧损失反向仍可能报错？
6. `u.grad`为空是否说明 $u$ 的局部导数没有用到？

**答案**

1. `[6,-2]`；清梯度后为 `[3,-1]`。前向是否重建图、梯度是否累积是两个独立问题。
2. 它求的是一个标量 $y_0+y_1$ 对输入的梯度，即 $J^\top[1,1]$，形状与输入相同。
3. 数值都是12。梯度分别为12和6；分离改变的是求导路径，不是该次前向数值。
4. 不能，需要在开启后重新前向。
5. 旧图反向需要的保存数据可能已被释放；清梯度缓冲不会恢复它们。
6. 不是。默认只保留需梯度叶张量的`.grad`；中间梯度仍参与链式传递。

## 来源、视频分P与缺口

1. **教材导读依据**：阿斯顿·张、李沐、扎卡里·C. 立顿、亚历山大·J. 斯莫拉，《动手学深度学习》中文第二版，[自动微分固定源码](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_preliminaries/autograd.md)。已读全文；概念依据来自“一个简单的例子、非标量变量的反向传播、分离计算、Python控制流的梯度计算”，实现解读以PyTorch分支为准。当前固定提交不是2021快照。仓库许可见同提交 [LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)，不外推视频。
2. **编者API补充，不是视频指定阅读**：PyTorch维护者，[Autograd mechanics（2.5）](https://docs.pytorch.org/docs/2.5/notes/autograd.html)，已读并使用“How autograd encodes the history、Setting requires_grad、No-grad Mode、Evaluation Mode、In-place operations”相关内容。这里只补叶张量、图生命周期与禁用梯度，不把后面的复杂数/并发细节设为先修。
3. **编者API定位**：[Tensor.backward（2.5）](https://docs.pytorch.org/docs/2.5/generated/torch.Tensor.backward.html)，核对种子、累积与保留图参数；[Tensor.detach（2.5）](https://docs.pytorch.org/docs/2.5/generated/torch.Tensor.detach.html)，核对分离与共享存储；[Tensor.retain_grad（2.5）](https://docs.pytorch.org/docs/2.5/generated/torch.Tensor.retain_grad.html)，核对中间梯度保留；[Optimizer.zero_grad（2.5）](https://docs.pytorch.org/docs/2.5/generated/torch.optim.Optimizer.zero_grad.html)，核对None与零梯度差异；[no_grad（2.5）](https://docs.pytorch.org/docs/2.5/generated/torch.no_grad.html)，核对张量工厂例外。以上均已实际读取；短代码、自测与图为本文自拟，没有复制整段课堂演示。
4. **视频元数据**：[07 自动求导【动手学深度学习v2】](https://www.bilibili.com/video/BV1KA411N7Px)，上传者“跟李沐学AI”，发布于2021-03-22（北京时间，UTC+8）。2026-11-13实际查询view与全部cid的标准公开player接口，均成功，字幕列表均为空、`need_login_subtitle=false`。未观看、未下载音视频；无法核实课堂演示和QA。

| 分P | 元数据标题 | 时长 | 内容核实状态 |
| --- | --- | --- | --- |
| P1 | 自动求导 | 11分40秒（700秒） | 公开字幕列表为空；讲授未核实 |
| P2 | 自动求导实现 | 6分42秒（402秒） | 公开字幕列表为空；演示未核实 |
| P3 | 自动求导 QA | 6分5秒（365秒） | 公开字幕列表为空；问答未核实 |

上表只报告各文件时长，不是内容时间线；公开接口空列表不排除烧录字幕或其他访问条件下的字幕。视频标志为 `copyright=1`、`no_reprint=1`，没有发现开放转录/再发布授权。精简请求证据与教材原文存于 `sources/p1-lec07/`。没有可核实字幕，不生成draft或猜测时间码；所需API补充已定点引用，不另生成重复materials。
