---
source: MIT 6.S081 Fall 2020 Lab traps 官方实验页
license: 课程网站 CC BY 3.0 US；中文翻译，编者说明单独标出
status: 已覆盖原页全部任务、问题、提示、实验输出与选做；通用提交段转公共资料；未运行实验
---

# Lab traps · 陷阱

本实验探索如何利用陷阱（trap）实现系统调用。你将先完成与栈有关的热身练习，再实现一个用户级陷阱处理的例子。

## 开始前

动手编码前，阅读 xv6 教材第 4 章，以及相关源文件：

- `kernel/trampoline.S`：负责从用户空间切换到内核空间、再切回去的汇编代码。
- `kernel/trap.c`：处理中断的代码。

教材与工具链入口见[公共资料](#/c/mit-6.s081-2020)。第 4 章译文分布在 [LEC 6 课程资料](#/c/mit-6.s081-2020/lec/lec06?v=materials)（除 §4.6）与 [LEC 8 课程资料](#/c/mit-6.s081-2020/lec/lec08?v=materials)（§4.6）。

切换到本实验的 `traps` 分支：

```sh
$ git fetch
$ git checkout traps
$ make clean
```

> 编者说明：以下文件名和命令针对 `xv6-labs-2020` 的 `traps` 分支。本站用于阅读的固定 2020 上游源码快照不是该实验分支，其中没有 `user/call.c`、`user/bttest.c`、`user/alarmtest.c`，也没有本实验评分脚本。

## RISC-V 汇编（简单）

理解一些 RISC-V 汇编十分重要；原课程假定你已在 6.004 接触过它。实验仓库里有 `user/call.c`，运行 `make fs.img` 会编译它，并生成便于阅读的汇编文件 `user/call.asm`。

阅读 `call.asm` 中的 `g`、`f` 和 `main`。RISC-V 指令手册入口列在页底的官方资料中。回答下面全部问题，把答案保存到 **`answers-traps.txt`**：

1. 函数参数存在哪些寄存器中？例如，`main` 调用 `printf` 时，哪个寄存器保存了 `13`？
2. 在 `main` 的汇编代码中，对函数 `f` 的调用在哪里？对 `g` 的调用又在哪里？提示：编译器可能会内联函数。
3. 函数 `printf` 位于什么地址？
4. 在 `main` 中执行跳向 `printf` 的 `jalr` 后，寄存器 `ra` 的值是什么？
5. 运行下面的代码。输出是什么？页底提供原页所链的 ASCII 表，可用它查字节对应的字符。

   ```c
   unsigned int i = 0x00646c72;
   printf("H%x Wo%s", 57616, &i);
   ```

   输出依赖于 RISC-V 采用小端序这一事实。如果 RISC-V 改为大端序，应把 `i` 设成什么值才能得到相同输出？需要把 `57616` 换成另一个值吗？原页还提供了大小端说明及一篇趣味说明，链接保留在页底。
6. 下面这段代码中，`y=` 后面会打印什么？注意：答案不是某个具体数值。为什么会这样？

   ```c
   printf("x=%d y=%d", 3);
   ```

## Backtrace：栈回溯（中等）

调试时，回溯往往很有帮助：它列出发生错误的位置上方、栈中各层函数调用。

在 `kernel/printf.c` 中实现 **`backtrace()`**。在 `sys_sleep` 中加入对它的调用，然后运行会调用 `sys_sleep` 的 **`bttest`**。输出应类似：

```text
backtrace:
0x0000000080002cda
0x0000000080002bb6
0x0000000080002898
```

运行 `bttest` 后退出 QEMU。在宿主机终端运行 `addr2line -e kernel/kernel`，或者 `riscv64-unknown-elf-addr2line -e kernel/kernel`，把输出的地址复制进去，例如：

```text
$ addr2line -e kernel/kernel
0x0000000080002de2
0x0000000080002f4a
0x0000000080002bfc
Ctrl-D
```

应该看到类似结果：

```text
kernel/sysproc.c:74
kernel/syscall.c:224
kernel/trap.c:85
```

> 编者说明：原页的两组示例地址本来就不相同，这里保留原样。实际地址可能略有差异；使用你自己的输出与同次构建的 `kernel/kernel`，不要要求与示例地址或行号完全一致。

编译器在栈帧中保存调用者的帧指针。`backtrace` 应沿这些保存的帧指针向上遍历，并打印每个栈帧保存的返回地址。

### 提示

1. 在 `kernel/defs.h` 中添加 `backtrace` 的函数声明，以便从 `sys_sleep` 调用。
2. GCC 将当前执行函数的帧指针放在寄存器 `s0` 中。在 `kernel/riscv.h` 中加入下面的函数，再在 `backtrace` 中调用它读取当前帧指针。这里用内联汇编读取 `s0`：

   ```c
   static inline uint64
   r_fp()
   {
     uint64 x;
     asm volatile("mv %0, s0" : "=r" (x) );
     return x;
   }
   ```

3. 原页所链的课堂 slides 给出了栈帧布局图。注意：返回地址位于帧指针的固定偏移 **`-8`** 处，保存的上一帧帧指针位于固定偏移 **`-16`** 处。相关讲解见 [LEC 5 笔记 §4](#/c/mit-6.s081-2020/lec/lec05?v=notes)。
4. xv6 为每个内核栈分配一页，起始地址按页对齐。可以利用 `PGROUNDDOWN(fp)` 和 `PGROUNDUP(fp)` 计算栈页的下、上边界，帮助终止回溯循环；宏定义在 `kernel/riscv.h` 中。

> 编者说明：上述固定偏移针对本实验采用的、保留帧指针和标准帧记录的 RV64 布局，不是任意函数或手写汇编都具有的结构。页边界的使用细节见实验指导。

回溯正常工作后，还要在 `kernel/printf.c` 的 **`panic`** 中调用它，让内核 panic 时也能打印回溯。

## Alarm：用户态定时回调（困难）

本练习给 xv6 添加一种功能：进程使用 CPU 时间时，定期通知它。它可以帮助计算密集型进程限制 CPU 消耗，也能让持续计算的进程周期性地执行一些动作。更一般地说，你将实现一种原始的用户级中断／故障处理机制；类似方式也能用于让应用程序自行处理缺页等事件。实现应通过 **`alarmtest` 和 `usertests`**。

### 接口与预期行为

新增系统调用 **`sigalarm(interval, handler)`**。应用调用 `sigalarm(n, fn)` 后，每消耗 `n` 个 tick 的 CPU 时间，内核就应使应用执行函数 `fn`。处理函数完成后，应用应从先前中断的位置继续。tick 是 xv6 中由硬件定时器中断频率决定的时间单位，并不对应一个固定的通用时间长度。

调用 **`sigalarm(0, 0)`** 应使内核停止产生周期性 alarm 调用。处理函数完成时如何回到被中断代码，由下文要求的 `sigreturn` 协议实现。

实验仓库提供 `user/alarmtest.c`。把它加入 `Makefile`；在添加 `sigalarm` 和 `sigreturn` 系统调用之前，它还不能正确编译。

`alarmtest` 的 `test0` 调用 `sigalarm(2, periodic)`，要求内核每 2 个 tick 强制执行一次 `periodic()`，随后忙循环一段时间。调试时可查看 `user/alarmtest.asm`。正确实现应产生类似下面的输出，并使 `usertests` 正常运行：

```text
$ alarmtest
test0 start
........alarm!
test0 passed
test1 start
...alarm!
..alarm!
...alarm!
..alarm!
...alarm!
..alarm!
...alarm!
..alarm!
...alarm!
..alarm!
test1 passed
test2 start
................alarm!
test2 passed
$ usertests
...
ALL TESTS PASSED
$
```

最终实现只需不多的代码，但做对可能颇费心思。课程会用**原始仓库版本的 `alarmtest.c`** 测试你的代码。你可以修改它辅助调试，但最终必须确保原版 `alarmtest` 报告所有测试通过。

### test0：调用处理函数

先修改内核，使它能跳到用户空间的 alarm 处理函数，让 `test0` 打印 `alarm!`。这一步暂时不必处理打印之后的情况；现阶段打印后崩溃也可以。

提示如下：

1. 修改 `Makefile`，把 `alarmtest.c` 编译成 xv6 用户程序。
2. 在 `user/user.h` 中添加以下声明：

   ```c
   int sigalarm(int ticks, void (*handler)());
   int sigreturn(void);
   ```

3. 更新 `user/usys.pl`（它会生成 `user/usys.S`）、`kernel/syscall.h` 和 `kernel/syscall.c`，使 `alarmtest` 能调用 `sigalarm`、`sigreturn`。
4. 暂时让 `sys_sigreturn` 直接返回零。
5. `sys_sigalarm()` 应把 alarm 间隔与处理函数指针存入 `proc` 结构的新字段中；结构定义在 `kernel/proc.h`。
6. 还需要在 `struct proc` 中记录：距上次处理函数调用经过了多少 tick，或者距离下次调用还剩多少 tick。可以在 `proc.c` 的 `allocproc()` 中初始化这些字段。
7. 每个 tick，硬件时钟强制产生一次中断；从用户态进入的这条路径由 `kernel/trap.c` 的 `usertrap()` 处理。
8. **只在定时器中断时**操作进程的 alarm tick 计数，判断形式应类似：

   ```c
   if(which_dev == 2) ...
   ```

9. 仅当进程启用了定时 alarm 时才调用处理函数。注意，用户 alarm 函数的地址**可能是 0**；例如原页指出，`user/alarmtest.asm` 中 `periodic` 的地址就是 0。
10. 修改 `usertrap()`，使进程的 alarm 间隔到期后，用户进程执行处理函数。思考：RISC-V 从 trap 返回用户空间时，是什么决定用户代码从哪条指令恢复？
11. 使用 GDB 查看 trap 时，让 QEMU 只用一个 CPU 会更方便：

    ```sh
    make CPUS=1 qemu-gdb
    ```

12. 当 `alarmtest` 打印出 `alarm!`，你就完成了这一阶段的目标。

> 编者说明：第 7 条按实际入口作了限定；用户态发生的 trap 与内核态发生的 trap 有不同处理入口。这里只要求在 `usertrap()` 的定时器路径计数，不是给全系统所有 tick 都累计进程 alarm 时间。

### test1／test2：恢复被中断代码

此时 `alarmtest` 很可能在 `test0` 或 `test1` 打印 `alarm!` 后崩溃，或最终打印 `test1 failed`，或没有打印 `test1 passed` 就退出。

要修复这些问题，必须保证处理函数结束后，控制流回到用户程序原先被定时器中断的位置；寄存器内容也必须恢复成中断时的值，让程序不受 alarm 干扰地继续执行。每次 alarm 触发后，还应重新布置（re-arm）计数器，以便周期性调用处理函数。

实验已指定一项设计：**用户 alarm 处理函数结束时必须调用 `sigreturn` 系统调用。** `alarmtest.c` 中的 `periodic` 是例子。可以让 `usertrap` 与 `sys_sigreturn` 相互配合，在处理完 alarm 后正确恢复用户进程。

提示如下：

1. 你需要保存并恢复寄存器。为了正确恢复被中断代码，究竟需要保存哪些寄存器？提示：数量不少。
2. 让 `usertrap` 在定时 alarm 触发时，把足够的状态保存在 `struct proc` 中，使 `sigreturn` 能正确恢复原用户代码。
3. **防止处理函数重入**：如果上一次处理函数尚未返回，内核就不应再次调用它。`test2` 检验这一点。

通过 `test0`、`test1` 和 `test2` 后，运行 **`usertests`**，确认没有破坏内核其他部分。

## 完成与提交

本实验的问答文件是 **`answers-traps.txt`**；保留全部六组汇编问题的回答，并与代码一起纳入提交。先完成 `bttest`、地址解析、`alarmtest` 和 `usertests` 的专用检查，再按[公共资料中的「实验的共同验收与提交步骤」](#/c/mit-6.s081-2020)完成 `make grade`、`time.txt`、Git 提交及原课程的 `make handin` 流程。

原页后续关于 API key、`myapi.key`、未跟踪文件、`make tarball`、提交状态查询与代码下载的共同说明，均见该公共章节。原文通用模板 `answers-lab-name.txt` 在这里具体对应 `answers-traps.txt`。

## 选做挑战（困难）

让 `backtrace()` 打印**函数名与行号**，而不是数字地址。

## 引用与许可

- MIT 6.S081 课程团队，[Lab: traps，Fall 2020](https://pdos.csail.mit.edu/6.S081/2020/labs/traps.html)。本页为中文翻译，保留任务、所有问题与提示、实验输出和选做题；共同提交段链接到公共资料。按课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名；增加的限定和版本说明均标作编者说明。共享原页抓取于 2026-11-06，本页未重新下载。
- 原页的前置阅读：[xv6 教材 rev1，第 4 章，2020-08-31](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)。教材有独立 MIT 许可，此处只作阅读定位。
- 原页提供的辅助链接：[RISC-V 指令手册入口](https://pdos.csail.mit.edu/6.S081/2020/reference.html)、[ASCII 表](http://web.cs.mun.ca/~michael/c/ascii-table.html)、[大小端说明](http://www.webopedia.com/TERM/b/big_endian.html)、[趣味大小端说明](http://www.networksorcery.com/enp/ien/ien137.txt)、[GCC 内联汇编说明](https://gcc.gnu.org/onlinedocs/gcc/Using-Assembly-Language-with-C.html)、[栈帧课堂 slides](https://pdos.csail.mit.edu/6.828/2020/lec/l-riscv-slides.pdf)。保留原链接，不代表已重新验证这些外部页面当前可用。
- 本页代码块为官方题面给出的片段，并非实验解答。未引用视频或课堂截图；课程网站许可不用于推定视频、外链文档或 xv6 源码的许可。
- 未获取实验分支的测试源码或生成反汇编，未运行编译、QEMU、实验测试或提交命令。上面的终端输出均来自官方题面，不是本站的实测结果。覆盖映射见本目录 `sources/coverage.json`。
