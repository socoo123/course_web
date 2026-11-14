---
title: "资源估算与实验纪律：先把单位和账本写清楚"
lectureId: bridge08
kind: "编者先修桥接，非官方讲次"
sourceVersion: "L02 recording trace @ de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e；PyTorch 2.9 文档快照"
sourceManifest: "sources/p2-bridge-systems/manifest-fragment.json"
status: "CPU 矩阵乘与 Timer 示例已执行；纯算术账本已核对，假设训练时间不是硬件测量。"
mediaStatus: "本桥接无独立官方录像；仅 notes，不制作 draft 或 materials。"
---

# 资源估算与实验纪律：先把单位和账本写清楚

## 1. 一句“这个模型跑得动”至少缺四个条件

先问：**跑什么阶段、用什么 dtype、输入多大、成功的标准是什么？**

- 能加载参数，不等于能完成前向。
- 能完成前向，不等于能保留训练需要的中间值并完成反向。
- 能跑一小步，不等于后续优化器状态创建后仍能跑。
- CPU 微型例子正确，不等于官方规模、硬件性能或训练质量达标。

本页只训练 L02 前需要的基本习惯：分账、单位、粗估与诚实记录。不展开 kernel、通信、并行策略或完整训练实现。

## 2. 先把 byte、GB、GiB 分清

一个普通稠密张量的**逻辑数据量**为：

$$
M_{\mathrm{logical}}=\operatorname{numel}(x)\times\operatorname{element\_size}(x).
$$

FP32 每元素4 byte，FP16/BF16 每元素2 byte；8 bit 才是1 byte。

| 单位 | 字节数 |
| --- | --- |
| kB、MB、GB | $10^3$、$10^6$、$10^9$ byte |
| KiB、MiB、GiB | $2^{10}$、$2^{20}$、$2^{30}$ byte |

例如 $10^9$ 个 BF16 参数的数据量是 $2\times10^9$ byte，即 **2 GB，约1.863 GiB**，不能同时把它写成2 GiB。硬件标称80 GB若按十进制解释，约为74.51 GiB；程序展示值必须先核对口径，而不是直接相减。

