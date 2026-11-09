---
source: MIT 6.5840 Spring 2026 Lab 4；2026-11-08 官方页快照；代码 513cac0aef010750fc74688da8a395974a83cf7a
license: MIT 课程网站 CC BY 3.0 US；官方要求中文翻译，终端样例缩写，接口差异另标编者注。
status: 完整阅读官方页及 A–C 全部任务和提示；固定骨架、RSM/KV 测试与恢复路径已静态核对。未实现答案，未运行实验测试。
---

# Lab 4：容错键值服务

## 1. 从复制日志到可用的服务

使用 Lab 3 的 Raft 库构建容错键值存储。客户端看到的服务类似 Lab 2，但背后是一组服务器，借助 Raft 维护相同的数据库。只要多数服务器存活且能相互通信，即使其他节点故障或发生网络分区，服务仍应继续处理可与该多数派通信的客户端请求。

完成后，你将实现官方交互图中的 Clerk、Service、Raft 三个部分。客户端仍通过 Clerk 的 `Put`、`Get` 访问服务，语义与 Lab 2 相同：Put 至多执行一次，Put/Get 的历史必须线性一致。

单服务器比较容易提供线性一致性；复制服务还要让所有副本为并发请求选择相同顺序，避免从过时状态回复，并在故障恢复后保留所有已向客户端确认的更新。

本实验分三部分，官方要求按各自截止日期提交：

| 阶段 | 任务 | 官方难度 |
|---|---|---|
| 4A | 用 Raft 实现不依赖具体请求类型的复制状态机包 `rsm` | 中等／困难 |
| 4B | 基于 `rsm` 实现复制 KV，暂不使用快照 | 中等 |
| 4C | 接入 Lab 3D 快照，使 Raft 可以丢弃旧日志 | 中等 |

复习扩展 Raft 论文，尤其是 §7；本实验不要求 §8 的优化。若希望拓宽视野，可以阅读 Chubby、Paxos Made Live、Spanner、ZooKeeper、Harp、Viewstamped Replication 和 Bolosky 等人的工作。尽早开始。

