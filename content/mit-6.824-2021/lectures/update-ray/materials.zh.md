---
source: Stephanie Wang 等，Ownership: A Distributed Futures System for Fine-Grained Tasks，NSDI 2021；MIT 6.5840 Spring 2026 指定论文、Ray 讲义和 FAQ
license: 论文公开全文翻译许可未确认；本页为自主中文精读，不是全文译文。课程自有讲义/FAQ 的 CC BY 3.0 US 不延伸到论文。
status: PDF 1–16 页全文、摘要、§1–7、致谢、56 条文献条目、附录 A–B 已读；15 图、3 表、图内 API/代码和附录公式均实际看页。讲义与 FAQ 全文已读；未追读外链、现代源码或运行实验。
---

# Ownership 论文精读：元数据、内存与恢复怎样一起去中心化

## 1. 接口的表达能力：异步、远端存储、一级值是不同维度

**摘要、§1–2，PDF 第 1–4 页；Figure 1–3、Table 1。**

Figure 2 把两条轴画开：同步/异步决定 caller 是否等待；按值/按引用决定数据是否必须经过 caller。只加 futures 的异步 RPC 可以并行计算两个输入，却仍可能把两个大结果搬回 driver。只加远端内存可以少搬数据，却仍可能按顺序等待。分布式 futures 把两者结合。

论文默认共享对象不可变，因而不需处理多份副本各自改写同一值的一致性冲突。这不意味着系统没有元数据同步问题，也不禁止 actor 在自身进程中保持私有可变状态。

### 1.1 Table 1 中六类操作如何配合

| 操作角色 | 具体语义 | 容易忽略之处 |
|---|---|---|
| 调用普通远程函数 | 立即得到 DFut，任务含函数、参数和资源要求 | 得到句柄不等于结果已物化 |
| 普通 DFut 参数 | 在执行被调函数前，由系统隐式解引用为值 | 用户函数开始运行时看到的是值 |
| get | 等到值已计算且本地可用，返回值的副本 | 等待计算与等待传输都可能阻塞 |
| del | 从调用者作用域删除一条引用 | 表中是显式程序操作；删除一个引用不代表全局回收 |
| shared 与 SharedDFut 参数 | 把 future 本身交给被调方，使其成为 borrower | 被调方可继续传递，不必先取大数据 |
| actor 方法调用 | 任务绑定到该 actor 所在进程 | 同样返回 DFut；actor 引用 ARef 也可传递 |

Table 1 注释还允许任务直接返回 DFut，产生嵌套 future；使用时可自动展平。但“接口展平”没有消除内部回收时对嵌套关系的跟踪，见 §5.3。

`shared` 是论文抽象接口。2026 讲义用 `@ray.remote`、`.remote()`、`ray.get()` 和 `Counter.remote()` 演示 Python 表达方式，并链接 latest 文档；它们不是把 Table 1 所有符号逐字映射成今日 API 的承诺。讲义的并行注释只能说明调用可并发，实际并行还依赖资源和调度。

### 1.2 两种应用为什么同时需要不同能力

**模型服务：** Figure 3(a) 的 Preprocess 处理输入图像，Router 按应用策略选 Model。Model actor 将权重保留在 GPU；Router actor 可攒批，也可到超时时提前发批以限制延迟。Router 接收的是 first-class future，因此它负责“选谁”，不必承担“复制全部图像”。分布式系统没有替应用决定模型版本灰度等业务路由策略。

**在线视频：** Figure 3(b) 的 Decode、Flow、CumSum、Smooth、Sink 既有帧内阶段依赖，又有跨帧数据或状态依赖。Flow 跟踪相邻帧运动，CumSum 累加轨迹，Smooth 做移动平均；Decode actor 保持解码状态。每阶段约毫秒到数十毫秒，不能先等整批未来视频帧到齐才开始工作。

当帧到来，程序动态创建对应工作，系统按依赖流水执行并回收不再使用的帧。多条视频流可各有一个嵌套 driver；把独立流的控制逻辑拆开，也是控制面分片的一部分。

