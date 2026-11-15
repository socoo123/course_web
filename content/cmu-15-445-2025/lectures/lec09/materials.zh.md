# L9 课外资料：把“索引能回答”拆成三道检查

“有这个索引”不等于“查询只读这个索引”，也不等于“更新的工作消失了”。下面用三个问题把课堂的结构直觉推进到真实产品的执行约束：**候选是否完整，所需值是否齐全，可见性是否已证明。**

## 1. GIN 的 posting tree 与 pending list 是两种不同的补救

### 从复合值提取多个 key

PostgreSQL 文档把整个被索引值称为 item，把从中抽出的元素称为 key。比如一个数组是 item，数组中的元素是 key；文档是 item，抽出的词是 key。这与课堂为方便解释而把整列称为 key、内部词称为 term 的用词不同，读接口时先确认上下文。

GIN 保存 `(key, posting list)` 关系，同一行可以出现在许多 key 的 posting 中。它的通用性来自 operator class：类型扩展说明如何从 item 与查询提取 key，如何判断这些 key 的出现足不足以支持原查询；GIN 负责树、并发和日志等底层事务。

重要的是，提取后不一定保留原值的全部信息。`consistent` 可以说“肯定不匹配”“肯定匹配”或“可能匹配、需要 recheck”。`triConsistent` 则把未知明确建模为 `GIN_MAYBE`。这与本讲过滤器的思维相通：**候选不能被误当最终答案，无法证明的部分要复核。**

### Posting tree 解决单个 key 的命中集合过大

GIN 内部有一棵按 key 组织的 B-tree。较小的 posting list 可连同 key 放入一个 index tuple；太大时，用指针连接 posting tree，树里组织 heap pointers。这里外层按“元素值”查，内层按“记录位置”组织，不是在同一层把两个 key 类型混着比较。

多列 GIN 以 `(列编号, key 值)` 作为区分，避免不同列相同值发生语义混淆。空 item、NULL item 与 item 内 NULL key 还有专门处理；不能只用“没有抽到 key 就不存”推导完整 SQL 语义。本文不重复接口签名或展开可提交的 operator class 实现。

### Pending list 解决一条新记录引出许多树更新

新文档可能提取出几十、几百个 term；逐一即时修改主 GIN 结构很贵。启用 `fastupdate` 时，新条目可先进入未排序的 pending list，再批量移入主结构。文档列出的触发包含 vacuum／autoanalyze、显式 `gin_clean_pending_list`，以及 pending list 超过阈值。

这不是“延迟后工作就没有了”。读查询要同时覆盖主索引与 pending entries，否则会漏掉刚写入的有效记录。pending list 过大，读查询变慢；某次前台写入触发清理，又可能出现长延迟。后台清理与阈值是在吞吐、读开销、延迟稳定性之间权衡。

因此课堂的 mod-log 类比可以帮助理解批量维护，但不能替代具体语义：pending list 不是 WAL，也不能据此认定所有更新／删除都以相同方式写入一个通用日志。对响应时间更敏感时，文档还给出关闭 `fastupdate` 的选择，但那会改变写入成本，不能只写“关掉更快”。

### 一个容易误读的选项

文档还描述 `gin_fuzzy_search_limit`：默认 0 不限制；设非零值时，对很大的结果集合可返回随机子集，而且是软限制。这是明确改变返回集合完整性的配置，不能跟普通 GIN 的精确候选／recheck 保证混为一谈。任何“索引不会漏结果”的产品论断都应带上操作符类、执行方式与配置前提。

阅读定位：PostgreSQL 18 §65.4，尤其 §65.4.3 的一致性接口、§65.4.4 的结构与 fastupdate、§65.4.5 的搜索限制。

## 2. Partial index 的使用条件是逻辑蕴含

对 `Orders` 建以下自拟索引：

```sql
CREATE INDEX orders_open_sku
ON Orders (sku)
WHERE status = 'open';
```

它不是“全部订单的缩水版精确索引”，而是“只覆盖 open 子集的完整索引”。两类查询的正确性差别很直接：

```sql
-- 候选集合位于索引覆盖子集内
SELECT order_id FROM Orders
WHERE sku = 'A17' AND status = 'open';

-- 还需要 closed 等其他状态，不能只靠此索引回答
SELECT order_id FROM Orders
WHERE sku = 'A17';
```

必要关系是：查询谓词 $Q$ 蕴含索引谓词 $P$，即 $Q\Rightarrow P$。还要规划器能识别这个关系，而不是读者能在纸上证明就够了。文档解释它能识别一些简单不等式关系，但不是通用定理证明器；通常需要与查询条件匹配的形式。对未知参数的通用计划，也不能假设参数未来必然落在索引子集内。

文档给出的另一层用途是部分唯一性：只在满足谓词的行之间强制唯一，不约束集合之外的行。这是约束语义，不只是读性能优化。也因此，不能把“没被索引”的行理解成“不受任何其他表约束影响”。

### 何时部分索引反而拖累系统？

若只对少数热点或罕见状态感兴趣，减少无关行可能节省空间与维护。但数据分布或负载变了，原来的排除条件可能不再有用，还可能让某些本来能用索引的请求失去访问路径。

文档明确反对用大量互不重叠的部分索引模拟分区。为每个月、每类各建一棵树，会让规划器逐一判断适用性，它并不自动理解这些部分索引组成一个统一分区方案。复合索引或真正分区可能更合适。课堂按月索引的例子应在这个约束下理解，不能推广为无限扩张的生产规则。

