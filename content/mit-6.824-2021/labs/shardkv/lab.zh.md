---
source: MIT 6.5840 Spring 2026 Lab 5；官方页 2026-11-08 快照；代码固定 513cac0aef010750fc74688da8a395974a83cf7a
license: MIT 6.5840 课程实验文字，CC BY 3.0 US；本页为中文翻译、编排及明确标注的校注。
status: 完整阅读官方 HTML 807 行，覆盖 A–C 全部要求、提示与测试入口；D 单列官方开放扩展。源码与测试仅静态阅读，未运行实验。
---

# Lab 5：分片键值服务

## 1. 实验目标与系统组成

你将把键划分到多个由 Raft 复制的键值服务器组（`shardgrp`）上。一个分片是键值对的一个子集；例如可以想象按首字母划分，但本实验实际使用给定的 `Key2Shard()`。每组只处理部分分片，各组并行工作，从而让总吞吐量随组数增加。

系统包含以下部分：

- **分片组**：保存键值数据，通过 Lab 4 的 RSM 和所用 Raft 实现复制。
- **系统 Clerk**：向应用提供 `Get` 与版本化 `Put`，先查询配置，找到某个键所属分片的服务组，再访问该组。
- **配置 KV**：使用你在 Lab 2 实现的 `kvsrv` 保存配置。配置描述“分片 → 分片组”和“分片组 → 服务器列表”。
- **控制器**：管理员（这里是测试器）启动的另一个客户端。它通过 `ChangeConfigTo` 接收新配置，使用 `FreezeShard`、`InstallShard`、`DeleteShard` RPC 移动数据，并更新配置 KV。

需要迁移的原因包括负载不均、新组加入以扩充容量，以及旧组因维修或退役而退出。

本实验的主要挑战，是在分片归属变化及控制器中途故障／分区时，仍保持 `Get/Put` 的线性一致性：

1. 有些客户端可能还在访问旧组，另一些已访问新组。**任一时刻，同一分片至多由一个组对外服务。**
2. 控制器可能在分片已开始迁移、尚未完成时失联。测试器会启动新控制器；你必须让它接续完成原来的配置变更，恢复进展。

### 约束

- 这里的 configuration 指分片到组的分配，**不是 Raft 集群成员变更**；无需实现后者。
- 每台分片服务器只属于一个组；一个组内部的服务器集合不变。
- 客户端和服务器之间只能通过 RPC 交互；不同服务器实例不能共享 Go 变量或文件。
- 使用 Lab 2 的 `kvsrv`，以及 Lab 4 使用的 RSM/Raft；Lab 4 和 Lab 5 必须共用同一套 RSM/Raft 实现。Raft 的实现基础来自 Lab 3。

这些设计与 Flat Datacenter Storage、BigTable、Spanner、FAWN、HBase、Rosebud、Spinnaker 等系统有共同思路，但真实系统的成员管理、数据模型与查询能力通常更复杂。

**官方课程安排：**学生可以选择自拟期末项目，或完成本实验；5A 可以使用 late hours，5B–D 不可以。5D 是官方实验的开放扩展部分，本自学路线把它放在 A–C 之后作为进阶项。

## 2. 开始前