## 2. 四种元数据与三种架构选择

**§3，PDF 第 4–6 页；Figure 4–6。**

Figure 4 比较“已有值的远端指针”与“尚未计算的 future”：前者可以随引用带上已知位置；后者可能还没有最终执行位置。消费者不能看到空位置就认定失败。Figure 5 则说明：按值 RPC 重试时调用者仍有参数；按引用执行时，节点故障可能把参数值也一起带走，需要保存创建输入的 lineage。

由此出现四类状态：

1. **已物化值的位置**：让持有者能找到字节。
2. **使用关系**：保证回收不早于最后一位使用者。
3. **未完成任务的位置**：判断 future 是否因 executor 失败而无法完成。
4. **lineage**：任务描述及输入依赖，用于重建丢失值。

三种设计不是简单的“有无中央服务器”：

| 设计 | 记录位置/时机 | 好处 | 主要代价 |
|---|---|---|---|
| 同步中央 master | 派发前先在 master 记录 | 故障与恢复决策集中、易理解 | 额外往返；控制吞吐集中；分 shard 仍有跨进程同步 |
| 分布式任务租约 | 元数据异步写，全局视图允许滞后；worker 更新任务租约 | 减少同步远端写，可分片 | 等租约过期影响恢复；谁重建对象还需协调 |
| Ownership | caller 的本地表同步记录其拥有的 futures | 常见路径本地化；owner 对其对象集中决策 | owner 失败要扩大失效范围，应用结构影响扩展性 |

论文允许已物化对象位置短暂不准确，因为可向候选位置验证；但用于失败判断的任务位置要与转交保持同步。最小方案并不将 owner 表做同步复制，而是靠 fate sharing 和祖先重放恢复。保存 owner 状态以缩短恢复时间被列为未来扩展。

## 3. 身份与调度协议的实现细节

**§4–4.1，PDF 第 6–7 页；Table 2、Figure 7–8。**

### 3.1 三层架构和表字段

每节点包括多个 worker、一个 scheduler 和一个 object store。worker 管 future 解析、计数和恢复；scheduler 管本地资源与跨节点重定向；object store 管不可变数据及节点间传输。同节点通过共享内存减少 worker 间复制。

TaskID 由父 TaskID 与父任务已提交的任务序号进行 hash 得到；根 TaskID 随机生成。ObjectID 再组合 TaskID 与返回对象序号。DFut 包含 ObjectID 及 owner 地址，后者是 IP、端口、WorkerID。讲义的 `parentTaskId + task_index` 是概要，论文明确为 hash，不应解释为字符串相加就是完整实现。

owner 表记录 ID、Owner、Value、References、Task、Locations。Value 有三态：尚未计算；指向 distributed memory；小对象的内联值。Locations 对未完成任务表示任务位置，对大对象表示副本位置。borrower 保存 Table 2 带星号的前四类字段，而不是完整复制 owner 的 Task；正文另说明可缓存 owner 提供的位置。

actor 也有 ID/Owner，用同一张表定位；其 Location 为 actor 地址。worker 在论文模型中一次执行一个任务，但任务可再提交子任务；不能把一个节点上的所有 worker 与一个进程混为一谈。

### 3.2 每次重定向都把决策交回 owner

owner 通常先向本地 scheduler 发送资源要求和 distributed-memory 参数，也可为数据局部性直接选远端 scheduler。

若 scheduler 接受，它先获取参数、分配资源，再把某个 worker 租给 owner；若拒绝，它返回所选远端节点。owner 接到响应后更新本地 Locations，再向被租 worker 派发，或在下一节点重复申请。因此 scheduler 不能悄悄把任务一路转走而不通知 owner。

已租 worker 满足后续任务资源要求时，owner 可直接再次派发，跳过 scheduler。当前论文实现**不复用给具有不同 distributed-memory 依赖的任务**，因为那些参数由 scheduler 预取。owner 无任务可发或到配置的到期时间后归还资源；其他撤销策略留待后续。

