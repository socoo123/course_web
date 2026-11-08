---
source: MIT 6.5840 Spring 2026，Lab 3 Raft；2026-11-08 官方页快照；代码 513cac0aef010750fc74688da8a395974a83cf7a
license: MIT 课程网站 CC BY 3.0 US；官方要求中文翻译，终端样例压缩，固定版本差异另标编者注。
status: 完整阅读官方正文、3A–3D 任务与提示；静态核对固定代码接口、测试和快照恢复路径。未实现答案，未运行实验测试。
---

# Lab 3：Raft

## 1. 目标：让多个副本按同一顺序执行

这是容错键值存储系列的第一步：实现 Raft 复制状态机协议。下一个实验在 Raft 上构建 KV 服务，再下一个实验把服务分片到多个复制组以提高性能。

复制服务把完整状态保存到多台服务器，从而容忍服务器崩溃及网络中断、丢包。难点是故障可能让副本持有不同的数据。

Raft 把客户端请求组织成有序日志，让副本按相同顺序执行相同的请求。宕机后恢复的服务器由 Raft 帮助追赶日志。只要多数服务器存活并能相互通信，系统就应能继续工作；无法形成可通信多数派时停止推进，通信恢复后再继续。

本实验把 Raft 实现为 Go 对象及其方法，供更大的服务调用。多个 Raft 实例通过 RPC 维护复制日志。日志项使用 index 编号；当 Raft 确认条目已经提交，就交给上层服务执行。

> **编者术语说明：** 上述目标不表示每次 `Start()` 接受的条目都一定会提交。尚未提交的条目可能因换主而被覆盖；接口承诺见下一节。

遵循扩展版 Raft 论文，尤其是 Figure 2。需要实现大部分协议，包括持久化和崩溃后的恢复；**不实现 §6 的成员变更**。实验分四部分，官方要求分别按对应截止日期提交。

