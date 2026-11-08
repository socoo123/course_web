---
source: MIT 6.824 Spring 2021 官方课表与课程信息；MIT 6.5840 Spring 2026 官方课表、实验页与固定代码
status: 已切换 2021 讲次和视频入口；复用 P1 的 L1 书面笔记、论文精读与 2026 Lab 1 说明和指导。2021 字幕待用户提供，视频元数据与许可待核对；实验测试未运行。
license: 本页为编者自主导航；外链论文、视频、讲义与实验要求分别核实许可。
---

# 分布式系统：公共资料与学习路线

## 怎样学这门课

先把一个请求沿系统走一遍：客户端如何发出请求，服务器如何执行，回复丢失后怎么办；再增加副本，追问哪个节点可以决定执行顺序；最后把数据分片，追问迁移时谁有权服务。

这条路线贯穿五个实验：**MapReduce → 单机 KV 与锁 → Raft → 复制 KV → 分片 KV**。读论文时抓住问题、机制、不变量与故障情境；写实验时把不变量落实到状态、并发边界和测试。

- **课程与视频**：2021 年 6.824，保留官方 L1–L21 编号。L6、L8 是实验答疑，课表未列视频；L15 有上下两段；L21 是项目展示。
- **动手实验**：全部采用 2026 年 6.5840，同一个仓库与固定提交，逐步复用自己的实现。
- **Updates**：两项实验桥接与六项专题选读。Chain Replication、SUNDR 已在 2021 主线中，相关 2026 阅读入口归入对应讲次，不另设重复章节。
- **三种材料**：课程笔记提炼和推导；中文译稿整理真实课堂；课程资料承载课外阅读。共享材料集中在一处展开。

## 先走完五个实验

以下是编者建议的自学顺序；“核心 / 选读”、难度星级与实验工时不是 MIT 官方评价。