Figure 8(e) 的 critical path 用本地、远端 RTT 分开计量，不是所有方案都只“省一次 RTT”：

| 方案与目标位置 | 本地 RTT | 远端 RTT |
|---|---:|---:|
| Master，本地或远端任务 | 1 | 1 |
| 旧任务租约，本地任务 | 1 | 0 |
| 旧任务租约，远端任务 | 1 | 0.5 |
| Ownership，本地任务 | 0.5 或 1.5 | 0 |
| Ownership，远端任务 | 0 或 1 | 0.5 或 1.5 |

表对应图里的 master/节点放置和是否可复用资源；半个 RTT 表示单向派发这一段。最坏路径因为绕回 owner 可能更长，常见复用路径则更短。这也是不能仅凭架构图宣称所有任务延迟都下降的原因。

### 3.3 actor 的资源寿命不同

actor 构造任务像普通任务一样放置，完成后却不归还 worker lease；只要 actor 仍有引用，该 worker 专门执行通过 ARef 提交给它的任务。调用者先向 actor owner 查询地址，可缓存后直接派发；actor 重启后再查询。

这个持久资源绑定让模型权重保温，也限制任务移动的自由。论文只规定同一 caller 的提交次序，不为任意跨 caller 调用补充顺序语义。FAQ 的“优先本地、否则询问随机 scheduler”是课程概要；论文将具体调度策略抽象掉，其协议不依赖这一随机选择是唯一策略。

## 4. 大小对象双路径与 pin 的职责

**§4.2，PDF 第 7–8 页；Figure 9。**

### 4.1 并非所有结果都进 object store

系统在创建结果时按可配置大小阈值决定传值还是传引用。小值直接返回 owner，每个持有者得到一份副本；大值存进 distributed object store，返回的是引用。后者少复制大数据，却至少要付一次读取 object store 的 IPC 等成本，因此不总适合几个字节的结果。

Figure 9 的完整路径是：B 创建并 pin 大对象 X；把引用交给 A；A 在输入可用后派发 C；C 的节点从 object store 获取 X，可能形成 secondary copy；C 产生的小 Y 直接回给 A。数据经过哪里，与谁维护元数据，是两张不同的路径图。

若任务 caller 本身借用了参数，必须先向该参数的 owner 请求 Value。owner 待值就绪再回复内联内容或 distributed-memory 指针；caller 才能准备下游任务描述。其他进程无需自行判定空目录是延迟还是失败。

### 4.2 primary 是被固定保留的那份，不是共识主副本

首份大对象为 primary，在 owner 释放或失效前保持 pinned；secondary copies 可用作 LRU cache，内存紧张时可淘汰，无须每次向 owner 询问。它们是不可变对象的副本，不是可分别接收写入的 primary-backup 状态机。

对象存储提供 Create、Pin、Release、Get。Pin 指定位置并在该节点失败时返回 false；Release 表示“可淘汰”，不是立即物理删除；Get 找不到任何副本时等待某个 worker 重建后 Create。**object store 本身不负责沿 lineage 重新执行任务**，责任在 ownership 层。

懒惰淘汰有恢复价值：已经允许回收但尚未被内存压力挤掉的 secondary，可能免去一长串重算。但它没有变成可靠持久存储，不能拿缓存残留作为一定存在的恢复边界。

## 5. 附录 A：分层计数不能只写成“加一、减一”

**§4.2、§4.3 与附录 A，PDF 第 8–9、16 页；Table 3。**

### 5.1 每个持有进程跟踪五类关系

| 字段 | 何时仍有作用 | 主要控制的回收对象 |
|---|---|---|
| Local reference | future 仍在进程作用域中 | 值 |
| Submitted task count | 本进程提交的依赖任务尚未完成 | 值 |
| Borrowers | 本进程通过 first-class 传递创建的其他持有者 | 值及后续跟踪责任 |
| Nested DFuts | 仍在作用域内的其他 future，其值包含本 future | 被包含 future 的值 |
| Lineage count | 依赖本 future、可能再次执行的 Task 记录仍存在 | Task / lineage，不要求一直 pin 值 |

