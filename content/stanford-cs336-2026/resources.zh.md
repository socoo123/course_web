---
source: Stanford CS336 Spring 2026 官网（课程介绍、先修要求、作业概述与课表）；本站 production-plan.json
license: 本页为编者自主学习导航，不是官方讲义译文；外链材料分别核实许可，不据公开访问推定全文翻译权。
status: P1 来源采集与核查已完成并保留缺口；18 条官方录像的身份、时长及英文非 ASR 字幕已核实，L18 未找到。讲义、五仓库和16篇论文已固定版本，实际阅读范围逐项记录，不代表全文精读。讲次与实验正文仍为0；没有运行课程实验或收费算力。
---

# 从零构建语言模型：公共资料与学习路线

## 从一条可解释的训练闭环开始

给定文本，怎样把它变成 token、变成批次、变成预测下一个 token 的概率，再变成可重复的训练与评测？先把这条闭环写清楚，再讨论模型能做多大、数据怎样选、GPU 怎样跑得更快。

本路线以 **2026 年五份官方作业**串起模型、系统、缩放规律、数据和后训练。课程保留官方 L01–L19 编号，其中 L18、L19 为嘉宾课；8 个「先修」与 16 个「专题」是编者补充，不是新增的 Stanford 讲次。侧栏按建议学习顺序穿插这些条目，不伪造官方周次。

- **课程笔记**：抓问题、推导、张量形状、设计取舍、易错点与自测。
- **中文译稿**：按真实课堂时间顺序整理讲授、演示与问答；课堂截图只在这里。
- **课程资料**：课外论文和阅读材料的获准译文或明确标注的自主精读；不是把讲过的幻灯片再译一遍。
- **实验说明 / 实验指导**：前者忠实区分官方任务与编者补充，后者给思路与调试路线，不给可直接提交的完整答案。

## 先修自检

