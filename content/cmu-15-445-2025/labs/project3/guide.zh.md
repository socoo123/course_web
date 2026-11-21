---
source: CMU Fall 2025 Project 3；BusTub v20251119-2025fall @ d49b823f829a4bf311a2c80b239ab5a9864c9c41 的执行器、优化器与 SQLLogicTest
license: 原创调试指导和自拟练习；不提供可提交实现，不转载题面或公开测试的答案。
status: 静态阅读；以下私有工作区练习均未代跑，学习者状态 not_attempted。
---

# Project 3 指导：找出第一行是在哪里丢的

面对一条少了两行的查询，先不要改哈希函数。问三个问题：**走的是我以为的计划吗？孩子真的交出了那两行吗？它们的内容、RID 和输出列位置还配得上吗？** 沿着最早出现分歧的那条边向下查，通常比盯着最终结果更快。

[四个任务的要求及例外](#/c/cmu-15-445-2025/lab/project3?v=zh) · [页、pin 与 guard](#/c/cmu-15-445-2025/lab/project1?v=guide) · [B+Tree 与迭代](#/c/cmu-15-445-2025/lab/project2?v=guide)

## 先立一个能手算的对照

沿用 [L13 订单与库存](#/c/cmu-15-445-2025/lec/lec13?v=notes)。这里用小写列名，金额、数量等用 `INT`，字母和仓库名用 `VARCHAR`。订单 `(id, sku, qty)` 是 `(101,A,2), (102,B,6), (103,A,5), (104,C,8), (105,D,7), (106,B,NULL)`；库存 `(sku, depot, available)` 是 `(A,东,9), (A,西,2), (B,东,7), (D,西,8)`。自建表时字符串加单引号。**不在重复的 sku 上建 Project 3 的唯一键索引**；需测索引时另用 `orders.id`。

```sql
SELECT o.id, s.depot
FROM orders AS o INNER JOIN stock AS s ON o.sku = s.sku
WHERE o.qty >= 5;
```

仅等值连接，不额外比较库存数量。手算：订单先由六行变为四行；其中 103 匹配两个仓库，104 一个也不匹配。INNER 的输出仍是四行，但这**不表示每笔订单各匹配一行**。改 LEFT 后保持这四条匹配，再为 104 加一条空右侧。未写最外层 `ORDER BY`，对照的是行的多重集，不是打印顺序。此处是自拟对照，不是运行成绩，也不是公开 `.slt` 的期望输出。

| 分开观察 | 在自己的 shell 中怎么查 | 它不能证明什么 |
|---|---|---|
| 绑定和计划 | 在查询前加 `EXPLAIN`，看查询别名对应的列；再用 `EXPLAIN (o,s)` 指认扫描、连接、投影及各自 schema | 不能证明结果有四行，不能测磁盘 I/O |
| 规则的效果 | 用同一数据、同一 SQL 对比 starter 与默认 custom；没有库存索引时，前者可保留 NLJ，后者在你的规则完成后可改为 HashJoin。以自己打印的节点为准 | 不能把计划中 `HashJoin` 的名字当成分区已经落盘 |
| 运行结果 | 去掉 `EXPLAIN` 后实际执行，比较每行及重数；重试前确认不是在旧表上重复插入 | 结果一致不能证明没泄漏、没超内存，也不能证明更快 |

这条查询在小数据下 NLJ 的比较、建哈希表的开销都很小。把库存放大时，比较次数、分区读写以及匹配结果大小都会变。L15–16 所说的**估计**用于作选择；你记录的实际输入行、匹配行和 I/O 用于事后解释。这里既不是 PostgreSQL `EXPLAIN ANALYZE`，也不是让你给 BusTub 加完整统计模块。

## 第一条边：为什么 20 行都对，第 21 行错？

每次停在 `Next` 返回点时，只记六项：本轮 `Init` 编号、请求容量、孩子的批号和行下标、已交 tuple 数、已交 RID 数、下次继续的状态。调试基表行可记 `(主键, RID)`；调试连接结果记一对输入的逻辑标识，而不是给拼接行虚构一个物理 RID。

- **批长守恒。** 正请求下，成功批非空、不超请求且两向量等长；每一对都来自同一次筛选／发射。父节点可以连续收到短批，不得见短就当 EOF。新调用替换旧输出；返回 `false` 不能让调用者读到上次的尾部。
- **游标守恒。** 一次调用交满，不一定用完一条输入的所有匹配。若在 103 的两个仓库中间停下，下次要继续这笔订单的剩余匹配，既不能重新发第一个，也不能跳到 104。用一个左键对应超过 20 个右匹配可直接触发这种边界；另用 19、20、21 条记录区分批内、恰满和换批。
- **空批不等于耗尽。** 让扫描先遇到一整批已删或全部不满足谓词的记录，后面才有一条活跃匹配。问自己：到底谁知道以后还有没有输入？空候选批不能代替孩子最终的 `false`。
- **重启不是续读。** 在 NLJ 右侧放一个分组或索引扫描，先耗尽一次，再由父节点初始化。上次留下的空标志、待发尾行、哈希表、run、分区游标都不应串入本轮。`p3.12-repeat-execute.slt` 专门搭了右子树；不能靠“每条查询构造一次对象”掩盖第二个外行的问题。

`ValuesExecutor` 可参照如何清空两向量、尊重请求容量及给常量行配占位 RID；`ProjectionExecutor` 和 `FilterExecutor` 可观察行与 RID 如何同步。参照的是接口和数据流，而不是把样例的所有缓冲策略照抄到一个会放大行数的连接里。

## Task 1 调试：值改对了，为什么旧键还查得到？

给一行订单画两个独立视图：堆表记 `(RID, is_deleted_, id, 其他值)`；每个索引单独记 `(按该索引抽出的键, RID)`。在同一张表上对**两个各自唯一的整数列**分别建索引，按“插入一条 → 更新索引列和非索引列 → 删除 → 同键重新插入”停下来对账。每一步既做点查，也从堆上读活跃行；不要只看 DML 返回的计数。

| 观察到的分歧 | 下一处检查 |
|---|---|
| 堆扫描已无旧行，从索引还能看到它 | 查索引键是否按旧行和旧 RID 删除；回表是否看了 `TupleMeta::is_deleted_`。索引命中只给 RID，不替堆表做可见性判断 |
| 改非索引列后，索引找不到行或取出旧内容 | Project 3 的 update 是删后插，**键值未变也可能换 RID**；对账的是每个索引的键／RID 配对，而不是只比较键值 |
| 扫描碰上 update 就反复改同一业务行 | `TableHeap::MakeIterator()` 固定创建时的尾界，`MakeEagerIterator()` 不固定；检查子树是否把本语句新插的版本又当成待更新旧行。索引入口更新时也要能解释待修改集合为何不会被自己破坏 |
| 全表读对，带 WHERE 的 DELETE 改错行 | 同时记录谓词结果和传上来的 RID；筛掉第 i 个 tuple 时是否也筛掉相应 RID？不要按投影值重新猜定位 |
| 删除 0 行没有返回或多次返回计数 | 将“无更多待修改输入”和“已向父节点交过最终计数”分开。判断 `InsertTuple` 等的实际结果，别对每个输入批都发汇总 |

**隔离优化器和访问器。** 先在无索引表跑 `id = 常量`，再建 `id` 的索引，分别打印同一谓词、反写等值、同一键多次 OR 的计划。`IndexScanPlanNode` 的 table OID 和 index OID 不是同一个命名空间。最后加第二列上的条件作反例：一次点查恰好命中不代表 `id = 103 OR qty = 8` 可以只探 103。对有序路径改用 `ORDER BY id` 和 `ORDER BY id DESC`，看哪种方向由已有规则选择。`p3.05` 用 starter，单测默认 custom 的效果不能代替这项验证。

## Task 2 调试：三种“相等”与一个右孩子

分组与连接最容易共用错一套 NULL 语义。为每个结果先写明**问题的类型**：

| 问题 | 相应判断 |
|---|---|
| `WHERE x = y` 或普通等值连接是否通过？ | 只有真才通过；任一侧为 NULL 时不是匹配 |
| 两个 GROUP BY 键是否属于同一组？ | 对同一组位置，两个 NULL 应归同组；`AggregateKey` 的哈希和相等必须相容，尤其要能认回自己的键 |
| `ORDER BY` 比较器应把 NULL 放哪里？ | 这是顺序约定，不是 SQL 谓词的真假；显式优先，否则采用项目的方向默认值 |

聚合的最小对照包括四种输入：零行无分组、零行有分组、有 NULL 聚合参数、分组键包含两个 NULL。写下**应有几行**，再考虑每行各槽保存的是哪种聚合状态。`COUNT(*)` 看行；`COUNT(expr)` 看非空输入；全局空输入的 `COUNT(expr)` 本题另有 `integer_null` 约定。若空表有分组却多一个“默认组”，说明你把全局聚合空输入的特殊结果套给了普通分组。多聚合列要按计划并排，不要让 COUNT 的初始化污染 MIN；`HAVING` 错时先看 Aggregation 的原始输出，再看上方 Filter。

对嵌套循环连接，选**同一份左输入**分别搭空右表、单个匹配、右侧两个不同记录的键相同、以及从不匹配的非等式。记录“哪一左行”“右侧在第几批”“这条左行曾否匹配”。仅仅某个右批不匹配不能补 NULL；要等该左行所需的右输入已经查完。`p3.10/11` 的部分检查还观察右执行器重新 `Init()` 的行为，`InitCheckExecutor` 按成功的 `Next` 调用计数，并非记录磁盘读次数。

对索引连接，相同数据再建右侧**唯一整数键**索引（与前文的重复 sku 分开）。从 `NestedIndexJoinPlanNode::KeyPredicate()` 得到的是用左行求值的探针表达式，不是对拼接结果求布尔条件；读回右行时用右表 schema。`EXPLAIN` 中如果仍有两个扫描孩子，调试的可能还是 NLJ；将右侧写成子查询、改为非等值、或没有匹配索引，不能再期待同一条索引连接规则。先确认 13 号文件所用的 starter 设置，再追索引执行器。

## Task 3 调试：把“同桶”与“匹配”分开验

先验证规则，再验证落页；两种错都能表现成“连接少一行”。

1. **给复合键的每个分量贴来源。** 将左右两表的键列放在不同列号，用两个等式且故意把其中一个反写，再加第三个等式。逐项核对 `LeftJoinKeyExpressions()` 与 `RightJoinKeyExpressions()` 所指是否仍是对应的列，而不是用“在谓词树左边”代替“来自左孩子”。用非等式、OR、两列来自同侧作不应该整段匹配的反例。
2. **分区只决定见面地点。** 记下每一侧输入和各分区的行数，先检查保留下来参与匹配的行有没有在分区交接时丢失或重复。相等复合键必须去可配对的分区；不同键进同一区很正常。再问分区内真正的键比较是否检查了所有分量，对 NULL 的普通等值比较是否会误判。
3. **多重集与 LEFT 记账。** 一个非空键，左边重复 $m$ 行、右边重复 $n$ 行时，INNER 应有 $mn$ 个组合；右边没有匹配时，每条左行各有一条空扩展，而不是“这个键”共补一次。逻辑上的左／右与物理选择的 build／probe 不是同一件事；如果改变后者，先证明未匹配左行的记录方式仍成立。
4. **给内存设上限。** 分别写下持有的分区页 ID、当前 pin 的页及真正常驻的 tuple／哈希状态。只把所有行复制到内存后再象征性写几页，并没有实现 Grace。一个倾斜的热键也提醒你：平均分区小不等于每个分区小，原样再次用同一映射不保证它缩小。题面没有给出评分器的分区个数或倾斜阈值，不要把猜出的常数当作契约。
5. **换一个观测量。** `p3.14` 有由笛卡尔积生成的 `big_l`、重复键与最多四个等值条件，`p3.15` 有一棵树内多处 HashJoin。`.slt` 的结果比较只能观察关系结果；用调试器看分区页是不是在用、一个批次返回时是否仍持有无用 guard，才能分辨内存 HashJoin 与真正的外部执行。不要为了通过检查改 runner 或删除 `+ensure`。

一个可检验的问题：若两个不同复合键碰撞，而同一真实键在右边重复两条，错误实现有哪些表现？只依哈希判断会**多出假匹配**，用键覆盖旧值会**漏掉真匹配**；两种错误的总行数甚至可能相抵。因此对照 NLJ 时必须看**行内容与重数**，不能只对 `COUNT(*)`。

## Task 4 调试：顺序对了，页也要还清

### 先只检验一个排序键和一页

给比较器独立列一张真值表：相等值、两个 NULL、只有一侧为 NULL、反方向、两个首键相同但次键不同的记录。请自己回答：`a` 是否排在自身前面？`a` 在 `b` 前时，反向还能同时为真吗？仅把 ASC 的布尔结果取反会把相等变成“小于”，破坏严格弱序。`OrderBy` 是**方向、NULL 次序、表达式**三元组，排序键需按当前输入 schema 求值，不能假定它永远是第 0 列或原始列值。

临时页先不做归并：画出“哪些字节是元数据，哪些字节是可读 tuple，有几字节尚可用”。构造相同列数但字符串长度不同的行，依次尝试空字符串、多字节字符串、恰好剩余空间、差一点放不下。`Tuple::GetLength()` 是数据体字节数；若采用 `Tuple::SerializeTo`，它还写一个长度前缀，**不序列化 RID**。请按你选择的格式算准大小，不要把 `sizeof(Tuple)` 或进程里的 `std::vector` 指针写进页。重取页面时原对象地址可能已失效；验证能否用页内信息还原同一列值，而不借用已释放 guard 后的指针。

### 再把多页看作一个 run

用含三页的 run，把最后一页做成不满。在页末 `++` 一次后，读取的应该是**同一 run 的下一页首行**或 `End()`，不是物理 page ID 自增后的页面。两个 run 各自第一个位置不应被误判相同；`End()` 不能解引用。对每轮归并并排记四个数：输入行数、输出行数、输出内部逆序对是否为零、仍由各 run 持有的页 ID。每轮行数须守恒，对于 5 个初始 run 的两路归并，还要说明未配对的第 5 个 run 在下一轮归谁；不能偷偷复制或删掉它。

临时页账与 buffer frame 账分开：`NewPage()` 给的是页 ID；`ReadPage`／`WritePage` 产生 guard；`DeletePage` 回收不再需要的页。一个 run 有 100 页，不表示可以把 100 个 guard 都一直拿着。设计时安排三种结束路径：归并淘汰旧段、正常读完最终段、父 `Limit` 达标后不再调用子节点。任一时刻都要能回答“谁还会读此页、谁负责释放”，否则可能是顺序完全正确却超预算或留下僵尸页。无需自行调用磁盘层模拟刷盘。

`p3.16` 既有简单 LIMIT，也有多列不同方向、带 NULL 与 `VARCHAR`、表达式排序、嵌套 `ORDER BY … LIMIT`、跨多个排序页和连接的查询。`__mock_external_merge_sort_input` 在该标签的生成器规模为 100,000 行；不要用在这份模拟表上全体内存排序的偶然成功，取代外部算法。Limit 自测用 0、小于一批、恰到批边界、大于输入长度；看它是否**跨所有批次只计一个上限**，并逐项对齐保留下的 tuple 与 RID。

### 最后检验窗口：“一个值贴给哪一行？”

自拟三笔订单：同一客户，金额 30、30、50，另一个客户只有一笔。分别画四列：原订单标识、分区、排序后的 peer（同序键行）组、各行的名次。自问：两笔 30 能否同名次？50 是第二名还是第三名？换客户能不能沿用上一客户的名次？然后把窗口换成无 `ORDER BY` 的分区求和；同一分区每行应挂同一个总额，而不是输出一行总额。再用**不重复的**顺序键看有序累积与整组总额的区别；不要用 `RANK` 的并列测试去推断公开用例没有规定的所有 frame 同分细节。

同一句 SELECT 同时放普通列、按客户 `SUM` 和全体 `SUM`，两个窗口用同一顺序键但不同分区。对账的是**每个原订单**收到的两个值，不是两列各自的值集合。`window_functions_` 以输出列下标索引；普通列的表达式按孩子的 schema 求值，planner 为窗口列预留的位置不能当真实输入列求值。空输入要区别于无分组的普通聚合：窗口没有可贴结果的输入行，因此没有输出行。`p3.20` 有并列 `RANK` 和不同分区的多窗口；题面开头的滑动平均不是 planner 的功能清单。

## 最短排错路径：先找失败所属层

| 现象 | 下一步只看这里 |
|---|---|
| 结果似乎正确，runner 却说没用索引／连接节点不符 | 查看实际 `EXPLAIN (o,s)` 与本文件里的 `force_optimizer_starter_rule`；弄清是规则没进调用链、前置形状没形成，还是误把顺序索引当点查 |
| SQLLogicTest 在第一个差异行报错 | `query rowsort` 按整行排序后比较、保留重数；普通 `query` 默认按原顺序。`-d` 可把两侧差异写到文件。先分清是值、列位置、重数，还是顺序 |
| 检查提示重启异常，单次执行正常 | 最小化成一条左记录多匹配，再让右子树作为 NLJ 内侧重复执行；观察孩子 `Init`、成功 `Next` 和未交完的尾部 |
| 耗尽、并列、空表之一处理不对 | 优先对照 `p3.06/07/08/12/20` 中该分支的语义，不要去改 binder 或引用另一学期实现 |
| 所有小结果对，大表慢或崩 | 在固定 `--bpm-size` 下分别记录创建／释放页、pin 峰值、批容器保留的行；runner 另有 `--check-min-disk-write`、`--check-max-disk-write`、`--check-min-disk-delete`，阈值须明确设定，不能声称默认就做了全部检查 |
| 组合查询错，单个算子各自看似正常 | `p3.18` 的图查询按嵌套层次逐层比较，`p3.19` 通过中间表物化；两者都问“哪一次 join／聚合后行数或值第一次不同？”19 的文件注释建议 Release、至少 60 秒，不等于公开了线上时限 |
| `test-p3` 包含不打算实现的 TopN 或很慢的榜单 | 对照要求页的**注册清单与评分范围之别**，分文件检查本阶段；不要改测试、把零分项升格为必做，或声称本地总目标就是官方成绩 |

<details>
<summary>自测：规则把一个 LEFT JOIN 改成 HashJoin 后，INNER 查询都对，LEFT 独独少一行。先检查什么？</summary>

先看新节点的 join type 和左右输出 schema；若它们保持不变，再给一个键能路由到正确分区但没有精确匹配的左行。检查它是在分区时被丢掉、被碰撞误判匹配，还是在探测完成后根本没发出空扩展。若仅在跨批时错，再看“这条左行是否匹配过”的状态何时清零。这些观察可区分计划错误、路由错误和发射错误。
</details>

<details>
<summary>自测：排序结果对、ASan 没报错，能说明满足外部排序要求吗？</summary>

不能。进程内的一个完整数组可以排序正确，也可能从未访问非法内存；遗留在缓冲池管理下的临时页也未必触发 C++ 内存泄漏报告。还要分别证明中间数据确实落在临时页、同时驻留的有效数据有限、过期页及最后一批不再访问的页能够回收。
</details>

## 参考与来源

- [Fall 2025 正式项目规范](https://15445.courses.cs.cmu.edu/fall2025/project3/)；[使用的 BusTub 提交](https://github.com/cmu-db/bustub/commit/d49b823f829a4bf311a2c80b239ab5a9864c9c41) 与[仓库许可](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE)。例子、账本和排查顺序为本站原创，未执行官方项目或提供实现。
- 行流：[引擎 `PollExecutor` 和 NLJ 检查](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/execution_engine.h)、[`ValuesExecutor`](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution/values_executor.cpp)、[目录与索引](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/catalog/catalog.h)、[堆表迭代尾界](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/storage/table/table_heap.cpp)、[表达式的左右输入](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/expressions/column_value_expression.h)。
- 阻塞与外存：[聚合哈希表](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/executors/aggregation_executor.h)、[分组键](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/plans/aggregation_plan.h)、[哈希键向量](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/plans/hash_join_plan.h)、[tuple 序列化](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/storage/table/tuple.cpp)、[比较器和排序键](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution/execution_common.cpp)、[窗口输出槽](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/plans/window_plan.h)。
- 直接阅读 SQLLogicTest：[索引 DML](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.05-index-scan-btree.slt)、[空输入聚合](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.07-simple-agg.slt)、[重复执行](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.12-repeat-execute.slt)、[索引连接](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.13-nested-index-join.slt)、[复合键／大输入](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.14-hash-join.slt)、[多路哈希连接](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.15-multi-way-hash-join.slt)、[外部排序与 Limit](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.16-sort-limit.slt)、[窗口函数](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.20-window-function.slt)、[注册表](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/CMakeLists.txt)、[runner 的比较与检查](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/tools/sqllogictest/sqllogictest.cpp)。
