---
source: MIT 6.S081 Fall 2020 · Lab locks · https://pdos.csail.mit.edu/6.S081/2020/labs/lock.html
license: MIT 课程网站 CC BY 3.0 US；中文翻译，通用提交段链接公共资料
status: 官方两项任务、全部提示、四组测试输出与选做已核对；未取得 lock 分支专用测试及评分器，未运行实验
---

# 实验 8 · 锁与并行

本实验练习通过重新设计代码来提高并行度。多核机器上，并行度不足的一个常见表现是锁争用严重。要提高并行度，往往需要同时改变数据结构与加锁策略，减少争用。你将对 xv6 的内存分配器和磁盘块缓存进行这样的改造。

## 开始之前

编写代码前，务必阅读 xv6 教材的以下部分及相关代码：

- 第 6 章 **Locking（锁）**。
- §3.5 **Code: Physical memory allocator（代码：物理内存分配器）**。
- §8.1–8.3 **Overview / Buffer cache layer / Code: Buffer cache（概览 / 缓冲区缓存层 / 代码：缓冲区缓存）**。

在实验仓库中执行：

```sh
$ git fetch
$ git checkout lock
$ make clean
```

> **编者阅读指引：** 教材与实验环境见[公共资料](#/c/mit-6.s081-2020)。第 6 章中文译文在[第 10 讲课程资料](#/c/mit-6.s081-2020/lec/lec10?v=materials)，§3.5 在[第 4 讲课程资料](#/c/mit-6.s081-2020/lec/lec04?v=materials)。§8.1–8.3 先读公共资料链接的 rev1 原书。本实验的机制分析与调试思路见[实验指导](#/c/mit-6.s081-2020/lab/lock?v=guide)。

## 内存分配器（Memory allocator，难度 moderate）

程序 `user/kalloctest` 对 xv6 的内存分配器施加压力：三个进程反复扩大和缩小自己的地址空间，从而大量调用 `kalloc` 与 `kfree`。这两个函数都会取得 `kmem.lock`。

对于 `kmem` 和其他几把锁，`kalloctest` 会输出：为了获取已被另一核持有的锁，`acquire` 的循环尝试了多少次。输出中的名字是 `#fetch-and-add`。这些循环迭代次数是锁争用程度的粗略度量。完成实验之前，输出类似：

```text
$ kalloctest
start test1
test1 results:
--- lock kmem/bcache stats
lock: kmem: #fetch-and-add 83375 #acquire() 433015
lock: bcache: #fetch-and-add 0 #acquire() 1260
--- top 5 contended locks:
lock: kmem: #fetch-and-add 83375 #acquire() 433015
lock: proc: #fetch-and-add 23737 #acquire() 130718
lock: virtio_disk: #fetch-and-add 11159 #acquire() 114
lock: proc: #fetch-and-add 5937 #acquire() 130786
lock: proc: #fetch-and-add 4080 #acquire() 130786
tot= 83375
test1 FAIL
```

`acquire` 为每把锁维护两项计数：调用 `acquire` 的次数，以及循环尝试设置锁却失败的次数。`kalloctest` 调用一个系统调用，让内核打印 `kmem`、`bcache`（本实验关注的锁）以及争用最严重的五把锁的计数。存在锁争用时，`acquire` 的循环次数会很大。这个系统调用返回 `kmem` 与 `bcache` 锁的失败循环次数之和。

本实验必须使用一台**有多个核、没有其他负载、专供此次测试使用的机器**。如果机器还在做其他事情，`kalloctest` 打印的计数就没有意义。可以使用专用 Athena 工作站或自己的笔记本，但不要使用共享的 dialup 登录机器。

争用的根源是 `kalloc()` 只有一条空闲链表，并由一把锁保护。为消除争用，需要重新设计分配器，不再使用这一条全局链表和一把全局锁。基本办法是：**每个 CPU 一条空闲链表，每条链表一把锁**。不同 CPU 的分配和释放操作处理不同链表，因此可以并行执行。

主要挑战在于：本核链表已经为空，但其他核还有空闲内存。这时，本核必须从另一核的空闲链表中“偷取”一部分页。偷取可能引入锁争用，但希望它发生得不频繁。

### 必做任务

实现每 CPU 的空闲链表，并在本核链表为空时从其他核偷取空闲页。

必须为这里的所有锁使用以 **`kmem`** 开头的名字：逐一调用 `initlock`，传入以 `kmem` 开头的名称。

运行 `kalloctest`，查看实现是否减少了锁争用；运行 `usertests sbrkmuch`，检查分配器是否仍能分配全部可用内存。输出应类似下面的例子：所有 `kmem` 锁的总争用显著下降，但具体数字可以不同。还要确保 `usertests` 中的全部测试通过；`make grade` 应报告 kalloctests 通过。

```text
$ kalloctest
start test1
test1 results:
--- lock kmem/bcache stats
lock: kmem: #fetch-and-add 0 #acquire() 42843
lock: kmem: #fetch-and-add 0 #acquire() 198674
lock: kmem: #fetch-and-add 0 #acquire() 191534
lock: bcache: #fetch-and-add 0 #acquire() 1242
--- top 5 contended locks:
lock: proc: #fetch-and-add 43861 #acquire() 117281
lock: virtio_disk: #fetch-and-add 5347 #acquire() 114
lock: proc: #fetch-and-add 4856 #acquire() 117312
lock: proc: #fetch-and-add 4168 #acquire() 117316
lock: proc: #fetch-and-add 2797 #acquire() 117266
tot= 0
test1 OK
start test2
total free number of pages: 32499 (out of 32768)
.....
test2 OK
$ usertests sbrkmuch
usertests starting
test sbrkmuch: OK
ALL TESTS PASSED
$ usertests
...
ALL TESTS PASSED
$
```

### 官方提示

1. 可以使用 `kernel/param.h` 中的常量 `NCPU`。
2. 让 `freerange` 把所有空闲内存交给执行 `freerange` 的那个 CPU。
3. `cpuid` 返回当前核的编号，但**只有在中断关闭时，调用它并使用返回值才安全**。使用 `push_off()` 与 `pop_off()` 关闭、恢复中断。
4. 可以查看 `kernel/sprintf.c` 的 `snprintf`，了解字符串格式化方法。不过，把所有锁都直接命名为 `"kmem"` 也可以。

## 缓冲区缓存（Buffer cache，难度 hard）

这一半实验与前一半相互独立。无论是否完成内存分配器，都可以进行本部分并通过其测试。

多个进程密集使用文件系统时，很可能争用 `bcache.lock`。这把锁保护 `kernel/bio.c` 中的磁盘块缓存。`bcachetest` 创建多个进程，反复读取不同文件，以制造对 `bcache.lock` 的争用。修改前的输出类似：

```text
$ bcachetest
start test0
test0 results:
--- lock kmem/bcache stats
lock: kmem: #fetch-and-add 0 #acquire() 33035
lock: bcache: #fetch-and-add 16142 #acquire() 65978
--- top 5 contended locks:
lock: virtio_disk: #fetch-and-add 162870 #acquire() 1188
lock: proc: #fetch-and-add 51936 #acquire() 73732
lock: bcache: #fetch-and-add 16142 #acquire() 65978
lock: uart: #fetch-and-add 7505 #acquire() 117
lock: proc: #fetch-and-add 6937 #acquire() 73420
tot= 16142
test0: FAIL
start test1
test1 OK
```

你的数字可能不同，但 `bcache` 锁对应的 `acquire` 失败循环次数会很高。查看 `kernel/bio.c` 会发现，`bcache.lock` 保护缓存缓冲区链表、每个缓冲区的引用计数 `b->refcnt`，以及缓存块的身份 `b->dev` 和 `b->blockno`。

### 必做任务

修改块缓存，使运行 `bcachetest` 时，块缓存中所有锁的 `acquire` 失败循环次数接近零。理想情况下总和为零；**总和小于 500 也可以**。

修改 `bget` 与 `brelse`，使对缓存中不同磁盘块的并发查找、释放不容易发生锁冲突，例如不再全部等待 `bcache.lock`。必须维持不变量：**每个磁盘块至多有一个缓存副本**。

完成后的输出应类似下面的例子，不要求逐字相同。确保 `usertests` 仍然通过，最后 `make grade` 应通过全部测试。

```text
$ bcachetest
start test0
test0 results:
--- lock kmem/bcache stats
lock: kmem: #fetch-and-add 0 #acquire() 32954
lock: kmem: #fetch-and-add 0 #acquire() 75
lock: kmem: #fetch-and-add 0 #acquire() 73
lock: bcache: #fetch-and-add 0 #acquire() 85
lock: bcache.bucket: #fetch-and-add 0 #acquire() 4159
lock: bcache.bucket: #fetch-and-add 0 #acquire() 2118
lock: bcache.bucket: #fetch-and-add 0 #acquire() 4274
lock: bcache.bucket: #fetch-and-add 0 #acquire() 4326
lock: bcache.bucket: #fetch-and-add 0 #acquire() 6334
lock: bcache.bucket: #fetch-and-add 0 #acquire() 6321
lock: bcache.bucket: #fetch-and-add 0 #acquire() 6704
lock: bcache.bucket: #fetch-and-add 0 #acquire() 6696
lock: bcache.bucket: #fetch-and-add 0 #acquire() 7757
lock: bcache.bucket: #fetch-and-add 0 #acquire() 6199
lock: bcache.bucket: #fetch-and-add 0 #acquire() 4136
lock: bcache.bucket: #fetch-and-add 0 #acquire() 4136
lock: bcache.bucket: #fetch-and-add 0 #acquire() 2123
--- top 5 contended locks:
lock: virtio_disk: #fetch-and-add 158235 #acquire() 1193
lock: proc: #fetch-and-add 117563 #acquire() 3708493
lock: proc: #fetch-and-add 65921 #acquire() 3710254
lock: proc: #fetch-and-add 44090 #acquire() 3708607
lock: proc: #fetch-and-add 43252 #acquire() 3708521
tot= 128
test0: OK
start test1
test1 OK
$ usertests
  ...
ALL TESTS PASSED
$
```

> **编者校注：** 上例忠实保留官方数字。列出的 `kmem/bcache` 行均为 0，末尾却写 `tot= 128`；该展示本身不能据此还原总数计算细节，也不要把 128 当成必须得到的结果。原页明确要求的是相关争用总数小于 500。

请为这里的所有锁使用以 **`bcache`** 开头的名字：逐一调用 `initlock`，传入以 `bcache` 开头的名称。

块缓存比 `kalloc` 更难减少争用，因为缓存缓冲区确实由不同进程、不同 CPU 共享。内存分配器可以通过每核独立的分配器消除大部分争用；块缓存不能照搬这一办法。建议用哈希表查找块号，**每个哈希桶一把锁**。

### 允许出现锁冲突的情况

以下情形存在锁冲突是可以接受的：

1. 两个进程同时使用同一块号。`bcachetest` 的 `test0` 不会这样做。
2. 两个进程同时缓存未命中，都需要寻找一个未使用的缓冲区来替换。`test0` 不会这样做。
3. 两个进程使用的块在你的分区和锁方案中发生冲突，例如块号散列到同一哈希槽。根据设计不同，`test0` 可能发生这种情况；应调整方案细节来尽量避免，例如改变哈希表大小。

`bcachetest` 的 `test1` 使用的不同磁盘块数量超过缓冲区数量，并覆盖文件系统的许多代码路径。

### 官方提示

1. 阅读 xv6 教材 §8.1–8.3 中关于块缓存的说明。
2. 可以使用固定桶数，无须动态调整哈希表大小。使用质数个桶，例如 **13**，可以降低哈希冲突的可能性。
3. 在哈希表中查找一个缓冲区，以及未找到时为它分配缓存条目，这两步必须构成**原子操作**。
4. 去掉所有缓冲区组成的全局链表（`bcache.head` 等），改为用最后使用时间为缓冲区打时间戳，可以使用 `kernel/trap.c` 中的 `ticks`。这样 `brelse` 不必再取得全局 `bcache` 锁，`bget` 可以根据时间戳选择最近最少使用的块。
5. 可以串行化 `bget` 中的淘汰部分，即缓存查找未命中后，选择一个缓冲区重新使用的部分。
6. 某些情况下可能需要同时持有两把锁，例如淘汰时同时持有 `bcache` 锁与某个桶锁。务必避免死锁。
7. 替换块时，新块可能散列到不同桶，因此需要把 `struct buf` 从旧桶移到新桶。一个棘手情况是新旧块恰好散列到同一个桶；这种情况也必须避免死锁。
8. 调试时可以先实现桶锁，同时保留 `bget` 开头、结尾的全局 `bcache.lock` 获取和释放，使这段代码串行执行。确认串行化后的实现正确，再去掉全局锁，处理并发问题。也可以用 `make CPUS=1 qemu` 在单核下测试。

## 完成、验收与提交

完成两项任务后，确保全部 `make grade` 测试通过。

通用的答案文件模板、`time.txt`、Git 跟踪与提交、`make handin`、API key、`myapi.key`、未跟踪文件警告、`make tarball` 和提交状态查询，统一见[公共资料「实验的共同验收与提交步骤」](#/c/mit-6.s081-2020)。本实验原页的共同提交要求与该节一致。

> **编者核对：** 原页写的是条件式模板：“如果本实验有问题，将答案写入 `answers-lab-name.txt`。”本页没有另列必答问题或指定专用答案文件，不应把模板擅自变成必交的 `answers-lock.txt`。共同提交示例中的 `[util c2e3c8b]` 是原页沿用的示例输出；本实验实际分支仍是 `lock`。

## 选做挑战

让块缓存中的查找成为 **lock-free（无锁）** 操作。提示：使用 GCC 的 `__sync_*` 函数。你如何说服自己，证明实现是正确的？

## 来源、许可与核验范围

- **L-lock**：MIT 6.S081 课程团队，[Lab: locks（2020）](https://pdos.csail.mit.edu/6.S081/2020/labs/lock.html)。本文为官方要求的完整中文翻译；共同提交段按站点约定转至公共资料，明确标出的编者指引与校注不属于原文。原页四组实验输出完整保留，未把示例输出冒充实际运行记录。
- 课程网站按 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 使用并署名；翻译、排版及站内指引为本站修改。
- 共享 HTML 于 2026-11-06 抓取，2026-11-07 全文核对；文件 SHA-256 与抓取元数据见 `sources/manifest.json`，逐项覆盖见 `sources/coverage.json`。历史 URL 的抓取件不等于证明自 2020 年以来从未改动。
- 未取得 2020 `lock` 分支的 `kalloctest`、`bcachetest`、专用评分器及 `kernel/sprintf.c`；其名称与行为以本次已读官方页为依据，未逐行核对专用实现。未运行 xv6、QEMU、GDB、实验测试或提交命令。