> **编者版本说明：** 本页是 2026 Lab 3，主题对应 2021 Lab 2，但接口以固定提交为准。论文精读统一在 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)；环境与获取代码见[公共资料](#/c/mit-6.824-2021)。这里的 `src/` 均指实验仓库。

## 2. 骨架、运行入口和接口

实现入口是 `src/raft1/raft.go`，官方测试是 `src/raft1/raft_test.go`。做过 Lab 1 就已有同一仓库；否则先按公共资料取得代码。

官方步骤会先执行 `git pull` 获取课程更新，再进入 `src` 运行测试。本学习路线冻结代码提交，因此保持固定学习分支，使用以下入口：

```bash
# 当前目录：实验仓库 src/
make raft1
```

Makefile 先构建 `main/raft1d`，再进入 `raft1` 运行默认带 `-v -race` 的 Go 测试。骨架未实现时，初始选举测试会报告找不到 leader。官方评分不加 `-race`，但你应确保带 `-race` 时也能稳定通过。

### 2.1 上层如何使用 Raft

```text
rf := Make(peers, me, persister, applyCh)
rf.Start(command) -> (index, term, isLeader)
rf.GetState()     -> (term, isLeader)
```

- `peers` 是包含本节点在内的所有节点的 RPC 端点，`me` 是本节点在数组中的下标。
- `Start(command)` 请求把一条命令加入复制日志，必须立即返回，不能等复制完成。返回的 leader 标志表示本节点当时认为自己是 leader，不保证该命令最终提交。
- 每个节点确认新的日志项已提交后，通过构造时传入的 `applyCh` 发送 `ApplyMsg`，通知上层执行。
- `GetState()` 返回本节点当前任期以及是否自认为是 leader。

详细定义位于 `raft.go`、`raftapi/raftapi.go`。快照阶段还要实现 `Snapshot(index, snapshot)`，并保留骨架已有的 `PersistBytes()` 接口。

### 2.2 通信约束

骨架提供发送 `RequestVote` 的例子和对应 RPC handler。Raft 节点之间必须使用实验的 `labrpc` 通信。测试器会延迟、重排、丢弃 RPC，以模拟网络故障。

允许临时修改 `labrpc` 来调试，但最终必须在原版 `labrpc` 上正确运行，因为评分使用原版。**不能通过共享 Go 变量或文件在 Raft 节点之间通信。** 后续实验会依赖这份实现，应预留足够时间调试。

## 3. 3A：领导者选举

实现 leader election 和心跳，即不携带日志项的 `AppendEntries` RPC。目标是选出一个 leader；没有故障时保持稳定；leader 故障或与其他节点失联后，能选出新 leader。

```bash
make RUN="-run 3A" raft1
```

### 官方提示

1. 按 Figure 2 实现选举相关的状态、`RequestVote` 收发和服务器规则；选举逻辑分布在图中的多个区域，应合起来阅读。
2. 在 `Raft` 结构体里加入选举状态，补全 `RequestVoteArgs`、`RequestVoteReply`。
3. 修改 `Make()`，创建后台 goroutine；一段时间未收到相关节点通信时发起选举。实现 `RequestVote()` handler。
4. 定义 `AppendEntries` 参数并实现 handler；这一阶段可以暂不需要全部日志参数。leader 周期性发送心跳。
5. **心跳发送频率不得高于每秒 10 次。** 若多数节点仍能通信，应在旧 leader 故障后 **5 秒内**选出新 leader。
6. 论文的 150–300 ms 选举超时假设心跳明显更频繁；本实验限制心跳速率，需要更大的选举超时，但又不能大到妨碍 5 秒内完成重选。
7. 可以使用 `math/rand`。定期任务最容易通过 goroutine 循环加 `time.Sleep()` 实现，参照骨架 `ticker()`；官方建议不要使用较难正确处理的 `time.Timer`、`time.Ticker`。
8. 实现 `GetState()`。RPC 只传输首字母大写的结构体字段，嵌套结构和日志项字段也一样；不要忽略 `labgob` 的警告。
9. 调试可能是最困难的部分。失败时测试器生成带有分区、宕机、检查事件的时间线文件。还可以添加 `tester.Annotate("Server 0", "short description", "details")` 注解。

本阶段包含 `TestInitialElection3A`、`TestReElection3A`、`TestManyElections3A`，分别检查初次选举、网络故障后的重选、多轮选举。

官方说明把 `Passed` 后的统计解释为耗时、节点数、RPC 数、RPC 字节数、已提交日志项数；数值不要求与示例完全相同，可用于判断通信开销是否异常。

> **编者校注：** 当前网页样例行只展示 `time/#peers/#RPCs/#Ops` 四组数值，与文字所说的五项不完全一致。应按实际输出标签读数，不能硬按位置把 `#Ops` 当作字节数。

官方页面给出的 Lab 3/4/5 评分限制是总测试超过 600 秒或单个测试超过 120 秒会失败；评分时不加 `-race`。这些是页面中的评分说明，不是本站执行结果。

## 4. 3B：日志复制

实现 leader 和 follower 追加日志的代码，通过全部 3B 测试：

```bash
make RUN="-run 3B" raft1
```

### 官方提示

- 论文从 index 1 开始编号。可以在 Go 切片下标 0 放一个 term 为 0 的占位条目，使首次 `AppendEntries` 的 `PrevLogIndex=0` 能对应有效位置。
- 先以 `TestBasicAgree3B` 为目标：实现 `Start()`，按 Figure 2 经 `AppendEntries` 发送和接收日志，再由各节点通过 `applyCh` 交付新提交项。
- 必须实现论文 §5.4.1 的**选举限制**。
- 不要用不暂停的循环反复检查事件。使用条件变量，或者每轮加入类似 `time.Sleep(10 * time.Millisecond)` 的等待，避免忙等使测试过慢。
- 为后续实验维护清楚、整洁的代码。测试失败时从 `raft_test.go` 出发，跟踪测试到底要求什么。
- 官方此处也提醒 `git pull`；本路线继续使用冻结提交。

测试覆盖基本一致、RPC 字节数、follower/leader 故障、重连后追赶、失去多数派时不提交、并发 `Start()`、旧 leader 重返、冲突日志回退及 RPC 数量。具体测试名见[实验指导](#/c/mit-6.824-2021/lab/raft?v=guide)。

后续实验可能因实现太慢而失败。可以用系统 `time` 命令观察实际耗时与 CPU 时间。官方 3B 样例总耗时约 72 秒；它只是参考。若运行远超几分钟，检查睡眠和 RPC 等待时间、无等待的循环、过多 RPC；不是把样例时间当作必须复现的结果。

## 5. 3C：持久化

服务器重启后应从原来的状态继续服务，因此必须保存可跨重启恢复的 Raft 状态；哪些状态需要持久化见 Figure 2。

真实系统会把状态写到磁盘。本实验由传入 `Make()` 的 `Persister` 提供保存与恢复接口；你不直接操作磁盘。`tester1/persister.go` 的 `ReadRaftState()` 返回上次保存的状态，`Save()` 保存新状态。

完成 `persist()`、`readPersist()`：用 `labgob` 把状态编码成字节数组、解码恢复；每次修改持久状态时在适当位置调用 `persist()`。`labgob` 类似 Go 的 `gob`，但对无法编码的小写字段会给出警告。

在尚未实现快照的 3C 阶段，调用：

```text
persister.Save(raftstate, nil)
```

### 快速回退提示

可能需要让 `nextIndex` 一次回退多项。扩展论文第 7 页底到第 8 页顶部给出方向，细节需自己设计。官方建议失败回复可以携带：

| 字段 | 含义 |
|---|---|
| `XTerm` | 冲突条目的任期（若存在） |
| `XIndex` | 该任期第一条日志的索引（若存在） |
| `XLen` | follower 的日志长度 |

官方给出的处理提示是：leader 没有 `XTerm` 时回退到 `XIndex`；leader 有 `XTerm` 时回退到自己该任期最后一项的下一位置；follower 日志过短时使用 `XLen`。这是官方提示，不是完整的 RPC 实现；快照引入后还需自行明确这些量与绝对索引的关系。

3C 比前两部分更严苛，失败也可能来自原有的选举或复制逻辑。完成后必须同时通过 3A、3B、3C：

```bash
make RUN="-run 3C" raft1
```

测试包括三组持久化场景、Figure 8、丢包下的一致性、丢包与乱序下的 Figure 8，以及可靠／不可靠网络下的 churn。官方建议提交实现前多次运行测试；页面各处的拉取更新提醒仍按本路线固定版本处理。

## 6. 3D：日志压缩与快照

长期保留完整日志不现实，重启后重放全部历史也越来越慢。服务应周期性持久化状态快照，Raft 随后删除已由快照覆盖的旧日志，减少保存空间和恢复时间。

如果 follower 太落后，leader 可能已经删除它需要的日志；这时必须发送快照，再发送快照之后的日志。论文 §7 给出总体设计，你需要完成细节。

### 6.1 服务主动产生快照

Raft 必须提供：

```go
Snapshot(index int, snapshot []byte)
```

Lab 3D 中测试器周期性调用它；Lab 4 中由你编写的 KV 服务调用，快照中包含完整键值状态。**每个副本上的服务都可以调用，不限于 leader。** `index` 是快照已经反映的最高日志索引，包括该条目本身。Raft 应尽可能删除其覆盖的旧日志，并让其余代码支持只保存日志后缀。

### 6.2 把快照交给落后副本

实现论文中的 `InstallSnapshot` RPC，让 leader 帮助落后节点替换状态。需要考虑它与 Figure 2 的其他状态、规则如何协调。

follower 接收快照后，可以在 `applyCh` 上发送带快照的 `ApplyMsg`；`raftapi/raftapi.go` 已定义测试所需字段。快照只能让服务状态向前推进，不能使它倒退。

### 6.3 保存与重启约定

Raft 状态和对应快照都必须持久化，快照作为 `persister.Save()` 的第二个参数；还没有快照时该参数为 `nil`。

**重启时，由应用层读取已保存快照并恢复应用状态。** 随后收到的第一条 `ApplyMsg` 必须是以下之一：

- `SnapshotIndex` 大于刚恢复快照索引的新快照；
- `CommandIndex` 紧接刚恢复快照索引的普通命令。

完成 `Snapshot()`、`InstallSnapshot` 以及截断日志所需修改，通过所有 3D 和此前各阶段测试。

### 官方提示

1. 先让实现支持“日志从任意索引 X 开始存储”。初始 X=0，先保持 3B/3C 正常；再由 `Snapshot(index, snapshot)` 压缩日志并更新 X。做到这里应能通过第一个 3D 测试。
2. 第一个快照测试失败的常见原因是 follower 追赶太慢。
3. leader 不再持有所需日志时，改发 `InstallSnapshot`。
4. **一次 RPC 发送完整快照，不实现 Figure 13 的 `offset` 分块传输。**
5. 删除旧日志必须真正释放对旧条目的可达引用，让 Go GC 可以回收其内存。
6. 重启后的 `Persister` 同时持有 Raft 状态与服务快照。日志已经压缩时，每次 `Save()` 都必须携带当前快照；因此可以在 `Make()` 中用 `ReadSnapshot()` 读取并保留它。
7. 官方给出的全套 Lab 3 参考用时：不带 `-race` 约 6 分钟实际时间、1 分钟 CPU；带 `-race` 约 10 分钟实际时间、2 分钟 CPU。机器和调度会影响结果。

```bash
make RUN="-run 3D" raft1
# 最后回归整个 Lab 3
make raft1
```

本阶段包含基本压缩、断连补快照、丢包补快照、崩溃恢复、所有节点崩溃，以及重启后快照初始化。`TestSnapshotInit3D` 特别检查“重启 → 新写入 → 再次重启”是否丢失原有快照。

## 引用与许可

- MIT 6.5840 Spring 2026 课程团队，[Lab 3: Raft](https://pdos.csail.mit.edu/6.824/labs/lab-raft1.html)。本地快照 `sources/lab-raft-2026.html`，抓取于 2026-11-08，Last-Modified 为 2026-02-01。
- [课程首页](https://pdos.csail.mit.edu/6.824/index.html)链接 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。本页为官方正文、四项任务及提示的中文翻译；终端输出压缩为命令、测试范围和解释，编者版本提示与校注明确分开。
- 固定代码 `513cac0aef010750fc74688da8a395974a83cf7a`：`raft1/raft.go`、`raftapi/raftapi.go`、`tester1/persister.go`、`raft1/server.go`、`raft1/proxy.go`、`raft1/test.go`、`raft1/raft_test.go`、`main/raft1d.go`、`src/Makefile` 已静态阅读。审阅见 `sources/P3-REVIEW.txt`；没有执行测试。
- 官方公共入口：[协作约定](https://pdos.csail.mit.edu/6.824/labs/collab.html)、[提交](https://pdos.csail.mit.edu/6.824/labs/submit.html)、[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)、[调试建议](https://pdos.csail.mit.edu/6.824/labs/guidance.html)、[时间线示例](https://pdos.csail.mit.edu/6.824/labs/vis.html)。这些外链不计入本页完整阅读范围。