若 future 从不离开 owner 作用域，owner 已知所有待完成依赖任务，不需要额外分布式计数协议。借用允许控制逻辑下放，才需要跨进程跟踪。

### 5.2 借用树的收缩需要转交责任

创建 borrower 有两种方向：任务把 SharedDFut 传给子任务；或者把 SharedDFut 返回给父任务。发送方记录接收方 worker ID，形成追踪结构，许多维护信息可搭载在调度请求与完成回复上。

常见情况下，子任务完成时已经没有本地引用和依赖任务，owner 可随完成回复去掉它，避免额外逐引用 RPC。若子任务已提交的工作仍在运行，或 actor 将引用存进状态，则回复必须说明仍在借用。

最终 owner 对其 borrower 集合发出等待归零的请求。borrower 在本地引用及待完成任务消失后，回复自己累计的 borrower 集合；owner 去掉旧 borrower、合并新集合，再继续询问。**附录明确说 borrower 自己不从本地 borrower 集合中删除条目。** 因此这个协议不是每个节点各自看计数零就悄悄忘掉下游。若 borrower 先死亡，owner 收到死亡通知后移除它。

以 A→C→D 为例，C 提前返回但 D 仍用 x，必须保留这一事实。可以由 C 继续报告借用，待其本地使用结束时把后续跟踪关系移交给 A；不能因为 C 返回就把整条分支剪掉。

### 5.3 嵌套 future 与 lineage 分开计数

任务返回另一个 future 时，外层 future 的值包含内层 future。即使普通下游使用会自动展平，也必须记录谁包含谁；只要包含关系仍在作用域内，内层值就需保持 pinned。

lineage 则是另一种寿命。传 x 给新任务时增加 x 的 lineage count；依赖任务的 Task 字段被回收时才减少。任务已经完成仍可能重跑，所以“任务完成”和“任务配方可删”不是同一事件。

所有返回值都按值内联、任务完成后，不必再为这些结果保留重建描述；对按引用返回的对象，必须等它们及依赖关系不再需要重建。只有 Task 与 Value 都能收集，才删除对应记录。系统级对象 checkpoint 以提前收集 lineage，是论文列出的计划；不要与 §7 的应用级 Redis checkpoint 混成一个已实现通用接口。

## 6. 恢复协议：检测、对象重建、owner 重建各管一层

**§4.3，PDF 第 8–9 页；Figure 10–11。**

worker 不相互全连接发心跳；本地 scheduler 发布 worker 失败，节点之间通过心跳检测节点失效，节点上的 workers 与节点 fate-share。通知携带 worker/node ID，各 worker 扫描自己的 ownership 表：匹配 Locations 表示自己拥有的任务/值丢失；匹配 Owner 表示恢复协调者丢失。

### 6.1 丢值先找副本，再重放必要依赖

owner 首先尝试把 secondary 提升为 primary。无法找到可用副本才读取 Task 字段重新提交生产任务；其输入若也缺失，再递归重建。多数依赖可能由同一 owner 管理，所以可本地遍历；若 lineage 中包含借来的引用，则向相应 owner 请求重建。

Figure 10 中节点 2 丢失 X，W1 仍有 B 的描述，可安排新节点 4 执行 B。正在等待的 C 不负责判断目录迟迟没有位置的原因，只需等待 owner 处理。待输入恢复即可继续，未丢失的数据不必全部回滚。

### 6.2 丢 owner 不尝试现场拼回旧表

Figure 11 中 W1 失效，旧对象、资源 lease 和持有它所拥有引用的任务被一起回收/终止；A 的 owner 再次提交 A，新执行重建其控制状态、子任务与引用。这样避免同步持久化每次 owner 表更新，却付出额外重执行成本。

