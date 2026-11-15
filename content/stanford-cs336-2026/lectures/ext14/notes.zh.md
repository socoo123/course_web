---
title: "后训练目标统一推导：谁采样，谁比较，梯度流向哪里？"
lectureId: ext14
kind: "编者专题，非官方讲次"
sourceVersion: "DPO 2305.18290v3；DeepSeekMath 2402.03300v3；DeepSeek-R1 2501.12948v2（2026-01-04）"
sourceManifest: "sources/p7-lec15/manifest-fragment.json"
readingScope: "独立读取DPO §§3–4、A.1–A.2；DeepSeekMath §§4.1–4.2、5.2.1开头/表10、A.1.4–A.1.6；R1 §§2.1–2.2。只作跨目标原创推导，不重复论文唯一正文。"
license: "DPO为CC BY 4.0；两篇DeepSeek论文arXiv非独占分发许可不构成全文翻译许可。本文为原创教学组织、推导与自拟算例。"
status: "无模型、数据集或官方环境下载；无训练与作业答案；小概率例不代表性能复现。"
---

# 后训练目标统一推导：谁采样，谁比较，梯度流向哪里？

## 1. 统一的不是一个损失，而是一份计算合同

“SFT、DPO、策略梯度都像带权交叉熵”只说对了一半。若不交代样本从哪里来、权重是否依赖参数、是否停止梯度及如何归一化，相同外形可能对应完全不同的目标。

