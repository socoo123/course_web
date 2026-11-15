---
source: Fall 2025 Project1全页及固定BusTub声明、骨架、公开测试、channel和disk依赖；来源见要求页
version: v20251119-2025fall；d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 原创无答案指导，不是题面全文授权翻译；不包含可提交完整实现
status: 仅静态分析；未运行学生骨架、工具链检查、测试或排行榜；learnerLabCompletion not_attempted
---

# Project 1：用不变量贯穿一页的生命周期

导航：[完整要求与固定接口](#/c/cmu-15-445-2025/lab/project1?v=zh) · [Project0先修](#/c/cmu-15-445-2025/lab/project0?v=guide) · [L4笔记](#/c/cmu-15-445-2025/lec/lec04?v=notes) · [公共资料](#/c/cmu-15-445-2025)。

不要从“填完所有空函数”开始；先明确某个page当前由谁保留、谁允许读写、谁承担最后一次释放责任。本文不给实现代码或完整逐步解法，而给设计检查、反例和私有测试方向。

## 1. 开工前必须能解释的C++关系

复用Project0的RAII、移动／复制区别、`unique_ptr`／`shared_ptr`及调试准备。此处只补本项目增加的关系：

- `shared_ptr<FrameHeader>`管理对象存活；它不pin页面，也不锁页数据。
- `std::atomic<size_t>`使单个计数操作安全；它不会把page table、计数、ARC状态合并为一个原子事务。
- `std::shared_mutex`允许多个读者或一个写者；它不是递归锁，也不是事务锁。
- `std::promise<bool>`是一次性完成端，future是等待端；获取future后移动promise，仍应由唯一处理者完成同一个共享状态。request因此不可随便复制。
- `std::optional<Guard>`的“有值”和guard内部`is_valid_`是两个层次；移动走里面的guard不会凭空增加一份pin。

公开guard测试特意把guard放入vector、移动覆盖、自移动、从无效对象移动。只做“正常构造—析构”不足以证明资源管理正确。

## 2. 给frame画状态图，但别把所有属性压成一个枚举

可在私有草稿标出以下概念状态：空闲 → 正在装载 → 驻留且被pin → 驻留且可驱逐 → 正在写回／复用。它们是**设计推演状态，不是题目要求新增的枚举或完整实现方案**。dirty、页锁和pin数还要单独记录。

以逻辑订单页`Orders#A`为例：frame F曾装A，后来装B。F的地址可以完全没变；若某个异步请求还拿着指向F的裸指针，地址有效却可能已经指向错误的逻辑页。这类错误不会总表现为悬空指针，更可能是数据静默串页。

### 每个公开操作前后都应成立的不变量

| 不变量 | 违反时的可观察症状 |
|---|---|
| 同一驻留page只有一个frame；一个frame不同时属于两个page | 同页两个写者操作不同副本，最后写回互相覆盖 |
| free frame不同时出现在已发布的驻留映射／替换候选中 | 一个空闲槽被重复分配 |
| pin大于0的驻留frame不可被Evict选中 | 持guard读到另一页内容 |
| ARC Size等于可驱逐驻留项数 | 明明有候选却报告满池，或计数下溢 |
| 正常I/O完成前缓冲不能销毁、改装或被不兼容访问 | 写回存了新页数据、读取被并发修改 |
| 有效guard拥有一份访问资源责任；移动只转移它 | pin泄漏、double unpin、重复解锁 |
| dirty清除针对的是已安全写出的版本 | Flush返回后新修改被当成clean而丢失 |

这些不变量约束的是完整状态转换，不是要求在每条机器指令之间所有外部线程都可任意观察中间状态。你需要明确哪些中间状态由哪把锁／哪种保留机制遮住。

## 3. ARC：先写纸面账本，再选择容器

要求页已列全四种RecordAccess与驱逐规则。这里关注如何证明状态一致，而非再次给一遍算法。

### 3.1 三种身份不能串用

驻留记录关联`page_id`与`frame_id`；ghost记录只认page。假设F原来放A，被驱逐后放B，再后来A被装到G：

- B使用F不是A的ghost命中；
- A使用G仍可能命中A的ghost；
- ghost里的旧frame id不能作为驱逐结果交给BPM。

这是公开`SampleTest`的重要意图。用一个“frame出现过就算命中”的集合会把缓存历史和内存槽历史混淆。

### 3.2 每一步记录哪些列

自行生成不与公开样例相同的短访问序列，记录：操作、T1、T2、B1、B2、目标p、evictable集合、Size。至少让序列分别触及：

- 真实命中；两种ghost命中；四表全miss；
- 目标上／下边界；ghost长度比例不为1；
- T1长度等于目标；优先侧全部pinned、另一侧可选；两侧都不可选；
- `|T1|+|B1|=c`裁剪及总量`2c`裁剪；
- 重复SetEvictable、Remove不存在项、Remove不可驱逐项；
- 同一frame复用成新page，以及同一page回到不同frame。

每次计数变化都写明触发原因。访问热度变化不自动增加可驱逐项；设同样的evictable值不应再加减计数；Remove与Evict也不能共用错误的ghost语义。

### 3.3 容器选择与性能门槛

若每次访问都在线性列表里从头找节点，长轨迹会让`RecordAccess`越来越慢。先问是否能由身份直接找到对应状态／列表位置，再比较更新时的成本。选择标准容器即可，不必引入复杂框架或每次访问复制整份缓存。

不要因为公开文件只有两个顺序样例，就认为并发与性能不用做。网页明确提到RecordAccess性能测试；公开测试没有包含它，不代表隐藏测试没有。

## 4. Scheduler：把完成信号画在真实I/O之后

建议先在纸上画三个泳道：调用者、队列、worker。标出future取得、request移动入队、DiskManager开始／结束、promise完成、调用者允许复用缓冲的时刻。

### 4.1 两种不同的所有权

`Schedule(vector&)`借用vector作为输入容器，但异步worker不能依赖函数返回后vector仍在。请求与promise需要有效转交给队列／worker；vector里被移动的请求不是可再次重复提交的完整请求。至于`data_`，它仍只是借来的整页缓冲地址。

不必为了异步就无条件复制每个8KB页；先证明保留frame及访问约束能否覆盖I/O。如果设计确实使用临时缓冲，必须明确谁持有它、何时可释放、写回后如何判定哪个版本已持久化，不能只为让一个断言通过偷偷拷贝。

### 4.2 Exactly-once指的是回调，不是分布式存储保证

这里的“恰好一次”要求是：每个正常被接收的请求，在操作完成后由唯一所有者完成一次promise。它不意味着磁盘介质级exactly-once，也不是WAL或事务提交协议。

遗漏完成会让`future.get()`永久等候；提前完成会让调用者复用仍在读写的缓冲；重复完成会破坏promise协议。固定API返回`bool`的future，但底层读写是`void`，不能从true推断所有操作系统／硬件错误都已经被严密检测。

### 4.3 关闭不是“队列空了就return”

`Channel::Get()`在空队列上等待，并通过predicate抵御虚假唤醒；暂时没有请求不是scheduler生命周期结束。固定析构把`nullopt`放进FIFO后join，单worker要处理此前已接受的请求再退出。

在对象被销毁前先停止生产者，并保证DiskManager没有被提前关闭／释放。不要把“析构可清空合法队列”扩成“任意线程都可与对象析构并发调用Schedule”。如果做多worker优化，要重新证明所有worker能退出、已接收请求全部完成、同页请求不乱序。

### 4.4 应补的私有边界场景

公开测试只有一写一读，且分别是长度1的vector；它不能证明空vector、多请求批次、多个生产者、未等future就启动正常关闭等情况。自行设计时使每个缓冲的生命周期清楚，先验证内容及future完成，再测吞吐。不要通过缩短等待、吞掉future异常或伪造true来“修复”挂起。

## 5. BPM与guard的交接点才是并发核心

### 5.1 命中也可能出错

找到page table项不代表可以先释放全部保护再加pin。查映射、保留frame驻留性、协调替换器状态之间存在竞态窗口；另一个线程可能在你取得页latch前驱逐它。你要说明**从哪一刻起此frame不能被改装**，以及之后怎样安全等待页访问权。

反过来，读盘完成前就让另一个调用者取得“有效guard”，也可能读到Reset后的零字节或部分旧数据。若缩小BPM全局锁覆盖范围，必须补足对装载中状态和同页重复miss的协调；不能只把一把锁删掉来提高QPS。

### 5.2 锁边界表

以下是需要明确的保护职责，不规定唯一实现：

| 资源 | 应明确的保护与边界 |
|---|---|
| page table、free list、驻留转换 | BPM latch或等价协议；映射读取和frame使用不能脱节 |
| pin与evictable联合变化 | 单独atomic计数不够；最后一次unpin和新pin必须相互协调 |
| 页字节 | frame读写latch；读guard共享、写guard独占；I/O也会访问字节 |
| ARC列表、索引、目标、Size | ARC内部latch；禁止出现反向调用导致循环等待 |
| 请求队列 | Channel内部锁；不要持它执行长时间I/O |
| dirty及flush进度 | 明确同步责任；共享读锁允许多个读guard并存，因此不能假定它排他保护所有元数据写入 |

普通`bool is_dirty_`不是原子字段。尤其两个读guard都Flush、或guard访问器同时观察dirty时，你需要让读取与改变遵循兼容同步协议；仅说“大家都有共享页锁”不足以证明写元数据无竞争。

### 5.3 必须手画的死锁反例

线程A已经持有页X的写guard；线程B尝试访问X，等待其页latch。此时A还要请求页Y。如果B等X时握住BPM总锁，A取Y又要总锁，就形成等待环。

公开`DeadlockTest`直接覆盖这种结构。解决方向是划清“管理状态受保护的阶段”和“可能阻塞等待页latch的阶段”，同时确保等待期间目标frame不能被驱逐。不能只释放总锁而不保留frame；那会把死锁换成串页。

同理，Drop若在持页latch时等待BPM总锁，而另一路在持总锁时等待该页latch，也会成环。先为所有取锁路径画等待图，再考虑缩小粒度；不要声称“整个函数都加一把大锁一定安全”。网页已对这一点给出必须提前释放避免死锁的例外。

### 5.4 I/O与frame复用

需要替换dirty页时，应能够解释：旧page id在何时不再对外可见、旧数据写请求何时完成、何时能覆盖frame字节、何时目标页可被访问。只把写请求放入队列就Reset同一frame，会使worker读取已改变的数据。

Clean受害页不必为了形式完整而强制写盘；dirty页也不能只清flag不写数据。不要把驱逐时的写回和DeletePage的删除语义混为一谈。

## 6. Guard移动、Drop与dirty的审计表

### 6.1 移动是资源责任转移，不是再次取页

| 情形 | 应在私有测试观察的事情 |
|---|---|
| 有效源移动构造目标 | 页仍只被原有那份访问权保留；源析构不再unpin |
| 有效目标被另一个有效源移动覆盖 | 目标原页得到释放，源原页仍有一份保留；二者page id不同更容易暴露错误 |
| 自移动 | 对象不应丢失自己持有的访问权，pin数不应改变 |
| 无效源覆盖有效目标 | 目标原资源得到释放，之后两者均可安全析构 |
| 默认对象／已Drop对象再次Drop | 无动作，不触碰未初始化page id或空frame指针 |
| vector搬移／erase | 不能因容器搬移多pin或漏解锁 |

移动涉及page id、frame、replacer、BPM latch、scheduler和validity的完整关系；只移动frame指针不够。复制构造／赋值已删除，不要为让容器编译而恢复复制。

### 6.2 Drop的核心证明

为有效guard写一份资源清单：持有何种页锁、承担哪一个pin、关联哪些管理对象。Drop之后清单应为空，下一次Drop仍为空；最后一次pin释放必须使替换状态正确，而其他guard存在时不能设为evictable。

**pin先变0就直接让别人复用frame**与**仍持旧页latch才做后续访问**不能随意混用。请说明哪把锁把这一段转换遮住，哪个时刻之后旧guard彻底不再接触页字节。这里不给可直接粘贴的解锁顺序，因为顺序必须与你的BPM锁协议一起证明。

### 6.3 Flush不终结写guard

写guard可能先取得mutable指针，Flush，然后继续通过同一指针修改。裸指针写入不会自动再次调用`GetDataMut()`。因此不能仅以“一次拿指针时设dirty、Flush后永远clean”作为证明。

检查你的dirty策略是否满足：

- 真正修改的数据最终不会以clean状态被丢弃；
- 读guard本身不被误当作用户修改页的证据；
- Flush完成只覆盖它安全写出的内容；guard仍可继续工作；
- 从guard Flush不递归取得已经持有的页锁；
- Unsafe flush遵守“不取页latch”的接口要求，但调用者和管理层仍须维持合法访问／缓冲生命周期；Unsafe不是无限制并发读写字节的许可证。

允许你在私有设计中选择保守标脏策略，但要说明何时标记、何时可清除，以及并发观察是否安全。不要把一个测试没检查dirty就当它可省略。

## 7. 按可观察行为组织实现与自测

建议学习顺序：ARC纸面轨迹与接口 → scheduler生命周期 → BPM最小访问与GetPinCount → 两类guard及移动 → 替换／删除／flush → 并发 → 可选优化。它是编者学习路线，不是官方强制提交顺序；BPM和guard须协同完成，不能假设其中一个尚未实现时另一个就能完整运行。

| 要求 | 公开入口 | 仍应补充的私有思考 |
|---|---|---|
| ARC状态转换 | `arc_replacer_test.cpp`的2个SampleTest | 比例调整、全部pinned、重复设置、Remove、并发与性能 |
| 异步请求 | `disk_scheduler_test.cpp`的ScheduleWriteReadPageTest | 空／多元素批次、缓冲与shutdown边界、同页顺序 |
| pin与移动 | `page_guard_test.cpp`的DropTest／MoveTest | dirty／Flush、读共享与写排他、重复移动链 |
| 满池与回读 | BPM的VeryBasic、PagePinEasy、PagePinMedium | 单frame、clean与dirty受害者、失败不破坏原映射 |
| 删除 | VeryBasic仅有基础成功删除 | pinned拒绝、不驻留／不存在删除、磁盘释放调用；内存backend的Delete是no-op，不能据其行为省掉正式调用 |
| 并发 | PageAccess、Contention、Deadlock、Evictable | 同页并发miss、最后unpin与新pin竞争、不同页I/O进展 |
| Flush家族 | 固定源码契约，公开文件未单独完整覆盖 | 驻留／不驻留、clean／dirty、持guard再Flush、Flush后再写、遍历中管理状态 |
| 基准正确性 | `tools/bpm_bench/bpm_bench.cpp` | 改容量与线程数仍正确；不能仅优化一组参数 |

所有公开用例名在固定版本都带`DISABLED_`。**零测试执行不是通过。** 在私有工作区完成对应功能后，按课程要求启用本项目用例并检查实际执行数量；不要启用尚未实施的未来项目来制造噪声，也不要删除失败断言。

## 8. 只供完成实现后的操作路线

以下命令是给学习者在**独立私有BusTub工作区**使用的示例，本轮没有执行，不是本仓库构建步骤。先通过Project0确认依赖／编译器；固定C++17和Clang15建议、FAQ C++20差异及Ubuntu24.04评分边界见要求页。

```sh
# 私有工作区根目录；对应功能已实现且用例已启用后
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target arc_replacer_test disk_scheduler_test page_guard_test buffer_pool_manager_test -j 4
./build/test/arc_replacer_test
./build/test/disk_scheduler_test
./build/test/page_guard_test
./build/test/buffer_pool_manager_test
```

`-j 4`只是并行度示例，不是课程评分参数。遇到挂起先看线程栈和持锁关系；遇到数据不一致先跟踪page id／frame id／pin／dirty／request完成顺序。不要先加sleep来碰运气。

完成后再按官方要求检查`format`、`check-lint`、`check-clang-tidy-p1`，以及Debug的ASAN／LSAN；macOS不能代替Linux的LSAN检查。官方允许因调试器交互临时关闭sanitizer，但交付前必须恢复所需验证，不能把关闭检查当修复内存错误。变更编译器／sanitizer时使用独立构建目录，避免把旧缓存误当新配置；不必破坏学生源码。

可选排行榜使用RelWithDebInfo构建`bpm-bench`，网页演示执行`bustub-bpm-bench --duration 5000 --latency 1`。它不是完整评分参数，也不是本轮已测性能。先保留正确性checkpoint，再考虑预取和并行I/O。

### 提交归档对应的八个文件

固定CMake的`P1_FILES`为：

```text
src/include/buffer/arc_replacer.h
src/buffer/arc_replacer.cpp
src/include/buffer/buffer_pool_manager.h
src/buffer/buffer_pool_manager.cpp
src/include/storage/disk/disk_scheduler.h
src/storage/disk/disk_scheduler.cpp
src/include/storage/page/page_guard.h
src/storage/page/page_guard.cpp
```

`cmake --build build --target submit-p1`对应官方`make submit-p1`目标，在项目根目录生成`project1-submission.zip`。若把必需实现放进未归档的新文件，不能假设评分环境会收到它。提交前自行查看归档与实际实现是否一致，保留私有版本和检查记录，不公开归档。

Gradescope认证／提交未在本轮核验。隐藏测试比公开测试复杂，公开12项通过不等于保证满分；排行榜优化也不能代替正确性、无内存错误和风格要求。

## 9. 本版本特别容易读错的地方

- `DiskScheduler`构造仍有阻断启动的`UNIMPLEMENTED`，不是完全做好了的黑箱。
- 两类guard的默认构造已提供；待实现的是私有有参构造和移动／Flush／Drop。
- `FrameHeader`注释讨论传统4KB分段，实际常量和题面均为8192字节。
- BPM头文件说先完成DiskManager，但官方Task2实际让你实现的是DiskScheduler；DiskManager已提供，只需理解依赖。
- `DiskManager::DeletePage`的历史注释称no-op，但固定文件backend实际回收slot；memory backend才明确no-op。保持通过scheduler调用DeallocatePage的BPM要求。
- 基准里的`lru-k-size`名称与测试中的LRU旧注释不改变ARC变体；`AccessType`默认参数不可从声明删掉。
- ARC独立测试的frame标识约定与BPM数组索引不完全相同，不能用新加的越界断言把原测试判错。

## 来源与完成边界

[官方题面](https://15445.courses.cs.cmu.edu/fall2025/project1/)、[固定仓库](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41)的具体阅读清单见[要求页来源节](#/c/cmu-15-445-2025/lab/project1?v=zh)。本页锁边界、生命周期账本和新增测试方向是基于这些契约的原创指导，不是参考实现。没有浏览学生答案仓库、修改学生代码、执行构建／测试／格式化或向Gradescope提交；学习者完成状态为 **not_attempted**。
