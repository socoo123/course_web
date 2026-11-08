---
source: MIT 6.824 Spring 2020 官方课表；MIT 6.5840 Spring 2026 官方课表、五个实验页与实验代码
status: P1 已交付 L1 笔记、论文精读与 2026 Lab 1 说明及指导；L1 字幕重试仍为 HTTP 429，译稿缺失。其余内容按后续批次推进；实验测试未运行。
license: 本页为编者自主导航；外链论文、视频、讲义与实验要求的许可分别核实，不视为统一 CC 授权。
---

# 分布式系统：公共资料与学习路线

## 怎样学这门课

先把一个请求沿系统走一遍：客户端如何发出请求，服务器如何执行，回复丢失后怎么办；再增加副本，追问哪个节点可以决定执行顺序；最后把数据分片，追问迁移时谁有权服务。

这条路线贯穿五个实验：**MapReduce → 单机 KV 与锁 → Raft → 复制 KV → 分片 KV**。读论文时抓住问题、机制、不变量与故障情境；写实验时把不变量落实到状态、并发边界和测试。

- **课程主线**：2020 年 6.824，保留 L1–L21 编号。L21 是项目展示，L1–L20 有官方视频入口。
- **动手实验**：五个实验全部采用 2026 年 6.5840。同一个代码仓库、同一个固定提交，逐步复用自己的实现。
- **Updates**：排在旧课之后。前两项是实验桥接，其余是专题选读；“新增”只表示相对本课程选用的 2020 主线新增或明显变化。
- **三种讲座材料**：课程笔记提炼和推导；中文译稿整理真实课堂；课程资料承载课外阅读。共享阅读入口集中在本页。

## 先走完五个实验

以下是编者建议的学习顺序，不是 MIT 的官方上课日期。侧栏的“核心 / 选读”和实验难度星级也用于自学导航；实验工时因基础与调试过程而异。