本专题建立四本账：**分布账、监督账、梯度账、归约账**。先用有限回答空间说明数学，再连接自回归token。讲课语境见[L15](#/c/stanford-cs336-2026/lec/lec15?v=notes)与[L16](#/c/stanford-cs336-2026/lec/lec16?v=notes)。DPO唯一论文正文在[L15材料页](#/c/stanford-cs336-2026/lec/lec15?v=materials)，DeepSeekMath与R1唯一正文在[L16材料页](#/c/stanford-cs336-2026/lec/lec16?v=materials)。本页不重新翻译这些论文。

![后训练四种分布角色](assets/four-policy-roles.svg)

*原创角色账本。模型权重相同只是一时的数值事实，不能取消角色不同所带来的更新和梯度约定。*

### 1.1 四个对象，永远分开写

| 对象 | 本页记号 | 由什么决定 |
| --- | --- | --- |
| 数据分布 | $D$，其提示边缘为 $d(x)$ | 人类示范、离线偏好与提示抽样 |
| 行为/旧策略 | $\mu(y\mid x)$ | 真正生成这一批回答的过程 |
| 当前策略 | $p_\theta(y\mid x)$ | 现在要优化的模型参数 |
| 冻结参考策略 | $q(y\mid x)$ | KL或DPO使用的比较锚点 |

离线示范分布一般不等于某个已知行为策略。离线偏好对也可能来自多个模型和人工编辑；不知道其生成概率时，不能凭空写一个重要性比。

“冻结参考”指**当前优化窗口内**不对它求梯度、不由本步优化器更新，不一定指整个项目永不更换。标准离线DPO常固定SFT reference；DeepSeekMath算法1可在外层迭代重设reference；固定R1 v2 §2.1还报告每400步更新reference。更换锚点必须被记为目标定义变化，而不是偷偷把它当作old策略。

### 1.2 先固定回答token的概率口径

令 $h_t=(x,y_{<t})$，终止规则与EOS是否计入序列必须一致：

$$
\begin{aligned}
p_\theta(y\mid x)&=\prod_{t=1}^{T}p_\theta(y_t\mid h_t),\\
\ell_\theta(x,y)&=\sum_{t=1}^{T}\log p_\theta(y_t\mid h_t).
\end{aligned}
$$

有限例子默认回答空间归一化且公共支持上概率为正。实际生成还有温度、截断、top-$p$、最大长度和模板；如果它们改变真实采样分布，就不能无条件把原始模型softmax当作行为概率。下面所有精确重要性恒等式都要求使用**真实行为分布**。

## 2. SFT：在固定数据分布下拟合条件概率

先不做长度归一化：

$$
\mathcal L_{\rm SFT}
=-\mathbb E_{(x,y)\sim D}\log p_\theta(y\mid x).
$$

对每个 $x$，交叉熵可拆成不随参数变化的数据熵与KL：

$$
\begin{aligned}
H(D_x,p_\theta)
&=H(D_x)\\
&\quad+D_{\rm KL}(D_x\Vert p_\theta).
\end{aligned}
$$

所以无限容量、足够数据下，最优模型拟合示范分布 $D_x$。这里KL的左边是**数据**，不是当前策略。若用答案长度倒数给每条序列重加权，目标已变成重加权的经验学习问题，不能继续不加说明地称为原来的序列最大似然。

### 2.1 原创两回答例

示范概率是 $(3/4,1/4)$，当前模型是 $(1/2,1/2)$。设第一类logit为 $a$，第二类logit固定0，则交叉熵梯度为：

$$
\frac{\partial\mathcal L}{\partial a}
=p_\theta(y_1)-D_x(y_1)=-\frac14.
$$

这鼓励把第一类概率提高到 $3/4$。如果奖励只给第一类1分，未正则化的奖励最大化却偏好概率1。两种最优点不同，不存在“只要把SFT做足就必然等于奖励优化”的恒等式。

### 2.2 mask是任务定义，不是最后的实现细节

考虑目标token位置依次为“提示1、提示2、答1、答2、EOS、PAD、PAD”，答案loss mask为 $(0,0,1,1,1,0,0)$。提示仍作为上下文，PAD不计损失，EOS是否训练由终止合同决定。

如果三个有效目标的概率为 $(0.5,0.25,0.8)$，序列概率是0.1，序列NLL为 $\log10\approx2.3026$；按三个有效token平均则为约0.7675。两者不是同一标量，padding长度更不应改变分母。

语言模型输出通常预测“下一个位置”，所以mask要对齐**目标token**而非未移位输入位置。多轮数据还需明确是否监督所有assistant轮，工具返回是不是观察。仅仅把PAD设成忽略值，并不等于已正确实现回答mask。

## 3. Bradley–Terry：先拟合比较，不先拟合策略

对同一提示的两个回答，设潜在奖励为 $r_\phi(x,y)$。Bradley–Terry（BT）模型规定：

$$
\begin{aligned}
\Delta r_\phi&=r_\phi(x,y_w)-r_\phi(x,y_l),\\
P_\phi(w\succ l\mid x)&=\sigma(\Delta r_\phi),\\
L_{\rm BT}&=-\log\sigma(\Delta r_\phi).
\end{aligned}
$$

其梯度为：

$$
\nabla_\phi L_{\rm BT}
=-\sigma(-\Delta r_\phi)\nabla_\phi\Delta r_\phi.
$$

如果同一比较中赢家只在四次判断中胜三次，理想模型拟合的概率是0.75，奖励差是 $\log3$，而不是无穷大。这说明标签不必被解释成确定性真理。

给所有回答奖励同时加上 $c(x)$，比较概率不变。因此奖励的提示相关平移不可辨识。若人群存在循环偏好、上下文效应或不同评价维度，单一标量BT未必能精确表达；这是建模假设，不是人类偏好的自然定律。

这里优化的是 $\phi$。随后策略更新时，奖励值通常作为外部反馈冻结；“奖励模型可训练”不意味着actor更新要穿过它和离散采样路径一起求导。

## 4. KL正则奖励最大化：指数倾斜从哪里来？

对一个固定提示省略 $x$，取 $\beta>0$，考虑：

$$
\begin{aligned}
J(p)&=\sum_y p(y)r(y)\\
&\quad-\beta\sum_y p(y)\log\frac{p(y)}{q(y)}.
\end{aligned}
$$

约束 $\sum_y p(y)=1$。对归一化约束引入乘子 $\lambda$，内部驻点满足：

$$
r(y)-\beta\left(\log\frac{p(y)}{q(y)}+1\right)+\lambda=0.
$$

把与 $y$ 无关的项吸收进归一化常数：

$$
\begin{aligned}
Z&=\sum_y q(y)e^{r(y)/\beta},\\
p^*(y)&=\frac{q(y)e^{r(y)/\beta}}{Z}.
\end{aligned}
$$

不仅可以找驻点，还能直接验证最优性：

$$
J(p)=\beta\log Z-\beta D_{\rm KL}(p\Vert p^*).
$$

KL非负，因此 $p=p^*$ 达到最大值。这一结论需要策略空间足够自由；参数共享的神经网络未必能同时表达所有提示的最优分布。

### 4.1 支持集条件不能省掉

- 若 $q(y)=0$ 而 $p(y)>0$，$D_{\rm KL}(p\Vert q)$ 为无穷大；有限正则目标不允许向reference零支持的回答搬质量。
- 在有限公共支持上、有限奖励且 $\beta>0$，$Z$有限。无限序列空间则还需检查可归一化、终止与可积性。
- $\beta$是奖励尺度与偏离代价之间的相对单位；奖励整体乘常数，不能再用未调整的 $\beta$ 声称目标不变。

### 4.2 原创三回答倾斜例

取 $q=(1/2,3/10,1/5)$，$r=(\log2,0,-\log2)$，$\beta=1$。未归一化质量为 $(1,3/10,1/10)$，所以：

$$
\begin{aligned}
Z&=7/5,\\
p^*&=(5/7,3/14,1/14),\\
J(p^*)&=\log(7/5)\approx0.3365.
\end{aligned}
$$

奖励最高的回答没有获得全部概率；reference与KL保留了其他质量。给所有奖励加同一个常数不改变 $p^*$，只平移最优目标值。

## 5. DPO：将BT奖励换成策略的log比

从上节最优关系反解：

$$
r(x,y)=\beta\log\frac{p^*(y\mid x)}{q(y\mid x)}+\beta\log Z(x).
$$

同一提示下做奖励差，$\log Z(x)$相消。现在以可训练策略表示隐含奖励，定义：

$$
\begin{aligned}
a_\theta(y)&=\log p_\theta(y\mid x)-\log q(y\mid x),\\
z_\theta&=\beta[a_\theta(y_w)-a_\theta(y_l)],\\
L_{\rm DPO}&=-\log\sigma(z_\theta).
\end{aligned}
$$

关键不是“把奖励代回期望奖励就完了”，而是**把隐含奖励代入BT偏好似然**。这才得到离线比较损失。

令 $s_w=\nabla_\theta\log p_\theta(y_w\mid x)$，$s_l$类似，则：

$$
\begin{aligned}
c_\theta&=\beta\sigma(-z_\theta),\\
\nabla_\theta L_{\rm DPO}&=-c_\theta(s_w-s_l).
\end{aligned}
$$

reference不接收梯度。$c_\theta$是对原损失求导后得到的系数；不能另外构造 $-c_\theta(\ell_w-\ell_l)$ 并对系数继续求导，声称它与DPO相同。若用它表达局部带权梯度，系数必须当作已算出的数值停止梯度。

### 5.1 比绝对概率更重要的是相对reference的变化

自拟参考 $q=(0.6,0.3,0.1)$，当前 $p=(0.5,0.4,0.1)$，偏好第二个回答胜第一个，$\beta=1$：

$$
\begin{aligned}
z&=\log1.6,\\
P(w\succ l)&=8/13,\\
L&=\log(13/8),\\
c&=5/13.
\end{aligned}
$$

当前赢家概率0.4仍低于输家0.5；但它相对reference的增长更大。相反，两个回答绝对概率相等也不表示DPO的预测是1/2，还要看reference。

这个梯度同时通过所有共享参数。正负项是局部驱动力，不是有限学习率下“所有赢家绝对概率必增、所有输家必减”的逐样本保证。

### 5.2 理论与离线实践之间还有哪些桥？

推导依赖BT形式、reference支持、策略可表示性及同一提示比较。有限数据还需要足够覆盖；没有被比较过的回答不能由公式自动获得正确排序。真实离线数据的行为策略可能与reference不一致，分布漂移并不因“没有rollout”而消失。

标准DPO使用序列log概率和。若改用 $\ell(y)/T_y$，这不是同一序列概率：$e^{\ell/T}$一般没有按回答空间归一化。不同长度会改变比较，不能再直接套用上节原样的序列KL推导。

**读源提醒：** DeepSeekMath A.1.4式12明确使用长度归一化；原DPO式7使用序列log比。本页从各自明确写出的损失重新求导，不把不同论文中的“梯度系数”记号直接拼成同一算法。对应原文辨析保留在唯一材料页。

## 6. 策略梯度：采样分布本身随参数改变

考虑外部奖励 $r(x,y)$，没有显式 $\theta$ 依赖。固定提示，定义score $s_\theta(y)=\nabla_\theta\log p_\theta(y\mid x)$，以及 $F(\theta)=\mathbb E_{y\sim p_\theta}r(y)$，则：

$$
\begin{aligned}
\nabla_\theta F(\theta)
&=\sum_y r(y)\nabla_\theta p_\theta(y)\\
&=\mathbb E_{p_\theta}[r(y)s_\theta(y)].
\end{aligned}
$$

离散采样不提供普通路径导数；score-function恒等式让我们在样本固定后对log概率求导。局部actor代理损失可写为：

$$
L_{\rm actor}=-\operatorname{sg}(A)\log p_\theta(y\mid x).
$$

$\operatorname{sg}$表示停止梯度。其数值不是原始期望奖励，但在正确采样和优势条件下，梯度估计可对应所需更新。不要比较这两种标量损失的下降曲线就声称真实奖励提高。

### 6.1 为什么可以减baseline？

若 $b(x)$不依赖当前回答，则：

$$
\begin{aligned}
\mathbb E_{p_\theta}[b(x)s_\theta(y)]
&=b(x)\nabla_\theta\sum_y p_\theta(y\mid x)\\
&=0.
\end{aligned}
$$

因此使用 $A=r-b(x)$不改变期望梯度，并可能降低方差。但“任意减一个数都无偏”是错的：如果baseline包含当前动作的奖励，就要重新检查相关性。critic即便由可训练网络给出，actor更新也通常对其数值停止梯度，critic另用自己的目标训练。

## 7. 重要性采样与裁剪：分母是行为策略

rollout来自 $\mu$，要估计当前策略的期望，在支持满足 $p_\theta(y)>0\Rightarrow\mu(y)>0$ 时：

$$
\begin{aligned}
\rho(y)&=\frac{p_\theta(y\mid x)}{\mu(y\mid x)},\\
\mathbb E_{p_\theta}f(y)&=\mathbb E_\mu[\rho(y)f(y)].
\end{aligned}
$$

若 $f$本身随参数变化，完整求导还要包含它的显式导数；不能仅看到比值便把所有其他分支随意detach。

**原创例。** $\mu=(0.5,0.5)$，当前 $p=(0.8,0.2)$，奖励为 $(1,0)$。当前期望为0.8；直接用旧样本的未加权期望是0.5；权重 $(1.6,0.4)$恢复0.8。裁剪权重会改变这个等式，虽然可能降低方差或限制局部优化冲动。

### 7.1 序列比与token比不是同一校正

$$
\begin{aligned}
\rho_{\rm seq}
&=\prod_{t=1}^{T}\rho_t,\\
\rho_t
&=\frac{p_\theta(y_t\mid h_t)}{\mu(y_t\mid h_t)}.
\end{aligned}
$$

完整序列比能改变整个轨迹分布的测度，但长序列乘积容易高方差。常见PPO/GRPO使用旧前缀下的逐token比构造**局部代理目标**；这不等于完整回答分布的精确IS。对序列log比取长度均值再指数化，是几何平均比，也不再是原始序列概率比。

### 7.2 裁剪取min，符号决定哪一侧饱和

定义：

$$
\begin{aligned}
\bar\rho&=\operatorname{clip}(\rho,1-\epsilon,1+\epsilon),\\
S(\rho,A)&=\min(\rho A,\bar\rho A).
\end{aligned}
$$

最大化 $S$。$A>0$时，过度提高概率的收益被截住；$A<0$时，过度降低概率的收益被截住。反方向恶化仍会受到惩罚。

取 $\epsilon=0.2$：

| $A$ | $\rho$ | $\rho A$ | $\bar\rho A$ | 取min |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 1.6 | 1.6 | 1.2 | 1.2 |
| −1 | 0.4 | −0.4 | −0.8 | −0.8 |
| −1 | 1.6 | −1.6 | −1.2 | −1.6 |

这不是把实际策略概率强制投影到区间内。共享参数、多个样本和其他损失项仍能令某个比值跑出区间。

### 7.3 old等于current，不等于把比值删成常数

在采样后的第一个更新点，数值可能是 $p_\theta=\mu$，于是 $\rho=1$。但 $\mu$已经冻结：

$$
\nabla_\theta\rho\big|_{p_\theta=\mu}
=\nabla_\theta\log p_\theta.
$$

$ p_\theta/\operatorname{sg}(p_\theta)$的值为1但导数不为0；$p_\theta/p_\theta$却恒为1且导数为0。这是图结构区别，不是浮点误差。

一次rollout后，多个微批先累积梯度、最后只做一次optimizer step，不会在微批之间改变行为与当前策略的相等关系；对同一rollout做多次optimizer更新，从第二次起就使用旧策略数据。DeepSeekMath附录的old=current是简化分析条件，不是所有训练步都成立的通用假设。

## 8. KL方向、估计值与梯度是三个问题

本页使用：

$$
\begin{aligned}
K(p,q)&=D_{\rm KL}(p\Vert q)\\
&=\mathbb E_{y\sim p}\log\frac{p(y)}{q(y)}.
\end{aligned}
$$

不能把它与 $D_{\rm KL}(q\Vert p)$互换。原创例 $p=(0.8,0.2),q=(0.5,0.5)$：

$$
\begin{aligned}
K(p,q)&\approx0.192745,\\
K(q,p)&\approx0.223144.
\end{aligned}
$$

单个样本的 $\log(p/q)$可以为负，期望才非负。DeepSeekMath式4与R1式2使用一种逐样本非负形式。记：

$$
\begin{aligned}
u(y)&=q(y)/p(y),\\
k(y)&=u(y)-\log u(y)-1\ge0.
\end{aligned}
$$

在同一正支持且 $y\sim p$ 时，因为 $\mathbb E_p u=1$，有 $\mathbb E_p k=K(p,q)$。只说“无偏KL估计器”而省略采样分布，容易制造错误结论。

### 8.1 旧分布采样时，期望不再自动等于当前KL

上例两个 $k$值约为0.095004与0.583709。在 $p=(0.8,0.2)$ 下加权，得到0.192745；在旧分布 $\mu=(0.5,0.5)$ 下平均，却是0.339356。

若只有 $p\ll q$而公共支持并不相同，$\mathbb E_p(q/p)$也未必等于1，因为 $q$可能在 $p=0$处还有质量。非负性仍成立，但该无偏等式还需要额外支持条件。温度截断和top-$p$产生的零概率尤其需要小心。

### 8.2 数值估计无偏，不代表直接autograd得到目标的无偏梯度

若对 $\mathbb E_{p_\theta}k_\theta$求完整导数，需要同时考虑采样测度和 $k$的显式参数依赖。沿用log比 $a_\theta(y)=\log(p_\theta(y)/q(y))$ 和score $s_\theta(y)$，真实KL梯度在正规条件下是：

$$
\nabla K(p_\theta,q)
=\mathbb E_{p_\theta}[a_\theta(y)s_\theta(y)].
$$

但是在已经固定的样本上，只对 $k_\theta$反向传播，导数是 $(1-u)\nabla\log p_\theta$。即使样本恰好来自当前 $p$，这个固定测度下的期望也为：

$$
\mathbb E_p\nabla k
=-\mathbb E_q\nabla\log p.
$$

它一般不同于上一条真实KL梯度。二分类logit例中，前者为 $0.8-0.5=0.3$，真实 $K(p,q)$梯度为 $0.16\log4\approx0.221807$。

**结论不是“论文不能这样训练”**：论文可以选择这样的可微采样代理项。结论是报告必须区分“所估计的KL值”“固定旧样本上的代理损失”与“某个总体KL的精确梯度”，不能用一个无偏数值声明替代三个证明。

### 8.3 token KL还有前缀分布

完整序列KL能按当前策略产生的前缀展开为条件token KL之和。若前缀来自旧策略，或者每条序列额外除以自己的长度，得到的是另一种加权量。一个token位置上把方向写对，不表示整个训练日志已等于当前完整序列KL。

## 9. GRPO：同题多回答替代critic，不替代所有统计问题

对同一提示，从行为策略抽取 $G$个回答，取得奖励 $r_1,\ldots,r_G$。先明确使用总体标准差：

$$
\begin{aligned}
\bar r&=\frac1G\sum_i r_i,\\
s^2&=\frac1G\sum_i(r_i-\bar r)^2,\\
A_i&=\frac{r_i-\bar r}{s+\delta}.
\end{aligned}
$$

$\delta>0$是明确声明的数值稳定项；它不是所有论文原式都写出的同一超参数。奖励、均值、标准差和actor使用的 $A_i$均停止梯度。采用样本标准差 $G-1$会改变尺度，小组时差别明显，不能默默混用。

结果监督通常将同一 $A_i$赋给该回答全部有效token。令 $m_{it}$为答案mask，$T_i=\sum_t m_{it}$，定义局部项：

$$
\begin{aligned}
U_{it}&=S(\rho_{it},\operatorname{sg}(A_i)),\\
V_{it}&=U_{it}-\beta k_{it},\\
\widehat J&=\frac1G\sum_i\frac1{T_i}\sum_t m_{it}V_{it}.
\end{aligned}
$$

这是与DeepSeekMath式3结构对应的**每序列平均的采样代理目标**，不是把上一节全部KL/IS条件自动满足的精确总体目标。$p_\theta$保留梯度，old/reference冻结；KL项是否用这种样本形式、是否启用以及系数多大，都必须单独注明。

### 9.1 组归一化改变题目间权重

忽略稳定项以便手算：奖励 $(0,0,1,1)$给出均值0.5、标准差0.5，优势为 $(-1,-1,1,1)$。奖励 $(0,0,0,1)$给出均值0.25、标准差 $\sqrt3/4$，优势为：

$$
(-1/\sqrt3,-1/\sqrt3,-1/\sqrt3,\sqrt3).
$$

同样一个正确回答，在第二组得到更大系数。除以组标准差不仅降低数值尺度差异，也在重新分配不同问题与组的训练权重。

全对或全错的组具有零方差。若采用上述加稳定项的定义，任务优势全为0；不能借由极小分母制造“巨大正确方向”。但若KL项仍启用，整步梯度未必为0。组内没有相对差异也不代表该题永久不值得训练，只说明本次相对奖励没有提供区分信号。

### 9.2 把自身奖励放进baseline，不是自动无偏

先不除标准差。独立同分布的 $G$个回答中，令 $s_i=\nabla\log p(y_i)$，并记 $g=\mathbb E[r_i s_i]$，则：

$$
\mathbb E[(r_i-\bar r)s_i]
=\left(1-\frac1G\right)g.
$$

原因是组均值含有当前 $r_i/G$；其他回答的奖励与 $s_i$独立，其期望项为0。留一均值可在这些条件下消除这项自包含缩放，但加入随机标准差后还要重新分析，不能简单声称“baseline均不改变目标”。本段是原创统计辨析，不是要求修改官方作业。

另外，初始比值为1时组平均优势可恰好为0，代理目标值为0，但各回答的score梯度不同，**梯度仍可非零**。用标量loss接近0判断“GRPO没有学习”是不成立的。

### 9.3 过程监督与可验证奖励也不是同一个开关

DeepSeekMath §4.1.3讨论对步骤末端评分，并给较早token累积后续步骤的归一化奖励；结果监督只在整条回答结束时给分。这是信用分配差异，不是只把一个标量复制位置的无关实现细节。

R1 v2 §2.2讨论准确性与格式奖励相加，并说明其避免在推理任务使用神经奖励模型的动机。不能把论文中的奖励组合直接搬到A5：官方作业有自己的总奖励合同。规则验证仍受解析器、测试覆盖、超时、等价答案处理与数据选择影响，不是无噪声真值。

## 10. 长度归约：改变分母就是改变训练权重

![相同token项的三种归约](assets/reduction-contract.svg)

*原创算例。图中项可以理解为已算好的局部代理贡献，不是奖励成绩；不含任何实际训练曲线。*

设第 $i$条回答的有效token项为 $v_{it}$，$N$为回答数。三种常见定义是：

$$
\begin{aligned}
R_{\rm seq}&=\frac1N\sum_i\frac{\sum_t m_{it}v_{it}}{T_i},\\
R_{\rm tok}&=\frac{\sum_{i,t}m_{it}v_{it}}{\sum_i T_i},\\
R_{\rm const}&=\frac1N\sum_i\frac{\sum_t m_{it}v_{it}}{M}.
\end{aligned}
$$

$M$是声明的固定常数，不是每条实际长度。图中两条回答长度2、4，局部项分别全为1、全为−1，取 $M=4$，结果为0、−1/3、−1/4。它们不仅尺度可能不同，相互抵消关系也不同。

组内标准差归一化、每序列长度归约、全批token分母是三个独立开关。还需要说明先对组平均还是把所有回答摊平；当不同问题有不同有效组大小时，这两种做法会让题目权重不同。

跨微批累积时，不能简单平均每个微批的token均值再当作整个批次token均值，除非有效token数相同。应从所声明的全批目标倒推各微批权重。这里给的是数学合同，不给官方函数实现。

## 11. 统一看梯度，但不把不同目标说成等价

在某个参数点，很多actor更新可写成“有效token的score乘系数”。重要的是各系数的来历：

| 方法 | 样本来源 | 系数或监督 | 主要停止梯度位置 |
| --- | --- | --- | --- |
| SFT | 固定示范 $D$ | 正向最大似然 | 数据与mask |
| BT奖励模型 | 固定偏好对 | 比较误差权重 | 标签；训练的是奖励参数 |
| DPO | 固定偏好对 | 成对正负score，权重 $\beta\sigma(-z)$ | reference；若重写局部加权代理则detach系数 |
| 策略梯度 | 当前策略 | 奖励减合法baseline | 奖励与actor baseline |
| PPO型代理 | old rollout | 概率比、优势与裁剪分支 | old概率、优势 |
| GRPO型代理 | 同题group rollout | 组相对优势、裁剪及可选KL | group统计、old、reference |

统一外形不意味着相同采样分布、相同极值或相同统计性质。尤其不能把原论文附录在old=current条件下的系数，直接用作任意离策略训练的无偏证明。

**固定原文的定位差异：** DeepSeekMath算法1第11行写“Equation 21”，但完整裁剪目标实际在式3；式21是附录简化分析的梯度系数。此处保留这个引用差异，不静默将原文改成式3。R1 v2 §2.1用回答级记号给目标，本页为了审计token mask采用DeepSeekMath的token展开，不能据此声称已从R1简式还原其全部实现。

## 12. 实现前的八个口头检查

1. 我优化的到底是数据似然、偏好似然、真实期望奖励，还是一个采样代理目标？
2. 哪个checkpoint真正产生了样本？温度与截断是否改变行为概率？
3. reference何时冻结、何时重设？它与old是否只是在某个时刻相等？
4. log概率只覆盖答案吗？EOS、截断、工具观察和padding怎样处理？
5. reward、baseline、组标准差是否进入actor梯度？是否误让old或reference可训练？
6. KL方向和采样分布是否一起写出？日志的数值估计与反向目标是否相同？
7. 逐token比、完整序列比与几何平均比有没有被当成一回事？裁剪是不是被误说成严格约束？
8. 分母是实际长度、固定长度、全批tokens还是组数？微批累积是否保持这个目标？

优化目标正确也不能保证评测有效。独立评价还要固定题目集合、采样次数、推理token预算、解析规则和模型选择过程。用更多候选、筛选成功样本再报告结果，必须披露选择机制，不能当作相同预算下的单次能力提升。

LoRA/QLoRA可限制哪些参数接收这些梯度，但不会自动修复数据、偏好、mask或采样测度错误。适配器、冻结与显存机制请回看[ext11](#/c/stanford-cs336-2026/lec/ext11?v=notes)，不在本页重复。

## 13. 自测与答案

**1．把DPO的两个序列log概率都除以各自长度，损失更稳定，所以数学目标没变？** 错。比较margin改变了，原序列概率与KL推导不能原样沿用。

**2．$p/\operatorname{sg}(p)$等于1，所以没有梯度？** 错。只有分母停止梯度，导数仍为 $\nabla\log p$；把分子也相消会丢失策略梯度。

**3．为什么SFT和KL正则RL中的两个KL方向不同？** SFT的交叉熵对应 $D_{\rm KL}(D_x\Vert p)$；本页RL目标约束的是 $D_{\rm KL}(p\Vert q)$。左右分布和目标含义都不同。

**4．$k=q/p-\log(q/p)-1$每样本非负，能否用任意旧样本平均它当当前KL？** 不能。数值非负不等于在任意采样分布下无偏；支持、采样分布、梯度路径还要分别检查。

**5．全错的四个回答经过组归一化后会给出四个负优势吗？** 在减组均值的定义下不会，四个奖励一样，中心化后全为0。只有另设绝对基准才可能全负，那是另一种合同。

**6．组平均优势为0，为什么还能学习？** 不同回答的score向量不同，正负系数对不同向量加权后通常不抵消。

**7．clip0.2是否保证所有新旧概率比都落在0.8到1.2？** 不保证。它限制某些代理收益的增长，不是对参数或所有回答概率的硬投影。

**8．冻结reference是否与R1 v2每400步更新reference矛盾？** 不矛盾。前者是优化窗口内梯度合同，后者是明确安排的窗口间锚点更新。标准离线DPO不能因此随意改成每步追随current。

**9．若两条回答各有2、4个有效token，平均两个微批的token均值能还原整体token均值吗？** 一般不能。必须按2和4的有效数量加权；图中直接均值为0，而整体token均值为−1/3。

## 来源、实际读取与边界

- Rafael Rafailov、Archit Sharma、Eric Mitchell、Stefano Ermon、Christopher D. Manning、Chelsea Finn，*Direct Preference Optimization: Your Language Model is Secretly a Reward Model*，[2305.18290v3](https://arxiv.org/abs/2305.18290v3)，2024-07-29。实际读§§3–4、A.1–A.2，物理pp3–5、15–16；视觉核对pp4、16。[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；本页非官方独立重组，新增推导、支持条件与自拟例；不复制论文图，第三方权利另核。
- Zhihong Shao等，*DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models*，[2402.03300v3](https://arxiv.org/abs/2402.03300v3)，2024-04-27。实际读§§4.1.1–4.1.4、4.2（pp11–15）、§5.2.1开头及表10（pp18–19）、A.1.4–A.1.6（pp29–30）；视觉核对pp13、14、29。附录相邻文字随读取窗口被看到不计全文精读。
- DeepSeek-AI等，*DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning*，[2501.12948v2](https://arxiv.org/abs/2501.12948v2)，2026-01-04、86页版本。实际读§§2.1–2.2（pp2–4）及相邻上下文，视觉核对p3。不是2025 v1节号；本页不独立声称完成R1全部指定核心。
- 两篇DeepSeek论文的[arXiv非独占分发条款](https://arxiv.org/licenses/nonexclusive-distrib/1.0/)不授予本项目公开全文翻译权，模型或软件许可不能代替论文许可。本页采用原创概念讲解而非重复精读译文。
- 三张相关原创SVG与小概率案例只演示机制。未运行官方环境、评测、奖励服务、模型或训练；精确读取范围和九页视觉检查记录在`p7-lec15/reading-log.json`。最终集成验证由主流程单独登记。
