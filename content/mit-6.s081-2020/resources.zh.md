---
source: MIT 6.S081 Fall 2020 课程网站（课表、工具页、实验页）；xv6 教材 rev1
license: 课程网站 CC BY 3.0 US（工具页为中文翻译）；教材 MIT 许可
status: 工具页为 2020 年原文的翻译，安装步骤未在本机验证
---

# 公共资料

各讲、各实验都会用到的资料集中在这一章：教材、实验环境、代码仓库和课程网站。每讲专属的讲义和指定阅读，放在该讲的「课程资料」里。

## 教材：xv6 book

课程教材是 *xv6: a simple, Unix-like teaching operating system*（Russ Cox、Frans Kaashoek、Robert Morris 著，2020-08-31 rev1）。全书约 100 页，按内核子系统组织，每章对照 xv6 源码讲解。每讲指定读哪一章，以该讲页面的「指定阅读」为准。

| 章 | 主题 | 起始页 |
|---|---|---|
| 1 | 操作系统接口（Operating system interfaces） | 9 |
| 2 | 操作系统组织（Operating system organization） | 21 |
| 3 | 页表（Page tables） | 29 |
| 4 | 陷阱与系统调用（Traps and system calls） | 41 |
| 5 | 中断与设备驱动（Interrupts and device drivers） | 49 |
| 6 | 锁（Locking） | 55 |
| 7 | 调度（Scheduling） | 67 |
| 8 | 文件系统（File system） | 81 |
| 9 | 再谈并发（Concurrency revisited） | 99 |
| 10 | 总结（Summary） | 103 |

教材按指定阅读分配到各讲的「课程资料」，同一小节只翻译一次：