阅读定位：PostgreSQL 18 §11.8，尤其谓词蕴含段、Example 11.3 部分唯一性、Example 11.4 不替代分区。

## 3. Covering 是值的性质，index-only 还要可见性支持

PostgreSQL 的索引与 heap 分离。普通索引扫描找到记录位置后，需要访问 heap；即使索引候选很集中，heap 中的行也可能分散，产生随机访问。

对以下自拟查询，可以考虑携带返回列：

```sql
CREATE INDEX orders_sku_payload
ON Orders (sku) INCLUDE (order_id, status);

SELECT order_id FROM Orders
WHERE sku = 'A17' AND status = 'open';
```

`sku` 是搜索 key；`order_id, status` 是 payload。它们可供返回或过滤，却不因此成为同等的导航键。若使用 `UNIQUE`，唯一性约束也只作用于真正 key，不把 INCLUDE 列自动并入唯一性判断。B-tree 上层的 suffix truncation 会去掉非 key payload，帮助保持路标紧凑。

### 三道检查

1. **访问方法支持吗？** 文档说明 B-tree 支持 index-only；部分 GiST／SP-GiST operator class 支持。GIN 通常只存原值的组成部分，不能重建完整原值，因此不支持这种 index-only scan。
2. **值齐全吗？** 查询要读的列或可重建值必须在索引中。表达式索引、部分索引会使规划器识别更复杂；不能凭“我能推导出来”假设规划器必定采用。
3. **可见性已证明吗？** 对 PostgreSQL MVCC，每条结果还需对当前 snapshot 可见。索引项本身不存完整可见性信息；访问相应 heap page 的 visibility map，若 all-visible bit 已设，可直接返回，否则仍需访问 heap。

所以执行计划写着 Index Only Scan，仍不等于运行中 heap fetch 次数一定为零。经常修改的表更可能需要 heap 核验；很少改动、很多页 all-visible 的表更有机会受益。本文没有运行 PostgreSQL 或 EXPLAIN，不提供虚构执行计划和性能数字。

### 为什么不把全部列都 INCLUDE？

Payload 会复制表数据，增加索引体积、缓存压力和写维护。过宽的 index tuple 甚至可能超出访问方法的大小限制，使插入失败。若 heap 无论如何都要读，额外 payload 的收益又可能很小。增加列前，应该把少一次 heap 访问的价值与新增叶页及维护成本放在同一个模型里。

阅读定位：PostgreSQL 18 §11.9，包括表达式索引的规划器限制和部分索引交互。

## 4. 用同一套问题审视三种优化

| 优化 | 延后或省略了什么 | 必须保留什么 |
|---|---|---|
| GIN pending list | 延后大量主树写入 | 查询不能漏 pending entries |
| Partial index | 不存谓词外的行 | 查询必须处于被覆盖子集 |
| INCLUDE／index-only | 争取省 heap 取值 | 所需值和行可见性都要满足 |

共同原则是：**少做工作之前，先说清是哪一条不变量允许你省掉它。** 这比记住“GIN 很快”“覆盖索引不回表”更能迁移到陌生系统。

<details>
<summary>自测：pending list 只由后台合并，前台查询能否只看主 GIN 树？</summary>

不能。未合入的有效新条目仍属于查询语义范围，必须由查询或等效机制覆盖。延迟物理维护不能延迟已经承诺的数据可见性。

</details>

<details>
<summary>自测：数学上等价的两种 WHERE 写法，必然同样使用部分索引吗？</summary>

不必然。正确性蕴含与规划器能否识别是两层条件，后者依赖具体表达式和版本。这里只作解释，没有执行查询来证明某个计划。

</details>

---

## 来源、版本与许可

这是基于实际独立阅读的**原创资料导读**，不是 PostgreSQL 文档或教材的完整译文，也不只是重复课堂 slides。

- 作者／维护方：PostgreSQL Global Development Group；实际来源为 [PostgreSQL 18 §65.4 GIN](https://www.postgresql.org/docs/18/gin.html)、[§11.8 Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html)、[§11.9 Index-Only Scans and Covering Indexes](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)。页面显示 18.7 文档及 2026-11-12 更新信息，实际读取与快照取得为 2026-11-15/16。它们是课堂之外的后来版本补充，不能倒填成 Fall 2025 当时的实现事实。
- 已读范围：§65.4 GIN、§11.8 Partial Indexes、§11.9 Index-Only Scans 全部可见正文。未独立读取链接源码、图文件、标准文本、历史论文或其他产品排名实现。早先尝试单独的 `gin-implementation.html` 返回 404，改从 `gin.html` 读取合并后的完整章节。
- 指定教材 *Database System Concepts* 第七版 §14.1–14.4、§24.1 正文仍未取得／未读，章节定位不是精读证据。本页不是这些章节的替代全译。
- 本批未单独核查这些网页的全文翻译再许可，标记为未知；因此使用自拟 Orders 示例与原创解释，不复制整篇文档。课堂视频 CC 标签只适用于那个视频，不外推到产品文档。
- 来源 URL、取得时间、内容哈希与阅读状态见 [source-manifest](https://github.com/socoo123/course_web/blob/main/content/cmu-15-445-2025/source-manifest.json)。未运行数据库、SQL、测试或 benchmark；不声称实验完成。
