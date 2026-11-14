---
title: 从零训练循环与线性模型：阶段练习
kind: 编者阶段练习（教材改编整理，非官方编号 Lab）
source: 《动手学深度学习》中文第二版 3.1–3.7 节选及 PyTorch 分支；practice-plan 的 linear-training 四项任务
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 本页不是视频实验转录；相关课表入口与来源边界见页底
license: 教材仓库 Apache-2.0；Fashion-MNIST 官方仓库单独采用 MIT；均不外推视频
status: 四项任务规格与编者验收；不是已执行报告，实际独立机制验证范围见课程公共资料
execution: 不提供完整作业代码；全量训练、原课 Notebook 和学生实现未在本页宣称通过
version_boundary: 当前中文第二版固定源码，不是 2021 教材快照
---

# 从零训练循环与线性模型

## 目标：让每一次更新都有来路

把“取数据 → 前向 → 损失 → 反向 → 更新 → 评估”写成自己能够解释的程序。完成后，你应能指出：一个参数何时改变、某个指标的分母是什么、验证数据为什么不能参与更新、数值失败来自哪里。需要的矩阵和梯度只在当前任务中补，不新增论文或整门前置课。

这是**编者整合的阶段练习，不是官方编号 Lab，也没有官方 grade**。四个原任务全部保留。教材已是中文，本页是改编任务规格，不是翻译；没有对应英文原文，因此不建立 `lab.en.md`。

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

> 本地练习使用自己的Python/PyTorch环境。没有官方Lab分数或统一成绩门槛。

