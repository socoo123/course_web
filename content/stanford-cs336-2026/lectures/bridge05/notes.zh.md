---
title: "PyTorch 的内存语义：形状变了，数据搬了吗？"
lectureId: bridge05
kind: "编者先修桥接，非官方讲次"
sourceVersion: "L02 recording trace @ de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e；PyTorch 2.9 文档快照"
sourceManifest: "sources/p2-bridge-systems/manifest-fragment.json"
status: "内存语义微例已在 PyTorch 2.5.1 CPU 执行并核对；不代表官方作业环境验收。"
mediaStatus: "本桥接无独立官方录像；仅 notes，不制作 draft 或 materials。"
---

# PyTorch 的内存语义：形状变了，数据搬了吗？

## 1. 先把三个问题分开

看到 `y = x.reshape(...)`，不能只问“输出有几维”。还要问：

1. **逻辑索引**：`y[i, j]` 对应原来的哪个元素？
2. **存储关系**：`y` 与 `x` 是否共享底层数据？修改一个会不会影响另一个？
3. **求导关系**：从 `y` 出发的梯度还会不会传回 `x`？

这三个问题不等价。`clone()` 可以不共享数据而保留求导关系；`detach()` 可以切断求导关系却继续共享数据。本页只补读懂 L02 张量与资源账本所需的语义，不展开反向传播算法。

## 2. 一个张量不只是一串数

对普通的 **strided 稠密张量**，可以把张量理解成“底层存储 + 描述如何读它的元数据”。本页不讨论稀疏张量、`meta` 张量或特殊子类。

| 部分 | 含义 | 常用观察入口 |
| --- | --- | --- |
| storage | 保存实际数据的一维字节区 | `x.untyped_storage()` |
| dtype | 每个元素如何解释、占多少字节 | `x.dtype`、`x.element_size()` |
| shape | 每一轴有多少元素 | `x.shape` |
| stride | 沿某轴前进一步，跨过多少**元素** | `x.stride()` |
| storage offset | 第一个逻辑元素距 storage 起点多少**元素** | `x.storage_offset()` |

设索引是 $(i_0,\ldots,i_{d-1})$，stride 为 $(s_0,\ldots,s_{d-1})$，offset 为 $o$，每元素 $b$ 字节，那么该元素相对 storage 起点的字节偏移是：

$$
b\left(o+\sum_{k=0}^{d-1}i_ks_k\right).
$$

**stride 的单位不是 byte。** 只有最后乘上 `element_size()`，才得到字节偏移。

### 手算：同一块 storage 的三种读法

令 `x = torch.arange(6, dtype=torch.int64).reshape(2, 3)`，底层依次保存 `0, 1, 2, 3, 4, 5`，每个元素8字节。

| 表达式 | shape | stride | offset | 按行看到的值 |
| --- | --- | --- | --- | --- |
| `x` | `(2, 3)` | `(3, 1)` | `0` | `[[0, 1, 2], [3, 4, 5]]` |
| `t = x.transpose(0, 1)` | `(3, 2)` | `(1, 3)` | `0` | `[[0, 3], [1, 4], [2, 5]]` |
| `s = x[:, 1:]` | `(2, 2)` | `(3, 1)` | `1` | `[[1, 2], [4, 5]]` |

三者共享 storage，但并非同一个 Python 对象。

- `t[2, 1]` 的元素偏移是 $0+2\times1+1\times3=5$，值为5。
- `s[1, 0]` 的元素偏移是 $1+1\times3+0\times1=4$，字节偏移为32，值为4。
- `s` 只有4个逻辑元素，却仍引用原来的6元素存储；“逻辑数据量”不等于“为这个视图新分配的字节数”。

这里的转置只改 shape/stride，不把原始六个数重新排列。**逻辑顺序改变，不等于物理搬家。**

## 3. view、reshape、transpose 各自在保证什么

### `view(shape)`：不复制，但形状必须与 stride 相容

`x.view(3, 2)` 按 `x` 原有的逻辑元素顺序重新分组，得到 `[[0, 1], [2, 3], [4, 5]]`。它不是 `x.transpose(0, 1)`：两者形状相同，数值排列不同。

若要把相邻轴合并为一轴，相应轴之间需要满足文档给出的连续性式条件：

$$
\operatorname{stride}[i]
=
\operatorname{stride}[i+1]\operatorname{size}[i+1].
$$

例如 `x` 的 $3=1\times3$ 成立，所以可展平为长度6的视图；`t` 的 $1\ne3\times2$，因此 `t.view(-1)` 不能表示这个展平操作，会报错，而不是偷偷复制。