官方网页要求 `git pull` 获取最新实验软件。本路线固定上述提交：在自己的学习分支中继续 Lab 2–4 的实现，不能因为网页的更新命令而悄悄更换接口版本。工具链和仓库共用入口见[公共资料](#/c/mit-6.824-2021)。

骨架位于实验仓库 `src/shardkv1/`：

| 位置 | 用途 |
|---|---|
| `client.go` | 整个分片 KV 的 Clerk |
| `shardcfg/` | 配置表示、计算与键到分片的映射 |
| `shardgrp/` | 单个分片组的 Clerk、服务器及迁移 RPC |
| `shardctrler/shardctrler.go` | 初始化、查询、改变配置，以及控制器恢复 |

以下所有命令都在**实验仓库的 `src/`**，不是课程站目录：

```bash
make RUN="-run 5A" shardkv
```

固定 Makefile 会先构建 `main/kvsrv1d`、`main/shardgrp1d`，然后进入 `shardkv1`，运行带 `-v -race`、`-timeout 15m` 的 Go 测试。未完成骨架不会通过测试。下文保留官方各阶段的要求与提示，重复的构建输出和示例耗时不逐行重列。

## 3. 5A：移动分片（难）

先实现分片组，以及无控制器故障情形下的 `InitConfig`、`Query`、`ChangeConfigTo`。

给定的 `shardcfg.ShardConfig` 包含唯一配置号、分片号到组号的映射、组号到服务器列表的映射。通常分片数多于组数，因此每组持有多个分片，可以较细粒度地平衡负载。

### 3.1 存储和查询初始配置

在 `shardctrler/shardctrler.go` 实现：

- `InitConfig(cfg)`：接收测试器传入的第一个 `ShardConfig`，将它存入 Lab 2 的 `kvsrv`。
- `Query()`：读取 `kvsrv` 中的当前配置并返回。

**任务：**完成这两个方法并通过第一个测试。这一步不需要分片组。

```bash
make RUN="-run '^TestInitQuery5A$'" shardkv
```

**提示：**使用 `ShardCtrler.IKVClerk` 的 `Get/Put` 访问配置 KV；用 `ShardConfig.String()` 把配置转成可存储的字符串，用 `shardcfg.FromString()` 解析回来。

**固定骨架补充：**初始配置只由测试器调用一次 `InitConfig` 写入；键名由你选择，创建键使用版本 0。最初所有分片都分配给 `shardcfg.Gid1`。

### 3.2 先让静态的单组系统工作

**任务：**从自己的 Lab 4 `kvraft` 实现复制所需逻辑，在 `shardgrp/server.go` 实现初版分片组，在 `shardgrp/client.go` 实现对应 Clerk；在 `shardkv1/client.go` 实现系统 Clerk，通过 `Query()` 查找键所属的组，再访问该组。通过静态测试：

```bash
make RUN="-run '^TestStaticOneShardGroup5A$'" shardkv
```

**全部提示：**

1. 复用 `kvraft` 的 Get/Put 客户端、服务器代码及其他必要部分。
2. 系统 Clerk 负责整体路由；调用 `Query()` 获取当前配置，找到所需键所在分片的组。
3. 用给定的 `shardcfg.Key2Shard()` 求分片号。测试器会把 `ShardCtrler` 对象传给系统 Clerk 的 `MakeClerk`。
4. 通过配置的 `GidServers()` 得到该分片的组和服务器，调用 `shardgrp.MakeClerk(ck.clnt, servers)` 创建组 Clerk，再经它读写。
5. 系统 Clerk 的 Put 必须保留“回复可能丢失”的不确定性，必要时返回 `ErrMaybe`；它内部调用的组 Clerk Put 可以通过错误值传递这项信息。
6. 第一个组 `shardcfg.Gid1` 创建时，应初始化为拥有全部分片。

**编者校注：**网页命令中的 `TestStatiOneShardGroup5A` 少了字母 `c`，实际测试名如上。该测试还会关闭分片组的 Raft leader 后继续读，因此“静态”只表示不改变分片配置，不表示没有节点故障。

### 3.3 增加组并迁移数据

现在实现 `ChangeConfigTo(new)`：新配置可能加入旧配置没有的组，也可能移除旧组；控制器需要移动键值数据，让各组持有的分片与新配置一致。

官方建议按以下顺序移动一个分片：

1. 在源组冻结分片，使它不再接受该分片的写入。
2. 把分片状态复制、安装到目标组。
3. 删除源组的冻结分片。
4. 最后公布新配置，让客户端找到迁移后的分片。

这样组与组之间无需直接交互，并且不受迁移影响的分片仍可继续服务。

**编者校注：**上述网页叙述只点名冻结后的 Put；固定 `shardgrp/server.go` 对 `FreezeShard` 的注释明确要求拒绝后续 **Get 和 Put**。实现应按此边界处理，不能让旧组在目标组已接收新写入后继续回答旧值。

为确定配置变更的顺序，每个配置带唯一的 `Num`。5A 的测试器顺序调用 `ChangeConfigTo`，每次传入的 Num 比前一次大 1。更大 Num 表示更新配置。

网络可能延迟、打乱 RPC 顺序，因此 Freeze/Install/Delete 参数都包含 Num；每个组必须记住**每个分片所见过的最大配置号**，拒绝旧 RPC。

**任务：**实现控制器的 `ChangeConfigTo`；扩展 `shardgrp/client.go` 与 `server.go`，使用 `shardgrp/shardrpc` 中定义的 RPC 实现冻结、安装、删除，并按 Num 拒绝旧操作。系统 Clerk 还要处理组返回的 `ErrWrongGroup`。先通过：

```bash
make RUN="-run 'Test(JoinBasic|DeleteBasic)5A$'" shardkv
```

这两项主要检查增加组，暂时不要求通过退出组的测试。官方描述这一阶段的配置变更应成功，不考虑控制器中途失败；但完整 5A 仍有丢消息和分片组重启测试，不能据此省略重试及恢复。

**全部提示：**

1. 收到不属于本组负责分片的 Get/Put，应返回 `ErrWrongGroup`。系统 Clerk 应重新读取配置并重试原请求。
2. `FreezeShard`、`InstallShard`、`DeleteShard` 必须和 Get/Put 一样经过 RSM。
3. 可以通过 RPC 传整个 map，让分片传输保持简单。**固定接口的状态字段实际为 `[]byte`**，因此需把待传输状态编码进该字段，不是直接把字段改为 map。
4. 如果 RPC 回复引用服务器状态中的 map，RPC 编码器读取 map 时并不持有你的状态锁；此时服务器可能同时修改它。应返回独立副本，避免数据竞争。

### 3.4 支持退出组并完成整个 5A

**任务：**让 `ChangeConfigTo` 也处理旧配置中存在、新配置中不存在的组，将其分片移走。通过：

```bash
make RUN="-run '^TestJoinLeaveBasic5A$'" shardkv
```

前一步可能已支持退出，但此前测试没有检查这一情形。

**最终任务：**通过全部 5A 测试，包括多个组加入／退出、组重启与快照相关行为、某些分片离线或迁移时的 Get 进展，以及客户端并发操作与控制器重平衡同时发生时的线性一致性。

```bash
make RUN="-run 5A" shardkv
```

官方示例覆盖初始化、单组、Join、Delete、基本与多组 Join/Leave、Shutdown、两类 Progress，以及单／多 Clerk 在可靠和不可靠网络中的并发操作。**正在变更配置时，不受影响的分片必须继续服务。**

## 4. 5B：接续失败控制器的工作（易）

控制器是管理员运行的短生命周期命令：迁移分片后退出；但也可能在 `ChangeConfigTo` 中途故障或失去网络连接。测试器会隔离原控制器，启动新控制器并调用其配置变更逻辑；新控制器必须完成未完成的重配置。

测试器在启动控制器时调用 `InitController()`。可以在这里检查是否有中断的变更需要恢复。

官方建议在配置 KV 中保存两份配置：

- **current**：当前配置；
- **next**：准备切换到的下一份配置。

控制器开始重配置时先保存 next；完成迁移后，把 next 变成 current。`InitController()` 先检查已存 next 的 Num 是否高于 current；如果是，就完成切换到 next 所需的分片移动。

**任务：**按此思路修改 `shardctrler`。恢复者可能重复发出 Freeze、Install、Delete RPC；分片组应利用 Num 识别重复，避免重复修改或破坏状态。通过全部 5B：

```bash
make RUN="-run 5B" shardkv
```

测试包括 `TestJoinLeave5B`（组暂时停机时等待，恢复后完成）与 `TestRecoverCtrler5B`（接续失联控制器）。

**提示：**恢复入口就是 `shardctrler/shardctrler.go` 的 `InitController()`。

**编者校注：**网页此处把最后一种 RPC 简写为 `Delete`，固定方法名是 `DeleteShard`。网页所说的“检测并拒绝重复”不能理解成同一 Num 一概报错、无限重试：同号的不同迁移阶段以及成功回复丢失后的重试，都必须能够让恢复者安全推进；具体状态设计见实验指导。

## 5. 5C：并发配置变更（中）

原控制器崩溃或分区后，新控制器必须完成它未完成的工作。旧控制器可能并未真正死亡，随后恢复连接；多个控制器因此会同时向分片组和配置 KV 发 RPC。

主要困难是阻止这些控制器互相破坏状态。5A 已用 Num 隔离旧分片 RPC；多个控制器接续同一项已确定工作时，重复迁移 RPC 不应再次改变已经完成的效果。

还必须保证**某个 Num 只能选中一份 next 配置**。测试器会让多个控制器都读取当前配置，分别计算加入／退出不同组的新配置，再调用 `ChangeConfigTo`，因此它们可能传入 Num 相同、内容不同的候选配置。

可以使用配置 KV 中键的版本号及版本化 Put，让只有一个控制器写入 next，其他竞争调用不执行自己的变更而返回。这里的**键版本号不是配置 Num**。

### 5.1 唯一选中下一配置

**任务：**修改控制器，使每个新 Num 只有一个候选能发布为 next，只有胜出的候选启动对应迁移。通过并发测试：

```bash
make RUN="-run '^TestConcurrentReliable5C$'" shardkv
make RUN="-run '^TestAcquireLockConcurrentUnreliable5C$'" shardkv
```

**提示：**阅读 `test.go` 的 `concurCtrler`，了解测试器如何同时运行多个控制器。

### 5.2 把接续恢复与旧控制器重新连网结合起来

**任务：**新控制器执行 5B 的恢复；如果旧控制器在配置变更中被分区，必须确保它重新连接后不能干扰新控制器。若所有更新已经正确检查 Num 并隔离旧操作，就不必额外增加另一套协议。通过 Partition 测试：

```bash
make RUN="-run Partition" shardkv
make RUN="-run 5C" shardkv
```

这包括 Join 中途隔离控制器，以及可靠／不可靠网络下、带／不带并发 Clerk 的多次分区恢复。

完成后，你已经实现一个具有多个分片组、可重配置以平衡负载、能够接续控制器故障的分片 KV。**编者补充：**A–C 默认的配置存储仍是 Lab 2 单机 KV；“控制器可恢复”不表示配置 KV 已具有副本容错。

**回归任务：**重新运行所有测试，确认控制器修改没有破坏早期阶段。官方提醒 Gradescope 还会重跑 3A–D 和 4A–C：

```bash
make raft1
make kvraft1
make shardkv
```

**固定 Makefile 补充：**4A 及 RSM 层的 4C 位于独立 `rsm1` 目标。要覆盖官方文字所说的全部 Lab 4，还应运行 `make rsm1`；网页三条命令本身不会进入该目录。

## 6. 5D：官方开放扩展／自学进阶项

这是官方实验的最后一部分：选择下列想法之一，或提出自己的扩展；**自己编写测试**。在 `extension.md` 写一段说明，并按官方课程安排上传到 Gradescope。较难、开放性较强的扩展允许与另一位同学合作。

本自学路线先完成 A–C，再选择进阶方向；这不改变官方对 5D 的任务表述。固定源码没有通用 `5D` 测试组。

1. **让配置存储容错（易）。**修改测试器，用 `kvraft` 代替 `kvsrv` 保存控制器配置；写测试验证一个 kvraft 副本停机时仍能查询、更新配置。测试器相关代码分布于 `src/kvtest1`、`src/shardkv1`、`src/tester1`。
   - **版本校注：**网页提示在 `MakeTestMaxRaft` 内把 `kvsrv.StartKVServer` 换成 `kvraft.StartKVServer`；固定代码实际上通过 `tester.MakeConfig(..., 1, ..., "kvsrv1d", ...)` 启动单机 daemon，控制器也创建单机 `kvsrv.MakeClerk`。实现扩展时需相应调整启动组、进程、Clerk 与构建入口，不能只照替换函数名。
2. **恰好一次语义（中）。**让 `kvsrv` 的 Get/Put 具有 exactly-once 语义，并在 `kvraft` 实现同样能力。官方链接到 [2024 Lab 2 的丢消息部分](http://nil.csail.mit.edu/6.5840/2024/labs/lab-kvsrv.html)，可以考虑移植其中测试。
   - **年份校注：**2026 网页称该链接为“去年”，但 URL 明确是 2024；本页按链接年份标识，不把旧接口并入 A–C。
3. **范围查询（中）。**给 `kvsrv` 增加 `Range(low, high)`，返回键区间中的所有键。遍历整个 map 是简单方案；更好的是 B-tree 等支持范围搜索的数据结构。编写测试，让简单遍历方案失败而高效方案通过。
4. **不经日志的线性一致读（难）。**修改 `kvraft`，让 leader 的 Get 不经过 RSM；实现 Raft 论文 §8 末尾讨论的优化，包括租约，并维持线性一致性。既要通过现有 kvraft 测试，也要增加性能测试（例如比较 RPC 数），以及验证新 leader 必须等待旧租约到期、任期切换因而变慢的测试。论文统一见 [L5 课程资料](#/c/mit-6.824-2021/lec/lec05?v=materials)。
5. **单组事务（难）。**让 `kvraft` 能原子执行多个 Get/Put。事务表达能力包含版本化 Put，不再必须依靠它作为唯一条件更新接口。可参考 [etcd 事务接口](https://etcd.io/docs/v3.4/learning/api/)，自行编写测试。
6. **跨分片事务（难）。**让 `shardkv` 能跨分片原子执行多个 Get/Put。官方此扩展方向要求实现两阶段提交（2PC）和两阶段锁（2PL），并编写测试。

**2PC/2PL 属于这里的跨分片事务扩展，不是 5A–C 的基础迁移要求。**配置迁移和事务的概念衔接见[实验接口桥接](#/c/mit-6.824-2021/lec/update-lab-bridge?v=notes)。

## 7. 提交前

官方要求提交前最后再运行全部测试，页面再次列出 `make raft1`、`make kvraft1`、`make shardkv`；结合上文，还应覆盖独立 RSM 目标。仓库根目录的 Makefile 是提交打包入口，`src/Makefile` 才是测试入口，不要混用。

## 引用与来源

- MIT 6.5840 Spring 2026 课程团队，[Lab 5: Sharded Key/Value Service](https://pdos.csail.mit.edu/6.824/labs/lab-shard1.html)。本页为实验正文、A–C 全部任务与提示、D 扩展及提交要求的中文翻译和编排；图示含义以文字列出，终端重复输出缩写；编者校注明确标识。
- 许可根据[课程首页](https://pdos.csail.mit.edu/6.824/index.html) `rel=license`：[CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。该证据用于课程自有实验文字，不扩展到源码、外链论文或其他实验年份材料。
- 来源 `lab-shard-2026-p5`：快照抓取于 2026-11-08，HTTP Last-Modified 为 2026-04-23；它晚于固定代码提交的 2026-02-13。源码按 `513cac0aef010750fc74688da8a395974a83cf7a` 核对，页面差异保留，不假设二者同日发布。
- 精确哈希、逐文件阅读范围与差异登记：`sources/p5-lab5/manifest-fragment.json`、`sources/p5-lab5/review.txt`。外链的协作政策、提交细则、Go 安装、Piazza、图像、2024 实验及 etcd 文档未计为本次全文阅读。
- 自主实现思路、状态边界及测试诊断见[实验指导](#/c/mit-6.824-2021/lab/shardkv?v=guide)。本次没有编译或运行任何实验代码，终端命令是供学习者实现后执行的入口。
