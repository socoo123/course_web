---
source: CMU 15-445/645 · Fall 2025 · Project #3 — Query Execution；BusTub v20251119-2025fall @ d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 原创中文要求导读；未确认项目网页授权全文翻译。官方代码库另用 MIT 许可。
status: 四项必做任务、可选榜单与公开 SQLLogicTest 已静态核对；未运行学生项目，学习状态 not_attempted。
---

# Project 3：让同一条 SQL 换计划，不换结果

一笔订单有两个能供货的仓库。把嵌套循环连接换成哈希连接，两条匹配都得留下；把查询改成左连接，没有仓库的订单也得留下。**计划决定怎么取数，执行器要保证交出来的仍是同一张结果表。** 这个项目要把这样的承诺落实到批边界、表中的物理记录和临时磁盘页。

[实验指导：如何定位第一处偏差](#/c/cmu-15-445-2025/lab/project3?v=guide) · [L13 批量执行](#/c/cmu-15-445-2025/lec/lec13?v=notes) · [L15 计划变换](#/c/cmu-15-445-2025/lec/lec15?v=notes) · [L16 计划选择](#/c/cmu-15-445-2025/lec/lec16?v=notes)

## 交付边界

| 必做任务 | 交付什么 | 如何区分它与下一项 |
|---|---|---|
| 1 · Access Method Executors | 堆表读写、维护所有相关索引、两类 B+Tree 扫描、点查计划改写 | 此时可自建真实表，不必依赖模拟表 |
| 2 · Aggregation & Join Executors | 内存分组聚合、普通嵌套循环连接、索引嵌套循环连接 | 有了可作语义对照的 INNER／LEFT 连接 |
| 3 · HashJoin Executor and Optimization | **Grace Hash Join**、中间分区页、等值连接计划改写 | 即使整侧不适合装入内存也能执行；不是单个常驻哈希表 |
| 4 · External Merge Sort + Limit Executors + Window Functions | 两路外部归并、Limit、分区／有序窗口和 `RANK` | 排序要能落页；窗口不把同组多行折成一行 |

这是个人项目。Fall 2025 作业表列出发布日 **10 月 20 日**（课表挂在 L13），而 **10 月 22 日**的 [L14 开场](#/c/cmu-15-445-2025/lec/lec14?v=draft)口头说“今天发布”；两者的截止日同为 **11 月 16 日**。作业表写 **23:59**，未标时区；题面最后更新于 **11 月 6 日**。下文的 01–06 等是题面建议的**功能检查点**，不是额外的分期提交日期。

保留可恢复的私有 Project 3 版本；前置的是自己可用的 [Project 1 缓冲池](#/c/cmu-15-445-2025/lab/project1?v=guide) 和 [Project 2 B+Tree](#/c/cmu-15-445-2025/lab/project2?v=guide)。题面当年说拉最新 `master`，今天复现应使用页底的学期标签与完整提交；不要把正在变化的主线或后续项目的 MVCC 实现混进来。

## 开始前：读懂一次调用

在 shell 用 `\dt` 区分模拟表与真实表。`MockScan` 按预定方式生成行，不能拿修改模拟表来验证 DML。用 `CREATE TABLE` 建自己的表；题面示例以 `INT`、`VARCHAR(n)` 和单引号字符串为主，普通语句用分号结束。这里不是完整的 SQL 产品，不依赖 `DROP TABLE`／`DROP INDEX` 来重置样例。CLion 终端有交互问题时，题面建议启动 shell 时加 `--disable-tty`。官方 Web Shell 可作公开行为参考，不能证明你的私有实现正确。

`EXPLAIN` 展示绑定结果、planner 计划和 optimizer 计划；`EXPLAIN (o)` 只看优化后树，`EXPLAIN (o,s)` 一并看节点输出 schema。绑定器把 `*` 展开，planner 建树，优化器可消除不改变列的投影。`#0.1` 的 **0 是输入编号，1 是该输入内从零开始的列号**；二元连接中的 `#1.0` 才是右输入的首列。`Projection` 可计算表达式，`Filter` 以谓词选行，`Values` 产生常量行。最后由 `ExecutorFactory` 递归构造执行器。**打印计划没有执行这棵树**，不会给实际输出基数、读写页数或运行时间。

固定版本 `AbstractExecutor` 的调用顺序是 `Init()` → 多次 `Next(tuple_batch, rid_batch, batch_size)`，`GetOutputSchema()` 说明父节点如何解释这些行。这里是两个输出向量和本次请求的容量，返回值是 `bool`；不是旧注释所写的单行 `Next(Tuple*, RID*)`。执行引擎默认请求 `BUSTUB_BATCH_SIZE = 20`，具体调用以传入的 `batch_size` 为准。对于正容量，每次成功给 **1 到容量** 个 tuple，RID 向量与之等长且逐项配对；耗尽才返回 `false`。调用方会复用容器，下一批不应掺入上一批的数据。一个孩子的批次全被筛掉不是 EOF。`Init()` 再次调用时，子树必须能从头执行。

源表扫描输出匹配行的副本及其**原 RID**（页号、槽号）；过滤和投影示例保持配对。常量、计数、分组或拼接出的行不应自称是某个可写的基表记录：没有单一物理记录仍需配一个占位 RID；`ValuesExecutor` 使用无效的 `RID{}`。最终结果不仅要数量对，列数、类型和位置也要与本节点的输出 schema 一致。

## Task 1：同一张表，要能从堆表和索引两条路读到

| 执行器 | 输入 → 输出 | 必须维护的事实 |
|---|---|---|
| `SeqScanExecutor` | 从 catalog 找表，无孩子 → 活跃且满足下推谓词的行与原 RID | 读 `TupleMeta::is_deleted_`，谓词只接受真，不发已删除、假或未知的行；`TableIterator` 提供前置 `++`、`GetRID()`、`GetTuple()`、`IsEnd()` |
| `InsertExecutor` | 一个孩子（可以是 `Values`，也可以是查询）→ 一行整数 | 数据满足目标表 schema；插入 `TableHeap`，用新 RID 维护该表的**每个**索引；统计实际插入行数 |
| `UpdateExecutor` | 一个孩子给旧行与旧 RID → 一行整数 | 用计划 `target_expressions_` 求新值；按本学期要求**旧行标删，再插新行**，旧／新索引项对应各自 RID；一次更新只计一行，不调用 `UpdateTupleInPlace` |
| `DeleteExecutor` | 一个孩子给待删行与 RID → 一行整数 | 按原 RID 改元信息并移除对应索引项；项目允许假设 Delete 在根，不把被删的行流回父节点 |
| `IndexScanExecutor` | 由 table/index OID 定位 → 符合条件的活跃表行与原 RID | 用 `ScanKey` 点查得到 RID 后回表；按索引顺序扫描则用树迭代器；两条路径都不能吐出表中已删除的行 |

三个 DML 的整数都是**整条语句一次**的结果，影响零行也交一行 0；不能每个子批交一次或把子批长度当最终计数。`Catalog::GetTable`、`GetIndex`、`GetTableIndexes` 对应表、指定索引、表上的索引列表。索引键按本索引的 key schema 和 key attributes 从表行投影，不是把整行一律当键。普通场景限单列、唯一整数索引键；`BPlusTreeIndexForTwoIntegerColumn` 是固定版本真实类型名，不要求把必做题扩成复合／重复键索引。

**需要写的规则：`OptimizeSeqScanAsIndexScan`。** 已有 `OptimizeMergeFilterScan` 可把独立 Filter 合入尚未携带谓词的 SeqScan，所以 SeqScan 自身必须会筛选。单个 `键 = 常量`、`常量 = 键`，以及在**同一索引列**上用 OR 联结的多个这样的点查都要识别。`IndexScanPlanNode` 除 `filter_predicate_` 还有 `pred_keys_`。同一个键重复出现不能令输入的一行重复返回。无索引、跨列 OR、`a = 1 AND b = 2` 等不属于这个点查改写；不要丢掉谓词的一半。另一条路径是 **ORDER BY 索引列**：已有 `OptimizeOrderByAsIndexScan` 匹配排序列与索引键，执行器只需支持 ASC／默认升序的有序扫描；不是要求倒扫或通用范围扫描。

## Task 2：分组消行，连接可能增行

**聚合。** `AggregationExecutor` 有一个孩子。`SimpleAggregationHashTable` 可以全放内存，不必像 Task 3 那样分区；需要补 `CombineAggregateValues`，并让执行器建表后按组输出。输出 schema 先列出分组键，再放聚合结果；`HAVING` 的过滤由上层 Filter 执行。要覆盖 `COUNT(*)`、`COUNT(expr)`、`SUM`、`MIN`、`MAX`、多列分组、表达式，以及借分组去重的 `DISTINCT`。

不要用一个“NULL 等于什么”规则包办全部情况。分组键同位置的 NULL 可以归入同组；普通 `=` 产生未知不等于“属于不同组”。聚合参数的 NULL 不应当普通的 0 参与求和、比较或 `COUNT(expr)`，而 `COUNT(*)` 数行。**空输入、没有 GROUP BY** 时仍输出一行；按此版本题面和 `p3.07`，只有 `CountStarAggregate` 为 0，`COUNT(expr)` 也同 `SUM/MIN/MAX` 返回 `integer_null`。这点不能照搬其他数据库。**有分组键且空输入**则一个组也没有。建表是流水线阻塞段，何时建、何时遍历由你设计，但新一次 `Init()` 不得带上老分组。

**嵌套循环。** `NestedLoopJoinExecutor` 有左右两个孩子；必做 INNER 与 LEFT，包括非等值谓词。对**一对**输入用 `EvaluateJoin` 和各自的 schema 求值；只有真才匹配。同键不同记录全部保留，输出列始终是左后右。左连接的某一左行在**整个右侧**都无匹配时，才输出一次该左行和按右侧类型填充的 NULL。右子树不只是可倒回的数组，也可能是分组、扫描或另一个连接。

**索引嵌套循环。** 计划、执行器和计划打印名分别为 `NestedIndexJoinPlanNode`、`NestedIndexJoinExecutor`、`NestedIndexJoin`。已有改写可识别右侧为带匹配索引的 SeqScan、两侧列之间单个等值条件的 NLJ。新执行器**只有一个孩子**：左侧每行用 `KeyPredicate()` 求探针键；右侧通过内表／索引 OID 和 `InnerTableSchema()` 回表，不再从第二个孩子拉批。仍要支持 INNER、LEFT 并按左后右输出；题面不要求处理索引中离奇的 NULL 特例，但不能忽略普通的左侧未命中。

## Task 3：不是把 NLJ 改个名字

先使 Task 2 的 NLJ 正确，再以它作对照。`OptimizeNLJAsHashJoin` 应接受**任意个**由 AND 联结的、左右两侧列之间的等式（单个也算）；每个等式中左右列书写次序可独立翻转。识别依据是表达式结点与 `GetTupleIdx()`，不是表名、字符串打印结果或“等号左边一定属于左孩子”。新 `HashJoinPlanNode` 的两组键表达式要一一对应，保留原 join type、孩子与输出 schema。只有一个键上相等、其余条件错配的两行不能相连。非等值、OR、同侧比较等不能整个丢掉，基本规则无法等价改写时保留原计划。对逗号连接，先合并合适的 Filter 与 NLJ，才能在 join 谓词里看见等式。

`HashJoinExecutor` 交付的是 **Grace Hash Join**：整侧输入不保证放得进内存，需要把两侧按兼容的复合键分区，将中间结果写入缓冲池管理的临时页，再在匹配的分区对内建表／探测。题面的 “up to 4KB tuples” 是描述哈希表容量受限，不等于“页长 4 KiB”“能放 4096 行”或“允许把所有桶放在 C++ 容器”。该标签实际 `BUSTUB_PAGE_SIZE = 8192` 字节。`IntermediateResultPage` 只是让你设计布局和读写接口的骨架；可与 Task 4 共用，也可为排序另设布局。

输出语义仍与 NLJ 相同：内／左连接、左后右、有重复键时所有匹配的组合。**同哈希值不是键相等**，同一个分区里的不等键不能互连。build 完成之前的“未找到”不能用于左连接补空。题面给出的访问器拼写 `GetLeftJoinKey()`／`GetRightJoinKey()` **不是固定头文件接口**：实际是 `LeftJoinKeyExpressions()`／`RightJoinKeyExpressions()`，都返回表达式向量。该项目不要求实现完整代价优化器或并行连接。

## Task 4：外部归并、Limit 和窗口

**排序。** 有适用的升序索引时可能直接利用 Task 1；否则计划是 `SortPlanNode`，工厂真正构造 `ExternalMergeSortExecutor<2>`，不是旧的 `SortExecutor`。全表不能放内存。先得到许多内部有序的 run（有序段），中间结果**在临时页中**，每一轮归并已有 run，最后按批产出。允许 `std::sort` 排能放进**一个排序页**的数据，不允许对所有输入一次内存排序。虽有模板参数 K，本学期只测**两路**。

- `TupleComparator` 与 `GenerateSortKey` 在 `execution_common.cpp` 仍是骨架。按 `GetOrderBy()` 给的表达式依次比较，可混用 ASC、DESC 与 `NULLS FIRST/LAST`。默认方向 ASC；本项目默认 **ASC 时 NULL 在前、DESC 时 NULL 在后**。前一个键相同才看后一个；不能用排序方向翻转掉显式的 NULL 顺序。题面不要求为完整排序键打平规定稳定的行次序，窗口 `RANK` 的并列另论。
- `MergeSortRun` 持有排序页 ID 和 BPM；`Begin()`、`End()`、迭代器的解引用、前移与比较都要理解为**跨页的同一条有序序列**。入／出 schema 不变。紧凑页格式要能保存含 `VARCHAR` 的变长 tuple；题面保证这样的单个 tuple 不需跨两页存储。当前页放不下就换页，不按“每行一样长”计容量。
- 页的持久读写由缓冲池完成。上一轮用完的页和最后不再需要的页必须实际回收，防止留下无人再访问的“僵尸页”；放掉 guard 只是不再 pin，并不是 `DeletePage`。外存排序的正确性既包括**行顺序**也包括**资源用量**。

**Limit。** `LimitPlanNode::GetLimit()` 是整条流的上限；余量小于一个批次时只交剩余条数，子输入更短则原样结束，不改变 schema。不要求 `OFFSET`。可先写 Limit，但题面没有单独完成 Limit 就算过 Task 4 的检查点，它和排序一起验证。

**窗口。** `WindowFunctionExecutor` 不像聚合那样每组只交一行，而是为**每个输入行**计算窗口列。没有 `PARTITION BY` 时全体是一个分区；否则各分区独立。没有窗口 `ORDER BY` 的聚合窗口看整个分区；有序时按题面的默认窗口处理到当前行，公开聚合前缀例用不重复的排序键。`RANK` 必须带窗口顺序，同分区排序键相同的行名次相同，下一名留空档。不要推出普通排序必须消除并列，或把 `RANK` 写成 `ROW_NUMBER`／`DENSE_RANK`。

同查询可以有多个窗口函数，**窗口 ORDER BY 必须兼容**（固定 planner 比较项数、方向、NULL 顺序和表达式），但函数和分区键可不同；`window_functions_` 的键是输出列下标，不能把遍历哈希表的次序当 SELECT 列次序。普通列及各窗口值必须同属原输入行。固定工厂支持 `COUNT(*)`、`COUNT(expr)`、`SUM`、`MIN`、`MAX`、`RANK`。题面以 `AVG` 和显式滑动 frame 说明概念，不是让你实现这两项；不要求自定义 frame 或一条查询里的不同窗口排序。**窗口内部顺序不是最外层 SQL 的 ORDER BY 保证**；固定公开文件中少数有序窗口 `query` 没开 `rowsort`，其实际期望行序仍需阅读。

## 哪些优化是现成的，哪些不是？

BusTub 的机制是按次序应用规则。通常先处理孩子，再在带新孩子的节点上验证形状和语义条件；不适用时仍保留孩子的改写。下面的名字是该提交的函数名，不能只根据实现文件是否存在判断规则是否运行。

| 路径 | 固定入口的调用顺序（均省略前缀 `Optimize`） |
|---|---|
| `force_optimizer_starter_rule=yes` | `MergeProjection` → `MergeFilterNLJ` → `NLJAsIndexJoin` → `OrderByAsIndexScan` → `MergeFilterScan` → `SeqScanAsIndexScan` |
| 默认 `OptimizeCustom` | `MergeProjection` → `MergeFilterNLJ` → `NLJAsHashJoin` → `OrderByAsIndexScan` → `SortLimitAsTopN` → `MergeFilterScan` → `SeqScanAsIndexScan` |

`MergeProjection` 消去保持列位置与类型的冗余投影；`MergeFilterNLJ` 在 NLJ 既有条件恒真等前提下合并上层谓词并重定位左右列号；`MergeFilterScan` 合并扫描与过滤。`NLJAsIndexJoin`、`OrderByAsIndexScan` 也已有实现。**两个必写改写**是 `SeqScanAsIndexScan` 和 `NLJAsHashJoin`：骨架直接返回原计划。强制 starter 不会调 HashJoin 规则，默认链也没有调用索引连接规则。`SortLimitAsTopN` 虽在默认调用链，骨架不改写；`OptimizeEliminateTrueFilter` 已有实现、`OptimizeColumnPruning` 是骨架，两者都未列入这两条初始链。`EstimatedCardinality` 识别特定表名后缀，是可选优化的辅助估计，不是从真实行数收集的统计。

### 去哪里找每个任务的骨架？

执行器通常是一对文件：`src/include/execution/executors/<名字>_executor.h` 定义状态与接口，`src/execution/<名字>_executor.cpp` 是实现；计划节点在 `src/include/execution/plans/`，不要把计划里描述的查询变成跟着某一次 `Next` 改变的游标。

| 任务 | 上述文件名里的 `<名字>` | 同时阅读／涉及的其他文件 |
|---|---|---|
| 1 | `seq_scan`、`insert`、`update`、`delete`、`index_scan` | `src/optimizer/seqscan_as_indexscan.cpp`。注意这里文件名是 `seqscan`，执行器文件才是 `seq_scan_executor.cpp` |
| 2 | `aggregation`、`nested_loop_join`、`nested_index_join` | `src/include/execution/plans/aggregation_plan.h` 的分组键；`CombineAggregateValues` 在 `aggregation_executor.h`，不是独立的哈希表实现文件 |
| 3 | `hash_join` | `src/optimizer/nlj_as_hash_join.cpp`、`src/include/storage/page/intermediate_result_page.h` |
| 4 | `external_merge_sort`、`limit`、`window_function` | `src/execution/execution_common.cpp` 中排序部分、上面的中间结果页；同一文件中的 undo／MVCC 不属本项目 |

## 可选排行榜：不影响基本满分

| 题面场景 | 建议方向 | 不能牺牲的语义 |
|---|---|---|
| Q1：三表连接，条件都堆在 WHERE | 拆出跨表等值键，将可下推的单表条件提前 | 仍需满足所有旧谓词，不能漏掉重复行 |
| Q2：宽聚合上面只取少数列，左连接的右侧恒空 | 列裁剪、去重复计算、恒假过滤化为空输入；`column_pruning.cpp` 可作起点 | 空右侧不等于左连接整体为空；上层表达式的输入列号仍需有效 |
| Q3：两侧很大但交集很小 | 给 HashJoin 的 build 键附加 Bloom filter 降低无效探测 | 阳性仍需精确比较；LEFT 时拒绝匹配不等于抛弃左行 |

不要求通用连接重排或跨所有算子的谓词下推。题面明确：本项目榜单超时或段错误不影响基本分，榜单数据会随机化；申请 bonus 的实现要经助教人工检查，不能用 late days。允许针对**计划类别**做正确优化，不许按用例名字／内容硬编码结果或侦测评分环境。新规则不能破坏基本用例，有些测试强制使用 starter。网页源中的“报告 planner bug 加分”是被注释掉的旧文字，不是本学期公布的奖励。

## 检查点、质量与提交

使用 `test/sql/`（单数 `test`，不是题面导言的 `tests/sql`）：

| 文件编号 | 能看到什么 | 怎么解释 |
|---|---|---|
| `p3.00` | runner 入门，查询模拟表 | 题面给的单文件入口，不在本标签的 CTest 注册表中 |
| `p3.01–06` | 扫描、插／改／删、B+Tree 点查和有序扫、空表 | Task 1 检查点；05 还用计划形状检查 |
| `p3.07–13` | 空表／分组 NULL、聚合、简单和多路连接、右子树反复初始化、索引连接 | Task 2 检查点；12 验重复执行，13 用 starter 检查 `NestedIndexJoin` |
| `p3.14–15` | 多列、多路、左哈希连接，大输入，部分用例要求无剩余 Filter | Task 3 检查点；不是看到 `HashJoin` 字样就证明外部算法正确 |
| `p3.16`、`p3.20` | 外部多页排序、NULL、变长字段、Limit；窗口前缀、分区、多函数及并列排名 | Task 4 直接相关；16 内也有要求 HashJoin 的组合查询 |
| `p3.18–19` | 图路径的连接、聚合、排序、嵌套／物化后反复查询 | 端到端集成；旧注释说用定长图标签，不撤销 2025 的 `VARCHAR` 排序要求 |
| `p3.17-topn.slt` | 文件里有 `+ensure:topn`，也被 CTest 注册，但文件头写 **0 pts，Fall 2025 - TopN Not Implemented** | 不能把 `TopN`、`TopNPerGroup` 或 `Sort + Limit → TopN` 升格为第五项必做 |

`test-p3` 的实际匹配范围是**所有已注册的 `SQLLogicTest`**：含三个 `p0`、`p3.01–20` 和 `p3.leaderboard-q1/q2/q3`。另有实际存在的 `p3.leaderboard-q1-index.slt`、`p3.leaderboard-q1-window.slt`，未注册于该列表，也不是题面增设两个榜题。项目页 Testing 明说 P3 的用例公开、没有隐藏用例；这项承诺不等于本地注册集合逐项对应线上分值，不等于已证明内存／页管理正确，更不保证榜单数据、时限或人工评审结果一致。

**留给学习者在私有 BusTub 的已配置 `build/` 中运行**（不是本站执行记录）：

```sh
cmake --build . --target shell sqllogictest
./bin/bustub-shell
# 离开交互 shell 后：
./bin/bustub-sqllogictest ../test/sql/p3.00-primer.slt --verbose
```

每次改实现后重新编译 runner，再有针对性地替换 `.slt` 文件。官方质量标准同时要求正确结果、无内存错误／泄漏、符合 Google C++ 风格；网页说明格式／静态检查失败会令项目成绩为零。`make format` 会改文件，`make check-lint`、`make check-clang-tidy-p3` 检查；用 Debug 和 sanitizers 查内存，题面提醒 macOS 通常只能用 ASan 而无此处 Linux 的 LSan。调试时 `BUSTUB_ASSERT` 在 Release 不执行，不要在断言中藏必要操作；需总生效的条件用 `BUSTUB_ENSURE`。编译配置陈旧时用新的独立构建目录。按根 `CMakeLists.txt`，从构建目录运行 `make submit-p3` 在项目根打出 `project3-submission.zip`，只包含列入 `P3_FILES`（并含 `P2_FILES`）的文件，不能假设任意新增文件都会进入提交包。

迟交见大纲；只允许讨论高层概念，不能抄白板、查看／复制其他学生实现或公开自己的解答。课程问题走 Piazza，成绩以课程方为准。本站没有代写、执行、提交或验证 Gradescope 登录后的评分。

## 来源与许可

- CMU 15-445/645，Fall 2025：[Project #3 全页](https://15445.courses.cs.cmu.edu/fall2025/project3/)（含各任务、榜单、公测与提交政策）、[学期作业表](https://15445.courses.cs.cmu.edu/fall2025/assignments.html#project3)、[大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html#late-policy)。本页为原创导读，不是题面全文翻译。
- CMU Database Group，BusTub：[学期标签](https://github.com/cmu-db/bustub/tree/v20251119-2025fall)、[固定提交](https://github.com/cmu-db/bustub/commit/d49b823f829a4bf311a2c80b239ab5a9864c9c41)、[仓库 MIT 许可](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE)。代码许可不移用于题面、视频或教材。
- 固定源码：[批接口](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/executors/abstract_executor.h)、[常量](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/common/config.h)、[执行器工厂](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution/executor_factory.cpp)、[计划节点全集](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/plans)、[执行器实现目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/execution)。
- 关键合同：[哈希连接键](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/plans/hash_join_plan.h)、[临时页](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/storage/page/intermediate_result_page.h)、[外部排序 run](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/execution/executors/external_merge_sort_executor.h)、[窗口规划](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/planner/plan_window_function.cpp)、[窗口函数工厂](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/planner/expression_factory.cpp)。
- 规则：[强制 starter 链](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/optimizer/optimizer.cpp)、[默认 custom 链](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/optimizer/optimizer_custom_rules.cpp)、[所有规则源码](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/optimizer)。
- [SQLLogicTest 原文件](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql)、[注册清单](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/CMakeLists.txt)、[0 分 TopN 文件](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/sql/p3.17-topn.slt)、[打包与质量目标](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/CMakeLists.txt#L324-L376)。上述为静态阅读；没有发布学生答案或测试的结果集。
