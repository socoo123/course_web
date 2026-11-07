---
source: https://pdos.csail.mit.edu/6.S081/2020/labs/util.html
license: MIT 课程团队；CC BY 3.0 US，署名与修改说明见正文
status: 2020 util 实验要求中文翻译；未运行实验或评分脚本
---

# 实验：xv6 与 Unix 工具

本实验帮助你熟悉 xv6 及其系统调用。

来源：MIT 6.S081 Fall 2020 课程团队，[Lab: Xv6 and Unix utilities](https://pdos.csail.mit.edu/6.S081/2020/labs/util.html)。按课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 标识署名翻译。保留原网页九个章节及顺序、全部任务、提示、选做题和提交步骤；纯编译日志、目录大小与上传进度日志作了省略，不影响操作要求。编者注与官方要求分开。英文来源快照保存在课程 `sources/lab-util.html`。

## 启动 xv6（简单）

可以在 Athena 机器或自己的计算机上完成实验。使用自己的计算机时，先看[同学期工具页面](https://pdos.csail.mit.edu/6.S081/2020/tools.html)中的环境准备说明。

如果使用 Athena，必须使用 x86 机器：`uname -a` 输出应包含 `i386 GNU/Linux`、`i686 GNU/Linux` 或 `x86_64 GNU/Linux`。可通过 `ssh -X athena.dialup.mit.edu` 登录公共主机。课程已在 Athena 配置编译器和模拟器，执行 `add -f 6.828` 即可使用。每次登录都要执行，也可以加到 `~/.environment`。如果编译或运行 QEMU 时出现难以理解的错误，检查是否添加了课程 locker。

获取实验源码并切换到 util 分支：

```sh
git clone git://g.csail.mit.edu/xv6-labs-2020
cd xv6-labs-2020
git checkout util
```

`xv6-labs-2020` 与教材使用的 `xv6-riscv` 略有不同，主要是增加了一些文件。感兴趣可以运行 `git log` 查看历史。

本次及后续实验的文件通过 Git 分发。刚才切换的 util 分支包含为本实验定制的 xv6。可参考 [Git 用户手册](https://www.kernel.org/pub/software/scm/git/docs/user-manual.html)及[面向计算机科学背景读者的 Git 介绍](http://eagain.net/articles/git-for-computer-scientists/)。Git 记录你对代码的修改；完成一道题后，可以提交进度：

```sh
git commit -am 'my solution for util lab exercise 1'
```

用 `git diff` 查看自上次提交以来的修改，用 `git diff origin/util` 查看相对于初始 util 分支的修改。

> 编者注：原文在紧接这条命令的解释里写成 `origin/xv6-labs-2020`，与前面的实际分支名不一致；这里以命令中的 `origin/util` 为准。`git commit -am` 不会自动纳入新文件，新建文件需先 `git add`。

编译并启动：

```sh
make qemu
```

它会编译内核、用户程序，生成文件系统镜像，并启动 RISC-V QEMU。省略编译日志后，启动输出形如：

```text
xv6 kernel is booting
hart 2 starting
hart 1 starting
init: starting sh
$
```

在 xv6 提示符输入 `ls`，会看到 `.`, `..`, `README`, `xargstest.sh`, `cat`, `echo`, `forktest`, `grep`, `init`, `kill`, `ln`, `ls`, `mkdir`, `rm`, `sh`, `stressfs`, `usertests`, `grind`, `wc`, `zombie`, `console` 等文件。它们由 mkfs 放入初始文件系统；多数是可以运行的程序，你刚才已经运行了其中的 ls。

xv6 没有 ps 命令，但按 `Ctrl-p` 可以让内核打印每个进程的信息。此时通常能看到 init 和 sh 两行。退出 QEMU：先按 `Ctrl-a`，再按 `x`。

> 编者注：以上保留 2020 官网的环境与仓库命令；本页未实际测试当前 Athena 服务、仓库协议或本机工具链。

## 评分与提交方式

运行 `make grade`，使用评分程序测试你的解答。助教会使用相同的程序评分。另外还有实验检查面谈，安排见[课程评分政策](https://pdos.csail.mit.edu/6.S081/2020/general.html#grading)。

实验的 GNU Make 规则简化了提交过程。完成最后的 Git 提交后，在实验目录执行 `make handin`。详细流程见下面「提交实验」。

## sleep（简单）

为 xv6 实现 Unix 的 sleep 程序：暂停用户指定数量的 **tick**。tick 是 xv6 内核定义的时间单位，表示定时器两次中断之间的时间。代码放在 `user/sleep.c`。

提示：

- 编码前先读 xv6 教材第 1 章，其中文译文在[第 1 讲的「课程资料」](#/c/mit-6.s081-2020/lec/lec01?v=materials)。
- 查看 `user/echo.c`、`user/grep.c`、`user/rm.c`，了解如何取得命令行参数。
- 用户没有传参数时，sleep 应打印错误消息。
- 命令行参数是字符串，可用 `atoi` 转成整数，见 `user/ulib.c`。
- 使用 sleep 系统调用。
- `kernel/sysproc.c` 的 `sys_sleep` 是内核实现；`user/user.h` 声明用户程序可调用的 sleep；`user/usys.S` 包含从用户代码进入内核的汇编代码。
- 确保 main 调用 exit 结束程序。
- 把 sleep 加到 Makefile 的 `UPROGS` 中；之后 `make qemu` 会编译它，并允许从 xv6 shell 运行。
- 学习 C 可参考 K&R 的《The C Programming Language》第 2 版。

在 xv6 中运行：

```text
$ sleep 10
（暂停一小段时间）
$
```

程序应暂停后返回提示符。运行 `make grade` 检查 sleep 测试是否通过。它会运行全部任务测试；只测 sleep，可在宿主机实验目录执行：

```sh
./grade-lab-util sleep
# 等价写法
make GRADEFLAGS=sleep grade
```

## pingpong（简单）

编写程序，利用 Unix 系统调用，通过一对方向相反的管道在两个进程之间往返传递一个字节。

父进程先发送一个字节给子进程；子进程打印 `<pid>: received ping`，其中 `<pid>` 是自己的进程 ID，然后通过另一条管道把字节写回父进程并退出。父进程读取这个字节，打印 `<pid>: received pong`，然后退出。代码放在 `user/pingpong.c`。

提示：

- 用 pipe 创建管道，用 fork 创建子进程。
- 用 read 读取管道，用 write 写入管道。
- 用 getpid 取得调用进程的 PID。
- 把程序加入 Makefile 的 `UPROGS`。
- xv6 用户程序可用的库函数有限，列表见 `user/user.h`；除系统调用之外的实现主要在 `user/ulib.c`、`user/printf.c` 和 `user/umalloc.c`。

在 xv6 shell 运行，应产生类似输出：

```text
$ pingpong
4: received ping
3: received pong
$
```

正确解答要真的在两个进程之间传递字节，并输出上述形式的信息。PID 以实际运行结果为准。

## primes（中等／困难）

使用管道实现并发素数筛。这个想法来自 Unix 管道的发明者 Doug McIlroy。[这篇文章](https://swtch.com/~rsc/thread/)中部的图及周围文字解释了方法。代码放在 `user/primes.c`。

目标是用 pipe 和 fork 建立流水线。第一个进程把 2 到 35 的整数送入流水线。每个素数对应一个进程：它通过管道从左邻居读取，再通过另一条管道向右邻居写入。由于 xv6 的文件描述符和进程数量有限，第一个进程在 35 停止即可。

提示：

- 小心关闭每个进程不用的 fd，否则还没处理到 35 就可能耗尽 xv6 资源。
- 第一个进程送完 35 后，应等待整个流水线结束，包括子进程、孙进程等所有后代。主 primes 进程只能在全部输出打印完、其他 primes 进程都退出后结束。
- 管道写端关闭后，读取到末尾的 read 返回 0。
- 直接通过管道传递 32 位（4 字节）整数最简单，不必转换为格式化的 ASCII 文本。
- 只在需要时创建下游进程。
- 把程序加入 `UPROGS`。

正确解答使用管道实现筛法，并输出：

```text
$ primes
prime 2
prime 3
prime 5
prime 7
prime 11
prime 13
prime 17
prime 19
prime 23
prime 29
prime 31
$
```

## find（中等）

实现简化版 Unix find：查找目录树中所有具有指定名字的文件。代码放在 `user/find.c`。

提示：

- 查看 `user/ls.c`，了解怎样读取目录。
- 使用递归进入子目录。
- 不要递归进入 `.` 与 `..`。
- 文件系统修改会在多次 QEMU 运行之间保留。需要重新得到干净文件系统时，执行 `make clean`，再执行 `make qemu`。
- 需要使用 C 字符串，可参考 K&R §5.5。
- C 中的 `==` 不像 Python 那样比较字符串内容，应使用 `strcmp()`。
- 把程序加入 `UPROGS`。

当存在 b 和 a/b 时，结果应为：

```text
$ echo > b
$ mkdir a
$ echo > a/b
$ find . b
./b
./a/b
$
```

## xargs（中等）

实现简化版 Unix xargs：从标准输入逐行读取，对每一行运行一次命令，把该行内容作为参数传给命令。代码放在 `user/xargs.c`。

例如：

```text
$ echo hello too | xargs echo bye
bye hello too
$
```

命令原本是 `echo bye`，额外参数是 `hello too`，组合后执行 `echo bye hello too`，输出 `bye hello too`。

真正的 Unix xargs 会优化为一次向命令传入多个输入参数，本实验不要求这种批处理优化。原文建议在 Unix 上用 `-n 1` 观察逐个参数执行的行为：

```sh
echo "1\n2" | xargs -n 1 echo line
```

预期输出为 `line 1` 和 `line 2` 两行。

> 编者注：不同 shell 的 echo 对 `\n` 处理不一致，宿主机演示可用 `printf '1\n2\n' | xargs -n 1 echo line`。`-n 1` 限制的是输入参数个数，而不是任意文本的行数；本实验仍按原任务要求逐行执行。

提示：

- 对每行输入，用 fork 和 exec 运行命令；父进程用 wait 等待子进程完成。
- 可逐字符读取，直到遇到换行 `\n`，从而得到一行。
- `kernel/param.h` 中定义了 `MAXARG`，声明 argv 数组时可能有用。
- 把程序加入 `UPROGS`。
- 文件系统修改会跨 QEMU 运行保留；需要干净文件系统时执行 `make clean`、`make qemu`。

xargs、find 与 grep 可以组合：

```sh
find . b | xargs grep hello
```

它会对当前目录及子目录中每个名为 b 的文件执行 `grep hello`。

测试 xargs 时，在 xv6 中执行脚本：

```text
$ sh < xargstest.sh
$ $ $ $ $ $ hello
hello
hello
$ $
```

如果结果不对，可能还要回头修复 find。输出中有很多 `$`，因为 xv6 shell 不知道自己正在从文件而非控制台读取命令，仍为每条命令打印提示符。

## 提交实验

实验至此结束。确认通过所有 `make grade` 测试。如果实验包含问答，把答案写入 `answers-<lab-name>.txt`。提交修改，记得纳入答案文件，然后在实验目录执行 `make handin`。

### 花费时间

新建 `time.txt`，里面只写一个整数，表示完成实验花费的小时数。不要忘记 git add 和 git commit。

### 提交步骤

原课程使用[2020 提交网站](https://6828.scripts.mit.edu/2020/handin.py/)。首次提交前，要在网站申请 API key。最终代码提交到 Git 后，执行：

```sh
git commit -am "ready to submit my lab"
make handin
```

按提示输入 API key。make handin 会把它存入 `myapi.key`。需要更换时，删除该文件，让 make handin 再次生成；文件中不能含换行符。

如果存在未提交的修改或未跟踪文件，会看到类似：

```text
 M hello.c
?? bar.c
?? foo.pyc
Untracked files will not be handed in. Continue? [y/N]
```

检查这些行，确保实验需要的文件都已被 Git 跟踪，而不是以 `??` 开头。用 `git add filename` 添加新文件。

如果 make handin 不正常，可以检查 curl 或 Git 命令的问题；也可以运行 `make tarball` 生成压缩包，再通过提交网站上传。

官方提交前提醒：运行 make grade，确保通过全部测试；运行 make handin 前提交所有修改的源码；可在提交网站检查提交状态、下载已提交代码。

> 编者注：这是历史学期的完整提交流程。本地自学者完成代码、测试并保存进度即可；本次内容整理没有实际调用提交服务。

## 可选挑战

- 写 uptime 程序，使用 uptime 系统调用，以 tick 为单位打印运行时间。（简单）
- 让 find 的名字匹配支持正则表达式。`grep.c` 有一个基础实现可参考。（简单）
- 改进 `user/sh.c`。Shell 只是另一个用户程序，当前实现很小，缺少真实 shell 的许多功能。可以尝试：
  - 从文件读取命令时不打印 `$`。（中等）
  - 支持 wait。（简单）
  - 支持用 `;` 分隔的命令列表。（中等）
  - 通过 `(` 与 `)` 支持子 shell。（中等）
  - 支持 Tab 补全。（简单）
  - 保存过去执行过的命令历史。（中等）
  - 以及任何你想加入的功能。如果目标较大，可能还需要修改内核，因为 xv6 的现成功能有限。