**非 contiguous 不等于所有 `view` 都失败。** 令 `q = torch.arange(12).reshape(3, 4)[:, ::2]`，它的 shape 为 `(3, 2)`、stride 为 `(4, 2)`。它不是默认连续布局，但 $4=2\times2$，所以 `q.view(-1)` 可以用 stride `(2,)` 表示 `0, 2, 4, 6, 8, 10`。判断依据是目标形状能否由现有 stride 描述，而不是一个粗略标签。

本页说的是 `view(shape)`；`view(dtype)` 是另一重载，涉及按位重新解释，不能代替 `.to(dtype)` 数值转换。

### `reshape(shape)`：保证逻辑形状，不保证是否复制

- stride 相容时，可以返回共享数据的视图。
- 不相容时，需要复制。
- 因此程序不能靠“我这次观察到共享”来保证后续原地修改会同步影响输入。

对上面的转置 `t`，`t.reshape(-1)` 的逻辑结果是 `0, 3, 1, 4, 2, 5`；这个布局需要复制。若算法要求独立数据，明确 `clone()`；若要求严格不复制并且布局不合适就失败，用 `view()` 表达该要求。

### `transpose`：交换轴，而非任意重新分组

`transpose(a, b)` 交换两个轴的形状和 stride；普通 strided 张量中返回视图。不要用 `reshape` 冒充“换轴”：即使元素总数和最终 shape 都对，也可能把每个样本/特征的含义打乱。

## 4. contiguous 不是“给我一份新副本”

默认连续布局可以直观理解为按行遍历时最后一轴走得最快，且中间没有跳过存储位置。本页的 `contiguous` 都指默认 `torch.contiguous_format`；带其他 `memory_format` 的连续性另有定义。

- `x.contiguous()`：`x` 已连续时返回 `x` 自身，不复制。
- `t.contiguous()`：按 `t` 的逻辑顺序复制，得到 shape `(3, 2)`、stride `(2, 1)` 的连续张量；值仍是 `[[0, 3], [1, 4], [2, 5]]`。
- `t.contiguous().view(-1)`：这时可以展平，但复制成本已经在 `contiguous()` 中支付。

因此不要为了“保险”在每次换轴后无条件调用它；先弄清后续算子是否需要这个布局。对于资源核算，额外副本和临时峰值都是真实成本。

## 5. alias、clone、detach：两条轴上的选择

**alias（别名）**指不同引用可能访问同一底层数据，不是这里要求调用的某个专用 API。共享 storage 的两个切片还可能访问互不重叠的区域；“同一 storage”和“元素范围重叠”也不是同一判断。

| 操作 | 是否共享输入数据 | 是否保留到输入的求导关系 |
| --- | --- | --- |
| `y = x` | 是，还是同一个对象 | 原关系不变 |
| `x.view(...)`、普通转置/基本切片 | 是 | 可微操作在启用梯度时保留 |
| `x.reshape(...)` | 可能，不能依赖 | 可微操作在启用梯度时保留 |
| `x.contiguous()` | 已连续时是；否则复制 | 可微操作在启用梯度时保留 |
| `x.clone()` | 否，复制数据 | **保留**，不是停止梯度 |
| `x.detach()` | **是** | **切断**当前求导关系 |
| `x.detach().clone()` | 否 | 切断；适合需要独立存储的数值快照 |

两点特别容易反过来记：

1. `clone()` 的默认 `preserve_format` 会保留合适的非重叠稠密布局。例如转置矩阵的 clone 不一定成为默认 contiguous。**复制与连续性是两回事。**
2. `detach()` 不是数据保护罩。原地改 detached 张量，原张量的数据也会变，还可能触发 autograd 的正确性检查错误。不要用它规避原地修改约束，也不要用 `.data` 绕开检查。

### 微型机制例：先预测，再观察

以下是独立 API 示例，不是任何作业组件；本批已在 CPU 核对注释中的别名、副本和梯度标记结果。

```python
import torch

x = torch.arange(6, dtype=torch.int64).reshape(2, 3)
t = x.transpose(0, 1)
c = t.contiguous()
s = x[:, 1:]

t[0, 1] = 99
# x[1, 0] 变成 99；c[0, 1] 仍为复制时的 3。
print(x.tolist(), c.tolist())
print(x.stride(), t.stride(), s.storage_offset())

u = torch.tensor([2.0, 3.0], requires_grad=True)
v = u.clone()
w = u.detach()
frozen = u.detach().clone()
print(v.requires_grad, w.requires_grad, frozen.requires_grad)
# 预期 True, False, False；不在本例中原地修改需要梯度的 u。
```

