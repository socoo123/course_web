---
source: CMU 15-445/645 Fall 2025 Homework 1 官方网页全文、schema 图、大纲；DuckDB 1.3 文档
version: Fall 2025 Lahman 作业；题面 CLI 示例 DuckDB v1.3.2
license: 未发现作业网页完整翻译发布授权；本页是原创要求导读，不是授权全文翻译；不转载数据集或完整 SQL 答案
status: 六题与可达 schema、提交规则已覆盖；数据未下载、SQL 未执行、Gradescope 未验证；学习者完成 not_attempted
---

# HW1：用 SQL 表达精确的问题

HW1 是 **Homework #1 — SQL**，固定导航 ID 为 `hw01`，不是第六个官方 Project。它与[现代 SQL 讲次](#/c/cmu-15-445-2025/lec/lec02?v=notes)配套；C++ 项目另见 [Project 0](#/c/cmu-15-445-2025/lab/project0?v=zh)。

导航：[无答案指导](#/c/cmu-15-445-2025/lab/hw01?v=guide) · [公共资料](#/c/cmu-15-445-2025)。

目标不是记住棒球统计答案，而是从自然语言中确定结果的粒度、连接键、聚合对象、存在性条件、排序和修改语义。本文完整登记六题的可达要求，不提供可提交 SQL；官方 Q1 虽有示范答案，这里也只指回原页。

## 1. 版本、工具与学习状态

| 项目 | 官方历史要求／本轮事实 |
|---|---|
| 课程 | Andy Pavlo，CMU 15-445/645 Fall 2025；个人独立作业 |
| 发布／截止 | 2025-08-27／2025-09-07 23:59；历史截止，不是本站安排 |
| 内容 | 6 题，总分 100；每题**只允许一条 SQL statement** |
| 数据 | 课程裁剪的 Lahman 数据库 `lahman-cmudb2025.db.gz`，不是随意下载的其他年份 Lahman |
| 引擎 | DuckDB CLI；题面演示 `v1.3.2 (Ossivalis) 0b83e5d2f6` |
| 本轮范围 | 已读官方题面、全部 11 表描述及 schema 图；没有获取／打开数据文件、安装 DuckDB、运行答案或登录 Gradescope |
| 学习者状态 | **not_attempted**；文档就绪不能算作业完成 |

题面中还残留一句 “You can start with using SQLite”，但下载文件、CLI、文件后缀及高级语法指导均围绕 DuckDB。不要把这句当成 SQLite 与该 `.db` 文件直接兼容的承诺；按 DuckDB 版本学习，并记录自己实际使用的版本。

安装入口如今会跳转新版本文档；截至 2026-11-15，本轮访问的 `stable` SQL 文档亦跳到 2.0。本站为语义核对另读 **1.3** 的 SQL 文档，不以当前最新版反推 2025 行为。1.3 安装目录候选返回 404，因此没有声称复现过旧版安装；从官方发布渠道取得目标版本后再验证。

## 2. 数据准备与只读起步

官方数据入口：[lahman-cmudb2025.db.gz](https://15445.courses.cs.cmu.edu/fall2025/files/lahman-cmudb2025.db.gz)。题面要求压缩文件的 MD5 为：

```text
a4fb302c11f80030f26bb6bb59d68cac
```

题面给出的解包方式是 `tar zxf lahman-cmudb2025.db.gz`，解压后数据库约 **40 MB**。不要仅凭 `.gz` 后缀改成另一种文件格式处理方式；先核对下载文件和归档内容，再按官方说明解包。MD5 在这里用于发现文件下载不一致，不是对互联网下载的安全认证。本轮没有实际下载或计算此文件哈希，上述值来自题面。

在独立练习目录中保存原始数据库的一份干净副本，特别是 Q6 会修改表。CLI 入口为：

```bash
duckdb lahman-cmudb2025.db
```

随后用 `.tables` 查看表名，用 `DESCRIBE 表名;` 核对字段、可空性和键。官方基本核对点：应有 **11 张表**，`appearances` 应有 **115355 行**。这些是学习者将来可核对的期望，不是本站实测结果。

如果数据无法取得，不换数据集“做出类似题目”后标为完成。恢复条件是取得官方同名归档、核对指定 MD5、成功在目标引擎打开，并重新核对表结构与行数；当前六题题文本身与 schema 均已可达，无缺题阻塞。

## 3. 11 张表：先认粒度，再选连接键

下面是按用途重组的 schema 索引，不是完整 SQL DDL。字段和类型依据网页 `DESCRIBE` 输出；“关系”是用于理解连接的语义关系，**不表示数据库一定声明并强制所有外键**。已同时看过官方 schema 图；字段／键存在冲突时优先核对实际数据库，不能只凭图中箭头推断约束。

类型简记：`S=SMALLINT`、`I=INTEGER`、`V=VARCHAR`。PK 是题面输出标出的复合／单列主键；`非空`另外列出非主键的 NOT NULL 字段；其余非主键字段允许 NULL。

| 表 | 字段与类型 | 键／非空与粒度 |
|---|---|---|
| `appearances` | `yearID:S, teamID:V, lgID:V, playerID:V, G_all:S, G_batting:S, HR:S` | PK `(yearID, teamID, playerID)`；一名球员在某年某队的一条出场统计，不是一次挥棒／一场比赛 |
| `awardsplayers` | `playerID:V, awardID:V, yearID:S, lgID:V` | 四列共同为 PK；球员在某年某联盟获得某奖 |
| `awardsmanagers` | `playerID:V, awardID:V, yearID:S, lgID:V` | 四列共同为 PK；经理的获奖记录 |
| `collegeplaying` | `playerID:V, schoolID:V, yearID:S` | 题面未声明 PK；`playerID` 非空；球员、学校、年份的关联可能产生多行 |
| `schools` | `schoolID:V, name_full:V, city:V, state:V, country:V` | PK `schoolID`；学校位置用于 PA 筛选 |
| `people` | 见下表 | PK `playerID`；姓名不是身份键 |
| `halloffame` | `playerID:V, yearid:S, inducted:V` | 三列共同为 PK；出现一条名人堂记录不等于已入选 |
| `managers` | `playerID:V, yearID:S, teamID:V, lgID:V, inseason:S` | PK `(yearID, teamID, inseason)`；`playerID` 可空；同队同年可有不同任期经理 |
| `teams` | `yearID:S, lgID:V, teamID:V, franchID:V, divID:V, teamRank:S, name:V, attendance:I` | PK `(yearID, lgID, teamID)`；队伍的年度记录，不是每队永远只有一行 |
| `leagues` | `lgID:V, league:V, active:V` | PK `lgID`；`league, active` 非空 |
| `divisions` | `divID:V, lgID:V, division:V, active:V` | PK `(divID, lgID)`；`division, active` 非空 |

`people` 的全部字段分组如下：

| 分组 | 字段与约束 |
|---|---|
| 标识 | `ID INTEGER NOT NULL`，`playerID VARCHAR PRIMARY KEY`；不要把 ID 与 playerID 混用 |
| 出生日期 | `birthYear, birthMonth, birthDay`：均为可空 INTEGER |
| 出生地点 | `birthCountry, birthState, birthCity`：均为可空 VARCHAR |
| 去世日期 | `deathYear, deathMonth, deathDay`：均为可空 INTEGER |
| 去世地点 | `deathCountry, deathState, deathCity`：均为可空 VARCHAR |
| 姓名 | `nameFirst, nameLast, nameGiven`：均为可空 VARCHAR |

### 关系阅读路径

- 球员身份：统计／获奖／大学／名人堂记录的 `playerID` 对应 `people.playerID`；不要用显示姓名连接。
- 学校资格：`collegeplaying.schoolID → schools.schoolID`；资格是“曾在符合条件的学校打球”，不意味着每条学校经历都要乘进统计行。
- 球队年度：按年份、队标识与适当联盟条件关联 `appearances`、`managers` 和 `teams`；只连 `teamID` 易把多年记录混成笛卡尔式重复。
- 联盟、分区：`lgID` 指向联盟；分区识别还需要 `divID` 与 `lgID`。`active` 是数据字段，不是你根据当前现实棒球世界重新判断的属性。
- `G_all` 是总出赛数，`G_batting` 是打击出赛数，`HR` 是该统计行的本垒打数；三者不能替换。

## 4. 六题的任务清单

共同规则：先保住题目要求的**输出列顺序**、结果粒度及排序。列别名不计较，但列顺序计较；“最多十条”也不能在中间随意截断来省事。完整官方样例及 Q1 示范 SQL 请在[原题](https://15445.courses.cs.cmu.edu/fall2025/homework1/)对应小节查看，不在这里复制答案。

### Q1 · 0 分 · 输出约定热身

- 文件：`q1_sample.duckdb.sql`。
- 从 `divisions` 中列出全部活跃分区名称，按字母顺序排列；官方示范使用去重后的名称。
- 只有一列分区名称。题面给了正确查询和六行结果，用于核对提交／输出格式，不是可以省略的文件。

### Q2 · 20 分 · 资格与最高单条统计分开

- 文件：`q2_hr.duckdb.sql`。
- 限定曾为 **PA 州学校**打过球的人；在其全部年份和球队的 `appearances` 中找最高 `HR`。
- 输出最高者中的 **10 人**，主序为最高 HR 降序，次序为 **first name** 字母序。
- 输出两列：`name | max_hr_appearance`。
- 展示姓名格式必须为 `{FIRST} ({GIVEN}) {LAST}`；题面提示 `||` 可用于拼接。
- “single appearance”在此对应表里的一条统计记录及其 `HR`，不是生涯总和，也不是把表误当逐场数据。

### Q3 · 20 分 · 球员—球队、奖项年份与均值范围

- 文件：`q3_mvp.duckdb.sql`；虽然文件名有 `mvp`，指定奖项实际是 **`Gold Glove`**，不能按文件名改题。
- 找出 **10 个 `(player, team)` 配对**：球员在活跃联盟中于 **1999 年之后**赢得该奖，且打击出赛数超过其球队 **自 1999 年以来**的平均水平。
- 平均值依据该队各球员的 `appearances.G_batting`；不是 `G_all`，也不是先对每个人求平均再对均值取平均。
- 主序为**不同获奖年份数量**降序，次序为 **given name** 字母序。
- 输出三列：`nameGiven | teamID | distinct_years`。
- 两个时间范围不是同一个谓词：“after 1999”排除 1999；“since 1999”包含 1999。获奖、出场、球队的年份／联盟对应关系应明确，不把一个人别年别队的奖随意连接过来。官方提示 correlated subquery，但不强制某一种写法。

### Q4 · 30 分 · 先判团队年度事件，再统计出现年份

- 文件：`q4_award.duckdb.sql`。
- 对一个 `(team, year)`，事件 E 同时要求：**超过 5 名不同球员**在该年获奖；该队有经理在**同年**获奖。
- 范围为所有活跃联盟；找出 E **发生超过一次**的球队。
- 主序为 E 的出现次数降序，次序为球队名称字母序。
- 输出三列：`league | team_name | distinct_years`；使用联盟与球队的名称，不用 ID 冒充名称。
- 题面提示 correlated subqueries／CTE。多个奖或多个获奖经理不应把一个团队年度事件计数多次。

### Q5 · 20 分 · 每个人自己的最早队友

- 文件：`q5_hof.duckdb.sql`。
- 从**确已入选**的名人堂球员中选 **10 人**；对每位球员，找最早与他同队出现的队友。
- “队友”由两名球员在**同年、同队**的 `appearances` 定义；本人不是自己的队友。
- 若最早年份有多人，按队友的构造姓名字母序选第一人；最终结果按名人堂球员的构造姓名字母序排列。
- 输出三列：`hof_player_name | earliest_teammate_name | earliest_teammate_year`。
- 两个姓名都采用 `{FIRST} ({GIVEN}) {LAST}`。官方提示 lateral join；这里的“每人最早”不是整个结果集的全局最早一行。

### Q6 · 10 分 · 一条语句中的插入与冲突更新

- 文件：`q6_upsert.duckdb.sql`。
- 对 `teams` 中 **2024 年的所有球队记录**生成新记录，以原 `franchID` 作为新 `teamID`，其他信息按题意保留。
- 如果候选插入记录触发键冲突，将**已有冲突记录**的 `attendance` 改成 **−1**，而不是无条件把所有候选的 attendance 都设为 −1。
- 整个插入／更新必须在**一条 statement**内；不是先写 INSERT 再写 UPDATE，也不是提交查询假装修改完成。
- 评分会读取 2024 年记录，依次取 `yearID, lgID, teamID, franchID, teamRank, attendance` 六列，排序键依次为 `lgID, teamID, franchID, teamRank, attendance`。年份已经固定，不是漏做第六个排序维度。
- 这些是评分观察的列，不代表插入时可以丢掉 `divID` 或 `name` 等其他列；按完整 schema 分析候选新行。

## 5. 文件与提交规则

六个文件名必须保留；每题一条语句，CTE 可以属于同一条 statement，调试过程中用的多个独立查询不能原样塞进提交文件。

```text
placeholder/
  q1_sample.duckdb.sql
  q2_hr.duckdb.sql
  q3_mvp.duckdb.sql
  q4_award.duckdb.sql
  q5_hof.duckdb.sql
  q6_upsert.duckdb.sql
```

在 `placeholder/` 的**父目录**执行官方打包命令：

```bash
zip -j submission.zip placeholder/*.sql
```

`-j` 去除目录路径；ZIP 根目录应直接是六个 SQL 文件，不要套一层 `placeholder/`。题面先让你进入 placeholder 创建文件，打包示例又使用 `placeholder/*.sql`，因此要明确切回父目录，不能机械地在错误工作目录执行。

上传单个 `submission.zip` 到[官方 Gradescope 课程](https://www.gradescope.com/courses/1074751)，CMU 学生使用 Piazza 公布的课程码。题面允许反复提交，按类似 `diff` 的结果比较给反馈；输出元组、指定排序和列顺序均须认真核对。不要提交数据库、截图、说明文档或多余调试脚本代替 SQL。

本轮未验证登录后课程开放状态、校外 HW1 评分权限或实际分数；FAQ 的校外项目入口也不能替代这项验证。

## 6. 迟交与合作边界

- 大纲明确**不接受迟交 homework**；项目的四天 late-day 额度不能移到 HW1。
- 独立完成；可以讨论高层概念，但不能复制他人／网上答案，不搜索学生解答仓库，不把别人白板内容照抄成自己的查询。
- 不公开自己的答案。任何引用与帮助依照课程政策注明；如果不确定某种帮助是否允许，正式修课时向课程工作人员核实。
- 本站提供问题拆解与原创反例，不给六个可提交文件的查询实现。

## 来源与阅读边界

核对日期：**2026-11-15**。

1. [HW1 官方网页](https://15445.courses.cs.cmu.edu/fall2025/homework1/)：复用已有 HTML，正文顺序全文阅读，含 11 表、6 题、分数、样例、打包和合作规则；全文及页尾未发现开放翻译授权。
2. [官方 schema 图](https://15445.courses.cs.cmu.edu/fall2025/homework1/img/schema2025.png)：实际取得并目视核对 11 表与关系，未转载原图；实际数据库未打开，不能把图和网页的检查称为数据实测。
3. [课程大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html)：全文阅读，核对 homework 迟交与合作政策；未找到把课程视频 CC 许可外推到作业网页的授权。
4. DuckDB **1.3** 文档：[子查询](https://duckdb.org/docs/1.3/sql/expressions/subqueries.html)、[WITH](https://duckdb.org/docs/1.3/sql/query_syntax/with.html)、[FROM／LATERAL](https://duckdb.org/docs/1.3/sql/query_syntax/from.html)、[INSERT／ON CONFLICT](https://duckdb.org/docs/1.3/sql/statements/insert.html)。已读本作业需要的语义章节；WITH 的递归图遍历、FROM 的 As-Of 等非必要部分不声称全读。正文只做原创指导，不把这些网页当作可自由整份转载的许可证。
