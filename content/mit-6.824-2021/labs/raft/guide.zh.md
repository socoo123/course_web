---
source: MIT 6.5840 Spring 2026 Lab 3；固定提交 513cac0aef010750fc74688da8a395974a83cf7a；Raft extended Figure 2 与 §7 的阅读入口见 L5
license: 编者自主实验指导；官方要求译文与署名见实验说明。
status: 依据固定骨架、接口、完整 raft_test.go 和测试服务恢复路径静态整理；不提供完整实现，未运行实验测试。
---

# Lab 3 实验指导：把协议变成可检查的不变量

## 1. 动手前先分清四个事件

一次命令可能依次经历：**本地接受 → 副本保存 → 提交 → 应用**。`Start()` 只对应最前一步，成功返回的 index 不是服务成功响应的凭据。一个被隔离的旧 leader 仍可能自认为是 leader，接受命令却永远无法提交。

先读 [L5 笔记](#/c/mit-6.824-2021/lec/lec05?v=notes)、[L7 笔记](#/c/mit-6.824-2021/lec/lec07?v=notes)，对照 [L5 共用论文精读](#/c/mit-6.824-2021/lec/lec05?v=materials)。实验要求、频率和时限集中在[实验说明](#/c/mit-6.824-2021/lab/raft?v=zh)，下面只讲如何组织思考和排错。

## 2. 固定代码地图

所有路径相对实验仓库的 `src/`：

| 文件 | 阅读目的 |
|---|---|
| `raft1/raft.go` | 你的实现入口；已有构造、投票 RPC 范例、`persist/readPersist`、`ticker` |
| `raftapi/raftapi.go` | 上层依赖的四个方法与 `ApplyMsg` 字段 |
| `tester1/persister.go` | 原子保存状态与快照；读取会返回副本 |
| `raft1/server.go` | 测试用服务如何消费日志、制作快照、启动时恢复快照 |
| `raft1/test.go` | 如何找 leader、统计提交、检查各副本同一 index 的内容 |
| `raft1/raft_test.go` | 各阶段真实故障注入和检查条件 |
| `raft1/proxy.go`、`main/raft1d.go` | 测试器与独立服务器进程之间的桥接 |
| `Makefile` | `make raft1` 先构建 daemon，再运行测试 |

构造函数的真实签名为：

```go
func Make(peers []*labrpc.ClientEnd, me int,
    persister *tester.Persister, applyCh chan raftapi.ApplyMsg) raftapi.Raft
```

导入路径是 `6.5840/tester1`，其中包名为 `tester`。返回接口有 `Start`、`GetState`、`Snapshot`、`PersistBytes`；本版本没有要求你提供 `CondInstallSnapshot` 或旧教程中的 `Kill` 接口。节点终止由测试框架的进程机制处理，不能照抄别年骨架的生命周期假设。

### ApplyMsg 的两个分支

普通命令使用 `CommandValid/Command/CommandIndex`；快照使用 `SnapshotValid/Snapshot/SnapshotTerm/SnapshotIndex`。接口要求两种 Valid 标志**恰好一个为 true**。Raft 不负责解码 KV 状态；快照字节属于上层服务。

## 3. 先画状态表，再写并发代码

建议把变量按职责分组，并写清“谁能修改、在哪把锁下修改、修改后何时持久化”：

| 类别 | 要回答的问题 |
|---|---|
| 任期与投票 | 重启后是否还记得这一任期投给了谁？ |
| 日志与快照边界 | 每个绝对 index 对应哪个保留条目或快照边界？ |
| 提交与应用进度 | 哪些条目确定安全，哪些已经交给服务？ |
| leader 的复制进度 | 对每个 follower，哪些是猜测，哪些已得到确认？ |
| 定时与角色 | 哪类事件确实延长当前 leader 的有效联系时间？ |

锁保护的不是“某一行 Go 代码”，而是成组的不变量。RPC 等待、channel 阻塞跨越了外部调度，不应让它们长期占住协议状态锁。释放锁后再收到的回复，也不能直接应用到已经变化的角色或任期上。

调试日志至少能还原：节点、事件类型、请求任期、当前任期、角色、相关 index、提交／应用边界。先找到第一次违反不变量的事件，再看后面的连锁超时。

## 4. 3A：检查为什么能当选，而非只调超时

一轮选举需要不同节点的多数票。重复回复不是新的一票，上一轮的回复不是本轮证据；收到更高任期应重新审视当前角色。

写代码前用三节点手推：A 与 B 同时超时；A 收到 B 的拒票；C 的回复很晚才回来；与此同时 A 已观察到更高任期。你能说清哪些旧信息还能改变当前状态吗？

最常见的两类失败：

- **一直选不出来**：检查票是否按任期计数、随机等待是否真正打散竞争、是否被不该重置计时的过期消息反复拖延。
- **无故频繁换主**：检查心跳发送间隔、后台循环是否被 RPC 阻塞、锁竞争是否让有效心跳处理延迟。

`RaftElectionTimeout=1000ms` 是测试里的等待常量，不是直接给你的实现指定选举超时。骨架 `ticker()` 的随机 sleep 也只是检查循环示例，不是完整选举定时协议。

## 5. 3B：把三种边界分开

### 5.1 匹配前缀不等于复制整条日志

`AppendEntries` 用前一条日志的位置和任期验证连接点。先确认连接点，再处理新条目；只有实际出现冲突才考虑删除冲突后缀。一个迟到、内容较短但与前缀一致的 RPC，不应无条件把较新的尾部截掉。

心跳也是 `AppendEntries`，不能因为 entries 为空就忽略协议要求的前缀检查。

### 5.2 nextIndex 不等于 matchIndex

前者指导下一次尝试从哪里发送，后者表示已被确认匹配到哪里。失败回退改变发送尝试；成功证据才支持推进确认范围。乱序回复到达时，先判断回复属于哪个请求与任期，避免旧失败覆盖新成功。

### 5.3 多数份数不等于任意旧项都能直接提交

leader 直接以多数复制推进提交时还要满足当前任期条件。旧任期条目如何随当前任期条目的提交一起确定，见论文 §5.4.2 精读。把这个限制遗漏，往往在 Figure 8 或重连测试才暴露。

交付给上层的普通日志应按顺序前进；服务消费慢时，不能阻塞其他节点的心跳和选举处理。

## 6. 3C：持久化的是协议承诺

不要把 `persist()` 当作“每隔一段时间备份”。考虑：节点对外宣布投票成功，随后立即崩溃；重启后如果忘记这次投票，会不会又投给另一个候选人？日志追加成功的回复也应作类似推理。

对每种改变持久状态的事件写下三个动作的先后关系：**修改状态、保存状态、对外确认**。再从恢复入口走一遍，确认后台任务启动时看见的是恢复后的状态。

本版只有 `Persister.Save(raftstate, snapshot)`，不是旧资料中的 `SaveRaftState` 或 `SaveStateAndSnapshot`。`Save()` 会同时替换两份数据；到了 3D，仍把第二个参数传 `nil` 会清掉已有快照。

快速回退能减少冲突后缀造成的 RPC 往返。官方提示集中在实验说明；先约定每个字段代表绝对索引、任期首项还是长度，再写分支。网络延迟大时，少量错误的退步就可能变成长时间超时。

## 7. 3D：快照是日志前缀的另一种表示

### 7.1 先改索引模型

快照覆盖到索引 S 后，逻辑日志编号继续增长，不能把下一个命令编号重置为 1。程序需要知道 S 及其对应任期，才能让后续日志继续接受前缀检查。

先让所有访问路径使用同一种索引换算，再压缩：`Start` 分配位置、选举时比较最后一项、发送复制请求、检查连接点、推进提交、应用日志都受影响。不要靠每处临时加减一个数补洞。

### 7.2 三条快照路径

| 路径 | 进入点 | 应思考的边界 |
|---|---|---|
| 本节点服务已应用后压缩 | `Snapshot(index, bytes)` | 不能让服务回到过去；可释放哪些旧条目？ |
| leader 帮落后 follower 追赶 | `InstallSnapshot` RPC | 快照是否更新？与随后命令交付的顺序如何协调？ |
| 故障后重新启动 | `Make()` 与上层服务初始化 | 恢复的快照和 Raft 元数据是否来自同一次原子保存？ |

如果接收的新快照与本地某个日志位置及任期匹配，是否能保留其后缀？不匹配时凭什么信任原后缀？用这个问题检查自己对“快照取代前缀”的理解，而不是把所有情况都写成清空日志。

### 7.3 本版本的恢复契约

`raft1/server.go` 在调用 Raft 构造前取得初始快照副本，随后由服务自己恢复 `lastApplied` 和应用日志。Raft 不应再把同一旧快照当作新的状态交付。第一条普通命令必须紧接恢复边界，或者先交付更靠后的快照。

`SnapshotValid` 与普通命令不能分别由毫无协调的发送路径任意穿插，否则可能出现“刚装好索引 100 的快照，又应用索引 90 的命令”。这里要维护的是应用层整体顺序，不只是 Raft 内部两个整数单调增长。

### 7.4 最容易漏掉的二次重启

`TestSnapshotInit3D` 的结构是：产生快照 → 全部重启 → 提交一条新命令 → 再全部重启 → 再提交。它专门暴露“第一次恢复看似成功，但后续 `Save()` 把快照丢了”的实现。

`TestSnapshotBasic3D` 主动让 follower 追赶完成，不要求靠安装远程快照才能通过；先用它检查本地压缩与索引。测试中的 `MAXLOGSIZE=2000` 是持久 Raft 状态的检查阈值，不是给应用快照规定 2000 字节上限。

## 8. 分阶段测试地图

以下命令全部在实验仓库 `src/`，是供你实现后执行的入口：

| 阶段 | 命令 | 失败时优先定位 |
|---|---|---|
| 3A | `make RUN="-run 3A" raft1` | `InitialElection/ReElection/ManyElections`：角色、任期、投票与超时 |
| 3B | `make RUN="-run 3B" raft1` | `BasicAgree/RPCBytes/FollowerFailure/LeaderFailure/FailAgree/FailNoAgree/ConcurrentStarts/Rejoin/Backup/Count`：复制、提交及通信开销 |
| 3C | `make RUN="-run 3C" raft1` | `Persist1/2/3`、`Figure8`、`UnreliableAgree`、`Figure8Unreliable`、`ReliableChurn/UnreliableChurn`：崩溃与换主组合 |
| 3D | `make RUN="-run 3D" raft1` | `SnapshotBasic/Install/InstallUnreliable/InstallCrash/InstallUnCrash/AllCrash/Init`：压缩、传输与恢复 |
| 回归 | `make raft1` | 四阶段同时成立，默认含 race detector |

表中测试名省略 `Test` 和阶段后缀。例如定点排查可执行 `make RUN="-run '^TestSnapshotInit3D$'" raft1`。随后回归受影响的阶段和全套；不能仅因某个快照测试通过就认定此前所有性质仍然成立。

测试器 `checkOneLeader()` 按任期分组检查同任期多 leader，选择已连接节点中最高任期的 leader；它不要求被隔离的旧 leader 瞬间知道自己过期。`CheckLogs` 检查同一 index 上已交付命令的一致性，服务侧检查交付顺序。理解测试的观察点，才能分辨协议问题和对测试的误读。

## 9. 交给 Lab 4 之前的自问

<details><summary>Start 返回 true 后宕机，服务能直接回复成功吗？</summary>

不能。Raft 可能尚未取得提交证据，服务也可能尚未执行命令。Lab 4 的 RSM 层要把请求提交与对应应用结果联系起来。
</details>

<details><summary>快照字节已保存，为什么还要一起保存日志边界和任期？</summary>

否则恢复后无法确定快照取代了哪些日志，也无法继续做正确的前缀匹配。同一快照与不相容的 Raft 状态拼接，不能形成合法的恢复点。
</details>

<details><summary>所有测试一次通过，是否已经证明协议正确？</summary>

没有。测试检查有限故障交错；仍应能解释 Figure 2 的规则如何落实到状态转移，并按官方建议用 race detector 和适当重复运行检查不稳定故障。教程的静态阅读本身更不是测试通过。
</details>

## 引用与来源

- MIT 6.5840 Spring 2026，[Lab 3](https://pdos.csail.mit.edu/6.824/labs/lab-raft1.html)，2026-11-08 快照；官方要求完整中译见实验说明。
- 官方仓库 `git://g.csail.mit.edu/6.5840-golabs-2026`，固定提交 `513cac0aef010750fc74688da8a395974a83cf7a`。上述代码地图中的文件均完整静态阅读；`raft_test.go` 共 1353 行，`server.go` 235 行，`test.go` 432 行。框架其余内部实现未计为通读。
- Diego Ongaro、John Ousterhout，*In Search of an Understandable Consensus Algorithm (Extended Version)*；论文正文集中在 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)。这里的并发组织和调试顺序为编者建议，不是额外评分要求。
- 来源与接口审阅记录 `sources/P3-REVIEW.txt`。没有修改或执行实验代码，不提供完整答案。