如要观察存储，可比较仍存活、非空的普通张量的 `untyped_storage().data_ptr()`。不要把 `tensor.data_ptr()` 当 storage 起点：带 offset 的切片可以与原张量共享 storage，却拥有不同的首元素地址。地址观察只是这个小例的辅助证据，不是通用的别名检测器。

## 6. 写代码前的四句自问

- 我是在**换轴**，还是只在**重新分组元素**？
- 我是否依赖“不复制”，还是依赖“独立副本”？有没有用对 API？
- 如果这里修改数据，哪些仍存活的视图会看见变化？
- 资源表里算的是逻辑元素量，还是不同 storage 的实际驻留量？共享视图不能逐个累加当新分配；小切片也可能让大 storage 继续存活。

基本切片通常返回视图，整数列表/张量等高级索引的取值通常返回副本；但 `x[index] = value` 是对 `x` 的原地赋值。不要把“取值返回副本”误解成“用这个索引赋值不会改变原张量”。

## 7. 自测：能解释原因才算过关

<details>
<summary>1. x.view(3, 2) 与 x.transpose(0, 1) 形状相同，为什么不相等？</summary>

前者把原有顺序 `0,1,2,3,4,5` 按每行2个重新分组；后者交换行列对应关系，按行看到 `0,3,1,4,2,5`。形状只描述轴长，不规定元素语义。

</details>

<details>
<summary>2. s = x[:, 1:] 的第一个元素离 storage 起点多少字节？s 是否新占了32字节数据区？</summary>

这里 `x` 是 int64，offset 为1，所以第一个元素偏移8字节。`s` 有4个逻辑元素，即32字节的逻辑数据量，但它没有为这些值单独复制数据，而是共享原来的48字节 storage；张量元数据仍有自己的开销。

</details>

<details>
<summary>3. 想保存“以后修改原张量也不会变、而且不保留梯度关系”的数值，detach() 够吗？</summary>

不够。`detach()` 继续共享数据；需要独立存储时可用 `x.detach().clone()`。只用 `clone()` 虽然复制了数据，却仍可能保留求导关系。

</details>

<details>
<summary>4. contiguous() 和 clone() 能互换吗？</summary>

不能。前者在已经满足指定连续布局时返回自身；后者会复制，但默认可保留转置矩阵的非默认连续 stride。一个保证布局，一个保证数据副本，目标不同。

</details>

完成后回到 [L02：PyTorch、einops 与资源核算](#/c/stanford-cs336-2026/lec/lec02?v=notes)，把“看懂张量”接到完整资源账本。本页不重复 L02 的 einsum、训练循环或系统性能推导。

## 来源、阅读范围与边界

- 课程锚点：[L02 recording 讲义](https://cs336.stanford.edu/lectures/?trace=lecture_02_recording)，固定仓库提交 `de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e`，实际读取内嵌 `files[lecture_02.py]` 的开场、张量数据量与资源相关段落；本页内存布局教学是**编者补充**，不宣称录像逐项讲过这些 API。
- PyTorch **2.9**：[Storage](https://docs.pytorch.org/docs/2.9/storage.html)（组成、共享、指针与特殊情况）；[Tensor Views](https://docs.pytorch.org/docs/2.9/tensor_view.html)（正文）；[Tensor.view](https://docs.pytorch.org/docs/2.9/generated/torch.Tensor.view.html)（shape/stride 约束与 dtype 重载说明）；[clone](https://docs.pytorch.org/docs/2.9/generated/torch.clone.html)、[detach](https://docs.pytorch.org/docs/2.9/generated/torch.Tensor.detach.html)（完整 API 正文）。这是固定版本文档快照，不是声称课程安装环境恰为2.9。
- 上游 PyTorch 仓库 [v2.9.0 LICENSE](https://github.com/pytorch/pytorch/blob/v2.9.0/LICENSE) 为 BSD 三条款式许可；不把代码仓库许可外推给课程录像、外链图片或整个文档站资产。课程讲义开放翻译许可未确认；本文为自主讲解与自拟算例，不复制讲义全文。
- 逐源 URL、SHA256、UTC 获取时间及阅读范围在 `sources/p2-bridge-systems/manifest-fragment.json`。没有下载媒体、截帧或核音；微例结果见 `sources/p2-shared/cpu-example-check.json`，运行版本为 PyTorch 2.5.1 CPU，不是课程依赖验收。
