---
title: 从零训练循环与线性模型：实现与排查指导
kind: 编者阶段练习指导（非官方 Lab 解答）
source: 固定中文第二版 3.1–3.7 节选及 PyTorch 分支；Fashion-MNIST 官方数据说明；PyTorch/torchvision API
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
video: 未依据视频演示或问答制作，不是课堂解答转录
license: 教材源码 Apache-2.0；Fashion-MNIST 官方仓库 MIT；本文为编者自主路线与排错提示
status: 独立实现指导；不是完整答案或执行报告，实际验证边界见课程公共资料
execution: 不提供完整训练脚本、已填结果或模型权重
version_boundary: 当前中文第二版固定源码，不是 2021 课程教材快照
---

# 实现与排查指导

## 先把一个 batch 解释清楚

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

打开[实验说明](#/c/d2l-pytorch-2021/lab/linear-training?v=zh)，数据、四个 task id、固定配置和验收以那里为准。本页只提供路线、不变量、排错顺序和逐级提示，不重印任务，不给可直接复制的整套程序。

> 本地练习使用自己的Python/PyTorch环境。环境安装和实际 CPU 验收看[课程公共资料](#/c/d2l-pytorch-2021)，不照抄旧 Notebook 安装单元。真实 Fashion-MNIST 的下载/校验仍是任务的一部分；无法下载时记录阻塞，不能用合成图像冒充完成。

建议按“形状 → 一次前向 → 单个梯度 → 一次更新 → 一轮 → 多轮”的顺序增加程序。每一级先预测、后运行、再解释。把一百行程序交给 AI 整体重写，通常会抹掉最值得定位的错误。

自己的程序可以分为四个简单职责，无须先造训练框架：

| 职责 | 读什么 | 允许改变什么 |
|---|---|---|
| 数据准备 | 官方文件、固定划分规则 | 产生索引与固定预处理，不接触模型 |
| 训练一轮 | 训练加载器、模型、优化器 | 参数、梯度、训练计数 |
| 评估 | 冻结模型、指定加载器 | 只累计本地指标，不写参数或梯度 |
| 实验记录 | 配置、测量值 | 写文本/CSV，不保留整批计算图 |

日志需要标量时再 `.item()`；不要把它接回待求导的损失。参数历史只有在确实需要跨更新比较时才做 `detach().clone()`；仅保存 Python 对象引用不是快照。

## 任务 1：先定位“等价”的前提

### 路线

先只实现从零前向与半平方损失，用一个 batch 手算某个残差及其对一个权重的影响，再加入 autograd 和更新。随后建立高层版，对齐初始数值、输入顺序、dtype、损失系数和归约。最后才把两条路线接到多轮训练。

`nn.Linear` 存储的是 `(out_features,in_features)`；手写 $Xw$ 的权重方向可能不同。应比较映射后的同一对象，不要直接拿 shape 不同的张量相减，让广播把错误掩盖。

### 必须始终成立的不变量

- 预测与标签完全同形；batch 中只有一个样本也如此。
- 同一初值与同一 batch 应给同一预测；同一目标应给同一梯度。
- 一次 backward 只生成/累积梯度，不更新参数；更新只在其后发生。
- mean 与 sum 只选一套缩放规则。**“mean 反传，再除 batch size”是重复归一化。**
- 从零更新放在 `no_grad` 中，之后清理梯度并重新前向；禁止 `.data` 和依赖 `retain_graph=True` 重用旧训练图。
- 每条对照均从独立的相同参数快照开始，不共享参数存储，不从上一条已训练模型继续。

### 提示层级

<details>
<summary>提示 1：两条损失刚好差两倍，先看哪里？</summary>

先把两个数学定义写出来，而不是先改学习率。教材半平方与框架默认 MSE 的系数不同；先统一目标，才比较优化器实现。再核对是否对 `(B,1)` 求 mean，还是把每样本损失直接求和。

</details>

<details>
<summary>提示 2：只有最后一个 batch 对不上，怎样缩小问题？</summary>

单独打印最后一批的实际 B、损失求和、损失均值和梯度范数。分母应该来自这批输入，而不是配置值 64。把两条路线恢复到同一初值，只跑尾批的一次更新；不需要反复执行整段训练。

</details>

<details>
<summary>提示 3：梯度正确但参数不动，怎样分辨？</summary>

分别记录 backward 前、backward 后、step 后的参数差。若前两者相同是正常现象；检查 step 是否真的更新模型当前使用的参数、梯度是否在更新前被清掉，以及是否把新张量赋给局部变量而没有更新模型持有的对象。

</details>

## 任务 2：数据加载与数值稳定分开排查

### 路线 A：先拿到可信数据

下载、解压、读取、变换是四个环节。先对压缩文件核对官方 MD5，再核对图像/标签数量、标签范围和一对样本形状；不要用“下载函数没报错”替代数据核验。已存在的解压缓存不意味着每次都会重新验证原 gzip 哈希，运行记录需保留自己的校验结果。

`FashionMNIST(train=True)` 是官方训练池，`train=False` 是官方测试池。先保存固定随机排列划分，再对训练/验证候选取规定前缀。小规模前缀仍来自真实数据，不是另造小数据集；完整扩展仅增加候选中使用的索引数量，不重定义测试集。

`ToTensor` 对这里的灰度 PIL 图像进行通道布局转换和除以 255；如果直接访问 `.data` 得到原始 uint8 张量，不会自动执行 transform。不要把 0–255 输入和 0–1 输入混在两条对照中，也不要重复除以 255。类别标签无需 one-hot，保持 long 索引即可。

### 路线 B：先分清三个输出

- **logits**：实数得分，没有“每行和为 1”的要求。
- **softmax 概率**：在类别轴归一化，每行是一个分布。
- **交叉熵**：每个样本一个损失，再按实际 batch 求平均用于更新。

训练采用 logits 与框架稳定交叉熵。为了学习机制，局部稳定实现只与框架作小核对；不要把不稳定教学公式搬进完整训练后，用概率裁剪偷偷改变目标。

<details>
<summary>提示 1：输入 `(B,1,28,28)` 为什么不能整体 flatten？</summary>

先给轴命名：样本、通道、高、宽。每个样本应各自产生 784 个特征，batch 轴必须保留。检查 B=1 时的行为；无参数 `squeeze()` 容易把样本轴一起去掉。

</details>

<details>
<summary>提示 2：减去最大值以后，为什么还可能有无穷损失？</summary>

减最大值控制了指数上溢，但非常小的正确类概率仍可能下溢为 0。比较“先得到概率再取 log”和“直接在对数表达式中消去 exp/log”的计算路径。只给概率加 epsilon 会改变损失及梯度，不是本题的稳定等价实现。

</details>

<details>
<summary>提示 3：如何核对类别轴而不抄整段函数？</summary>

只拿两张图，画出两行十列：每行属于一张图，每列属于一个类别。概率总和、最大类别与标签索引都围绕每一行计算。标签索引应每行选一格，而不是给所有行选同一列。

</details>

### 当基线不学习时

按顺序排查：原图/标签是否对齐 → 像素尺度 → 输出与标签 shape → logits 是否被重复 softmax → loss 是否仍连计算图 → 梯度有限且非零 → step 是否更新 → mean 是否重复除 B。基础路线的单样本尾批会让在线曲线抖动，不能用“每一步必须下降”断言；冻结模型重评整个训练子集，才比较同一个目标。

验证 accuracy 只有 73 个样本，跳变一个正确样本就会改变比例；它不是稳定的全量泛化估计。不得按验证表现重新抽种子、重新挑索引、删错例，或与教材全量成绩作同尺度比较。

## 任务 3：四个开关不是一个开关

### 路线

先用同一模型做四格前向观察，暂不更新；随后在训练样本上单独做一次诊断 backward；最后接正式训练/评估分支。诊断梯度必须清掉，正式验证不反传。不要为了展示“eval 仍可求梯度”就在验证集上反传，留下可能被下一次 step 消费的梯度。

| 概念 | 管什么 | 不自动管什么 |
|---|---|---|
| `train()` / `eval()` | 模块的训练行为开关 | 不关闭 autograd、不清空梯度、不禁止 step |
| grad / `no_grad()` | 普通运算是否记录求导图 | 不清除旧梯度、不阻止用旧梯度 step |
| `backward()` | 累加当前目标的梯度 | 不执行优化器更新 |
| `step()` | 按优化规则改变参数 | 不判断样本属于训练还是验证 |

纯线性模型在 train/eval 下数值相同是正确现象，因为没有 Dropout/BatchNorm 等模式相关层。不能为了让四格输出不同，偷偷改变题目模型；这里先看 `training` 和求导状态。

### 指标累计器只维护三个量

对本题无类别权重、无忽略标签的分类目标，累计损失总和、正确数、样本数即可。若输入为每批平均损失，先还原该批损失总和；epoch 最后才统一除总样本数。不要把计算图中的整个 loss 张量长期塞进日志列表。

检查固定 73 个样本在 B=64 与 B=32 下的评估是否一致。这是在**冻结模型**上改评估分批，不是重训后比较两种训练 batch size；后者参数可能不同，不能拿来测累计器。

<details>
<summary>提示 1：评估前梯度非零，评估后还非零，是泄漏吗？</summary>

不一定。`no_grad` 不清除旧 `.grad`，所以应比较评估前后的真实快照，确认没有新累积。仅看“非零”会误判；仅看参数没变也不足以排除误 backward，因为梯度可能留到后续更新才生效。

</details>

<details>
<summary>提示 2：为什么两个 batch 的平均不能直接再平均？</summary>

一个 batch 代表四个样本，另一个只代表一个。先写出每个样本的权重；直接对两个 mean 平均，就把尾批的单个样本赋予了过大的权重。accuracy 同理，先累加正确数，不能平均两个百分比。

</details>

<details>
<summary>提示 3：验证标签干预后，训练参数变了，先检查什么？</summary>

核对训练过程是否混用了验证加载器、是否评估中调用了 backward/step、是否从验证统计量拟合预处理。再看两次初值与训练顺序是否真的一致，是否有验证触发的早停或学习率调度。本任务固定训练预算，不含这些自适应决策。

</details>

## 任务 4：让失败有可重复的原因

先只实现二样本夹具的一次更新，写出残差对 w 和 b 的贡献。两条样本对称，适合检查偏置与符号；先手算第一步，再让程序继续。不要先看完整曲线后再倒填预测。

控制变量表至少有：数据、初始化、dtype、损失、batch、顺序、更新数、学习率。两行配置仅学习率一列不同。记录 step 0 的共同起点，确保每个 loss 都在相同相位测量——本题规定为更新后的重新前向。梯度若来自更新前，就在列名或说明里明确，不把前后状态混为同一时刻。

<details>
<summary>提示 1：较大步长失败是否证明梯度错了？</summary>

梯度提供当前位置的局部方向，不保证任意距离都下降。在一维参数轴上画当前位置、目标位置与下一点，观察是否越过目标，下一步是否又越到另一侧。无需先补完整优化理论。

</details>

<details>
<summary>提示 2：怎样区分可复现失败与随机抖动？</summary>

二样本实验没有 shuffle 或噪声；从相同初值、同一配置重新运行，参数/损失序列应吻合。真实 Fashion-MNIST 的在线小批量曲线则混有样本差异与持续变化的参数，不能凭一处上升就断言发散。

</details>

<details>
<summary>提示 3：可选 batch size 实验为什么要同时记 epoch 与 step？</summary>

epoch 统计“训练数据被完整走过几轮”，step 统计“参数更新几次”。固定 epoch 时大 batch 通常更新更少；固定 step 时大 batch 通常见过更多样本。先选比较目的，声明预算，不在结论中把两种公平性混为一谈。

</details>

## 症状到证据的最短路径

| 症状 | 先看证据，不先改什么 |
|---|---|
| 下载失败 | 来源 URL、HTTP/网络错误、缓存文件与校验；不换 FakeData |
| loss 为 NaN/Inf | 输入有限性、logits 幅度、是否直接 exp/log、学习率；不先裁剪遮盖 |
| loss shape 变成 `(B,B)` | 预测/标签是否 `(B,1)` 与 `(B,)` 混用 |
| CPU 真实子集似乎没学 | 数据是否真的读入、梯度/参数差、训练目标前后值；不先上 GPU |
| 最后一批报维度错 | B=1 是否被 squeeze、是否硬编码 64 |
| train/eval 输出相同 | 本模型是否只有 Linear；不假设求导已关闭 |
| 评估改变了后续训练 | 参数及梯度前后快照、评估是否误 step、诊断梯度是否清掉 |
| 改评估 batch 指标变了 | 是否丢尾批、均值再平均、模型未冻结、样本集变了 |
| 两条 SGD 路线不同 | 初值、权重方向、半平方系数、归约、实际 B、更新顺序 |

## 怎样向 AI 求助

给出一个失败断言、该 batch 的 shape、损失定义、相关局部实现和运行前预测，请 AI 判断哪一个不变量被破坏。可以请求解释 `Linear.weight` 的方向、半平方系数或数值下溢；不请求完整四题脚本、成品曲线或替你编造运行记录。最终需要自己实现、运行并解释结果。

## 来源与边界

本指导对应的实际读取范围、原件哈希与任务映射见 `sources/p2-linear-training/manifest-fragment.json`；[实验说明页底](#/c/d2l-pytorch-2021/lab/linear-training?v=zh)列出全部教材固定链接、官方数据校验与许可。这里采用的是**3.1–3.7 节选正文及 PyTorch/通用分支**，不是全框架源码通读或 2021 视频复现。

- 回归路线：[3.2 从零实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-scratch.md)、[3.3 简洁实现](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/linear-regression-concise.md)，使用数据批处理、半平方、优化/训练及学习率练习。
- 分类与稳定性：[3.5 数据集](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/image-classification-dataset.md)、[3.6 从零 softmax](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/softmax-regression-scratch.md)、[3.7 简洁 softmax](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_linear-networks/softmax-regression-concise.md)，使用加载、标签索引、累计、训练和稳定损失。
- 数据/API：[Fashion-MNIST 官方说明](https://github.com/zalandoresearch/fashion-mnist)、[独立 MIT 许可](https://github.com/zalandoresearch/fashion-mnist/blob/master/LICENSE)、[vision 0.20 FashionMNIST](https://docs.pytorch.org/vision/0.20/generated/torchvision.datasets.FashionMNIST.html)、[ToTensor](https://docs.pytorch.org/vision/0.20/generated/torchvision.transforms.ToTensor.html)、[PyTorch 2.5 CrossEntropyLoss](https://docs.pytorch.org/docs/2.5/generated/torch.nn.CrossEntropyLoss.html)、[Autograd mechanics 的模式区分](https://docs.pytorch.org/docs/2.5/notes/autograd.html)。这些均已实际读取，不额外要求论文。

本批数据获取证据采用官方 GitHub HTTPS raw 手工缓存路线，四份 gzip 的 MD5 与 IDX 头核验见 `sources/p2-shared/dataset-acquisition.json`。加载时使用预置缓存与 `download=False`；没有测试旧 HTTP S3 镜像的可达性。真实训练、依赖和机制检查的实际范围仍以课程公共资料为准，不能由下载成功推断训练已完成。

指导中的划分纪律、干预检验、四格观察、尾批统计、局部失败夹具为编者工程补充，不冒充官方习题原文或官方评分。教材 Apache-2.0、数据仓库 MIT、视频版权分别处理。未在本页提供或宣称执行完整学生解答、旧 Notebook、全量 Fashion-MNIST 训练/测试或 GPU 路线；实际独立机制验收以课程公共资料与共享批次记录为准。