| 阶段 | 先读什么 | 动手目标 | 过关时应能解释 |
|---|---|---|---|
| 0 · Go 准备 | [L2 RPC 与线程](#/c/mit-6.824-2021/lec/lec02?v=notes)、按需提前读 [L10 Go 嘉宾课](#/c/mit-6.824-2021/lec/lec10?v=notes) | goroutine、channel、mutex/cond、RPC、race detector | 哪些状态被共享？锁保护哪个不变量？ |
| 1 · 调度与重试 | [L1 MapReduce](#/c/mit-6.824-2021/lec/lec01?v=notes)、L2 | [Lab 1 MapReduce](#/c/mit-6.824-2021/lab/mr?v=zh) | 慢 worker 与宕机为何难以区分？重派何时安全？ |
| 2 · RPC 语义 | [线性一致性](#/c/mit-6.824-2021/lec/update-linearizability?v=notes)、L2/L10 | [Lab 2 KV 与锁](#/c/mit-6.824-2021/lab/kvsrv?v=zh) | versioned Put、ErrVersion 与 ErrMaybe 的区别？ |
| 3 · 复制与共识 | [L3 GFS](#/c/mit-6.824-2021/lec/lec03?v=notes)、[L4 主备](#/c/mit-6.824-2021/lec/lec04?v=notes)、[L5](#/c/mit-6.824-2021/lec/lec05?v=notes) / [L7 Raft](#/c/mit-6.824-2021/lec/lec07?v=notes) | [Lab 3 Raft A–D](#/c/mit-6.824-2021/lab/raft?v=zh) | 选举、日志匹配、提交、持久化和快照维护什么？ |
| 4 · 从日志到服务 | [L9 ZooKeeper](#/c/mit-6.824-2021/lec/lec09?v=notes)、[实验衔接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)的 RSM 部分 | [Lab 4 KV Raft A–C](#/c/mit-6.824-2021/lab/kvraft?v=zh) | Start 返回、提交、应用与回复有何区别？ |
| 5 · 分片闭环 | 实验衔接中的迁移部分；扩展读 [L13 事务](#/c/mit-6.824-2021/lec/lec13?v=notes)、[L14 Spanner](#/c/mit-6.824-2021/lec/lec14?v=notes) | [Lab 5 Sharded KV A–C](#/c/mit-6.824-2021/lab/shardkv?v=zh)，D 为进阶 | 迁移中如何保持单一服务权，并恢复中断的配置变更？ |

Lab 5 基础部分实现分片迁移与控制器协调；跨分片事务和 2PC 属于开放扩展方向。分片配置变更不等于 Raft 成员变更。

完成实验主线后，继续 L11 链式复制、L12 Frangipani、L15 FaRM、L17 Memcached；按兴趣读 L16 Spark、L18 SUNDR、L19 Bitcoin、L20 Blockstack 和 L21 项目展示。

## 固定版本与开发目录

```bash
git clone git://g.csail.mit.edu/6.5840-golabs-2026 6.5840
cd 6.5840
git switch -c study-2026 513cac0aef010750fc74688da8a395974a83cf7a
cd src
go version
```

要求 **Go 1.22 或更新版本**；固定提交的 `src/go.mod` 声明 `go 1.22`，模块名 `6.5840`。该提交作者与提交时间为 `2026-02-13 16:36:14 -0500`，提交说明 `update`。官网实验页使用 2026-11-08 快照；接口以已核对的代码与页面为准。

五个实验共享 `study-2026` 工作分支，不逐实验切换分支。官网建议学期内拉取更新，而本路线固定提交以便复现；升级时应同时更新代码、要求快照与映射。

### 实现入口与验收

**实验页通用命令框中的 `make qemu`、`make grade` 不适用于本课程。** 下列命令全部在实验仓库 `src/` 中执行；Makefile 先构建必要程序，再运行默认带 `-race` 的 Go 测试。

| 实验 | 实现入口（相对 `src/`） | 命令 / 测试位置 |
|---|---|---|
| Lab 1 | `mr/{coordinator,worker,rpc}.go` | `make mr`；`mr/mr_test.go` |
| Lab 2 | `kvsrv1/{client,server}.go`、`kvsrv1/lock/lock.go` | `make kvsrv1`、`make lock1`；`kvsrv1/kvsrv_test.go`、`kvsrv1/lock/lock_test.go` |
| Lab 3 | `raft1/raft.go`、接口 `raftapi/raftapi.go` | `make raft1`；`raft1/raft_test.go` |
| Lab 4 | `kvraft1/rsm/rsm.go`、`kvraft1/{client,server}.go` | `make rsm1`、`make kvraft1`；各包的测试文件 |
| Lab 5 | `shardkv1/client.go`、`shardctrler/shardctrler.go`、`shardgrp/{server,client}.go` | `make shardkv`；`shardkv1/shardkv_test.go` |

单阶段示例：`make RUN="-run 3A" raft1`，按需替换为 `3B` / `3C` / `3D`。Lab 4A 用 `make RUN="-run 4A" rsm1`，4B 用 `make RUN="-run 4B" kvraft1`，4C 分别对 `rsm1` 与 `kvraft1` 筛选。Lab 5 可用 `make RUN="-run 5A" shardkv`，替换为 `5B` / `5C`；5D 自行设计测试，没有通用 `5D` 目标。

这些是实现后的验收入口；取得骨架、编译成功和教程产出均不代表实验通过。

## 2021 → 2026 实验对照

| 2021 课内实验 | 本路线 2026 实验 | 接口变化 |
|---|---|---|
| Lab 1 MapReduce | Lab 1 MapReduce | socket 显式传参；使用 `make mr`，不套旧 `test-mr.sh` |
| 无独立同名实验 | Lab 2 KV Server + lock | 版本化 Get/Put、ErrMaybe |
| Lab 2 Raft | Lab 3 Raft A–D | `raft1` / `raftapi` / `tester1`；D 为日志压缩 |
| Lab 3 KV Raft | Lab 4 KV Raft A–C | A 通用 RSM；B 版本化 KV；C 双层快照 |
| Lab 4 Sharded KV | Lab 5 Sharded KV A–D | 控制器驱动迁移、恢复与并发；D 开放扩展 |

此表仅表示主题对应，不表示旧代码和测试兼容。2021 L6/L8 答疑讨论当年 Lab 1 / Lab 2 A+B，学习时需对照新版要求。

### 跨实验接口速查

- **MapReduce**：`MakeCoordinator(sockname, files, nReduce)`；`Worker(sockname, mapf, reducef)`。进程入口也接收 socket 参数。
- **KV**：`Get(key) (string, rpc.Tversion, rpc.Err)`；`Put(key, value, version) rpc.Err`。版本匹配才写入并递增；首次 RPC 得到 ErrVersion 表示未执行，重发后则可能应返回 ErrMaybe。
- **Raft**：`Start`、`GetState`、`Snapshot`、`PersistBytes`；经 `raftapi.ApplyMsg` 交付。持久化方法是 `tester1.Persister.Save(raftstate, snapshot)`，骨架旧注释中的 `SaveStateAndSnapshot` 不是该提交的方法名。
- **RSM**：`Submit(req any) (rpc.Err, any)`；服务实现 `DoOp(any)`、`Snapshot()`、`Restore([]byte)`，Lab 4/5 复用。
- **分片**：控制器提供 `InitConfig`、`Query`、`ChangeConfigTo`、`InitController`；分片组提供 `FreezeShard`、`InstallShard`、`DeleteShard`。迁移配置号 `Num` 与键版本号不同。
- **依赖**：Lab 5 控制器用 Lab 2 KV 存配置，分片组用 Lab 4 RSM 与 Lab 3 Raft。把配置存储也改成复制 KV 是 5D 扩展之一。

## Updates 与共享阅读

| 条目 | 对应 2026 内容 | 学习连接 |
|---|---|---|
| [线性一致性](#/c/mit-6.824-2021/lec/update-linearizability?v=notes) | L8、Lab 2 | KV 与锁之前必读 |
| [RSM、KV 与分片衔接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes) | Lab 2–5；编者导读 | Lab 4/5 前分段阅读 |
| [Paxos](#/c/mit-6.824-2021/lec/update-paxos?v=notes) | L4 | 对照 L5/L7 Raft |
| [Go 模式](#/c/mit-6.824-2021/lec/update-go-patterns?v=notes) | L5 Russ Cox | L2/L10 后核对差异 |
| [验证](#/c/mit-6.824-2021/lec/update-verification?v=notes) | L15 IronFleet | 从不变量走向证明 |
| [AWS Lambda](#/c/mit-6.824-2021/lec/update-lambda?v=notes) | L17 | 按需加载 |
| [Ray](#/c/mit-6.824-2021/lec/update-ray?v=notes) | L18 | 与 L16 Spark 衔接 |
| [实用拜占庭容错](#/c/mit-6.824-2021/lec/update-bft?v=notes) | L21 | 从崩溃故障到恶意行为 |

2026 课表没有为这些条目列视频；按书面材料制作。2026 L13 Chain Replication 的讲义与论文归入 2021 L11 的阅读对照；2026 L19 SUNDR 归入 2021 L18。2026 L10 Raft 问答作为 Lab 3 的补充入口。

**MapReduce (2004)** 由 [L1 课程资料](#/c/mit-6.824-2021/lec/lec01?v=materials)集中精读。**Raft extended (2014)** 由 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)集中展开：L5 读至 §5 末，L7 读 §7 至末、跳过 §6；Lab 3 不实现成员变更，Lab 4 回看快照。**事务**指定章节放 L13，**线性一致性**论文至 §3.1 放对应 Updates。

Go 的共享工具入口为 A Tour of Go、The Go Memory Model、race detector 文档；动态网页应对照所用工具链，不当作 2021 原文。阅读时区分 replication / sharding、retry / at-most-once、commit / apply、term / version / configuration number，以及 snapshot / persistence。

## 引用与来源

### 课程与视频

- MIT 6.824 Spring 2021：[官方课表](http://nil.csail.mit.edu/6.824/2021/schedule.html)、[课程信息](http://nil.csail.mit.edu/6.824/2021/general.html)。课程讲师 Frans Kaashoek；L10 嘉宾 Russ Cox。
- L1：[2021 视频](https://www.youtube.com/watch?v=WtZ7pcRSkOA)。字幕与后续时间轴以该视频为准。
- L15 FaRM：[上半场](https://www.youtube.com/watch?v=07xsfL5E8Ck)、[续集](https://www.youtube.com/watch?v=XwU4jKhBxws)。译稿须分别保留两段的时间轴。
- 全部视频入口来自官方课表；登记见 `sources/schedule-inventory-2021.json`，视频标题、时长、频道与许可尚需逐条核对。

### 2021 指定阅读入口

| 讲次 | 指定阅读或课堂材料 |
|---|---|
| L1 | [MapReduce (2004)](http://nil.csail.mit.edu/6.824/2021/papers/mapreduce.pdf) |
| L2 | [Go tutorial](http://tour.golang.org/)、[crawler.go](http://nil.csail.mit.edu/6.824/2021/notes/crawler.go)、[kv.go](http://nil.csail.mit.edu/6.824/2021/notes/kv.go)、[vote examples](http://nil.csail.mit.edu/6.824/2021/notes/condvar.tar.gz) |
| L3 | [GFS (2003)](http://nil.csail.mit.edu/6.824/2021/papers/gfs.pdf) |
| L4 | [Fault-Tolerant Virtual Machines (2010)](http://nil.csail.mit.edu/6.824/2021/papers/vm-ft.pdf) |
| L5 / L7 | [Raft extended (2014)](http://nil.csail.mit.edu/6.824/2021/papers/raft-extended.pdf) |
| L6 / L8 | 实验答疑，课表无指定论文、讲义或录像 |
| L9 | [ZooKeeper (2010)](http://nil.csail.mit.edu/6.824/2021/papers/zookeeper.pdf) |
| L10 | [Russ Cox 幻灯片](https://swtch.com/mit-6824-go-2021.pdf) |
| L11 | [Chain Replication (2004)](http://nil.csail.mit.edu/6.824/2021/papers/cr-osdi04.pdf) |
| L12 | [Frangipani](http://nil.csail.mit.edu/6.824/2021/papers/thekkath-frangipani.pdf) |
| L13 | [6.033 Chapter 9](https://ocw.mit.edu/resources/res-6-004-principles-of-computer-system-design-an-introduction-spring-2009/online-textbook/)：§9.1.5、§9.1.6、§9.5.2、§9.5.3、§9.6.3 |
| L14 | [Spanner (2012)](http://nil.csail.mit.edu/6.824/2021/papers/spanner.pdf) |
| L15 | [FaRM (2015)](http://nil.csail.mit.edu/6.824/2021/papers/farm-2015.pdf) |
| L16 | [Spark (2012)](http://nil.csail.mit.edu/6.824/2021/papers/zaharia-spark.pdf) |
| L17 | [Memcached (2013)](http://nil.csail.mit.edu/6.824/2021/papers/memcache-fb.pdf) |
| L18 | [SUNDR (2004)](http://nil.csail.mit.edu/6.824/2021/papers/li-sundr.pdf)，课表范围原文：until Section 3.4 |
| L19 | [Bitcoin (2008)](http://nil.csail.mit.edu/6.824/2021/papers/bitcoin.pdf)、[Michael Nielsen 协议说明](http://www.michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works) |
| L20 | [BlockStack (2016)](http://nil.csail.mit.edu/6.824/2021/papers/blockstack-atc16.pdf) |
| L21 | [AnalogicFS experience paper](http://nil.csail.mit.edu/6.824/2021/papers/katabi-analogicfs.pdf) |

### 实验与新版补充

- MIT 6.5840 Spring 2026：[课表](https://pdos.csail.mit.edu/6.824/schedule.html)、[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)；无年份 URL 以 2026-11-08 快照固定。
- 实验要求：[Lab 1](https://pdos.csail.mit.edu/6.824/labs/lab-mr.html)、[Lab 2](https://pdos.csail.mit.edu/6.824/labs/lab-kvsrv1.html)、[Lab 3](https://pdos.csail.mit.edu/6.824/labs/lab-raft1.html)、[Lab 4](https://pdos.csail.mit.edu/6.824/labs/lab-kvraft1.html)、[Lab 5](https://pdos.csail.mit.edu/6.824/labs/lab-shard1.html)。
- Go：[Tour](https://go.dev/tour/)、[Memory Model](https://go.dev/ref/mem)、[Race Detector](https://go.dev/doc/articles/race_detector)。
- 新版讲义：[Paxos](https://pdos.csail.mit.edu/6.824/notes/l-paxos.txt)、[Go patterns](https://pdos.csail.mit.edu/6.824/notes/Go-MIT6824-2026.pdf)、[线性一致性](https://pdos.csail.mit.edu/6.824/notes/l-linearizability.txt)、[Raft 问答](https://pdos.csail.mit.edu/6.824/notes/l-raft-QA.txt)、[Chain Replication](https://pdos.csail.mit.edu/6.824/notes/l-cr.txt)、[验证](https://pdos.csail.mit.edu/6.824/notes/l-ironfleet.txt)、[Lambda](https://pdos.csail.mit.edu/6.824/notes/mbrooker_cs_slides_2026.pdf)、[Ray](https://pdos.csail.mit.edu/6.824/notes/l-ray.txt)、[SUNDR](https://pdos.csail.mit.edu/6.824/notes/l-sundr.txt)、[BFT](https://pdos.csail.mit.edu/6.824/notes/l-bft.txt)。论文入口见各讲元数据与官方课表。

### 归档与复用说明

归档位于 `content/mit-6.824-2021/sources/`。`schedule-inventory-2021.json` 与 `version-map-2021.json` 记录当前讲次、视频和映射；`manifest-2021.json` 记录本次抓取。无 `-2021` 后缀的原 manifest、inventory、version-map 保留为 P0/P1 的历史记录，不能用于当前编号。

L1 书面笔记仍明确引用实际读过的 2020 讲义；论文精读仍使用 P1 阅读的 13 页 OSDI 2004 快照。两者是复用的书面学习材料，不代表已覆盖 2021 课堂。P1 对 2020 视频的 HTTP 429、79:35 时长与 CC 标签不适用于新的 2021 视频。详细历史许可与来源见 `sources/P1-REVIEW.txt`；2026 Lab 1 中译保留课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名与修改说明。
