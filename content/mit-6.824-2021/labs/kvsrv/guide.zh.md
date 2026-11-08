---
source: MIT 6.5840 Spring 2026 Lab 2；官方 starter 固定提交 513cac0aef010750fc74688da8a395974a83cf7a 的 kvsrv1、kvtest1 与 src/Makefile
license: 编者自主实验指导；官方要求中译与署名集中在实验说明，不提供完整实验实现。
status: 已静态读取接口、骨架、两组完整测试与共享测试工具；未实现实验答案，未编译或运行实验测试。
---

# Lab 2 指导：将“执行一次”与“知道结果”分开

## 1. 先画清三个层次

应用 → 锁对象 → KV Clerk → RPC → KVServer。

- **KVServer** 决定一个请求是否符合键的当前版本。
- **Clerk** 处理消息未返回及同一请求的重发，向应用表达确定／不确定结果。
- **锁对象** 用读到的状态和条件写入决定所有权，不能把不确定写入直接当作拿锁成功。

理论背景分别见 [L2](#/c/mit-6.824-2021/lec/lec02?v=notes)、[L10](#/c/mit-6.824-2021/lec/lec10?v=notes)和[线性一致性](#/c/mit-6.824-2021/lec/update-linearizability?v=notes)。实验要交付的四项任务以[实验说明](#/c/mit-6.824-2021/lab/kvsrv?v=zh)为准。

## 2. 固定提交的接口地图

以下路径都相对**实验仓库**：

| 文件 | 阅读目的 |
|---|---|
| `src/kvsrv1/rpc/rpc.go` | 参数、回复、错误常量、`Tversion uint64` |
| `src/kvsrv1/client.go` | Clerk 的重试边界与 RPC 名称 |
| `src/kvsrv1/server.go` | 内存状态与并发 handler |
| `src/kvsrv1/lock/lock.go` | 锁只依赖 `kvtest.IKVClerk` |
| `src/kvtest1/kvtest.go` | Clerk 接口、操作计数、测试调用约定 |
| `src/kvsrv1/kvsrv_test.go` | 四个 KV 测试及真实断言 |
| `src/kvsrv1/lock/lock_test.go` | 六个锁测试及互斥检查 |
| `src/Makefile` | 构建服务进程、测试入口与默认 `-race` |

```go
// 接口摘录，不是实验答案。
Get(string) (string, rpc.Tversion, rpc.Err)
Put(string, string, rpc.Tversion) rpc.Err

MakeLock(ck kvtest.IKVClerk, lockname string) *Lock
Acquire()
Release()
```

RPC 方法名是 `KVServer.Get`、`KVServer.Put`；请求字段首字母大写。GetReply 有 Value、Version、Err；PutReply 只有 Err。服务器 handler 不返回 Go `error`，签名也不同于 2021 `net/rpc` 示例。

`ErrMaybe` 明确是 **Clerk-only** 错误。`ErrWrongLeader`、`ErrWrongGroup` 为以后实验预留；本实验无 leader 选择和分片路由。`StartKVServer` 的复制相关参数，骨架已说明本阶段可忽略。

## 3. 第一阶段：先写顺序规格，再决定锁范围

将单键状态理解成“不存在”或 `(value,version)`，按以下表核对所有分支：

| 当前状态 | 请求 | 结果与新状态 |
|---|---|---|
| 不存在 | Get | ErrNoKey；不变 |
| 存在 `(a,v)` | Get | OK、a、v；不变 |
| 不存在 | Put(b,0) | OK；变成 `(b,1)` |
| 不存在 | Put(b,v)，v>0 | ErrNoKey；不变 |
| 存在 `(a,v)` | Put(b,v) | OK；变成 `(b,v+1)` |
| 存在 `(a,v)` | Put(b,w)，w≠v | ErrVersion；不变 |

这里版本是**每个键的版本**，不是全局时钟、客户端编号或 RPC 次数。失败的 Put 不递增；成功写入即使值相同也递增，因为它仍是一次成功写入。

并发时必须原子化“判断键是否存在／检查版本／写入值与新版本”。如果检查和写入被拆开，两名客户端都可能基于同一版本成功。Get 也必须取得同一状态的 value/version，不能把两个时刻拼成一对。

最初用一把锁保护服务器状态即可形成清晰的实现边界。远程调用发生在 Clerk，不需要为本任务增加服务器侧 RPC 等待或后台调度结构。

阶段验收先看 `TestReliablePut`：创建键后版本为 1；用 0 再写同键得到 ErrVersion；不存在键用非零版本得到 ErrNoKey。然后检查并发测试和内存测试，而不是只看单客户端成功。

## 4. 第二阶段：锁不是“读空闲，再无条件写忙碌”

两名客户端可能同时读到空闲。只有带版本条件的写入，才能让基于同一状态的竞争产生明确胜者。

先自行设计锁状态表示，写下三个不变量：

1. 同名锁至多有一个当前所有者。
2. 不同锁名使用独立状态，可以同时持有。
3. Release 不应清除另一个客户端后来取得的所有权。

官方提示的随机标识用于区分锁客户端。它不是“服务器要保存每个 Clerk 历史”的指令，也不能用进程内 `sync.Mutex` 替代服务器上的跨客户端协调。

先在可靠网络下解释：观察空闲是什么意义？哪个条件写入能赋予所有权？竞争失败后，需要重新观察什么？把这些解释写出来再编码。

这里的 Nested 测试是**同一客户端持有两把不同名称的锁**，不是要求同一把锁可重入。Basic 和 Nested 几乎只检查调用能返回，空实现也能通过；ManyClients 才会用共享受保护数据检验互斥。

## 5. 第三阶段：同一个逻辑 Put，重发参数保持不变

一次应用层 `Put(k,b,v)` 可以对应多次 RPC 尝试。只要仍在这个调用内部重发，`k,b,v` 都应保持不变。

如果原请求成功后回复丢失，你在 Clerk 内偷偷 Get 新版本，再把 Put 的版本升高重试，就把一次逻辑操作变成第二次写入；这会破坏至多一次，也可能覆盖并发客户端已经写下的状态。

### 客户端的结果知识

| Clerk 的观察 | 应如何理解 |
|---|---|
| `Call` 返回 false | 没拿到回复；并不能判断是否执行；稍等后重发原请求 |
| 收到 OK | 这次逻辑 Put 成功 |
| 首次 RPC 收到 ErrVersion | 确定没有执行该 Put；返回 ErrVersion |
| 发生过无回复重发后，收到 ErrVersion | 先前可能执行；返回 ErrMaybe |
| 收到 ErrNoKey | 键不存在且请求版本不适合创建；不要伪装成成功 |

该表的“是否重发”属于**当前 Put 调用**，不能作为 Clerk 永久状态污染以后的调用。服务端只知道当前请求的条件是否成立，不知道客户端曾丢过哪一份回复，因此不能由服务器擅自返回 ErrMaybe。

### 两个无法区分的历史

设最初键是 `(old,7)`，A 请求写 `(new,7)`：

- 历史甲：A 成功，键版本变 8；OK 回复丢失；A 重发收到 ErrVersion。
- 历史乙：B 先把键版本改为 8；A 的原请求未成功且没有可见回复；A 重发收到 ErrVersion。

A 观察相同，实际效果不同。`ErrMaybe` 是忠实暴露这个知识边界，不是“随便返回一个错误”。不要把它等价为成功，也不要等价为失败。

读请求不修改状态，因此 Get 丢回复后可以重试。读到的值可以是重试期间某个合法时刻的状态，而不一定是最初请求发出时的状态。

## 6. 第四阶段：锁怎样面对“不知道写成没有”

把 Acquire、Release 各自列成一张状态表：当前读到谁持有锁、准备依据哪个版本尝试状态转换、返回确定成功／确定冲突／ErrMaybe 时，掌握了什么事实。

关键提示：

- Acquire 收到 ErrMaybe，不能直接进入临界区；先思考怎样利用服务器上**可辨别的所有者标识**确认当前权利。
- 如果试图只写一个相同的“忙碌”值，读回忙碌也无法判断是自己还是别人拿到了锁。
- Release 回复丢失后，旧释放可能已经成功，且另一客户端可能已经拿到锁。不能重新读一个新版本，再无条件把新持有者清掉。
- 版本条件用来绑定“我依据的那次观察”，标识用来区分“状态是谁建立的”；两者职责不同。
- 客户端不崩溃是本实验假设。这里没有要求 lease、公平队列或自动回收死客户端锁。

请先用两个客户端手画“获取成功但回复丢失”“释放成功但回复丢失”“另一个客户端在两次观察间取得锁”三种时间线。你的实现应能说明每个返回点为什么安全；本指导不提供完整锁状态机或答案代码。

## 7. 按固定提交执行测试

完成自己的实现后，在实验仓库 `src/` 执行：

```bash
make RUN="-run Reliable" kvsrv1
make RUN="-run Reliable" lock1
make kvsrv1
make lock1
```

进一步定位时可按已有测试名筛选，例如：

```bash
make RUN="-run '^TestUnreliableNet$'" kvsrv1
make RUN="-run '^TestManyClientsUnreliable$'" lock1
```

Makefile 会构建测试需要启动的 `main/kvsrv1d`。只在包目录直接跑 `go test`，可能漏掉先构建服务进程的步骤；首选上述 make 入口。页面通用组件的 QEMU 命令不适用。

阅读测试还能避免三种误判：

- `TestMemPutManyClientsReliable` 在固定提交中创建 20,000 个 Clerk，检查服务器内存增量；按客户端无限增长的去重缓存不是这版任务需要的机制。官网终端示例里的计数是另一次运行结果。
- `TestUnreliableNet` 特意要求出现 ErrMaybe。在它的**单写客户端**前提下，某些 ErrMaybe 可被测试推断为确实写过；不能推广为多客户端时 ErrMaybe 总等于成功。
- KV 并发和不可靠测试有 Porcupine 检查入口；测试通过只覆盖实际生成的历史，不等于所有可能执行均已证明正确。

## 8. 调试时先问这五个问题

1. 同一版本为何会有两个 Put 都返回 OK？检查判断与更新是否在同一临界区。
2. 为什么版本比预期大？检查是否对失败请求递增、是否重试时换了版本。
3. 为什么偶发返回 ErrVersion 却出现了自己的值？检查 Clerk 是否把重发后的冲突误报为确定失败。
4. 为什么两名客户端都进入临界区？检查是否将 ErrMaybe 当作拿锁成功，或是否只有无条件“读空闲再写忙碌”。
5. 为什么释放后还会抢走别人的锁？检查是否用旧操作的意图覆盖了新的版本与所有者。

## 引用与来源

- [2026 Lab 2 官方要求](https://pdos.csail.mit.edu/6.824/labs/lab-kvsrv1.html)，完整中译见本实验说明。
- 官方仓库 `git://g.csail.mit.edu/6.5840-golabs-2026`，提交 `513cac0aef010750fc74688da8a395974a83cf7a`；源码归档、文件清单及哈希见 `sources/lab-code-manifest.json`，本批详细阅读记录见 `sources/P2-REVIEW.txt`。
- 本页为静态接口与测试解读。没有运行 KV 或锁实验测试，不记录学习者已完成实验。