| 阶段 | 先读什么 | 动手目标 | 过关时应能解释 |
|---|---|---|---|
| 0 · Go 准备 | [L2 RPC 与线程](#/c/mit-6.824-2020/lec/lec02?v=notes)、按需提前读 [L5 Go 与 Raft](#/c/mit-6.824-2020/lec/lec05?v=notes) | 熟悉 goroutine、channel、mutex/cond、RPC 和 race detector | 哪些状态被多个 goroutine 访问？锁保护哪个不变量？ |
| 1 · 调度与重试 | [L1 MapReduce](#/c/mit-6.824-2020/lec/lec01?v=notes)、L2 | [Lab 1 MapReduce](#/c/mit-6.824-2020/lab/mr?v=zh) | 为什么无法可靠区分慢 worker 与宕机 worker？重派何时安全？ |
| 2 · RPC 语义 | [Updates · 线性一致性](#/c/mit-6.824-2020/lec/update-linearizability?v=notes)、回看 L2/L5 | [Lab 2 KV 与锁](#/c/mit-6.824-2020/lab/kvsrv?v=zh) | 带版本号的 Put、ErrVersion 与 ErrMaybe 分别表示什么？ |
| 3 · 复制与共识 | [L3 GFS](#/c/mit-6.824-2020/lec/lec03?v=notes)、[L4 主备复制](#/c/mit-6.824-2020/lec/lec04?v=notes)、L5、[L6](#/c/mit-6.824-2020/lec/lec06?v=notes)–[L7 Raft](#/c/mit-6.824-2020/lec/lec07?v=notes) | [Lab 3 Raft A–D](#/c/mit-6.824-2020/lab/raft?v=zh) | 选举、日志匹配、提交、持久化与快照分别维护什么？ |
| 4 · 从日志到服务 | [L8 ZooKeeper](#/c/mit-6.824-2020/lec/lec08?v=notes)、[Updates · 实验衔接](#/c/mit-6.824-2020/lec/update-lab-bridge?v=notes) 的 RSM 部分 | [Lab 4 KV Raft A–C](#/c/mit-6.824-2020/lab/kvraft?v=zh) | Start 返回、日志提交、状态机应用、回复客户端有何区别？ |
| 5 · 分片闭环 | 实验衔接中的迁移部分；扩展阅读 [L12 事务](#/c/mit-6.824-2020/lec/lec12?v=notes)、[L13 Spanner](#/c/mit-6.824-2020/lec/lec13?v=notes) | [Lab 5 Sharded KV A–C](#/c/mit-6.824-2020/lab/shardkv?v=zh)，D 作为进阶 | 配置变更中，如何保持单一服务权并接续中断的迁移？ |

Lab 5 基础部分实现的是分片迁移与控制器协调；跨分片事务和 2PC 属于开放扩展方向。分片配置变更也不等于 Raft 集群成员变更。

做完实验主线后，优先补 L9 CRAQ、L10 Aurora、L11 Frangipani、L14 FaRM、L16 Memcached、L17 COPS；再按兴趣读 L15 Spark、L18 Certificate Transparency、L19 Bitcoin、L20 Blockstack 与 L21 的项目阅读。

## 固定版本与开发目录

实验仓库：`git://g.csail.mit.edu/6.5840-golabs-2026`。

本路线固定提交：

```text
513cac0aef010750fc74688da8a395974a83cf7a
```

该提交的作者与提交时间均为 `2026-02-13 16:36:14 -0500`，提交说明为 `update`；抓取日为 **2026-11-08**。官网实验页采用同日抓取的 Spring 2026 快照。网页修改日期与 Git 提交日期不同，接口对应关系以本次逐项核对为准。

Go 环境页要求 **Go 1.22 或更新版本**；固定提交的 `src/go.mod` 同样声明 `go 1.22`，模块名为 `6.5840`。

在你准备存放实验的目录执行：

```bash
git clone git://g.csail.mit.edu/6.5840-golabs-2026 6.5840
cd 6.5840
git switch -c study-2026 513cac0aef010750fc74688da8a395974a83cf7a
cd src
go version
```

五个实验共享 `study-2026` 工作分支，逐步积累实现；不是每个实验切换一个专用分支。实验页面标签中的 `513cac0aef01` 是共同的起始提交。官网要求学期内 `git pull` 以接收更新，而这里为了复现固定版本，采用上面的提交；以后确需升级时应同时更新代码、要求快照与映射。

源码与测试位置：

| 实验 | 主要实现入口（相对 `src/`） | 官方测试入口 |
|---|---|---|
| Lab 1 | `mr/coordinator.go`、`mr/worker.go`、`mr/rpc.go` | `mr/mr_test.go` |
| Lab 2 | `kvsrv1/client.go`、`server.go`、`kvsrv1/lock/lock.go` | `kvsrv1/kvsrv_test.go`、`kvsrv1/lock/lock_test.go` |
| Lab 3 | `raft1/raft.go`；公共接口在 `raftapi/raftapi.go` | `raft1/raft_test.go` |
| Lab 4 | `kvraft1/rsm/rsm.go`、`kvraft1/client.go`、`server.go` | `kvraft1/rsm/rsm_test.go`、`kvraft1/kvraft_test.go` |
| Lab 5 | `shardkv1/client.go`、`shardctrler/shardctrler.go`、`shardgrp/server.go` 与 `client.go` | `shardkv1/shardkv_test.go` |

### 正确的实验命令

**当前实验页的通用“常用命令”框仍带有 xv6 的 `make qemu`、`make grade`，不适用于本课程。请使用下表。** 以下命令均在实验仓库的 `src/` 下运行，Makefile 会先编译测试所需的程序，再进入对应包执行 Go 测试；默认启用 `-race`。

| 目标 | 命令 |
|---|---|
| Lab 1 全部测试 | `make mr` |
| Lab 2 KV / 锁 | `make kvsrv1`；`make lock1` |
| Lab 3 全部测试 | `make raft1` |
| Lab 3 单阶段（示例） | `make RUN="-run 3A" raft1`；将 `3A` 替换为 `3B`、`3C` 或 `3D` |
| Lab 4A | `make RUN="-run 4A" rsm1` |
| Lab 4B | `make RUN="-run 4B" kvraft1` |
| Lab 4C 的 RSM / KV 快照 | `make RUN="-run 4C" rsm1`；`make RUN="-run 4C" kvraft1` |
| Lab 4 全部测试 | `make rsm1`；`make kvraft1` |
| Lab 5 基础部分全部测试 | `make shardkv` |
| Lab 5 单阶段（示例） | `make RUN="-run 5A" shardkv`；也可筛选 `5B`、`5C` |

这些是供完成实现后使用的验收入口。初始骨架包含待实现函数，不能把下载、编译成功或教程产出当成实验通过。Lab 5D 要自行设计扩展和测试，没有一个通用的 `5D` 测试目标。

## 2020 → 2026 实验对照

| 2020 课内实验 | 本路线使用的 2026 实验 | 需要重新核对的地方 |
|---|---|---|
| Lab 1 MapReduce | Lab 1 MapReduce | socket 由参数显式传入；用 `make mr` 和 Go 测试，不能套旧 `test-mr.sh` 流程 |
| 无独立同名实验 | Lab 2 Key/Value Server + lock | `Get` 返回值与版本；`Put` 带版本；保留 `ErrMaybe` 的不确定性 |
| Lab 2 Raft | Lab 3 Raft A–D | `raft1` / `raftapi` / `tester1` 包；持久化与快照 API；D 为日志压缩 |
| Lab 3 KV Raft | Lab 4 KV Raft A–C | A 单独实现通用 RSM；B 使用版本化 KV；C 涉及 RSM 和服务快照 |
| Lab 4 Sharded KV | Lab 5 Sharded KV A–D | 控制器驱动 Freeze/Install/Delete；恢复与并发控制；D 开放扩展 |

这是主题对应，不表示旧实现、API 或测试兼容。

### 跨实验接口速查

- **MapReduce**：`MakeCoordinator(sockname, files, nReduce)`；`Worker(sockname, mapf, reducef)`。进程入口也接收 socket 参数，worker 必须连接指定协调器。
- **KV**：`Get(key) (string, rpc.Tversion, rpc.Err)`；`Put(key, value, version) rpc.Err`。版本匹配的 Put 才写入并递增版本；首次 RPC 得到 `ErrVersion` 表示没有执行，重发后得到它则可能需要返回 `ErrMaybe`。它不是“所有重试都可保证客户端知道恰好执行一次”的接口。
- **Raft**：`Start`、`GetState`、`Snapshot`、`PersistBytes`；提交与快照经 `raftapi.ApplyMsg` 交给上层。持久化对象的实际方法是 `tester1.Persister.Save(raftstate, snapshot)`，部分骨架注释残留的 `SaveStateAndSnapshot` 不是该提交的方法名。
- **RSM**：`Submit(req any) (rpc.Err, any)`；服务实现 `DoOp(any) any`、`Snapshot() []byte`、`Restore([]byte)`。Lab 4/5 复用这一层。
- **分片**：控制器提供 `InitConfig`、`Query`、`ChangeConfigTo`、`InitController`；分片组提供 `FreezeShard`、`InstallShard`、`DeleteShard`。迁移 RPC 带配置号 `Num`；KV 的版本号与配置号是不同概念。
- **依赖**：Lab 5 控制器使用 Lab 2 的 KV 存配置，分片组使用 Lab 4 的 RSM 与 Lab 3 的 Raft。把配置存储也改成复制 KV 是 Lab 5D 的一种扩展，不是基础骨架已经提供的能力。

## Updates 导航

| 条目 | 对应 2026 内容 | 与旧课的连接 |
|---|---|---|
| [线性一致性与版本化 KV](#/c/mit-6.824-2020/lec/update-linearizability?v=notes) | L8；Lab 2 | 实验桥接，Lab 2 前必读 |
| [RSM、KV 与分片实验衔接](#/c/mit-6.824-2020/lec/update-lab-bridge?v=notes) | Lab 2–5；编者导读，无独立讲次 | Lab 4/5 前分段阅读 |
| [Paxos](#/c/mit-6.824-2020/lec/update-paxos?v=notes) | L4 | 与 Raft 对照 |
| [Go 编程模式](#/c/mit-6.824-2020/lec/update-go-patterns?v=notes) | L5，Russ Cox | 在旧 L2/L5 后选读 |
| [链式复制](#/c/mit-6.824-2020/lec/update-chain-replication?v=notes) | L13，原始 Chain Replication | 与 L9 CRAQ 对照 |
| [分布式系统验证](#/c/mit-6.824-2020/lec/update-verification?v=notes) | L15，IronFleet | 从协议不变量走向形式化证明 |
| [AWS Lambda](#/c/mit-6.824-2020/lec/update-lambda?v=notes) | L17，On-demand Container Loading | 服务启动与按需加载 |
| [Ray](#/c/mit-6.824-2020/lec/update-ray?v=notes) | L18 | 与 L15 Spark 衔接 |
| [SUNDR](#/c/mit-6.824-2020/lec/update-sundr?v=notes) | L19 | 与 L18 的分叉一致性对照 |
| [实用拜占庭容错](#/c/mit-6.824-2020/lec/update-bft?v=notes) | L21，Practical BFT | 从崩溃故障拓展到恶意行为 |

2026 课表没有为这些条目提供视频链接，按书面材料入口登记；不使用 2020 视频替代。2026 L10 是 Raft 实验问答，作为 Lab 3 补充入口；2026 L22 项目展示不替换旧 L21。

## 共享阅读与术语

**MapReduce (2004)** 是 L1 与 Lab 1 共用的阅读，集中在 [L1 课程资料](#/c/mit-6.824-2020/lec/lec01?v=materials)自主精读：程序模型、故障语义、性能实验及与 2026 实验的差异。实验页仅展开实现要求与指导。

**Raft extended (2014)** 是 L6/L7 与 Lab 3/4 共用的主要阅读。L6 读至 §5 末，L7 读 §7 至末尾、跳过 §6；Lab 3 不实现成员变更，Lab 4 重点回看 §7。后续中文精读统一放在 [L6 课程资料](#/c/mit-6.824-2020/lec/lec06?v=materials)，其他条目引用其章节。

**Go** 的共同入口为 A Tour of Go、The Go Memory Model 和 Go 的 race detector 文档。旧课表中的在线链接可能指向更新后的版本；学习当前 Go 行为时应与所用工具链一致，不把当前页面文字视为 2020 原文。

**事务**使用 6.033 Chapter 9 的指定小节；**线性一致性**使用 Herlihy 与 Wing 论文至 §3.1。它们分别在 L12 和 Updates · 线性一致性的课程资料集中展开。

| 术语 | 阅读时区分什么 |
|---|---|
| replication / sharding | 复制同一份状态以容错 / 拆分数据以扩展容量与吞吐 |
| retry / at-most-once | 重新发送请求 / 对某次操作效果的约束 |
| linearizability | 每次已完成操作可视作在调用到返回之间的某一瞬间生效，并保留真实时间先后 |
| commit / apply | 协议确认日志可提交 / 状态机实际执行该条命令 |
| term / version / configuration number | Raft 任期 / 某个键的版本 / 分片配置的编号 |
| snapshot / persistence | 压缩后的应用状态 / 崩溃恢复所需的持久记录；两者要保持对应 |

## 引用与来源

### 版本与公共入口

- MIT 6.824 Spring 2020：[课表](http://nil.csail.mit.edu/6.824/2020/schedule.html)、[课程信息与教学人员](http://nil.csail.mit.edu/6.824/2020/general.html)。2020 授课教师登记为 Robert Morris；不把 2026 教师表回填到旧课。
- MIT 6.5840 Spring 2026：[课表](https://pdos.csail.mit.edu/6.824/schedule.html)、[课程信息](https://pdos.csail.mit.edu/6.824/general.html)、[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)。这些无年份路径按 2026-11-08 抓取快照固定。
- Go：[A Tour of Go](https://go.dev/tour/)、[The Go Memory Model](https://go.dev/ref/mem)、[Data Race Detector](https://go.dev/doc/articles/race_detector)。现代工具文档作为补充入口。
- 实验官方要求：[Lab 1](https://pdos.csail.mit.edu/6.824/labs/lab-mr.html)、[Lab 2](https://pdos.csail.mit.edu/6.824/labs/lab-kvsrv1.html)、[Lab 3](https://pdos.csail.mit.edu/6.824/labs/lab-raft1.html)、[Lab 4](https://pdos.csail.mit.edu/6.824/labs/lab-kvraft1.html)、[Lab 5](https://pdos.csail.mit.edu/6.824/labs/lab-shard1.html)。接口核对以官方仓库上述固定提交的源码和 Makefile 为准。

### 2020 主线阅读索引

以下为课表指定入口，不表示已取得全文翻译许可。完整讲义、视频入口、FAQ、问题页、日期和当年的实验发布日期关联，保存在仓库 `sources/schedule-inventory.json`。

| 讲次 | 指定阅读 |
|---|---|
| L1 | [MapReduce (2004)](http://nil.csail.mit.edu/6.824/2020/papers/mapreduce.pdf) |
| L2 | [Online Go tutorial](http://tour.golang.org/)；[crawler.go](http://nil.csail.mit.edu/6.824/2020/notes/crawler.go)、[kv.go](http://nil.csail.mit.edu/6.824/2020/notes/kv.go) |
| L3 | [GFS (2003)](http://nil.csail.mit.edu/6.824/2020/papers/gfs.pdf) |
| L4 | [Fault-Tolerant Virtual Machines (2010)](http://nil.csail.mit.edu/6.824/2020/papers/vm-ft.pdf) |
| L5 | [The Go Memory Model](https://golang.org/ref/mem)；[代码示例](http://nil.csail.mit.edu/6.824/2020/notes/go-concurrency.tar.gz) |
| L6–L7 | [Raft extended (2014)](http://nil.csail.mit.edu/6.824/2020/papers/raft-extended.pdf)；范围见共享阅读节 |
| L8 | [ZooKeeper (2010)](http://nil.csail.mit.edu/6.824/2020/papers/zookeeper.pdf) |
| L9 | [CRAQ (2009)](http://nil.csail.mit.edu/6.824/2020/papers/craq.pdf) |
| L10 | [Aurora (2017)](http://nil.csail.mit.edu/6.824/2020/papers/aurora.pdf) |
| L11 | [Frangipani](http://nil.csail.mit.edu/6.824/2020/papers/thekkath-frangipani.pdf) |
| L12 | [6.033 Chapter 9 所在教材](https://ocw.mit.edu/resources/res-6-004-principles-of-computer-system-design-an-introduction-spring-2009/online-textbook/)：§9.1.5、§9.1.6、§9.5.2、§9.5.3、§9.6.3 |
| L13 | [Spanner (2012)](http://nil.csail.mit.edu/6.824/2020/papers/spanner.pdf) |
| L14 | [FaRM (2015)](http://nil.csail.mit.edu/6.824/2020/papers/farm-2015.pdf) |
| L15 | [Spark (2012)](http://nil.csail.mit.edu/6.824/2020/papers/zaharia-spark.pdf) |
| L16 | [Memcached at Facebook (2013)](http://nil.csail.mit.edu/6.824/2020/papers/memcache-fb.pdf) |
| L17 | [COPS (2011)](http://nil.csail.mit.edu/6.824/2020/papers/cops.pdf) |
| L18 | [What is CT](https://www.certificate-transparency.org/what-is-ct)、[How CT works](https://www.certificate-transparency.org/how-ct-works)、[Transparent Logs](https://research.swtch.com/tlog)（跳过 Tiles 与附录） |
| L19 | [Bitcoin (2008)](http://nil.csail.mit.edu/6.824/2020/papers/bitcoin.pdf)、[Michael Nielsen 的协议说明](http://www.michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works) |
| L20 | [BlockStack (2017)](http://nil.csail.mit.edu/6.824/2020/papers/blockstack-2017.pdf) |
| L21 | [AnalogicFS experience paper](http://nil.csail.mit.edu/6.824/2020/papers/katabi-analogicfs.pdf) |

### 2026 增补入口

| 对应讲次 | 讲义与阅读 |
|---|---|
| L4 Paxos | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-paxos.txt)、[伪代码](https://pdos.csail.mit.edu/6.824/notes/paxos-code.html)、[Paxos Made Simple](https://pdos.csail.mit.edu/6.824/papers/paxos-simple.pdf) |
| L5 Go patterns | [Russ Cox 幻灯片](https://pdos.csail.mit.edu/6.824/notes/Go-MIT6824-2026.pdf)、[The Go Programming Language and Environment](https://cacm.acm.org/magazines/2022/5/260357-the-go-programming-language-and-environment/fulltext) |
| L8 线性一致性 | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-linearizability.txt)、[Linearizability](https://pdos.csail.mit.edu/6.824/papers/p463-herlihy.pdf)（至 §3.1） |
| L10 实验问答 | [Q&A Lab 3A+B](https://pdos.csail.mit.edu/6.824/notes/l-raft-QA.txt) |
| L13 Chain Replication | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-cr.txt)、[CR (2004)](https://pdos.csail.mit.edu/6.824/papers/cr-osdi04.pdf) |
| L15 验证 | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-ironfleet.txt)、[IronFleet (2015)](https://pdos.csail.mit.edu/6.824/papers/ironfleet.pdf) |
| L17 Lambda | [幻灯片](https://pdos.csail.mit.edu/6.824/notes/mbrooker_cs_slides_2026.pdf)、[On-demand Container Loading (2023)](https://pdos.csail.mit.edu/6.824/papers/atc23-brooker.pdf) |
| L18 Ray | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-ray.txt)、[Ray](https://pdos.csail.mit.edu/6.824/papers/ray.pdf)（课表标 2021） |
| L19 SUNDR | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-sundr.txt)、[SUNDR (2004)](https://pdos.csail.mit.edu/6.824/papers/li-sundr.pdf)（至 §3.3.2 末） |
| L21 BFT | [讲义](https://pdos.csail.mit.edu/6.824/notes/l-bft.txt)、[幻灯片](https://pdos.csail.mit.edu/6.824/notes/65840-pbft.pdf)、[Practical BFT (1999)](https://pdos.csail.mit.edu/6.824/papers/castro-practicalbft.pdf) |

归档文件位于本项目的 `content/mit-6.824-2020/sources/`，不作为站内 Markdown 页面发布：`manifest.json` 记录来源状态、抓取时间、SHA-256 与 Last-Modified；`version-map.json` 记录跨年对应与实验依赖；`lab-code-manifest.json` 记录固定代码树和已核对文件；`INTERFACE-AUDIT.txt` 记录接口核对结论。抓到文件不等于已精读，也不等于已完成中文内容。

2020 与 2026 官方课程首页均标注 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)，本批据此整理官方 L1 讲义与翻译 Lab 1 要求，不推广到外链论文和视频。MapReduce 论文使用自主中文精读。L1 视频元数据标示 Creative Commons Attribution；当前 YouTube 帮助页链接 CC BY 4.0，尚不能据此确定旧视频的具体许可版本。核对记录见 `sources/P1-REVIEW.txt`；本批没有发布视频译稿。
