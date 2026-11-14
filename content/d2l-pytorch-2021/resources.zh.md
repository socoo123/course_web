---
source: 李沐《动手学深度学习》2021 中文课程官方课表；《动手学深度学习》中文第二版
status: 已完成LEC1–35学习笔记、自绘图及前五项实验说明/指导；其中LEC30为官方竞赛来源导读，其他笔记不冒充课堂整理。35个BV共105P公开字幕均为空，完整课堂稿持续阻塞。页头官方入口与核实时长按全部分P合计；CPU性能微基准、梯度与通信预算推演不等于真实多GPU实测或学生作业完成。
license: 本页为编者自主课程导航；教材、代码、视频分别按原始许可处理，视频授权不由教材许可推定。
---

# 动手学深度学习：公共资料、完整课表与实践路线

## 这门课要学到什么

从一个张量的形状开始，理解神经网络如何计算、如何训练，以及为什么采用不同的结构。用 PyTorch 把原理落实成小程序，再观察训练稳定性、泛化、内存和运行时间，建立继续学习 CS336 所需的模型直觉与工程基础。

这里采用**李沐 2021 年中文 PyTorch 课程的完整顺序**，不是只挑 Transformer 的速成路线：数学回顾、MLP、CNN、计算机视觉、RNN、机器翻译、注意力、Transformer、BERT、优化与总结全部保留。竞赛发布、案例和回顾也保留在课程中，但完整学课不等于必须参加历史竞赛或运行全部大规模训练。

不增加独立数学公开课、CS229、CS224N 或刷论文任务。数学遗忘时，在当前课程中补回符号、矩阵运算、梯度和概率；先用小数值例子理解，再回到模型。课程外论文不是本路线的必读要求。

## 三类内容怎样配合

- **课程笔记**：解释核心问题、必要数学、张量形状、设计取舍、易错点和自测，不按视频顺序重复讲一遍。
- **中文译稿**：沿用网站标签；本课原视频是中文，实际内容应为按真实时间轴整理的**中文课堂讲授、演示和问答**，不是再翻译一次。课堂截图只放这里。
- **课程资料**：仅承载课堂之外确有必要的独立阅读；教材原本已是中文，优先定位官方章节，不机械重写全文，也不重复课堂幻灯片。

共享教材、环境和代码入口集中在本页文末。学习某一讲时，先看课堂与笔记，卡在概念时再回到对应教材；不要把每个参考链接都变成必须完成的阅读任务。

## 全课内容大纲

| 阶段 | 内容范围 | 应形成的理解 |
|---|---|---|
| 入门与数学回顾 | 课程介绍、安装、数据操作与预处理、线性代数、矩阵计算、自动求导 | 数据怎样变成张量；运算的输入输出维度；梯度在描述什么 |
| 基础模型与训练 | 线性回归、Softmax、损失、MLP、模型选择、过拟合、权重衰减、Dropout、数值稳定性、初始化 | 数据、模型、损失、优化器和训练循环如何配合；训练误差与泛化为何不同 |
| PyTorch 模块与卷积网络 | 层与块、参数、读写、GPU、卷积/填充/步幅/通道/池化、LeNet、AlexNet、VGG、NiN、GoogLeNet、BatchNorm、ResNet | 从简单网络到模块化模型；局部性、通道、残差与归一化各解决什么问题 |
| 计算与性能 | CPU/GPU、专有硬件、数据并行、多 GPU 训练及实现、分布式训练 | 参数、数据和计算放在哪里；计算与通信怎样影响速度；区分理解机制与必须具备多卡硬件 |
| 计算机视觉 | 增广、微调、分类案例、目标检测与相关模型、分割、转置卷积、风格迁移 | 分类、检测与分割的任务和输出有什么不同；预训练模型怎样迁移到新数据 |
| 序列与循环网络 | 序列模型、文本预处理、语言模型、RNN、从零与简洁实现、GRU、LSTM、深层与双向 RNN | 怎样组织序列样本；状态如何传递；训练时可见的信息与预测时可见的信息如何区分 |
| 机器翻译与注意力 | 翻译数据、编码器—解码器、seq2seq、束搜索、注意力机制与分数、带注意力的 seq2seq | 条件生成怎样训练和解码；注意力怎样在序列中选择信息 |
| Transformer 与 BERT | 自注意力、位置编码、Transformer、BERT 结构/数据/预训练/微调、自然语言推理 | 追踪输入到输出的形状；区分编码器—解码器、掩码语言模型与下一 token 预测 |
| 优化与收尾 | 课程末尾的优化算法专题、课程总结与进阶方向 | 将训练现象连接回优化选择；整理模型设计与实现经验，为 CS336 建立问题清单 |

以上是编者划分的学习阶段，不是官方额外增加的讲次。基础优化方法已在前段出现，最后的优化专题仍按原课顺序保留；BERT 不是 GPT，不能把两者的训练目标混为一谈。

## 完整课表

按官方课表首次出现顺序，同一 B 站 BV 上传的分 P 主题归为一讲，共 **73 个站内讲次、103 个原课表教学条目**。LEC 编号是本站编排，不是视频标题中的官方编号；原课表的 11 个休课条目不占讲次。日期为 2021 年原课表日期，不是要求今天按周赶完的学习期限。

点击讲次进入本站阅读页；原视频入口集中在文末「引用与来源」。同一上传的多主题完整保留，不能只看首个分 P 就认为整讲已学完。

### 深度学习基础

