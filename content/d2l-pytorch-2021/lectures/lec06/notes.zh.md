---
draftStatus: "not_required_by_user"
source: "《动手学深度学习》中文第二版微积分；固定提交 e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照；完整链接见文末。"
video: "https://www.bilibili.com/video/BV1eZ4y1w7PY"
license: "教材仓库Apache-2.0，不外推视频。视频copyright=1、no_reprint=1，未取得开放转载许可；本文自拟算例与自绘图。"
status: "教材导读/编者笔记；视频内容未核实，全部2P公开字幕列表为空；中文原课通过页头观看，本课不另作课堂逐段整理。有限差分片段、线性层梯度与小步更新数值已在共享CPU环境核对，非课堂复现。"
title: "矩阵计算与微积分：从变化率走到梯度形状"
lectureId: lec06
kind: "教材导读 / 编者笔记"
sourceBoundary: "已读固定提交中文教材微积分全文；未核实视频讲授与QA。例子、推导组织与图为编者自拟，不是课堂复述。"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
textbookVersion: "当前中文第二版固定提交，非2021课程快照"
acquiredOn: "2026-11-13"
codeExecution: "本页1个Python代码块及指定解析例已核对；输出见sources/p1-shared/notes-smoke.json。"
---

# 矩阵计算与微积分：从变化率走到梯度形状

## 学完应能回答什么

给你一个标量损失和一组参数，你应能说清：**改变哪个量、其余哪些量固定、梯度有多大、梯度形状是什么，以及它如何沿运算链传回去。** 这里不要求先学完整微积分，也不要求读论文。

阅读顺序是变化率 → 偏导 → 梯度 → 形状 → 链式法则。公式中的实数向量都按列向量理解；代码里的 `(n,)` 是一维张量，不自带“行/列”方向。

## 1. 变化率：先比较，再让步长变小

自拟函数 $f(x)=x^2+x$，在 $x=2$ 时，$f(2)=6$。把输入增加 $h$：

$$
\frac{f(2+h)-f(2)}h=5+h.
$$

| 步长 $h$ | 平均变化率 | 与瞬时变化率5的差 |
| --- | --- | --- |
| 0.1 | 5.1 | 0.1 |
| 0.01 | 5.01 | 0.01 |
| 0.001 | 5.001 | 0.001 |

这些是代数展开得到的值，不是程序输出。导数就是这个平均变化率在 $h\to0$ 时的极限：$f'(2)=5$。因此，小扰动 $\Delta x=0.01$ 会让输出约增加 $5\times0.01=0.05$；实际增加 $0.0501$，多出的 $0.0001$ 是这次线性近似忽略的二次项。

一般形式是：

$$
f(x+\Delta x)\approx f(x)+f'(x)\Delta x.
$$

**导数不是函数值，也不是“输入增加1以后输出必定增加多少”。** 它描述当前点附近、足够小变化下的比例。

本讲先够用的规则：常数导数为0，$x^2$ 的导数为 $2x$；常数倍可提出；和的导数逐项相加；乘积必须两项都求导：$(uv)'=u'v+uv'$。

### 有限差分是检查工具，不是自动求导的工作原理

中心差分同时向两侧试探：

$$
f'(x)\approx\frac{f(x+h)-f(x-h)}{2h}.
$$

下面是自拟的独立检查片段，不是课程实验答案：

```python
def f(x):
    return x * x + x

x, h = 2.0, 1e-4
forward = (f(x + h) - f(x)) / h
central = (f(x + h) - f(x - h)) / (2 * h)
print(forward, central)  # 解析预期：约5.0001、5.0，不保证末位完全相同
```

步长不是越小越好：大步长不够局部，过小又会使两个接近的浮点数相减，放大舍入影响。查错时可改变几个数量级的 $h$，用双精度，在光滑点比较趋势。不要在不可微拐点上要求有限差分等于框架选定的梯度。

## 2. 偏导：一次只动一个旋钮

设标量损失 $L(a,b)=a^2+ab+2b^2$。求 $\partial L/\partial a$ 时，**把 $b$ 固定**：

$$
\frac{\partial L}{\partial a}=2a+b,\qquad
\frac{\partial L}{\partial b}=a+4b.
$$

在 $(a,b)=(1,2)$ 处，$L=11$，两个偏导分别为4和9。若同时作小变化，便有：

$$
\Delta L\approx4\Delta a+9\Delta b.
$$

“偏”不是近似的意思，而是明确**只对哪一个自变量变化**。若 $b$ 又是 $a$ 的函数，就不能把总变化误写成上述单个偏导；那需要后面的链式法则。

