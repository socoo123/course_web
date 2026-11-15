---
source: CMU 15-445/645 Fall 2025 Project1全页；固定BusTub接口、骨架、依赖及4个公开测试文件全文，来源见页底
version: v20251119-2025fall；d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 网页未核实全文翻译发布授权；本文是完整任务覆盖的原创要求导读，非授权全译。固定BusTub代码MIT许可不外推题面。
status: 仅静态阅读；未运行骨架、构建或测试；learnerLabCompletion not_attempted
---

# Project 1：Buffer Pool Manager 要求导读

本项目把逻辑上的磁盘页放进有限的内存帧，让上层通过page guard安全访问，而不必知道一次请求命中了缓存还是需要I/O。它是官方 **Project 1**，不是本站制作批次P1；本次内容制作属于P2。

导航：[无答案实现指导](#/c/cmu-15-445-2025/lab/project1?v=guide) · [Project 0共同先修](#/c/cmu-15-445-2025/lab/project0?v=guide) · [L4内存管理](#/c/cmu-15-445-2025/lec/lec04?v=notes) · [HW2](#/c/cmu-15-445-2025/lab/hw02?v=zh)。

## 1. 冻结版本，不拿旧模板替换新接口

| 项目 | 本页采用的事实 |
|---|---|
| 学期／教师 | Fall 2025，Andy Pavlo，个人独立完成 |
| 原发布／截止 | 2025-09-08／2025-09-28 23:59，历史修课日期 |
| 网页更新时间 | 2025-09-22；网页与代码标签不是同日快照 |
| 代码 | `v20251119-2025fall` @ `d49b823f829a4bf311a2c80b239ab5a9864c9c41` |
| 页大小 | `BUSTUB_PAGE_SIZE = 8192`字节；不是从旧说明复制的4KB |
| 实现范围 | ARC变体、DiskScheduler、BufferPoolManager、ReadPageGuard、WritePageGuard，均须线程安全 |
| 不在范围 | 不实现LRU-K／LRU／Clock；不重写DiskManager；忽略本项目的LogManager；不提前实现后续项目 |

沿用[Project 0](#/c/cmu-15-445-2025/lab/project0?v=guide)的私有仓库、C++所有权／移动语义、调试和工具链准备，不在本站公开学生实现。历史网页的“更新最新代码”不等于今天直接合并`master`；需要补丁时另记SHA。

可以增加辅助成员和方法，但不能改预定义API签名或移除BPM所依赖的scheduler／replacer。ARC头文件中的辅助结构与列表表示可按其注释调整。允许标准C++17容器，不允许另加Boost等第三方库；标准容器不会自动变成线程安全。

## 2. 五个不同概念，不能用一个标志替代

| 概念 | 含义 | 不等于什么 |
|---|---|---|
| page／`page_id_t` | 逻辑数据页，可能在磁盘、内存或两处 | 不是数组下标frame id |
| frame／`frame_id_t` | 可反复装载不同page的一块固定内存 | `shared_ptr<FrameHeader>`存活不代表其中仍是原page |
| pin count | 当前访问者对驻留性的保留；大于0时不能驱逐 | 不提供页内容的互斥访问 |
| dirty | 内存修改尚未被对应的安全写回覆盖 | 不表示正在被访问，也不表示必须马上写回 |
| latch／evictable | latch保护并发访问；evictable表示替换器可否选它 | 解锁不自动unpin；unpin不自动刷盘；atomic pin不自动同步替换器 |

page table保持驻留page到frame的一对一映射。页被驱逐后，ghost只能记page身份，不能继续声称它拥有旧frame。`FrameHeader`的`rwlatch_`保护读写访问；`bpm_latch_`保护共享管理状态；ARC另有自己的latch。具体保护范围必须由你的实现写清楚。

## 3. Task 1：本学期的ARC变体

### 3.1 四条列表与五种“大小”

记容量为 $c$，MRU目标为 $p$：

- `MRU`（下文T1）：近期只访问过一次的驻留页。
- `MFU`（T2）：近期被重复访问的驻留页；这里不是一个按累计访问次数排序的通用LFU堆。
- MRU ghost（B1）、MFU ghost（B2）：已驱逐页的身份历史，不含可用frame和页数据。
- 列表前端表示新近使用；驱逐从所选侧的旧端寻找可驱逐项，跳过pinned项。

不能混淆容量`replacer_size_`、四列表总项数、`curr_size_`、目标`mru_target_size_`和T1实际长度。初始四表为空、目标为0；四表总数最多为 $2c$。`Size()`只数驻留且evictable的frame，**不是**T1+T2，更不是四表之和。

### 3.2 `RecordAccess`的四种互斥情况

这里完整列出指定变体的状态要求，而不是可提交实现。每次要记录的是已pin住的`(frame_id,page_id)`。

| 命中位置 | 必须产生的状态变化 |
|---|---|
| T1或T2 | 移到T2的新端；命中不制造第二份页记录 |
| B1 | 用命中前的ghost长度调整目标：B1不短于B2则增加1，否则增加向下取整的`|B2|/|B1|`；上限为c。移出ghost，绑定本次frame，进入T2新端 |
| B2 | B2不短于B1则目标减少1，否则减少向下取整的`|B1|/|B2|`；下限为0。移出ghost，绑定本次frame，进入T2新端 |
| 四表均未命中 | 若`|T1|+|B1|=c`，删除B1旧端，再把新页放T1新端；否则该和应小于c，此时若四表总数恰为2c，删B2旧端后加入T1，否则直接加入T1 |

ghost命中时分母所在列表必非空。最后一行的ghost裁剪有其调用顺序和容量不变量前提；应解释为什么裁剪时会有可删ghost，而不是随意删除一个驻留页。`RecordAccess`不执行`Evict`的替换步骤；固定源码明确将两者拆开。

### 3.3 驱逐、删除与可驱逐状态

- `Evict() -> optional<frame_id_t>`：若T1实际长度 **小于** p，优先T2；否则（包括相等）优先T1。所选侧没有evictable项就尝试另一侧，两侧都没有则`nullopt`。成功时返回frame、减少evictable计数，并把page身份放入对应ghost。
- **本变体与原论文不同**：T1长度等于目标时，不根据最后一次访问类别再作选择；pinned项要跳过，必要时跨侧尝试。不要把论文的完整流程不加修改地搬过来。
- `SetEvictable(frame_id,bool)`：仅状态真正改变时增减计数；重复设置同一状态不能重复计数。固定注释要求无效frame id抛异常或终止；其余不适用情形不改变状态。
- `Remove(frame_id)`：用于删除页面，不是按ARC选择受害者。不存在则返回；对存在但不可驱逐的frame，固定注释要求异常或终止；成功移除时维护计数和相关记录，不制造一次“驱逐命中历史”。
- `Size()`也需在线程安全的状态下读取。`RecordAccess`含可选`AccessType`参数，主要用于排行榜优化；网页的简写签名没有列出这个默认参数。

公开ARC测试用的是抽象frame标识，其中有`ArcReplacer(3)`配合frame ids 1、2、3；不要仅凭BPM的0起始数组下标给独立ARC测试添加冲突断言。头文件没有给出统一的“invalid”数值规则，需把容量、已登记身份、调用契约分开审视，不篡改公开测试或API。

## 4. Task 2：DiskScheduler与请求所有权

固定接口是：`void Schedule(std::vector<DiskRequest> &requests)`。**不是**旧学期的单个`DiskRequest`参数，也不是值传递vector。

| 对象／方法 | 契约 |
|---|---|
| `DiskRequest::is_write_` | 决定调用DiskManager的WritePage还是ReadPage |
| `data_` | 指向整页缓冲；写请求从此读，读请求向此写；裸指针不拥有内存 |
| `page_id_` | 本次I/O的逻辑page身份，不能由frame id代替 |
| `callback_` | `std::promise<bool>`；请求处理完成后置true，让对应future可等待 |
| `Schedule(vector&)` | 接收批次，将每个请求及其move-only promise交给异步处理；批次不是只处理第一项 |
| `StartWorkerThread()` | 从队列取得请求、分派I/O并完成回调；不能因暂时队列为空就退出 |
| 析构 | 骨架将`nullopt`放入队列并join后台线程；线程遇到关闭信号必须能退出 |

原网页说构造和析构已经实现，但固定`disk_scheduler.cpp`构造函数在启动线程前仍有`UNIMPLEMENTED`。完成本任务必须处理该占位并保留正确启动／关闭行为，不能只填两个空方法后以为能启动。

`Channel`是移动入队、阻塞取出的FIFO；锁仅保护队列，不保护`data_`指向的页。生产者必须保证缓冲直到I/O完成都存活，并满足读／写方向对应的访问排他要求。**移动请求或promise不会移动、复制或延长页缓冲的生命周期。**

每个被接受的正常请求恰好完成一次promise：不能提前报告完成、漏掉回调、重复`set_value`或把关闭哨兵当真实请求处理。固定DiskManager的读写返回`void`，没有统一的错误码协议；不要声称这里提供了生产级掉电持久性或全部错误传播保证。有关故障处理的额外设计不能改题目签名。

关闭依赖调用者先停止提交、让已接受请求排在结束标记前，并保证DiskManager活到worker退出；析构与外部线程继续调用同一已销毁对象不构成合法用法。优化为多个worker时，单个哨兵不自动关闭全部线程，同页请求仍须保持等价顺序和read-after-write一致性。

## 5. Task 3：BufferPoolManager全部接口

`FrameHeader`的构造、数据指针、Reset已提供；Reset清零缓冲、pin和dirty。BPM也提供初始frames、free list、page table预留空间、replacer和scheduler。任务不要求你解析tuple字节。

| 接口 | 结果／失败语义 | 必须考虑的状态 |
|---|---|---|
| `NewPage()` | 返回单调增加、线程安全分配的page id | 逻辑分配不等于马上占用frame；DiskManager按访问延迟分配磁盘空间 |
| `DeletePage(page_id)` | pinned则不修改并返回false；不存在或删除成功返回true | 驻留映射、替换记录、free frame及`DeallocatePage`；不能只删map |
| `CheckedReadPage(page_id,AccessType)` | 返回共享读取guard；无法让目标驻留时返回nullopt | 命中、空闲frame、替换三条路径；页内容读完前不能交付有效guard |
| `CheckedWritePage(page_id,AccessType)` | 返回独占读写guard；无可用frame返回nullopt | 同上；dirty受害页须安全写回后才能复用其内存 |
| `FlushPageUnsafe(page_id)` | 不驻留返回false，否则true；按修改状态写回 | **不得取得页latch**；管理元数据的同步与页latch是不同问题 |
| `FlushPage(page_id)` | 不驻留返回false，否则true；安全写回 | 需页latch保护一致内容，完成后dirty状态不能覆盖后来修改 |
| `FlushAllPagesUnsafe()` | 处理当前内存中的页；不取页latch | 页集合遍历、frame驻留性、dirty更新与I/O生命周期 |
| `FlushAllPages()` | 处理当前内存中的页并安全取页latch | 不等于遍历所有磁盘page id，也不是承诺跨页事务快照 |
| `GetPinCount(page_id)` | 不驻留为nullopt；驻留为实际pin计数，包括0 | 取BPM latch保护映射，再atomic load；不要为计数取得页读写latch |

已提供的`ReadPage`／`WritePage`是Checked版本的便利包装，失败会终止进程，不是可恢复的内存不足API。BPM的`Size()`返回frame容量，和ARC的`Size()`含义不同。

同一page最多有一份驻留数据；已有用户访问时不能把该frame改装成另一页。所有可用frame都pinned时，Checked接口要失败，不能悄悄驱逐、返回无效guard或把任务改成无界等待。

## 6. ReadPageGuard与WritePageGuard全部任务

两类guard都不可复制，可移动。读guard持共享访问，写guard持独占访问；两者共同承担pin和释放责任。

| 接口类别 | 需要完成／保留的行为 |
|---|---|
| 默认构造 | 固定头文件已`= default`，`is_valid_=false`；只为稍后移动赋值提供空对象，不可访问页数据 |
| 有参私有构造 | 只有BPM可调用；建立有效guard及其资源关系，这是固定cpp中的待实现构造 |
| 移动构造 | 转移page身份、frame／replacer／BPM latch／scheduler关联和资源责任；源对象失效，不新增pin、不重复加页锁 |
| 移动赋值 | 先正确处置目标原来资源，再接收源；必须考虑自移动、无效源、无效目标，保持`noexcept`及返回目标引用 |
| `Flush()` | 在guard仍保护该页的条件下安全写回；不要重复取得自己已经持有的非递归页锁 |
| `Drop()` | 有效时准确释放资源，协调pin与evictable；无效时无动作，多次调用幂等 |
| 析构 | 固定实现调用Drop；搬移后的源、默认对象也须可安全析构 |
| 访问器 | `GetPageId`、`GetData`、`IsDirty`及`As<T>`只在有效guard上使用；写guard另有`GetDataMut`／`AsMut<T>` |

网页列表把“无参构造”放进任务，而固定代码真正有占位的是私有有参构造；按代码核对，不重写已提供默认构造来掩盖错误。固定`GetDataMut()`目前只是返回指针，不替学生完成dirty协议；须结合写guard生命周期处理，尤其是Flush后继续通过已有指针修改的情形。

Drop不应被理解为“无条件刷盘后销毁页面”。它释放本次访问权，dirty页可以留在缓存中，之后由flush或eviction持久化；不能漏掉最后一次unpin，也不能仍有人pin时把frame设成evictable。

## 7. 公开测试、优化与评分边界

完整静态阅读了以下 **4个文件、12个测试**，均带`DISABLED_`前缀：

| 固定路径 | 用例与覆盖 |
|---|---|
| `test/buffer/arc_replacer_test.cpp` | `SampleTest`、`SampleTest2`：命中／ghost命中、目标调整、容量裁剪、跳过pinned、frame复用与驱逐顺序 |
| `test/storage/disk_scheduler_test.cpp` | `ScheduleWriteReadPageTest`：vector请求、promise/future、同页先写后读、数据比较、scheduler先析构后关闭DiskManager |
| `test/storage/page_guard_test.cpp` | `DropTest`、`MoveTest`：重复Drop、作用域释放、dirty页再读取、pin计数、自移动、移动覆盖、无效源、释放后重新加锁 |
| `test/buffer/buffer_pool_manager_test.cpp` | `VeryBasicTest`、`PagePinEasyTest`、`PagePinMediumTest`、`PageAccessTest`、`ContentionTest`、`DeadlockTest`、`EvictableTest`：读写删除、满池失败、驱逐回读、页读写互斥、竞争、跨页取锁、pin与evictable一致 |

这些是教学证据，不是完整规格。固定公开文件未把每种flush、删除失败、并发加载、批次长度和ARC性能边界都列成断言；应据接口自行补充私有测试。测试中的旧`LRU`注释不能改变本期ARC要求。

排行榜**优化可选，正确结束不可选**：实现仍须能正确完成基准、无死锁／段错误。网页描述8个scan线程、8个按Zipf分布get／update线程，三轮各30秒（不同设置，无模拟延迟／带模拟延迟）；延迟模型随机I/O约1ms、顺序／局部I/O约0.1ms。网页示例5000ms参数不是评分参数。权重为两组无延迟scan/get QPS各除1000，再加延迟组scan/get QPS。

已读`tools/bpm_bench/bpm_bench.cpp`和内存DiskManager依赖：基准检查页身份及内容一致性，不只是计时。其`--lru-k-size`残留参数只被解析和打印，没有传入当前BPM构造，不能据此恢复LRU-K。可选方向包括利用AccessType、预取、并行I/O；同页操作顺序和正确性不能为QPS让步。优化前保留私有正确性checkpoint；不能识别评分环境硬编码行为、靠`NDEBUG`切换答案，排行榜有人工复核且不能用late days。

## 8. 环境、提交与开发规则

- 固定CMake强制 **C++17**，推荐 **Clang15**；FAQ Q5写 **C++20**，保留差异，不为了统一文案修改固定源码。AppleClang被构建文件识别，但不等于课程推荐编译器完全一致。
- 官方README推荐Ubuntu24.04，macOS M1／M2／Intel仅作开发；评分环境是Ubuntu24.04，不支持WSL。本包制作环境Apple Silicon／Darwin arm64不代表已准备或验证评分环境。
- 未实现骨架含`UNIMPLEMENTED`，本轮**没有构建或运行**。实施后的工具／测试路线见指导页，不以运行空骨架制造“通过率”。
- 官方检查包括Google C++风格、格式／lint／clang-tidy-p1、ASAN／LSAN；macOS缺少与Linux相同的LSAN验证。风格不合格会影响乃至失去该项目成绩，不能只看功能测试。
- Debug的`BUSTUB_ASSERT`在Release可能不执行表达式；不要把必要状态变化写在断言里。要始终检查的条件对应`BUSTUB_ENSURE`。降低日志噪声，避免提交时因大量日志影响评分。
- 完成后官方`make submit-p1`生成`project1-submission.zip`；具体归档文件与私有测试路线见指导页。Gradescope网页存在不代表我们已登录、加入或评分；公开测试不承诺隐藏分数。
- 项目迟交规则见[大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html)：全学期编程项目有4个日历late days，向上取整计天；其他迟交扣分等按原规则，排行榜不得使用late days。不要把HW2与Project1迟交规则混用。
- 个人实现，只讨论高层概念，不搜索／复制学生解答，不公开实现或把工作白板内容照搬为答案。

## 来源、许可与真实完成状态

- [官方Project1全页](https://15445.courses.cs.cmu.edu/fall2025/project1/)：Overview至Collaboration Policy全文已读，包括排行榜、开发提示、测试／评分／提交，读取日2026-11-15。其完整翻译许可未知，本文为原创要求导读。
- [固定BusTub源码根目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41)：全文读`src/include/buffer/`下的`arc_replacer.h`、`buffer_pool_manager.h`及对应cpp；`src/include/storage/`下的`disk/disk_scheduler.h`、`page/page_guard.h`及对应cpp；上述4个测试文件；`common/channel.h`、`common/config.h`、DiskManager与memory backend头／cpp、`tools/bpm_bench/bpm_bench.cpp`。CMake只读版本／编译器与P1提交清单等相关区段，未称全文审查整个仓库。
- [固定MIT LICENSE](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/LICENSE)：全文核实，版权属CMU Database Group；许可限仓库软件与随附文档，不覆盖独立课程PDF／网页，更不是允许公开学生答案。
- [固定README](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/README.md)、[FAQ](https://15445.courses.cs.cmu.edu/fall2025/faq.html)、[大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html)：全文读取以核对环境与学术规范。

本包只完成文档制作与静态来源阅读；未运行学生骨架、未核验视频音画、未测试Gradescope，学习者状态始终为 **not_attempted**。固定源码中仍有历史注释／占位差异，本页已显式保留，不承诺隐藏测试结果。
