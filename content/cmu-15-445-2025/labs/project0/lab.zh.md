---
source: CMU 15-445/645 Fall 2025 Project 0；固定 BusTub 头文件、骨架、公开测试及构建文件，来源见页底
version: v20251119-2025fall；d49b823f829a4bf311a2c80b239ab5a9864c9c41
license: 原网页未发现完整翻译发布授权；本页是原创要求导读，不是授权全译。BusTub MIT 许可不外推课程网页。
status: 可达要求已覆盖；仅静态阅读；学习者实验 not_attempted；未构建、运行测试或向 Gradescope 提交
---

# Project 0：Count–Min Sketch 要求导读

这是官方 **Project 0 — C++ Primer**，不是制作批次 P0，也不是 Buffer Pool 的 Project 1。目标是用一个小型近似计数器检查 C++ 的资源管理、模板和并发基础。它不是完整 SQL 引擎，也不要求提前实现数据库后续项目。

导航：[无答案指导与哈希／概率先修](#/c/cmu-15-445-2025/lab/project0?v=guide) · [HW1 SQL](#/c/cmu-15-445-2025/lab/hw01?v=zh) · [公共资料](#/c/cmu-15-445-2025)。

## 1. 先冻结版本与交付边界

| 项目 | 本页采用的事实 |
|---|---|
| 课程 | Andy Pavlo，Fall 2025，个人独立完成 |
| 官方发布日期／截止 | 2025-08-25／2025-09-07 23:59；历史修课安排，不是本站新截止时间 |
| 课程门槛 | 官方要求本项目满分才能继续；它不是通常计入课程项目成绩的普通项目；不允许 late days |
| 代码 | 标签 `v20251119-2025fall`，完整提交 `d49b823f829a4bf311a2c80b239ab5a9864c9c41` |
| 实现与提交文件 | `src/include/primer/count_min_sketch.h`、`src/primer/count_min_sketch.cpp` |
| 实际制作环境 | Apple Silicon / Darwin arm64；本轮没有配置或验证学生实验环境 |
| 学习者完成 | **not_attempted**；导读完成不表示实现、测试或评分完成 |

在独立的**私有**工作区学习；不要把项目实现放进本课程内容仓库或公开 fork。历史网页要求跟进 `public/master`，但当前 master 不是这份 2025 项目的替身：先固定上述提交，任何后续补丁另记 SHA，不盲目合并新版本。

官方网页说在头文件完成函数；固定仓库的声明在 `.h`、方法骨架在 `.cpp`，提交目标也包含两者。应以这套固定文件一起阅读，而不是从别年项目复制接口。

## 2. 数据结构究竟回答什么

设矩阵有 `depth` 行、`width` 列，每行用自己的种子选择一个桶。插入一个键，每行对应的计数各增加一次；查询同一个键时，取各行对应桶计数的最小值。碰撞会把别的键的贡献混入桶，因此查询一般是**估计值**，不是精确字典。

无删除、无溢出、插入正确完成后，估计不应小于真实出现次数；未插入的键也可能得到正数。宽度为 1 时所有键挤在同一列，连不存在的键也会读到累计流长度。公式、原创小例子与适用假设集中在[指导页](#/c/cmu-15-445-2025/lab/project0?v=guide)，这里不重复展开先修。

## 3. 八项接口核对表

所有条目都在范围内，不能只实现 `Insert` 与 `Count` 就宣布完成。

| 接口 | 必须保住的语义 | 边界／常见误读 |
|---|---|---|
| `CountMinSketch(uint32_t width, uint32_t depth)` | 建立指定尺寸、初始计数全零的 sketch；生成每行散列函数 | 任一维为 0 抛 `std::invalid_argument`；宽／深为 1 合法 |
| 移动构造 `CountMinSketch(CountMinSketch &&) noexcept` | 接收源对象的资源与逻辑计数；目标可继续查询、插入 | 不是复制；散列闭包捕获 `this`，不能只看矩阵搬过去没有 |
| 移动赋值 `operator=(CountMinSketch &&) noexcept` | 用源对象状态替换已有目标状态，返回目标引用 | 原目标资源须正确释放；旧计数不能残留；不要改掉 `noexcept` |
| `void Insert(const KeyType &)` | 每行对这个键对应的桶增加一次 | **唯一明确要求线程安全的操作**；多线程可对同一个或多个 sketch 同时插入 |
| `uint32_t Count(const KeyType &) const` | 返回各行对应计数的最小值，不修改对象 | 结果可能高估；不能要求所有未出现键永远为 0 |
| `void Clear()` | 回到可复用的空计数状态 | 不是破坏尺寸或让对象失去散列能力；若有辅助状态也须一致 |
| `void Merge(const CountMinSketch &other)` | **原地更新当前对象**，逐对应桶合并；`other` 保持不变 | 尺寸不兼容抛 `std::invalid_argument`；网页“创建新 sketch”的措辞与固定接口不符 |
| `TopK(uint16_t k, const vector<KeyType> &candidates)` | 从**调用者给定候选**中取估计计数最大的至多 k 项，返回 `(item, count)` 向量，按计数降序 | 不是自动枚举整个输入流的键，也不是保证真实频率前 k 名 |

默认构造、复制构造和复制赋值在头文件中已删除。固定 `.cpp` 显式实例化 `std::string`、`int64_t` 和 `int`。新增辅助结构可以，但不要改受保护的 `SEED_BASE=15445`、散列生成器和构造函数末尾生成每行散列函数的区块；不要换外部库或自行设计一套散列来迎合测试。

### 不把残留注释当新增任务

头文件的 `Insert` 注释提及更新 min-heap，`Clear` 注释提及 item set／heap，`TopK` 注释写着 “capped at initial k”。但构造函数没有初始 k 参数，公共接口明确由 `candidates` 提供键。本项目不因此要求存储整个键集合或在每次插入时维护全局排名。按实际接口、题面与测试理解契约，不扩成另一种数据结构。

题面没有给出通用的并列计数顺序、重复候选去重规则、计数溢出策略或移动后源对象可执行全部操作的保证。指导页把它们作为设计／边界讨论，**不捏造为官方评分断言**。移动后仍须满足安全析构等 C++ 基本资源要求。

## 4. 并发要求到底到哪里

允许许多线程同时调用 `Insert`；正确性不能靠所有实例共享同一份计数或全局工作状态。官方**没有**要求 `Clear`、`Merge`、移动、`TopK` 或 `Count` 与插入同时执行时仍有一致快照语义。已读公开并发测试先 `join`，再查询、清空、合并；不要把未要求的并发快照难题加给学习者。

一个覆盖整个数据结构的大锁可帮助你在私有工作区建立正确性基线，但不是最终性能目标。网页建议缩小锁粒度或考虑原子操作，明确不期望只用单个全局 latch。公开性能测试输出还警告：未实现 lock-free 版本、超时或段错误可能被人工扣除并发测试分。因此不能从“网页允许讨论细粒度锁”推断任何加锁方案都保证获满分；保留此措辞差异，以官方评分澄清为准。

## 5. 环境与构建：区分建议和已运行

- 固定 `CMakeLists.txt` 强制 **C++17**，推荐 **Clang 15**；FAQ Q5 则写 **C++20**。保留差异，本页不为迎合 FAQ 修改固定构建标准。
- 固定 README 推荐 Ubuntu 24.04，macOS M1/M2/Intel 只作开发环境，评分环境为 Ubuntu 24.04；不支持 WSL。平台 mutex 行为可能影响结果。
- `build_support/packages.sh` 会安装／更新系统包，macOS 分支使用 Homebrew；应先审读，不在内容仓库盲跑。脚本注释列 macOS 13，不能据此宣称当前 Darwin 25 已受验证。
- Debug 默认 AddressSanitizer；网页说明 macOS 没有该流程中的 LeakSanitizer 支持。Linux 上的泄漏检查仍需独立完成，Apple Silicon 编译成功也不能替代它。
- 不要在仓库根目录原地运行 CMake。遇到工具链问题，先看编译器、架构、依赖路径与 CMake 输出，不改学生算法迁就平台。

以下仅为学习者完成实现后的操作入口，**本轮均未执行**。从固定 BusTub 仓库根目录配置独立目录：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target count_min_sketch_test
./build/test/count_min_sketch_test
```

评分说明使用 Release；另建 `build_rel` 配置，不把 Debug 耗时当 Release 性能。网页的 `make -j$(nproc)` 是环境相关写法，macOS 是否有 `nproc` 取决于工具安装；上面的构建入口不依赖它。

`BUSTUB_ASSERT` 在 Release 下不会执行表达式，不能在断言中做必需的状态更新；`BUSTUB_ENSURE` 在固定宏中检查失败会终止进程，不等于业务异常处理。

## 6. 公开测试的静态覆盖地图

本轮顺序读完 `test/primer/count_min_sketch_test.cpp` 的 **791 行、13 个 TEST**，没有运行未实现骨架。

| 测试名 | 实际覆盖 |
|---|---|
| `BasicTest1`、`BasicTest2` | 字符串、正负整数、重复插入、已选不碰撞例子的精确计数 |
| `EdgeTest1`、`EdgeTest2` | 零维异常；宽 1、深 1、两者均为 1；未出现键因碰撞而非零 |
| `MoveTest` | 普通和碰撞状态的移动构造、覆盖已有目标的移动赋值、移动后目标继续插入 |
| `ClearTest` | 清空后多个键的查询归零 |
| `MergeTest` | 原地合并、源对象不变、宽 1 的合并 |
| `ParallelTest` | 同一 sketch 多线程插入，等待完成后 TopK 检查 |
| `ComplexParallelTest` | 多 sketch 插入、等待、分别查询／清空，再合并 |
| `TopKBasicTest`、`TopKDynamicTest` | 候选排名；多轮**累计**插入后的排名变化 |
| `TopKComprehensiveTest` | 四个 sketch、多组线程、两级合并后候选排名与计数 |
| `ContentionRatioTest` | 两线程各插入 10,000 次，十轮交替外部串行锁与不加外部锁；最后检查计数和速度比 |

性能断言是 `speedup > 1.2`，即串行化耗时总和／未外部串行化耗时总和。代码变量名虽含 `time_ms`，实际计时单位为**微秒**。该测试受核数、调度、编译模式及宿主负载影响；**本机未跑，没有性能通过结论**。不要删断言、改变负载或降低阈值冒充解决竞争。

Project 0 网页明确说**没有隐藏测试**；不能把大纲针对后续项目的通用说明倒套为本项目隐藏测试承诺。反过来，本地公开测试也不验证当前 Gradescope 服务可用、账户资格或人工评判结果。未覆盖的自测思路见指导页。

## 7. 提交之前，交付物不只是“算对了”

1. 在自己的私有工作区完成两个指定文件，保持固定接口与受保护代码；不公开答案、不查阅学生答案仓库。
2. 运行该版本的功能测试，检查是否人为留下 `DISABLED_` 前缀。当前已读 13 个测试没有此前缀；这不是替你运行过测试。
3. 遵守 Google C++ 风格。网页列 `make format`、`make check-clang-tidy-p0`，并提及 `check-lint`；格式／静态检查失败可能导致零分。`format` 会修改代码，先明确范围。
4. 检查内存安全、泄漏及 Release 行为，不把 sanitizer 关闭后“没有报告”当修复。调试器受 sanitizer 干扰时可以单独建立禁用 sanitizer 的调试配置，最终仍应恢复检查。
5. 从构建目录运行 `make submit-p0`。固定 CMake 的工作目录是**源码根目录**，生成的 `project0-submission.zip` 也在那里，内容只含上述两个文件；不要因网页说“在 build 运行”就误找 ZIP 位置。
6. 官方提交入口为 Gradescope 课程 `1074751`；CMU 学生使用 Piazza 公布的代码，校外入口见 FAQ Q7。固定 README 另要求提交前运行 `python3 gradescope_sign.py` 签署协议；本轮未执行脚本、未登录、未验证可加入或评分。

允许多次提交不意味着 Gradescope 是唯一调试工具；截止前可能排队。技术问题按当学期政策发 Piazza，不直接邮件找 TA，Project 0 TA 不代看／调试代码。官方允许高层讨论、禁止抄代码／白板内容；Project 0 页面允许生成式 AI 辅助，但责任仍属学习者，大纲的引用和独立完成要求仍适用。本材料不给完整实现。

## 来源与阅读范围

核对日期：**2026-11-15**。下列网页／代码为事实依据，不表示其文字可整份翻译发布。

- [Fall 2025 Project 0](https://15445.courses.cs.cmu.edu/fall2025/project0/)：缓存正文全文阅读，含任务、环境、评分、提交和合作政策；全文及页尾未找到网页开放翻译许可。
- [固定 BusTub 目录](https://github.com/cmu-db/bustub/tree/d49b823f829a4bf311a2c80b239ab5a9864c9c41)：完整读头文件、骨架、公开测试、README、LICENSE、安装脚本；CMake 阅读至 Project 0 提交目标，不声称全仓读完。代码适用仓库 MIT 许可。
- [固定公开测试](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/test/primer/count_min_sketch_test.cpp)、[固定 HashUtil](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/common/util/hash_util.h)、[固定宏](https://github.com/cmu-db/bustub/blob/d49b823f829a4bf311a2c80b239ab5a9864c9c41/src/include/common/macros.h)：均已静态阅读。
- [FAQ](https://15445.courses.cs.cmu.edu/fall2025/faq.html)与[大纲](https://15445.courses.cs.cmu.edu/fall2025/syllabus.html)：全文阅读，核对语言版本、校外入口、独立完成及迟交规则。没有找到把视频许可扩到作业网页的授权条款。
