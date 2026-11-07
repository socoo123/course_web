---
source: MIT 6.S081 Fall 2020 · Lab Multithreading 官方实验页
license: CC BY 3.0 US；MIT 课程团队署名及原页链接见页底
status: 官方任务、提示、问题、样例、验收与选做完整中译；共同提交流程链接公共资料；未取得 thread 分支及评分器，未运行实验
---

# 多线程

本实验帮助你熟悉多线程：为用户级线程库实现线程切换，使用多个线程加速程序，并实现一个屏障（barrier）。

## 准备

开始编写代码前，确保读过 xv6 教材第 7 章「调度」，并研究对应代码。

> **编者阅读导航：**第 7 章至 §7.4 的中文译文在[第 11 讲课程资料](#/c/mit-6.s081-2020/lec/lec11?v=materials)，§7.5–7.10 在[第 13 讲课程资料](#/c/mit-6.s081-2020/lec/lec13?v=materials)。环境和实验仓库见[公共资料](#/c/mit-6.s081-2020)。

切换到 `thread` 分支，开始本实验：

```bash
$ git fetch
$ git checkout thread
$ make clean
```

## Uthread：在线程之间切换（中等）

本题要求你设计并实现用户级线程系统的上下文切换机制。起始代码提供了 `user/uthread.c`、`user/uthread_switch.S`，以及 Makefile 中用于构建 `uthread` 程序的规则。`uthread.c` 已包含用户级线程库的大部分代码和三个简单测试线程，但缺少创建线程和切换线程的一部分代码。

**任务：**设计创建线程、保存和恢复寄存器以切换线程的方案，然后实现它。完成后，`make grade` 应报告你的程序通过了 `uthread` 测试。

在 xv6 中运行 `uthread`，应看到如下输出；三个线程开始执行的顺序可能不同：

```text
$ make qemu
...
$ uthread
thread_a started
thread_b started
thread_c started
thread_c 0
thread_a 0
thread_b 0
thread_c 1
thread_a 1
thread_b 1
...
thread_c 99
thread_a 99
thread_b 99
thread_c: exit after 100
thread_a: exit after 100
thread_b: exit after 100
thread_schedule: no runnable threads
$
```

这段输出来自三个测试线程：每个线程在循环中打印一行，然后把 CPU 让给其他线程。此时若还没有实现上下文切换代码，则不会看到输出。

你需要补充以下位置：

- `user/uthread.c` 中的 `thread_create()` 和 `thread_schedule()`。
- `user/uthread_switch.S` 中的 `thread_switch`。

第一个目标是：`thread_schedule()` 首次运行某个线程时，该线程应在**自己的栈上**执行传给 `thread_create()` 的函数。第二个目标是：`thread_switch` 保存被切走线程的寄存器，恢复目标线程的寄存器，并回到目标线程上次停止的位置继续执行。

你需要决定把寄存器保存在哪里、从哪里恢复。修改 `struct thread`，让它容纳寄存器，是一种好方案。还需要在 `thread_schedule` 中加入对 `thread_switch` 的调用；可以给它传递你需要的参数，意图是从线程 `t` 切换到 `next_thread`。

### 提示与 GDB 调试

- `thread_switch` 只需要保存、恢复 callee-save 寄存器。为什么？
- `user/uthread.asm` 中可以看到 uthread 的汇编代码，调试时可能有用。
- 使用 `riscv64-linux-gnu-gdb` 单步执行 `thread_switch`，有助于测试代码。可以从下面的命令开始：

```text
(gdb) file user/_uthread
Reading symbols from user/_uthread...
(gdb) b uthread.c:60
```

这会在 `uthread.c` 第 60 行设置断点。断点可能在你运行 `uthread` 之前就触发，也可能不会。为什么会这样？

xv6 shell 启动后，输入 `uthread`，GDB 会在第 60 行停下。此时可以检查 uthread 的状态：

```text
(gdb) p/x *next_thread
```

用 `x` 命令查看某个内存位置的内容：

```text
(gdb) x/x next_thread->stack
```

跳到 `thread_switch` 开头：

```text
(gdb) b thread_switch
(gdb) c
```

逐条执行汇编指令：

```text
(gdb) si
```

GDB 在线文档见页底。

## 使用线程（中等）

本题通过哈希表探索利用线程和锁进行并行编程。请在具有多个处理器核心的真实 Linux 或 macOS 计算机上完成，**不在 xv6 中，也不在 QEMU 中运行**。多数较新的笔记本都有多核处理器。

本题使用 UNIX `pthread` 线程库。可以运行 `man pthreads` 查阅手册，也可以查阅页底列出的互斥锁、初始化和线程创建文档。

`notxv6/ph.c` 包含一个简单哈希表：单线程使用时正确，多线程使用时不正确。在 xv6 仓库主目录，例如 `~/xv6-labs-2020`，运行：

```bash
$ make ph
$ ./ph 1
```

Makefile 使用**宿主操作系统的 gcc** 构建 `ph`，而不是 6.S081 的交叉编译工具。`ph` 的参数指定有多少线程对哈希表执行 put 和 get。运行一段时间后，`ph 1` 会产生类似输出：

```text
100000 puts, 3.991 seconds, 25056 puts/second
0: 0 keys missing
100000 gets, 3.981 seconds, 25118 gets/second
```

根据计算机速度、是否有多个核心、是否正在执行其他任务，实际数字可能与样例相差两倍甚至更多。

`ph` 运行两个基准测试。先调用 `put()` 向哈希表添加许多键，输出每秒插入次数；再通过 `get()` 查找这些键，输出本应已插入却没有找到的键的数量——本例为零——以及每秒查找次数。

传入大于 1 的参数，可以让多个线程同时使用哈希表。试试 `ph 2`：

```text
$ ./ph 2
100000 puts, 1.885 seconds, 53044 puts/second
1: 16579 keys missing
0: 16579 keys missing
200000 gets, 4.322 seconds, 46274 gets/second
```

第一行表示两个线程并发插入时，总插入速率达到每秒 53,044 次，约为单线程 `ph 1` 的两倍。这是约 2 倍的优秀并行加速，达到了这里所期待的理想效果：核心数量翻倍，单位时间完成的工作也翻倍。

但两行 `16579 keys missing` 表明大量本该存在的键丢失了；put 本应插入它们，却出了问题。阅读 `notxv6/ph.c`，尤其是 `put()` 和 `insert()`。

### 需要提交的问题

为什么两个线程会丢失键，而一个线程不会？找出一种两个线程的事件交错次序，使某个键最终丢失。把这个次序以及简短解释写入 **`answers-thread.txt`**。

### 先保证正确

为避免这种事件交错，在 `notxv6/ph.c` 的 `put` 和 `get` 中插入加锁、解锁语句，使两个线程运行时丢失键的数量始终为 0。相关 pthread 调用如下：

```c
pthread_mutex_t lock;            // 声明锁
pthread_mutex_init(&lock, NULL); // 初始化锁
pthread_mutex_lock(&lock);       // 获取锁
pthread_mutex_unlock(&lock);     // 释放锁
```

当 `make grade` 报告通过 `ph_safe` 测试时，这一步完成；它要求两个线程运行时没有丢失的键。此时未通过 `ph_fast` 是允许的。

不要忘记调用 `pthread_mutex_init()`。先用 1 个线程测试，再用 2 个线程测试。程序是否正确，即是否消除了键丢失？双线程是否比单线程实现了并行加速，即单位时间完成更多总工作？

### 再实现并行加速

有些并发 `put()` 对哈希表所读写的内存没有重叠，因此彼此之间不需要用同一把锁互斥。能否修改 `ph.c`，利用这些情况让一部分 `put()` 并行执行？提示：为每个哈希桶安排一把锁怎么样？

**任务：**在保持正确性的同时，让部分 put 操作并行执行。`make grade` 同时通过 `ph_safe` 和 `ph_fast` 才算完成。`ph_fast` 要求双线程的每秒 put 次数至少为单线程的 **1.25 倍**。

## 屏障 Barrier（中等）

屏障是程序中的一个同步点：所有参与线程都必须等到其他参与线程也到达该点，才能继续。你将使用 pthread 条件变量，这是一种与 xv6 的 sleep/wakeup 类似的执行顺序协调机制。

本题也在真实计算机上完成，**不在 xv6 或 QEMU 中运行**。

`notxv6/barrier.c` 提供了一个有缺陷的屏障：

```text
$ make barrier
$ ./barrier 2
barrier: notxv6/barrier.c:42: thread: Assertion `i == t' failed.
```

参数 2 指定参与屏障同步的线程数，也就是 `barrier.c` 中的 `nthread`。每个线程执行一个循环：每轮调用 `barrier()`，然后睡眠随机数量的微秒。断言失败，是因为一个线程在另一个线程到达屏障之前就离开了。期望行为是：每个线程都阻塞在 `barrier()` 中，直到全部参与线程都已调用它。

**任务：**实现上述屏障行为。除了 ph 题中使用的锁原语，还需要以下 pthread 原语；文档见页底：

```c
pthread_cond_wait(&cond, &mutex);  // 在 cond 上睡眠：释放 mutex，醒来返回前重新获取它
pthread_cond_broadcast(&cond);     // 唤醒所有正在 cond 上睡眠的线程
```

确保通过 `make grade` 中的 `barrier` 测试。特别注意，`pthread_cond_wait` 在调用时释放 mutex，在返回前重新获取它。

起始代码已经提供 `barrier_init()`。你的任务是实现 `barrier()`，消除上述失败。已定义的 `struct barrier` 及其字段可供使用。

有两个使任务变复杂的问题：

1. 屏障会被连续调用；每一次同步称为一轮（round）。`bstate.round` 记录当前轮次。每当所有线程都到达屏障，就应递增它。
2. 一个线程可能在其他线程尚未退出屏障时，就快速跑完循环并再次进入。尤其要注意，`bstate.nthread` 会在相邻轮次之间复用。必须确保前一轮还在使用它时，快速进入下一轮的线程不会把它递增。

分别用 1 个、2 个以及多于 2 个线程测试代码。

## 验收与提交

完成全部实验后，确保通过所有 `make grade` 测试。本实验明确要求提交的问答文件是 **`answers-thread.txt`**；将它和代码修改一起纳入 Git。

随后执行[公共资料中的「实验的共同验收与提交步骤」](#/c/mit-6.s081-2020)：填写整数小时数的 `time.txt`、跟踪新增文件并提交修改、按 2020 课程流程使用 `make handin`。该节也包括 API key、`myapi.key` 不含换行符的要求、未跟踪文件检查、curl/Git 排错、`make tarball` 网页上传及提交状态查询。

> **编者核对：**本页官方提交段与公共资料所依据的 2020 pgtbl 页面没有实质流程差异。原文的 `answers-lab-name.txt` 是模板，本实验前文已明确为 `answers-thread.txt`；原文终端记录中的 `[util c2e3c8b]` 是沿用的示例输出，不改变本实验应使用 `thread` 分支的要求。

## Uthread 选做挑战

用户级线程库与操作系统之间存在几种不良交互。例如，一个用户级线程在系统调用中阻塞时，另一个用户级线程也无法运行，因为用户级调度器不知道它的某个线程已被 xv6 调度器停止调度。

另一个例子是：两个用户级线程不会在不同核心上同时运行，因为 xv6 调度器不知道还存在多个可以并行执行的线程。而且，即使让它们真正并行运行，当前实现也会因多种竞态出错：例如不同处理器上的两个线程同时调用 `thread_schedule`，可能选中同一个 runnable 线程，并在两个处理器上同时运行它。

有几种解决办法。一种使用 **scheduler activations（调度器激活）**；另一种像 Linux 内核那样，为每个用户级线程配备一个内核线程。在 xv6 中实现其中一种方案。正确实现并不容易，例如，为多线程用户进程更新页表时，需要实现 **TLB shootdown**。

为你的线程库添加锁、条件变量、屏障等功能。

## 来源、许可与核对范围

- MIT 6.S081 课程团队，[Lab: Multithreading（Fall 2020）](https://pdos.csail.mit.edu/6.S081/2020/labs/thread.html)。本页为中文翻译；仅明确标记的编者导航和校注为新增内容。按课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名，修改包括翻译、排版及共用提交段的链接归并。
- 已逐项读取共享 HTML 与文本，抓取时间为 2026-11-06，核对时间为 2026-11-07；出处及行号映射见本实验 `sources/manifest.json`、`sources/coverage.json`。
- 官方链接的 [GDB 手册](https://sourceware.org/gdb/current/onlinedocs/gdb/)、[pthread_mutex_lock](https://pubs.opengroup.org/onlinepubs/007908799/xsh/pthread_mutex_lock.html)、[pthread_mutex_init](https://pubs.opengroup.org/onlinepubs/007908799/xsh/pthread_mutex_init.html)、[pthread_create](https://pubs.opengroup.org/onlinepubs/007908799/xsh/pthread_create.html)、[pthread_cond_wait](https://pubs.opengroup.org/onlinepubs/007908799/xsh/pthread_cond_wait.html)、[pthread_cond_broadcast](https://pubs.opengroup.org/onlinepubs/007908799/xsh/pthread_cond_broadcast.html) 保留为查阅入口，未在本次获取或全文核验。
- 官方扩展链接：[Barrier](https://en.wikipedia.org/wiki/Barrier_(computer_science))、[Scheduler activations](https://en.wikipedia.org/wiki/Scheduler_activations)，未另行读取；HTTP 链接改为 HTTPS。
- 未取得 `thread` 实验分支、专用起始文件及评分器；测试名、命令、阈值和样例均取自官方页面，不代表已经执行或验证通过。未运行 xv6、QEMU、GDB、pthread 程序或 `make grade`。