| 教材范围 | 阅读位置 |
|---|---|
| 第 1 章 | [LEC 1](#/c/mit-6.s081-2020/lec/lec01?v=materials) |
| 第 2、3 章 | [LEC 3](#/c/mit-6.s081-2020/lec/lec03?v=materials)、[LEC 4](#/c/mit-6.s081-2020/lec/lec04?v=materials) |
| 第 4 章（除 §4.6）／§4.6 | [LEC 6](#/c/mit-6.s081-2020/lec/lec06?v=materials)／[LEC 8](#/c/mit-6.s081-2020/lec/lec08?v=materials) |
| 第 5、6 章 | [LEC 9](#/c/mit-6.s081-2020/lec/lec09?v=materials)、[LEC 10](#/c/mit-6.s081-2020/lec/lec10?v=materials) |
| 第 7 章至 §7.4／§7.5–7.10 | [LEC 11](#/c/mit-6.s081-2020/lec/lec11?v=materials)／[LEC 13](#/c/mit-6.s081-2020/lec/lec13?v=materials) |
| 第 8 章非日志部分／§8.4–8.6 日志 | [LEC 14](#/c/mit-6.s081-2020/lec/lec14?v=materials)／[LEC 15](#/c/mit-6.s081-2020/lec/lec15?v=materials) |

页码均指 rev1 印刷页码；不要用新版教材的节号替换本课索引。第 9、10 章可自行延伸阅读。实验星级为本站学习难度估计，并非 MIT 官方评分权重；实际耗时取决于 C、汇编和调试基础。

阅读源码时也要区分版本：本站用上游提交 `e23d53f27f6e187732a92a2b4705639d1c260f05`（2020-08-28）辅助核对教材。它不是讲者录课时的修改工作树，也不是 `xv6-labs-2020` 的各实验分支。若课堂画面、教材和代码不同，各讲会在对应位置注明；动手实验仍以题目指定分支为准。

## 实验环境

> 以下译自 2020 年的课程工具页。版本号（QEMU 5.1、Ubuntu 18.04 等）和 Homebrew 安装命令都停留在 2020 年；在新系统上按原样执行可能失败，以最后「检查安装」一节能通过为准。

本课程需要几种工具的 RISC-V 版本：QEMU 5.1、GDB 8.3、GCC 和 Binutils。

课程强烈建议在 Debathena 机器（例如 athena.dialup.mit.edu）上做实验。MIT Athena 的 Linux 机器上，这些工具都在 6.828 locker 里，输入 `add -f 6.828` 即可使用。没有 Debathena 机器的话，可以按下面的说明直接安装工具，或者使用装有 Linux 的虚拟机。

### 使用 Athena（仅限 MIT 账号）

ssh 登录任意一台 Athena dialup 机器，然后加载工具：

```bash
$ ssh {your kerberos}@athena.dialup.mit.edu
$ add -f 6.828
```

### 在 macOS 上安装

先安装开发者工具：

```bash
$ xcode-select --install
```

然后安装 macOS 的包管理器 Homebrew：

```bash
$ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

接着安装 RISC-V 编译工具链：

```bash
$ brew tap riscv/riscv
$ brew install riscv-tools
```

brew 的安装公式可能不会链接到 `/usr/local`。你需要修改 shell 的配置文件（例如 `~/.bashrc`），把相应目录加进 `$PATH`：

```bash
PATH=$PATH:/usr/local/opt/riscv-gnu-toolchain/bin
```

最后安装 QEMU：

```bash
brew install qemu
```

### 通过 APT 安装（Debian / Ubuntu）

确认你的 Debian 版本是 “bullseye” 或 “sid”（在 Ubuntu 上可以运行 `cat /etc/debian_version` 查看），然后执行：

```bash
sudo apt-get install git build-essential gdb-multiarch qemu-system-misc gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu
```

“buster” 自带的 QEMU 版本太旧，需要另外获取。

**qemu-system-misc 的问题：** 目前 qemu-system-misc 包的一次更新破坏了与课程内核的兼容性。如果运行 `make qemu` 后，脚本在下面这行之后卡住：

```text
qemu-system-riscv64 -machine virt -bios none -kernel kernel/kernel -m 128M -smp 3 -nographic -drive file=fs.img,if=none,format=raw,id=x0 -device virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0
```

就需要卸载这个包，改装旧版本：

```bash
$ sudo apt-get remove qemu-system-misc
$ sudo apt-get install qemu-system-misc=1:4.2-3ubuntu6
```

### 在 Arch 上安装

```bash
sudo pacman -S riscv64-linux-gnu-binutils riscv64-linux-gnu-gcc riscv64-linux-gnu-gdb qemu-arch-extra
```

### 其他 Linux 发行版：自己编译工具链

这里假定你在较新的 Ubuntu 上把工具链装到 `/usr/local`。编译需要相当多的磁盘空间（约 9 GiB）；空间不够的话，考虑使用 MIT Athena 机器。

先克隆 RISC-V GNU 编译工具链仓库：

```bash
$ git clone --recursive https://github.com/riscv/riscv-gnu-toolchain
```

确认已安装编译工具链所需的包：

```bash
$ sudo apt-get install autoconf automake autotools-dev curl libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev
```

配置并编译工具链：

```bash
$ cd riscv-gnu-toolchain
$ ./configure --prefix=/usr/local
$ sudo make
$ cd ..
```

接着下载并解压 QEMU 5.1.0 的源码：

```bash
$ wget https://download.qemu.org/qemu-5.1.0.tar.xz
$ tar xf qemu-5.1.0.tar.xz
```

为 riscv64-softmmu 编译 QEMU：

```bash
$ cd qemu-5.1.0
$ ./configure --disable-kvm --disable-werror --prefix=/usr/local --target-list="riscv64-softmmu"
$ make
$ sudo make install
$ cd ..
```

### Windows：运行 Linux 虚拟机

课程没有测试过，但也许可以通过 Windows Subsystem for Linux（WSL）或自己编译工具得到所需的一切。

更简单的办法可能是用虚拟机运行上面列出的某个操作系统。借助平台虚拟化，Linux 可以和你平时的计算环境共存。安装 Linux 虚拟机分两步：先下载虚拟化平台：

- VirtualBox（Mac、Linux、Windows 免费）
- VMware Player（Linux 和 Windows 免费，需要注册）
- VMware Fusion（MIT 学生可从 IS&T 免费下载）

VirtualBox 稍慢、不够灵活，但免费。

装好虚拟化平台后，下载你选择的 Linux 发行版的启动盘镜像，例如 Ubuntu Desktop。下载得到的文件名类似 `ubuntu-18.04.3-desktop-amd64.iso`。启动虚拟化平台，新建一台 64 位虚拟机，用下载的 Ubuntu 镜像作为启动盘；各平台步骤不同，但都很简单。

### 检查安装

安装完成后，应该能看到下面的结果：

```bash
$ riscv64-unknown-elf-gcc --version
riscv64-unknown-elf-gcc (GCC) 10.1.0
...

$ qemu-system-riscv64 --version
QEMU emulator version 5.1.0
```

还应该能编译并运行 xv6：

```bash
# 在 xv6 目录中
$ make qemu
# ... 大量输出 ...
init: starting sh
$
```

退出 qemu：按 `Ctrl-a x`。

## 实验代码与 11 个实验

所有实验共用一个仓库，每个实验是一个分支：

```bash
$ git clone git://g.csail.mit.edu/xv6-labs-2020
$ cd xv6-labs-2020
$ git checkout util      # 换成对应实验的分支名
$ make qemu
$ make grade             # 在 qemu 外运行，跑本实验全部测试
```

| 分支 | 实验 | 官方页面 |
|---|---|---|
| `util` | Unix 工具 | [util](https://pdos.csail.mit.edu/6.S081/2020/labs/util.html) |
| `syscall` | 系统调用 | [syscall](https://pdos.csail.mit.edu/6.S081/2020/labs/syscall.html) |
| `pgtbl` | 页表 | [pgtbl](https://pdos.csail.mit.edu/6.S081/2020/labs/pgtbl.html) |
| `traps` | 陷阱 | [traps](https://pdos.csail.mit.edu/6.S081/2020/labs/traps.html) |
| `lazy` | 懒分配 | [lazy](https://pdos.csail.mit.edu/6.S081/2020/labs/lazy.html) |
| `cow` | 写时复制 fork | [cow](https://pdos.csail.mit.edu/6.S081/2020/labs/cow.html) |
| `thread` | 多线程 | [thread](https://pdos.csail.mit.edu/6.S081/2020/labs/thread.html) |
| `lock` | 并行与锁 | [lock](https://pdos.csail.mit.edu/6.S081/2020/labs/lock.html) |
| `fs` | 文件系统 | [fs](https://pdos.csail.mit.edu/6.S081/2020/labs/fs.html) |
| `mmap` | 内存映射 | [mmap](https://pdos.csail.mit.edu/6.S081/2020/labs/mmap.html) |
| `net` | 网卡驱动 | [net](https://pdos.csail.mit.edu/6.S081/2020/labs/net.html) |

动手前建议先读课程的 [Lab guidance](https://pdos.csail.mit.edu/6.S081/2020/labs/guidance.html)，里面有调试技巧和难度说明。

## 实验的共同验收与提交步骤

先完成各实验说明中的专用测试，再运行 `make grade`。实验要求回答的问题应写入对应答案文件；2020 页面中的 `answers-lab-name.txt` 是通用模板，具体文件名以该实验说明和分支要求为准。

在实验目录创建 `time.txt`，只写一个整数，表示完成实验所花的小时数。将新增文件加入 Git，并提交最终修改；新增答案文件和 `time.txt` 也需要跟踪，单独使用 `git commit -am ...` 不会添加未跟踪文件。

2020 课程的正式提交使用 `make handin`：

1. 首次先到课程的提交网站申请 API key，运行命令时按提示输入。
2. 命令将 key 保存在实验目录的 `myapi.key`；如需更换，删除该文件后重新执行。原页要求文件内容不含换行符。
3. 如果命令列出未提交修改或以 `??` 开头的未跟踪文件，检查实验所需文件是否已全部纳入版本管理；未跟踪文件不会被提交。
4. `make handin` 失败时，原页建议检查 curl 或 Git；也可用 `make tarball` 生成归档，再通过网页上传。
5. 原课程网站提供提交状态查询及已提交代码下载。

这些是原课程的历史提交流程；本地自学重点是完成题目要求与测试，不需要把代码交到 MIT 的历史教学系统。各实验页保留专用命令、问题与选做任务，通用流程集中在此。

## 引用

- MIT 6.S081 课程团队，[Fall 2020 课表](https://pdos.csail.mit.edu/6.S081/2020/schedule.html)：讲次、视频、实验链接。
- MIT 6.S081 课程团队，[Tools Used in 6.S081](https://pdos.csail.mit.edu/6.S081/2020/tools.html)：本章「实验环境」的原文，页面标注 CC BY 3.0 US；译文保留全部步骤与命令，命令未改动。
- Russ Cox、Frans Kaashoek、Robert Morris，[xv6 教材 rev1](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)，2020-08-31：目录与页码取自该版 PDF；教材采用 MIT 许可。
- MIT PDOS，[xv6-riscv 固定参考提交](https://github.com/mit-pdos/xv6-riscv/tree/e23d53f27f6e187732a92a2b4705639d1c260f05)，2020-08-28：教材源码核对基准；归档记录见 `sources/code-snapshot.json`。
- 实验列表与分支名取自 2020 课表与课程导航中的实验链接。
- MIT 6.S081 课程团队，[2020 Page tables 实验](https://pdos.csail.mit.edu/6.S081/2020/labs/pgtbl.html)的「Submit the lab」「Time spent」「Submit」：本章共同验收与提交步骤的中文整理，按课程官网 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) 署名；已区分本地自学说明。原提交入口为 `https://6828.scripts.mit.edu/2020/handin.py/`，未验证当前可用性，未实际执行提交或实验测试。
- 已核对 2020 [cow](https://pdos.csail.mit.edu/6.S081/2020/labs/cow.html)、[thread](https://pdos.csail.mit.edu/6.S081/2020/labs/thread.html)、[lock](https://pdos.csail.mit.edu/6.S081/2020/labs/lock.html)、[fs](https://pdos.csail.mit.edu/6.S081/2020/labs/fs.html) 的共同提交段，与上述 pgtbl 原文一致；thread 专用的 `answers-thread.txt` 要求保留在该实验说明中。
