---
source: CMU 15-445/645 Fall 2025 官方课表、大纲、FAQ；Database System Concepts 第七版官网与目录；BusTub 固定标签
license: 本页为编者原创导航；视频、教材、讲义、实验网页和代码各自适用独立许可，不相互外推。
---

# 数据库系统：公共资料与准备路线

## 先追踪一条订单查询

把目标设成回答一个完整问题：**一条 SQL 从提交给数据库，到读出正确结果并可靠地保存修改，中间经过了什么？**

例如，查出尚未发货且库存足够的订单：先明确表、键和查询语义，再考虑记录怎样存入页、哪些页进入缓冲池、索引是否有用、连接和排序如何执行。加入两个同时扣库存的事务，再追问谁能看见哪个版本；最后在提交前后模拟宕机，区分日志持久化、数据页落盘与客户端收到回复。

本路线采用 **Andy Pavlo 的 CMU 15-445/645 Fall 2025**，保留 25 个官方讲次。课程主要讲数据库内核，不等价于 PostgreSQL/MySQL 的完整生产运维教程。BusTub 是教学系统；其简化实现和固定接口不能直接套作商业数据库的行为。

## 学习顺序与材料分工

| 阶段 | 讲次 | 先能回答的问题 | 动手衔接 |
|---|---|---|---|
| 查询的含义 | L1–3 | 文件为什么不够？关系代数与 SQL 分别描述什么？记录和页有什么区别？ | C++ 准备、HW1、官方 Project 0 |
| 存储与缓冲 | L4–6 | pin、dirty、latch 各保护什么？行存和列存怎样影响读写？ | HW2、Project 1 |
| 访问路径 | L7–10 | 点查、范围查询、过滤误报与并发修改有什么取舍？ | HW3、Project 2 的索引基础 |
| 执行与优化 | L11–16 | 内存不足时怎么排序、连接？结果相同的计划为什么代价不同？ | Project 2、HW4、Project 3 |
| 事务 | L17–20 | 隔离级别与可串行化怎样区分？如何判断版本可见、冲突和回滚？ | HW5、Project 4 |
| 恢复与分布式 | L21–25 | COMMIT 后哪些东西已持久化？复制、分片与分布式提交有何区别？ | HW6、综合推演 |

正常节奏可按每周两讲；项目周减少新课。若每周投入约 8–12 小时，可先按 4–6 个月安排，再按 C++ 基础调整。这是编者建议，不是学完或通过项目的保证。

- **课程笔记**：按问题提炼机制、推导、反例与自测。默认从这里开始。
- **中文译稿**：按真实视频时间顺序整理课堂讲解、演示与问答；课堂截图只放这里。时间索引是返回原片定位的依据，不代表逐帧核验。
- **课程资料**：只承载独立课外阅读，不再把课堂逐项讲过的 slides/notes 翻译一遍。无独立内容时不创建占位文件。
- **公共资料**：共用教材、版本、工具链和学习方法集中在本页；实验说明与指导提供无答案的要求导读，学习者实现留在独立私有仓库。

网站“材料已就绪”不等于学习者完成实验。**制作批次 P0–P11 与官方 Project 0–4 是两套编号**；HW1–6 是另一组作业，导航中的 HW1、HW2、HW3 不是新增的官方 Project。

