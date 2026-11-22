---
source: CMU 15-445/645 · Fall 2025 · Project 4 — Concurrency Control；BusTub v20251119-2025fall @ d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 原创中文要求导读，不是题面全文翻译。项目网页未确认独立再利用许可；BusTub 源码另依 MIT 许可。
status: 已静态核对四项必做任务、两项可选榜单、公开测试和提交入口；未运行学生实验，学习者状态 not_attempted。
---

# Project 4：让一条库存记录同时回答两个时间的问题

仓库刚把库存从 12 减到 9。盘点员在这次扣减前开始读表，下单员在扣减提交后才来。两人查询同一个货号，分别得到 12 和 9，都可能是对的。现在让盘点员**根据 12 再扣一件**：允许从旧版本读，不表示允许覆盖新版本。这正是 BusTub 要加的两项不同承诺：**按快照读，按冲突规则写**。最后还要回答：两笔订单写的根本不是同一行，又为什么可能不得不撤销一笔？

[实验指导：沿一条 RID 查错](#/c/cmu-15-445-2025/lab/project4?v=guide) · [L19 时间戳排序](#/c/cmu-15-445-2025/lec/lec19?v=notes) · [L20 多版本并发控制](#/c/cmu-15-445-2025/lec/lec20?v=notes)

## 范围、依赖与检查点

项目实现 **MVOCC（多版本乐观并发控制）**：先做 Snapshot Isolation（SI，快照隔离），再为 Serializable（可串行化）的读写事务加提交验证。表堆仍是原来的表堆，保存最新完整行；旧状态从事务工作区的内存差量还原。不要求把 undo 持久化，也不是重写整个存储引擎。

| 官方任务 | 子任务 | 完成的判据 |
|---|---|---|
| 1 · 时间戳 | 1.1 分配；1.2 水位线 | 新事务从已发布的提交取快照；能高效给出最老活跃快照 |
| 2 · 格式与顺序扫描 | 2.1 重建；2.2 收集日志与扫描 | 给定差量能复原；不同读者在同一 RID 能看见不同的值或根本看不到行 |
| 3 · MVCC 执行器 | 3.1 插入；3.2 提交；3.3 生成 undo；3.4 更新与删除；3.5 停世界 GC；3.6 Abort | 写集、链头和行一致；提交、回滚后其他事务能继续；最老读者不被回收伤害 |
| 4 · 主键索引 | 4.1 插入竞争；4.2 索引扫描、删除与更新；4.3 改主键；4.4 Serializable 验证 | 同一键稳定指向一个 RID；按各自快照回表；谓词依赖也能在提交时发现 |

这是**个人**项目。Fall 2025 作业表与项目页都列 **11 月 10 日发布、12 月 7 日 23:59 截止**（表中未标时区）；课表挂在 L19。项目页最后更新于 12 月 7 日。评分的功能分界是 **做到 4.1（含）累计 75 分**，此范围只有一个并发测试；再完成 **4.2–4.4 累计 100 分**。这不是两个提交日期，75 也不是一个只需要读／写、不需要回滚的项目。另有两个榜单负载，不是第 5 个必做任务。

开始前把自己可用的 [P3](#/c/cmu-15-445-2025/lab/project3?v=zh) 留为单独的私有 **checkpoint**，从它另开 P4 工作线。今天复现用学期标签 `v20251119-2025fall` 指向的固定提交，不照搬旧网页的“拉最新 master”。[P1](#/c/cmu-15-445-2025/lab/project1?v=zh) 的缓冲池和 [P2](#/c/cmu-15-445-2025/lab/project2?v=zh) 的索引正确性是前置条件；不需要先把 P3 所有题做到满分，但 4.2 确实需要 P3 的顺扫转索引扫描规则，榜单需要聚合器。保留 `Init()` / 批式 `Next(tuple_batch, rid_batch, batch_size)` 契约；改的是可见性和修改语义，而不是退回旧年份的单行接口。

**从 Task 3 起不再与 P3 所有场景兼容**：本项目的写路径只要求定长类型，普通非键更新用原 RID 原地改；P3 的普通 Update 要求删旧插新，且删除时维护、移除普通索引项。P4 主键历史反而依赖索引项不消失。不要拿 P3 回归是否全绿作为 P4 验收，也不要把整数写测试外推为 Task 2 只需支持整数。每个测试里的事务都在同一隔离级别运行；题面不要求实现混用级别或 `READ_UNCOMMITTED`。

## Task 1：分清三个数，再谈水位线

**1.1 Timestamp Allocation。** `TransactionManager::Begin` 给事务分配标识，同时记录 `read_ts`：这是 Begin 时系统**最后一次已完整发布**的提交时间，而不是事务编号，也不是等到第一次 SELECT 时才确定。多个事务可以共享 `read_ts`。成功 Commit 分配唯一、单调增加的 `commit_ts`，初始系统已提交时间为 0，第一个成功提交为 1。未提交的堆行另用事务自己的 `GetTransactionTempTs()` 标记。固定树中事务编号从 `TXN_START_ID = 1LL << 62` 开始；调试显示的 `txn7` 不是提交时间 7。UndoLog 的 `ts_` 表示倒退所到的历史状态，不写入临时戳。

**1.2 Watermark。** 对所有尚未 Commit／Abort 的事务取最小 `read_ts`；集合为空才返回最近提交戳。`RUNNING` 与尚未清理的 `TAINTED` 都没有结束。两个读者若同在 5，一个退出不能把另一个也消掉。`Watermark` 提供 `AddTxn`、`RemoveTxn`、`UpdateCommitTs`、`GetWatermark`；提交时先通知最新提交戳再移除该读时间，Abort 不制造一次提交。题面要求能用 $O(\log N)$ 或更好的代价维护水位线，不能每次遍历全部历史事务。Task 1 使用 Abort 骨架即可，但这不替代 3.6。

## Task 2：先决定走多远，再重建

跟同一条 RID（页号、槽号）走一遍数据所在的三个地方：

| 位置 | 实际存放 | 容易误认的东西 |
|---|---|---|
| `TableHeap` | 最新的完整 `Tuple` 及 `TupleMeta{ts_, is_deleted_}` | 堆顶最新不等于读者可见；有槽位不一定有逻辑行 |
| `TransactionManager::PageVersionInfo` | 页内各槽位的第一条 `UndoLink` | 不是每页一条公共链；读没见过的槽不应顺手创建映射 |
| `Transaction` 工作区 | `undo_logs_` 中各条 `UndoLog` | `UndoLink{prev_txn_, prev_log_idx_}` 是“哪个事务的第几条”，不是 C++ 裸指针或提交戳 |

**2.1 `ReconstructTuple` 只管重建。** 输入表 schema、堆基础行、基础元信息和已选好的日志列表。由新到旧应用**所有**给定日志，不按时间二次筛选，也不访问事务管理器。`modified_fields_` 与整表列数等长，但日志的 `tuple_` 只装置位列的旧值：整表第 4 列可能是差量的第 1 列。要用相应的部分 schema 解释它。日志的 `is_deleted_` 表示退回去的那个状态是否已删除，不能用堆顶删除标志代替。最终状态是删除标记就返回 `std::nullopt`；某一个列值为 SQL `NULL` 的行仍然是存在的行。

**2.2 `CollectUndoLogs` 管选择，`SeqScanExecutor` 管输出。** 看到自己的临时戳，或者看到不晚于 `read_ts` 的已提交堆顶，不必绕道 undo。若堆顶是别人的临时戳或太新的提交，则沿链退到**第一个**不晚于读点的版本；使你抵达这个版本的那条差量也要带上。一路退到底仍达不到读点，例如这是别人刚插入的全新行，则当时不存在。该函数返回 `optional<vector<UndoLog>>`：**空向量**表示可直接使用基础状态，**无向量**表示找不到那个时间的版本；有向量也可能最后重建出删除标记。

顺扫用 `GetTupleAndUndoLink` 取得同一观察点的基础数据和第一条链接，基于**可见行**判断谓词并输出，还要把原 RID 配回批中。不能像 P3 那样看到堆顶已删便跳过；事务旧快照可能仍看得到它。固定测试会直接造基础行及版本链，不必先完成 Insert；重建还要考虑整数以外的类型、空值及“删除后又出现”。

## Task 3：让行、链和事务状态一道改变

**3.1 Insert Executor。** 在暂不处理主键的情形，插入新槽，堆元信息写本事务临时戳和未删除状态，并调用 `AppendWriteSet(table_oid, rid)`。此前根本没有这个 RID 的逻辑版本，**新槽插入不生成 undo**。后来同一事务再改这个新槽，不等于凭空多出一个已提交前身。写集登记的是改过的物理位置，不是 SQL 的影响行数。

**3.2 Commit。** `commit_mutex_` 让提交阶段一次只有一个事务进入。一次提交可能改了多个 RID 甚至多张表，所有写集内的堆顶要交接到同一提交戳，事务改为 `COMMITTED` 并更新提交时间和水位线。关键是**发布顺序**：若 Begin 已能取得新戳，所有相关行就必须已准备好让它按这个戳读取。先在全局计数器上公开新戳、然后才逐行补签会暴露半次提交。题面示意中的 `last_committed_ts_` 在固定头文件实际叫 `last_commit_ts_`。

**3.3 Generate Undo Log。** 对已有行首次修改用 `GenerateNewUndoLog`；同一事务再次修改同一 RID 用 `GenerateUpdatedUndoLog`，替换已有条目而不是追加整条历史。目标是从事务最终改出的行，仍能退回到**这笔事务动手之前**。普通更新只记需要的旧字段；删除旧行必须能恢复整行；把已有墓碑恢复成活行需要能退回墓碑。接口用 `base_tuple == nullptr` 表示原先已删、`target_tuple == nullptr` 表示目标删除，不是某列为 `NULL`。题面建议合并时只增加所保留的旧信息，不因某列后来改回原值便删去既有字段。每事务每 RID **至多**一条日志，不是每次 SQL 一条。

**3.4 Update / Delete。** Update 是阻断式算子：先收全孩子交来的行与原 RID，再开始改堆；不能边扫边把新值当成新的输入。普通更新保留 RID，删除留下标记，二者都要维护写集、基础行及链头。若堆顶属于另一未结束的写者，或已提交版本比自己 `read_ts` 新，即使能读到旧行，也不能据此改写。写自己的临时版本不算冲突。写写冲突必须 `SetTainted()` **且**抛 `ExecutionException` 令本条 SQL 失败（`ExecuteSqlTxn` 返回 `false`）；这时可能早已有本事务其他写入，尚未回滚。不要把一次冲突当作“受影响行数为零”的成功语句。

自插新槽又自删，若提交，逻辑上从未存在，且无旧链；题面允许在早期任务按通常提交戳处理，也给出 0 戳标记的表示。**只在没有旧历史**时可这样理解，4.4 还须能识别这次无净记录变化。若有前身，即使堆顶已删，旧快照仍要按真实时间找回它。

**3.5 Stop-the-world GC。** 显式调用 `TransactionManager::GarbageCollection()` 时工作事务都暂停访问表，并非每次写操作在后台自动收集。对每条链确定水位线及其之后的快照仍会用到的那段，尤其包括**刚好能恢复到水位线或更早最近版本的最后一跳**。回收单位是 `txn_map_` 中整个**已提交或已中止**的事务对象；它为任意一条链提供一条仍需要的日志，就不能整包释放。不能单凭“事务早已结束”或“这条日志的 `ts_` 小于水位线”判断。题面容许被截断的历史深处残留不可达链接；扫描器不可越过所需边界去解引用。必做 GC 不要求搬移表槽、删主键项或在线回收。

**3.6 Abort。** 现在才真正撤销。遍历**本事务**改过的 RID，恢复旧数据、删除状态、时间戳，使其他事务可继续写；新插且无前身的槽改为 `ts = 0` 的删除标记，不物理移除表槽。允许两种表示：① 恢复堆顶但保留本事务的 undo，链上会出现相同的历史时间戳，读路径须正确处理，GC 仍可能需要该工作区；② 原子地恢复堆顶并把链头接回前驱，完全脱链的 abort 日志不必等水位线才能失去用途。两种都不撤销已创建的主键映射。多个事务必须能够并行 Abort，不用 `commit_mutex_` 或其他全局锁包住整个回滚函数。局部保护仍然必要；只改状态枚举不算回滚。

## Task 4：键找到槽，快照决定槽里的哪一行

**4.1 Index Insert。** 建表声明主键会创建唯一主键索引，一表最多一个；DDL 支持单列或两列整数组合主键，本题不要求维护另用 `CREATE INDEX` 创建的二级索引。单线程看到已存在的活键就应报冲突，不要无条件先分配多余表槽。并发时两个插入者都可能先查到“不存在”，各自分配了新槽，却只能有一个 `InsertEntry` 成功。必须处理其返回值；失败方进入 `TAINTED`、语句失败，可能已留有一个没被索引指向的槽，不能让它成为第二个可见结果。此阶段的测试允许走顺扫，**尚不以 4.2 的索引读作为前提**。

**4.2 Index Scan、Delete 与 Update。** 键一旦进索引，就一直指向同一个 RID，即使当前已删除。先前的读者要靠这个入口找历史；`ScanKey` 返回 RID 不是回答“当前读者看得到吗”。索引扫描与顺扫应回到同一版本选择，再检验谓词。重新插入已删除的同一键，满足唯一性和写冲突规则时，要**复用墓碑所在 RID**，而不是另造 RID 改掉映射。若索引命中的是活行、别人的临时写，或超出本快照的修改，不能只因“我的 SELECT 没查到”就复用。等值查询需让 `OptimizeSeqScanAsIndexScan` 真的产出 `IndexScan`。

多线程下，分两次读取堆和链头，可能拿到来自不同更新的两半状态。从这一阶段使用带检查的 `UpdateTupleAndUndoLink` 与 `GetTupleAndUndoLink`，确保冲突判断到发布之间不会覆盖另一写者。它们是 `bustub` 命名空间的**自由函数**，不是 `TransactionManager` 成员；带 `WithLockAcquired` 的底层接口和自行再次取同一页锁的普通接口也不能混用。

**4.3 Primary Key Updates。** 不改主键仍是在原 RID 更新。改变主键时，对同一条 SQL 收集到的目标行，语义是**先删所有要迁出的旧键，再插所有新键**。例如原有相邻货号 40、41，一起加 1 得到 41、42，不应因为尚未迁出旧 41 而误报重复，也不能把刚变为 41 的行再次迁到 42。对不在迁出集合中的既有活键仍要执行唯一约束。两个键各自保留原先的映射和可追溯历史；不是就地改 B+ 树键，也不是任意换指针。

**4.4 Serializable Verification。** 在 SI 上加 **OCC 后向验证**：记录本事务每次 SeqScan／IndexScan 对哪个表用了哪些谓词，包括没有匹配行的扫描。提交一个有写入的 Serializable 事务时，以其 `read_ts` 为界，考察**此后已经提交**的事务的写集；按表和 RID 检验各次已提交变化是否触及自己的扫描条件。只读事务可跳过这次验证。固定树预留 `AppendScanPredicate` 和私有 `VerifyTxn`；后者骨架一直返回真，并不意味着验证已实现。

| 在该历史步发生的变化 | 验证对照什么 |
|---|---|
| 不存在 → 存在 | 新行对读谓词是否为真；开始时没返回过这条 RID 也算 |
| 存在 → 不存在 | 删除前的旧行是否匹配，不能只盯着墓碑 |
| 存在 → 存在 | 改前或改后任一匹配都要考虑；不能只比较链两端 |
| 同一事务新插又删，从无到无 | 是无净记录变化，不是假造的一次删除 |

同一事务改值又改回、留下一个值相同的更新，仍按一次 update 评估；两次不同提交把 `X → Y → X`，中间的 `Y` 也不能抹去。验证失败的 `Commit` 应真正走 `Abort`、返回 `false`，最终是 **`ABORTED` 而非 `TAINTED`**。这里要求记录级检查，不要求为常规正确性实现属性级精细验证或并行验证。

## 可选：T-NET 的两种工作负载

1. **Token Transfer / SI**：一笔交易加一个账户、减另一个，观察并发吞吐与总额一致性。
2. **Trading-Network / Serializable**：能否免手续费取决于两方网络；此外还有带奖励的邀请入网、花费代币另建网络。负余额允许。负载因此既有读后决定的写，也有会改变这种决定的写。

可选程序目标 `terrier-bench`，产物 `bin/bustub-terrier-bench`，`--bench-1` / `--bench-2` 二选一；用 `SUM(token)` 检查总量，因此聚合不只是用来显示结果。榜单比较吞吐与**堆槽数加 undo 条数的采样峰值**，不是按进程内存字节；负载不调用 3.5 的停世界 GC。可研究在线清理（需要保留事务提交信息时可考虑 `ClearUndoLog`）、更细粒度或并行验证，这些不能反过来放宽必做的可见性。每项排名第 1／2–10／11–20 分别给 25／15／5 加分，两项相加受榜单总加分上限约束；会人工复核。不得故意拖慢吞吐以压空间、整库大锁串行化、探测评分环境、硬编码负载答案；榜单不接受 late days。

## 公开测试、质量与交付

固定树的入口是 `test/txn/` 下 **6 个 `*_test.cpp`，共 28 个带 `DISABLED_` 前缀的 GoogleTest 案例**，另有公共辅助头；不是 P3 的 `.slt` 清单。详见[指导页的逐目标表与调试命令](#/c/cmu-15-445-2025/lab/project4?v=guide)。Task 1 的实际 suite 名是 `TxnTsTest`，不是网页叫法 `TxnTimestampTest`。官方说明并发测试公开、隐藏测试为单线程；部分公开文件有后续留给 Gradescope 的注释。SQL 观察结果之外，公开测试还看日志数量、堆槽、行重建和事务状态；不按 `TxnMgrDbg` 漂亮程度或唯一一种链的打印格式评分。公开通过不代表隐藏分数。

在**自己的私有**工作区按 P0 环境配置。题面要求 Google C++ 风格；在 `build/` 下的相关目标为 `make format`（会改文件）、`make check-lint`、`make check-clang-tidy-p4`。正式项目同时看正确性、样式与内存错误：Debug 配置用 ASan／LSan，题面注明 macOS 不提供该 Linux 路径的 leak 检查；临时关闭 sanitizer 便于调试不能作为通过证明。保留规定的签名、成员；必要辅助逻辑写在会被打包的文件。`transaction_manager_impl.cpp` 注明不随评分收取；根 CMake 的 `P4_FILES` 是管理器与水位线的四个文件加 `P3_FILES`（其下还有前置项目文件），不是任意新文件都在提交里。

按题面的评分说明，忽略样式检查会导致项目零分；遇到崩溃可先用图形调试器区分异常与断言。`BUSTUB_ASSERT` 在 Release 不执行，始终必须检查的条件要区分 `BUSTUB_ENSURE`。题面列的 `cmake -DCMAKE_BUILD_TYPE=Debug -DBUSTUB_SANITIZER= ..` 是为调试暂时关闭 sanitizer 的配置，不是正式的内存检查；陈旧的生成配置有问题时，`make clean` 也不等于在新的构建目录重新配置。

在 `build/` 下 `make submit-p4` 会按清单在项目根生成 `project4-submission.zip`；历史题面指向 Gradescope，本站不验证登录或评分。常规延迟规则见 syllabus；独立作答、只交流高层思路、不复制讨论后的白板或别人的代码，不公开学生仓库。下面链接是核对入口，不是本页已执行过的检查清单。

## 引用与来源

- CMU 15-445/645，Fall 2025：[Project 4 完整题面](https://15445.courses.cs.cmu.edu/fall2025/project4/)，含 [Task 3.5 GC](https://15445.courses.cs.cmu.edu/fall2025/project4/#task-35-stop-the-world-garbage-collection)、[3.6 Abort](https://15445.courses.cs.cmu.edu/fall2025/project4/#task3.6)、[4.4 Serializable](https://15445.courses.cs.cmu.edu/fall2025/project4/#task4.4)、[榜单](https://15445.courses.cs.cmu.edu/fall2025/project4/#terrier_bench)及[基础评分分界](https://15445.courses.cs.cmu.edu/fall2025/project4/#points-distribution)；[作业表](https://15445.courses.cs.cmu.edu/fall2025/assignments.html#project4)、[11 月 10 日课表](https://15445.courses.cs.cmu.edu/fall2025/schedule.html#nov-10-2025)、[延迟及协作规则](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html#late-policy)。未复制题面原图、未宣称获得全文翻译许可。
- CMU Database Group，BusTub，[学期标签](https://github.com/cmu-db/bustub/tree/v20251119-2025fall)、[固定提交](https://github.com/cmu-db/bustub/commit/d49b823f829a4bf311a2c80b239ab5a9864c9c41)、[MIT License](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE)。[事务、UndoLink 与 UndoLog](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/concurrency/transaction.h#L41-L196)、[管理器与原子读写声明](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/concurrency/transaction_manager.h#L42-L112)、[水位线](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/concurrency/watermark.h#L26-L49)。
- [重建、选链、差量接口](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution/execution_common.cpp#L42-L116)、[原子操作实现](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/concurrency/transaction_manager_impl.cpp#L126-L161)、[批接口](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/executors/abstract_executor.h#L42-L54)、[主键 DDL](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/common/bustub_ddl.cpp#L57-L84)。
- [六个事务测试与辅助头](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn)、[打包目标](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/CMakeLists.txt#L378-L396)、[T-NET 负载](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/tools/terrier_bench/terrier.cpp)、[当年题面所列 Gradescope 入口](https://www.gradescope.com/courses/935004)（未登录）。阅读固定版本的接口与公开测试不等于编译、提交或完成学生项目。