论证按引用传播的 API 分情况：传给子任务，使子/后代成为持有者；返回给父任务，使父成为 borrower，并可能向上扩大 fate sharing。重放这些任务才能让引用指向新 owner，而不是期待旧 DFut 内的地址自行变正确。

这一论证对 actors 有明确限制：透明恢复要求不把 borrowed DFuts 留在 actor 本地状态。附录 A 可以追踪这种保存以做内存管理，不代表 §4.3 已证明它透明恢复正确。应用也可选择只依赖故障检测，自行处理恢复。

### 6.3 actor 重启与业务状态恢复分离

actor 自身失败时，owner 重新提交构造任务；actor owner 失败时，actor 和 ARef 持有者命运共享。actor 的可变状态如何恢复不在本工作范围。对只读、可检查点或暂态状态，可以叠加相应恢复方法；任意非确定性和外部副作用不能自动交给 lineage。

整个应用与 driver fate-share。owner 表持久化、进一步减少重放范围是未来方向，而不是本协议已提供的无单点保证。核心不变量与失败反例见[课程笔记 §5–9](#/c/mit-6.824-2021/lec/update-ray?v=notes)。

## 7. 性能评估：把负载、基线与计量口径一起读

**§5，PDF 第 9–12 页；Figure 12–15。以下均为作者实验，不是本站复现。**

### 7.1 基线并不是“所有版本的 Ray”

论文比较按值 futures、Ray v0.7 的分布式任务租约方案、由 v0.7 修改的同步中央 master，以及 Ownership。distributed-futures 系统使用分片且未复制的 Redis 保存所需全局元数据，异步请求；都采用 Ray 的调度层和适用的 object store。Ownership 与按值方案使用 gRPC 做 worker 间通信。

实验在 EC2，默认 head node 为 m5.16xlarge，具体变体另注。任务被安排到预定节点以减少调度变动。因此这些微基准主要隔离控制路径，不是一次任意负载、任意放置策略的全面产品竞赛。

### 7.2 Figure 12：横向与单节点控制面扩展不同

每 5 个 m5.8xlarge worker 节点增加一个中间 driver，后者向自己的 5 个节点提交 no-op 叶任务。图纵轴为叶任务 tasks/s；返回值为短字符串或 1 MB 数据。中间 drivers 或聚集在同一 m5.8xlarge，或各占一台。

- **(a) 小对象、drivers 聚集：** Ownership 与按值路径接近，约到每秒八万任务一带后趋平；两基线的每节点控制进程更早受限。不是 worker 多了就永远线性。
- **(b) 小对象、drivers 分散：** Ownership 与按值路径随节点数增长，百节点约到每秒二十多万；租约方案也扩展，但斜率较低。小结果直接内联给 owner，减少了每次取结果的 RPC。
- **(c) 大对象、drivers 聚集：** Ownership 仍优于基线，但绝对吞吐低于小对象，需支付对象管理与回收开销。
- **(d) 大对象、drivers 分散：** Ownership 与租约吞吐接近，百节点约十五万任务/秒；Ownership 还提供论文所述内存安全。大对象的按值基线没有稳定结果，因为作者实现缺少 backpressure，图中缺失不是“吞吐为零”。
- **(e) 同节点借用扩展：** 共 100K 个 no-op 任务，共享 driver 创建的 1 MB 输入；x=0 为 driver 直接提交，x=1 为单个借用者，之后增加嵌套任务。Ownership 约提升两倍，基线改善很小，说明分层计数与分散提交可以一起去掉单进程瓶颈。

中央 master 使用两个 shards，在约 60 个节点后趋平；再增加 shard 可推迟瓶颈，但不会消除远端记录成本。图上近似读数用于辨认趋势，不应当作公开的精确性能表。

### 7.3 Figure 13：测的是开始执行前的延迟

driver 提交 3000 个任务，共享一个 1 MB 参数，每个立即返回短字符串；worker 或与 driver 同节点，或在另一台 m5.16xlarge。横轴分本地 actor、本地 task、远端 actor、远端 task；纵轴毫秒，误差线为这 3000 个任务的标准差。

按值路径反复复制大输入，延迟较高。Ownership 相对 centralized 和 leases 平均约低 1.6 倍，来自本地元数据写与 worker lease 复用。它是这个实验的平均启动延迟比较，不是所有函数从调用到业务结果的固定“1 ms 保证”。

### 7.4 Figure 14：纵轴是相对总运行时间，不是恢复秒数

一串依赖任务在远端 m5.xlarge 上执行；每个按横轴指定的毫秒数 sleep，总计算时间为 10 秒。返回值分别为短字符串和 10 MB 数据。纵轴为相对“Ownership 无故障”的总运行时间，使用对数刻度。

故障实验在作业开始 5 秒时杀掉并重启 worker 节点，心跳超时 1 秒；中央 master 未做此实验，原因是实现成本，不能给它补一条恢复曲线。

正常运行中租约方案最多可比 Ownership 快约 1.18 倍，但失败时要等各任务租约过期，恢复拖累明显，甚至不如整作业重启。v0.7 通过倍增租约时限减少续租负担，又使长任务恢复更慢。Ownership 的总运行时间保持在无故障约两倍以内；小结果时只重跑在途任务，大结果时沿 lineage 恢复并减少正常运行的数据复制。这个结果依赖指定的故障时点与链状负载。

### 7.5 Figure 15(a)：中位数一样，尾部仍可差一个数量级

模型服务用 4 台 p3.16xlarge，每台 1 个 Router 和 8 个 ResNet-50 Model，batch size 为 16，输入 2300 requests/s。Ownership 与 centralized 中位延迟同为 54 ms；论文报告尾部为 108 ms 与约 1 秒，约九倍差距。

消融 `Ownership -borrow` 让 Router 接收图像值而不是 first-class future，再复制给 Model：p50 升至 80 ms，p100 到 3.2 秒。Figure 15(a) 右半专门放大 p95–p100，不能只看左图拥挤在一起的中位区域。此处说明的是数据路径与路由瓶颈，不是宣称 actor 本身让模型计算加快九倍。

### 7.6 Figure 15(b–c)：worker failure 与 owner failure不能合并

视频实验为 60 条并发流，每流一台 m5.xlarge worker；另有 owner 节点，每台容纳四个 driver。输入 29 frames/s，移动平均半径 1 秒。Decode actor 有跨帧状态，但允许付出延迟重读早先帧，使任务可以重执行。

无故障时各方案中位延迟约 65 ms；leases 和 centralized 尾部约为 1208 ms、1923 ms。故障图只画 p90 以上，横轴单位改为**秒**。

旧租约方案在开始 5 秒后注入 Decoder actor 故障，需要重放解码任务且反复受租约到期延迟影响；其 lineage 不能安全回收，也阻碍了该实现的 checkpoint 方案。Ownership 的不同故障试验在 10 秒时注入：worker failure 恢复约 1.9 秒，owner failure 因需重跑更长历史约 8.8 秒。

作者再加入应用级 checkpoint：每秒把转换一帧所需的中间状态（如累计轨迹和）写入远端 Redis；sink 收到转换结果后写帧索引，提交这个 checkpoint。图中正常开销可忽略，owner failure 恢复约 1.1 秒。这里既有状态保存，也有输出到达后的提交标记；不能把它概括成“定时存一份变量就够了”。

不同方案故障时点并不全部相同，图中不是严格同一故障事件下所有路径的单变量对比。checkpoint 是应用在 Ownership 之上实现的实验方案，没有填补任意 actor 状态自动恢复的缺口。

## 8. 附录 B：形式化检查到底覆盖了什么

**PDF 第 16 页。**

作者给 ownership 表建立状态转换模型，涉及任务调度、垃圾回收和 worker failures。目标包括三类性质：

- **Safety：** 存在依赖任务时，不可提前丢失重建其值所需的 lineage。
- **Liveness：** 在模型的条件下任务最终执行、future 得到解析，Get 最终返回。
- **No resource leakage：** 所有引用出作用域后，任务状态与值最终清理。

页面中的递归定义可整理为：

$$
\operatorname{LineageInScope}(x)\ \triangleq\
(x=\text{INLINE\_VALUE})\ \lor\
\left(\forall a\in x.\mathrm{args}:\operatorname{LineageInScope}(a)\right).
$$

其直觉是：内联值已经随持有者保存；否则依赖输入也必须递归具备安全的重建条件。这个抽象表达式不是把完整实现的所有判断都列完的可执行恢复算法，更不是证明外部副作用可重放。

TLA+ Model Checker 检查至多 3 层递归远程调用、每函数至多创建 3 个 futures，共超过 4400 万个不同状态，并报告 safety/liveness 成立。**模型当时不包含 first-class futures 或 actors。** 因而不能用它替前面的复杂 borrowing/actor 情况背书，更不能称为现代 Ray 源码已获完整机器证明。本任务只阅读模型说明，没有下载或运行规格。

## 9. 相关模型与论文自己的实现边界

**§6–7、致谢和文献表，PDF 第 11–15 页。**

论文没有把 futures、distributed memory 或 lineage 宣称为新发明。其贡献在于对细粒度动态任务，把自动内存管理与故障协调低开销地放在 caller 的 ownership 上。

- 与集中式 CIEL、Dask 等分布式 futures 系统相比，重点是控制状态直接放到调用任务的 workers。
- 与数据并行系统相比，强调运行时继续创建任务的灵活性；静态任务图的细粒度执行和动态控制流不是一个维度。Nimbus 的 execution templates 可缓存重复控制决策，与这里逐任务分散调度可互补。
- 与 actor supervision 相比，继承“监督者处理子工作失败”的思想，并把监督范围扩展到对象、引用与对象重建。
- 与 MPI 相比，提供按引用与语言层任务依赖；与 Legion 等并行运行时相邻，但这里聚焦分布式失败检测和恢复。
- 与可变 DSM 相比，不提供全局任意可写地址空间。object store 的耐久性是恢复优化，而非唯一正确性基础；计算依赖语义让系统有机会用重算代替持久保存所有中间值。

§7 说 ownership 成为 Ray v1.0+ 架构基础，约 14K 行 C++；此前全局分片元数据的延迟问题促成 v0.7 租约，后者仍难扩展多对象协议，最终引向 ownership。论文同时坦言：当时 ownership 透明恢复尚未被广泛使用，用户更常获得的是性能、正确的失败检测和垃圾回收。定制恢复需求与重放成本，使透明对象恢复成为可选项。

这里的“v1.0+”与使用情况是 2021 论文叙述，不是当前版本功能表。56 条文献条目与致谢已读，不代表独立读过所列论文、产品文档或 artifact。

## 10. 2026 讲义与 FAQ 的补充和校注

讲义用先中央表、再对象 ID 分片、最后按 ownership 分片的思路解释设计；这条教学路线在[课程笔记 §2–7](#/c/mit-6.824-2021/lec/update-ray?v=notes)展开，不再逐条复制课堂提纲。其最后问题是 C 调用 D 得到 z，D 未完成就失败；因 C 是 z 的 owner，应由 C 重提 D。

有三处需要保持原文与技术结论的区别：

1. **失败角色：** 讲义 195–198 行在“loss of an owner”下简写“2 crashes…3 fails and 1 fails”，与前面的 W1=A(owner)、W2=B(producer)编号不自洽。其 200–208 行及论文 Figure 10–11 更明确：W2 丢失而 W1 存活是对象/执行者恢复；W1 owner 丢失才需要 fate sharing。正文按后者说明，不把讲义这段简写扩成新规则。
2. **借用与可变性：** FAQ 比较 Rust 时说 borrower 可修改 Ray 对象，容易与论文 §1–2“所有共享对象不可变”相冲突。本文保留论文对象模型：actor 本地状态可变；不可变分布式对象不会因为成为 borrower 就可原地修改。该 FAQ 句子不能用来推翻模型；两种 ownership 的目的也确实不同，不能把 Ray 当成 Rust 借用检查器的分布式版。
3. **调度的时间范围：** FAQ 给本地优先、随机其他 scheduler 的概要并链接 latest 文档；这里没有读取当前产品文档，因此只将其作为本次课程快照说明，不据此断言今天 Ray 的完整默认调度政策。

其余 FAQ 说明了应用类别、actor 保温与批处理价值、lineage/持久日志的成本区别、非幂等副作用需应用协议、fate sharing 防止无限等待，以及分布式 tracing GC 面临失败与暂停成本。名字 Ray 没有特殊技术含义，是作者觉得合适的候选之一。

FAQ 的部署安全模型描述为一个 Ray deployment 服务一个应用，通过专用机器、VM 或容器与其他部署隔离，并非内部多租户隔离机制。它是该课程回答的范围，不据此外推现代托管服务的完整安全设计。FAQ 关于 OpenAI、Anyscale 与外部 GC 综述的链接也未在本任务独立核验。

## 引用与来源

- Stephanie Wang、Eric Liang、Edward Oakes、Ben Hindman、Frank Luan、Audrey Cheng、Ion Stoica，**Ownership: A Distributed Futures System for Fine-Grained Tasks**，NSDI 2021，[MIT 指定 PDF](https://pdos.csail.mit.edu/6.824/papers/ray.pdf)。第 1 页题名与作者已看；本 PDF 无首页会议年份横栏，内部文献 [53] 写作 “Ownership nsdi’21 artifact”，PDF 元数据 CreationDate/ModDate 为 `D:20210402112000-07'00'`，与 2026 讲义注明 NSDI 2021 相符。第 14 页文献 [34] 才是另一篇 OSDI 2018 Ray 论文。
- 全文读取 1–16 页，包括摘要、§1–7、致谢、56 条文献、附录 A–B。实际看页：1（Figure 1–2 与代码）、3（Table 1/Figure 3）、4（Figure 4–5）、5（Figure 6）、6（Table 2/Figure 7）、7（Figure 8 及 RTT 表）、8（Figure 9/API）、9（Figure 10–11）、10（Figure 12）、11（Figure 13–14）、12（Figure 15）、16（Table 3/附录公式）。其余页全文文字已读，不冒称另做图像核验。
- PDF、讲义复用 2026-11-08 抓取快照，分别保留原取得时间；服务器 Last-Modified 为 2026-01-27、2026-04-23，不代表论文发表年份或课堂录像日期。[讲义](https://pdos.csail.mit.edu/6.824/notes/l-ray.txt)内部题名 “6.5840 2026 Lecture 18: Ray”，223 行全文；[FAQ](https://pdos.csail.mit.edu/6.824/papers/ray-faq.txt) 105 行全文，2026-11-09 新抓取，Last-Modified 为 2026-04-22。无年份 URL 是动态入口，不能假定以后字节不变。
- MIT 6.5840 Spring 2026 [课表 L18，2026-04-23，fk](https://pdos.csail.mit.edu/6.824/schedule.html)，指定三项书面材料，无视频链接；课程自有文字按[首页](https://pdos.csail.mit.edu/6.824/index.html)声明的 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 改写并校注。该许可不覆盖外部论文的全文翻译。
- 本地获取 metadata、哈希和阅读/校注边界见 `sources/p9-ray/`；论文 artifact、现代 Ray 代码、FAQ 外链未读，未执行论文实验或课程实验。与 Spark 的比较依据已完成的 [L16 RDD 精读](#/c/mit-6.824-2021/lec/lec16?v=materials)，不是复用 Spark 阅读状态代替本论文阅读。
