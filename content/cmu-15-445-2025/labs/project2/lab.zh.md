---
source: CMU 15-445/645 Fall 2025 Project2完整网页；固定BusTub源码、骨架与五份公开测试
version: v20251119-2025fall；d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 原创要求导读；题面全文翻译许可未知；BusTub源码MIT许可单独核查
status: 静态阅读完成；未运行骨架、构建、测试、排行榜或Gradescope；learnerLabCompletion not_attempted
---

# Project 2：带延迟删除的并发 B+Tree

导航：[无答案指导](#/c/cmu-15-445-2025/lab/project2?v=guide) · [Project1指导](#/c/cmu-15-445-2025/lab/project1?v=guide) · [L8索引](#/c/cmu-15-445-2025/lec/lec08?v=notes) · [L10索引并发](#/c/cmu-15-445-2025/lec/lec10?v=notes) · [公共资料](#/c/cmu-15-445-2025)。

这里按官方四项任务整理全部要求，并补上固定源码才能确认的接口与边界。它不是题面逐句翻译，也不是学生实现。**Fall 2025 的叶页包含 tombstone buffer，不能用旧年“删除就移动数组”的普通 B+Tree 代替。**

## 1. 交付目标与工作边界

你要建立支持唯一键的页式 B+Tree：内部页负责路由，叶页保存 key 与 RID；支持线程安全的点查、插入、删除、结构调整及按序迭代。完成指标不是“填完空函数”，而是操作后仍满足树结构、可见性、资源生命周期和并发协议。

- 官方发布日期为 **2025-09-29**，截止为 **2025-10-26 23:59**；这是历史课程日期，不是当前学习期限。网页显示最后更新 **2025-10-03**。
- 必须独立完成。可以讨论高层设计；不能复制讨论白板、他人实现或网上答案，也不要公开自己的实现和提交归档。
- 依赖 Project1 的 BPM 与 page guards；若前一项目有误，须修复，不能在本项目绕过缓冲池。先复用本站 Project1 的 pin／dirty／Drop／锁顺序指导。
- 保留原有公开函数签名和既有成员；可以增加必要的函数、成员。页内成员另受固定布局约束，不能随意加动态容器。
- 网页中的 `git pull public master` 是当学期指令。历史学习固定到本页 SHA，不将当前 master 混进来；私有仓库与环境准备复用 [Project0](#/c/cmu-15-445-2025/lab/project0?v=guide)。

| 官方任务 | 本页定位 | 核心验收对象 |
|---|---|---|
| Task 1 — B+Tree Pages | §2–3 | base/internal/leaf 格式、容量、tombstone、页访问 |
| Task 2 — Operations | §4 | Insert／Remove／GetValue、分裂合并借位、root/header |
| Task 3 — Index Iterator | §5 | Begin／Begin(key)／End、跳过删除项、生命周期 |
| Task 4 — Concurrency Control | §6 | optimistic crabbing、安全判定、释放与重启 |
| Leaderboard（优化可选） | §7 | 并发基准正确结束；性能优化不是基本功能替代品 |
| 通用要求与提交 | §8–10 | 测试、图形调试、风格、内存、归档、合作政策 |

## 2. Task 1：页格式先于树算法

### 2.1 四种身份不要混用

以 `Orders(order_id)` 索引为例：业务键 `order_id` 决定排序；叶页 value 是定位表记录的 **RID（表页 page id 与 tuple slot）**；内部页 value 是定位下一层索引页的 **page_id**；BPM 的 **frame_id** 只是当前驻留内存槽。叶数组下标又是第五种位置，不是 RID 的 tuple slot。

固定 `config.h` 的页大小是 **8192 字节**。一页的索引结构覆盖在 BPM 返回的数据区域，不是独立 `new` 出来的整棵内存树。读取用 `ReadPage`，修改用 `WritePage`；通过 guard 的 `As<T>()`／`AsMut<T>()` 解释字节。对应 guard 必须覆盖指针使用期，最后由 Drop／析构释放页访问资源，不要手动重复 unpin。

### 2.2 Base Page

`BPlusTreePage` 的公共头是三个4字节字段：页类型 `page_type_`、物理项数 `size_`、最大项数 `max_size_`。完成：

- `IsLeafPage`、`SetPageType`；
- `GetSize`、`SetSize`、`ChangeSizeBy`；
- `GetMaxSize`、`SetMaxSize`、`GetMinSize`。

`GetMinSize` 的骨架注释允许根据设计选择半满阈值的取整方式，不要从别的年份抄一个公式就认定全项目适用。根页是需要单独处理的边界；内部根只剩一个孩子、最后记录消失等不能按普通非根页机械处理。

### 2.3 Internal Page

内部页存储有序分隔键与孩子页号：有效分隔键数比孩子数少一。固定结构是分离的 `key_array_` 和 `page_id_array_`，不是可任意替换成 vector 的 pair 数组。第0个 key 无效，第0个 child 有效；`GetSize()` 对应孩子／数组项数，不能当成有效分隔键数。

完成 `Init`、`KeyAt`、`SetKeyAt`、`ValueAt`，并留意头文件还有 `ValueIndex` 声明，而对应 `.cpp` 没有预留函数体。新增辅助操作也必须保持原接口与路由约束。查找从有效分隔键开始，根据比较器选择孩子；一条分隔键是路由边界，不是叶中记录的第二份业务数据。

非根内部页应维持半满要求。插入造成不变量破坏时分裂或重新分配；删除后需要借位或合并时维护父分隔键与孩子关系。内部页的 value 为 `page_id_t`，叶页为 RID，因此二者容量**不必相同**。

### 2.4 Leaf Page

叶页包含基础头、`next_page_id_`、tombstone 数目、固定 tombstone 下标数组、`key_array_`、`rid_array_`。完成 `Init`、`GetTombstones`、`GetNextPageId`、`SetNextPageId`、`KeyAt`；按需要添加辅助方法，但不能改掉提供的 key/value 数组。

新增页字段只能使用适合原始页字节布局的简单类型，不能把 `std::vector` 等拥有动态资源的对象放进页内。`GetTombstones()` **返回** vector 与页内**保存** vector 是两件事。类构造被删除，页初始化依赖 `Init`；注释提到 page id／parent id 不代表当前类已有这些字段。

## 3. 本年关键规则：逻辑删除不等于删除槽位

### 3.1 容量由模板决定

树、叶页和 iterator 使用带 `ssize_t NumTombs` 的完整模板参数，默认值是0：

- `NumTombs > 0`：每叶固定最多容纳 k 个待兑现删除；不是整树共享队列，也不是根据当前页大小动态扩容。
- `NumTombs == 0`：没有延迟删除缓冲，删除需要落实到物理项。
- `NumTombs < 0`：固定宏使用 `LEAF_PAGE_DEFAULT_TOMB_CNT`，当前默认0。官方排行榜使用 **-1**，允许为此模式调整默认数量；不能把自由优化外推到显式 k 的功能测试。

叶容量宏从8192字节扣除16字节头、一个 `size_t` 的计数和 k 个 `size_t` 下标，再除以 key/RID 的合计大小。运行时 `leaf_max_size` 还可能人为设得很小。**编译期能放多少、运行时设多少、逻辑剩多少项是三种量。**

### 3.2 删除、读取和重新插入

| 情形 | 必须维持的可观察语义 |
|---|---|
| k>0，删除活跃键 | 立即在索引逻辑上消失，但物理 key/RID 可仍留在页内；tombstone 记录的是物理数组下标 |
| 缓冲尚有空位 | 可记录此次删除，不能为了简化而提前把全部旧 tombstone 清空 |
| 已有 k 个待删除项，又接收新的待删除项 | 兑现最旧项的物理删除，再维持至多 k 个待删除项；恰好填到 k 不等于把全部清空 |
| `KeyAt(i)` | 返回第 i 个物理 key，即使这个槽已 tombstoned |
| `GetTombstones()` | 返回待删除的 key，按**最旧在前、最新在后**，不是按 key 大小排序 |
| 点查／普通扫描 | 不把 tombstoned 项当作活跃记录返回 |
| 插入仍活跃的重复键 | 不插入、不覆盖旧 RID，返回 false |
| 重新插入仅剩 tombstone 的同键 | 不是活跃重复键；须恢复为一个可见项，使用本次传入 RID，去掉对应待删除状态 |
| 删除不存在或已逻辑删除的键 | 不应凭空多建记录或重复累积同一删除；保持其他键和顺序不变 |

题面“buffer 有 k 项时兑现”的句子容易误读。固定 `TombstoneBasicTest` 与 `TombstoneSplitTest` 确认缓冲能保留 k 项，后续压力才兑现最旧项；`b_plus_tree_leaf_page.cpp` 明确 `GetTombstones` 最旧在前。重新插入语义也由 Basic 测试实际覆盖，不能把物理 key 存在直接等同于重复键失败。

### 3.3 结构变化不能丢掉待删除历史

- **插入或压缩数组**：物理位置会移动；每个仍存在的 tombstone 必须继续指向原来那个 key，而不是继续使用过期下标。
- **分裂**：key/RID 移到哪个叶，其待删除状态也随之归属那个叶；各叶保留分配到自己条目的原相对删除次序。不能把分裂当成清空 tombstones 的机会。
- **合并／重新分配（借位）**：官方特别规定，搬入叶的待删除项视为比接收叶原有待删除项**更新**；需要处理容量压力时，接收叶原有待删除项先处理。这不是把两叶按真实墙钟时间重新全局排序。
- **可见项为零**：不代表物理页一定已清空。固定 tombstone 测试要求所有键逻辑删除后仍可能有物理页／待删除记录，但 `Begin().IsEnd()` 为真；k=0 的普通删除测试则检查最终 root id 为 invalid。

页占用、逻辑可见项、tombstone 队列和树结构必须联合检查。不能用“只剩一个可见 key”就断言页物理下溢，也不能仅因 `GetSize()>0` 就让 iterator 解引用。

## 4. Task 2：查、插、删与根变化

固定公共接口：

| 方法 | 职责 |
|---|---|
| `IsEmpty() const -> bool` | 判断索引无可见键值；注意物理页保留与逻辑空的区别 |
| `GetValue(const KeyType &, vector<ValueType> *) -> bool` | 唯一键点查；找到活跃项时报告其唯一 value，未找到返回 false |
| `Insert(const KeyType &, const ValueType &) -> bool` | 插入新活跃项；拒绝活跃重复键；必要时调整树 |
| `Remove(const KeyType &) -> void` | 删除目标键；维护 tombstone 与必要的借位、合并及根收缩 |
| `GetRootPageId() -> page_id_t` | 从一致的 header/root 状态报告根页号 |

`KeyType` 通常是不同宽度的 `GenericKey`；`ValueType` 通常是 RID。`GenericComparator` 实际返回负数／0／正数，不能按布尔“是否小于”使用，也不要用调试专用 `ToString()` 或原始字节比较代替它。

根 id 保存于独立的 `BPlusTreeHeaderPage::root_page_id_`；构造器接受的是 **header page id**，不是已经存在的根页。固定构造器初始化 header 的根为 `INVALID_PAGE_ID`，不是自动恢复已有持久化树的打开接口。插入形成首根、根分裂、删除导致根收缩／失效都必须保持 header 正确；不能只更新线程栈上的变量。

`Context` 是可选辅助类，包含 `header_page_`、`root_page_id_`、`write_set_`、`read_set_`。写集合可以保存访问路径供结构修改找到父页，读集合不要求一定使用。保存 guard 是保存访问责任，不是保存永久有效的页指针。释放 header 时 reset 为 `nullopt`，其他 guard 显式 Drop／移出容器；不能只丢失裸指针就以为锁释放了。分裂前可用断言检查父路径／header 的必要保护是否仍存在。

官方建议以二分查找寻找页内位置，线性查找可能超时。其建议分裂时机是叶页插入后值数达到 `max_size`、内部页插入前达到 `max_size`；这是建议而非唯一合法方案。若选择其他策略，必须自行证明不越过实际数组容量、不产生未处理的单孩子内部页、保持既定占用规则，不能把建议误读为允许写越界。

## 5. Task 3：有序迭代与页内对象寿命

迭代器沿叶链按 key 顺序访问所有活跃 key/RID，并跳过 tombstone。固定接口大小写为：

- `IsEnd()`；`operator++()` 返回 iterator 引用；
- `operator*()` 返回 `std::pair<const KeyType &, const ValueType &>`；
- `operator==`、`operator!=`；可按成员需要设计构造器，维护析构资源责任；
- 树的 `Begin()`、`Begin(const KeyType &)`、`End()`。

结束是**尾后状态**，不是最后一个仍可读取的键值。网页 `isEnd` 的说明写“最后一个 pair”，但固定测试使用 `iter != End()` 或 `!IsEnd()` 后解引用，要求最后活跃项也能访问。网页小写 `begin/end` 与固定头文件的大写也有差异，不要为了照网页而改测试接口。

网页还把 iterator 的 `.cpp` 链接写成 `src/index/storage/index_iterator.cpp`；固定树目录的真实路径是 `src/storage/index/index_iterator.cpp`。按真实目录定位，不创建倒置路径来迎合网页笔误。

`Begin()` 要处理物理空树、仅有 tombstones 的树及开头整叶无活跃项。`Begin(key)` 用于从指定低键开始扫描；固定骨架只写“找到包含输入 key 的叶”，公开用例覆盖 key 存在的情况。对 key 不存在时，建议明确采用通常的“不小于 key 的首个活跃项”下界语义并自测，不把公开测试未证明的完整边界误称已验证。

解引用返回页内引用，不能引用临时拼出的 pair 值或已释放的页。跨叶后旧引用不应继续被当作稳定快照；资源保留方式与移动／析构必须一致。不要为了扫描把整棵树预先复制进 vector。

## 6. Task 4：并发要求不是最后加一把锁

官方要求 **optimistic latch coupling/crabbing**，必要时取页 latch，确认安全后尽早释放祖先。不能用全局锁从操作开始保护整棵索引直到结束；也不能把 header 写锁全程当作等价的全树大锁。

- latch 保护页结构与字节的一致性，不等于事务 lock，不提供可串行化、范围谓词锁或 MVCC。
- pin 防止 frame 被驱逐，不能代替读写 latch；`shared_ptr` 也不能替代 pin。
- 乐观路径应允许只读经过内部节点、在安全的局部修改情形仅写目标叶；结构变化需要合适的重启／更强路径保护。
- safe 必须按**操作、物理容量、tombstone 压力、分隔边界与根特例**判断，不是静态的“这个节点半满”。具体检查问题见指导页。
- 单线程不能重复获取同一页的 read latch；不要假设共享 mutex 递归可用，也不要持读锁直接阻塞等待本页写锁而不考虑升级死锁。
- 官方要求按 header 到下层取得 latch，释放也按从上到下的顺序；`Context` 是 deque，不代表随手从尾部析构就满足这一要求。
- 兄弟间移动是额外的横向取锁问题。官方说不测试 iterator 的线程安全叶扫描，但正确并发叶扫描在无法取得兄弟 latch 时应抛出 `std::exception`，避免相向等待死锁；不测不等于可无限等待。固定公开 traced/BPM 接口没有直接给出 try-read 方法，不能虚构 `TryReadPage` API。

固定 `bpm_` 是 `shared_ptr<TracedBufferPoolManager>`，头文件明确禁止改成普通 BPM。公开 OptimisticInsert／OptimisticDelete 测试通过读写计数观察局部安全更新的访问方式；绕过 tracer 不属于实现优化。

## 7. 排行榜：优化可选，正确结束仍是要求

官方基准 `tools/btree_bench/btree_bench.cpp` 多线程执行查找与更新；优化排名可选，前四项即可获得基本完整分数，但基准必须正确结束，不能死锁或段错误。使用 `NumTombs=-1`，可研究 tombstone 表示、默认容量等；该任务允许假定整数 key，不能据此缩窄一般接口。

固定基准中的一条注释把重复插入写成“overwrite”，但 Task2 明确活跃重复键不插入并返回 false。**基准注释不改变唯一键契约。** 不根据基准的键分布或读写比例硬编码答案，不把某一次吞吐当作评分保证。

## 8. 公开测试、调试与运行边界

本轮全文读过下列五份固定公开测试，但**没有编译或运行**：

| `test/storage/` 文件 | 实际涉及的能力 |
|---|---|
| `b_plus_tree_insert_test.cpp` | 初始根叶、点查、多层插入、迭代入口、乐观局部插入 |
| `b_plus_tree_delete_test.cpp` | 删除／空根、不同小容量混合操作、乐观局部删除 |
| `b_plus_tree_sequential_scale_test.cpp` | 打乱插入顺序、小页与小缓冲池、多层点查 |
| `b_plus_tree_concurrent_test.cpp` | 同键及分区插删、混合写、稳定键并发查；k=0与k=3 |
| `b_plus_tree_tombstone_test.cpp` | 延迟删除、重新插入、顺序、逻辑空扫描、分裂、借位、合并 |

网页 Testing 只列前四份；固定仓库第五份不能遗漏。所有这些测试声明均带 `DISABLED_`，默认执行零条不能说通过。实现完成后在私有工作区按课程方式启用相关用例；不要删除断言、弱化预期或启用未实现未来项目来制造噪声。公开测试不是全部隐藏评分，仍需自己设计边界和交错场景。

官方提供 `b_plus_tree_printer`，可设置叶／内部最大项数，交互插入、删除、打印与导出 DOT，再用 Graphviz 本地显示。图中的内部第一个空 key 是正常的；叶的物理 key 行和 tombstone 行要分开看。固定 printer 实例用 k=2；不同 k 要明确变更私有调试配置。官网另有浏览器参考可视化入口，本轮没有运行或核验其结果。

编者提醒：图只是一张状态截面，不证明 latch／pin／并发正确性。固定头文件的 `LeafPage` alias **没有传入 NumTombs**，而 debug helper 使用这个 alias；遇到非零 k 的布局／图形异常，应先审计模板传递，不能盲目把调试图当真值，更不能把所有叶强转成默认 k=0。

## 9. 环境、质量与提交

固定 CMake 要求 **C++17**，推荐 **Clang15**；Fall2025 FAQ Q5 写 **C++20**。二者不一致，本页按固定可复现源码保留17，不悄悄升级标准。README 支持 Ubuntu24.04 或 macOS（M1/M2/Intel）开发，评分环境为 Ubuntu24.04，且明确不支持 WSL。Apple Silicon 上 AppleClang、mutex 行为与 sanitizer 能力不等价于 Linux 评分环境；本机没有完成该环境验证。

官方质量要求：

1. Google C++ Style；`format` 会修改文件，`check-lint`、`check-clang-tidy-p2` 检查风格；题面警告不通过可记零分。
2. Debug 下使用 ASAN／LSAN 检查内存；题面注明 macOS 只支持 ASAN 而不支持 LSAN，不能用本机无报告代替 Linux 泄漏检查。
3. 可用图形调试器；必要时为了调试临时用 `-DBUSTUB_SANITIZER=` 关闭 sanitizer，但这不是修复内存错误，最终须恢复检查。
4. `BUSTUB_ASSERT` 中的表达式在 Release 不执行，不能放必需副作用；必须始终执行的检查用 `BUSTUB_ENSURE`。
5. 换编译配置时，`make clean` 不等于清空 CMake 缓存；采用新的独立构建目录重新配置，不误删源码。
6. 评分看测试正确性、无泄漏、风格；超时可能来自死锁或超过题面所述60秒限制，日志过多也会影响评分。不要先靠删日志掩盖错误。

固定 `submit-p2` 生成根目录的 `project2-submission.zip`。它包含下面11个 P2 文件及 Project1 的8个文件：

```text
src/include/storage/page/b_plus_tree_page.h
src/storage/page/b_plus_tree_page.cpp
src/include/storage/page/b_plus_tree_internal_page.h
src/storage/page/b_plus_tree_internal_page.cpp
src/include/storage/page/b_plus_tree_leaf_page.h
src/storage/page/b_plus_tree_leaf_page.cpp
src/include/storage/index/index_iterator.h
src/storage/index/index_iterator.cpp
src/include/storage/index/b_plus_tree.h
src/include/storage/index/b_plus_tree_debug.h
src/storage/index/b_plus_tree.cpp
```

P1 归档列表见 [Project1指导](#/c/cmu-15-445-2025/lab/project1?v=guide)。新增未列入归档的文件不一定能到达评分环境；尤其 header page、tracer 等虽需阅读，却不在上述 P2 修改清单中。不要为了绕开问题把实现放到未提交的任意文件里。

官方允许多次提交并反馈；CMU 学生使用当年 Piazza 发布的课程信息，迟交按 syllabus 的 late policy，项目问题走 Piazza 而非直接邮件 TA。校外入口见 FAQ，但登录、加入课程与评分可用性本轮均未核验，不承诺隐藏分数。完整命令路线放在指导页，**不是让尚未实现的骨架先跑起来**。

## 10. 来源与阅读记录

本页为原创中文导读。官方项目网页全文已读，但没有发现足以授权全文翻译发布的许可，因此不发布逐句译文。BusTub 固定仓库 [MIT LICENSE](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE) 已单独全文核查；该许可不自动覆盖课程网页、教材或视频。没有搜索学生答案、改学生源码或提交原始媒体。

- [Project2完整题面](https://15445.courses.cs.cmu.edu/fall2025/project2/)：Overview、Task1–4、Leaderboard、Roadmap、Hints/Pitfalls、Testing/Visualization、Formatting/Memory、Grading/Submission/Collaboration 全部读取。
- [固定页声明目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/storage/page)：`b_plus_tree_page.h`、`b_plus_tree_internal_page.h`、`b_plus_tree_leaf_page.h`、`b_plus_tree_header_page.h` 全文；前三者对应 `.cpp` 全文。
- [固定索引声明目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/storage/index)：`b_plus_tree.h`、`index_iterator.h`、`b_plus_tree_debug.h`、`generic_key.h`、`b_plus_tree_index.h` 全文；tree／iterator／index adapter 对应 `.cpp` 全文。
- [固定公开测试目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/storage)：§8所列五文件及 `test/include/storage/b_plus_tree_utils.h` 全文。仅概括覆盖意图，不提供测试答案或可提交实现。
- [Traced BPM](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/buffer/traced_buffer_pool_manager.h)、BPM／page_guard 声明、`common/rid.h`、`common/config.h` 全文；Project1内部实现细节复用既有指导，不重做前项。
- [固定 benchmark](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/tools/btree_bench/btree_bench.cpp)、printer 及各自 CMake 全文；根 `CMakeLists.txt`、`test/CMakeLists.txt`、[README](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/README.md) 全文；[FAQ](https://15445.courses.cs.cmu.edu/fall2025/faq.html) Q2–11局部阅读，用于C++与校外参与差异。
- 逐文件 SHA256、获取／阅读／许可的独立状态见[课程来源清单](https://github.com/socoo123/course_web/blob/main/content/cmu-15-445-2025/source-manifest.json)。图像、音视频、官方浏览器参考树未核验；本页不依赖其视觉结果。学习者完成状态仍为 **not_attempted**。
