---
title: A1 从零训练语言模型：概念、依赖与调试指导
kind: 编者完整概念指导；不提供作业解答、数值答案或可提交实现
source: CS336 Assignment 1 (basics), Spring 2026, Version 26.0.3
source_commit: a158843b20107949f1a8d7df1b05cd33b9166712
source_read_scope: 全部 47 页提取文本及 README、LICENSE、pyproject、CHANGELOG 全文；未逐页视觉审校
status: P3 概念指导；覆盖分词至实验的完整学习路径，文档完整不表示实验完成
license: 第一方讲义与仓库文档按 MIT 使用；完整版权、许可和修改声明见页底
execution: 未实现或执行任何官方作业、安装依赖、下载数据、训练或启动收费计算
---

# 把 A1 看作一组能够逐层验证的合同

本页回答“为什么这样分层、错了先查哪里、什么证据才够”；[完整实验说明](#/c/stanford-cs336-2026/lab/a1-basics?v=zh)负责每题要求、所有子问、接口、分值、资源路线与提交，重复细节不另抄一份。本页是在原有任务地图上直接扩展的唯一指导，不是第二套作业或答案。

整条链由三种独立资产组成：

1. **数据资产**：原始文本、词表、有序 merges、特殊 token、编码后的训练/验证数组。
2. **可学习状态**：模型参数、梯度、优化器 moments 与更新步数。
3. **实验证据**：固定配置、预算、日志、checkpoint、生成结果与对照结论。

一个阶段产出“能读的文件”，不表示下一阶段读到了同一语义；一个 loss 下降，也不证明掩码、数据切分和预算正确。最有效的顺序是先检查合同，再检查数值，再检查统计表现，最后才优化速度。

## G0．规则和依赖：先决定自己要证明什么

**对应说明：§0、§7；涉及全部任务。**

官方只允许 AI 做概念/API 辅助，禁止任何作业实现或自动补全，包括排行榜。本页因此只提供推理问题、观测维度和调试分叉，不给 adapters、训练器、优化器或 tokenizer 代码。发生 API 疑义时，可以查函数签名、参数注册、设备语义；“帮我把整题写好”已越过边界。

固定版是 Spring 2026 v26.0.3，不是 README 的旧标题，也不是包版本号。先在自己的记录中分别登记源码提交、讲义版次、依赖环境、设备和路线。CPU/MPS 减量不等于原规模完成；标准、官方低资源、更小机制练习的区别见实验说明 §6.1。BPE 的主存/时间包络也不构成最低硬件保证。

### 按缺口补先修，而非先把全部资料读完

| 你卡在什么问题 | 应读的知识正文 | 回到 A1 时应能说明 |
| --- | --- | --- |
| 字节和 token 的区别 | [L01 分词](#/c/stanford-cs336-2026/lec/lec01?v=notes) | 什么是训练资产，什么是编码操作 |
| 参数为什么没被更新 | [Python 实验工程](#/c/stanford-cs336-2026/lec/bridge04?v=notes)、[自动微分](#/c/stanford-cs336-2026/lec/bridge03?v=notes) | 模块注册、计算图、梯度与状态分别在哪 |
| 形状相同却结果不对 | [张量形状](#/c/stanford-cs336-2026/lec/bridge01?v=notes)、[内存语义](#/c/stanford-cs336-2026/lec/bridge05?v=notes) | 每条轴代表什么，转置是否只改视图 |
| attention、norm、门控怎么组合 | [L03 架构](#/c/stanford-cs336-2026/lec/lec03?v=notes) | 各模块处理哪一种依赖、改变哪个合同 |
| RoPE 的符号和配对 | [L03 精读材料](#/c/stanford-cs336-2026/lec/lec03?v=materials) | 输入位置、配对约定、相对旋转的意义 |
| loss、梯度或 optimizer 不稳定 | [稳定计算](#/c/stanford-cs336-2026/lec/bridge07?v=notes)、[梯度诊断](#/c/stanford-cs336-2026/lec/ext01?v=notes)、[优化器动态](#/c/stanford-cs336-2026/lec/ext02?v=notes) | 不稳定首次出现在哪一层、哪一步 |
| 怎么组织训练与验证 | [训练闭环](#/c/stanford-cs336-2026/lec/bridge06?v=notes)、[资源估算](#/c/stanford-cs336-2026/lec/bridge08?v=notes) | 数据、状态、指标、预算是否闭合 |
| 怎么解释 loss 或长度实验 | [概率与信息论](#/c/stanford-cs336-2026/lec/bridge02?v=notes)、[位置与长度实验](#/c/stanford-cs336-2026/lec/ext03?v=notes) | 比较的条件和计量单位是什么 |

这些是编者依赖关系，不是官方禁止提前阅读。L04 的替代 attention / MoE 可以扩展架构视野，但不是把 A1 基线替换成更复杂模型的前提。

**阶段门槛**：你能区分“源码接口测试”“受控实验”“达到目标”“课程提交资格”。尚未确认环境或权限时，继续纸笔合同和小样本推理即可，不要先下载整库数据或启动 GPU。

## G1．Unicode 与 BPE：从第一处分歧定位错误

**对应说明：01–07；`unicode1`、`unicode2`、`train_bpe`、两项 BPE 训练、`tokenizer`、`tokenizer_experiments`。**

### G1.1 三种表示不能互当长度单位

Python 字符串按 Unicode 码点组织，UTF-8 是字节编码，BPE token 是词表中的 bytes 序列。词表项不必单独构成一个完整 Unicode 字符。问“最长 token”前，应说明按 byte 长度还是其他量度；做 bytes/token 时必须量编码后的 bytes，不能把字符串 `len` 不加说明当成字节数。

`unicode1` 要练的是“表示与可见输出”分离，`unicode2` 要练的是“解码需要怎样的边界”。先自行观察原题要求，再写一句能解释现象的话；不要让助手代给反例或把一次可运行当成普遍正确。

**分叉**：若 ASCII 看起来正确而混合语言出错，先检查 bytes/str 边界和解码时机；若 ID 往返一致但得到的字节不同，检查序列化；若字节一致而屏幕显示不同，才检查表示层。这个顺序避免把 Unicode 问题误判成 merge 计数问题。

### G1.2 训练器正确性的最小证据是有序决策

BPE 不是“找到一些常见单词”，而是在边界约束下产生一个确定的合并序列。最终词表相似不保证路径一致；下游编码取决于 merges 的优先级，因此应定位**第一次不同的 merge**，而不是盯着最后几千个词表项。

| 症状 | 优先检查 | 不能用什么替代 |
| --- | --- | --- |
| 第一轮就不同 | pre-token 切分、频次是否按出现次数加权、special 是否进入统计 | 只比较词表大小 |
| 只有同频时不同 | 比较的是原始 bytes 二元组，选择字典序较大者 | 拼接后的字符串排序、显示字符排序或随机选一个 |
| 前几轮相同后偏离 | 合并后相邻 pair 的计数是否一致；重复/重叠出现的处理是否对应同一规则 | 让缓存“差不多”就继续 |
| 含 special 才失败 | 是否先划硬边界再处理各片段；special 自身是否参与 merge | 删除 special 后直接拼接左右文本 |
| 换进程数改变结果 | 切块是否跨文档/UTF-8 或 pre-token 边界，归并计数是否完整 | 声称并行天然不确定 |
| 时间或主存急增 | profiling 分开预分词、计数、合并、序列化；测峰值而非只量文件大小 | 直接改语言或盲目加进程 |

特殊 token 和普通 pre-token 都是硬边界，但特殊 token 在训练与编码中的处理不同：训练排除其统计，编码保留其 ID。它必须在词表容量账里。不要为了通过一个样例而在输入字符串上硬编码特殊判断；检查规则在不同排列、重复和相邻边界是否仍成立。

建议先在自己造的小语料上手工审查每轮“候选计数—选择—合并后表示”，再与自己的优化版本比较同一输出。这里是验证思路，不是给官方题答案。正确后才评估缓存或并行；序列化应能恢复 bytes，而非把不可打印字节丢成替代字符。

### G1.3 编码不是第二次训练

编码使用冻结资产。遇到同一个文本，不应因同时编码的其他文档改变结果。若资产载入后 ID 映射变了，先查文件格式和顺序，不要修改训练算法补偿。

流式 API 的价值是内存与输入大小解耦，但任意切成若干 Python 字符串后分别编码未必等于整体编码。先定义输入流连接后的文本语义，再检查切分是否处于可安全提交的边界；跨块 UTF-8、特殊 token、空白/缩写及长 pre-token 都应有明确解释。仅证明 generator 是惰性的，不足以证明边界正确。

解码时先在 bytes 层拼合，再解释 Unicode。非法 bytes 的替换是 decode 的指定合同，不应被挪到 BPE 训练中“清洗掉”合法字节；这样会改变学习语料。

### G1.4 把分词实验当作测量，不当作展示

压缩率报告要写明语料、抽样方式、tokenizer 资产和单位；跨语料实验只改 tokenizer 或数据中一个明确因素。吞吐测量区分初始化、读盘和实际编码，说明测量是否包含这些开销；外推 825 GB 是线性吞吐估算，不是已处理这么多数据。

写出编码数组后，先在小范围检查 ID 合法性、读写 dtype 一致性和解码语义，再让模型消费。正式 tokenizer 用训练集训练；在验证小集上做开发只用于调试，不能混进正式资产而声称验证独立。

**阶段门槛**：官方分词接口测试、原题短答、真实 BPE 测量、两套词表/merges、四份编码数据分别有证据。小样本正确与全语料完成分开记，资源不够就诚实标路线，不填虚构结果。

## G2．Linear 与 Embedding：形状只是合同的一部分

**对应说明：08–09；`linear`、`embedding`。**

先为每个张量写“轴语义、存储 dtype、device、是否可学习、是否在 state_dict 中”。Linear 的权重逻辑形状是输出特征 × 输入特征，前导维只是同一个变换被反复应用的位置；Embedding 的 ID 轴不是可学习的连续输入，查表后才出现特征维。

如果单个向量正确而 batch 出错，检查自己是否把某个固定维号当作特征维；如果输出形状正确但数值转置，检查权重存储与乘法约定；如果 forward 正确而参数列表为空，检查注册而不是 optimizer。把一个 Tensor 放在普通 Python 容器里，不自动等于模块会管理它。

初始化的方差和标准差不能互换，截断范围也必须与给定标准差对应。检查“是不是要求的分布和尺度”，而不是拿一小份随机样本均值恰好不为零当失败。测试载入指定权重时，不应在 forward 再次初始化覆盖它。

**阶段门槛**：任意前导 batch 维被保留，embedding 末维语义正确，给定权重可准确加载，参数随模块设备/dtype 管理。通过后再组装 block，不必为了“先看 loss”跳过这些底层证据。

## G3．完整前向：分开查语义、数值与布局

**对应说明：10–18；RMSNorm、SwiGLU、RoPE、softmax、attention、block、LM 与前向资源题。**

### G3.1 RMSNorm 与 SwiGLU 的诊断单位是一个位置

RMSNorm 沿每个位置的特征维归一化，不把 batch 或 sequence 合并。它调节尺度，不是减均值的 LayerNorm。固定版要求输入**在平方之前**升到 float32，最终结果转回输入 dtype；“归约时才指定 float32”不能挽救已经在低精度平方中溢出的值。参数存储 dtype 与中间计算 dtype 是两张不同的表。

若 float32 正常而低精度异常，查首次产生非有限值的位置；若所有值有限却输出尺度随 batch 大小变化，先查约简轴。不要用到处增加 epsilon 掩盖轴或 cast 错误。零输入和不同幅度输入是机制观察方向，但不能只验证一个固定输入。

SwiGLU 需要辨清两条向内投影、一条向外投影，以及哪一条先经过 SiLU。门控是逐元素作用在匹配的隐藏轴，不是矩阵相乘，不跨 token。若输出同形状但数值不对，检查参数名对应与分支角色；若临时删门控后更快，这还不是公平消融，参数匹配留到 G8。

### G3.2 RoPE 首先是“位置输入合同”

本作业采用相邻维配对的旋转约定；不能直接移植另一个库的 half-split 配对而认为名字相同就兼容。位置张量可以不是 `0…T−1`，head 是 batch-like 维，Q/K 需要一致的位置解释，V 不旋转。cos/sin 是固定几何量，不应成为可训练参数。

若从零开始正常、偏移位置失败，检查是否实际读取 token_positions；若单头正常、多头异常，检查广播是否把 head 当序列；若维数改变就失败，检查频率指数和配对索引，而不是增大容差。几何推导与不变量见 [L03 材料](#/c/stanford-cs336-2026/lec/lec03?v=materials)，不要在这里重建一份 RoFormer 译文。

### G3.3 softmax、掩码与因果性要分别证明

稳定 softmax 的不变量是：沿约定轴归一化，沿该轴整体平移 logits 不改变概率；不是“任意加常数到某个位置都不变”。attention 中归一化发生在 key 位置，query 位置产生不同分布。检查三个合同：Q/K 特征内积、key 轴归一化、V 的末维输出。

**本作业 mask True=允许；False=禁止。**其他 API 同名 mask 可能反过来，不能仅照抄参数名。因果 mask 允许看自身及以前，不能把对角线一起屏蔽；禁止位置在 softmax 前排除，而不是事后乘零留下不归一的行。

| 观察 | 先问什么 | 下一层证据 |
| --- | --- | --- |
| 概率行和错误 | softmax 轴、mask 应用时点对吗 | 每个 query 的允许项合计与禁止项概率 |
| 三维正常、四维失败 | 是否写死了 batch/序列维 | 前导维独立性 |
| 改未来 token 会改过去 logits | 因果方向、对角线、广播是否正确 | 固定前缀，改变后缀的因果一致性 |
| 同一 head 内数值异常 | 缩放用的是 d_k 还是 d_model | 在进入多头组合前的组件比较 |
| 单组件通过、block 失败 | 残差连接的是谁，norm 在哪里 | 各子层输入输出逐站定位 |

不要用“训练 loss 很低”证明因果性：偷看目标恰好会让 loss 很好看。也不要对全禁止的一行默默编造均匀分布；这类输入没有正常的注意力概率合同，标准含对角线的 causal mask 应避免产生它。

### G3.4 block 与 LM 的边界是 logits，不是概率

pre-norm 的 residual stream 与子层输入不是同一个概念：norm 用于子层计算，残差路径不能被不小心替换成已经归一化的值。完整 LM 还有最终 norm；模块都通过但 LM 失败时，查组装顺序、层数、参数装载和最终输出，不要先改基础算子。

模型输出 logits，使稳定 loss 和生成分布可以各自处理数值；提前 softmax 会改变交叉熵输入合同。训练与推理用同一组参数，但评估不应构建无用计算图，更不应偷偷更新状态。

### G3.5 资源题从实际张量表出发

`transformer_accounting` 的五个子问对应“参数—装载字节—前向乘法清单—组件比例—尺寸变化”。列出每个矩阵乘法的输入/输出轴和层数、head 数的重复因子，再统一 FLOPs 口径；不要拿网络搜索到的 GPT-2 XL 参数数目替代本作业架构。

参数装载内存不包含梯度、moments、激活；上下文增加会影响一些激活/乘法，却不等于同比增加所有参数。报告 GB/GiB 与精度口径，比例以同一分母计算。讲义“约 17M”的近似文字不能替代你自己的参数登记。具体推导方法读 [L02](#/c/stanford-cs336-2026/lec/lec02?v=notes) 与[资源估算桥接](#/c/stanford-cs336-2026/lec/bridge08?v=notes)，本页不填任何计分数值。

**阶段门槛**：组件测试与完整 LM 测试分别满足，轴/位置/因果证据齐全，资源表与实际架构一致；尚未证明 optimizer 或训练质量。

## G4．loss 与更新：不把“叫 AdamW”当成同一个算法

**对应说明：19–24；`cross_entropy`、`learning_rate_tuning`、`adamw`、`adamw_accounting`、调度、裁剪。**

### G4.1 先查 loss 的输入和分母

next-token loss 接受 logits 和离散 target，目标轴必须对应当前输入位置的下一个 token。多维 batch 的平均应按有效 token 数定义；不能先对大小不同的部分各自平均，再未经加权地平均一次。

如果 loss 一开始非有限，按 logits → 稳定变换 → target 索引定位；如果 loss 合理但梯度为空，回到[自动微分](#/c/stanford-cs336-2026/lec/bridge03?v=notes)查图是否被切断、参数是否参与、是否在正确的上下文求导。不要用裁剪修复错误的 loss；裁剪不把 NaN 变成可信梯度。

perplexity 与 loss 的关系见[概率桥接](#/c/stanford-cs336-2026/lec/bridge02?v=notes)。比较前先核对自然对数、token 单位与验证平均方式，不把任务阈值换成另一个量。

### G4.2 小 SGD 观察与完整模型搜索分开

`learning_rate_tuning` 是给定小例的十步观察，要求真实记录三个指定学习率的行为，不是推测哪一个应发散。`learning_rate` 才是在 TinyStories 上搜索。用前者理解步长和曲率，不把它的结论当成后者的可直接复用超参数。

若参数完全不动，检查 step 是否真的作用在 model 的 Parameter、当前学习率是否为零、grad 是否存在；若第一步动、之后重复同一更新，检查清梯度和状态计数。先能解释一个更新事件，再谈长期曲线。

### G4.3 2026 AdamW 的精确约定

固定版在已有梯度下，先以**当前基础学习率**施加解耦衰减，再更新 moments 并作梯度更新；计数从 1 起。衰减不是 L2 loss 项，不进入一、二阶矩；不能在梯度更新之后再把新参数整体缩小，因为这会顺带缩放刚施加的梯度项。

原讲义用偏差修正步长，分母是**未校正二阶矩的平方根加 epsilon**。若把它改写成校正 moments 的形式，同一个数值 epsilon 不会自动保持严格相等。尤其不能因为 PyTorch 文档也叫 AdamW，就默认以其同值 epsilon 公式替代 A1 合同。精确式见实验说明 21；两种约定的代数区别见 [ext02 优化器动态](#/c/stanford-cs336-2026/lec/ext02?v=notes)。

诊断时分开记录当前基础学习率、t、moments 与参数变化；只有最终 loss 会把状态错误隐藏很久。第一步对、后续错通常应查状态保存和计数；仅 weight decay 非零才偏离时，应查衰减对象与次序；tiny gradient 下才偏离时，应查 epsilon 位置与缩放。以上都是定位方向，不是可提交实现。

### G4.4 调度、裁剪和资源账互不替代

调度的 t、warmup 末点、cosine 末点和恢复后的 iteration 要采用同一个计数语义；若学习率曲线有非预期跳跃，先查边界和日志采样，不立即改成更平滑的另一种调度。低资源缩短步数时，要重新明确衰减终点。

裁剪使用全模型已有梯度的整体范数，对各参数按同一个比例缩放；逐张量各裁一次会改变方向和整体上限。记录裁剪前后的范数能区分“偶发尖峰被限制”与“每一步都被截断”；后者可能提示步长、loss 缩放或架构问题，不是“越裁越安全”。如果使用额外混合精度机制，还须区分真实梯度与缩放梯度，但不应把这扩张为原题未要求的训练系统。

`adamw_accounting` 的 (a–d) 逐项需要参数/激活/梯度/moments、batch 依赖、更新 FLOPs、硬件时间估计。按题设列激活，不把实际 allocator 峰值和简化代数题混为一谈；MFU 和 FLOPs/s 单位对应后才能换算小时。题设 H100 不更改实训 B200 版本。

**阶段门槛**：loss、optimizer、调度、整体裁剪分别有官方接口证据；能解释一次更新中的状态和次序，再接完整训练，不提前声称最优学习率或算力实测。

## G5．数据与恢复：能继续跑不等于恢复了训练

**对应说明：25–27；`data_loading`、`checkpointing`、`training_together`。**

### G5.1 先核对一个 batch 的含义

用可逐项辨认的小 ID 序列理解输入窗口与右移目标。窗口最后一个 target 不能越过数组尾部；采样范围的端点必须按“额外需要一个 token”推导。训练数组与验证数组是不同数据资产，不能因为变量名相似就共用一份。

若 ID 突然很大，先查 mmap dtype、字节布局、`.npy` 头和读取方式；若 ID 合法但文本无意义，查是否载入了另一套词表；若 CPU 正常而设备训练失败，查模型、输入、target 与 optimizer state 的设备，而不是重新训练 tokenizer。

文件在磁盘上不等于读取内存就是常数：不必要的完整转换/复制会破坏 mmap 的价值。只把需要的 batch 变成计算输入，并理解“文件映射”“主存 batch”“设备 tensor”是三层，不要让训练脚本每步重新编码原始文本。

### G5.2 checkpoint 的最低合同和更强复现主张

原题最低要求是**模型状态、优化器状态、iteration**，并支持路径和二进制 file-like；load 恢复前两项并返回第三项。模型权重相同但 moments 清零，是新优化过程，不是原训练状态恢复；iteration 丢失会让调度错位。

| 你要声称什么 | 至少要看什么 | 还不能推断什么 |
| --- | --- | --- |
| 保存/加载往返正确 | 给定 model/optimizer/iteration 的状态恢复 | 完整数据流水线可重复 |
| 可以从中断点继续训练 | 恢复后的状态、配置、下一步调度语义正确 | 每一步与不中断时逐位一致 |
| 逐步可复现的续训 | 还需定义随机源、采样位置、设备算法等并保留相应状态 | 跨硬件、跨版本自动逐位一致 |

这是从弱到强的三类合同，不把第三类额外字段擅自冒充原题必交清单。还要明确保存的是“已完成的步”还是“下一步编号”，保持和 loop 一致。只打开自己可信的 checkpoint；任意来源的序列化文件不应作为安全输入处理。

### G5.3 集成失败按阶段分叉

- **forward 就失败**：先查 batch、ID 范围、位置长度和 device；不是 learning rate 问题。
- **forward 正常而 backward 失败**：查计算图、原地覆盖和非有限中间值；不要捕获异常后继续下一步。
- **backward 正常但 step 后坏掉**：查梯度尺度、学习率、moments、衰减与状态；保存首次异常前的观测，不等跑完再猜。
- **训练正常而验证异常**：查验证数据与 tokenizer、评估模式/梯度上下文、平均权重，确保没有参数更新。
- **只在恢复后异常**：查 optimizer state、iteration、配置和设备迁移；不要只比较权重文件大小。
- **loss 正常但很慢**：把 batch 加载、前向/反向/更新、验证、checkpoint 各自计时；先找测量主因，再讨论优化。

训练 loop 的知识正文见[训练闭环](#/c/stanford-cs336-2026/lec/bridge06?v=notes)。这里不提供循环模板，读者须自己实现并保留最小可解释证据。

**阶段门槛**：用户配置、数据、状态、日志四条路径都打通；单 batch 调试与独立验证分开。没有一个名为“训练成功”的单元测试可以替代这四项。

## G6．生成：先证明采样合同，再评价文笔

**对应说明：28、32；`decoding`、`generate`。**

LM 在每个输入位置预测下一个 token，生成只取最后一个位置的分布。teacher forcing 中“每个位置都有预测”不等于一次能独立采出整个未来。生成 API 的 prompt、最大新增 token 数、EOS、temperature、top-p 各自是一个合同。

若重复、乱码或过早停止，先排除 tokenizer/checkpoint 不配套、取错位置、EOS ID 不一致、截断上下文后位置不一致，再讨论模型是否学得不够。解码 bytes 合法并不意味着语句流畅；好看的个例也不意味着验证 loss 合格。

temperature 缩放 logits，top-p 截断概率集合；保留集合应含跨过阈值的那个 token，并重新归一化。若分布只剩一个候选，检查是否是合法参数结果，还是 off-by-one 错误把候选都排掉；不能靠遇空集合就随便返回某 ID 掩盖问题。

比较生成质量时固定 checkpoint 与 prompt，再改变一个采样参数；报告真实样本及设置，不从很多样本里只挑最好的一段来代表平均质量。原题要求的 256 tokens 或首个 EOS、两个质量因素等交付见说明 32，不用本站或官方示范故事充当输出。

**阶段门槛**：四项解码功能可解释，停止和长度有证据；模型质量要由真实 checkpoint 的验证与生成共同说明。

## G7．TinyStories 基线：先固定预算，再搜索

**对应说明：29–32；日志、学习率、batch 与生成实验。**

日志应在第一个长 run 之前建立。每个 run 记录配置/数据资产身份、设备、随机性、开始/结束时间、token 数、验证协议、loss 曲线、失败原因与 checkpoint 对应关系。服务平台可选；本地日志只要完整就能支持科学比较，不必为记录实验启动付费服务。

标准 TinyStories 目标是约 **327.68M tokens / loss≤1.45**，官方 CPU/MPS 约 **40M / loss≤2.00**，二者不是同一成绩。单 B200 20–30 分钟和 M4 Max 的 CPU 82 / MPS 36 分钟都是原文参考，不是本页观测；不能据此保证自己的机器时长。详细配置只以实验说明 §6.1 为准。

### G7.1 loss 不下降时不要先扩大搜索

先看一个固定 minibatch 是否能被学习：不能时优先查目标对齐、图/参数更新、loss/optimizer 合同；能时只说明模型能拟合这一份输入。若训练下降而验证不下降，检查数据/评估协议和泛化，不再用更久过拟合该 batch 代替独立验证。

若只有高学习率发散，记录发散边界并定位是否出现非有限值；若任意小学习率都异常，应先查实现。原题要求至少一次发散曲线，是观察稳定区域，不是要求故意运行到硬件故障。训练到首次明确失败后可以按自己的停止规则记录，不应把失败数据删除。

### G7.2 让搜索策略留下可解释轨迹

学习率可以先粗后细，但报告自己真实搜索范围、各 run 的最终结果/发散和选取依据；不把事后只挑一个最好值包装成预先确定的方法。比较学习率时保持预算和验证口径，若改变 warmup 或衰减终点，要记作额外变化。

batch 影响优化噪声、吞吐和每步 token 数。原题要求从 1 到可用 GPU 内存边界，含 64/128 等中间值；不够资源就标注路线限制，不能声称已探索不存在的设备边界。必要重调学习率是允许的，但应分别呈现“直接改变 batch”和“重调后”的结论。

基本预算关系是：

$$
\begin{aligned}
N_{\text{tokens}}
&=B\times T\times S,\\
B&=\text{batch size},\\
T&=\text{context length},\\
S&=\text{更新步数}.
\end{aligned}
$$

固定步数、固定 token、固定墙钟是三种不同对照。不要用同一个“训练时长”混指它们；曲线至少保留原题要求的 steps 与 wall-clock，再辅助 token 横轴解释。

**阶段门槛**：标准或低资源路线明确，曲线覆盖搜索与失败，验证指标达到所选目标才声称达标；生成分析不是 loss 的替代品。没有跑实验时只能登记计划/未执行，不能填入 staff 结果。

## G8．消融和 OWT：每个结论都需要一个对照身份

**对应说明：33–37；四项架构消融与 `main_experiment`。**

对照身份至少由“基线版本、改变因素、参数量、训练预算、优化设置、数据/词表、评估协议”组成。只写“其他都一样”往往漏掉 FFN 参数数、调度长度或 batch 改变。

| 实验 | 必须保持清楚的唯一变化 | 常见误判与排查 |
| --- | --- | --- |
| 去 RMSNorm | 全部移除，分别观察旧最优学习率和降低学习率后的行为 | 只移除 block 内而保留最终 norm；把重调预算隐藏 |
| pre → post norm | norm 相对于 residual 的位置改变；记录 block 外最终 norm 的处理 | 同时换初始化/学习率却只归因 norm；仅换模块名称不换连接 |
| RoPE → NoPE | 去显式位置编码，保留 causal mask | 去掉 mask 引入未来泄漏；把“无显式位置”误写成“没有任何顺序信息” |
| SwiGLU → SiLU | 非门控内宽按原题约束匹配参数规模 | 只删第三投影却不改内宽；算力/参数差异被当成门控效应 |
| TinyStories → OWT | 数据/配套 tokenizer 变化；按原题保持架构及总迭代次数 | 10k/32k 资产混用；改 batch 后仍宣称严格同 token/算力 |

四个消融独立从基线出发，不累计到一个越来越不同的模型。去掉 RMSNorm 后若旧学习率不稳定而重调可稳定，应把两个观察同时保留，不选一个来支持预设结论。post-norm 对最后 norm 的处理需记录；原题明示的两个 block 公式之外不要无声添加更多变化。

NoPE 实验只在本任务的训练分布和长度设置内比较，不自动证明长上下文泛化，更不能据一次短长度曲线说位置编码“没用”。更严格的长度/位置外推研究方法见[位置与长度专题](#/c/stanford-cs336-2026/lec/ext03?v=notes)，不把那些扩展实验强塞成 A1 必交项。

公平不总等于所有数值完全相同。SwiGLU/SiLU 要按题设近似匹配参数，学习率可以为变体重调，但必须标明调参预算。多个随机种子有助于分辨波动；若资源只够一次，应把结论限制为观察到的这一组 run，不编造统计置信度。

OWT 任务原文要求同架构、同迭代次数，并允许重调学习率/batch；这几句话并不自动保证实际 token 数和 FLOPs 一样。词表维随对应 tokenizer 合理变化，但 block 架构保持。解释 loss 时必须承认文本难度、tokenizer 和计量单位变化，不能仅凭更大的 per-token loss 宣称模型能力退化多少。

**资源分叉**：p.44 对 GPU 有限的校外在线读者建议继续 TinyStories 修改、可选排行榜提交。这是正式说明中的替代路线，不是本文擅自缩题；采用时明确未完成标准 OWT 实验。标准课程计分要求不能借此统一降为选做。

**阶段门槛**：每项题目曲线、原题分析、修改记录和预算可回溯；结论只覆盖实际测过的条件，不由文档完整推断已跑消融。

## G9．排行榜与最终交付：预算也是正确性

**对应说明：38 和 §0 提交规则。**

排行榜标准题为 **6 分**；题名的 **10 B200 小时**是探索标注，最终训练是**单 B200 最多 45 分钟 / 0.75 B200-hours**，且只能使用官方提供的 OWT 训练集。最终墙钟曲线、loss、方法与提交记录都要有，不能拿探索阶段最佳 checkpoint 的 loss 冒充预算内结果。目标超过 loss 5.0 的 naive baseline，不是把 5.0 当百分数或困惑度。

先在小规模探究一个有机制依据的改变，再判断是否值得花最终预算。weight tying 等建议只是候选方向，不是让 AI 写一份 speedrun；官方“改进自由”不撤销 AI 政策。时限测量应包含什么、提交仓库当前怎样要求，应由读者按官方说明核对，本站不杜撰尚未确认的排行榜执行协议。

若性能不佳，先分清实现错误、数据协议错误、优化不佳与速度不足；不要把降低验证频率、改验证数据或只计 GPU kernel 时间当成模型进步。任何速度结论都需说明计时范围；学习曲线最终按原题的墙钟证据交付。

### 最终自查只问证据，不问自信

1. 38 个 Problem 的全部子问、书面答复、代码/数据/曲线能否逐项定位？
2. 哪些官方测试自己真正运行过，使用哪个提交与依赖？哪些只是导航？
3. 标准、低资源、机制练习三种结果是否清楚分开？
4. checkpoint、词表、数据和日志身份能否对应，而不是只保留“final”文件名？
5. 搜索/发散/消融/生成有没有真实记录，没跑的是否标未执行？
6. `writeup.pdf` 与 `code.zip` 是否按官方流程准备，数据/checkpoint 是否误入代码包？
7. 课程/排行榜资格与算力访问是否确实拥有，而非由公开仓库推断？

本页没有可执行代码块，也没有通过记录。官方验收入口和逐题交付统一回到[完整实验说明](#/c/stanford-cs336-2026/lab/a1-basics?v=zh)，共同的安装、数据入口与权限背景见[课程资料](#/c/stanford-cs336-2026)。

## 固定来源、修改说明与许可

1. CS336 Staff，[A1 Spring 2026 / Version 26.0.3 PDF](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/cs336_assignment1_basics.pdf)。实际完整读 47 页提取文本；未逐页视觉校验公式/图片，不把参考文献条目阅读算作论文全文阅读。
2. 同固定提交的 [README](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/README.md)、[pyproject](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/pyproject.toml)、[CHANGELOG](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/CHANGELOG.md)、[LICENSE](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/LICENSE) 均全文阅读。未审查全部 tests/adapters 源码、未安装官方依赖或执行任何 A1 实验。
3. [Spring 2026 集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit) 只作实际读过范围的资格、安全、并发概括；其许可不继承仓库 MIT，本文未访问 workspace 或启动作业。
4. **修改声明**：编者把原有中文任务地图扩展为概念、依赖与诊断指导；完整任务细节移到同一实验的说明页，加入自主教学分析和本站回链。不是 Stanford 官方中文版本，不含答案或可提交实现，不复制第三方论文/插图/示例故事。MIT 只覆盖相应第一方软件及文档，不自动覆盖数据、依赖和外部服务。原始获取时间、完整哈希与实际阅读范围见 `sources/p3-a1/manifest-fragment.json`；38 题及全部子项映射见 `sources/p3-a1/task-coverage.json`。P2 历史索引保留不改。

以下保留原仓库完整版权与许可：

> Copyright 2025 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