- **CPU 基础**：普通 Python 脚本即可。任务 1 使用合成回归数据，任务 2–3 必须使用真实 Fashion-MNIST；不能用随机图片、`FakeData` 或合成标签替代。
- **硬件扩展**：完整数据规模可独立扩展，GPU 仅是可选加速，不要求 CUDA、MPS 或排行榜成绩。
- **环境**：沿课程公共资料的 Python 3.11.8 / PyTorch 2.5.1 / NumPy 1.26.4 / pandas 2.2.3 基线；本实验数据路线新增 torchvision，版本与实际安装结果见[课程公共资料](#/c/d2l-pytorch-2021)。不要求 `d2l`、Jupyter、matplotlib，不混装旧教材依赖。
- **数据存放**：下载到自己的运行时缓存，不放网站 `content/`，不提交样本或模型权重。在本地记录来源、校验、划分索引和指标即可。

## 统一输入输出与复现约定

交自己的脚本及运行记录，不交 AI 代写的完整答案。记录：task id、环境版本、设备、dtype、种子、数据哈希、索引划分、初始化、损失归约、batch size、学习率、epoch、实际更新次数、样本数、指标、断言和失败解释。曲线可以交 CSV/文本表，不强制安装绘图库。

同一环境内比较两次运行时，固定数据、初值与批次顺序。数据生成/划分用独立 CPU generator，种子 **2021**；参数初始化用 **2022**；训练 shuffle 用 **2023**。每个对照从同一份初始快照和同一批次索引重启，不能接着上一轮模型继续训。记录种子不等于承诺跨版本、跨设备逐位相同。

- 基础训练用 CPU `float32`，标签分类索引用 `torch.long`；手算一步核对可用 `float64`。
- 先比较 shape，再比较浮点。一步对照建议 `atol=1e-6, rtol=1e-5`；`float64` 手算可收紧为 `atol=1e-10, rtol=1e-8`。这些是编者局部检查约定，不是官方成绩阈值。
- 所有加载器 `drop_last=False`；CPU 起步 `num_workers=0`。训练 shuffle，验证不 shuffle。不能为了消除尾 batch 而扔样本。
- 本实验不加权重衰减、动量、类别权重、label smoothing 或数据增强，以免对照混入另一因素。

## 任务 1：从零 SGD 与 `nn.Linear` 真正等价吗

**task id：`linear-training-1`**

### 输入与模型

一次生成 1000 个样本：$X\in\mathbb R^{1000\times2}$ 各元素独立标准正态，真实参数 $w_*=[2,-3.4]^\top$、$b_*=4.2$，噪声独立正态、标准差 0.01。先生成全部 X，再生成形状 `(1000,1)` 的噪声；标签保持 `(1000,1)`。前 800 行训练，后 200 行验证；本合成分布独立同分布，固定顺序划分便于复现。

从零版自己写批处理、$Xw+b$、半平方损失和 SGD 参数更新；允许 autograd 求梯度，但不能在这一路调用 `nn.Linear` 或优化器。对照版使用 `nn.Linear(2,1)` 与 `torch.optim.SGD`，训练循环仍自己写。

| 对象 | 从零版形状 | 高层版对应 |
|---|---|---|
| 一批 X | `(B,2)` | 相同 |
| 权重 | `(2,1)` | `Linear.weight` 是 `(1,2)`，需转置对应 |
| 偏置 | `(1,)` | `(1,)` |
| 预测与标签 | 均为 `(B,1)` | 相同；相减不得广播成 `(B,B)` |
| 每样本损失 | `(B,1)` | 高层 MSE 需匹配半平方约定 |

统一优化目标为

$$
L_B=\frac{1}{B}\sum_{i=1}^B\frac{(\hat y_i-y_i)^2}{2}.
$$

`MSELoss` 默认没有这里的 $1/2$，不能直接把两个不同损失当作等价。若已对损失取 mean，更新时不得再除 B；若反传 sum，更新必须除**该批实际样本数**，不是配置的 batch size。

### 要做什么

1. 两条实现从完全相同的权重和偏置出发：权重正态初始化、标准差 0.01，偏置 0；显式复制初值，不能只假设“用了同一个种子就一样”。在 `no_grad` 中赋值，禁止 `.data`。
2. 先在第一批上逐项比较预测、标量损失、梯度、一次更新后的参数。解释 `Linear` 的转置约定。
3. 再用相同批次索引训练两条路线：`B=64`、`lr=0.03`、40 epochs，每轮 13 次更新，尾批 32 个样本。逐轮固定当前参数，重新评估全部训练及验证集的半平方损失；不要将训练过程中不断变化的模型损失混作这个指标。
4. 输出真实参数与估计参数的差、两条路线参数最大绝对差，以及 epoch 0 与各轮评估损失。

### 可观察验收

- 一轮每个训练 id 恰出现一次，验证 id 从未进入更新；总计每条路线 520 次更新。
- 一步对照在上述容差内吻合；尾批单独核对归一化。长程参数允许累计浮点误差，但应报告差值并解释，不要求逐位相同。
- 基线末轮训练/验证损失低于初始化，参数应接近 $w_*,b_*$；编者建议以各参数绝对误差小于 0.05 作为排查目标。若未达到，保留真实结果并排查，不伪造“达到阈值”。噪声数据不要求损失为零。
- 回归不报告分类 accuracy；保存的历史参数必须是真正数值快照，不是会随训练改变的别名。

## 任务 2：真实 Fashion-MNIST softmax 分类

**task id：`linear-training-2`**

### 数据取得与严格划分

Fashion-MNIST 官方发布 **60000 张训练图、10000 张测试图**，每张 28×28 灰度图、标签 0–9。它不是手写数字 MNIST。

使用 `torchvision.datasets.FashionMNIST(root=自己的缓存, train=True/False, transform=ToTensor(), download=...)`。`train=False` 指官方测试集，**不会自动替你切验证集**。下载前先核对来源与文末 MD5。默认源不可达时，可从官方 GitHub 的 `data/fashion/` 取得同名 gzip、核对 MD5 后解压到缓存的 `FashionMNIST/raw/`；不要换成来源不明的压缩包或伪造数据。该版本加载器检查四个解压文件是否存在，因此即使只训练 `train=True`，缓存也应备齐四份；下载了测试文件不等于允许调参时读取测试样本。

1. 在官方训练集索引 `0…59999` 上，以独立种子 2021 生成一次 `randperm(60000)`。
2. 排列的前 5000 个索引作为验证候选，其余 55000 个作为训练候选，保存索引或其哈希。
3. **基础 CPU 路线**：固定取训练候选前 **257** 个、验证候选前 **73** 个。二者是真实图片、真实标签，不能重抽“更好学”的子集。打印各类计数以说明小样本局限，不按表现筛选样本。
4. **完整规模扩展**：保持原划分，改为 55000 训练 / 5000 验证；模型和循环不变。独立选择合理训练轮数，用验证集选择配置。配置冻结后才对官方 10000 测试样本做一次最终评估，测试分数不能再反馈调参。基础路线不要求最终测试评估。

基础预处理只有固定的像素除以 255，无需拟合数据统计量。若扩展标准化，只用训练子集拟合均值方差，冻结后用于验证/测试；不能从完整 60000 或测试集借统计量。

### 模型、数值与任务

| 阶段 | 形状与含义 |
|---|---|
| `ToTensor` 单图 | `(1,28,28)`，浮点像素位于 `[0,1]` |
| 一批图像与标签 | `(B,1,28,28)` 与 `(B,)`，标签为 long、范围 0–9 |
| 展平 | `(B,784)`；只折叠特征轴，不折叠 batch 轴 |
| 参数 | 手写 W 为 `(784,10)`、b 为 `(10,)`；`Linear.weight` 为 `(10,784)` |
| logits / 概率 | `(B,10)`，类别轴为 1 |
| 每样本交叉熵 / 预测类别 | 均为 `(B,)`；求均值后损失才是标量 |

1. 自己组织分类训练循环。模型可采用 `Flatten + Linear(784,10)`；也可手写仿射变换。没有隐藏层、CNN 或额外特征。权重标准差 0.01、偏置为 0，SGD `lr=0.01`、`B=64`、**5 epochs** 为基础起点。每轮 5 次更新，尾批只有 1 个样本；不能用裸 `squeeze()` 丢掉 batch 轴。
2. 先实现/解释一个按行的稳定 softmax，以及由 logits 直接计算的稳定交叉熵小核对。令一行 logits 为 $z$，真实类为 y，$m=\max_jz_j$：

$$
\ell(z,y)=(m-z_y)+\log\sum_j\exp(z_j-m).
$$

3. 用局部输入 `z=[[1000,0,-1000],[0,0,0]]`、`y=[2,1]` 检查损失与梯度是否有限，并与 `CrossEntropyLoss(reduction='none')` 比较。三类只是数值单元，不替代真实十类训练。说明为什么只做“减最大值的 softmax 再 log”仍会因正确类概率下溢为 0 而失败。
4. 真实训练直接把**原始 logits** 传给 `CrossEntropyLoss`，不要先 softmax。无类别权重/忽略标签时 mean 的分母是实际 B。accuracy 用 logits 的 `argmax(dim=1)`，不是对 loss 求导，也不是沿 batch 轴找最大。
5. 交 epoch 0–5 的训练/验证损失和 accuracy、每轮样本数与更新数、参数变化及有限性检查；再列 5 个验证 id 的真实标签和预测标签，不能挑选全对样本展示。

### 可观察验收

- 数据下载校验、标签范围、各级形状、训练/验证索引交集为空均有记录；测试集未参与更新或配置选择。
- 共 25 次训练更新；每轮消费 257 个训练样本，评估各消费 257/73 个。accuracy 在 `[0,1]`，正确数为整数，参数确实更新，梯度与正常基线损失均有限。
- 小核对的稳定损失与框架结果一致；每行概率非负、和接近 1；给某行 logits 全加同一个有限常数不改变该行概率和交叉熵（容差内）。
- 用固定参数重新评估的训练损失应比初始化降低；若未降低，先排查流程并留下失败记录。**不要求每轮单调、不设置小验证集必须达到教材全量 accuracy 的门槛**，更不能把 257/73 的结果宣称为全量复现。

## 任务 3：模式、梯度、更新、指标四件事分开

**task id：`linear-training-3`**

在任务 2 模型与真实数据上完成。为可独立调试，可以只用一个真实训练 batch 和一个真实验证 batch，再接回完整的五轮基线。

1. 对同一个线性分类器、同一批输入，分别使用 `train()` / `eval()` 与默认 grad / `no_grad()` 的四种组合。记录 `model.training`、输出 `requires_grad`、loss 的 `grad_fn`。每格重新前向，参数不变。纯 `Linear` 没有模式特定行为，所以不能用“输出没变”推断 `eval()` 没作用或已关闭梯度。
2. 在独立诊断分支、使用**训练样本**展示 `eval()` + 默认 grad 仍能 backward；只反传、不 step 时参数不变。清掉诊断梯度后再开始正常训练，避免污染。另展示 `train()` + `no_grad()` 的普通前向不产生可反传的损失；不必靠捕获所有异常判断成功。
3. 正式训练阶段用 `train()`、开梯度、清梯度、前向、反向、step。正式评估用 `eval()` 与 `no_grad()`，禁止 backward/step，结束后下一轮恢复 `train()`。
4. 评估前保存参数与现有梯度快照，评估后核对二者未变；`no_grad()` 不会自动清空旧梯度。此模型没有 BatchNorm 缓冲，后续含缓冲的模型还要核对状态，而不只参数。
5. **干预检验**：固定训练输入、初值、顺序和轮数，把验证标签替换成另一组合法标签。两次训练结束参数应一致，验证指标可以变化。此检验不使用基于验证的早停或调参，否则参数变化可能是有意的配置选择，不能混在此处。

### 尾 batch 与指标验收

训练时每批损失用于更新；日志中本页约定的 `train_loss`、`train_accuracy` 是**每轮结束后冻结当前模型重新遍历训练集**得到的，与同次验证指标可比。若另记在线 batch 损失，命名为 `online_train_loss`，不能悄悄替换。

对包含 K 批的评估集，第 k 批有 $B_k$ 个样本、平均损失 $\bar\ell_k$、正确数 $c_k$：

$$
\mathrm{loss}=\frac{\sum_{k=1}^{K}B_k\bar\ell_k}{\sum_{k=1}^{K}B_k},\qquad
\mathrm{accuracy}=\frac{\sum_{k=1}^{K}c_k}{\sum_{k=1}^{K}B_k}.
$$

不能对各批 mean 或各批 accuracy 再无权平均。用两个假定的**统计量**做独立手算：批量 4 和 1，平均损失 1 和 5，正确数 3 和 0；核对你的累计器与逐样本结果一致。这只是统计单元，真实 Fashion-MNIST 仍必须运行。

评估同一冻结模型、同一 73 个验证样本，分别用 B=64 与 B=32，结果应在容差内一致，且分母始终为 73；这一步不改变训练 batch。参数冻结、样本不丢失、批大小不影响总体指标，三条证据都要保留。

## 任务 4：官方学习率习题的控制变量与失败曲线

**task id：`linear-training-4`**

选定教材 **3.2“练习”第 6 项：不同学习率对损失下降快慢的影响**。本页将其改编为可手算、可复现的极小回归对照；也关联第 7 项的尾批检查。不是教材已经给出的实验结果。

### 固定失败夹具

为排除真实数据的噪声和 batch 顺序影响，单独使用两条自拟样本：`X=[[-1],[1]]`、`y=[[-2],[2]]`；$\hat y=Xw+b$，`w=0,b=0`，CPU `float64`，目标仍为平均半平方损失。两个样本组成一个 B=2 的完整 batch，不 shuffle，不加正则或动量，**每次从零初值开始**。

- 配置 A：`lr=0.25`。
- 配置 B：`lr=3.0`。
- 都运行 8 次更新；在更新前记 step 0，此后每次更新后重新前向记录 step 1–8 的同一目标。只改变学习率。

### 输出与验收

1. 先手算第一次梯度与两种学习率的下一步参数，再运行对照。不提供完整脚本或填好的曲线。
2. 表格包含 `run_id, lr, step, w, b, loss, grad_norm`，梯度范数要标明属于更新前状态。两个配置画在同一个 step 横轴上，或交可直接绘制的数表；不是把两个最终数叫作“曲线”。
3. 正常配置向拟合目标靠近；失败配置表现出越过最优点并增大的损失。保留失败值，不用裁剪梯度、换损失、改数据或悄悄调小学习率来遮住它。这个有限八步实验应无需等待 NaN 才能说明失败。
4. 相同环境从初值重跑配置 B，参数/损失序列应在容差内复现。解释“梯度方向正确，但一步太大”与“loss 实现错误”的区别，并指出修复只需改变哪一个超参数。
5. 将这个局部结论迁回任务 1 或 2：写明若比较真实训练的 batch size，固定 epoch 会改变更新步数，固定 step 又改变见过的样本数，报告必须同时给两者；不能声称本二样本结论证明所有数据上的最佳学习率。

这是完整的基础任务 4。可选扩展为教材 3.7 练习第 1 项：在真实 Fashion-MNIST 上只改变 batch size 或学习率，使用同一数据划分、初值和预算，并保留所有运行。扩展不取代上面的确定性失败曲线，也不要求为了某个准确率持续刷参数。

## 完成自查

四个 task id 均有实际输入、输出、检查和解释；能说明半平方损失的系数、`Linear.weight` 的方向、尾 batch 的分母、logits 的含义、模式与求导的区别、以及失败曲线的控制变量。遇到错误先用[实现指导](#/c/d2l-pytorch-2021/lab/linear-training?v=guide)定位一个环节，不向 AI 索取整套作业与报告。

## 来源、数据许可与执行边界

### 实际阅读的教材范围

阿斯顿·张、扎卡里 C. 立顿、李沐、亚历山大 J. 斯莫拉及 d2l-ai/d2l-zh 贡献者，《动手学深度学习》中文第二版。以下均实际阅读**节选正文和对应 PyTorch/通用代码分支**，不声称通读所有框架实现、附录或参考论文；固定当前提交不是 2021 快照。

| 固定来源 | 使用范围与任务映射 |
|---|---|
| [3.1 线性回归](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression.md) | 线性模型、损失、解析解与 SGD、预测；任务 1/4 |
| [3.2 从零实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-scratch.md) | 合成数据、批处理、参数、模型、损失、SGD、训练、练习第 5–7 项；任务 1/4 |
| [3.3 简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-concise.md) | DataLoader、Linear、初始化、MSE、SGD、训练及练习；任务 1 |
| [3.4 softmax 回归](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/softmax-regression.md) | 分类、架构、softmax、batch、交叉熵与导数、预测评估；任务 2/3 |
| [3.5 图像分类数据集](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/image-classification-dataset.md) | Fashion-MNIST、标签/形状、读取小批量及整合加载器；任务 2/3 |
| [3.6 从零 softmax](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/softmax-regression-scratch.md) | 参数、softmax、标签索引、accuracy、评估/训练及稳定性练习；任务 2/3 |
| [3.7 简洁 softmax](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/softmax-regression-concise.md) | Flatten/Linear、稳定损失、优化训练、超参数习题；任务 2/4 |

**编者改编**：固定种子与小规模、从官方训练集另拆验证集、冻结模型重评训练指标、无泄漏干预、尾批累计器、两样本失败夹具与局部容差，均为本站新增。教材演示中直接使用官方测试集的做法不作为本页调参协议。源码原件只改后缀为 `.txt`，置于 `sources/p2-linear-training/`，哈希及精确阅读行范围见该目录 manifest。

教材仓库根 [LICENSE 为 Apache-2.0](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)，许可原件与边界见 `sources/p1-shared/book-version.json`；`setup.py` 的 MIT-0 包字段另记，不外推书外资源。

### 官方数据与 API

已核实 [Fashion-MNIST 官方 README](https://github.com/zalandoresearch/fashion-mnist) 的数据规模、格式、类别、下载与校验表，及独立 [MIT LICENSE](https://github.com/zalandoresearch/fashion-mnist/blob/master/LICENSE)（2017 Zalando SE）。数据作者为 Han Xiao、Kashif Rasul、Roland Vollgraf；此处不新增论文必读。只存来源和许可文本，不转载图片或分发数据。

| 官方 gzip 文件 | 官方公布 MD5（压缩文件） |
|---|---|
| train-images-idx3-ubyte.gz | `8d4fb7e6c68d591d4c3dfef9ec88bf0d` |
| train-labels-idx1-ubyte.gz | `25c81989df183df01b3e8a0aad5dffbe` |
| t10k-images-idx3-ubyte.gz | `bef4ecab320f06d8554ea6380940ec79` |
| t10k-labels-idx1-ubyte.gz | `bb300cfdad3c16e7a12a480ee83cd310` |

MD5 用于比对官方历史文件和传输完整性，不当作抗恶意篡改保证；自己运行时另存实际 SHA-256、来源 URL、字节数与下载日期。四份对应数据位于[官方 data/fashion 目录](https://github.com/zalandoresearch/fashion-mnist/tree/master/data/fashion)。

已读 [vision 0.20 FashionMNIST API](https://docs.pytorch.org/vision/0.20/generated/torchvision.datasets.FashionMNIST.html)、[ToTensor API](https://docs.pytorch.org/vision/0.20/generated/torchvision.transforms.ToTensor.html)，并核对 [v0.20.1 mnist.py](https://github.com/pytorch/vision/blob/v0.20.1/torchvision/datasets/mnist.py) 的加载路径、FashionMNIST 下载源和校验常量；另读 [PyTorch 2.5 CrossEntropyLoss](https://docs.pytorch.org/docs/2.5/generated/torch.nn.CrossEntropyLoss.html) 的 logits、标签与归约合同，以及 [Autograd mechanics](https://docs.pytorch.org/docs/2.5/notes/autograd.html) 的 grad/no-grad/evaluation mode 部分。API 阅读不等于已完成安装或数据训练，实测证据统一见课程公共资料。

本批实际的数据获取采用**官方 GitHub HTTPS raw → 校验四份 gzip → 解压到运行时缓存**，记录在 `sources/p2-shared/dataset-acquisition.json`：四份 MD5 与官方表一致，IDX 头分别对应 60000/10000 张 28×28 图像及同数标签，没有随站点发布数据。此缓存路线随后以 `download=False` 读取；本批没有尝试旧 HTTP S3 镜像，因此不声称默认 `download=True` 成功，也不声称 S3 已失效。下载与头校验不等于完成训练或测试集评估。

### 视频与尚未执行的范围

课表对应 [线性回归 BV1PX4y1g7KC](https://www.bilibili.com/video/BV1PX4y1g7KC) 与 [Softmax BV1K64y1Q7wu](https://www.bilibili.com/video/BV1K64y1Q7wu)。本页依据教材和官方数据/API，未据视频讲授、演示、QA 或历史 Notebook 编写，不声称课堂实验复现；分P元数据与字幕获取状态归相应 LEC8/9 来源记录。视频版权不受教材或数据许可覆盖。

正文是学习者需要独立实施的规格，不是已经完成的学生报告。基础机制验证不等于两条完整回归训练、全部任务作业、55000/5000 全量训练、10000 测试评估、GPU/MPS/CUDA 或旧 Notebook 均已通过；精确运行配置与结果以[课程公共资料](#/c/d2l-pytorch-2021)及批次共享验收记录为准。
