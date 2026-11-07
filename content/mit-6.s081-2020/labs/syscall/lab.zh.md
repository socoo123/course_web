---
source: MIT 6.S081 Fall 2020 · Lab System calls · https://pdos.csail.mit.edu/6.S081/2020/labs/syscall.html
license: MIT 课程团队；课程网站 CC BY 3.0 US；中文翻译，编者校注另标
status: 2020 官方任务、提示、完整追踪样例、验收条件与两项选做已译；共同提交段转公共资料；未运行实验
---

# 系统调用实验

上一个实验使用系统调用编写了几个工具。本实验要为 xv6 添加新的系统调用，从而理解系统调用的工作方式，并接触 xv6 内核的一些内部结构。后续实验还会添加更多系统调用。

## 开始之前

编写代码前，阅读 xv6 教材**第 2 章及第 4 章的 §4.3、§4.4**，以及相关源码：

| 部分 | 文件 |
|---|---|
| 用户空间系统调用代码 | `user/user.h`、`user/usys.pl` |
| 内核空间系统调用代码 | `kernel/syscall.h`、`kernel/syscall.c` |
| 进程相关代码 | `kernel/proc.h`、`kernel/proc.c` |

> **编者阅读导航：** 第 2 章中译见 [LEC 3 课程资料](#/c/mit-6.s081-2020/lec/lec03?v=materials)；第 4 章请按 rev1 的 §4.3「调用系统调用」与 §4.4「系统调用参数」阅读，教材入口及实验仓库见[公共资料](#/c/mit-6.s081-2020)。本实验指导中的内存分配背景另可参阅 [LEC 4 课程资料](#/c/mit-6.s081-2020/lec/lec04?v=materials) §3.4–3.5。

在实验仓库中切换到 `syscall` 分支：

```sh
$ git fetch
$ git checkout syscall
$ make clean
```

此时运行 `make grade`，会看到评分脚本无法执行 `trace` 和 `sysinfotest`。你的工作是添加必要的系统调用及桩函数（stub），使它们可以工作。

## 系统调用追踪（System call tracing，moderate）

### 任务要求

添加系统调用追踪功能；它可能帮助你调试后续实验。新增的 `trace` 系统调用用于控制追踪，接收一个整数参数 **`mask`**，其各个位指定要追踪哪些系统调用。

例如，要追踪 `fork`，程序调用 `trace(1 << SYS_fork)`；`SYS_fork` 是 `kernel/syscall.h` 中定义的系统调用号。修改 xv6 内核：每个系统调用即将返回时，如果掩码中与该调用号对应的位被设置，就打印一行，包含：

- 进程 ID；
- 系统调用名称；
- 返回值。

**不要求打印系统调用参数。** `trace` 应对调用它的进程，以及该进程此后通过 `fork` 创建的子进程启用追踪；不能影响其他进程。

### 官方运行样例与验收

实验提供用户程序 `trace`（见 `user/trace.c`），用于在启用追踪的情况下运行另一个程序。完成后，应能看到类似输出：

```text
$ trace 32 grep hello README
3: syscall read -> 1023
3: syscall read -> 966
3: syscall read -> 70
3: syscall read -> 0
$
$ trace 2147483647 grep hello README
4: syscall trace -> 0
4: syscall exec -> 3
4: syscall open -> 3
4: syscall read -> 1023
4: syscall read -> 966
4: syscall read -> 70
4: syscall read -> 0
4: syscall close -> 0
$
$ grep hello README
$
$ trace 2 usertests forkforkfork
usertests starting
test forkforkfork: 407: syscall fork -> 408
408: syscall fork -> 409
409: syscall fork -> 410
410: syscall fork -> 411
409: syscall fork -> 412
410: syscall fork -> 413
409: syscall fork -> 414
411: syscall fork -> 415
...
$
```

四组样例分别说明：

1. `trace 32` 运行 `grep`，只追踪 `read`；这里 `32` 是 `1 << SYS_read`。
2. `trace 2147483647` 运行 `grep`，追踪所有系统调用；该整数的低 31 位都为 1。
3. 直接运行 `grep` 时未启用追踪，因此不打印追踪信息。
4. `trace 2 usertests forkforkfork` 追踪 `usertests` 中 `forkforkfork` 测试所有后代的 `fork` 调用。

官方以程序具有上述行为为正确标准，进程 ID 可以不同。

> **编者校注：** 原页第二组样例命令为正确的 `2147483647`，但紧随其后的说明误写成 `2147583647`。这里统一为 `2147483647 = 2^31 - 1`，并保留此纠错记录。以上为官方样例，不是本站运行结果；`...` 也来自原样例。

### 官方提示

1. 在 `Makefile` 的 `UPROGS` 中加入 `$U/_trace`。
2. 运行 `make qemu`。由于系统调用的用户空间桩函数尚不存在，`user/trace.c` 会编译失败。需要在 `user/user.h` 中添加系统调用原型，在 `user/usys.pl` 中添加桩函数条目，在 `kernel/syscall.h` 中添加系统调用号。`Makefile` 调用 Perl 脚本 `user/usys.pl` 生成 `user/usys.S`；后者包含实际的系统调用桩函数，通过 RISC-V 的 `ecall` 指令进入内核。修好编译问题后，运行 `trace 32 grep hello README`；此时仍会失败，因为内核中尚未实现该系统调用。
3. 在 `kernel/sysproc.c` 中添加 `sys_trace()`，把参数保存在 `proc` 结构的新变量中（见 `kernel/proc.h`）。从用户空间取得系统调用参数的函数在 `kernel/syscall.c` 中；其使用示例可在 `kernel/sysproc.c` 中找到。
4. 修改 `kernel/proc.c` 中的 `fork()`，把父进程的追踪掩码复制给子进程。
5. 修改 `kernel/syscall.c` 中的 `syscall()`，打印追踪输出。需要添加一个系统调用名称数组，以调用号为索引查找名称。

## 系统信息（Sysinfo，moderate）

### 任务要求

添加 `sysinfo` 系统调用，收集运行中系统的信息。它接收一个参数：指向 **`struct sysinfo`** 的指针（见 `kernel/sysinfo.h`）。内核填写结构中的字段：

| 字段 | 官方定义 |
|---|---|
| `freemem` | 空闲内存的**字节数** |
| `nproc` | `state` **不等于 `UNUSED`** 的进程数 |

实验提供测试程序 `sysinfotest`；它打印 **`sysinfotest: OK`** 时，这项任务通过。

### 官方提示

1. 在 `Makefile` 的 `UPROGS` 中加入 `$U/_sysinfotest`。
2. 运行 `make qemu`，此时 `user/sysinfotest.c` 会编译失败。按上一项任务的步骤添加 `sysinfo` 系统调用。在 `user/user.h` 中声明 `sysinfo()` 的原型之前，需要先前置声明 `struct sysinfo`：

   ```c
   struct sysinfo;
   int sysinfo(struct sysinfo *);
   ```

   修好编译问题后，运行 `sysinfotest`；此时仍会失败，因为还没有实现内核中的系统调用。
3. `sysinfo` 需要把一个 `struct sysinfo` 复制回用户空间。参照 `kernel/sysfile.c` 中的 `sys_fstat()` 和 `kernel/file.c` 中的 `filestat()`，了解如何使用 `copyout()` 完成这件事。
4. 在 `kernel/kalloc.c` 中添加一个函数，收集空闲内存量。
5. 在 `kernel/proc.c` 中添加一个函数，收集进程数量。

## 完成与提交

两项任务完成后，必须通过全部 `make grade` 测试。

`time.txt`、Git 跟踪与提交、`make handin`、API key、未跟踪文件检查，以及失败时的 `make tarball` 网页上传流程，统一见[公共资料 →「实验的共同验收与提交步骤」](#/c/mit-6.s081-2020)。本页已核对该公共流程与 2020 syscall 原页一致。

> **编者说明：** 原页提交模板写“如果本实验有问题”，才要求把回答写入 `answers-lab-name.txt`。本实验正文没有单列需书面作答的问题，也没有指定专属答案文件；不要把通用模板误读成额外必做题。原提交日志示例中的 `[util ...]` 也是通用示例，本实验分支仍是 `syscall`。

## 选做挑战（Optional challenge exercises）

1. 为被追踪的系统调用打印参数（easy）。
2. 计算平均负载（load average），并通过 `sysinfo` 导出（moderate）。

> **编者说明：** 这两项是原页的选做，不是上述两项必做任务的验收条件。原页没有进一步规定平均负载的采样周期或计算公式。

## 来源与许可

- MIT 6.S081 课程团队，[Lab: System calls，Fall 2020](https://pdos.csail.mit.edu/6.S081/2020/labs/syscall.html)。按课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名翻译；内容变更为中文表述、重排小节、标记原页数字笔误，并把共用提交段集中到公共资料。
- 共享原页存档抓取于 2026-11-06；本页覆盖正文起止、全部提示、完整追踪输出样例、测试与两项选做。对应范围见 `sources/coverage.json`，来源哈希见 `sources/manifest.json`。
- 本文没有运行 QEMU、`sysinfotest`、`make grade` 或提交命令。实验分支测试源码未在本次资料中读取；原页仅公布上述验收命令与结果，不据此宣称已知评分脚本的每个内部用例。