如果还不能独立写出小型神经网络的训练循环，先学习站内[《动手学深度学习》](#/c/d2l-pytorch-2021)。已有基础者按下表自检，不必为了顺序把所有桥接从头重学。

| 进入位置 | 编者桥接 | 自检目标 |
|---|---|---|
| L01 前 | [Python 实验工程基础](#/c/stanford-cs336-2026/lec/bridge04?v=notes) | 能建立隔离环境，读异常栈，写小测试，保存配置与结果 |
| L01 前 | [概率、信息论与语言建模](#/c/stanford-cs336-2026/lec/bridge02?v=notes) | 能区分条件概率、负对数似然与采样；知道训练集和测试集为何分开 |
| L02 前 | [线性代数与张量形状](#/c/stanford-cs336-2026/lec/bridge01?v=notes) | 能为矩阵乘法、广播和按轴归约写出输入输出形状 |
| L02 前 | [PyTorch 的内存语义](#/c/stanford-cs336-2026/lec/bridge05?v=notes) | 能区分形状、stride、view、复制及设备迁移 |
| L02 前 | [浮点数与数值稳定性](#/c/stanford-cs336-2026/lec/bridge07?v=notes) | 能解释溢出、下溢与累加误差，知道为何检查有限值 |
| L02 前 | [资源估算与实验纪律](#/c/stanford-cs336-2026/lec/bridge08?v=notes) | 能分别估算参数、优化器状态、激活与运行时间，并记录预算 |
| L03 前 | [反向传播与自动微分](#/c/stanford-cs336-2026/lec/bridge03?v=notes) | 能沿小计算图推导梯度，辨认错误的 detach 和梯度累积 |
| L03 前 | [自回归模型训练闭环](#/c/stanford-cs336-2026/lec/bridge06?v=notes) | 能说明输入与标签错位、因果掩码、更新、验证和保存恢复 |

官网要求熟练 Python、深度学习与 PyTorch、基本系统优化知识，以及微积分、线性代数、概率统计。桥接用于补缺，不把高实现强度的课程变成无需基础的入门课。

## 主线与动手顺序

| 阶段 | 官方讲次 | 动手连接 | 学完要回答的问题 |
|---|---|---|---|
| 模型闭环 | [L01 分词](#/c/stanford-cs336-2026/lec/lec01?v=notes)、[L02 PyTorch 与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)、[L03 架构](#/c/stanford-cs336-2026/lec/lec03?v=notes)、[L04 Attention 替代与 MoE](#/c/stanford-cs336-2026/lec/lec04?v=notes) | [A1](#/c/stanford-cs336-2026/lab/a1-basics?v=zh) | 从文本到 loss 的每一步是什么，模型和优化器状态如何保存？ |
| 训练系统 | [L05 GPU / TPU](#/c/stanford-cs336-2026/lec/lec05?v=notes)、[L06 Kernel / Triton](#/c/stanford-cs336-2026/lec/lec06?v=notes)、[L07](#/c/stanford-cs336-2026/lec/lec07?v=notes) / [L08 并行训练](#/c/stanford-cs336-2026/lec/lec08?v=notes) | [A2](#/c/stanford-cs336-2026/lab/a2-systems?v=zh) | 瓶颈在计算、内存还是通信；优化前后是否仍算同一个东西？ |
| 预算与评测 | [L09](#/c/stanford-cs336-2026/lec/lec09?v=notes) / [L11 Scaling Laws](#/c/stanford-cs336-2026/lec/lec11?v=notes)、[L10 推理](#/c/stanford-cs336-2026/lec/lec10?v=notes)、[L12 评测](#/c/stanford-cs336-2026/lec/lec12?v=notes) | [A3](#/c/stanford-cs336-2026/lab/a3-scaling?v=zh) | 有限预算下怎样分配模型与数据，外推证据和评测协议是什么？ |
| 数据流水线 | [L13 数据来源](#/c/stanford-cs336-2026/lec/lec13?v=notes)、[L14 数据处理](#/c/stanford-cs336-2026/lec/lec14?v=notes) | [A4](#/c/stanford-cs336-2026/lab/a4-data?v=zh) | 过滤、去重与混合改变了什么，如何排除评测污染？ |
| 后训练 | [L15 SFT / RLHF](#/c/stanford-cs336-2026/lec/lec15?v=notes)、[L16 RLVR](#/c/stanford-cs336-2026/lec/lec16?v=notes)、[L17 对齐与多模态](#/c/stanford-cs336-2026/lec/lec17?v=notes) | [A5 推理强化学习](#/c/stanford-cs336-2026/lab/a5-reasoning?v=zh)、[A5 官方选做](#/c/stanford-cs336-2026/lab/a5-safety-optional?v=zh) | 学习信号来自示范、偏好还是可验证奖励；奖励变高意味着什么？ |
| 研究练习 | [L18 Daniel Selsam](#/c/stanford-cs336-2026/lec/lec18?v=notes)、[L19 Dan Fu](#/c/stanford-cs336-2026/lec/lec19?v=notes) | [自拟综合项目](#/c/stanford-cs336-2026/lab/capstone?v=zh) | 能否用清楚的对照实验支持一个有限结论，而非只展示最好的一次结果？ |

L09 → L10 → L11 → L12 仍按官方顺序学习；表中把两次 Scaling Laws 合在同一问题下。嘉宾课只沿用官网姓名，不凭嘉宾研究方向猜测课堂主题。

### 官方作业和自拟项目的边界

五份必做作业是 **A1–A5**。A5 安全对齐是同一作业的 **Optional Part 2**，不是 Assignment 6；自拟综合项目也不是官方作业。为了沿用站点的数字实验页头，A5 两个入口都用 `LAB 5`，自拟项目用 `LAB 0` 并在标题、目标中明示身份。

难度星级、学习顺序和“核心 / 选读”是编者建议，不是 Stanford 评分权重。页面课程进度不计选读；实验任务进度会包含选做和自拟项目，表示个人阅读与实践勾选，不代表官方成绩。实验入口中的任务是主题级导航，正式小题、交付物、约束和测试以固定版本讲义为准。

自拟项目分两条线：一条用自己训练的小模型研究数据、架构或优化；另一条选有相应基础能力的开放模型研究后训练。不要把 TinyStories 上的小模型直接当成已经具备 GSM8K 数学解题能力的基座。

## 深挖专题怎么选

| 读完主线 | 编者专题 | 聚焦的问题 |
|---|---|---|
| L02–L03 | [稳定计算与梯度诊断](#/c/stanford-cs336-2026/lec/ext01?v=notes)、[优化器与训练动态](#/c/stanford-cs336-2026/lec/ext02?v=notes) | loss 看似正常时，怎样定位梯度、更新量与数值异常？ |
| L03–L04 | [位置编码与长上下文](#/c/stanford-cs336-2026/lec/ext03?v=notes) | 位置机制、训练长度和长度外推不是同一个问题 |
| L04、L10 | [Attention 的资源账本](#/c/stanford-cs336-2026/lec/ext04?v=notes) | 训练、prefill 与 decode 的计算和内存项怎样变化？ |
| L05–L06 | [FlashAttention 数学推导](#/c/stanford-cs336-2026/lec/ext05?v=notes)、[GPU 性能分析方法](#/c/stanford-cs336-2026/lec/ext06?v=notes) | 怎样把等价计算重排成更少的数据搬运，并测出真实收益？ |
| L07–L08 | [集合通信算法](#/c/stanford-cs336-2026/lec/ext07?v=notes)、[分片训练与恢复](#/c/stanford-cs336-2026/lec/ext08?v=notes)、[MoE 的系统问题](#/c/stanford-cs336-2026/lec/ext09?v=notes) | 状态放在哪里，通信与负载失衡的代价由谁承担？ |
| L10 | [推理服务与 KV 内存管理](#/c/stanford-cs336-2026/lec/ext10?v=notes) | 延迟、吞吐、批处理和 KV 内存如何相互制约？ |
| L10、L15 | [量化与参数高效微调](#/c/stanford-cs336-2026/lec/ext11?v=notes) | 减少权重存储和减少可训练参数分别解决什么问题？ |
| L09、L11 | [Scaling Laws 的统计方法](#/c/stanford-cs336-2026/lec/ext12?v=notes) | 拟合是否可识别，误差和外推区间怎样报告？ |
| L12–L14 | [数据配方与污染审计](#/c/stanford-cs336-2026/lec/ext13?v=notes) | 数据质量结论依赖哪些分割、混合和去重条件？ |
| L15–L16 | [后训练目标统一推导](#/c/stanford-cs336-2026/lec/ext14?v=notes) | 目标、采样策略、奖励与估计器各自起什么作用？ |
| L17 | [多模态连接方式](#/c/stanford-cs336-2026/lec/ext15?v=notes) | 图像表示怎样连接语言模型，哪些参数和数据在改变？ |
| L03、L08、L10、L16 | [技术报告与源码阅读方法](#/c/stanford-cs336-2026/lec/ext16?v=notes) | 如何从声称、实验配置与实现证据之间找出缺失环节？ |

如果需要复习内存层级、锁与并发，可回看[操作系统工程](#/c/mit-6.s081-2020)；分析多机通信、故障和恢复时，可对照[分布式系统](#/c/mit-6.824-2021)。这两门课提供思考工具，但训练并行不等同于 Raft 共识。

## 共享环境与实验纪律

### 把代码版本、运行环境和数据分开记录

每份作业有自己的官方仓库，不假定它们共用一个环境或一个提交。开始实验前，按该仓库的说明建立隔离环境，使用其声明的 Python 与依赖版本，并记录：

1. 仓库 URL、完整提交 SHA、讲义版本及本地改动。
2. Python、PyTorch、加速器运行时与驱动版本；设备型号、设备数量和可用内存。
3. 数据来源、版本、许可、处理脚本、训练 / 验证 / 测试划分和 tokenizer 版本。
4. 随机种子、配置、有效训练 token 数、精度、并行方式与 checkpoint 路径。
5. 结果指标、测量方法、实际耗时，以及失败和中断记录。

先检查已有环境，而不是直接复制其他课程的安装命令。下面只是信息采集命令，不安装依赖，也不代替作业测试：

```bash
python --version
git --version
# 仅在已安装 PyTorch 的实验环境内执行：
python -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available())"
# 仅在有 NVIDIA GPU 与相应驱动的主机执行：
nvidia-smi
```

不要把 `cuda.is_available()` 为真当成性能或多卡通信验收；为假也不等于所有 CPU 学习实验都不能做。Apple Silicon 的 MPS 后端不是 CUDA / Triton 实验的等价替代。具体依赖安装、训练和评分命令分别属于各作业的固定版本说明；xv6 的 `make qemu`、`make grade` 不适用于 CS336。

### 先查正确性，再花算力

官网建议先在 CPU 上调试正确性，再用作业推荐数量的 GPU 做训练或性能测量。本站把两种运行路径分开：

| 路径 | 可以说明什么 | 不能声称什么 |
|---|---|---|
| 官方规模实验 | 在指定数据、模型、硬件和评测协议下完成题目要求 | 不能以另一种硬件的一次结果替代全部官方测量 |
| 低资源教学实验（编者补充） | 用小形状、小数据或短运行验证局部机制与接口 | 不能据此声称完成官方规模训练、复现论文质量或获得正式成绩 |

开始长训练前，先估算内存和时间，写下预算上限与停止条件。记录峰值内存、吞吐、训练 token 数和精度，不只记最终 loss。GPU 测时需考虑异步执行、预热和同步；这些细节在系统专题展开，不在这里重复实验教程。

校内 Modal workspace 只供正式选课学生，需 Stanford Google 登录和邀请；公开自学账号不带校内集群、共享卷、Slack 或 Gradescope 权限。A3 训练 API 还要求已登记的 Stanford ID 及校内网络 / VPN，不能把任意学号或合成数据练习当成真实 API 的替代。

模型套餐额度不等于 GPU 预算。云算力价格会变化，本页不把官网历史报价当成当前报价；不自动购买、开机或启动收费训练。

### 固定基线与校外边界

| 作业 | 已核讲义版本 | 官方规模或参考配置 | 校外学习边界 |
|---|---|---|---|
| A1 | Spring 2026 · 26.0.3 | 单 B200 参考训练；BPE 主要消耗 CPU / RAM | 有官方低资源路线，但 token 预算与验收目标不同，不算原规模等效完成 |
| A2 | Spring 2026 · 26.1.3 | 通信实验最高 6 GPU；8B 训练 step 排行榜用两张 B200 | CPU / Gloo 可调正确性，不能替代 CUDA / Triton / NCCL 性能证据；Triton 后向为选做 |
| A3 | Spring 2026 · 26.0.5 | 单 B200；12 GPU 小时探索，预测 48 GPU 小时最终配置 | 合成数据仅 Part 1；自建路径需自备计算、数据、存储和服务，README 的 standalone 路径存在静态代码冲突，尚未运行验证 |
| A4 | Spring 2026 · 26.0.1 | 约 430M 固定模型，8×B200，约 8.6B tokens；输入来自 2500 个 raw WET 的英语过滤数据 | 可缩小样本学习流水线，不能冒称完成官方训练；公开下载脚本仍有课程路径与账号配置边界 |
| A5 正篇 | Spring 2026 · 26.0.0 | OLMo-2-0425-1B base + GSM8K；当前 helper 配置双 B200 | 模型和数据有公开路径；原任务还含 MaxRL、GSPO 与自拟估计器，不只是一次 GRPO 演示 |
| A5 选做 | Spring 2026 · 26.0.0 | Llama 3.1 8B 的 SFT / DPO；70B 评委用双卡 | Llama 需要模型访问审批；2026 课程精确 SFT 混合文件的校外下载仍未核实可用 |

这些是固定讲义 / 配置的要求或参考设置，**不是本机实测、最低显存保证或已获计算额度**。集群通用指南建议同时不超过 3 张 GPU，而具体作业有更多卡的配置；应向教学团队确认安排，不擅自开机，也不自行缩小后声称满足官方规模。

各仓库独立建环境：A1/A2 当前锁定 NumPy 2.4.4、PyTorch 2.11.0，A4 要求 NumPy <2，A3 服务端使用 JAX / CUDA 13；A5 使用 Python 3.12、PyTorch 2.10.0、vLLM 0.19.1 和特定 Linux wheel。不要合并成一个“通用安装命令”，也不要承诺 Apple Silicon 能执行原规模 GPU 任务。具体依赖与完整提交 SHA 保存在来源清单。

### 用问题引导实现

先用小输入验证形状、概率归一化、梯度和保存恢复，再扩大实验。阅读论文时记录“问题—机制—假设—证据—局限”；实验指导只提供分阶段提示和失败分析。

官方 AI 政策允许概念与库 API 层面的辅助，但禁止用 AI 实现任何作业或排行榜实验代码，并要求关闭 AI 自动补全。本站只提供解释与调试思路；实现和实验代码由学习者独立完成，不把现成解答当作学习成果。

## 术语与符号约定

术语第一次出现时同时写中文和英文；接口、变量、公式符号及论文原题不擅自翻译。不同论文若使用不同符号，保留原记号并列映射，不把本页的约定强套到原文。

| 记号或术语 | 本路线的默认含义 | 容易混淆的边界 |
|---|---|---|
| token / tokenizer | 词元 / 分词器 | token 不必是词、汉字或单个字符；字节级方案另行说明 |
| $B, T, V$ | 批大小、序列长度、词表大小 | $B$ 必须说明是单设备 microbatch 还是全局有效批大小 |
| $d_{\mathrm{model}}, h, d_h$ | 隐藏维度、注意力头数、每头维度 | 典型布局可用 $[B,T,d_{\mathrm{model}}]$，转置后的轴顺序要另写 |
| $N, D, C$ | 参数量、训练 token 数、计算量 | MoE 的总参数与激活参数分开；数据集大小不等于重复训练后的 token 数 |
| FLOPs / FLOP/s | 浮点运算数量 / 每秒浮点运算数 | 是否把乘加计为两次运算需明确；不要把计算量当吞吐 |
| byte / GiB | 字节 / $2^{30}$ 字节 | 与十进制 GB、元素个数和参数个数分开 |
| arithmetic intensity | 算术强度，单位通常是 FLOP/byte | 必须说明统计哪个存储层级的数据搬运 |
| activation / gradient / optimizer state | 激活 / 梯度 / 优化器状态 | 显存不只有模型权重；梯度累积也不等于保留全部历史计算图 |
| loss / perplexity | 损失 / 困惑度 | 必须说明归约、掩码、对数底及 tokenizer；不同分词器不能直接比较数值 |
| prefill / decode / KV cache | 提示处理 / 自回归生成 / 键值缓存 | 训练激活与推理 KV cache 是不同内存项 |
| DP / TP / PP | 数据并行 / 张量并行 / 流水线并行 | 状态分片与计算划分分别说明；不靠缩写代替通信图 |
| SFT / RLHF / RLVR | 监督微调 / 人类反馈强化学习 / 可验证奖励强化学习 | 人类偏好与可执行验证器提供的学习信号不同 |
| DPO / GRPO | Direct Preference Optimization / Group Relative Policy Optimization | 保留目标和估计器约定，不仅凭算法名称判断具体实现 |
| checkpoint | 训练检查点 | 恢复训练可能还需要优化器、调度器、随机数及数据进度，不等于只保存权重 |

## 论文只在一个位置展开

下面是单一正文归属。精确节号、版本、已读范围与处理类型记录在 `sources/reading-map.json`：A2 明确推荐 FlashAttention 两篇，并要求针对 ZeRO stage 1 做比较；A3 推荐熟悉 Chinchilla 方法。其余课堂引用、方法实现和编者必读不能混成官方全文必读。FineWeb 不等于 A4 引用的 RefinedWeb，DataComp-LM 也不是 A4 指定阅读。

| 论文 | 正文归属 | 共享使用 |
|---|---|---|
| Attention Is All You Need；RoFormer | [L03 课程资料](#/c/stanford-cs336-2026/lec/lec03?v=materials) | L04、位置编码专题 |
| FlashAttention；FlashAttention-2 | [L06 课程资料](#/c/stanford-cs336-2026/lec/lec06?v=materials) | 数学推导专题、A2 |
| ZeRO | [L08 课程资料](#/c/stanford-cs336-2026/lec/lec08?v=materials) | 分片训练专题、A2 |
| Training Compute-Optimal Large Language Models | [L09 课程资料](#/c/stanford-cs336-2026/lec/lec09?v=materials) | L11、统计专题、A3 |
| Efficient Memory Management for Large Language Model Serving with PagedAttention | [L10 课程资料](#/c/stanford-cs336-2026/lec/lec10?v=materials) | 推理服务专题 |
| The FineWeb Datasets；DataComp-LM | [L14 课程资料](#/c/stanford-cs336-2026/lec/lec14?v=materials) | L12–L13、数据审计专题、A4 |
| LoRA；QLoRA | [量化与参数高效微调专题的课程资料](#/c/stanford-cs336-2026/lec/ext11?v=materials) | L10、L15 |
| Direct Preference Optimization | [L15 课程资料](#/c/stanford-cs336-2026/lec/lec15?v=materials) | 后训练目标专题、A5 官方选做 |
| DeepSeekMath；DeepSeek-R1 | [L16 课程资料](#/c/stanford-cs336-2026/lec/lec16?v=materials) | 后训练目标专题、A5 推理强化学习 |
| Learning Transferable Visual Models From Natural Language Supervision（CLIP）；Visual Instruction Tuning（LLaVA） | [L17 课程资料](#/c/stanford-cs336-2026/lec/lec17?v=materials) | 多模态专题 |

获准全文或章节翻译时，保留作者、版本、许可、原文定位和修改说明；许可不明时采用自主中文精读和必要有限短引，明确不称完整译文。课堂讲义已经讲过的内容随译稿整理，不在课程资料再展开一次；课上未讲到的阅读才单独定位。

PagedAttention、FineWeb、DataComp-LM、QLoRA、DPO、LLaVA 的固定论文版本明确使用 CC BY 4.0，可按署名、版本与修改说明等条件翻译。RoFormer 使用 CC BY-NC-ND 4.0，不能据此公开翻译改编；其余已核论文的 arXiv 分发许可也不等于公众翻译许可，采用自主精读。论文许可不自动覆盖模型、训练数据和第三方图像。DeepSeek-R1 本次固定 2026 年 v2，不能套用 2025 年 v1 的节号。

## 引用与来源

- Stanford CS336 教学团队，[2026 官方课程主页与课表](https://cs336.stanford.edu/)，2026-11-14 读取：核对学期、教师 Percy Liang / Tatsunori Hashimoto、19 个官方讲次、先修要求、五份作业及 Optional Part 2 入口、CPU 先调试的建议与诚信政策。本站学习顺序、桥接、专题、星级、符号表与实验纪律为编者整理，不是官方要求逐字翻译。
- 官方 [2026 YouTube 播放列表](https://www.youtube.com/playlist?list=PLoROMvodv4rMqXOcazWaTUHhq-yembLCV)：核实 Stanford Online 发布的 L01–L17 与 L19 共18条，单条时长及英文非 ASR 字幕已保存；L18 Daniel Selsam 未找到。视频开放翻译许可未确认；没有观看全片或完整校订字幕，不把平台字幕分类当成人工准确性保证。
- [固定讲义仓库](https://github.com/stanford-cs336/lectures/tree/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e)：保存17讲讲义及独立 L02 recording trace；这是课后更新的当前版本，不保证与录像完全一致，图片依赖未全部本地下载。仓库未找到统一许可证，不能据公开访问宣称可全文翻译。
- 固定作业仓库：[A1](https://github.com/stanford-cs336/assignment1-basics/tree/a158843b20107949f1a8d7df1b05cd33b9166712)、[A2](https://github.com/stanford-cs336/assignment2-systems/tree/ca8bc81a59b70516f7ebb2da4808daade877c736)、[A3](https://github.com/stanford-cs336/assignment3-scaling/tree/03e9372992e913061b9e78b5cfcb62ad8a87de35)、[A4](https://github.com/stanford-cs336/assignment4-data/tree/0555bea66369872d912652debf10b115ca0688c8)、[A5](https://github.com/stanford-cs336/assignment5-alignment/tree/c2734a26308710949fe13226960a1e8cece94b7e)。五份正篇已由 PDF 内文核实 Spring 2026；A1 README 遗留的2025标题不是讲义年份。A1–A4 有 MIT 许可；A5 未找到明确作业许可证，第三方材料不能继承代码许可。
- A5 官网的旧选做路径已失效。采用从固定仓库发现并核对封面的 [2026 补充讲义](https://github.com/stanford-cs336/assignment5-alignment/blob/c2734a26308710949fe13226960a1e8cece94b7e/cs336_spring2026_assignment5_supplement_safety_rlhf.pdf)（Spring 2026，26.0.0）；另行固定的2025旧版只作对照，不能搬用其 Together 路径、硬件预算或测试接口。
- [2026 集群指南](https://docs.google.com/document/d/1cHE0iKVyXLJ3XpIs2XuXTmZ-HMmPk2hIPeCvy-AydMg/edit)与 [AI 政策](https://docs.google.com/document/d/1SZAlExB1qAc9izHt54gwunNpjKE6wXb8Y7yA_e-baK8/edit)已读取公开正文并存快照；指南公开不等于获得集群资格。未创建账号、获取凭据或运行云任务。
- [Spring 2025 历史官网](https://cs336.stanford.edu/spring2025/)单独存档，只读取历史页身份元数据，不与2026共用视频时间轴。当前首页仍为动态页面，获取日期与哈希见快照记录。
- 实施与审计记录：`sources/P1-REVIEW.txt`、`sources/production-plan.json`、`sources/manifest.json`、`sources/reading-map.json`、`sources/model-preflight.json` 和 `status.json`。登记、采集、实际阅读、撰写、审查、页面验收分别记录；原始大文件和授权不明全文留本地，GitHub 仅提交轻量审计记录与固定链接，不把本地采集说成已远端备份。
