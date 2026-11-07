# Lab util · Xv6 与 Unix 工具

MIT 6.S081 Fall 2020 · 官方任务中文导读（非逐段全文翻译）

完整任务和提示已译入本实验的「实验说明」标签。本页保留任务思路与常见错误，适合动手时对照。

来源：MIT 课程团队，[Lab: Xv6 and Unix utilities](https://pdos.csail.mit.edu/6.S081/2020/labs/util.html)。按照课程网站 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 标识署名；本页翻译、压缩启动输出与提交说明，增加了标为“编者提示”的衔接内容。

**版本锁定：** 使用 `xv6-labs-2020` 的 `util` 分支。任务是 sleep、pingpong、primes、find、xargs；不要与其他年份的实验任务表混用。

## 1. 环境与启动

官方历史命令：

```sh
git clone git://g.csail.mit.edu/xv6-labs-2020
cd xv6-labs-2020
git checkout util
make qemu
```

这是网页提供的命令，本次没有执行或验证当前仓库连接。工具安装参考[同学期 tools 页](https://pdos.csail.mit.edu/6.S081/2020/tools.html)；现代 macOS 的实际安装步骤应在实验准备任务中单独验证。

正常启动后能看到 xv6 shell 的 `$` 提示符，输入 `ls` 查看文件。`Ctrl-p` 打印进程信息；退出 QEMU 使用 `Ctrl-a`，再按 `x`。

用户程序写在 `user/`，还必须加入 Makefile 的 `UPROGS`，才会编译并放进 xv6 文件系统。`make grade` 执行测试；修改进度可用 Git 保存。

## 2. sleep

**官方要求：** 在 `user/sleep.c` 实现 sleep，暂停用户给出的 tick 数。tick 是内核定时器两次中断之间的时间单位。缺少参数时打印错误。

阅读 `user/echo.c` 等程序学习 argv；用 `atoi` 将字符串变成整数，调用 sleep 系统调用，最后调用 exit。声明见 `user/user.h`，实现入口见 `kernel/sysproc.c` 的 `sys_sleep`，用户态汇编跳板见构建产生的 `user/usys.S`。

在 xv6 中运行 `sleep 10` 应短暂停顿再返回；单项测试：

```sh
./grade-lab-util sleep
# 或
make GRADEFLAGS=sleep grade
```

编者提示：在 xv6 的 shell 中执行用户程序，与在宿主机终端运行测试脚本，是两个不同环境。

## 3. pingpong

**官方要求：** 在 `user/pingpong.c` 使用一对管道，在父子进程之间往返传递一个字节。父发给子；子打印 `<pid>: received ping`，回发一个字节并退出；父收到后打印 `<pid>: received pong` 并退出。PID 用 `getpid` 获取。

编者提示：一条管道是一条单向字节流，往返需要明确两条管道的方向。画出 fork 后各进程持有的四个 fd，再关闭每个进程不用的端点。

## 4. primes

**官方要求：** 在 `user/primes.c` 用 pipe 和 fork 实现并发素数筛。首进程输入 2 到 35；每个筛选进程取出遇到的第一个素数，将不可被该素数整除的数传给下游。

- 根据需要创建下游进程，不一次创建所有进程。
- 建议传输 4 字节整数，不转换成十进制字符串。
- 关闭不需要的 fd，避免达到 xv6 的进程或 fd 限制。
- 首进程退出前应确保整个管道链已结束，包括后代进程。
- 最终应打印 2、3、5、7、11、13、17、19、23、29、31。

编者提示：一层等待自己的直接子进程，配合下一层的相同行为，可以逐级收束整个进程链。EOF 依赖所有写端关闭，不是“目前没人写”。

## 5. find

**官方要求：** 在 `user/find.c` 搜索目录树中具有指定名字的文件。

- 参考 `user/ls.c` 读取目录。
- 使用递归进入子目录，但不要递归进入 `.` 和 `..`。
- C 字符串比较用 `strcmp`，不是 `==`。
- xv6 文件系统会跨 QEMU 运行保留内容；需要清空实验文件系统时，官方建议 `make clean` 后重新启动。

例如创建 `b` 和 `a/b` 后，运行 `find . b` 应得到 `./b` 与 `./a/b`。

## 6. xargs

**官方要求：** 在 `user/xargs.c` 从标准输入读行，把每行参数追加到指定命令后，逐行运行命令。

```sh
echo hello too | xargs echo bye
# 期望输出：bye hello too
```

用 fork/exec 执行命令，父进程 wait；可以逐字节读取直到换行。`kernel/param.h` 中的 `MAXARG` 可用于参数数组。这里不要求真实 Unix xargs 的批处理优化。

用 `sh < xargstest.sh` 检查行为，最后用 `make grade` 验收整个实验。find 与 xargs 组合失败时，也可能需要回头检查 find。

## 7. 完成标准与选做

官方要求所有评分测试通过；历史课程还要求提交代码、记录 `time.txt` 和通过课程系统交作业。本地学习以测试和理解实现为目标，提交细节见原文。

选做：用 uptime 显示运行 tick 数；让 find 支持正则表达式；扩展 shell 的命令列表、子 shell、历史、补全等功能。

**本次验证状态：** 已读取官方实验页，完成任务导读；没有运行实验代码或评分脚本。
