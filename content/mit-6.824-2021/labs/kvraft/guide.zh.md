---
source: MIT 6.5840 Spring 2026 Lab 4；固定提交 513cac0aef010750fc74688da8a395974a83cf7a
license: 编者自主实验指导；官方要求译文与署名见实验说明。
status: 完整静态阅读 RSM/KV 骨架与测试、共用 RPC 和测试模型；定点复核 P3 恢复契约。未运行实验测试，不提供完整答案。
---

# Lab 4 实验指导：把提交、执行与回复接起来

## 1. 先把一条请求走通

先在纸上写出调用路径，再决定结构体和锁：

```text
Clerk.Get/Put
  → KVServer.Get/Put
  → RSM.Submit → Raft.Start
  → 已提交的 ApplyMsg → reader → KVServer.DoOp
  → 对应 Submit 的结果 → RPC 回复 → Clerk
```

读写都走这条路径。`GetState()` 的 leader 标志和 `Start()` 的成功接受都不是提交证据，更不能直接授权读取本地数据库返回。基本原理见 [RSM 接口桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)；全部任务见[实验说明](#/c/mit-6.824-2021/lab/kvraft?v=zh)。这里专注实现边界和排错。

4A 先用官方整数状态机隔离 RSM 问题；4B 接入版本化 KV；4C 再让日志前缀被快照取代。不要同时改三层后只看最终错误。

## 2. 固定接口地图

路径相对实验仓库 `src/`：

| 文件 | 动手前要确认的契约 |
|---|---|
| `kvraft1/rsm/rsm.go` | `Op`、`RSM`、`MakeRSM`、`Submit`，以及三方法 `StateMachine` |
| `raftapi/raftapi.go` | `Start/GetState/Snapshot/PersistBytes`；命令和快照两种 `ApplyMsg` |
| `kvraft1/server.go` | RPC handler 负责提交和回填回复；`DoOp` 执行业务；`Snapshot/Restore` 编解码状态 |
| `kvraft1/client.go` | `servers`、最近成功的 `leader`；寻找 leader 与版本化重试 |
| `kvsrv1/rpc/rpc.go` | 共用 Get/Put 参数和回复；这里承担旧资料中所谓 common 的职责 |
| `kvraft1/rsm/server.go`、`rsm_test.go`、`test.go`、`proxy.go` | 整数状态机、并发／分区／重启检查、跨进程调用 |
| `kvraft1/kvraft_test.go`、`test.go` | KV 测试及服务器启动配置 |
| `kvtest1/kvtest.go`、`porcupine.go`、`models1/kv.go` | 版本和数值断言、历史记录、线性一致性检查的实际范围 |
| `tester1/persister.go`、`raft1/server.go` | 原子保存；P3 服务的初始快照恢复顺序 |
| `Makefile`、`main/rsm1d.go`、`main/kvraft1d.go` | 先构建 daemon，再运行测试 |

关键签名：

```go
// 包 rsm
MakeRSM(servers []*labrpc.ClientEnd, me int,
    persister *tester.Persister, maxraftstate int, sm StateMachine) *RSM
Submit(req any) (rpc.Err, any)

// StateMachine
DoOp(any) any
Snapshot() []byte
Restore([]byte)

// Clerk
Get(key string) (string, rpc.Tversion, rpc.Err)
Put(key string, value string, version rpc.Tversion) rpc.Err
```

以上是签名摘录，不是可直接编译的实现。`StartKVServer(..., maxraftstate)` 把阈值交给 `MakeRSM`，并返回 `[]any{kv, kv.rsm.Raft()}` 供框架注册。构造函数必须尽快返回；先准备服务数据，再让后台 reader 有机会调用 `DoOp/Restore`。

`Submit` 的第一个返回值表示 RSM 是否拿到了对应执行结果；第二个是业务结果。例如 `Submit` 成功取得一次 Put 的 `PutReply{Err: ErrVersion}`，这是**RSM 正常完成、业务条件不满足**，不要把两层错误混成一次寻找 leader 的失败。

骨架已注册 `rsm.Op`、`rpc.PutArgs`、`rpc.GetArgs`。若添加通过 `any` 编码传输的新类型，需要按使用位置注册，待编码字段首字母大写；同时明确 `DoOp` 收到的是值还是指针、返回的具体类型是什么。

## 3. 4A：请求身份与日志位置是两回事

### 3.1 先回答“这个结果属于谁”

| 信息 | 用途 | 不能代替什么 |
|---|---|---|
| 请求唯一标识 | 把一次 Submit 与它的 apply 结果匹配 | 不能仅以同样的业务参数判断身份 |
| 日志 index | 请求被接受时的候选位置；观察该位置后来提交了谁 | 不是永久属于该请求的编号 |
| Start 返回的 term | 识别等待期间是否发生任期变化 | 不是已提交标记 |
| 键的 version | KV 条件更新和至多一次生效 | 不是 Raft term，也不是 RSM 等待者 ID |

两个客户端可以提交相同的 Get，整数测试也会重复提交相同的 `Inc{}`；不能靠请求内容区分等待者。反过来，同一 index 在旧条目未提交时可能被新 leader 的另一请求占据。

请求身份还要跨服务器、跨重启区分。只用“本地计数从零开始”会让重放的旧操作撞上新等待者。你可以选择能区分启动代际的身份设计，或论证其他设计为何不会误匹配；不要求维护一个无限增长的已完成请求表。

**RSM 的匹配 ID 不等于 KV 的客户端去重协议。** 同一个 Clerk Put 重试可能产生不同的 RSM 提交；本版通过 key/version 的条件更新限制业务效果，不必套用旧 PutAppend 教程的完整客户端序列号表。

### 3.2 Start 返回之后，还有两个独立事件

`Start(op)` 返回 `(index, term, true)` 仅表示本机当时认为自己是 leader 并接受了提议。正常成功返回 `Submit` 的依据应是：reader 收到**身份匹配**的已提交操作，调用 `DoOp()`，得到该次执行结果。

所有副本都执行已提交操作，即使自己没有 waiter、不是 leader、或者该操作属于重启前。不能因为“无人等待”就跳过 `DoOp()`，否则 follower 和恢复节点会丢状态。

但没有 waiter 不等于必须缓存每一个历史结果。区分“要对状态机执行”与“要通知本地调用者”，并给等待记录规定明确的创建、完成、失效和删除时机。

### 3.3 最容易漏掉的 apply／waiter 竞态

手推以下交错：

1. Submit 调用 Start，Raft 很快完成复制。
2. reader 已收到并执行该操作。
3. Submit 才把等待记录放入 map。

如果第二步丢掉结果，第三步就永远等不到。设计时要证明：**登记等待关系与接收结果之间没有丢通知窗口**。可以从预先登记身份、协调登记和 reader 的同步边界等方向思考，但别通过让 reader 长时间阻塞来“解决”竞态。

再反向手推：waiter 已退出，reader 此时才准备通知。通知不能永久堵住唯一 reader，也不能向已经关闭的 channel 发送。等待记录的清理应只针对自己的身份，防止旧调用误删新记录。

尤其避免 handler 持有 KV 锁等待 Submit，而 reader 必须拿同一锁调用 DoOp；这是完整闭环死锁。把锁顺序写清，区分等待者映射、业务状态和 Raft 内部状态，不要长期持锁跨越 RPC 或等待结果。

## 4. 旧 leader：失去回复资格不等于证明没执行

有三种需要分别处理的观察：

- Start 立即报告非 leader：本次提议没有在这里被接受，向上报告 `ErrWrongLeader`。
- 已接受后看到任期／角色变化，或者该 index 提交了别人的请求：不能把别人的结果回复给自己的 waiter；按等待失效路径让客户端寻找新 leader。
- 旧 leader 被隔离，既没有 apply，也没有看到新任期：没有证据完成操作，允许等待分区恢复。

“任期变了”并不普遍证明旧请求从未执行：它可能已提交但结果通知较晚。`ErrWrongLeader` 是重试路由信号，不是对业务效果的否定证明。Clerk 在重发过程中仍必须保留原来的 key/value/version 和必要的不确定性信息。

固定 `TestLeaderPartition4A` 向旧 leader 并发提交 100 个 Dec：任一调用返回 OK 都失败；即使全部以非 OK 结束，只要这批调用在 1 秒观察窗内全部退出，也失败；恢复连接后又要求这批调用在 1 秒内结束。只看“超过若干毫秒”就统一返回，可能违反这份测试的等待行为；时间应帮助检查真实状态，不能替代提交或失效证据。

### 关闭测试怎么读

`TestShutdown4A` 注释提到 `raft.Kill()` 关闭 `applyCh`，这是残留注释。实际调用链是测试组关闭服务器、保存 Persister checkpoint、终止 daemon 进程；测试侧代理调用随之失败或结束。`raftapi.Raft` 无 `Kill`，不应为这条注释照搬旧版关闭协议。`TestRestartSubmit4A` 则提醒你检查恢复后请求身份与旧日志的混淆问题。

## 5. 4B：业务状态只在 DoOp 中决定

handler 负责提交请求、区分 RSM 错误与业务回复；`DoOp` 根据已排序的请求和当前数据库决定结果。不要在 handler 里先修改 map，再把操作交给 Raft；失败提议会留下未复制的状态。

业务状态至少要保存每个键的 **value 和 version**。条件更新必须作为一次状态机操作判断并生效：检查版本和写值之间不能插入另一个已提交操作。

Clerk 的操作路径可先写成这张决策表：

| 观察到的结果 | 下一步思考 |
|---|---|
| RPC 不可达／无回复 | 结果可能不明；保持请求参数，换节点重试 |
| `ErrWrongLeader` | 换节点；保留此前尝试可能已执行的信息 |
| Get 的 `OK`／`ErrNoKey` | 返回对应业务结果 |
| Put 的 `OK` | 返回成功 |
| Put 首次 RPC 返回 `ErrVersion` | 本次调用未生效，返回版本冲突 |
| Put 重发后返回 `ErrVersion` | 按固定 Clerk 契约返回 `ErrMaybe` |

网页的“重试回复丢失时 ErrMaybe”与骨架的精确描述不同，见实验说明校注。`ErrMaybe` 只属于 Clerk；不要把 RPC 失败当成服务器已经返回 ErrMaybe，也不要在 Clerk 内自动提高 version 来“帮助重试”，那会变成新的业务写入。

`Clerk.leader` 是性能缓存，不是权威；成功响应后更新，之后先尝试它，失效再换。`TestSpeed4B/4C` 对 1000 次串行 Put 计时，要求平均不超过约 **33.3 ms/op**：测试固定以 100 ms 除以 3 作为门槛，不是按你实现的心跳间隔计算。若基础测试正常而速度失败，检查是否每次都遍历服务器、是否只等下一轮心跳才复制、以及不必要的固定 sleep。

## 6. 4C：快照字节必须对应一个确定的应用边界

### 6.1 三层各管一件事

| 层 | 职责 |
|---|---|
| KV | `Snapshot()` 编码 value/version 等业务状态；`Restore()` 用快照替换状态 |
| RSM | 跟踪已应用边界、判断阈值、取得一致状态、协调恢复与后续 apply |
| Raft | 把快照关联到日志 index，裁剪日志并与 Raft 元数据原子保存；给落后节点传快照 |

`rf.PersistBytes()` 衡量的是 `Save` 第一个参数，不是 map 大小、日志条数或快照大小。`maxraftstate=-1` 时不制作快照；固定 KV 通用测试也会检查这时快照大小为零。

### 6.2 本地制作：状态和 S 必须来自同一时刻

设已应用到 S，则提交给 `rf.Snapshot(S, bytes)` 的字节必须反映**恰好到 S 的状态**。如果读出 S 后 reader 又执行两条命令，最后编码到 S+2 的数据库，却仍标为 S，恢复后会重复应用那两条。

先决定如何串行化 `DoOp`、`Snapshot`、`Restore`，再设计编码。官方整数状态机的 Snapshot/Restore 没有给所有访问自行加锁，更说明 RSM 不能随意并发调用这些方法。

服务接口 `Snapshot() []byte` 不接收 index，`Restore([]byte)` 也不返回 index。因此如果 RSM 恢复后需要知道自己的已应用边界，可在外层快照封装中保存 S，再携带不透明的服务字节；不要假设 Raft 会替你解释 KV 编码，或者 `ReadSnapshot()` 会额外返回 index。

要保存业务恢复必需的信息和你设计的必要 RSM 元数据，不要保存 goroutine、channel、waiter 或无限请求历史。`TestSnapshotSize4C` 对“反复覆写一个键”的快照设 500 字节上限；它针对该小状态场景，不是任意数据库的统一容量限制。

### 6.3 启动恢复：承接 P3，而非重新定义 Raft

沿用 [Lab 3 指导的恢复契约](#/c/mit-6.824-2021/lab/raft?v=guide)：

1. 在启动可能改写 Persister 的 Raft 后台逻辑前，取得初始快照的稳定副本；P3 的 `raft1/server.go` 就这样做。
2. 非空时恢复 RSM 必需元数据，并把服务部分交给 `sm.Restore()`；准备好完整状态后再消费 apply。
3. Raft 接下来交付的第一条消息，只能是更靠后的快照，或紧接恢复边界的命令。不能再应用被旧快照覆盖的命令。

空快照表示从初始业务状态开始，不要用无法解码的空字节调用业务 Restore。4B 没有快照，依靠持久日志重放；4C 是快照恢复加后缀重放，不能两种路径各执行一遍完整历史。

`Persister.Save(raftstate, snapshot)` 原子替换两份数据。已有快照后仍传 `nil` 会把它清掉；Raft 重启后也必须保留当前快照，供之后每次持久化使用。P3 的 `TestSnapshotInit3D` 专门覆盖“恢复 → 新提交 → 再次恢复”，一次重启看起来正常还不够说明这一契约成立。

### 6.4 远程安装：先恢复，再接后缀

`ApplyMsg` 恰好一个 `CommandValid` 或 `SnapshotValid` 为真。快照消息走恢复路径，不是 `DoOp` 的另一种业务请求。安装 S 后，后续普通命令应从 S 后继续；旧快照或旧命令不能让状态倒退，也不能重复生效。

RSM 还要检查被该快照跨过的等待记录：快照说明状态已包含某个前缀，并不自动提供每个请求的原始执行结果。不要仅凭 `waiter.index <= S` 就回复成功；沿用身份、结果和领导权证据来处理等待者。

本版没有 `CondInstallSnapshot`；旧教程把应用层判断藏在这个调用里，不能原样移植。消息交付顺序由 Lab 3 的 Raft 契约保证，RSM 恢复与应用也要遵守同一条单调边界。

## 7. 测试驱动的排错顺序

以下是给学习者实现后运行的命令，本次内容制作没有运行它们。当前目录为实验仓库 `src/`。

| 步骤 | 命令 | 首先检查 |
|---|---|---|
| RSM 基本链路 | `make RUN="-run '^TestBasic4A$'" rsm1` | 全副本执行、结果交给正确 waiter |
| RSM 并发和故障 | `make RUN="-run 4A" rsm1` | 丢通知、身份碰撞、分区等待、恢复重放 |
| KV 无故障链路 | `make RUN="-run '^TestBasic4B$'" kvraft1` | 版本、具体类型、两层错误 |
| KV 全故障组合 | `make RUN="-run 4B" kvraft1` | leader 缓存、原参数重试、Get 也经日志 |
| RSM 快照 | `make RUN="-run 4C" rsm1` | 阈值、S 与字节一致、启动 Restore |
| KV 快照 | `make RUN="-run 4C" kvraft1` | value/version 恢复、远程补快照、快照空间 |
| 完成回归 | `make rsm1`、`make kvraft1`、`make raft1` | 4A–C 与 3A–D 同时成立 |

RSM 的 `TestSnapshot4C` 检查日志不超过 `2*maxraftstate`，KV 部分测试使用 `8*maxraftstate` 容差；这是检查时刻的余量，不是建议等到八倍才触发压缩。`TestSnapshotRPC4C` 先隔离一个节点，让多数派裁剪日志，再改变分区，强迫落后节点参与新的多数派，检查远程快照追赶。

调试记录建议至少包含：节点／启动代际、请求身份、Start index/term、apply index、操作类型、业务 version、waiter 完成原因、快照边界和持久状态字节数。先找第一条配错结果或越过边界的记录，别只追最后一个超时。

测试器也有观察边界：`models1/kv.go` 的 Get 步骤只比较 Value，其他测试才会显式比较 Version；Porcupine 超时会报告 `Unknown`。通过某一条检查不能替代接口语义，尤其不要把输出中的“assuming history is ok”理解成完整证明。

## 引用与来源

- MIT 6.5840 Spring 2026，[Lab 4](https://pdos.csail.mit.edu/6.824/labs/lab-kvraft1.html)，2026-11-08 快照；官方任务和全部提示译文见[实验说明](#/c/mit-6.824-2021/lab/kvraft?v=zh)。
- 固定仓库 `git://g.csail.mit.edu/6.5840-golabs-2026`，提交 `513cac0aef010750fc74688da8a395974a83cf7a`；实际完整阅读文件与定点范围逐项登记于 `sources/p4-lab4/manifest-fragment.json`、`sources/p4-lab4/review.txt`。不存在 `kvraft1/common.go`，共用协议定义是 `kvsrv1/rpc/rpc.go`。
- Raft 共用论文只链接 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)；服务背景只链接 [RSM 接口桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)。本页的排错路径、状态表和并发思考为编者建议，不是新增评分要求。
- 未修改、编译或运行实验代码；源码是未完成的官方 starter，不是参考解答。