这还不是进程的总显存：共享视图并没有为每个逻辑张量复制一份数据，切片也可能保留整个更大的 storage；还有张量元数据、分配器、运行时和其他库的开销。有关共享关系见 [bridge05](#/c/stanford-cs336-2026/lec/bridge05?v=notes)。

## 3. 分账：先数元素，再各乘一次字节数

令 $N$ 为参数元素总数，而不是参数字节数。下面是单设备、未分片的一份**显式假设账本**，不是所有 PyTorch 优化器的默认布局：

| 账户 | 统计对象 | 如何估计 |
| --- | --- | --- |
| 参数 | 当前参与计算的权重数据 | $N\times b_{\mathrm{param}}$ |
| 梯度 | 已分配的参数梯度 | $N\times b_{\mathrm{grad}}$，未创建/已清为 `None` 时另记 |
| 优化器状态 | 例如 Adam 类的两个逐参数状态 | 两个状态各自的元素数 × 各自 dtype 字节数 |
| 主参数副本 | 某些混合精度方案的 FP32 master weights | 若存在，再加 $4N$；若不存在不能凭空添加 |
| 保存的激活 | 为后续计算保留的中间张量 | 逐项 shape × dtype，并考虑 storage 共享与存活时间 |
| 临时 buffer | 算子 workspace、转换副本等短期数据 | 看实现与同时存活峰值，不能仅由 $N$ 推出 |
| 其他 | 输入、输出、掩码等 | 按实际角色分列，避免遗漏或重复归类 |

**不要把“参数占多少字节”再次当“参数个数”乘 dtype 字节数。** 例如参数为 BF16 时 `parameter_bytes = 2 * N`；若梯度也是 BF16，应为 `gradient_bytes = 2 * N`，不是 `2 * parameter_bytes`。

### 手算：1 Mi 个参数不是1 MiB参数

假设 $N=2^{20}=1,048,576$，参数和梯度为 BF16，两个优化器状态各为 FP32：

- 参数：$2N$ byte = 2 MiB。
- 梯度：$2N$ byte = 2 MiB。
- 两个状态：$(4+4)N$ byte = 8 MiB。
- 小计：**12 MiB**，即0.01171875 GiB。

若方案另有一份 FP32 主参数，则小计增加4 MiB，变成16 MiB。若权重本来就以 FP32 保存，并只在部分算子中低精度计算，账本又不同。**“每参数12字节”或“16字节”都必须跟着假设使用。** 这里只核算数据区，不包括少量计步状态和实现额外开销。

再假设本次计算需要同时保留3份互不共享存储的 BF16 激活，每份形状为 `(2, 128, 512)`：

$$
\begin{aligned}
M&=2\times128\times512\times2\\
&=262144\ \mathrm{byte}=256\ \mathrm{KiB}.
\end{aligned}
$$

三份共768 KiB = 0.75 MiB。若同一时刻还存在512 KiB临时 buffer，则在**没有主参数副本、其他开销暂不计、上述账户同时存活**的假设下，总量是：

$$
12+0.75+0.5=13.25\ \mathrm{MiB}.
$$

这只是账本练习；三份激活和临时 buffer 大小是编者给定条件，不是某个真实模型的测量结果。实际峰值不能据此保证。

## 4. 内存峰值是一条时间线，不是所有对象历史总和

对某时刻 $t$ 的实际存活数据，抽象地写成：

$$
\begin{aligned}
M_{\mathrm{peak}}&=\max_t M(t),\\
M(t)&=M_{\mathrm{param}}(t)+M_{\mathrm{grad}}(t)\\
&\quad+M_{\mathrm{opt}}(t)+M_{\mathrm{act}}(t)\\
&\quad+M_{\mathrm{temp}}(t)+M_{\mathrm{other}}(t).
\end{aligned}
$$

要先去除共享 storage 的重复计数，再谈相加。

- 前向期间，某些中间结果被保留；反向推进时，一部分可能不再需要。
- 梯度和优化器状态可能延迟分配，所以“刚创建模型”不是训练峰值。
- 一个大张量被复制时，旧值和新值可能短暂并存；只看复制后的终态会漏掉峰值。
- 两个不同时刻的临时 buffer 不一定需要把各自最大值全加起来；若无法确认存活关系，可以明确标“保守上界”，不能称实测峰值。

CUDA 的几种观测值也要分开：

- `memory_allocated()`：当前由张量占用的 CUDA 分配量。
- `memory_reserved()`：缓存分配器管理的总量，其中**已经包含**相应的已分配部分，不能再与 allocated 简单相加。
- `max_memory_allocated()`：从相应统计起点以来的已分配峰值；记录时要写明何时重置、是否包含模型初始化、是否包含第一次优化器更新。
- 外部设备监视工具看到的进程占用还可能包括上下文、缓存及其他分配，不能直接当“模型参数量”。

`empty_cache()` 只能释放未使用的缓存块，不能释放仍被活张量占用的数据。更重要的是，测量前是否清缓存会改变实验条件，不能一边比较速度一边随意切换。

## 5. FLOPs 是工作量，FLOP/s 才是速度

采用常见约定：一次加法算1 FLOP，一次乘法算1 FLOP；一次 fused multiply-add 虽然可能由一条硬件指令完成，仍按2 FLOPs计。

设：

$$
\begin{aligned}
X&\in\mathbb{R}^{m\times k},\\
W&\in\mathbb{R}^{k\times n},\\
Y&=XW\in\mathbb{R}^{m\times n}.
\end{aligned}
$$

每个输出元素包含 $k$ 次乘法与 $k-1$ 次加法，按这个朴素点积计数是 $mn(2k-1)$。做规模估算时通常记：

$$
F_{\mathrm{matmul}}\approx2mkn.
$$

例如 `(2, 3) @ (3, 4)` 产生8个输出，每个3乘2加，严格按上述计数为40 FLOPs；常见大规模估算式给48 FLOPs。对很小的矩阵，不要把近似式当精确指令计数；对大矩阵则主要看主导项。

单位关系是：

$$
\mathrm{秒}=\frac{\mathrm{FLOPs}}{\mathrm{FLOP/s}}.
$$

“算了 $10^{12}$ FLOPs”没有告诉你花了几秒；“峰值 $10^{12}$ FLOP/s”也没有保证当前小矩阵能跑满这个速度。访存、调度、布局、数据搬运和算子形状都可能影响实际耗时。这里先建立单位意识，不展开后续 roofline 分析。

## 6. 有条件的 $6ND$：能用，但不能见模型就套

对一层稠密线性变换，前向大约做一次矩阵乘，若反向既要计算输入梯度又要计算权重梯度，则还要做两次量级相同的矩阵乘。于是总量约为前向的3倍。

把主要稠密权重数记为 $N$，整个训练期间处理的 token 次数记为 $D$，可以得到常用粗估：

$$
F_{\mathrm{train}}\approx6ND.
$$

使用前先写下条件：

1. **主要工作由这些稠密权重的矩阵乘主导**；$N$ 的口径与参与计算的权重一致。
2. **训练包含前向和所需反向**，不是只做推理；某些层不需要输入梯度时，该局部项会少。
3. **额外开销在本次粗估中忽略或单列**：损失、非线性、优化器更新等并非神秘地消失。
4. **序列相关的额外计算不能压过权重矩阵乘**；长上下文等情形不能无条件沿用这个一阶近似。
5. **没有把额外重算当免费**；有额外计算就另记。稀疏激活模型也不能直接拿全部存储参数数目代入稠密公式。
6. $D$ 是实际处理的 token **次数**，重复训练数据也重复计；不是词表大小，不是去重后的文本长度。

编者算例：若 $N=10^6$、$D=10^8$，则 $6ND=6\times10^{14}$ FLOPs；假设**有效**吞吐是 $10^{12}$ FLOP/s，同口径时间估计为600秒。有效吞吐在这里是人为给定的条件，**不是本机跑分，也不是官方训练预算**。

硬件规格给的是某个 dtype、稀疏性和计算模式下的峰值。用稠密 FP32 任务去除以低精度稀疏峰值，会把时间乐观估错；多设备也不能不计效率就把单卡峰值线性相加。

## 7. 计时要回答“这段区间里到底完成了什么”

### 一个最小而诚实的实验流程

1. 固定输入 shape、dtype、device、stride/连续性和是否跟踪梯度。
2. 在测量区间外生成输入；若要测数据搬运，就把搬运明确纳入区间，而不是忽进忽出。
3. 先 warmup。首次调用可能含延迟初始化、缓存建立或编译等成本；若关心冷启动，把它单独报告，不能混成稳定态样本。
4. 选择一致的计时边界。CUDA 默认异步，普通主机计时需要在起点前排空先前工作，在终点前等待被测工作完成；也可以用正确放置的 CUDA events，并在读结果前等待事件完成。
5. 多次重复，报告中位数和离散程度，而不是只挑最快的一次。记录线程数、设备、库版本和环境负载。
6. 先确认数学结果与 dtype 合理，再解释速度；快但做错工作不是优化。

只在开始前同步、结束时不等待，可能测到的主要是提交工作到队列的时间；只在结束后同步，可能把起点之前尚未结束的工作也算进来。不要为了每个极小算子都同步而无意把同步开销当成算子本身；批量计时与逐次计时要各自说明口径。

### 一个只在 CPU 上观察计时方法的微例

以下不是训练代码，不会下载模型或数据。输入全部为1，因此每个输出元素应为64；它只演示如何把输入准备和被测表达式分开。本批已在既有 PyTorch 2.5.1 CPU 环境执行，输出形状和值符合预期；计时仅代表该本地微例，不作为课程性能基准。

```python
import torch
from torch.utils.benchmark import Timer

x = torch.ones((32, 64), dtype=torch.float32, device="cpu")
w = torch.ones((64, 16), dtype=torch.float32, device="cpu")
y = x @ w
print(y.shape, y[0, 0])  # 数学预期：(32, 16)，64

measurement = Timer(
    stmt="x @ w",
    globals={"x": x, "w": w},
    num_threads=1,
    label="CPU matmul mechanism example",
).blocked_autorange(min_run_time=0.05)
print(measurement)
```

`Timer` 会处理 warmup、重复与相应计时细节。这里测的是**含结果创建的 CPU 表达式**，不是纯 kernel 时间；`min_run_time` 也不是整个脚本的严格总运行时间上限。无梯度跟踪且只有一次矩阵乘，不能称为训练吞吐。要换 CUDA/MPS 等后端，需要使用对应的同步与测量约定，不能把 `torch.cuda.synchronize()` 生搬到其他设备。

这个微例还可以手算：矩阵乘估计 $2\times32\times64\times16=65536$ FLOPs；`x`、`w`、`y` 的逻辑数据量之和为 $4(2048+1024+512)=14336$ byte = 14 KiB。它不是 Python 进程的内存峰值。

### 最小实验记录表

| 必填字段 | 要写什么 |
| --- | --- |
| 目标与结论范围 | 检查 API 语义、单算子速度，还是完整训练？ |
| 代码与软件 | 自己代码的版本、Python/PyTorch 版本；不是只写“最新版” |
| 硬件与后端 | CPU/GPU 型号、线程数、相应运行时；实际使用了哪个 device |
| 输入与模式 | shape、dtype、stride、随机种子或固定值、梯度开关 |
| 计时边界 | 是否包含初始化、分配、搬运、前向、反向、优化器更新 |
| 测量协议 | warmup、重复方式、同步方法、中位数/离散程度 |
| 内存口径 | 逻辑字节、allocated、reserved 还是峰值；统计起点 |
| 输出与限制 | 数值正确性参照、失败信息、未做项目；不填虚构跑分 |

## 8. 低资源实验能证明什么，不能证明什么

CPU 小例可以帮助验证 shape、dtype、别名关系、简单归约和计时协议；它不能验证 CUDA 算子的实际吞吐、多卡扩展性或某次官方训练的质量与预算。

缩短序列、减少层数、减少训练数据都是有效的教学实验设计，但它们改变了任务。报告应写“验证了哪一种机制”，不能写“完成了官方训练”。是否达到官方实验要求，要另按固定版本的任务、数据、硬件/资格和验收标准判断。

这些示例与公式用于概念/API解释，不提供 A1 可提交实现或排行榜代码；使用 AI 的边界仍以课程公共资料中的官方政策为准。没有必要为读懂本页购买 GPU、下载大模型或启动收费算力。

## 9. 自测

<details>
<summary>1. 一份2 GB的 BF16 权重，为什么不能推断2 GB显存就足够训练？</summary>

2 GB只覆盖权重数据区。训练还可能需要梯度、优化器状态、主参数副本、激活、输入输出及临时 buffer；缓存和运行时也有开销。还要先分清2 GB约为1.863 GiB，而非2 GiB。

</details>

<details>
<summary>2. N=2²⁰、BF16参数与梯度、两份FP32优化器状态，一共多少MiB？若再保留FP32主参数呢？</summary>

分别为2、2、8 MiB，共12 MiB；主参数再加4 MiB，变成16 MiB。这里的 $N$ 是元素个数，每个账户只乘一次字节数，尚未计激活和临时峰值。

</details>

<details>
<summary>3. allocated 为3 GiB，reserved 为5 GiB，能写“PyTorch用了8 GiB”吗？</summary>

不能。reserved 包含缓存分配器管理的已分配部分，直接相加会重复计数。外部监测值还可能包含其他运行时占用，应该分别报告口径。

</details>

<details>
<summary>4. 只跑前向也套6ND，再除以硬件最高低精度稀疏峰值，问题在哪？</summary>

6ND包含反向的粗估，与只做前向的工作量不同；峰值的 dtype、稀疏性和计算模式也必须与实际任务匹配。即便口径一致，峰值仍非有效吞吐，不能省略效率与其他耗时的假设。

</details>

<details>
<summary>5. CUDA调用前后立刻读主机时钟，结果非常快，为什么不足以证明算子很快？</summary>

CUDA默认异步，主机可能只完成了入队。要保证计时区间对应被测设备工作真正完成，排除先前未完成任务，并交代同步或事件协议。还需要 warmup、重复和数值正确性证据。

</details>

带着这份单位与账户清单，回到 [L02：PyTorch、einops 与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)。完整的课堂计算、性能直觉与演示在 L02，本页只负责不让基础单位和实验口径绊住你。

## 来源、阅读范围与边界

- [L02 recording 讲义](https://cs336.stanford.edu/lectures/?trace=lecture_02_recording)，固定提交 `de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e` 内嵌 `lecture_02.py`：资源动机、张量数据量、矩阵乘 FLOPs、梯度 FLOPs、优化器分账及计时辅助函数。本文算例与实验记录表为编者原创，不是官方作业要求。
- **静态源码与课堂自纠分开看**：recording 源码647行的 `parameter_memory` 已乘了2 byte，653/656行却仍拿它再乘梯度/状态字节数。实际读取 [L02 录像字幕](https://www.youtube.com/watch?v=kuYAsz7zspQ) 的70:00.700–70:30.980片段，其中 **70:08–70:24** 讲者已说明这应改为“参数个数”，分别乘2与4。因此本页按 $N\times b$ 分账是遵循该修正，不称作编者首次发现并纠正课堂。对应上下文见 [L02 课堂整理](#/c/stanford-cs336-2026/lec/lec02?v=draft)。字幕属平台 non-ASR 分类，不代表逐词人工校订；本页没有核音或看画面。
- PyTorch **2.9**：[CUDA semantics](https://docs.pytorch.org/docs/2.9/notes/cuda.html)（仅实际读取 Asynchronous execution 与 Memory management 开头的相关段落）；[Benchmark Utils](https://docs.pytorch.org/docs/2.9/benchmark_utils.html)（Timer 的 warmup、同步、重复、线程与 `blocked_autorange` 说明）；[Storage](https://docs.pytorch.org/docs/2.9/storage.html)（组成、共享与特殊情况）。版本文档用于核对 API，不等于课程依赖版本或本地测试环境。
- PyTorch 上游 [v2.9.0 LICENSE](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE) 为 BSD 三条款式许可；课程讲义、视频与字幕的开放翻译许可仍未确认，不外推仓库许可。只作自主讲解与有限译述，不发布未经许可的原始全文或截图。
- 逐源哈希、获取 UTC、实际阅读范围与未做事项在 `sources/p2-bridge-systems/manifest-fragment.json` 和 `review.txt`。CPU 微例及算术检查记录在 `sources/p2-shared/cpu-example-check.json`；没有安装课程环境、启动收费任务或执行官方训练。