| 讲次 | 原课表日期 | 本讲全部主题 |
|---|---|---|
| [LEC 1](#/c/d2l-pytorch-2021/lec/lec01?v=notes) | 3月20日 | 课程安排 |
| [LEC 2](#/c/d2l-pytorch-2021/lec/lec02?v=notes) | 3月20日 | 深度学习介绍 |
| [LEC 3](#/c/d2l-pytorch-2021/lec/lec03?v=notes) | 3月20日 | 安装 |
| [LEC 4](#/c/d2l-pytorch-2021/lec/lec04?v=notes) | 3月20日 | 数据操作；数据预处理 |
| [LEC 5](#/c/d2l-pytorch-2021/lec/lec05?v=notes) | 3月21日 | 线性代数；[补充] 按特定轴求和 |
| [LEC 6](#/c/d2l-pytorch-2021/lec/lec06?v=notes) | 3月21日 | 矩阵计算 |
| [LEC 7](#/c/d2l-pytorch-2021/lec/lec07?v=notes) | 3月21日 | 自动求导 |
| [LEC 8](#/c/d2l-pytorch-2021/lec/lec08?v=notes) | 3月27日 | 线性回归；基础优化方法；线性回归的从零开始实现；线性回归的简洁实现 |
| [LEC 9](#/c/d2l-pytorch-2021/lec/lec09?v=notes) | 3月28日 | Softmax 回归；损失函数；图像分类数据集；Softmax 回归的从零开始实现；Softmax 回归的简洁实现 |
| [LEC 10](#/c/d2l-pytorch-2021/lec/lec10?v=notes) | 4月10日 | 感知机；多层感知机；多层感知机的从零开始实现；多层感知机的简洁实现 |
| [LEC 11](#/c/d2l-pytorch-2021/lec/lec11?v=notes) | 4月11日 | 模型选择；欠拟合和过拟合 |
| [LEC 12](#/c/d2l-pytorch-2021/lec/lec12?v=notes) | 4月17日 | 权重衰减 |
| [LEC 13](#/c/d2l-pytorch-2021/lec/lec13?v=notes) | 4月17日 | Dropout |
| [LEC 14](#/c/d2l-pytorch-2021/lec/lec14?v=notes) | 4月18日 | 数值稳定性；模型初始化和激活函数 |
| [LEC 15](#/c/d2l-pytorch-2021/lec/lec15?v=notes) | 4月18日 | 实战 Kaggle 比赛：预测房价；竞赛 预测房价 |

### 卷积神经网络

| 讲次 | 原课表日期 | 本讲全部主题 |
|---|---|---|
| [LEC 16](#/c/d2l-pytorch-2021/lec/lec16?v=notes) | 4月24日 | 模型构造；参数管理；自定义层；读写文件 |
| [LEC 17](#/c/d2l-pytorch-2021/lec/lec17?v=notes) | 4月24日 | GPU |
| [LEC 18](#/c/d2l-pytorch-2021/lec/lec18?v=notes) | 5月15日 | 预测房价竞赛总结 |
| [LEC 19](#/c/d2l-pytorch-2021/lec/lec19?v=notes) | 5月15日 | 从全连接层到卷积；图像卷积 |
| [LEC 20](#/c/d2l-pytorch-2021/lec/lec20?v=notes) | 5月16日 | 填充和步幅 |
| [LEC 21](#/c/d2l-pytorch-2021/lec/lec21?v=notes) | 5月16日 | 多输入多输出通道 |
| [LEC 22](#/c/d2l-pytorch-2021/lec/lec22?v=notes) | 5月22日 | 池化层 |
| [LEC 23](#/c/d2l-pytorch-2021/lec/lec23?v=notes) | 5月22日 | 卷积神经网络（LeNet） |
| [LEC 24](#/c/d2l-pytorch-2021/lec/lec24?v=notes) | 5月23日 | 深度卷积神经网络（AlexNet） |
| [LEC 25](#/c/d2l-pytorch-2021/lec/lec25?v=notes) | 5月23日 | 使用块的网络（VGG） |
| [LEC 26](#/c/d2l-pytorch-2021/lec/lec26?v=notes) | 5月29日 | 网络中的网络（NiN） |
| [LEC 27](#/c/d2l-pytorch-2021/lec/lec27?v=notes) | 5月29日 | 含并行连结的网络（GoogLeNet） |
| [LEC 28](#/c/d2l-pytorch-2021/lec/lec28?v=notes) | 5月30日 | 批量归一化 |
| [LEC 29](#/c/d2l-pytorch-2021/lec/lec29?v=notes) | 5月30日 | 残差网络（ResNet） |
| [LEC 30](#/c/d2l-pytorch-2021/lec/lec30?v=notes) | 5月30日 | 竞赛 图片分类 |

### 计算机视觉

| 讲次 | 原课表日期 | 本讲全部主题 |
|---|---|---|
| [LEC 31](#/c/d2l-pytorch-2021/lec/lec31?v=notes) | 6月5日 | 硬件：CPU和GPU |
| [LEC 32](#/c/d2l-pytorch-2021/lec/lec32?v=notes) | 6月6日 | 更多的专有硬件 |
| [LEC 33](#/c/d2l-pytorch-2021/lec/lec33?v=notes) | 6月6日 | 多GPU训练 |
| [LEC 34](#/c/d2l-pytorch-2021/lec/lec34?v=notes) | 6月19日 | 多GPU训练的实现 |
| [LEC 35](#/c/d2l-pytorch-2021/lec/lec35?v=notes) | 6月19日 | 分布式训练 |
| [LEC 36](#/c/d2l-pytorch-2021/lec/lec36?v=notes) | 6月20日 | 图像增广 |
| [LEC 37](#/c/d2l-pytorch-2021/lec/lec37?v=notes) | 6月20日 | 微调 |
| [LEC 38](#/c/d2l-pytorch-2021/lec/lec38?v=notes) | 6月26日 | 实战 Kaggle 比赛：图像分类（CIFAR-10） |
| [LEC 39](#/c/d2l-pytorch-2021/lec/lec39?v=notes) | 6月26日 | 实战 Kaggle 比赛：狗的品种识别（ImageNet Dogs） |
| [LEC 40](#/c/d2l-pytorch-2021/lec/lec40?v=notes) | 6月27日 | 物体检测；边缘框实现；物体检测数据集 |
| [LEC 41](#/c/d2l-pytorch-2021/lec/lec41?v=notes) | 6月27日 | 锚框 |
| [LEC 42](#/c/d2l-pytorch-2021/lec/lec42?v=notes) | 6月27日 | 竞赛 树叶分类竞赛总结 |
| [LEC 43](#/c/d2l-pytorch-2021/lec/lec43?v=notes) | 7月3日 | 区域卷积神经网络（R-CNNs）；单发多框检测（SSD）；你只看一次（YOLO） |
| [LEC 44](#/c/d2l-pytorch-2021/lec/lec44?v=notes) | 7月4日 | 多尺度物体检测实现；SSD 实现 |
| [LEC 45](#/c/d2l-pytorch-2021/lec/lec45?v=notes) | 7月10日 | 语义分割；语义分割数据集 |
| [LEC 46](#/c/d2l-pytorch-2021/lec/lec46?v=notes) | 7月10日 | 转置卷积 |
| [LEC 47](#/c/d2l-pytorch-2021/lec/lec47?v=notes) | 7月10日 | 转置卷积是一种卷积 |
| [LEC 48](#/c/d2l-pytorch-2021/lec/lec48?v=notes) | 7月11日 | 全连接卷积神经网络（FCN） |
| [LEC 49](#/c/d2l-pytorch-2021/lec/lec49?v=notes) | 7月11日 | 样式迁移 |
| [LEC 50](#/c/d2l-pytorch-2021/lec/lec50?v=notes) | 7月11日 | 竞赛 目标检测 |

### 循环神经网络

| 讲次 | 原课表日期 | 本讲全部主题 |
|---|---|---|
| [LEC 51](#/c/d2l-pytorch-2021/lec/lec51?v=notes) | 7月17日 | 序列模型 |
| [LEC 52](#/c/d2l-pytorch-2021/lec/lec52?v=notes) | 7月17日 | 文本预处理 |
| [LEC 53](#/c/d2l-pytorch-2021/lec/lec53?v=notes) | 7月18日 | 语言模型和数据集 |
| [LEC 54](#/c/d2l-pytorch-2021/lec/lec54?v=notes) | 7月18日 | 循环神经网络 |
| [LEC 55](#/c/d2l-pytorch-2021/lec/lec55?v=notes) | 7月24日 | 循环神经网络的从零开始实现；循环神经网络的简洁实现 |
| [LEC 56](#/c/d2l-pytorch-2021/lec/lec56?v=notes) | 7月25日 | 门控循环单元（GRU） |
| [LEC 57](#/c/d2l-pytorch-2021/lec/lec57?v=notes) | 7月25日 | 长短期记忆网络（LSTM） |
| [LEC 58](#/c/d2l-pytorch-2021/lec/lec58?v=notes) | 7月25日 | 深层循环神经网络 |
| [LEC 59](#/c/d2l-pytorch-2021/lec/lec59?v=notes) | 7月25日 | 双向循环神经网络 |
| [LEC 60](#/c/d2l-pytorch-2021/lec/lec60?v=notes) | 8月7日 | 机器翻译与数据集 |
| [LEC 61](#/c/d2l-pytorch-2021/lec/lec61?v=notes) | 8月7日 | 编码器-解码器结构 |
| [LEC 62](#/c/d2l-pytorch-2021/lec/lec62?v=notes) | 8月7日 | 序列到序列学习（seq2seq） |
| [LEC 63](#/c/d2l-pytorch-2021/lec/lec63?v=notes) | 8月7日 | 束搜索 |

### 注意力机制

| 讲次 | 原课表日期 | 本讲全部主题 |
|---|---|---|
| [LEC 64](#/c/d2l-pytorch-2021/lec/lec64?v=notes) | 8月8日 | 注意力机制 |
| [LEC 65](#/c/d2l-pytorch-2021/lec/lec65?v=notes) | 8月8日 | 注意力分数 |
| [LEC 66](#/c/d2l-pytorch-2021/lec/lec66?v=notes) | 8月8日 | 使用注意力机制的seq2seq |
| [LEC 67](#/c/d2l-pytorch-2021/lec/lec67?v=notes) | 8月14日 | 自注意力和位置编码 |
| [LEC 68](#/c/d2l-pytorch-2021/lec/lec68?v=notes) | 8月14日 | Transformer |
| [LEC 69](#/c/d2l-pytorch-2021/lec/lec69?v=notes) | 8月15日 | BERT；BERT预训练数据集；预训练BERT |
| [LEC 70](#/c/d2l-pytorch-2021/lec/lec70?v=notes) | 8月15日 | 微调BERT；自然语言推理和数据集；自然语言推理：微调BERT |
| [LEC 71](#/c/d2l-pytorch-2021/lec/lec71?v=notes) | 8月15日 | 竞赛 目标检测总结 |
| [LEC 72](#/c/d2l-pytorch-2021/lec/lec72?v=notes) | 8月21日 | 优化算法 |
| [LEC 73](#/c/d2l-pytorch-2021/lec/lec73?v=notes) | 8月21日 | 课程总结和进阶学习 |

## 数学忘了怎样继续

每遇到一个公式，先确认三个问题：**符号是什么、输入输出形状是什么、用两三个数字能否算出一个例子**。然后再问它在模型里承担什么职责。

- 线性代数：先掌握向量、矩阵乘法、按轴求和和广播，不以补完特征分解或严格证明为开课条件。
- 微积分与自动求导：先理解变化率、偏导、链式法则、梯度累积和计算图；用手算的小例子核对 autograd。
- 概率与损失：结合 Softmax、交叉熵和语言模型补条件概率、期望、指数与对数，不另设整门概率论课。
- AI 辅导：可以要求拆公式、画形状、检查自己的解释、分析报错；不要让 AI 直接给完整实验答案。能自己解释并修改一个小例子，比只看懂解释更重要。

## 实践的统一约定

实践是按原课教材习题、Notebook 和竞赛案例整合的**站内阶段练习**，不是把 D2L 冒称为有统一官方 Lab 1–12 的课程。每项的来源与性质分别列明，难度和工时描述是编者建议，不是官方评分。

基础实验以小数据、小模型验证机制；完整数据训练、GPU/多 GPU 对照和历史竞赛作为明确标注的扩展。缩小运行规模不改变课程覆盖范围，也不能拿小实验的数值声称复现原课完整结果。

**实验页“常用命令”框中的 `git checkout`、`make qemu`、`make grade` 是网站现有的 xv6 通用模板，不适用于本课，请勿照抄。** 本课没有这些官方实验分支或评分命令。应使用经对应实验指导核对的 Python / Notebook 操作。

### 十二个阶段练习

以下“对应讲次”是主题关联，不要求全部看完才开始练习；遇到后续主题可以回来继续。完整课程学习与完成全部扩展实验分别记录。

| 阶段练习 | 对应站内讲次 | 基础目标与扩展边界 |
|---|---|---|
| [1. 张量、数据与自动求导](#/c/d2l-pytorch-2021/lab/tensor-autograd?v=zh) | LEC 1–7 | 形状、广播、预处理与手算梯度；CPU 小例即可。 |
| [2. 从零训练循环与线性模型](#/c/d2l-pytorch-2021/lab/linear-training?v=zh) | LEC 8–9 | 独立写训练/验证循环，对照从零实现与 PyTorch API。 |
| [3. MLP、泛化与房价基线](#/c/d2l-pytorch-2021/lab/mlp-generalization?v=zh) | LEC 10–15、18 | 观察正则化和泛化，建立房价基线；迁移历史竞赛为选做。 |
| [4. 模块工程、卷积与现代CNN](#/c/d2l-pytorch-2021/lab/cnn-architectures?v=zh) | LEC 16–17、19–29 | 各网络做形状与机制检查，LeNet/小 ResNet 做训练；不要求全量重训每个网络。 |
| [5. 计算性能与多设备训练](#/c/d2l-pytorch-2021/lab/training-performance?v=zh) | LEC 31–35 | 测量前向/反向/数据加载；多 GPU 实测需对应硬件，不能以推演代替。 |
| [6. 视觉迁移与分类竞赛实践](#/c/d2l-pytorch-2021/lab/cv-transfer?v=zh) | LEC 30、36–39、42 | 增广与微调的小基线；完整 CIFAR-10、狗品种和树叶竞赛训练按资源选做。 |
| [7. 检测、分割与风格迁移](#/c/d2l-pytorch-2021/lab/cv-dense-prediction?v=zh) | LEC 40–41、43–50、71 | 检测、分割、风格迁移的小实验；牛仔行头历史竞赛适配为扩展。 |
| [8. RNN、GRU与LSTM语言模型](#/c/d2l-pytorch-2021/lab/recurrent-language-model?v=zh) | LEC 51–59 | 文本批处理、状态传递、梯度裁剪；比较小规模 RNN/GRU/LSTM。 |
| [9. Seq2Seq、翻译与注意力](#/c/d2l-pytorch-2021/lab/seq2seq-attention?v=zh) | LEC 60–66 | 翻译数据与 mask，seq2seq 基线、搜索和注意力对齐。 |
| [10. 从注意力到Transformer](#/c/d2l-pytorch-2021/lab/transformer?v=zh) | LEC 67–68 | 逐步解释 Q/K/V、位置编码和 mask，训练教学规模编码器—解码器模型。 |
| [11. BERT预训练与自然语言推断](#/c/d2l-pytorch-2021/lab/bert-pretrain-finetune?v=zh) | LEC 69–70 | 理解 MLM/NSP 与微调；小模型验证，不以全量预训练为要求。 |
| [12. 优化回顾与全课程工程总结](#/c/d2l-pytorch-2021/lab/optimization-capstone?v=zh) | LEC 72–73 | 复用已有模型比较优化器、恢复训练并整理 CS336 准备清单。 |

### 环境与版本

- 全程选择教材的 **PyTorch** 实现，不混用 MXNet、TensorFlow 或 PaddlePaddle 代码。
- 2021 视频、在线教材和今天的 PyTorch 环境不必然完全兼容。本批采用独立的 CPU 基础环境；不要把它当作全课旧 Notebook 的兼容承诺，也不要把旧视频命令直接当作当前安装建议。
- CPU 可以承担基础算例；CUDA、Apple MPS 与多 GPU 是不同执行环境，不能互换名称或默认兼容。性能对照需记录设备、数据规模、精度、热身与同步方式。
- 保存参数与恢复训练不是同一件事；实践应明确是否同时保存优化器状态。训练、验证、测试数据分开，不能靠测试集反复调参。

#### 首批基础环境

首批张量实践与 LEC 4–7 的短代码已在 **macOS arm64、Python 3.11.8、PyTorch 2.5.1、NumPy 1.26.4、pandas 2.2.3、CPU** 上执行。首批没有安装 `d2l`、`torchvision` 或 Jupyter；没有运行 CUDA/MPS、2021 Notebook 全集或完整学生作业。源码里的 `d2l` 安装约束包含另一组旧版 NumPy/pandas，不要直接混装进这个环境。

在自己的练习目录中，先确认 `python3 --version` 为 Python 3.11；下面使用已经安装的 `uv` 包管理器（本次为 0.11.28），路径写法适用于 macOS/Linux，实际验证平台仅为 macOS arm64：

```bash
python3 -m venv .venv-d2l
uv pip install --python .venv-d2l/bin/python torch==2.5.1 numpy==1.26.4 pandas==2.2.3
```

把自己编写的练习保存为 `practice.py`，用同一个解释器运行，不必激活环境：

```bash
.venv-d2l/bin/python practice.py
```

已执行的验收包括：8个笔记代码块；导论损失、矩阵乘法和梯度的数值核对；独立小输入上的广播/归约、冻结训练预处理状态、梯度累积与清零、detach、加权反传、概率前缀计数与空条件处理。**这些机制烟测不是你的四项作业已经完成，也不是全课实验通过。** 具体环境、输出与完整依赖快照保存在仓库 `sources/p1-shared/` 的 `practice-smoke.json`、`notes-smoke.json`、`runtime-freeze.txt`。

#### 第二批：线性训练所需环境与实际边界

LEC 8–14 的 **12 个独立 Python 片段**已经在同版本 CPU 环境执行，数值与解析预期一致。`linear-training` 新增 **torchvision 0.20.1**，配套 PyTorch 2.5.1；不安装 `d2l`、Jupyter 或绘图库。在上面的隔离环境中安装本批依赖：

```bash
uv pip install --python .venv-d2l/bin/python torch==2.5.1 torchvision==0.20.1 numpy==1.26.4 pandas==2.2.3
```

真实 Fashion-MNIST 的四份官方 gzip 已从 **官方 GitHub HTTPS raw** 取得、核对官方 MD5 和 IDX 头后放入运行时缓存，使用 `FashionMNIST(download=False)` 读取。没有测试旧 HTTP S3 镜像；不声称默认 `download=True` 成功或镜像已失效。数据不随站点或本次提交发布，下载路径及校验表见[实验说明页底](#/c/d2l-pytorch-2021/lab/linear-training?v=zh)。

实际执行范围：

- 独立机制：半MSE梯度与从零/Linear一步SGD对照、稳定交叉熵及梯度、尾批指标加权、模式与求导分离、L2普通SGD、Dropout端点/期望、标量梯度连乘，以及任务4的两样本学习率失败夹具。
- 真实数据小基线：从官方训练集固定拆出55000/5000候选池，再用257训练/73验证；划分、初始化、shuffle种子分别2021/2022/2023，CPU、`num_workers=0`、B64（训练尾批1，验证尾批9）、`Flatten + Linear(784,10)`、SGD `lr=0.01`、5轮25次更新。训练损失从约2.303871降至1.974106，末轮验证损失约2.118220、accuracy为13/73。曲线并不单调；这些数只证明所述小基线，不是教材全量效果或你的作业成绩。
- 评估期间参数与既有梯度不变；同一73样本改为B32后损失在浮点容差内一致、accuracy不变。官方测试集只下载并核对文件头，没有参与训练、调参或评估。
- 初稿的 `lr=0.1` 在同一小数据配置下未通过“末轮训练损失低于初始值”断言，已保留失败记录并修正基础起点；不是删掉失败、弱化断言或改数据来宣称通过。

**没有执行**两条完整40轮回归作业、验证标签干预的完整重训、教材Notebook、55000/5000全量训练、10000测试集评估或GPU/CUDA/MPS。运行日志不能替学习者完成四个任务。完整环境、首轮失败及修正结果分别见 `sources/p2-shared/runtime-freeze.txt`、`first-runtime-attempt.json`、`practice-smoke.json`、`notes-smoke.json`、`dataset-acquisition.json`；临时验收脚本不作为答案发布。

#### 第三批：模块、卷积与 MLP／房价流程

继续使用上面的隔离 CPU 环境，没有重装或混入旧版 `d2l`。本次实际探测 **CUDA 不可用、MPS 已构建且可用**；全部验收仍显式选择 CPU，不能把后端可用性探测写成 MPS 运算、训练或加速比验证。

主 agent 独立运行了以下场景；这些是编者的验证证据，不是学生作业答案：

- 同权重 MLP 的张量实现与 `nn.Module` 实现：前向、梯度和一步 SGD 一致；参数共享的梯度累积、buffer 注册、模型与优化器状态恢复均有数值核对。仅恢复权重后重新创建动量优化器，下一步与连续训练不同。
- 卷积：用非对称核区分互相关与翻转卷积；核对非对称填充、步幅、多输入通道求和，以及 1×1 卷积与逐位置矩阵乘法的一致性。
- 合成泛化对照：固定 32 训练／128 验证、20 特征；线性模型与 64 隐藏单元 MLP，以及单独改变权重衰减或 Dropout 的配对实验。每组 SGD、B16、300 轮／600 次更新；大模型训练误差很低并不代表验证误差低，正则化也不保证在任意种子或数据上胜出。
- Ames 房价：官方 HTTPS 两份 CSV 下载后核对教材 SHA1；从 1460 条有标签记录固定抽取 257 条，K=3 的验证折大小为 86／86／85，折内拟合预处理，每折重建线性 log-price 模型与 Adam。每折 B64、30 轮／90 次更新，pooled OOF logRMSE 为 **0.176461**，折内常量均值基线为 **0.407783**；这不是 Kaggle 分数。
- 再用全部 1460 条有标签记录拟合一次同配置小模型，30 轮／690 次更新；只在内存导出 1459 行 `Id,SalePrice`，验证正有限价格与原始测试 Id 顺序。没有测试标签评估、排行榜提交、多模型调优或完整竞赛复现。

折内预处理包含训练均值插补、总体标准差（`ddof=0`）、常量／全缺失列回退，以及独立的缺失与未知类别；OOF 每条样本恰好出现一次。**教材 Ames 与 2021 加州房价不是同一数据集**；加州历史竞赛的访问与迁移边界见[第三项实验](#/c/d2l-pytorch-2021/lab/mlp-generalization?v=zh)，不能把 Ames 或 sklearn 的 California Housing 当作完成了它。

本批没有运行 CUDA/MPS、旧 Notebook 或全部学生任务。数据只保存在运行时缓存，不随站点发布；模型、预测 CSV、临时验收脚本也不作为解答发布。精确配置、每折数值与数据哈希见 `sources/p3-shared/environment.json`、`mechanism-smoke.json`、`practice-smoke.json`、`dataset-acquisition.json`。


#### 第四批：完整CNN前向与小模型训练恢复

继续复用同一CPU环境，实际执行8段笔记代码，以及固定教材的LeNet、AlexNet、VGG-11、NiN、GoogLeNet、ResNet-18完整前向。AlexNet/VGG/NiN使用单通道224输入，GoogLeNet/ResNet-18使用96输入；保留教材的全部卷积、分支、池化、通道与分类头，逐个构造释放。这里的“完整”指教材Fashion-MNIST变体，**不是原论文ImageNet训练复现**。除LeNet之外，上述完整宽度模型只做前向；训练另用明确缩小的ResNet。

独立机制核验覆盖：逐通道仿射层的解析梯度、共享与buffer恢复；卷积形状/参数；负值最大池化与平均池化padding、ceil末端窗口；1×1通道映射与GAP；Inception分支拼接；BN有偏前向方差与无偏running方差、四种模式组合及每通道单值退化；残差投影、奇数尺寸、ReLU恒等边界与梯度。

两条真实Fashion-MNIST小训练复用已校验的官方训练数据，未使用官方测试集。seed2021打乱60000条后，前5000作验证候选、其余55000作训练候选，分别取73和257；初始化seed2022、shuffle seed2023，Xavier权重/零偏置，CPU单线程，B64、尾批1，Adam学习率0.003，10轮各50次更新。表中训练CE均在冻结模型后以eval重评，不是混合训练时刻的批均值。

| 模型 | 参数量 | 初始训练CE | 末轮训练CE | 末轮验证CE | 验证正确数 |
|---|---:|---:|---:|---:|---:|
| 教材LeNet（Sigmoid/AvgPool） | 61,706 | 2.634785 | 2.300294 | 2.379941 | 8/73 |
| 编者小ResNet | 176,634 | 2.299596 | 0.313692 | 1.212001 | 46/73 |

LeNet在此极小配置下仍接近随机分类水平，不能把“损失下降、更新链路可用”说成已经学好了分类。小ResNet使用3×3/s1宽8的stem，四stage宽8/16/32/64，各两个完整基本残差块，保留BN、投影和GAP；不是把原ResNet直接塞入28输入后删层。

两模型评估均未改变参数、BN buffers或已有梯度，B32/B64指标一致。可信内存检查点恢复模型、Adam、BN buffers、CPU RNG及独立shuffle状态后，预测、下一随机数/批次、下一步loss/梯度/模型与优化器状态均匹配；更新后模型状态最大差值为0。故意只恢复模型并新建Adam，下一步参数分别出现约0.004869和0.005329的最大差值，说明预测相同不足以证明训练恢复。

本批不运行GPU/MPS、旧Notebook、全量Fashion或大模型全训；没有提交学生完整解答、数据集、检查点或临时脚本。配置、逐轮输出、形状与源码块定位见 `sources/p4-shared/practice-smoke.json`、`architecture-smoke.json`、`notes-smoke.json`、`mechanism-smoke.json`、`lab-mechanism-smoke.json`；主agent最终验收范围以 `sources/p4-manifest.json` 为准。

#### 第五批：CPU性能测量与梯度聚合推演

复用 Python 3.11.8 / PyTorch 2.5.1 环境，在 **Apple M2 Max、macOS 26.3.1、CPU单线程、float32** 上测量编者小MLP（784→64→10）。模型为训练模式，交叉熵均值、SGD 0.01；数据为8192条内存合成样本，`num_workers=0`，不包含磁盘读取、图像解码或设备传输。各batch在独立进程执行10步热身和30步测量，分别计时取批、前向与损失、反向、更新与清梯度；CPU同步执行，无CUDA/MPS操作。

| batch | 整步中位数 ms | 四分位区间 ms | 样本/秒 | 输入张量 KiB | 进程峰值RSS bytes |
|---:|---:|---:|---:|---:|---:|
| 16 | 0.1881 | 0.1823–0.1935 | 80,894 | 49 | 279281664 |
| 64 | 0.2911 | 0.2847–0.3018 | 193,505 | 196 | 279379968 |
| 128 | 0.4449 | 0.4361–0.4812 | 258,558 | 392 | 280461312 |

吞吐按测量窗口内实际样本数除以总时长计算，不是中位数的倒数。这里的“整步”是串行分段计时的同一窗口；短微基准受调度与计时开销影响，**不是硬件排名、收敛速度或GPU加速比**。输入字节数仅含float32特征；RSS是macOS `ru_maxrss` 的进程终身高水位，包含框架和全部数据，不是活跃张量内存，也不能从其差值推断batch独占内存。各阶段原始30个样本、中位数和四分位数见 `sources/p5-shared/performance-smoke.json`。

另在CPU float64上，用同初值线性层与逐样本可加损失核对等长3+3及不等长4+3分片：按样本数加权局部均值梯度，与整批梯度最大误差不超过2.23×10⁻¹⁶，一步SGD参数最大误差不超过2.78×10⁻¹⁷。错误地等权平均4+3两份局部均值，梯度最大误差约0.104568。这个反例证明归一化合同的重要性，**不证明真实all-reduce、参数服务器、网络通信或多GPU性能**。

本批CUDA设备数为0；MPS仅探测可用，未执行。补充核对了六讲纸面算例、三逻辑worker的同轮收齐/一次更新/重复与旧轮拒绝、遗漏不更新和到达顺序一致性，以及独立的两步MLP参数变化；均非网络执行。没有重训P4模型、运行分布式进程组或完成学生全部任务；[第五项实验](#/c/d2l-pytorch-2021/lab/training-performance?v=zh)仍要求学习者自行实现并记录。数值范围见 `sources/p5-shared/environment.json`、`mechanism-smoke.json`、`supplement-smoke.json`、`special-hardware-smoke.json`。

## 学完后怎样衔接 CS336

用三个问题自查：能否不依赖整段答案写出小模型训练循环；能否逐步解释 Attention 的形状与 mask；能否解释模型的参数、梯度、优化器状态和激活为何占用内存。

之后进入 CS336，继续完整理解课程，再按工程兴趣选择实验。重点带着架构取舍、资源核算、GPU/内存瓶颈、推理与并行、数据和评估的问题学习，不把刷论文、全量预训练或复现研究结果增加成前置要求。

## 引用与来源

- 李沐：[2021 中文 PyTorch 课程官方课表](https://courses.d2l.ai/zh-v2/)。课表顺序与原始链接是本课程编排依据。
- 阿斯顿·张、扎卡里 C. 立顿、李沐、亚历山大 J. 斯莫拉：[《动手学深度学习》中文第二版](https://zh.d2l.ai/)、[课表使用的历史入口](https://zh-v2.d2l.ai/)。本批正文依据[中文源码固定提交 e6b18ccea714](https://github.com/d2l-ai/d2l-zh/tree/e6b18ccea71451a55fcd861d7b96fddf2587b09a)，不是 2021 全书快照；在线网页与固定源码也不保证逐字一致。教材与录像分别登记，不把教材内容声称为实际课堂讲授。
- [中文教材与代码仓库](https://github.com/d2l-ai/d2l-zh)、[固定版本的依赖声明](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/setup.py)、[在线安装页](https://zh.d2l.ai/chapter_installation/index.html)。旧安装页列出 Python 3.9、PyTorch 1.12.0、torchvision 0.13.0、d2l 0.17.6；不等于本站基础练习的运行环境。
- [PyTorch 历史版本安装说明](https://pytorch.org/get-started/previous-versions/)列明torch 2.5.1 / torchvision 0.20.1配套；[vision 0.20 FashionMNIST API](https://docs.pytorch.org/vision/0.20/generated/torchvision.datasets.FashionMNIST.html)及[官方数据仓库](https://github.com/zalandoresearch/fashion-mnist)已核对。本批安装和CPU执行另有实际证据，不能由版本表推定其他平台或全课兼容。
- [Stanford CS336 官方课程](https://cs336.stanford.edu/)：后续学习目标，不是本课额外必读材料。

### 首批已核实的全部分 P

下表依据作者“跟李沐学AI”的公开视频元数据，补上课表未单列的实现和 QA。时长精确到接口所给秒，各 P 独立计时；这是文件清单，**不是已审阅的课堂时间轴**。18次公开字幕请求均成功但列表为空，尚未核实任何讲授、演示与问答，也未取得视频开放转载许可。因此已有笔记为教材导读，不能替代录像；不会用占位稿填充「中文译稿」。本批「课程资料」不单独成篇，必要阅读直接在笔记文末定位；页面的「待生成」不代表还需重译中文教材。

| 讲次 | 真实分 P 与时长 |
|---|---|
| LEC 1 | [P1 课程安排 · 08:08](https://www.bilibili.com/video/BV1oX4y137bC?p=1) |
| LEC 2 | [P1 深度学习介绍 · 13:34](https://www.bilibili.com/video/BV1J54y187f9?p=1)；[P2 QA · 09:23](https://www.bilibili.com/video/BV1J54y187f9?p=2) |
| LEC 3 | [P1 安装 · 16:06](https://www.bilibili.com/video/BV18p4y1h7Dr?p=1)；[P2 QA · 03:51](https://www.bilibili.com/video/BV18p4y1h7Dr?p=2) |
| LEC 4 | [P1 数据操作 · 04:41](https://www.bilibili.com/video/BV1CV411Y7i4?p=1)；[P2 数据操作实现 · 14:35](https://www.bilibili.com/video/BV1CV411Y7i4?p=2)；[P3 数据预处理实现 · 07:26](https://www.bilibili.com/video/BV1CV411Y7i4?p=3)；[P4 QA · 07:36](https://www.bilibili.com/video/BV1CV411Y7i4?p=4) |
| LEC 5 | [P1 线性代数 · 09:03](https://www.bilibili.com/video/BV1eK4y1U7Qy?p=1)；[P2 实现 · 12:51](https://www.bilibili.com/video/BV1eK4y1U7Qy?p=2)；[P3 按特定轴求和 · 07:31](https://www.bilibili.com/video/BV1eK4y1U7Qy?p=3)；[P4 QA · 12:09](https://www.bilibili.com/video/BV1eK4y1U7Qy?p=4) |
| LEC 6 | [P1 矩阵计算 · 12:38](https://www.bilibili.com/video/BV1eZ4y1w7PY?p=1)；[P2 QA · 01:57](https://www.bilibili.com/video/BV1eZ4y1w7PY?p=2) |
| LEC 7 | [P1 自动求导 · 11:40](https://www.bilibili.com/video/BV1KA411N7Px?p=1)；[P2 实现 · 06:42](https://www.bilibili.com/video/BV1KA411N7Px?p=2)；[P3 QA · 06:05](https://www.bilibili.com/video/BV1KA411N7Px?p=3) |

### 第二批已核实的全部分 P

LEC 8–14 共 **7 个 BV、28P**。标准公开 player 请求均成功但字幕列表为空；未下载或观看音视频，下表仍只是文件目录，不能当成课堂主题时间轴。七讲继续制作教材导读与自拟小例，不补造演示、问答或时间码；独立中文阅读不重译成 materials。

| 讲次 | 真实分 P 与时长 |
|---|---|
| LEC 8 | [P1 线性回归 · 14:57](https://www.bilibili.com/video/BV1PX4y1g7KC?p=1)；[P2 基础优化算法 · 08:24](https://www.bilibili.com/video/BV1PX4y1g7KC?p=2)；[P3 线性回归的从零开始实现 · 15:20](https://www.bilibili.com/video/BV1PX4y1g7KC?p=3)；[P4 线性回归的简洁实现 · 06:42](https://www.bilibili.com/video/BV1PX4y1g7KC?p=4)；[P5 QA · 24:21](https://www.bilibili.com/video/BV1PX4y1g7KC?p=5) |
| LEC 9 | [P1 Softmax 回归 · 10:26](https://www.bilibili.com/video/BV1K64y1Q7wu?p=1)；[P2 损失函数 · 06:24](https://www.bilibili.com/video/BV1K64y1Q7wu?p=2)；[P3 图片分类数据集 · 09:25](https://www.bilibili.com/video/BV1K64y1Q7wu?p=3)；[P4 Softmax 回归从零开始实现 · 18:43](https://www.bilibili.com/video/BV1K64y1Q7wu?p=4)；[P5 Softmax 回归简洁实现 · 04:09](https://www.bilibili.com/video/BV1K64y1Q7wu?p=5)；[P6 QA · 30:59](https://www.bilibili.com/video/BV1K64y1Q7wu?p=6) |
| LEC 10 | [P1 感知机 · 13:52](https://www.bilibili.com/video/BV1hh411U7gn?p=1)；[P2 多层感知机 · 22:39](https://www.bilibili.com/video/BV1hh411U7gn?p=2)；[P3 代码实现 · 08:26](https://www.bilibili.com/video/BV1hh411U7gn?p=3)；[P4 QA · 26:48](https://www.bilibili.com/video/BV1hh411U7gn?p=4) |
| LEC 11 | [P1 模型选择 · 18:36](https://www.bilibili.com/video/BV1kX4y1g7jp?p=1)；[P2 过拟合和欠拟合 · 16:46](https://www.bilibili.com/video/BV1kX4y1g7jp?p=2)；[P3 代码 · 06:47](https://www.bilibili.com/video/BV1kX4y1g7jp?p=3)；[P4 QA · 45:01](https://www.bilibili.com/video/BV1kX4y1g7jp?p=4) |
| LEC 12 | [P1 权重衰退 · 13:02](https://www.bilibili.com/video/BV1UK4y1o7dy?p=1)；[P2 代码实现 · 12:34](https://www.bilibili.com/video/BV1UK4y1o7dy?p=2)；[P3 QA · 11:35](https://www.bilibili.com/video/BV1UK4y1o7dy?p=3) |
| LEC 13 | [P1 丢弃法 · 11:59](https://www.bilibili.com/video/BV1Y5411c7aY?p=1)；[P2 代码实现 · 12:16](https://www.bilibili.com/video/BV1Y5411c7aY?p=2)；[P3 QA · 24:52](https://www.bilibili.com/video/BV1Y5411c7aY?p=3) |
| LEC 14 | [P1 数值稳定性 · 15:21](https://www.bilibili.com/video/BV1u64y1i75a?p=1)；[P2 模型初始化和激活函数 · 24:03](https://www.bilibili.com/video/BV1u64y1i75a?p=2)；[P3 QA · 22:29](https://www.bilibili.com/video/BV1u64y1i75a?p=3) |

LEC 10 的两种实现仍保留原课表的同一个 `?p=3`。真实列表显示 P3 为“代码实现”、P4 为“QA”，没有单列另一实现；仅凭标题无法核实 P3 内是否讲了两种实现，更无法划定各自时间段，**不能猜改到 P4**。本批 `copyright=1`；LEC 8–10 的 `no_reprint=1`，LEC 11–14 为 0。两种标志值都不是开放转录授权。

### 第三批已核实的全部分 P

LEC 15–21 共 **7 个 BV、23P、17122 秒**。逐 P 公开字幕请求全部成功且列表为空；没有下载或观看音视频，不据分 P 标题推测讲授顺序、演示或问答。元数据的时长不是课堂主题时间轴，仍不生成无依据的 draft。

| 讲次 | 真实分 P 与时长 |
|---|---|
| LEC 15 | [P1 实战 Kaggle 比赛：预测房价 · 14:30](https://www.bilibili.com/video/BV1NK4y1P7Tu?p=1)；[P2 课程竞赛：加州2020年房价预测 · 08:39](https://www.bilibili.com/video/BV1NK4y1P7Tu?p=2)；[P3 QA · 03:21](https://www.bilibili.com/video/BV1NK4y1P7Tu?p=3) |
| LEC 16 | [P1 模型构造 · 13:27](https://www.bilibili.com/video/BV1AK4y1P7vs?p=1)；[P2 参数管理 · 17:20](https://www.bilibili.com/video/BV1AK4y1P7vs?p=2)；[P3 自定义层 · 05:28](https://www.bilibili.com/video/BV1AK4y1P7vs?p=3)；[P4 读写文件 · 06:03](https://www.bilibili.com/video/BV1AK4y1P7vs?p=4)；[P5 QA · 10:51](https://www.bilibili.com/video/BV1AK4y1P7vs?p=5) |
| LEC 17 | [P1 使用 GPU · 13:34](https://www.bilibili.com/video/BV1z5411c7C1?p=1)；[P2 购买 GPU · 08:54](https://www.bilibili.com/video/BV1z5411c7C1?p=2)；[P3 QA · 08:03](https://www.bilibili.com/video/BV1z5411c7C1?p=3) |
| LEC 18 | [P1 竞赛总结 · 16:39](https://www.bilibili.com/video/BV15Q4y1o7vc?p=1)；[P2 QA · 26:03](https://www.bilibili.com/video/BV15Q4y1o7vc?p=2) |
| LEC 19 | [P1 从全连接到卷积 · 15:00](https://www.bilibili.com/video/BV1L64y1m7Nh?p=1)；[P2 卷积层 · 11:02](https://www.bilibili.com/video/BV1L64y1m7Nh?p=2)；[P3 代码 · 10:08](https://www.bilibili.com/video/BV1L64y1m7Nh?p=3)；[P4 QA · 07:44](https://www.bilibili.com/video/BV1L64y1m7Nh?p=4) |
| LEC 20 | [P1 填充和步幅 · 14:08](https://www.bilibili.com/video/BV1Th411U7UN?p=1)；[P2 代码实现 · 05:05](https://www.bilibili.com/video/BV1Th411U7UN?p=2)；[P3 QA · 23:57](https://www.bilibili.com/video/BV1Th411U7UN?p=3) |
| LEC 21 | [P1 多输入输出通道 · 19:34](https://www.bilibili.com/video/BV1MB4y1F7of?p=1)；[P2 代码实现 · 06:36](https://www.bilibili.com/video/BV1MB4y1F7of?p=2)；[P3 QA · 19:16](https://www.bilibili.com/video/BV1MB4y1F7of?p=3) |

LEC 17 的“购买 GPU”和七讲全部 QA 入口均保留，不因课表未单列就删除；没有观看时不提供所谓课堂购买建议或竞赛获奖方法。本批均为 `copyright=1`；LEC 15 的 `no_reprint=0`，LEC 16–21 为 1，都不能据此推定开放转录许可。

### 第四批已核实的全部分 P

LEC 22–29 共 **8 个 BV、24P、20337 秒**，均由官方课表指向作者“跟李沐学AI”的2021年上传。每讲3P，包括主题、实现与QA；页头时长按全部真实分P求和，不把P1当整讲。24次公开字幕请求均成功但列表为空；没有下载、观看或转录音视频，不能据文件标题推断片内时间轴。八讲仍为教材导读，不生成无依据的课堂整理。

| 讲次 | 真实分 P 与时长 |
|---|---|
| LEC 22 | [P1 池化层 · 10:21](https://www.bilibili.com/video/BV1EV411j7nX?p=1)；[P2 实现 · 06:58](https://www.bilibili.com/video/BV1EV411j7nX?p=2)；[P3 QA · 09:48](https://www.bilibili.com/video/BV1EV411j7nX?p=3) |
| LEC 23 | [P1 LeNet · 08:31](https://www.bilibili.com/video/BV1t44y1r7ct?p=1)；[P2 代码 · 21:47](https://www.bilibili.com/video/BV1t44y1r7ct?p=2)；[P3 QA · 30:08](https://www.bilibili.com/video/BV1t44y1r7ct?p=3) |
| LEC 24 | [P1 AlexNet · 35:16](https://www.bilibili.com/video/BV1h54y1L7oe?p=1)；[P2 代码 · 10:39](https://www.bilibili.com/video/BV1h54y1L7oe?p=2)；[P3 QA · 16:06](https://www.bilibili.com/video/BV1h54y1L7oe?p=3) |
| LEC 25 | [P1 VGG · 09:04](https://www.bilibili.com/video/BV1Ao4y117Pd?p=1)；[P2 代码 · 07:23](https://www.bilibili.com/video/BV1Ao4y117Pd?p=2)；[P3 QA · 04:16](https://www.bilibili.com/video/BV1Ao4y117Pd?p=3) |
| LEC 26 | [P1 NIN · 10:55](https://www.bilibili.com/video/BV1Uv411G71b?p=1)；[P2 代码 · 10:01](https://www.bilibili.com/video/BV1Uv411G71b?p=2)；[P3 QA · 16:42](https://www.bilibili.com/video/BV1Uv411G71b?p=3) |
| LEC 27 | [P1 GoogLeNet · 26:59](https://www.bilibili.com/video/BV1b5411g7Xo?p=1)；[P2 代码 · 07:10](https://www.bilibili.com/video/BV1b5411g7Xo?p=2)；[P3 QA · 16:33](https://www.bilibili.com/video/BV1b5411g7Xo?p=3) |
| LEC 28 | [P1 批量归一化 · 17:59](https://www.bilibili.com/video/BV1X44y1r77r?p=1)；[P2 代码 · 17:12](https://www.bilibili.com/video/BV1X44y1r77r?p=2)；[P3 QA · 11:00](https://www.bilibili.com/video/BV1X44y1r77r?p=3) |
| LEC 29 | [P1 ResNet · 14:10](https://www.bilibili.com/video/BV1bV41177ap?p=1)；[P2 代码 · 09:26](https://www.bilibili.com/video/BV1bV41177ap?p=2)；[P3 QA · 10:33](https://www.bilibili.com/video/BV1bV41177ap?p=3) |

八讲的 `copyright=1`、`no_reprint=1` 均不是开放转录许可。LEC27上传标题另含“Inception V3”，教材7.4展示的GoogLeNet结构不能据此冒称完整覆盖该课堂拓展；未核实部分保留缺口，不猜写。

### 第五批已核实的全部分 P

LEC 30–35共 **6个BV、12P、15677秒**，均为官方课表指向作者“跟李沐学AI”的2021年上传。LEC30单P，其余按全部真实P求和，包含QA；LEC34同时保留从零开始与简洁实现。12次公开player请求均成功但字幕列表为空，未下载或观看音视频，不造课堂稿、演示、问答或主题时间轴。

| 讲次 | 真实分 P 与时长 |
|---|---|
| LEC 30 | [P1 leaf · 06:37](https://www.bilibili.com/video/BV1z64y1o7iz?p=1) |
| LEC 31 | [P1 CPU 和 GPU · 39:22](https://www.bilibili.com/video/BV1TU4y1j7Wd?p=1)；[P2 QA · 52:47](https://www.bilibili.com/video/BV1TU4y1j7Wd?p=2) |
| LEC 32 | [P1 更多的芯片 · 29:19](https://www.bilibili.com/video/BV1VV41147PC?p=1)；[P2 QA · 37:18](https://www.bilibili.com/video/BV1VV41147PC?p=2) |
| LEC 33 | [P1 单机多卡并行 · 06:59](https://www.bilibili.com/video/BV1vU4y1V7rd?p=1)；[P2 QA · 03:56](https://www.bilibili.com/video/BV1vU4y1V7rd?p=2) |
| LEC 34 | [P1 从零开始 · 21:41](https://www.bilibili.com/video/BV1MQ4y1R7Qg?p=1)；[P2 简洁实现 · 11:53](https://www.bilibili.com/video/BV1MQ4y1R7Qg?p=2)；[P3 QA · 20:40](https://www.bilibili.com/video/BV1MQ4y1R7Qg?p=3) |
| LEC 35 | [P1 分布式训练 · 21:45](https://www.bilibili.com/video/BV1jU4y1G7iu?p=1)；[P2 QA · 09:00](https://www.bilibili.com/video/BV1jU4y1G7iu?p=2) |

六讲均为 `copyright=1`、`no_reprint=1`，不是开放转录许可。LEC30竞赛说明与LEC32硬件补充不冒充教材指定章节或课堂内容；树叶比赛与CIFAR-10、狗品种教材案例分别处理。空字幕接口不证明不存在烧录字幕。

### 全课视频入口

以下链接逐项保留课表中的 BV 与分 P 参数。未写 `p` 的原始链接标作「入口」，不推定它覆盖整组内容。LEC 1–35 的真实全部分 P 已列于上方五表；其余讲次尚待逐 P 核对。讲次页头提供原站链接与已记录时长；点击后在新标签页观看，本站保留笔记。嵌入播放器与“课程视频”标签已按用户要求移除。曾误接入的非本人YouTube上传也已撤下，不以转载替代官方课表来源。

| 站内讲次 | 原课表视频入口 |
|---|---|
| LEC 1 | [课程安排 · 入口](https://www.bilibili.com/video/BV1oX4y137bC) |
| LEC 2 | [深度学习介绍 · 入口](https://www.bilibili.com/video/BV1J54y187f9) |
| LEC 3 | [安装 · 入口](https://www.bilibili.com/video/BV18p4y1h7Dr) |
| LEC 4 | [数据操作 · 入口](https://www.bilibili.com/video/BV1CV411Y7i4)；[数据预处理 · P3](https://www.bilibili.com/video/BV1CV411Y7i4?p=3) |
| LEC 5 | [线性代数 · 入口](https://www.bilibili.com/video/BV1eK4y1U7Qy)；[[补充] 按特定轴求和 · P3](https://www.bilibili.com/video/BV1eK4y1U7Qy?p=3) |
| LEC 6 | [矩阵计算 · 入口](https://www.bilibili.com/video/BV1eZ4y1w7PY) |
| LEC 7 | [自动求导 · 入口](https://www.bilibili.com/video/BV1KA411N7Px) |
| LEC 8 | [线性回归 · 入口](https://www.bilibili.com/video/BV1PX4y1g7KC)；[基础优化方法 · P2](https://www.bilibili.com/video/BV1PX4y1g7KC?p=2)；[线性回归的从零开始实现 · P3](https://www.bilibili.com/video/BV1PX4y1g7KC?p=3)；[线性回归的简洁实现 · P4](https://www.bilibili.com/video/BV1PX4y1g7KC?p=4) |
| LEC 9 | [Softmax 回归 · 入口](https://www.bilibili.com/video/BV1K64y1Q7wu)；[损失函数 · P2](https://www.bilibili.com/video/BV1K64y1Q7wu?p=2)；[图像分类数据集 · P3](https://www.bilibili.com/video/BV1K64y1Q7wu?p=3)；[Softmax 回归的从零开始实现 · P4](https://www.bilibili.com/video/BV1K64y1Q7wu?p=4)；[Softmax 回归的简洁实现 · P5](https://www.bilibili.com/video/BV1K64y1Q7wu?p=5) |
| LEC 10 | [感知机 · 入口](https://www.bilibili.com/video/BV1hh411U7gn)；[多层感知机 · P2](https://www.bilibili.com/video/BV1hh411U7gn?p=2)；[多层感知机的从零开始实现 · P3](https://www.bilibili.com/video/BV1hh411U7gn?p=3)；[多层感知机的简洁实现 · P3](https://www.bilibili.com/video/BV1hh411U7gn?p=3) |
| LEC 11 | [模型选择 · 入口](https://www.bilibili.com/video/BV1kX4y1g7jp)；[欠拟合和过拟合 · P2](https://www.bilibili.com/video/BV1kX4y1g7jp?p=2) |
| LEC 12 | [权重衰减 · 入口](https://www.bilibili.com/video/BV1UK4y1o7dy) |
| LEC 13 | [Dropout · 入口](https://www.bilibili.com/video/BV1Y5411c7aY) |
| LEC 14 | [数值稳定性 · 入口](https://www.bilibili.com/video/BV1u64y1i75a)；[模型初始化和激活函数 · P2](https://www.bilibili.com/video/BV1u64y1i75a?p=2) |
| LEC 15 | [实战 Kaggle 比赛：预测房价 · 入口](https://www.bilibili.com/video/BV1NK4y1P7Tu)；[竞赛 预测房价 · P2](https://www.bilibili.com/video/BV1NK4y1P7Tu?p=2) |
| LEC 16 | [模型构造 · 入口](https://www.bilibili.com/video/BV1AK4y1P7vs)；[参数管理 · P2](https://www.bilibili.com/video/BV1AK4y1P7vs?p=2)；[自定义层 · P3](https://www.bilibili.com/video/BV1AK4y1P7vs?p=3)；[读写文件 · P4](https://www.bilibili.com/video/BV1AK4y1P7vs?p=4) |
| LEC 17 | [GPU · 入口](https://www.bilibili.com/video/BV1z5411c7C1) |
| LEC 18 | [预测房价竞赛总结 · 入口](https://www.bilibili.com/video/BV15Q4y1o7vc) |
| LEC 19 | [从全连接层到卷积 · 入口](https://www.bilibili.com/video/BV1L64y1m7Nh)；[图像卷积 · P2](https://www.bilibili.com/video/BV1L64y1m7Nh?p=2) |
| LEC 20 | [填充和步幅 · 入口](https://www.bilibili.com/video/BV1Th411U7UN) |
| LEC 21 | [多输入多输出通道 · 入口](https://www.bilibili.com/video/BV1MB4y1F7of) |
| LEC 22 | [池化层 · 入口](https://www.bilibili.com/video/BV1EV411j7nX) |
| LEC 23 | [卷积神经网络（LeNet） · 入口](https://www.bilibili.com/video/BV1t44y1r7ct/) |
| LEC 24 | [深度卷积神经网络（AlexNet） · 入口](https://www.bilibili.com/video/BV1h54y1L7oe/) |
| LEC 25 | [使用块的网络（VGG） · 入口](https://www.bilibili.com/video/BV1Ao4y117Pd/) |
| LEC 26 | [网络中的网络（NiN） · 入口](https://www.bilibili.com/video/BV1Uv411G71b/) |
| LEC 27 | [含并行连结的网络（GoogLeNet） · 入口](https://www.bilibili.com/video/BV1b5411g7Xo/) |
| LEC 28 | [批量归一化 · 入口](https://www.bilibili.com/video/BV1X44y1r77r/) |
| LEC 29 | [残差网络（ResNet） · 入口](https://www.bilibili.com/video/BV1bV41177ap/) |
| LEC 30 | [竞赛 图片分类 · 入口](https://www.bilibili.com/video/BV1z64y1o7iz/) |
| LEC 31 | [硬件：CPU和GPU · 入口](https://www.bilibili.com/video/BV1TU4y1j7Wd/) |
| LEC 32 | [更多的专有硬件 · 入口](https://www.bilibili.com/video/BV1VV41147PC/) |
| LEC 33 | [多GPU训练 · 入口](https://www.bilibili.com/video/BV1vU4y1V7rd/) |
| LEC 34 | [多GPU训练的实现 · 入口](https://www.bilibili.com/video/BV1MQ4y1R7Qg) |
| LEC 35 | [分布式训练 · 入口](https://www.bilibili.com/video/BV1jU4y1G7iu) |
| LEC 36 | [图像增广 · 入口](https://www.bilibili.com/video/BV17y4y1g76q) |
| LEC 37 | [微调 · 入口](https://www.bilibili.com/video/BV1Sb4y1d7CR) |
| LEC 38 | [实战 Kaggle 比赛：图像分类（CIFAR-10） · 入口](https://www.bilibili.com/video/BV1Gy4y1M7Cu) |
| LEC 39 | [实战 Kaggle 比赛：狗的品种识别（ImageNet Dogs） · 入口](https://www.bilibili.com/video/BV1j5411T7wx) |
| LEC 40 | [物体检测 · 入口](https://www.bilibili.com/video/BV1Lh411Y7LX)；[边缘框实现 · P2](https://www.bilibili.com/video/BV1Lh411Y7LX?p=2)；[物体检测数据集 · P3](https://www.bilibili.com/video/BV1Lh411Y7LX?p=3) |
| LEC 41 | [锚框 · 入口](https://www.bilibili.com/video/BV1aB4y1K7za) |
| LEC 42 | [竞赛 树叶分类竞赛总结 · 入口](https://www.bilibili.com/video/BV1by4y1K7SE) |
| LEC 43 | [区域卷积神经网络（R-CNNs） · 入口](https://www.bilibili.com/video/BV1Db4y1C71g)；[单发多框检测（SSD） · 入口](https://www.bilibili.com/video/BV1Db4y1C71g)；[你只看一次（YOLO） · 入口](https://www.bilibili.com/video/BV1Db4y1C71g) |
| LEC 44 | [多尺度物体检测实现 · P1](https://www.bilibili.com/video/BV1ZX4y1c7Sw?p=1)；[SSD 实现 · P2](https://www.bilibili.com/video/BV1ZX4y1c7Sw?p=2) |
| LEC 45 | [语义分割 · 入口](https://www.bilibili.com/video/BV1BK4y1M7Rd)；[语义分割数据集 · P2](https://www.bilibili.com/video/BV1BK4y1M7Rd?p=2) |
| LEC 46 | [转置卷积 · 入口](https://www.bilibili.com/video/BV17o4y1X7Jn/) |
| LEC 47 | [转置卷积是一种卷积 · 入口](https://www.bilibili.com/video/BV1CM4y1K7r7/) |
| LEC 48 | [全连接卷积神经网络（FCN） · 入口](https://www.bilibili.com/video/BV1af4y1L7Zu/) |
| LEC 49 | [样式迁移 · 入口](https://www.bilibili.com/video/BV1Eh41167GN/) |
| LEC 50 | [竞赛 目标检测 · 入口](https://www.bilibili.com/video/BV1F64y1x7xP/) |
| LEC 51 | [序列模型 · 入口](https://www.bilibili.com/video/BV1L44y1m768/) |
| LEC 52 | [文本预处理 · 入口](https://www.bilibili.com/video/BV1Fo4y1Q79L/) |
| LEC 53 | [语言模型和数据集 · 入口](https://www.bilibili.com/video/BV1ZX4y1F7K3/) |
| LEC 54 | [循环神经网络 · 入口](https://www.bilibili.com/video/BV1D64y1z7CA/) |
| LEC 55 | [循环神经网络的从零开始实现 · 入口](https://www.bilibili.com/video/BV1kq4y1H7sw/)；[循环神经网络的简洁实现 · P2](https://www.bilibili.com/video/BV1kq4y1H7sw?p=2) |
| LEC 56 | [门控循环单元（GRU） · 入口](https://www.bilibili.com/video/BV1mf4y157N2/) |
| LEC 57 | [长短期记忆网络（LSTM） · 入口](https://www.bilibili.com/video/BV1JU4y1H7PC/) |
| LEC 58 | [深层循环神经网络 · 入口](https://www.bilibili.com/video/BV1JM4y1T7N4/) |
| LEC 59 | [双向循环神经网络 · 入口](https://www.bilibili.com/video/BV12X4y1c71W/) |
| LEC 60 | [机器翻译与数据集 · 入口](https://www.bilibili.com/video/BV1H64y1s7TH/) |
| LEC 61 | [编码器-解码器结构 · 入口](https://www.bilibili.com/video/BV1c54y1E7YP/) |
| LEC 62 | [序列到序列学习（seq2seq） · 入口](https://www.bilibili.com/video/BV16g411L7FG/) |
| LEC 63 | [束搜索 · 入口](https://www.bilibili.com/video/BV1B44y1C7m1/) |
| LEC 64 | [注意力机制 · 入口](https://www.bilibili.com/video/BV1264y1i7R1/) |
| LEC 65 | [注意力分数 · 入口](https://www.bilibili.com/video/BV1Tb4y167rb/) |
| LEC 66 | [使用注意力机制的seq2seq · 入口](https://www.bilibili.com/video/BV1v44y1C7Tg/) |
| LEC 67 | [自注意力和位置编码 · 入口](https://www.bilibili.com/video/BV19o4y1m7mo/) |
| LEC 68 | [Transformer · 入口](https://www.bilibili.com/video/BV1Kq4y1H7FL/) |
| LEC 69 | [BERT · 入口](https://www.bilibili.com/video/BV1yU4y1E7Ns/)；[BERT预训练数据集 · P2](https://www.bilibili.com/video/BV1yU4y1E7Ns?p=2)；[预训练BERT · P3](https://www.bilibili.com/video/BV1yU4y1E7Ns?p=3) |
| LEC 70 | [微调BERT · 入口](https://www.bilibili.com/video/BV15L4y1v7ts)；[自然语言推理和数据集 · P2](https://www.bilibili.com/video/BV15L4y1v7ts?p=2)；[自然语言推理：微调BERT · P3](https://www.bilibili.com/video/BV15L4y1v7ts?p=3) |
| LEC 71 | [竞赛 目标检测总结 · 入口](https://www.bilibili.com/video/BV13b4y1m7y8) |
| LEC 72 | [优化算法 · 入口](https://www.bilibili.com/video/BV1bP4y1p7Gq) |
| LEC 73 | [课程总结和进阶学习 · 入口](https://www.bilibili.com/video/BV1AL4y1Y7gu) |

### 原课表需核对的链接

- MLP 的从零与简洁实现都链接到同一 `?p=3`；本批已核实真实 P3“代码实现”、P4“QA”，但内容归属仍待真实字幕/视频证据，两个原链接不改。R-CNN、SSD、YOLO 三个主题使用同一无 `p` 入口，尚待后续核实；不能漏掉任何主题。
- 课表的 `part-4_1.pdf`、`part-4_2.pdf`、`part-4_3.pdf` 在不同主题间重复使用；转置卷积两讲也共用教材/Notebook 入口。抓取时需对照真实内容，不能只按文件名认定对应关系。
- 官方课程简介计划四次竞赛，最终课表及课程公告可证实三次课程竞赛：房价预测、树叶分类、牛仔行头目标检测。教材中的 CIFAR-10、狗品种识别属于案例，不据此虚构第四次课程竞赛。

### 教材目录与对应范围

以下为当前中文第二版的目录入口，共 16 章；它不是 2021 年全书固定版本，也不表示每个小节都有独立视频。课程顺序以本页课表为准：计算性能与视觉早于序列模型，优化专题在课程末尾。数学补习和多头注意力等必要概念可随课补读；不把全书额外小节增加成新的完课门槛。

| 教材章 | 定位用途 |
|---|---|
| [1. 引言](https://zh.d2l.ai/chapter_introduction/index.html) | 课程导论 |
| [2. 预备知识](https://zh.d2l.ai/chapter_preliminaries/index.html) | 数学与张量基础；概率可作补习 |
| [3. 线性神经网络](https://zh.d2l.ai/chapter_linear-networks/index.html) | 回归、分类与训练循环 |
| [4. 多层感知机](https://zh.d2l.ai/chapter_multilayer-perceptrons/index.html) | MLP、泛化与房价案例 |
| [5. 深度学习计算](https://zh.d2l.ai/chapter_deep-learning-computation/index.html) | 模块、参数、设备与文件 |
| [6. 卷积神经网络](https://zh.d2l.ai/chapter_convolutional-neural-networks/index.html) | 卷积基础与 LeNet |
| [7. 现代卷积神经网络](https://zh.d2l.ai/chapter_convolutional-modern/index.html) | 现代 CNN；DenseNet 无独立课表入口 |
| [8. 循环神经网络](https://zh.d2l.ai/chapter_recurrent-neural-networks/index.html) | 序列、文本与 RNN；BPTT 按需补习 |
| [9. 现代循环神经网络](https://zh.d2l.ai/chapter_recurrent-modern/index.html) | GRU/LSTM、翻译与 seq2seq |
| [10. 注意力机制](https://zh.d2l.ai/chapter_attention-mechanisms/index.html) | 注意力、位置编码与 Transformer；多头注意力随模型补习 |
| [11. 优化算法](https://zh.d2l.ai/chapter_optimization/index.html) | 课程末尾优化专题；不推定逐节讲授 |
| [12. 计算性能](https://zh.d2l.ai/chapter_computational-performance/index.html) | 课中硬件与并行专题；编译/异步计算按需补读 |
| [13. 计算机视觉](https://zh.d2l.ai/chapter_computer-vision/index.html) | 视觉任务与教材比赛案例 |
| [14. 自然语言处理：预训练](https://zh.d2l.ai/chapter_natural-language-processing-pretraining/index.html) | 本课主要对应 BERT；word2vec/GloVe 等不另增视频讲次 |
| [15. 自然语言处理：应用](https://zh.d2l.ai/chapter_natural-language-processing-applications/index.html) | 本课主要对应 BERT 微调与自然语言推理 |
| [16. 附录：深度学习工具](https://zh.d2l.ai/chapter_appendix-tools-for-deep-learning/index.html) | 环境与工具按需查阅 |

### 竞赛、代码与许可边界

- [课程公告](https://courses.d2l.ai/zh-v2/announcements.html)用于核对实际三次课程竞赛；它们是历史学习材料，当前数据可用性、参赛资格和榜单状态需另查。教材的 Ames 房价与课程的加州房价不是同一数据集。
- [固定中文源码仓库 LICENSE](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/LICENSE)为 Apache-2.0；辅助包 `setup.py` 的包许可字段另列 MIT-0，不混为单一授权结论。以上均不外推至 B 站视频、字幕、第三方图片、竞赛数据或纸质出版物。本站讲解、例子与练习为编者整理或改编，不复制中文教材全文。
- 教材目录、公告、固定源码许可和安装说明已留存来源快照；章节实际阅读范围见逐讲来源。没有因此声称已读全书、取得录像再发布许可或验证全部 Notebook。