> **编者版本说明：** 这里是 Spring 2026 Lab 4，主题对应旧课的 KV/Raft 实验，但不是旧 `PutAppend` 接口。共用 Raft 论文统一见 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)。学习路线与服务层背景见 [RSM 接口桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)。环境与代码获取见[公共资料](#/c/mit-6.824-2021)；下文 `src/` 均指实验仓库。

## 2. 准备代码

骨架和测试在 `src/kvraft1`；服务器通过 `src/kvraft1/rsm` 复制状态。使用 RSM 的服务器必须实现 `StateMachine` 接口。主要工作是实现通用的 `rsm`，再在 `kvraft1/client.go`、`kvraft1/server.go` 中完成 KV 专有逻辑。这种分工让你在下一实验复用 RSM。

可以复制或导入 Lab 2 的实现复用部分逻辑，但这不是硬性要求。官方网页提示先在仓库根目录执行 `git pull`，获取最新代码。

> **编者固定版本说明：** 本路线统一使用提交 `513cac0aef010750fc74688da8a395974a83cf7a`，在自己的学习分支持续开发，不随网页示例更新提交。Go 导入路径以模块为准，例如 `6.5840/kvsrv1`；网页的 `src/kvsrv1` 是目录位置。

以下命令在实验仓库 `src/` 执行：

```bash
make rsm1
```

骨架尚未实现时，最初的 RSM 基本测试会失败。Makefile 先构建 `main/rsm1d` 或 `main/kvraft1d`，再运行相应包的 Go 测试，默认带 `-v -race`。

## 3. 4A：复制状态机

### 3.1 RSM 要连接的两条执行路径

使用 Raft 复制的服务有两种交互：leader 通过 `raft.Start()` 提交客户端操作；所有副本从 `applyCh` 收取已提交操作并执行。

在 leader 上，这两条路径必须会合：可能有许多处理客户端的 goroutine 已调用 `Start()`，正在等待各自的操作提交和执行结果；另一边，已提交操作不断从 `applyCh` 出现，服务需要执行它们，并把结果交给最初等待该操作的 goroutine。

`rsm` 封装这层交互，位于服务与 Raft 之间。你需要在 `rsm/rsm.go` 实现：

- 一个 reader goroutine，持续读取 `applyCh`；
- `Submit()`：调用 `raft.Start()`，等待 reader 交回该操作的执行结果。

reader 通过 `StateMachine` 接口访问服务。每个已提交操作交给 `DoOp()`，其返回值交回对应的 `Submit()`。参数和结果都使用 `any`，具体类型由服务决定；不能把 RSM 写成只认识 KV 请求的包。

固定骨架定义：

```go
type StateMachine interface {
    DoOp(any) any
    Snapshot() []byte
    Restore([]byte)
}

// Submit(req any) (rpc.Err, any)
```

服务应将每个客户端操作交给 `Submit()`。为便于把 apply 消息与等待者对应起来，`Submit()` 应把请求与唯一标识一起包进 `Op` 结构。必须等到该操作**提交且执行**后，才返回 `DoOp()` 的结果。

如果 `Start()` 表明当前节点不是 leader，`Submit()` 返回 `rpc.ErrWrongLeader`。还必须处理：刚调用完 `Start()` 就换主，导致该操作丢失、永远没有提交。

4A 的测试器充当服务：状态是一个整数，提交的操作主要是递增。4B 再由 KV 服务器实现 `StateMachine`、调用 `Submit()`。

正常请求的完整顺序是：

1. 客户端向服务 leader 发请求。
2. 服务 leader 调用 `rsm.Submit()`。
3. `Submit()` 调用 `raft.Start()`，随后等待。
4. Raft 提交请求，并在各副本的 `applyCh` 上交付。
5. 各副本的 reader 读取请求，调用服务的 `DoOp()`。
6. leader 上的 reader 把执行结果交给原来等待的 `Submit()`，由其返回。

### 3.2 任务与提示

**任务：实现 `rsm.go` 的 `Submit()` 和 reader goroutine，通过 RSM 的全部 4A 测试。**

```bash
make RUN="-run 4A" rsm1
```

测试包括 `TestBasic4A`、`TestConcurrent4A`、`TestLeaderFailure4A`、`TestLeaderPartition4A`、`TestRestartReplay4A`、`TestShutdown4A`、`TestRestartSubmit4A`。

官方提示：

- 应当不需要给 Raft 的 `ApplyMsg` 或 `AppendEntries` 等 RPC 添加字段，但允许这样做。
- 必须处理 leader 在 `Start()` 后、操作提交前失去领导权的情况。一种办法是发现 Raft 任期变化，或发现 `Start()` 返回的 index 上出现了不同请求，然后让 `Submit()` 返回 `rpc.ErrWrongLeader`。
- 若旧 leader 被单独隔离，它可能不知道新 leader 已产生；同处该分区的客户端也无法联系新 leader。这种情况下允许等待，直到分区恢复，不能靠本地自认 leader 就返回成功。

> **编者测试校注：** 固定 `TestLeaderPartition4A` 不仅禁止少数派成功执行 `Dec`，还检查这批等待调用在分区期间没有全部提前结束，恢复连接后能退出。因此不能把统一的短超时直接当作“请求没有提交”的证据。`TestShutdown4A` 注释仍提旧 `Kill()`，但本版实际通过独立进程模拟关闭；`raftapi.Raft` 没有 `Kill`，也没有 `CondInstallSnapshot`。

## 4. 4B：不使用快照的键值服务

每台 KV 服务器关联一个 RSM/Raft 实例。Clerk 向 Raft leader 对应的 KV 服务器发送 `Put`、`Get` RPC；KV 把操作提交给 RSM，由 Raft 复制，再在各副本调用 `DoOp()` 操作本地数据库，使副本按相同顺序维护数据库。

Clerk 不一定知道谁是 leader。联系了错误节点，或者无法联系该节点时，应换服务器重试。操作提交并应用后，leader 通过 RPC 回复执行结果；若操作未能提交，例如 leader 被替换，服务器返回错误，Clerk 到其他服务器重试。

### 4.1 先完成无故障路径

**任务：先在不丢消息、没有服务器故障的环境下工作。**

- 可将 Lab 2 的 `kvsrv1/client.go` 复制到 `kvraft1/client.go`，增加选择目标服务器的逻辑。
- 在 `server.go` 实现 `Put()`、`Get()` RPC handler，通过 `rsm.Submit()` 提交请求。
- 实现 `DoOp()`，供 RSM reader 消费已提交命令时调用。
- 稳定通过第一个测试才算完成这一步：

```bash
make RUN="-run TestBasic4B" kvraft1
```

官方提示：

- KV 服务器若不属于可推进的多数派，就不能完成 `Get()` 并返回旧数据。简单办法是把每个 Get 和 Put 都经 `Submit()` 写入 Raft 日志。不要求实现论文 §8 的只读优化。
- 从一开始就考虑加锁；避免死锁有时会影响整体设计。测试默认启用 race detector。

> **编者接口补充：** `Get(key)` 返回 `(value, version, err)`；`Put(key, value, version)` 仅在版本匹配时更新并递增版本。不存在的键可以用 version 0 创建，首次创建后的版本为 1；不存在且请求版本非 0 时返回 `ErrNoKey`，存在但版本不匹配时返回 `ErrVersion`。共用 RPC 类型在 `kvsrv1/rpc/rpc.go`，本提交没有 `kvraft1/common.go` 或 `PutAppend`。

### 4.2 再处理故障和重试

Clerk 可能需要多次发送 RPC 才能找到可回复的服务器。如果 leader 刚把操作提交就宕机，Clerk 可能收不到回复，随后向新 leader 重发。每次 `Clerk.Put()` 对指定版本号至多成功执行一次。

**任务：加入故障处理，采用类似 Lab 2 的重试策略，包括表达执行结果不确定的 `ErrMaybe`；稳定通过全部 4B 测试。**

```bash
make RUN="-run 4B" kvraft1
```

> **编者校注：** 官方此处写“重试 Put RPC 的回复丢失时返回 ErrMaybe”，措辞不够精确。固定 `kvraft1/client.go` 明确约定：首次 RPC 就收到 `ErrVersion`，返回 `ErrVersion`；重发后收到 `ErrVersion`，返回 `ErrMaybe`，因为先前请求可能已生效但回复丢失。RPC 失败本身应驱动重试，不能直接当成已知写入失败。`ErrMaybe` 是 Clerk 对应用表达的不确定性，不是 `DoOp()` 产生的服务器写入结果。

官方提示：

- RSM leader 可能失去领导权，`Submit()` 返回 `rpc.ErrWrongLeader`；此时让 Clerk 到其他服务器重发，直到找到新 leader。
- Clerk 最好记住最近成功 RPC 的 leader，下次先联系它，避免每次都从头寻找，否则某些测试可能太慢。

4B 测试覆盖基本读写、速度、多客户端、丢包、少数派不推进与多数派推进、反复分区、单／多客户端重启，以及重启、分区、丢包和随机键的组合。

官方成功样例中，`Passed` 后的数字依次是实际用时（秒）、副本数、RPC 数（含客户端 RPC）、执行的 KV 操作数（Clerk Get/Put 调用）。样例不是你的运行结果，也不要求统计值完全相同。

## 5. 4C：加入快照

没有快照时，重启服务器必须重放完整的持久化 Raft 日志来恢复状态。现在修改 KV 与 RSM，让它们与 Lab 3D 的 `Raft.Snapshot()` 协作，节省日志空间并缩短恢复时间。

### 5.1 RSM 负责何时截断

测试器把 `maxraftstate` 传给 `StartKVServer()`，再交给 RSM。该值限制的是持久化 Raft 状态的字节数，包含日志，**不包含应用快照**；具体是传给 `persister.Save()` 第一个参数的 GOB 编码字节。

RSM 应比较 `maxraftstate` 与 `rf.PersistBytes()`。当状态大小接近阈值时，调用 `StateMachine.Snapshot()` 取得服务状态，再交给 Raft 的 `Snapshot()`。`maxraftstate == -1` 时无需制作快照。

**任务：修改 RSM，检测持久 Raft 状态过大并交给 Raft 快照；重启时用 `persister.ReadSnapshot()` 读取快照，非空则恢复 `StateMachine`。通过 RSM 的 `TestSnapshot4C`。**

```bash
make RUN="-run 4C" rsm1
```

官方提示：

- 思考何时制作快照，以及除了服务器状态外，快照还需要包含哪些信息。
- Raft 使用 `Save()` 将快照和对应的 Raft 状态一同保存；`ReadSnapshot()` 可读取最近保存的快照。`Persister` 的源码在 `tester1/persister.go`。
- 快照中结构体的待编码字段必须首字母大写。

> **编者校注：** 官网这个任务写的是通过 **RSM** 的 `TestSnapshot4C`，但紧随的失败终端示例却运行 **KV** 的 `make RUN="-run 4C" kvraft1`。两者是不同测试入口，应分别运行。骨架 `rsm.go` 注释里的 `SaveStateAndSnapshot()` 是旧名；本提交实际只有 `Persister.Save(raftstate, snapshot)`。若 RSM 给服务快照加了自己的元数据封装，恢复时先拆封，再把服务字节交给 `Restore()`。

### 5.2 KV 负责保存什么，RSM 负责应用快照

**任务：实现 `kvraft1/server.go` 的 `Snapshot()`、`Restore()`，供 RSM 调用；修改 RSM，处理 `applyCh` 中包含快照的消息。**

```bash
make RUN="-run 4C" kvraft1
```

官方提示与完成条件：

- 这一阶段可能暴露 Raft 或 RSM 的问题。若修改 Raft，确保它仍通过 Lab 3 全部测试。
- Lab 4 全部测试的合理参考用时为实际时间 400 秒、CPU 时间 700 秒；这是官网参考，不是本页实测。
- 完成后应通过 4C、此前的 4A/4B，以及 Lab 3。

KV 的 4C 测试包括 `TestSnapshotRPC4C`、`TestSnapshotSize4C`、`TestSpeed4C`、`TestSnapshotRecover4C`、`TestSnapshotRecoverManyClients4C`、`TestSnapshotUnreliable4C`、`TestSnapshotUnreliableRecover4C`、`TestSnapshotUnreliableRecoverConcurrentPartition4C`、`TestSnapshotUnreliableRecoverConcurrentPartitionLinearizable4C`。

> **编者输出说明：** 官方成功样例含“linearizability check timed out, assuming history is ok”。固定检查器对 `Unknown` 打印该信息；这表示检查未在期限内得出结论，不是已经证明该段历史线性一致。

最终回归入口：

```bash
make rsm1
make kvraft1
make raft1
```

## 引用与许可

- MIT 6.5840 Spring 2026 课程团队，[Lab 4: Fault-tolerant Key/Value Service](https://pdos.csail.mit.edu/6.824/labs/lab-kvraft1.html)。本地 `sources/lab-kvraft-2026.html`，2026-11-08 抓取，Last-Modified 为 2026-04-11；正文、三部分任务和全部提示完整中译，终端重复输出压缩为入口、范围和说明。
- [课程首页](https://pdos.csail.mit.edu/6.824/index.html)链接 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。本页含中文翻译及明确标注的编者补充；代码接口核对不代表代码已实现或测试通过。
- 固定仓库 `git://g.csail.mit.edu/6.5840-golabs-2026`，提交 `513cac0aef010750fc74688da8a395974a83cf7a`。阅读范围、来源哈希与网页／代码差异见 `sources/p4-lab4/manifest-fragment.json`、`sources/p4-lab4/review.txt`。
- 共享 Raft 论文只见 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)。官方外链：[Raft 交互图](https://pdos.csail.mit.edu/6.824/figs/kvraft.pdf)、[Bolosky 等人的论文](http://static.usenix.org/event/nsdi11/tech/full_papers/Bolosky.pdf)、[协作约定](https://pdos.csail.mit.edu/6.824/labs/collab.html)、[提交](https://pdos.csail.mit.edu/6.824/labs/submit.html)、[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)、[调试建议](https://pdos.csail.mit.edu/6.824/labs/guidance.html)、[Piazza](https://piazza.com/mit/spring2026/65840)。这些外链不计入本次通读范围。