## 3. 梯度：把所有旋钮的敏感度排在一起

把参数写成 $\mathbf{x}=[a,b]^\top$，则

$$
\nabla_{\mathbf{x}}L=
\begin{bmatrix}\partial L/\partial a\\\partial L/\partial b\end{bmatrix}
=\begin{bmatrix}4\\9\end{bmatrix}.
$$

一阶变化是点积 $\Delta L\approx(\nabla L)^\top\Delta\mathbf{x}$。在欧氏长度约束下，梯度方向是局部最陡上升方向，负梯度是局部最陡下降方向。于是一个小步长更新可写为 $\mathbf{x}_{\rm new}=\mathbf{x}-\eta\nabla L$。

例如 $\eta=0.01$ 时得到 $(0.96,1.91)$，解析计算新损失为 $10.0514$，一阶预测为 $11-0.01(4^2+9^2)=10.03$。二者不完全相同是正常的；**步长过大不保证下降，训练损失下降也不保证泛化变好。**

## 4. 先写形状，再写矩阵公式

标量损失对参数张量的梯度，与参数张量具有相同形状：每个参数位置对应一个敏感度。

| 参数 / 输出 | 导数对象 | 数学形状 |
| --- | --- | --- |
| $x\in\mathbb R$，$L\in\mathbb R$ | $dL/dx$ | 标量 |
| $\mathbf{x}\in\mathbb R^n$，$L\in\mathbb R$ | $\nabla_{\mathbf{x}}L$ | $n$维列向量 |
| $W\in\mathbb R^{m\times n}$，$L\in\mathbb R$ | $\nabla_WL$ | $m\times n$ |
| $\mathbf{x}\in\mathbb R^n$，$\mathbf{y}\in\mathbb R^m$ | 雅可比 $J_{ij}=\partial y_i/\partial x_j$ | $m\times n$ |

这里明确采用“输出分量为行、输入分量为列”的雅可比约定。因此 $\mathbf{y}=A\mathbf{x}$ 时 $J=A$，反向传播标量损失时才有 $\nabla_{\mathbf{x}}L=A^\top\nabla_{\mathbf{y}}L$。教材以 $\nabla_{\mathbf{x}}A\mathbf{x}=A^\top$ 记向量导数，采用了另一布局；**不要在没有写明约定时把两个式子判成互相矛盾，更不要把向量输出的导数当成一个普通梯度向量。**

### 自拟线性层：转置从哪里来

令

$$
A=\begin{bmatrix}1&2\\-1&3\end{bmatrix},\quad
\mathbf{x}=\begin{bmatrix}2\\1\end{bmatrix},\quad
\mathbf{y}=A\mathbf{x}=\begin{bmatrix}4\\1\end{bmatrix},\quad
L=\tfrac12\mathbf{y}^\top\mathbf{y}=8.5.
$$

有 $\nabla_{\mathbf{y}}L=\mathbf{y}$，于是

$$
\nabla_{\mathbf{x}}L=A^\top\mathbf{y}
=\begin{bmatrix}3\\11\end{bmatrix}.
$$

若 $A$ 也可训练，$\partial L/\partial A_{ij}=y_i x_j$，所以

$$
\nabla_A L=\mathbf{y}\mathbf{x}^\top
=\begin{bmatrix}8&4\\2&1\end{bmatrix}.
$$

形状检查：$(2\times2)^\top(2\times1)$ 得到 $(2\times1)$；$(2\times1)(1\times2)$ 得到 $(2\times2)$。一般情况下，输入 $n$ 维、输出 $m$ 维，也完全相同。

## 5. 链式法则：沿路相乘，多路相加

自拟计算 $u=a+2b$，$L=u^2/2$。在 $a=1,b=2$ 时，$u=5$，因此

$$
\frac{\partial L}{\partial a}=
\frac{dL}{du}\frac{\partial u}{\partial a}=5\times1=5,\qquad
\frac{\partial L}{\partial b}=5\times2=10.
$$

![从两个参数到标量损失的前向与反向关系](assets/gradient-chain.svg)

图：编者自绘。前向求值；反向把“下游敏感度”乘上“当前局部变化率”，不需要把整个复合函数先展开。

若同一个变量通过多条路径影响损失，路径贡献要相加。例如 $u=x^2,v=3x,L=u+v$，有 $dL/dx=2x+3$，不是 $(2x)\times3$。写成一般式：