L2–3 的动手入口：[HW1 SQL 要求导读](#/c/cmu-15-445-2025/lab/hw01?v=zh)与[无答案指导](#/c/cmu-15-445-2025/lab/hw01?v=guide)；[Project 0 要求导读](#/c/cmu-15-445-2025/lab/project0?v=zh)与[哈希、概率及实现指导](#/c/cmu-15-445-2025/lab/project0?v=guide)。题面网页的全文翻译发布许可未确认，这些页面是编者原创导读，不冒充授权全文译文。

L4–6 的动手入口：[HW2 Storage 要求导读](#/c/cmu-15-445-2025/lab/hw02?v=zh)与[无答案指导](#/c/cmu-15-445-2025/lab/hw02?v=guide)；[Project 1 要求导读](#/c/cmu-15-445-2025/lab/project1?v=zh)与[ARC、异步 I/O、页守卫指导](#/c/cmu-15-445-2025/lab/project1?v=guide)。先用纸面状态表区分页面身份、内存槽位、使用权与读写互斥，再写并发代码；实验环境与 C++ 先修仍复用本页和 Project 0。

L7–9 的动手入口：[HW3 Indexes & Filters 要求导读](#/c/cmu-15-445-2025/lab/hw03?v=zh)与[无答案指导](#/c/cmu-15-445-2025/lab/hw03?v=guide)。先比较哈希点查、有序索引范围扫描和过滤器排除不可能命中的语义，再手推维护操作。概率先修复用 Project 0，页身份与守卫复用 Project 1；课堂普通 B+Tree 不等于 Project 2 的 tombstone 变体。

L10–12 的动手入口：[Project 2 要求导读](#/c/cmu-15-445-2025/lab/project2?v=zh)与[tombstone B+Tree 无答案指导](#/c/cmu-15-445-2025/lab/project2?v=guide)。先解释并发修改为何仍能保持树的物理结构，再计算外部排序和连接的页 I/O；不把这些纸面练习当成已经运行 BusTub。

L13–14 可连续练习：先读[查询执行（一）](#/c/cmu-15-445-2025/lec/lec13?v=notes)，跟踪算子如何交接一批记录；再读[查询执行（二）](#/c/cmu-15-445-2025/lec/lec14?v=notes)，判断把同一批工作分给多个 worker 后谁最后交卷。下文「订单查询推演」给出同一条查询的两种执行安排。

## C++ 先修：先把资源归属说清楚

开始写 BusTub 前，至少能独立完成下面四类小练习，并解释失败时破坏了什么条件：

1. **值、引用与生命周期**：返回局部变量引用为什么悬空？容器扩容以后保存的指针何时失效？
2. **RAII 与移动语义**：用构造/析构管理一项资源；区分复制资源、转移所有权与借用对象；理解 `unique_ptr`、`shared_ptr` 的使用边界。
3. **容器、模板与复杂度**：能读懂 `vector`、哈希表、模板类和迭代器；不把“平均常数时间”当作没有内存或同步成本。
4. **并发与错误定位**：理解互斥锁、条件变量、原子操作和数据竞争的区别；能读编译错误、栈回溯与 sanitizer 报告。原子计数并不自动保护多字段不变量。

这些是编者先修检查，不是官方项目答案。Count–Min Sketch 所需的哈希碰撞、概率界与近似计数集中在 [Project 0 指导](#/c/cmu-15-445-2025/lab/project0?v=guide)，不必等到 L7 才开始。

## 教材定位与分讲阅读

指定教材是 Silberschatz、Korth、Sudarshan 的 **Database System Concepts，第七版（2019）**。第六版或其他数据库教材可以辅助理解，但页码和章节编号不能混用。

第一讲指定阅读 Chapter 1–2。按第七版官方目录，可这样带着问题阅读：

| 定位 | 编者阅读问题 | 与 L1 的连接 |
|---|---|---|
| §1.2 Purpose of Database Systems；§1.3 View of Data | 如果应用各自解析文件，约束、并发和恢复分别由谁维护？ | 文件方案的代价；抽象层次 |
| §1.6 Database Engine；§1.7 Database and Application Architecture | 查询的含义和执行它的部件应怎样分开？ | 后续存储、执行、事务的路线图 |
| §2.1 Structure of Relational Databases；§2.2 Database Schema | 一张表的结构与某一时刻的数据有什么区别？ | 关系、元组、属性、schema |
| §2.3 Keys | 什么使一行可被唯一识别？应用中的名字为什么未必适合作键？ | 主键与关联的约束 |
| §2.6 The Relational Algebra | 一个操作的输入和输出是什么？怎样组合操作而不指定存储布局？ | 选择、投影、集合操作、连接 |

本页只依据官网与目录定位章节，**不是教材全文翻译，也不表示已通读教材正文**。阅读时先自己写出一个三行小表，再计算表达式结果；用反例区分关系代数的集合语义与后续 SQL 的多重集语义。L1 的技术提炼见[关系模型与关系代数笔记](#/c/cmu-15-445-2025/lec/lec01?v=notes)。

L2 指定 **Chapters 3–5**，L3 指定 **§12.1–12.4、§13.2–13.3**。按各讲笔记中的问题读自己的教材；该书全文翻译发布授权仍未确认。独立章节阅读导引若有制作，放在对应讲次的课程资料；它与课堂译稿分开，也不表示通读了教材正文。

L4 指定 **§13.2–13.5**，L5 指定 **§14.8.1、24.2**，L6 指定 **§11.2、13.6**。这些章节分别连接缓冲管理、日志结构/写优化及列式存储；课表指定章节与实际取得正文是两件事。带着各讲笔记中的问题阅读自己的合法教材，不把目录定位当作全文精读。L4、L5没有独立资料页；L6的[Parquet导读](#/c/cmu-15-445-2025/lec/lec06?v=materials)是另行读过的当前官方文档，不代替指定教材，也不倒填成2025课堂。

L7 指定 **§14.5、24.5（Hash Indices）**，L8 指定 **§14.1–14.4（基础概念、有序索引、B+Tree 及扩展）**，L9 另含 **§24.1（Bloom Filter）**。这里只核对第七版目录定位，未取得或通读这些教材正文。读自己的教材时分别记录“查找键是什么、索引项指向什么、更新会破坏哪条不变量”；不要把过滤器的可能命中当成已经找到记录。

L10 指定 **§18.10.2**，L11 指定 **§15.4–15.5**，L12 指定 **§15.4–15.6**。这些是官方课表的阅读定位，不代表已取得教材正文；用合法教材补读并发索引与查询处理。下列阶段自测限定 L1–11；L12 的连接算法自测留在[该讲笔记](#/c/cmu-15-445-2025/lec/lec12?v=notes)，不擅自扩大官方期中范围。

## 版本冻结与实验工作区

课程、视频与项目均以 **Fall 2025** 为主线，不把 2026 的编号、视频或当前 `master` 接口混入。BusTub 固定为：

```text
标签：v20251119-2025fall
提交：d49b823f829a4bf311a2c80b239ab5a9864c9c41
```

源码必须放在课程站之外的私有学习目录。每个官方项目完成后保存独立 checkpoint；后续项目的改动不能抹掉早先阶段可复现的实现与测试条件。获取骨架、读完指导、编译成功、公开测试通过与学习者真正完成项目是不同状态；公开测试也不代表隐藏评分满分。

## 五个官方项目：任务与先修地图

下表只建立准备路线，不代替后续实验说明与指导。导航中的星级是编者对相对难度的建议，工时未作实测估计；讲次先修映射也是学习建议，不是 CMU 的注册条件。

| 项目 | 完整任务边界 | 建议先读 |
|---|---|---|
| Project 0 · C++ Primer | Count–Min Sketch 的构造、移动语义、并发 Insert、Count、Clear、Merge、给定候选集合的 TopK | C++、哈希与基础概率；不必等到听完 L7 才开始 |
| Project 1 · Buffer Pool Manager | ARC 变体、Disk Scheduler、Buffer Pool Manager 与 Read/Write Page Guards | L3–5；RAII、move、线程与 promise/future |
| Project 2 · Database Index | B+Tree 页、插入/删除/点查、跳过 tombstone 的迭代器、optimistic latch crabbing | L8–10；复用 Project 1 的页访问能力 |
| Project 3 · Query Execution | 访问方法执行器；聚合与 Nested Loop / Index Join；Grace Hash Join 与优化规则；外部归并排序、Limit、窗口函数 | L2、L11–16；复用缓冲池与索引 |
| Project 4 · Concurrency Control | 时间戳与 watermark；重建 tuple / 选择 undo 历史；Insert、Commit、生成 undo、Update/Delete、stop-the-world GC、**Abort**；主键插入、扫描/删除/更新、**主键变更与 Serializable 验证** | L17–20；需访问执行器及 SeqScan→IndexScan 规则，不要求先完成 P3 全部算子 |

### 不可混用的接口与版本

- **语言标准**：FAQ 和 L1 口头介绍写 C++20；固定 `CMakeLists.txt` 使用 **C++17**，推荐 **Clang 15**。构建设置以固定提交为准，不为追随 FAQ 改成 C++20。
- **Project 0 Merge**：网页描述像是创建新 sketch；固定接口为 `Merge(const CountMinSketch &) -> void`，**原地更新接收者**，输入 sketch 保持不变。网页措辞不能覆盖接口与公开测试。
- **Project 1**：是 ARC 变体，不是往年的 LRU-K；`DiskScheduler::Schedule` 接收一组请求，Page Guards 是 move-only 的资源管理对象。
- **Project 2**：叶页保存 tombstone 缓冲，迭代时要区分物理槽位和逻辑上仍存在的键；不能直接照搬不带删除缓冲的旧 B+Tree 指导。
- **Project 3**：执行器实际采用 `Next(vector<Tuple> *, vector<RID> *, size_t batch_size)`，不是旧注释所说的逐 tuple 返回。Grace Hash Join 与外部排序不能退化为把全部输入装进内存；窗口函数是正式任务。
- **Project 4**：MVOCC 改写访问方法，Task 3 起针对固定长度 schema，不能期待包括 VARCHAR 在内的全部 P3 场景继续兼容。保留 **P3 checkpoint → P4 分支**。Abort 是实际回滚，不只是标记 TAINTED；可串行化验证不是排行榜附加题。
- Project 4 网页最后更新于 2025-12-07，晚于所固定 tag；网页获取日和代码 SHA 分别登记。后续若遇到新差异，应先定位证据，不静默更新到 `master`。

### 公开测试能证明什么

| 项目 | 官方公开范围 | 不应作出的推断 |
|---|---|---|
| Project 0 | `test/primer/count_min_sketch_test.cpp`；网页明确无隐藏测试 | 机器上的并发性能未运行，不能承诺速度阈值或评分 |
| Project 1 | ARC、磁盘调度、页守卫、缓冲池测试；评分另有更复杂测试 | 几个样例通过不等于并发与生命周期全部正确 |
| Project 2 | 插入、删除、规模、并发测试；固定代码另有 tombstone 测试 | 不能漏掉 tombstone 或只验单线程点查 |
| Project 3 | `test/sql/` 的 SQLLogicTest；网页明确测试公开，排行榜数据会随机化 | `test-p3` 并非只运行当前已实现算子的最小集合；本地输出不保证评分结果 |
| Project 4 | 时间戳、扫描、执行器、索引、并发、Abort/Serializable；并发测试公开，隐藏测试为单线程 | “并发测试公开”不等于“全部测试公开” |

固定骨架的一些测试仍带禁用标记；后续按项目阶段启用并执行相应测试。这里仅做静态接口与目录核对，**未编译 BusTub、未运行任何学生项目评分测试或 benchmark**。

## Apple Silicon：保守的环境准备路线

本机观察为 arm64、Apple Clang 17，命令行工具与 Homebrew 可见；`cmake`、`ninja`、`clang-15`、`clang-format`、`clang-tidy` 未在当前 PATH 中找到。Docker CLI 可见，但 daemon、镜像、架构和容器运行能力没有核实。此清单不表示全机其他位置不存在这些工具。

1. **先固定代码，再选择环境。** 在课程站之外执行下面的准备命令，核对打印的完整 SHA；这是给学习者的命令，本批没有执行 clone 或创建学生仓库。

   ```bash
   git clone --branch v20251119-2025fall --single-branch \
     https://github.com/cmu-db/bustub.git bustub-2025-study
   cd bustub-2025-study
   git rev-parse HEAD
   git switch -c study-2025
   ```

2. **先看安装脚本，不盲跑。** 固定 `build_support/packages.sh` 会安装软件并可能执行 `brew update`。本批没有安装依赖；也不把“工具在 PATH”当作“构建可用”。
3. **本机可作编辑与调试环境。** 若采用原生 arm64 路线，准备 CMake、LLVM/Clang 15 及相同主版本的格式化和静态检查工具，通过独立构建目录与显式编译器路径选择它们。历史 `llvm@15` 是否仍可直接安装，需要届时实际确认；当前 Apple Clang 17 不冒充 Clang 15。
4. **以 Linux 作为兼容性基准。** 固定 README 推荐 Ubuntu 24.04，评分环境也为 Ubuntu 24.04；macOS 仅作开发用途。脚本明确的 Linux 支持路线为 x86-64。Apple Silicon 如需对齐，可使用独立 x86-64 Ubuntu 24.04 VM/仿真或远程机器；原生 arm64 Linux 另作探索，不宣称与评分一致。
5. **不改学生代码迁就平台。** 若当前 macOS/SDK 与历史工具链不兼容，换隔离环境，而不是关闭警告、删测试或改项目 CMake。macOS 缺少 LeakSanitizer，锁的行为也可能不同；本机结果不能替代 Linux 上的检查。
6. **实现一个阶段，再验证该阶段。** 工具准备好后，按对应项目指导配置 Debug、编译相应目标并运行已实现路径的测试。可用 `cmake --build <build-dir> --parallel`，不要在 macOS 上照抄依赖 `nproc` 的命令。每个项目与每次性能优化前都留可恢复 checkpoint。

这是一条静态核对后的准备路线，**不是已经成功配置或编译的环境**。没有为了本批样章运行未实现的项目，也没有把下载源码当作完成实验。

## 校外跟课与时间安排

FAQ 提供校外 Gradescope 入口，但本批**未登录核实当前能否加入、查看作业或获得评分**。不承诺隐藏评分可用、满分或正式课程资格。实现应保存在私有仓库，不能公开完整项目答案；理解每一段实现仍是学习者的责任。

HW1 对应 SQL，HW2–6 分别衔接存储、索引、执行、事务、恢复与分布式阶段；官方题面和历史日期见页底作业索引。旧学期截止日期不是当前自学期限。L3 官方标注 **No In-Class Lecture**，仍有课表指定录像；L25 没有官方 Notes 链接，不补造文件。

## 期中阶段自测：把 L1–11 串成一条访问路径

先独立作答，再展开核对。以下十二题是编者自拟，不是 CMU 原卷、官方模拟卷或评分答案；可以回看笔记，不必计时。每题至少写清**语义、前提、状态变化**中的两项，而非只报结论。

### 1. 相同的输出列，是否就是相同的关系？

`Orders(id, sku, qty)` 中有三行 `(1,A,2)`、`(2,A,3)`、`(3,B,NULL)`。SQL 的 `SELECT sku FROM Orders` 与经典关系代数投影有什么差别？SQL 若没有 `ORDER BY`，能否依赖结果顺序？

<details><summary>展开核对：多重集与集合</summary>

SQL 默认保留重复项，得到两个 A 和一个 B；经典集合关系代数的投影会去重，只保留 A、B。SQL 用 `DISTINCT` 才明确要求去重。两者都不能凭这张小表的书写顺序推断 SQL 输出顺序；只有恰当的 `ORDER BY` 才给出相应排序保证。

</details>

### 2. NULL 会在哪一步改变聚合？

仍用上题三行。比较 `COUNT(*)`、`COUNT(qty)`、`SUM(qty)`、`AVG(qty)`；再问 `WHERE qty <> 2` 保留哪一行。不能把 NULL 偷换成零。

<details><summary>展开核对：行数、非空数与三值逻辑</summary>

结果分别为 3、2、5、2.5。AVG 的分母是参与计算的非空值数量。`qty <> 2` 对 NULL 得到 UNKNOWN，WHERE 只保留 TRUE，因此只剩 id=2。若业务要求保留未知数量，必须明确写出这项语义，而不是依赖“不等于”。

</details>

### 3. 记录移动后，哪个身份应当不变？

假设 RID 由 page id 与 slot id 组成。页内压缩把记录的字节从偏移 300 搬到 120，槽位编号保持不变。外部索引要不要跟着修改？如果记录搬到另一页，又缺少转发机制呢？

<details><summary>展开核对：业务键、RID、页与 frame</summary>

页内移动只需更新槽目录里的字节偏移，原 RID 仍能定位记录；索引不应把字节偏移当稳定 RID。跨页移动则改变 page id，若没有稳定间接层或转发机制，引用必须维护。业务键是查询/约束意义上的身份；page id 是存储页身份；frame id 是当前缓存槽位，页面重新载入后可以换 frame，不能写入持久索引代替 RID。

</details>

### 4. pin 了页面，为什么仍可能读到中间状态？

线程 A 持有页的 pin，线程 B 同时修改其槽目录和 tuple 区。A 是否已经安全？再区分“释放读写互斥”“允许淘汰”“需要写回”三个状态。

<details><summary>展开核对：三个互不替代的条件</summary>

pin 只防止页面在使用期间被淘汰或复用，不让多字段读写自动原子化；仍需正确的 latch 协议。释放 latch 表示不再占用读写互斥，pin 降为零才可能成为可淘汰候选，dirty 表示内存页与持久副本不同。dirty 页也可以在安全写回后被淘汰；pin 数为零并不等于已经写回。guard 的生命周期要同时考虑这些资源，但不能把三者合并成一个布尔值。

</details>

### 5. 只求一列之和，为什么行存可能读得更多？

给定 10 万行、每行十个等宽 8 字节属性；每页可用负载 4000 字节，忽略元数据、压缩与缓存。列各自紧密存放。全表求一个属性之和时，行存与列存分别至少读取多少数据页？若改成按主键查一整行呢？

<details><summary>展开核对：布局收益取决于访问形状</summary>

行存每页 50 行，共 2000 页；目标列共 800000 字节，占 200 页。该简化模型下列存少读十倍数据，不能泛化成所有查询都快十倍。整行点查还涉及索引访问、十列位置与缓存局部性；列存可能要访问多处。这里没有计算页头、对齐、解码与输出成本。

</details>

### 6. 字典编码能否直接用编号比较大小？

编码表为 `A→7, B→2, C→5`。按字符串排序的谓词 `sku < 'B'` 能否改为 `code < 2`？什么时候才可能直接用编码做范围比较？

<details><summary>展开核对：相等保持不等于顺序保持</summary>

不能。A 的编码是 7，却满足字符串谓词。普通唯一字典编码可保持相等关系，未必保持字典序；只有编码顺序与所用字符串排序规则一致，且相关值使用兼容字典时，才可直接比较编号。压缩节省 I/O 与是否能够在压缩域执行谓词是两个问题。

</details>

### 7. 目录翻倍是不是每次桶分裂都要做？

可扩展哈希的 global depth 为 3，某满桶 local depth 为 2。插入触发分裂时，是否必然把整个目录翻倍？如果该桶 local depth 已是 3 呢？

<details><summary>展开核对：区分目录位数与桶的区分位数</summary>

第一种情况可把桶深度增加到 3，重新分配该桶记录并更新原有目录别名，无须目录翻倍。第二种情况需要更多目录位来区分两个新桶，通常先把 global depth 增至 4。分裂仍只重分配目标桶的条目，不是重哈希整张表；连续共享前缀还可能导致进一步分裂。

</details>

### 8. Bloom 的“可能存在”能否跳过回表？

只插入未删除的标准 Bloom filter 对某业务键返回阳性。能否直接返回订单记录？若为了删除一个键而清除其所有对应位，会破坏什么？

<details><summary>展开核对：过滤与精确定位</summary>

阳性只说明不能排除，仍要精确索引/存储层核实；filter 不携带完整记录或 RID。其他键可能共享这些位，直接清零会产生假阴性。标准“无假阴性”结论依赖正确插入、维护及可见性前提；可删除的变体需要额外计数或其他协议，不能给标准位图强加删除。

</details>

### 9. 分隔键与实际索引项有什么区别？

根分隔键为 50，左叶含 10、20、40，右叶含 50、60。范围 `[20,60)` 怎样遍历？如果叶页中的 50 被 tombstone 标记，能否因此立即删掉父分隔键 50？

<details><summary>展开核对：路由边界与逻辑记录</summary>

先从根定位 20 所在叶，取 20、40，再沿叶链继续取小于 60 的有效项。父分隔键表达子树的路由范围，不是另一条业务记录；叶项逻辑删除并不单独证明孩子指针或分隔键应被移除。带 tombstone 的实现还要区分物理槽与逻辑可见项，具体重平衡和边界维护按 Project 2 固定规则，不能套用“删除一次就立刻合并”。

</details>

### 10. optimistic crabbing 为什么不能直接升级？

更新沿读 latch 路径到达叶页后发现可能分裂。线程如果一边保留自己持有的读 latch，一边等待改成写 latch，可能出现什么问题？安全快路径究竟要证明什么？

<details><summary>展开核对：重新开始不是失败兜底</summary>

若两个更新线程都持有同一读 latch 并等待独占升级，各自都挡住对方。协议通常释放乐观路径资源后，从根按正确写 latch 顺序重新取得所需保护；重新读取时树可能已变，不能继续使用旧裸指针。安全快路径要证明当前操作不会向未受保护祖先传播结构修改。判断依赖操作种类、容量、根状态和 tombstone 规则，不是泛泛一句“叶子还有空位”。latch 保证的是物理结构访问安全，不是完整事务隔离。

</details>

### 11. 排序的“第几趟”有没有算输出？

有 N=1000 页输入、B=11 个缓冲页。生成初始 run 时每批最多排序 B 页；归并时用一页输出，其余每路各用一页。假设各趟页数仍为 N，所有 run 都写入磁盘。不使用 replacement selection。求初始 run 数、归并趟数、总页 I/O；若最终输出直接流入下游呢？

<details><summary>展开核对：先写 run 递推，再算 I/O</summary>

初始 91 个 run，每次最多十路归并，run 数依次为 91→10→1。因此有一次生成趟与两次归并趟，不能把两次归并误称为总共两趟。

$$
R_0=\lceil1000/11\rceil=91
$$

全部物化时，每趟读取并写出 1000 页，共 6000 次页 I/O。最后一趟直接交给下游，可省最终 1000 页写出，排序自身共 5000 次；并未省掉读中间 run，也未计下游额外 I/O。内存里的归并比较、页预取和运行时间不在这个模型中。

</details>

### 12. 分区聚合能不能平均各分区的 AVG？

同一 sku 的非空 qty 在一个分区是 `[2,4]`，另一个分区是 `[100]`。两个局部平均为 3 和 100。总平均是不是 51.5？当 GROUP BY 状态超过预算时，仅换成哈希表就能避免落盘吗？

<details><summary>展开核对：聚合状态必须能够正确合并</summary>

总平均是 106/3，约 35.333；局部平均的平均丢失了每组数量。AVG 可保存并合并 `(sum,count)`，最后除法；NULL 仍遵守 SQL 聚合语义。哈希表并不消除内存上限，组数/状态过多时需分区溢写或采用排序等方法；极端倾斜也不能仅靠“再换一个哈希函数”保证解决。以上是自拟数据与推导，不是 Project 3 的实现答案。

</details>

若第 3–4 题解释不清，回到 Project 1 页面生命周期；若第 9–10 题解释不清，先看 L8/L10 再做 Project 2；若第 11–12 题只会套公式，回到 L11 重写内存与输出成本假设。答对这些题不等于完成任何官方实验。

## 订单查询推演：第一行何时能返回？

仓库只想知道每种缺货商品还欠多少件。`Orders` 中每行是一条未发货订单行，`Stock` 中 `sku` 唯一；本题所有值非 NULL。用同一条查询追踪单机流水线与并行分区。数据和代价均为纸面设定，不是 BusTub 实测或官方项目题。

```sql
SELECT o.sku, SUM(o.qty) AS missing_qty
FROM Orders AS o JOIN Stock AS s ON s.sku = o.sku
WHERE s.on_hand = 0
GROUP BY o.sku;
```

`Stock` 是 `(A,0), (B,4), (C,0)`；`Orders` 按扫描顺序分两批到达：`[(A,2),(B,1)]`、`[(C,3),(A,5)]`。

### 先手推：一次调用返回的不是最终答案

采用如下物理计划：先过滤并在 Stock 上建立哈希表，再扫描 Orders 探测，最后做普通的无序哈希聚合。写出每批后的连接输出和累计状态。第一批结束时，哪些算子已有输出？客户端能收到 `A` 的最终总数吗？

<details><summary>核对状态、阻塞点和结束条件</summary>

| 时刻 | 算子交给下游的记录 | 聚合表 |
|---|---|---|
| 建表完成 | 探测侧现在可以查 `{A,C}`，还没有连接结果 | 空 |
| 第一批结束 | `(A,2)`；`B` 没有匹配 | `A:2` |
| 第二批结束 | `(C,3), (A,5)` | `A:7, C:3` |
| 探测侧报告结束 | 不再有可能改变任一分组的记录 | 可输出 `(A,7), (C,3)`，不保证顺序 |

连接的**建表阶段**是屏障；之后探测和聚合更新可以流水工作。聚合可以提早消费，但在这份无序计划里不能提早交付最终分组。若第一批恰好全部未命中，一个空的中间批也不证明上游耗尽：结束要由实际的执行器协议报告。

</details>

### 再手推：工作均分了吗？

放大同一查询。假设同一阶段有 1000 条**已经过连接**的记录，按 `sku` 重分区给四个 worker，每个 worker 每毫秒处理 1 条。测量从分区交付完毕、四者同时开工起算；末端另有不可重叠的固定 20 ms 收尾。本题忽略 I/O、网络和同步。分别计算分区大小为 `[250,250,250,250]` 和 `[700,100,100,100]` 的用时。若 700 条全是同一个键，增加分区数能保证消除长尾吗？

<details><summary>核对关键路径，并找出可以搬动的工作</summary>

收尾必须等待最慢分区；总时间分别为 `max(250,250,250,250)+20 = 270 ms` 和 `700+20 = 720 ms`。两种安排的分区处理总工作量都是 1000 worker·ms；变的是完成时间，不是记录数。单 worker 同模型需 1020 ms，不应把四个 worker 直接记为四倍提速。

同一键的记录仍由同一分区接收。对本题的 `SUM`，可以在重分区**之前**按输入切片各算局部和，再让键的最终所有者合并各局部和；重复出现的 `A` 不必逐条经过交换。这个改写要求局部状态可合并，且足以恢复原查询的结果。它既没有消除扫描，也不保证总是更快：若几乎每行一个键，局部聚合可能只增加状态和工作。

</details>

## 引用与来源

- CMU Database Group / Andy Pavlo：[Fall 2025 官方课表](https://15445.courses.cs.cmu.edu/fall2025/schedule.html)、[课程大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html)、[FAQ](https://15445.courses.cs.cmu.edu/fall2025/faq.html)、[官方视频列表](https://www.youtube.com/playlist?list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5)。逐讲视频入口显示在各讲页头。
- Abraham Silberschatz、Henry F. Korth、S. Sudarshan：[*Database System Concepts*, 7th edition](https://www.db-book.com/)，McGraw-Hill，2019，ISBN 9780078022159；[官方目录](https://www.db-book.com/toc-dir/toc.pdf)。本批核对首页与章节目录，不取得教材全文翻译发布授权。
- CMU Database Group：[BusTub 固定源码](https://github.com/cmu-db/bustub/tree/v20251119-2025fall)、[固定提交](https://github.com/cmu-db/bustub/commit/d49b823f829a4bf311a2c80b239ab5a9864c9c41)。代码许可与课程网页、视频、第三方依赖许可分别适用。
- 官方 [作业与项目索引](https://15445.courses.cs.cmu.edu/fall2025/assignments.html)：[Project 0](https://15445.courses.cs.cmu.edu/fall2025/project0/)、[Project 1](https://15445.courses.cs.cmu.edu/fall2025/project1/)、[Project 2](https://15445.courses.cs.cmu.edu/fall2025/project2/)、[Project 3](https://15445.courses.cs.cmu.edu/fall2025/project3/)、[Project 4](https://15445.courses.cs.cmu.edu/fall2025/project4/)。任务与测试范围经网页和固定源码静态核对；不是已运行的验证结果。
- 工具链依据：固定提交的 [README](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/README.md)、[CMakeLists.txt](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/CMakeLists.txt)、[packages.sh](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/build_support/packages.sh)。原生开发与 Linux 验证路线为编者建议，未实际配置或运行。
- 六份作业：[HW1 SQL](https://15445.courses.cs.cmu.edu/fall2025/homework1/)、[HW2 Storage](https://15445.courses.cs.cmu.edu/fall2025/files/hw2-clean.pdf)、[HW3 Indexes & Filters](https://15445.courses.cs.cmu.edu/fall2025/files/hw3-clean.pdf)、[HW4 Execution & Planning](https://15445.courses.cs.cmu.edu/fall2025/files/hw4-clean.pdf)、[HW5 Transactions](https://15445.courses.cs.cmu.edu/fall2025/files/hw5-clean.pdf)、[HW6 Recovery / Distributed](https://15445.courses.cs.cmu.edu/fall2025/files/hw6-clean.pdf)。HW1–3 已阅读全文并制作原创要求导读；HW3 全部五大题及图形条件已读，不提供选项答案。HW4–6 仅登记、获取并核对元数据。HW3 索引截止日为 2025-10-05，PDF 却印“Sunday October 3rd”；HW5 索引为 11-23，PDF 为 11-16。保留冲突，不猜测延期原因。
- 期中范围依据：L8 课堂通知 **01:31–01:48** 明确为 Lecture 1–11 inclusive，见[L8 中文译稿 00:00–01:54](#/c/cmu-15-445-2025/lec/lec08?v=draft)。本页自测为原创，未取用官方考卷或解答；L12 虽同属制作 P4，未据此纳入官方期中考纲。
- 全课逐来源版本、访问与阅读范围见仓库 `content/cmu-15-445-2025/source-manifest.json`；制作与恢复状态见同目录 `status.json`。原始字幕、媒体与网页快照只保存在本地忽略的 `sources/`，不随站点发布。
