---
source: CMU 15-445/645 · Fall 2025 Project 4；固定 BusTub 提交 d49b823f829a4bf311a2c80b239ab5a9864c9c41 的事务、执行器、公开测试及工具
license: 原创指导与纸面例子；不搬运官方参考实现、学生解法、隐藏预期或题面原图。
status: 静态核对；以下复现实验供学习者在私有工作区自行执行，未代跑，not_attempted。
---

# Project 4 指导：先找出哪一个读者在何时看错了哪一行

看到“库存少了三件”，不要立刻追 B+ 树。先给出五个量：**哪个事务、哪个读点、哪个物理 RID、当时的堆顶、读者应当停在哪个版本**。如果顺扫和点查都错，先查共同的可见性；唯独点查错，再翻索引账。若两种读法都对而第二笔订单仍能错误提交，则要查的是写冲突或提交验证，不是 SELECT。

[完整任务与评分边界](#/c/cmu-15-445-2025/lab/project4?v=zh) · [L20 多版本并发控制](#/c/cmu-15-445-2025/lec/lec20?v=notes) · [P3 批执行器](#/c/cmu-15-445-2025/lab/project3?v=guide)

## 一张只记三笔动作的盘点单

库存表有 `(bin, sku, qty)` 三个整数列，501 号格存放商品 7。先不设主键，让顺扫的正确性与 P2、索引计划分开。下表是**纸面时间线**，`c10` 等是人为选的提交戳，不是 shell 的预期输出。只看一个物理位置 `r`。

| 时刻 | `r` 上发生什么 | 长事务 R | 正在写的 W | 此时新来的普通读者 |
|---|---|---|---|---|
| `c10` 后 | 已提交 `(501,7,12)`；R 取得读点 10 | 12 | — | 12 |
| W 改货量，未提交 | 堆顶 9，临时戳属于 W；有通向 12 的差量 | 12 | 9 | 12 |
| W 再从 9 改成 7 | 仍是同一笔事务、同一 RID | 12 | 7 | 12 |
| W 于 `c11` 提交 | 堆顶 7 的戳变为 11 | 12 | 已结束 | 7 |
| R 尝试按旧值扣减 | R 能读回 12，但堆顶已是后来的提交 | 语句失败，进入 `TAINTED` | 不受影响 | 7 |
| R 回滚后 | R 没有在 `r` 上赢得过写入 | 已结束 | — | 仍是 7，不能被 R 恢复成 12 |

先遮住最后两列自己填。一个实用对照是把最后一步改成 **W 在提交前自己 Abort**：此时 7 从来没有成为已提交库存，新读者仍应得到 12，后来合法的写者也不应再撞上 W 的临时戳。这两种回滚的责任不同：一个只取消失败者实际留下的东西，另一个要撤销它已经成功写过的行。

## 在一份私有库里制造两个观察点

在自己的 P4 工作线留好可返回的 P3 checkpoint。实现相应阶段后，在已有的 `build/` 下用 `cmake --build . --target shell` 构建 `./bin/bustub-shell`。先建立不带索引的小表：

```sql
CREATE TABLE bin_stock(bin int, sku int, qty int);
INSERT INTO bin_stock VALUES (501,7,12);
```

后续是**交互步骤**，不是一整块可以盲贴的 SQL。反斜线命令各占一行，不带分号；读写顺序比打印出来的 ID 数字重要。

1. `BEGIN;`，用 `\txn` 记下 R 的实际短 ID、`read_ts`；执行 `SELECT qty FROM bin_stock WHERE bin = 501;`。用 `\txn -1` **暂停** R 并返回每语句一个事务的模式。它没有提交，也没有让出水位线。
2. `BEGIN;` 得到 W 并记下它的 ID。`UPDATE bin_stock SET qty = 9 WHERE bin = 501;` 后，让 W 读一次，用 `\dbgmvcc bin_stock` 看堆；再把 9 改成 7。用 `\txn` 加空格和 R 的实际短 ID 切回 R，重读同一 SQL。核对的是 R 的读点没变、W 读到自己写的值；别写死 `txn0` 或假定每条查询都会在同一事务中。
3. 切回 W，`COMMIT;`。在非托管事务提示符下再读一次作为新读者；切回 R 再读。换一轮全新的同样数据，把 W 的 `COMMIT;` 换成 `ROLLBACK;`，比较两轮的**新读者**。测试旧快照时不要重开 R；做下一轮前结束不再用的事务，不要让它意外钉住 watermark。
4. 单进程内的 `\txn` 切换适合构造确定的逻辑交错，不证明线程安全。要观察两个同步活动的连接，另用 `cmake --build . --target nc-shell`、`./bin/bustub-nc-shell`；在服务端终端建表，再分别用 `nc 127.0.0.1 23333` 连接。同一服务进程的每个连接各开启一个事务。**分别启动两份独立的普通 shell 并不会共享这个内存状态**。

`TxnMgrDbg` 是 `execution_common.cpp` 里的调试钩子，题面强烈建议 Task 2 后就做。输出到 `stderr`，标出 `(page,slot)`、堆 `ts` 是提交戳还是哪个事务的临时戳、删除位、部分 schema、旧值、下一条的所有者及序号。用 `—` 表示该列不在差量中、`NULL` 表示它在且值为空；两者不能合并成同一个空格。表格边框不影响评分；在 GC 后也不要为了多打印一行而硬取一个已回收的历史事务。题面附官方 Web Shell 供人工观察参考行为，不是本地实现或学生评分的替代品。

## 查读错：选日志和应用日志分别问责

假设基础行为 `(501,7,9,3)`，四列依次是格号、商品、可售量、预订量。一次历史变更只动过后两列，则回到旧状态的 mask 可以写作 `0011`，差量载的是 `(12,NULL)`。这是**两个**紧排的值，不是四个单元；`NULL` 在这里是原预订量，前两个 0 才表示“不覆盖”。若总是按整表下标取差量值，只有修改了表首列的测试看上去正常。

1. **先不涉及事务**：给 `ReconstructTuple` 一段已经选好的差量。能否重建真空值、跳过未触及列？如果本次操作是恢复删除前的整行，数据是否足够？如果中间状态是墓碑而更早又是活行，是否错误地见墓碑就提前返回？这种错与水位线、优化器都没有关系。
2. **固定 RID，换读者**：画出 `堆顶 c17 → 差量到 c13 → 差量到 c8`。读点 13 需要第一跳；读点 12 还需要第二跳；读点 7 若更早没有历史，则无此行。无日志的**合法空向量**和**无足够历史的 nullopt**怎样在两次返回之间传递？到达目标就停，不要额外取下一个日志来“确认”。
3. **把测试包装到扫描中**：堆顶最新的 7 已不满足 `qty >= 10`，R 的可见旧值 12 却满足。若先对堆值做下推过滤，再去重建，R 会莫名少一行。检查重建后的行、谓词和配对的原 RID；在一批物理行全部不可见时，执行器仍可能从下一批取到可见行，不能把这一次“空”误作全表 EOF。

注意区分两个“相等”。`Value::CompareExactlyEquals` 可把两个空值视为同一旧值，适合判断要记录什么；普通过滤谓词按 SQL 三值逻辑执行，不能因此让 `NULL = NULL` 通过过滤。文中比较的是历史值是否要还原，不是改写 SQL 的等值语义。

## 查写错：写进去、可以提交、别人已看到，是三件事

给一次操作留两本账：事务账记 `table_oid → {RID}` 与每个 RID 的日志所有者，表账记“哪个临时戳占着它”。新插槽没有前身，但也必须在写集，否则提交时会留下临时戳。已有行被 W 连改三次，老读者从最后状态退**一次 W 的差量**，应该回到 W 开始前，而不是退到 W 的倒数第二次编辑。

| 最小对照 | 应当区分的现象 | 首查位置 |
|---|---|---|
| W 写了一行又写自己；另一事务想改同一行 | 自写可以合并，别人不能盖过未提交写 | 临时戳所有者、`GenerateUpdatedUndoLog` 与写写冲突判定 |
| W 在事务内新插又自删；另一事务删了先前已提交的行 | 前者没有可恢复的老活行；后者对旧读者仍必须存在 | `AppendUndoLog` 次数、删除前完整行、链头位置 |
| V 改订单成功，随后更新库存撞到 W | SQL 失败时 V 是 `TAINTED`，不是已完成回滚；V 已改的订单仍须在随后 Abort 清理 | 两张表的写集、`SetTainted`、异常与 `ExecuteSqlTxn` 返回值 |
| W 同时改了两个格位并提交 | W 提交前开始的读者应同时看到两个旧值；提交发布后开始的读者看到两个新值 | `commit_mutex_` 的保护范围、`last_commit_ts_` 发布点；不要只核对其中一个 RID |
| 普通 Update 在一批的边界重复改到同一行 | 最新版本不是“新的输入行” | 孩子是否完全消费、`target_expressions_` 算出的目标、批中原 RID 是否保留 |

若只在多线程时错，给这条交错标记四个时点：U 读到基础值，V 完成修改，U 打算发布，第三人读到结果。U 最早何时能确定依据仍有效？**拿锁写不等于你在锁外作的旧判断仍成立**。固定提交里，`GetTupleAndUndoLink` 在同一个页读保护下取元信息、tuple 和链头；`UpdateTupleAndUndoLink` 在页写保护中调用 `check`，失败便不发布。一个值得在调试器里核清的细节：传给这个组合函数回调的第四个参数就是调用方传入的 `undo_link`，不是它在锁内重新查出的旧 link；单独的成员 `UpdateUndoLink` 才把原有链接或 `nullopt` 传给自己的回调。不要错把两个回调当同一种 CAS 承诺。已有页 guard 时再调会重取同页锁的方法，也可能自己等自己。

## 查回滚与回收：按“谁还需要它”画线

**回滚验收至少用三位观察者**：W 更新前的长读者、W（要能在撤销前读自己的写）、W 回滚后才来的新写者。让 W 同时改一条老库存并插入一笔新订单，再明确 `ROLLBACK;`。长读者继续读到老库存；新读者不能看到那笔订单；新写者应能在同一库存上成功。只测“新订单查不到”是不够的：堆顶若还挂 W 的临时戳，读者可以绕链读对，而合法后继写者会一直报冲突。

对于已有历史的行，两条正确回滚路径可能打印出不同链。若恢复堆顶、保留 undo，堆顶和第一跳可能同戳，不能断言每一跳都严格变小；若恢复堆顶同时脱掉自己的头，则不该还从这个 RID 解引用 W 的工作区。对于无旧链的新插槽，物理槽可保留为 `ts=0` 的墓碑。**回滚不是清空整张表的所有临时行，也不是回滚者猜一个新的提交戳。**

再画一条已提交的链，箭头标签是“应用这份 undo 后抵达的版本”：`堆顶 c17 → c13 → c8 → c4`。设系统仍有读点 10、10、15 三个事务，最近提交为 17。

- 当前水位线 10。读点 10 需要停在 8，所以抵达 13 和抵达 8 的日志都受保护。**8 小于水位线并不是删除该条的充分条件。** 抵达 4 的那条对这个 RID 不再必要；其所属事务若还为另一行保有必要差量，整个事务对象仍不能移除。
- 一个读点 10 退出，另一个同点读者仍在；若只是进入 `TAINTED` 或在 shell 暂停，更不是退出。两个 10 都真正结束后，水位线才可到 15；此时仍需从 17 退到 13。最后一个也结束且没有新的提交时，才回到 17。这里把“结束”取为 Abort 以固定例中的最新提交戳；换作 Commit，要把新的提交戳也记上。
- 在所有线程暂停访问表时调用 `\txn gc`。先在纸上列仍受保护的 **owner 事务集合**，再看 `txn_map_`，而不是先按事务开始顺序逐个删除；在没有状态变化时连续收两次，结果不应再变。原始公共测试有专门带 `TAINTED` 的 GC 案例。

## 查主键：同一个入口不等于始终有货

另建有整数主键 `bin` 的表，追踪 `501 → r`。考虑下面三个已发布时刻；在各时刻开始的读者都保留到最后。`r` 从头到尾是同一个槽。

| 读者开始于 | 当时已提交的状态 | 删除后又重新插入时，按 501 点查的预期 |
|---|---|---|
| `c20` | 501 的货量为 12 | 仍然得到 12 |
| `c21` | 501 已删 | 不返回行，不是返回 `(501,NULL)` |
| `c22` | 501 在原槽重新上架，货量 5 | 返回 5 |

先用 `EXPLAIN (o)` 确认 `WHERE bin = 501` 真走 `IndexScan`，再与走 `SeqScan` 的等义条件比较（例如整数单点 `bin >= 501 AND bin <= 501`；实际计划以 `EXPLAIN` 为准）。**只是两次查询得到了相同的数，并不能证明索引路径已被覆盖。** 若三个时间都找不到，检索项是否被 P3 的删除逻辑移除了？若三个时间都给 5，点查后是否直接返回了堆顶？若回滚重插后多出第二个 501，先分别数表槽与成功插入索引的条目，不要把每个槽当作都能被索引找到。

下一步分开试两类竞争：两线程同时插一个从未建项的键；两线程同时要复用一个已有墓碑的键。前者由唯一索引插入裁决，先行的“没查到”不能预留成功；后者**索引已存在**，决定胜负的是同一堆槽上的状态和写冲突。再试主键批量迁移：只把 40、41 都加一，观察迁出集合里的 41 能被复用；另放一条不参加迁移的活 42，这次应冲突。失败可能发生在前半句已经写过其他槽以后，随后 Abort 要把整笔事务恢复。不要用反转扫描顺序来掩盖更新不是阻断式的问题。

## 最后的反例：只有快照，没有共同的批准

商品 7 有两个格位 701、702，每个恰剩一件。业务规定“至少留一件给线下订单”。甲、乙在同一快照先分别读 `WHERE sku = 7 AND qty > 0`，都看到两个格位；甲只把 701 改成 0，乙只把 702 改成 0。**不同 RID 没有写写冲突**。在 SI 下，两笔提交都可能成功，留下库存全零；若真让一笔完整做完再做另一笔，第二人会看到只能保留最后一件。两次查询各自一致不等于两笔决定共同可串行化。

在 Serializable 模式重演，先提交甲再验证乙。对乙而言，甲的成功提交落在乙读点之后；701 的变化触及乙先前的扫描，乙不能以同一快照再成功提交，已经对 702 做的写要随 Abort 撤回。若交换提交次序，角色可换。题面称“后向”，是因为验证现在提交的事务时去看**已经提交的别人**，不是只防下一位写者。哪怕甲**比乙先开始**，只要甲的提交晚于乙的读点，仍在考察范围。不要用事务 ID 大小替代提交时间。

把读账从“命中过哪些 RID”改写为“按表读过哪些条件”，再用四个变体找遗漏：

- **零命中**：乙找 `qty > 20` 时没有行；甲后来插入货量 25。若乙还是个有写入的事务，这次插入可能推翻它的决定，不会出现在其旧扫描的 RID 列表中。
- **跨边界**：甲把 25 改成 18，乙的谓词是 `qty > 20`；只看改后会漏。反向把 18 改成 25，只看改前也会漏。删除要检查消失前的活行；插入要检查出现后的活行。一个无过滤条件的全表扫描也不能记成“什么都没读”。
- **中间经过**：其他两次提交使货量 `12 → 25 → 12`，乙一直没结束。只比乙的读点与现在，误以为什么也没变；每个提交步都要独立考察。已有行在一笔事务内改了又改回，也不能仅凭两个端点数值相等就略过一次记录级更新。
- **有无逻辑行**：同一事务从无到无（新插又删）不等于从有到无。不要为了保险对所有物理墓碑一律判冲突；也不要为了“提高通过率”对所有更新都判冲突。纯只读事务按本题规则免验，写集不空的才做上述提交验证。

普通 shell 在新的 `BEGIN;` 前执行 `SET global_isolation_level=serializable;`，再用 `\txn` 检查实际隔离级别；Netcat 版用 `./bin/bustub-nc-shell --serializable`。前面示例中改隔离级别并不会重置原数据或改变已开启事务，重演时应另建干净的表。提交期验证失败是 `Commit` 返回 `false` 后的 **ABORTED**；不要把它与 DML 语句失败后还需主动清理的 **TAINTED** 混在一起。

## 公开测试怎么选，怎样避免“一个也没跑”

在固定标签的私有工作副本、已配置的 `build/` 中，例：

```sh
cmake --build . --target txn_timestamp_test
./test/txn_timestamp_test --gtest_list_tests
./test/txn_timestamp_test --gtest_also_run_disabled_tests --gtest_filter='TxnTsTest.DISABLED_TimestampTracking'
```

`--gtest_list_tests` 只列名不执行。下面右列为源码案例短名（**全部实际带 `DISABLED_` 前缀**）；使用 `--gtest_also_run_disabled_tests` 时过滤器也要写实际名字。仅构建目标、仅列清单、或者默认跳过后得到绿色，都不是跑过测试。每个目标可以独立构建，程序在 `build/test/`，不是 `build/bin/`；个别 suite 跨目标，不能把文件名当 suite 名。

| CMake 目标 | 涉及的实际 suite 与案例（按调试问题归类） |
|---|---|
| `txn_timestamp_test` | `TxnTsTest`：`TimestampTracking`、`WatermarkPerformance`；后者用大量时间点分别顺序、逆序移除，不是只看两事务示例 |
| `txn_scan_test` | `TxnScanTest`：`TupleReconstructTest`、`CollectUndoLogTest`、`ScanTest`；独立夹具可在 Insert 前核部分 schema、删除位、临时戳和快照 |
| `txn_executor_test` | `TxnExecutorTest`：`InsertTest`、`InsertCommitTest`、`InsertDeleteTest`、`InsertDeleteConflictTest`；`GenerateUndoLogTest`；`UpdateTest1`、`UpdateTest2`、`UpdateTestWithUndoLog`、`UpdateConflict`；最后 `GarbageCollection`、`GarbageCollectionWithTainted`。差量用例内有墓碑复插场景，会与 4.2 相接 |
| `txn_index_test` | `TxnIndexTest`：`IndexInsertTest`、`InsertDeleteTest`、`UpdateTest`、`UpdatePrimaryKeyTest`；`IndexUpdateConflictTest` 的 suite 实际是 **`GradingTxnIndexTest`** |
| `txn_index_concurrent_test` | `TxnIndexTest`：`IndexConcurrentInsertTest`（4.1 分界的并发争键）、`IndexConcurrentUpdateTest`；`TxnAbortTest`：`IndexConcurrentUpdateAbortTest`，检查跨行更新遭冲突后的撤销，而非只比较胜者个数 |
| `txn_abort_serializable_test` | `TxnAbortTest`：`SimpleAbortTest`、`AbortIndexTest`；`TxnSerializableTest`：`SerializableTest`、`ConcurrentSerializableTest`，分别观察验证与并发提交 |

公开辅助头 `txn_common.h` 里的 `CheckUndoLogNum`、`CheckUndoLogColumn`、`TableHeapEntryNoMoreThan`、`EnsureTxnGCed`、`EnsureIndexScan`、`QueryIndex` 提示你**应观测什么**。例如 `EnsureIndexScan` 切到 starter 规则，用等值查询的 EXPLAIN 核实存在 IndexScan；不能将所有查询降成顺扫来躲开检查。题面说从 Task 3 起以 SQL 驱动，不表示只有外层结果：固定树还直接调用差量 helper，并以 `ReconstructTuple` 做往返检查。某些文件只公开一个测试的一部分，不能从注释补写隐藏预期。

分级记录自己的进展：P3 私有 checkpoint 是否可找回；P4 做到哪个子任务；用的提交和配置；**实际运行的目标、过滤器、执行案例数及首个偏差**；最后才是可选榜单的吞吐、空间、是否保持正确性。不要以“文档写好了”“shell 能启动”“参考 Web Shell 行为正确”填作学习者已完成。本页没有执行上述命令，也没有成绩或排名。

## 引用与来源

- CMU Fall 2025 [项目页，含交互调试、GC、Abort、验证与榜单](https://15445.courses.cs.cmu.edu/fall2025/project4/)；[题面所链官方 Web Shell](https://15445.courses.cs.cmu.edu/fall2025/bustub/)（仅列入口，未操作）；[固定 BusTub 标签](https://github.com/cmu-db/bustub/tree/v20251119-2025fall)及[许可证](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE)。上面的格位、数值与交错为自拟。
- [Undo 格式和事务内接口](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/concurrency/transaction.h#L56-L166)、[表堆读写保护](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/storage/table/table_heap.h#L62-L87)、[原子 helper 的检查参数](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/concurrency/transaction_manager_impl.cpp#L126-L161)、[重建与差量函数说明](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution/execution_common.cpp#L42-L116)。
- [shell 的事务切换和 GC](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/common/bustub_instance.cpp#L444-L488)、[隔离级别与显式事务](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/common/bustub_ddl.cpp#L207-L256)、[Netcat 会话](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/tools/nc-shell/nc-shell.cpp#L48-L85)。
- [测试目标生成和输出目录](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/CMakeLists.txt#L5-L48)；[时间戳](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_timestamp_test.cpp)、[扫描](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_scan_test.cpp)、[执行器和 GC](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_executor_test.cpp)、[索引](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_index_test.cpp)、[并发索引与回滚](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_index_concurrent_test.cpp)、[Abort 与 Serializable](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_abort_serializable_test.cpp)、[公共辅助头](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/txn/txn_common.h)。