$$
\frac{\partial L}{\partial x_j}
=\sum_i\frac{\partial L}{\partial u_i}\frac{\partial u_i}{\partial x_j},
\qquad \nabla_{\mathbf{x}}L=J^\top\nabla_{\mathbf{u}}L.
$$

下一讲的反向自动微分，就是让框架沿实际执行的计算图完成这个过程。它不是用极小步长反复扰动每一个参数，也不是自动替你选择正确的损失。

## 6. 常见错误与排查顺序

| 症状 / 误解 | 先检查什么 |
| --- | --- |
| 把函数值当梯度 | 分开列出“当前输出”和“输入微变的输出变化率” |
| 求偏导时把其他独立变量也改了 | 明确固定量；有关联的量用链式法则 |
| 只乘导数、不加分支 | 同一个参数是否走了多条通往损失的路径 |
| 矩阵求导背出一个转置却乘不起来 | 先定义雅可比布局，再检查输入、输出与梯度形状 |
| 对 $x^\top A x$ 永远写 $2Ax$ | 一般是 $(A+A^\top)x$，只有对称 $A$ 才能这样化简 |
| 有限差分不匹配就断定公式错 | 查步长、精度、不可微点，以及扰动的是不是同一变量 |

## 7. 自测与答案

这些是编者概念自测，不是官方教材习题或阶段实验代答。先遮住答案。

1. $f(x)=x^2+x$ 在 $x=2$ 处，$\Delta x=-0.02$，一阶预测输出变化多少？
2. $L(p,q)=pq+q^2$ 在 $(2,-1)$ 的梯度是什么？
3. $W$ 形状为 `(3, 2)`，输入为 `(2,)`，输出为 `(3,)`。标量损失对 $W$ 的梯度形状是什么？输出对输入的雅可比形状呢？
4. $u=2x,v=x^2,L=uv$，在 $x=1$ 处的导数是多少？
5. 为什么用同一个很小 $h$ 检查百万参数不适合充当日常训练的求导方法？

**答案**

1. $5\times(-0.02)=-0.1$；实际变化 $-0.0996$，近似误差来自二次项。
2. $[q,p+2q]^\top=[-1,0]^\top$。第二个分量为0不代表损失不依赖 $q$，仅说明该点的一阶变化率为0。
3. `(3, 2)` 与 `(3, 2)`，但含义不同：前者每个参数一个数，后者每个输出—输入对一个数。
4. 两条路径：$v\cdot2+u\cdot2x=2+4=6$，也可由 $L=2x^3$ 得到。
5. 每个参数需要额外函数求值，且有步长与浮点误差问题。反向自动微分复用计算图与链式法则；有限差分适合小规模抽查。

## 来源、视频分P与缺口

- **教材导读依据**：阿斯顿·张、李沐、扎卡里·C. 立顿、亚历山大·J. 斯莫拉，《动手学深度学习》中文第二版，[微积分固定源码](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_preliminaries/calculus.md)，已读“导数和微分、偏导数、梯度、链式法则”及小结/练习。中文原书不再翻译；本文另换例子、按工程形状补讲，不复制绘图工具代码。
- 版本边界：本次固定的是当前仓库提交，不是2021录像所用教材快照。仓库许可见同提交 [LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)，不据此授权转载视频。
- **视频元数据**：[06 矩阵计算【动手学深度学习v2】](https://www.bilibili.com/video/BV1eZ4y1w7PY)，上传者“跟李沐学AI”，发布于2021-03-22（北京时间，UTC+8）。2026-11-13实际查询view与每个cid的标准公开player接口，均成功；所有P字幕列表为空、`need_login_subtitle=false`。这只是公开接口的观测，不证明不存在烧录字幕或其他访问条件下的字幕。未观看音视频，未整理QA。

| 分P | 元数据标题 | 时长 | 内容核实状态 |
| --- | --- | --- | --- |
| P1 | 矩阵计算 | 12分38秒（758秒） | 无可取得的公开字幕；未核实讲授 |
| P2 | 矩阵计算 QA | 1分57秒（117秒） | 无可取得的公开字幕；未核实问答 |

上表是文件级元数据，不是主题时间轴；本笔记没有猜测视频片段起止时间。视频标志 `copyright=1`、`no_reprint=1` 不提供开放再利用许可，因此不生成课堂长篇转录。原始教材文本及精简请求证据保存在 `sources/p1-lec06/`。没有额外必要的独立阅读，故不生成重复的 materials；中文原课通过页头观看，本课不另作课堂逐段整理。
