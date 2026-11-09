---
source: MIT 6.824 Spring 2021 官方课表与课程信息；MIT 6.5840 Spring 2026 官方课表、实验页与固定代码
status: P6 内容完成：新增 2021 L11/L12/L15/L17 共 12 份正文，L15 两条录像分别保留时间轴，2026 链式复制阅读已并入 L11。来源和实际阅读范围见页底各批审阅记录；实验测试未运行。
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
| 5 · 分片闭环 | [实验衔接 §9–15](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)；扩展读 [L13 事务](#/c/mit-6.824-2021/lec/lec13?v=notes)、[L14 Spanner](#/c/mit-6.824-2021/lec/lec14?v=notes) | [Lab 5 Sharded KV A–C](#/c/mit-6.824-2021/lab/shardkv?v=zh)，D 为官方开放扩展、路线进阶项 | 迁移中如何保持单一服务权，并恢复中断的配置变更？ |

Lab 5 基础部分实现分片迁移与控制器协调；跨分片事务和 2PC 属于开放扩展方向。分片配置变更不等于 Raft 成员变更。

## 用四个案例检验不变量

完成实验主线后，把“谁有权服务、何时可见、失败后凭什么继续”带到四个系统里：

| 案例 | 先问的问题 | 与实验主线的连接 |
|---|---|---|
| [L11 链式复制](#/c/mit-6.824-2021/lec/lec11?v=notes) | 写入沿链前进时，为什么读尾节点；故障重配后如何保持顺序？ | 对照 Raft 多数提交与分片迁移中的服务权交接 |
| [L12 Frangipani](#/c/mit-6.824-2021/lec/lec12?v=notes) | 把锁交给下一台文件服务器以前，脏缓存和日志分别要满足什么条件？ | 将互斥、缓存新鲜度、持久恢复分开推理 |
| [L15 FaRM](#/c/mit-6.824-2021/lec/lec15?v=notes) | 不在执行期锁住所有读，提交前怎样排除冲突并保证故障后统一决定？ | 在 L13 事务与 L14 Spanner 之后比较 OCC、复制和原子提交 |
| [L17 Memcached](#/c/mit-6.824-2021/lec/lec17?v=notes) | 数据库已更新，为什么缓存还会变旧；谁有资格回填？ | 区分缓存失效、回填许可与复制 KV 的线性一致性契约 |

这些案例用于分析设计取舍；2026 实验接口仍以固定代码和实验指导为准。随后可按兴趣学习 L16 Spark、L18 SUNDR、L19 Bitcoin、L20 Blockstack 和 L21 项目展示。

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
| [RSM、KV 与分片衔接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes) | Lab 2–5；编者导读 | RSM、版本化 KV、快照，以及冻结／安装／删除、控制器恢复与并发目标选择 |
| [Paxos](#/c/mit-6.824-2021/lec/update-paxos?v=notes) | L4 | 对照 L5/L7 Raft |
| [Go 模式](#/c/mit-6.824-2021/lec/update-go-patterns?v=notes) | L5 Russ Cox | L2/L10 后核对差异 |
| [验证](#/c/mit-6.824-2021/lec/update-verification?v=notes) | L15 IronFleet | 从不变量走向证明 |
| [AWS Lambda](#/c/mit-6.824-2021/lec/update-lambda?v=notes) | L17 | 按需加载 |
| [Ray](#/c/mit-6.824-2021/lec/update-ray?v=notes) | L18 | 与 L16 Spark 衔接 |
| [实用拜占庭容错](#/c/mit-6.824-2021/lec/update-bft?v=notes) | L21 | 从崩溃故障到恶意行为 |

2026 课表没有为这些条目列视频；按书面材料制作。2026 L13 Chain Replication 的讲义差异集中于 [L11 课程资料 §7](#/c/mit-6.824-2021/lec/lec11?v=materials)，两年论文快照字节相同，论文只精读一次；2026 L19 SUNDR 归入 2021 L18。2026 L10 Raft 问答作为 Lab 3 的补充入口。

**MapReduce (2004)** 由 [L1 课程资料](#/c/mit-6.824-2021/lec/lec01?v=materials)集中精读。**Raft extended (2014)** 由 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)集中展开：L5 读至 §5 末，L7 读 §7 至末、跳过 §6；L7 不再建第二份论文正文。Lab 3 不实现成员变更，Lab 4 回看快照。论文的请求编号去重与免日志读是阅读主题，2026 实验仍以版本化 Put、实际索引和恢复契约为准。**事务**指定章节放 L13，**线性一致性**论文至 §3.1 放对应 Updates。

Go 的共享工具入口为 A Tour of Go、The Go Memory Model、race detector 文档；动态网页应对照所用工具链，不当作 2021 原文。L2 的 Go Tour 是共享入门入口，不在各讲重复翻译；L2 讲义／代码与 L10 幻灯片均随课堂译稿走读，不再制作重复的 materials 标签。

排查并发时，先用 `-race` 检查实际执行中的冲突访问；观察阻塞可看 goroutine 栈。在 Unix 上 `Ctrl-\` 会让程序打印栈并退出；导入 `net/http/pprof` 的 HTTP 服务可通过 `/debug/pprof/goroutine` 查看在线栈。具体模式见 [L10](#/c/mit-6.824-2021/lec/lec10?v=notes)。Go 1.22 循环变量和 Go 1.23 timer 的变化均在该讲标注，不将 2021 经验直接当作所有新版本语义。

阅读时区分 replication / sharding、retry / at-most-once、commit / apply、term / version / configuration number，以及 snapshot / persistence。先完成 [Lab 2 的可靠 KV 与锁](#/c/mit-6.824-2021/lab/kvsrv?v=guide)，再加入重试与 ErrMaybe；一致性定义在 Updates，具体实现思路在实验指导。

## 引用与来源

### 课程与视频

- MIT 6.824 Spring 2021：[官方课表](http://nil.csail.mit.edu/6.824/2021/schedule.html)、[课程信息](http://nil.csail.mit.edu/6.824/2021/general.html)。课程讲师 Frans Kaashoek；L10 嘉宾 Russ Cox。
- L1：[2021 视频](https://www.youtube.com/watch?v=WtZ7pcRSkOA)。字幕与后续时间轴以该视频为准。
- L15 FaRM：[上半场](https://www.youtube.com/watch?v=07xsfL5E8Ck)、[续集](https://www.youtube.com/watch?v=XwU4jKhBxws)。译稿须分别保留两段的时间轴。
- 全部视频入口来自官方课表；登记见 `sources/schedule-inventory-2021.json`。下列视频分别查询元数据，频道均为 MIT 6.824: Distributed Systems，各自均标注 CC Attribution（具体版本未明确）：

| 条目 | 实际视频标题 | 时长 / 上传日 | 已获取英文自动字幕 |
|---|---|---|---|
| L1 | Lecture 1: Introduction | 79:08 / 2021-02-16 | 1906 条 |
| [L2](https://www.youtube.com/watch?v=oZR76REwSyA) | Lecture 2: RPC and Threads | 67:07 / 2021-02-18 | 1898 条 |
| [L3](https://www.youtube.com/watch?v=6ETFk1-53qU) | Lecture 3: GFS | 66:17 / 2021-02-23 | 1860 条 |
| [L4](https://www.youtube.com/watch?v=gXiDmq1zDq4) | Lecture 4: Primary-Backup Replication | 93:00 / 2021-02-25 | 2484 条，含课后问答 |
| [L5](https://www.youtube.com/watch?v=R2-9bsKmEbo) | Lecture 5: Fault Tolerance: Raft (1) | 99:22 / 2021-03-02 | 2426 条 |
| [L7](https://www.youtube.com/watch?v=h3JiQ_lnkE8) | Lecture 7: Fault Tolerance: Raft (2) | 108:46 / 2021-03-11 | 2732 条 |
| [L9](https://www.youtube.com/watch?v=HYTDDLo2vSE) | Lecture 9: Zookeeper | 82:50 / 2021-03-18 | 2239 条，含课后问答 |
| [L10](https://www.youtube.com/watch?v=IdCbMO0Ey9I) | Lecture 10: Guest Lecture on Go: Russ Cox | 95:27 / 2021-03-25 | 3145 条，含课后问答 |
| [L11](https://www.youtube.com/watch?v=1uUcW-Mqg5o) | Lecture 11: Chain Replication | 94:19 / 2021-03-30 | 2360 条，36 段译述 |
| [L12](https://www.youtube.com/watch?v=jPrUxfIcWWs) | Lecture 12: Cache Consistency: Frangipani | 87:58 / 2021-04-06 | 2198 条，33 段译述 |
| [L13](https://www.youtube.com/watch?v=B6btpukqHpM) | Lecture 13: Distributed Transactions | 81:29 / 2021-04-08 | 1893 条，含课后问答 |
| [L14](https://www.youtube.com/watch?v=ZulDvY429B8) | Lecture 14: Spanner | 97:09 / 2021-04-15 | 2326 条，含课后问答 |
| [L15 第一条](https://www.youtube.com/watch?v=07xsfL5E8Ck) | Lecture 15: Optimistic Concurrency Control (FaRM) | 94:37 / 2021-04-27 | 2459 条，33 段译述 |
| [L15 续集](https://www.youtube.com/watch?v=XwU4jKhBxws) | Lecture 15 continued: Optimistic Concurrency Control (FaRM) pt. 2 | 27:57 / 2021-04-30 | 711 条，12 段独立时间轴 |
| [L17](https://www.youtube.com/watch?v=eYZg0YJtFEE) | Lecture 17: Cache Consistency: Memcached at Facebook | 104:15 / 2021-05-04 | 2535 条，38 段译述 |

均保存并完整阅读英文自动字幕，未逐段回听或核对视频画面。L2/L3 分组讨论不在上传录像中；L4 的 42:18–50:00、L5 的 64:07–72:10 与 L7 的 61:16–69:32 保留分组活动及零散会务区间，无法恢复分组技术讨论。L4 末句未完成；L7 开头六秒无字幕，不据此断定静音。L5/L7 的提交判断、任期字段、批处理与匹配索引争论，以及 L10 幻灯片代码笔误，均在译稿单列校注。其余视频标题、时长、频道和许可仍待逐条核对。

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
- Go 版本校注：[Go 1.22 语言变更](https://go.dev/doc/go1.22)、[Go 1.23 Timer Channel Changes](https://go.dev/wiki/Go123Timer)，已针对循环变量与 timer 回收规则读取；不等于已通读所有 Go 文档。
- 线性一致性共享阅读：[论文](https://pdos.csail.mit.edu/6.824/papers/p463-herlihy.pdf)至 §3.1、[FAQ](https://pdos.csail.mit.edu/6.824/papers/linearizability-faq.txt)，分别集中于 Updates 的课程资料与笔记。
- 新版讲义：[Paxos](https://pdos.csail.mit.edu/6.824/notes/l-paxos.txt)、[Go patterns](https://pdos.csail.mit.edu/6.824/notes/Go-MIT6824-2026.pdf)、[线性一致性](https://pdos.csail.mit.edu/6.824/notes/l-linearizability.txt)、[Raft 问答](https://pdos.csail.mit.edu/6.824/notes/l-raft-QA.txt)、[Chain Replication](https://pdos.csail.mit.edu/6.824/notes/l-cr.txt)、[验证](https://pdos.csail.mit.edu/6.824/notes/l-ironfleet.txt)、[Lambda](https://pdos.csail.mit.edu/6.824/notes/mbrooker_cs_slides_2026.pdf)、[Ray](https://pdos.csail.mit.edu/6.824/notes/l-ray.txt)、[SUNDR](https://pdos.csail.mit.edu/6.824/notes/l-sundr.txt)、[BFT](https://pdos.csail.mit.edu/6.824/notes/l-bft.txt)。论文入口见各讲元数据与官方课表。

### 归档与复用说明

归档位于 `content/mit-6.824-2021/sources/`。`schedule-inventory-2021.json` 与 `version-map-2021.json` 记录当前讲次、视频和映射；`manifest-2021.json` 及其 `source_fragments` 记录逐来源获取与审阅。无 `-2021` 后缀的原 manifest、inventory、version-map 保留为 P0/P1 的历史记录，不能用于当前编号。

L1 中文译稿按 2021 英文自动字幕的真实时间顺序整理，课堂问答与书面材料的差异单列校注；笔记已对照 2021 讲义并保留实际使用过的 2020 讲义出处。论文精读使用 P1 阅读的 13 页 OSDI 2004 快照，课上展开的词频例子与基本流程转向译稿，不重复铺陈。当前校订记录见 `sources/L1-2021-REVIEW.txt`。

P1 对 2020 视频的 HTTP 429、79:35 时长与 CC 标签仅为历史记录，不能用于 2021 视频。详细历史许可与来源见 `sources/P1-REVIEW.txt`；2026 Lab 1 中译保留课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名与修改说明。

P2 记录见 `sources/P2-REVIEW.txt`：2021 L2/L10 原始字幕与独立元数据、2021 课堂代码／幻灯片快照、2026 线性一致性论文第 1–9 页，以及固定提交的 Lab 2 接口／测试静态阅读。Lab 2 要求中译沿用 2026 课程网站 CC BY 3.0 US 署名；论文与外链幻灯片不套用网站许可。内容完成不表示实验通过。

P3 记录见 `sources/P3-REVIEW.txt` 和各 `sources/p3-*/review.txt`。GFS 论文完整 15 页、VM-FT 论文完整 10 页，Raft 扩展论文按指定范围跳过 §6；图表实际核对，引用文献的外链全文不算已读。2021 链接的 L3/L4/L5/L7 讲义内部仍写 2020；L4 讲义与 L5 FAQ 的快照修改时间晚于对应课堂，L7 讲义／FAQ 与视频上传同日，但无法判断课前课后，保留这些史料边界。Lab 3 采用固定提交的 `raftapi`、`Persister.Save` 与应用层先恢复快照的契约；说明与指导均基于静态核对，未运行实验。原始字幕、PDF、HTML 和源码归档按既有约定留在本地，提交包含正文、来源清单与审阅记录。

P4 的实验及桥接记录见 `sources/P4-REVIEW.txt`、`sources/p4-lab4/review.txt`。Lab 4 沿用固定提交的 `StateMachine.DoOp/Snapshot/Restore`、`Submit` 与版本化 Get/Put，区分提交、应用、回复和客户端不确定性；快照恢复复用 P3 契约。P4 完成 RSM 桥接，迁移部分在 P5 接续；测试入口已核对，但实验测试未运行。

L9 的 2239 条字幕全部文本阅读，32 段译稿覆盖 82:50，包含课后问答；字幕区间并集有 147 处间隙（含开头 0.719 秒），不推断为静音，末条超时 2.159 秒保留，无音画核验。ZooKeeper 论文完整 14 页及全部 8 图、3 表已读／查看；未获全译许可，采用自主精读。2021 链接讲义仍写 2020 L8；课堂明确推迟锁配方，配方只在课程资料展开，不补入时间轴。详情见 `sources/p4-lec09/review.txt`。

P5 分片实验与迁移桥接见 `sources/P5-REVIEW.txt`、`sources/p5-lab5/review.txt`、`sources/p5-bridge/review.txt`。完整阅读 Lab 5 官方页 807 行与 20 个固定源码文件，静态核对接口和测试；A–C 全部要求与指导、D 六项官方开放扩展均已整理。网页快照修改于 2026-04-23，晚于固定提交；冻结后的 Get/Put 边界、测试名笔误、5D 旧启动提示及回归需额外覆盖 `rsm1` 均已校注。实验测试和 Go 编译未运行，来源中已有的示例通过输出不代表本次执行结果。

L13 的全部 1893 条字幕整理为 29 段；开头 0.560 秒无字幕，末条超时 1.560 秒。136 处字幕并集间隙共 661.492 秒，其中 37:37.839–44:07.119 为分组期间无字幕。L14 的全部 2326 条字幕整理为 36 段；160 处间隙共 650.364 秒，末尾 1.160 秒无字幕，约 46:24–53:43 分组／会议切换不能恢复组内讨论。两讲均只做文本阅读，未听音轨或核验课堂画面；不将字幕空隙断定为静音。

L13 指定 Chapter 9 五节与对应图表／公式页、2022 官方 Part II 勘误已读；没有通读全章 118 页。旧 OCW 入口出现重定向循环，实际使用[当前官方教材入口](https://ocw.mit.edu/courses/res-6-004-principles-of-computer-system-design-an-introduction-spring-2009/pages/online-textbook/)的 v5.0 PDF，不声称与 2021 字节一致；教材 PDF 自身为 CC BY-NC-SA 3.0 US，相关改写遵循该许可。2022 勘误属于后续核对。L14 Spanner 论文 14 页含附录 A、全部 6 图和 6 表已审阅，全文翻译许可未确认，采用自主精读。两讲讲义／FAQ 全文已读；L13 讲义／FAQ 修改于 2021-04-09，L14 讲义修改于 2021-04-30，均晚于对应视频上传日。详细边界见 `sources/p5-lec13/review.txt`、`sources/p5-lec14/review.txt`。

P6 四讲见 `sources/P6-REVIEW.txt` 和各 `sources/p6-lecNN/review.txt`：五条录像的 10263 条英文字幕均按序文本阅读，整理为 152 段，包含可恢复的课后问答。L15 首条 00:00–94:37，续集另从 00:00–27:57；续集上传日不等于已核实拍摄日。没有音轨或课堂画面核验。

| P6 录像 | 字幕并集间隙 | 原始末条超时 | 真实缺口 |
|---|---|---|---|
| L11 | 124 处，共 725.411 秒 | 0.840 秒 | 40:00–49:07 分组／返回期间讨论不能恢复 |
| L12 | 147 处，共 653.148 秒 | 1.920 秒 | 约 66 分钟至 72:21.840 的分组讨论不能恢复 |
| L15 第一条 | 156 处，共 301.245 秒 | 2.120 秒 | 课堂明确跳过分组；未虚构分组区间 |
| L15 续集 | 48 处，共 93.038 秒 | 1.640 秒 | 开头 4.319 秒无字幕；只读验证／盲写追问未得到完整现场回答 |
| L17 | 180 处，共 697.737 秒 | 1.800 秒 | 63:04–69:03 只有零星字幕，不能恢复组内讨论 |

这些间隙不是静音检测；原始字幕时间保留，未裁掉超时来制造“全段无超时”。四篇论文完整阅读 14／14／17／14 页，全部图表由各讲 worker 实际查看；主审完整阅读中文成品并定点核对原始来源，具体范围分开记录。论文全文翻译许可均未确认，课程资料采用自主中文精读；外链文献正文、现代实现和实验没有因此记为已读或已运行。

L11 的 2021 课表未列 FAQ，讲义内部保留 2020 标题；已有 2026 讲义全文及差异已读，两年论文 SHA-256 相同。L12 讲义与 L17 讲义／FAQ 的修改日与授课日相同，无法断定课前课后；L15 讲义修改于 2021-05-04、FAQ 修改于 2021-04-30，晚于首录像上传日。旧尾节点的服务权、Frangipani 迟到写、FaRM 恢复证据与 Memcache marker 的限制在各讲明确说明，不把后续阅读或编者分析补成课堂已说过的话。
