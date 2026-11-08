---
source: MIT 6.5840 Spring 2026，Lab 2 Key/Value Server；lab-kvsrv1.html 的 2026-11-08 快照；固定代码 513cac0aef010750fc74688da8a395974a83cf7a
license: MIT 课程网站 CC BY 3.0 US；本页为官方要求的中文翻译，测试输出压缩为命令与测试名称，版本说明另标编者注。
status: 已完整阅读并翻译官方正文与四项任务，静态核对固定提交的 RPC、Clerk、锁接口和测试入口；没有实现答案，没有运行实验测试。
---

# Lab 2：键值服务器

## 1. 简介

本实验要构建一个运行在单台机器上的键值服务器。即使网络发生故障，它也要保证每个 Put 操作**至多执行一次**，并使操作满足**线性一致性**。随后使用这个 KV 服务器实现锁。后续实验会复制类似的服务器，以应对服务器崩溃。

> **编者版本提示：** 这是 2026 新增的桥接实验，不是 2021 年的 Raft Lab 2。环境和固定提交的获取方法统一见[公共资料](#/c/mit-6.824-2021)。本页所有 `src/` 都指实验仓库，不是课程站源码。

## 2. KV 服务器的语义

客户端通过 Clerk 与服务器交互。Clerk 是一组向服务器发送 RPC 的库函数，提供两种操作：

```text
Put(key, value, version)
Get(key)
```

服务器维护一个内存 map，为每个键保存 `(value, version)`。键和值都是字符串；版本号记录该键已被成功写入的次数。

`Put(key,value,version)` 只有在请求版本与服务器上该键的版本相同的情况下，才安装或替换该键的值。版本匹配时，服务器还要将该键版本加一；不匹配则返回 `rpc.ErrVersion`。

客户端可以用版本 0 创建新键，创建成功后服务器保存的版本为 1。若请求版本大于 0，而键不存在，服务器应返回 `rpc.ErrNoKey`。

`Get(key)` 取得该键当前的值及版本；键不存在时返回 `rpc.ErrNoKey`。

为每个键维护版本号，将用于通过 Put 实现锁，也用于在网络不可靠、客户端重发时，维持 Put 的至多一次语义。

完成实验并通过全部测试后，从调用 `Clerk.Get`、`Clerk.Put` 的客户端视角看，服务应当线性一致：

- 没有并发时，各操作观察到之前操作序列造成的状态修改。
- 有并发时，返回值和最终状态应当等同于这些操作按照某个顺序、一次一个地执行。
- 两个操作的时间区间重叠，就称为并发。例如 X 调用 Put，Y 也调用 Put，之后 X 的调用才返回。
- 一个操作必须观察到在它开始前就已完成的操作的效果。

这对应用很方便，因为它近似于一个逐个处理请求的服务器。例如一个客户端已收到更新成功的回复，之后其他客户端才发起读取，就必须看到该更新的效果。对单机服务器，实现这一性质相对容易。背景解释见[线性一致性笔记](#/c/mit-6.824-2021/lec/update-linearizability?v=notes)。

## 3. 开始工作

骨架和测试在 `src/kvsrv1`：

- `client.go` 实现客户端使用的 Clerk，提供 Put、Get。
- `server.go` 包含服务器代码及 Put、Get RPC handler。
- 你需要修改 `client.go` 和 `server.go`。
- 请求、回复和错误定义在 `kvsrv1/rpc/rpc.go`；应阅读它，但不必修改它。

官方启动步骤先进入仓库、执行 `git pull` 获取课程更新，再进入 `src` 运行 `make kvsrv1`。未实现的骨架会在 `TestReliablePut` 中因 `Put err ErrNoKey` 等错误失败。

> **编者固定版本调整：** 本路线已经固定提交，按公共资料建立学习分支后使用下面的测试入口；不自动拉取最新代码，以免改变接口版本。官方的更新建议与本路线的版本冻结是两种不同安排。

```bash
# 当前目录：实验仓库 src/
make kvsrv1
```

该目标会先构建 `main/kvsrv1d`，再进入 `kvsrv1` 执行默认带 `-v -race` 的 `go test`。

## 4. 任务一：可靠网络上的键值服务器

第一项任务是在没有消息丢失时正确运行。给 `client.go` 的 Clerk Put/Get 增加 RPC 发送代码，并在 `server.go` 中实现 Put/Get handler。

通过测试套件中 Reliable 相关测试，即完成本阶段：

```bash
# 当前目录：实验仓库 src/
make RUN="-run Reliable" kvsrv1
```

| 测试 | 官方测试含义 |
|---|---|
| `TestReliablePut` | 单客户端，可靠网络上的 Put 与基本操作 |
| `TestPutConcurrentReliable` | 多客户端竞争写同一个键 |
| `TestMemPutManyClientsReliable` | 许多客户端写入时的服务器内存使用 |

官方示例中 `Passed` 后的数字依次是实际耗时（秒）、常数 1、发送的 RPC 数（含客户端 RPC），以及执行的键值操作数，也就是 Clerk Get/Put 调用次数。

## 5. 任务二：用 KV Clerk 实现锁

许多分布式应用使用键值服务协调不同机器上的客户端。例如 ZooKeeper、Etcd 的分布式锁，作用类似 Go 线程之间的 `sync.Mutex`；条件写入可以用于构建这种锁。

你的任务是用 KV 服务器保存设计所需的每把锁的状态。可以有多把相互独立的锁，各自名称通过 `MakeLock` 参数传入。

锁提供 `Acquire` 和 `Release`。规格是：**同一时刻至多一个客户端成功取得同名锁**；其他客户端必须等待，直到持有者调用 Release 释放。

骨架和测试在 `src/kvsrv1/lock/`。需要修改 `lock.go`，让 Acquire 与 Release 通过 `lk.ck.Put()`、`lk.ck.Get()` 将锁状态保存在 KV 服务器中。

如果客户端持锁时崩溃，锁就永远不会被释放。更复杂的设计可使用 lease，在租约到期时替客户端释放。但本实验假设客户端不崩溃，可以忽略这个问题。

实现两个方法并通过以下测试，即完成本阶段：

```bash
# 当前目录：实验仓库 src/
make RUN="-run Reliable" lock1
```

| 测试 | 官方测试含义 |
|---|---|
| `TestReliableBasic` | 一次 Acquire 和 Release |
| `TestReliableNested` | 一个客户端、两把锁 |
| `TestOneClientReliable` | 一个锁客户端持续使用 |
| `TestManyClientsReliable` | 十个锁客户端竞争 |

**即使尚未实现锁，最前面两个测试也会通过。** 不要以它们作为完成依据。本任务代码量不大，但比上一步需要更多独立思考。

官方提示：每个锁客户端需要一个唯一标识，可以调用 `kvtest.RandValue(8)` 生成随机字符串。

## 6. 任务三：处理丢失的 RPC 请求与回复

这一阶段，网络可能重排、延迟或丢弃 RPC 请求及回复。为从消息丢失中恢复，Clerk 必须不断重试每个 RPC，直到收到服务器回复。

请求丢失时，重发使服务器收到并执行重发请求。但若丢的是回复，服务器可能已经执行过原请求，随后又收到第二份。客户端只知道“没收到回复”，不能分辨是哪一种情况。

对 Get，重复请求不会修改服务器状态。对 Put，只要重发时使用**同一个版本号**，也是安全的：服务器若已执行了原请求，版本就已经改变，重发请求将得到 `rpc.ErrVersion`，而不是再次执行。

### 重发后的 ErrVersion 为什么要变成 ErrMaybe

如果服务器对一个已经重发过的 Put 返回 `rpc.ErrVersion`，Clerk 无法确定它的写入是否发生：

1. 原请求可能成功，但成功回复丢失；重发才得到 ErrVersion。
2. 也可能另一个 Clerk 在原请求到达前就修改了该键，所以这个 Clerk 的所有尝试都没有执行。

因此，**对重发 Put 收到 ErrVersion 时，`Clerk.Put` 必须向应用返回 `rpc.ErrMaybe`**。应用负责处理“可能已经执行”的情况。

如果最初那次、未经重发的 Put 就收到 ErrVersion，则应返回 ErrVersion，因为可以确定该操作没有执行。

若 Put 能恰好一次并总能报告确定结果，应用会更方便；但要避免这种 ErrMaybe，通常需要在服务器为每个 Clerk 保存额外状态。最后一项锁任务就是让你体会如何在至多一次的 Clerk.Put 之上编程。

### 修改 Clerk 并运行完整 KV 测试

修改 `kvsrv1/client.go`。`ck.clnt.Call()` 返回 true，表示收到服务器 RPC 回复；返回 false，表示在等待区间内未收到回复。Clerk 应持续重发直到收到回复，并遵守上面的 ErrMaybe 规则。**这一阶段不应要求修改服务器。**

```bash
# 当前目录：实验仓库 src/
make kvsrv1
```

完成标准是通过全部 KV 测试，包括前三个可靠网络测试及 `TestUnreliableNet`。

官方提示：重试之前稍等一会儿，例如使用 `time.Sleep(100 * time.Millisecond)`。

## 7. 任务四：不可靠网络上的锁

修改锁实现，使它在使用新版 Clerk、网络不可靠时也保持正确。通过全部 lock1 测试，即完成本阶段：

```bash
# 当前目录：实验仓库 src/
make lock1
```

除可靠网络下四个测试外，还需通过：

- `TestOneClientUnreliable`：一个锁客户端，不可靠网络。
- `TestManyClientsUnreliable`：多个锁客户端，不可靠网络。

思路与接口定位见[实验指导](#/c/mit-6.824-2021/lab/kvsrv?v=guide)。

## 引用与许可

- MIT 6.5840 Spring 2026，课程团队，[Lab 2: Key/Value Server](https://pdos.csail.mit.edu/6.824/labs/lab-kvsrv1.html)。快照 `sources/lab-kvsrv-2026.html`，抓取于 2026-11-08，Last-Modified 为 2026-01-27。
- [课程首页](https://pdos.csail.mit.edu/6.824/index.html)标注 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。本页为中文翻译，重排少量段落，保留全部任务与提示；终端示例的易变耗时和计数压缩为测试清单，不把官方示例通过输出当作本站运行结果。
- [官方线性一致性 FAQ](https://pdos.csail.mit.edu/6.824/papers/linearizability-faq.txt)；共享理论精读见对应 Updates。
- 官方页的通用入口：[协作约定](https://pdos.csail.mit.edu/6.824/labs/collab.html)、[提交方法](https://pdos.csail.mit.edu/6.824/labs/submit.html)、[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)、[实验建议](https://pdos.csail.mit.edu/6.824/labs/guidance.html)。这些外链不是本页全文翻译范围。
- 固定代码 `513cac0aef010750fc74688da8a395974a83cf7a` 的接口和测试已静态核对；官方页的样例测试耗时及操作数不要求与固定提交完全一致。实验测试未运行。
