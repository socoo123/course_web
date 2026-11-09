---
source: MIT 6.5840 Spring 2026 Lab 5；固定提交 513cac0aef010750fc74688da8a395974a83cf7a
license: 编者自主实验指导；官方要求译文与署名见实验说明。
status: 静态通读 shardctrler、shardgrp、shardrpc、两层 Clerk、shardcfg、Lab 5 测试及关联接口；未运行实验，不提供完整答案。
---

# Lab 5 实验指导：移动数据，也移动服务权

## 1. 先把“数据在哪里”和“谁能服务”分开

迁移不是把一个 map 复制到另一个组就结束。复制期间可以存在两份数据，但它们不能同时作为权威回答请求。先为每个分片回答：

1. 哪个组现在有权执行 Get/Put？
2. 拷贝出来的状态包含哪些已经完成的写入？
3. 重复、迟到的管理 RPC 能否让旧组重新获得服务权？
4. 控制器在任一步失联后，另一控制器凭什么知道要继续做什么？

概念推导集中在[实验接口桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)；完整官方任务见[实验说明](#/c/mit-6.824-2021/lab/shardkv?v=zh)。这里把问题落实到固定接口和测试观察点。

默认架构的两条路径：

```text
数据请求：应用 → shardkv Clerk → shardgrp Clerk → 组内 RSM → Raft → DoOp
配置管理：ShardCtrler → Lab 2 配置 KV；ShardCtrler → 各组的迁移 RPC
```

分片组复制不等于配置存储也复制。`MakeShardCtrler` 使用 `kvsrv.MakeClerk` 指向 group 0 的单个服务器；将它改为复制 KV 是 5D 的方向之一。

## 2. 固定代码地图与接口

以下路径相对实验仓库 `src/`：

| 文件 | 读的时候先找什么 |
|---|---|
| `shardkv1/shardctrler/shardctrler.go` | 配置持久于控制器对象之外的 KV；四个方法与构造行为 |
| `shardkv1/client.go` | `sck`、`rcks`、`GetClerk`；配置路由与跨组重试 |
| `shardkv1/shardgrp/client.go` | 组内 leader 缓存与五类操作 |
| `shardkv1/shardgrp/server.go` | 五个 handler、`DoOp/Snapshot/Restore`、组号与初始化 |
| `shardkv1/shardgrp/shardrpc/shardrpc.go` | 迁移 RPC 字段、`FreezeShardReply.Num` |
| `shardkv1/shardcfg/shardcfg.go` | 12 个分片、FNV-1a `Key2Shard`、配置深拷贝及重平衡工具 |
| `shardkv1/test.go`、`shardkv_test.go` | 谁创建组、谁提议配置、谁隔离控制器、何时检查完成 |
| `kvsrv1/rpc/rpc.go`、`kvsrv1/client.go`、`kvraft1/client.go` | 版本化 Put、ErrMaybe 与组内重试基础 |
| `kvtest1/kvtest.go`、`porcupine.go`、`models1/kv.go` | 版本检查、工作负载及历史检查的边界 |
| `Makefile`、`main/kvsrv1d.go`、`main/shardgrp1d.go` | 构建与进程入口 |

### 2.1 控制器不是旧版 shardmaster

```go
// 签名摘录，不是实现
InitConfig(cfg *shardcfg.ShardConfig)
Query() *shardcfg.ShardConfig
ChangeConfigTo(new *shardcfg.ShardConfig)
InitController()
```

`Query()` 没有历史配置号参数，返回当前配置；`ChangeConfigTo` 没有成功布尔值。并发竞争失败的候选可以不执行自己的变更而返回，测试器会再次查询实际配置。

`ShardConfig` 已提供 `Num`、`Shards [NShards]tester.Tgid`、`Groups map[tester.Tgid][]string`。`Copy()` 深拷贝服务器列表；`JoinBalance/LeaveBalance` 改变配置、增加 Num 并重新平衡。**这些是配置对象的本地方法，不是要求你实现的 Join/Leave/Move 控制器 RPC。**测试器已负责构造候选；你的核心任务是安全落实候选。

`Key2Shard()` 使用固定哈希，不能改成按首字母或自己选择分片数。初始 Num 为 1，`Gid1` 首次启动拥有全部分片；其他新组不能自动把所有空 map 当成自己负责的分片。

### 2.2 两种 Clerk 各守一层边界

两层都向上支持 `Get(key) (value, version, err)`、`Put(key, value, version) err`：

- 系统 Clerk 根据 `Key2Shard → Query → GidServers` 找组，维护 `rcks`。测试的 `shutdownLeader` 通过 `GetClerk(gid).Leader()` 找到最近访问的 leader，因此应维护实际使用过的组 Clerk。
- 组 Clerk 在固定服务器列表中寻找 leader，并执行普通读写和迁移 RPC。

组 Clerk 的迁移签名为：

```go
FreezeShard(s shardcfg.Tshid, num shardcfg.Tnum) ([]byte, rpc.Err)
InstallShard(s shardcfg.Tshid, state []byte, num shardcfg.Tnum) rpc.Err
DeleteShard(s shardcfg.Tshid, num shardcfg.Tnum) rpc.Err
```

线上的 Freeze 回复还含 `Num`，但上述 Clerk 签名不直接返回它。应在组 Clerk 内解释回复是否属于当前请求的迁移代际，再给调用者相应结果；不能把更高代际的任意 State 当成本次冻结结果。

三个 RPC 都有 `Shard/Num`，Install 另有 `State []byte`；Install/Delete 的回复只有 `Err`。骨架没有提供完整迁移状态机或专门的全部阶段错误码，不能把你设计的内部状态名写成已存在接口。

### 2.3 三种编号不能混用

| 编号 | 含义 | 正确用途 |
|---|---|---|
| `ShardConfig.Num` / `shardcfg.Tnum` | 分片配置代际 | 隔离旧迁移；判断候选是否已过时 |
| 配置 KV 某个键的 `rpc.Tversion` | 该存储记录的修改次数 | versioned Put 竞争唯一 next、条件发布 current |
| 业务键的 `rpc.Tversion` | 某个用户键的写入版本 | 业务 Put 的条件判断；迁移时随 value 一起保留 |

它们也都不是 Raft term/index 或 RSM 请求身份。两份不同候选可能共享 Num；对一个配置记录的多次写入也不等于发生了同样多次分片重配置。

## 3. 5A：先建立一条可解释的交接边界

### 3.1 服务权必须在 DoOp 中判断

handler 中先查“我有这个分片”，随后等待 Submit，这两件事之间可能插入已提交的 Freeze。仅靠前置检查会让本应冻结后的 Put 继续生效。

把 Get、Put、Freeze、Install、Delete 都交给同组 RSM 排序；在 `DoOp` 执行时检查分片服务状态、配置代际和业务版本。这样才能回答：**这次 Put 到底排在冻结之前还是之后？**

沿用 [Lab 4 的提交与回复契约](#/c/mit-6.824-2021/lab/kvraft?v=guide)：拿到正确请求的已执行结果才有业务回复；RSM 成功和业务 `ErrWrongGroup/ErrVersion` 不要混为一层错误。

### 3.2 为一个分片画最小状态表

以下是帮助推理的逻辑状态，不是要求照抄的枚举或完整转移程序：

| 逻辑阶段 | 需要成立的事实 |
|---|---|
| 源组服务中 | 源组可读写；目标组还没有服务权 |
| 源组已冻结 | 旧组拒绝后续 Get/Put；输出状态覆盖冻结前已应用写入 |
| 目标组已安装 | 状态及键版本已复制到目标组状态机；旧组仍不能服务 |
| 源组已删除 | 源组释放该代际的数据，但仍需能识别迟到操作 |
| 配置已发布 | 新的 Query 把客户端导向目标组；旧缓存最终靠 ErrWrongGroup 刷新 |

冻结与安装之间可以短暂没有组服务该分片；不能为追求无停顿而让两组同时接收写入。目标组有服务权的依据是其状态机已经完成相应安装，不是“控制器发出过请求”。

考虑源组日志顺序 `Put(k) → Freeze(s)`：迁移状态必须包含这次写入。若顺序相反，Put 就不能在旧组成功。冻结结果要是一个稳定副本；边编码边读仍在变化的 map，会破坏这个边界或产生 race。

### 3.3 迁移要带走什么，删除后留下什么

至少带走分片中每个键的 value 和 version，以及你的设计中保持业务语义必需的状态。只拷贝 value 并把版本重置，可能让同一个旧 Put 在新组再次生效。

Freeze 的输出与 Install 的输入都是字节。可以在受保护的一致状态上生成独立编码，也可以先复制再编码；关键是异步编码过程不能继续引用可变业务 map。

删除应释放迁走的业务数据，但不能把防止旧 RPC 的代际／阶段信息一并忘掉。分片以后可能回到同一组；迟到的旧 Delete 不能删掉新一轮安装的数据。

不必保留无限的数据副本来帮助重试。应思考怎样用有限的已完成阶段信息辨识“已做完”，并在恢复时区分“源组已删除”与“真的迁移了一个空分片”。

### 3.4 同号不等于重复，同号重复也不能重置数据

仅存最大 Num 然后写 `num <= max → 拒绝` 不足以完成实验：同一迁移的 Freeze 与 Delete 都会到达源组，并且这些 RPC 可能重发。

设计时分别推演：

- **旧 Num**：不能改变新代际状态。
- **同 Num、下一合法阶段**：不能被当作过期而永久卡住。
- **同 Num、同阶段重试**：不能重复产生破坏性效果，但调用者要能知道可以继续或已经完成。
- **更大 Num**：也不是无条件覆盖许可；仍须结合当前阶段与已选配置证明转移合法。

尤其是重复 Install：目标组可能已经接受新业务写入。若把旧 State 再覆盖一次，新写入就消失了。重复 Freeze 不应把已删除或后来重新获得的分片变成旧代际的有效快照。

这些约束属于迁移协议的幂等性，不是要求把 5D 的 exactly-once 客户端协议提前完整实现。

## 4. 路由刷新不能抹掉 Put 的不确定性

| 返回或观察 | 应由哪层处理 |
|---|---|
| RPC 无回复、`ErrWrongLeader` | 组内换节点／重试；不能推断旧尝试一定没执行 |
| `ErrWrongGroup` | 系统 Clerk 刷新配置后重新路由，不能只在旧组轮询 leader |
| `OK`、Get 的 `ErrNoKey` | 返回业务结果 |
| Put 的版本冲突 | 结合此前重发／不确定性，按 Clerk 契约决定 `ErrVersion` 或 `ErrMaybe` |

一条需要手推的路径：旧组 Put 实际生效但回复丢失 → 分片迁移 → 系统 Clerk 换组重试同一 `(key,value,version)` → 新组因版本已增加而拒绝。此时对外不能说“确定没有执行”。即使中途收到 `ErrWrongGroup`，也不能擦掉早先丢回复的历史。

内层和外层 Clerk 要约定怎样保留或传递这种不确定性；`ErrMaybe` 是 Clerk 层结果，不是服务器执行业务时返回的错误。无论换 leader 还是换组，都不能自动提高调用者提供的 version；那会把一次请求变成新写入。

配置可以缓存，但缓存不授予服务权；分片组自身必须拒绝不再负责的请求。配置发布前客户端可能反复看到旧 current，这属于迁移窗口，不能将“仍旧路由到旧组”误判为数据丢失。

## 5. 5B：恢复的是已经选定的工作

### 5.1 写在控制器本地的进度不够

旧控制器的 goroutine、局部变量或内存锁不会跟着新对象重建。先把迁移意图存入独立的配置 KV，才开始让分片进入冻结等中间状态。官方建议 current/next；新控制器在 `InitController()` 中观察两者，接续尚未发布的下一配置。

这里的“保存”表示状态不依赖某个控制器对象存活；默认 Lab 2 KV 不是复制数据库，本实验 A–C 没有因此承诺配置 KV 自身故障后的可用性。

### 5.2 用中断点验证，而不是靠重发碰运气

| 失联时刻 | 新控制器需要解释的问题 |
|---|---|
| next 写入成功，但回复丢失 | 怎样确认哪个候选真正被选中？ |
| Freeze 已完成，但回复丢失 | 重发能否取回有效冻结状态或辨识更后阶段？ |
| Install 已完成，但回复丢失 | 重复安装会不会覆盖已经接收的新写入？ |
| Delete 已完成，current 尚未发布 | 如何知道目标已有数据，避免把源组空状态再安装过去？ |
| current 已发布，旧控制器还在等待 | 后续迟到回复是否会造成配置倒退或重复清理？ |

不需要在指导里预先给出每个字段和所有分支，但你的实现必须能回答这些问题。恢复者的目标是完成**已记录的候选配置**，不是重新计算一份看起来合理、Num 相同的配置。

`TestRecoverCtrler5B` 经 `partitionCtrler` 停一个分片组，让旧控制器卡在 Join/Leave 中，再隔离它，恢复组、启动新控制器并调用 `InitController()`。测试随后检查配置前进、成员状态及键版本；因此不能让 InitController 只启动一个后台恢复任务就立即宣称恢复结束。

## 6. 5C：配置选定与分片隔离是两道不同的门

### 6.1 先竞争唯一候选，再做副作用

设 current 为 Num 7。控制器 A 算出“加入 G2”的 Num 8，B 算出“加入 G3”的 Num 8。分片组只看到 Num 无法区分两种互相矛盾的目标，所以必须先通过配置 KV 的版本化 Put 确定唯一 next。

竞争失败者不能开始移动自己候选的分片，也不能读到新版本后把同一旧候选强行覆盖进去。恢复者可以协作完成**已经被选定**的候选；“只有一个候选获选”不等于“只能有一个 goroutine 执行重复恢复 RPC”。

### 6.2 ErrMaybe 不是胜选通知

配置 KV 的 Put 也会遇到丢回复。拿到 `ErrMaybe` 既不能立刻认定胜出，也不能认定失败；应重新读取并依据配置内容、Num 与记录版本判断实际结果。仅比较 Num 不够，因为竞争候选的 Num 本来就相同。

在决定重试、协作或退出之前，想清楚当前看到的记录是否仍代表你等待的那轮变更。若配置已继续前进，不能用旧 RPC 回复把它拉回。

### 6.3 发布 current 也需要保护

只保护 next，而无条件覆盖 current，仍会被重新连网的旧控制器破坏。所有配置写入都应有相应的条件和单调性判断；所有分片管理 RPC 都应检查代际及阶段。

跨两个配置键的 Get/Put 并不是一个事务。你需要自行规定读写顺序以及冲突后如何重读确认，使可观察的中间组合仍可恢复；不要偷偷假定 Lab 2 提供了跨键原子更新，也不必为 A–C 引入 2PC。

固定测试有 `MakeTestLeases`、“leased leadership”文字和 `AcquireLock` 名称，但实际入口使用版本化配置和控制器分区重连来检查行为；这些名字不能单独推出“必须实现基于时间的租约”或“必须调用 Lab 2 锁”。与主线任务一致，关键是唯一选定、幂等恢复、旧操作隔离。

## 7. 复用快照契约，只扩充分片业务状态

继续使用 [Lab 4 指导 §6](#/c/mit-6.824-2021/lab/kvraft?v=guide) 的 KV/RSM 双层快照边界，以及 [Lab 3 恢复契约](#/c/mit-6.824-2021/lab/raft?v=guide)。本实验不重新发明 Raft 快照协议。

需要新考虑的是业务快照内容：除键值与键版本外，还要保存分片服务状态、迁移 Num 及恢复／幂等判定必需的阶段信息。否则某组重启后可能数据还在，却忘记“我已冻结、不能再服务”。

首次初始化 `Gid1` 拥有全部分片，不能覆盖后来 Restore 或日志重放得到的归属。先准备可用业务状态，再让 RSM reader 访问它；启动函数仍需尽快返回。

**分片 `InstallShard` 与 Raft `InstallSnapshot` 是不同操作。**前者把某个分片交给另一个独立组，并作为目标组的一条业务命令复制；后者把同一 Raft 组的日志前缀状态传给落后副本。配置 Num 不能用作 Raft snapshot index。

删除空间也值得定点检查：`TestDeleteBasic5A` 比较两组快照总大小与迁移前大小，容许多 10000 字节；它检查不要永久保留两份业务数据，不是给所有快照规定固定容量。`TestShutdown5A` 本身以 `maxraftstate=-1` 启动，主要检查持久日志恢复；不能仅凭测试名把它写成开启快照的专项恢复测试。

## 8. 进展粒度是分片，不是整个组

不要为了等待某个离线目标组，长期持有整个分片组的业务锁，也不要把整个组设成“迁移中禁止所有请求”。同组内没有移动的分片应继续工作。

`TestProgressShutdown5A` 关闭若干组后，要求仍在线组对应的 Get 在观察窗内结束；`TestProgressJoin5A` 则特意读取**参与迁移的组里那些没有移动的分片**，在 4 秒工作窗口统计至少 100 次 Get，并设置 8 秒外层超时。它比“系统中还有某个组活着”更严格。

这些时间是固定测试观察条件，不是让你按时钟决定迁移完成的协议规则。前进需要真实的冻结、安装、删除及配置发布证据。

## 9. 测试与排错入口

以下命令供你实现后在实验仓库 `src/` 执行；本次内容制作没有运行它们。

| 目标 | 命令 | 首查边界 |
|---|---|---|
| 配置存取 | `make RUN="-run '^TestInitQuery5A$'" shardkv` | 序列化、初始版本、Query |
| 静态数据路径 | `make RUN="-run '^TestStaticOneShardGroup5A$'" shardkv` | Gid1 初始化、组 Clerk、leader 切换 |
| 第一次移动与释放 | `make RUN="-run 'Test(JoinBasic|DeleteBasic)5A$'" shardkv` | 服务权、键版本、重复安装、旧数据清理 |
| 退出与重新加入 | `make RUN="-run '^TestJoinLeaveBasic5A$'" shardkv` | 数据来源、旧组恢复、迟到 Delete |
| 局部进展 | `make RUN="-run 'TestProgress.*5A$'" shardkv` | 不移动分片是否被整组锁住 |
| A 全部 | `make RUN="-run 5A" shardkv` | 多组、丢消息、重启、并发 Clerk |
| 接续恢复 | `make RUN="-run 5B" shardkv` | current/next、各阶段重发、InitController |
| 并发候选 | `make RUN="-run 'Test(ConcurrentReliable|AcquireLockConcurrentUnreliable)5C$'" shardkv` | 同 Num 不同配置、条件更新、ErrMaybe |
| 旧控制器重连 | `make RUN="-run Partition" shardkv` | 所有旧副作用是否被隔离 |
| C 全部 | `make RUN="-run 5C" shardkv` | 并发配置与故障恢复组合 |
| 回归 | `make shardkv`、`make rsm1`、`make kvraft1`、`make raft1` | 新状态未破坏底层接口 |

`make shardkv` 只在 `shardkv1` 当前包执行 `go test`，不会递归运行 `shardcfg` 的 `TestBasic`；需要定点查看配置工具时，可在 `src/` 执行 `go test -race ./shardkv1/shardcfg`。它验证给定配置辅助逻辑，不是你的迁移实现验收。

### 读测试时不要扩大它证明的范围

- `concurCtrler` 启动 4 条控制器工作流，反复提议 Join/Leave，检查最后数据；它不是旧版 shardmaster 接口测试。
- `TestAcquireLockConcurrentUnreliable5C` 实际执行的也是 `concurCtrler`，没有直接调用某个 Acquire 方法。
- Lab 5 的 `MakeTestMaxRaft` 传入 `randomkeys=false`；`OneClientPut` 默认选 `ka[0]`。并发历史测试虽创建多键列表，实际热路径主要竞争同一个键；`SpreadPuts/CheckGet` 才另行覆盖多键和键版本。
- `CheckGet` 显式比较 value、version、error；Porcupine 的 Get 模型只比较 value。检查器超时的 `Unknown` 会打印“assuming history is ok”，不能解读成完整证明。
- `TestJoinLeave5B` 第一次等待写成 `time.After(1 * NSEC)`，`NSEC=2`，实际上是 2 纳秒；后续窗口才明确乘 `time.Second`。遵守“目标不可用时不能虚报完成”的语义，不依赖这处短窗口放宽协议。

建议每条调试记录带：控制器／组／节点、分片、操作、请求 Num、本地 Num 与阶段、业务键版本、配置记录版本、RSM 请求身份，以及接受／忽略／退出原因。优先寻找第一次“旧状态覆盖新状态”或“双组都接受”的事件。

## 10. 完成前的自问

<details><summary>收到同 Num 的 Install，就能无条件返回成功吗？</summary>

不能只看数字。先确认它对应已经选定的那轮迁移，且本地状态确实说明安装已完成或已安全前进。真正的重复不应再次覆盖数据；尚未完成的合法安装也不能被误判成成功。
</details>

<details><summary>源组删除后，为什么还要保留少量迁移元数据？</summary>

为了辨认迟到 Freeze/Install/Delete，避免把已删除误判为空的有效分片，或让旧 Delete 破坏后来重新安装的数据。保留元数据不等于永久保留被迁走的整份数据。
</details>

<details><summary>新控制器已恢复，旧控制器还能继续存在吗？</summary>

可以存在甚至收到迟到回复，但不能执行会回退状态的副作用。不能靠“它大概死了”或本地锁保证这一点；分片操作与配置存储更新都要有隔离旧操作的条件。
</details>

<details><summary>迁移用冻结、安装、删除，是否就是两阶段提交？</summary>

不是。A–C 要解决的是单分片服务权交接和可恢复的配置变更，不提供任意跨分片业务事务。2PC/2PL 出现在官方 5D 的跨分片事务扩展中。
</details>

## 引用与来源

- MIT 6.5840 Spring 2026，[Lab 5](https://pdos.csail.mit.edu/6.824/labs/lab-shard1.html)；完整要求与全部提示的中译见[实验说明](#/c/mit-6.824-2021/lab/shardkv?v=zh)。本页为自主思路指导，不含完整实验实现。
- 固定仓库 `git://g.csail.mit.edu/6.5840-golabs-2026`，提交 `513cac0aef010750fc74688da8a395974a83cf7a`。归档及成员哈希已验证，独立临时解压后只读；逐文件范围见 `sources/p5-lab5/manifest-fragment.json` 与 `review.txt`。
- [RSM／迁移桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)、[Lab 4 指导](#/c/mit-6.824-2021/lab/kvraft?v=guide)、[Lab 3 指导](#/c/mit-6.824-2021/lab/raft?v=guide)承载共用推导和恢复契约；本页只增加分片迁移所需的业务边界。
- 官方源码是待实现 starter；以上属于静态接口和测试审阅，不代表实验已经实现或通过。没有运行实验或 Go 编译；课程站构建与内容检查另记于批次审阅记录。
