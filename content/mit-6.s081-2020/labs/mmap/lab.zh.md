---
source: MIT 6.S081 Fall 2020 · Lab mmap · https://pdos.csail.mit.edu/6.S081/2020/labs/mmap.html
license: MIT 6.S081 课程网站 CC BY 3.0 US；中文翻译与编者注
status: 官方要求、9 条提示、完整测试示例及 5 项选做已译；共同提交段见公共资料；未运行实验
---

# 内存映射文件

`mmap` 与 `munmap` 系统调用让 UNIX 程序能精细控制自己的地址空间。它们可用于进程间共享内存、把文件映射进进程地址空间，以及构建用户级缺页处理方案，例如课堂讨论过的垃圾回收算法。本实验要为 xv6 添加这两个系统调用，重点是**内存映射文件**。官方难度标为 hard。

## 1. 准备 mmap 分支

在实验仓库中取得更新并切换到 `mmap` 分支：

```bash
$ git fetch
$ git checkout mmap
$ make clean
```

仓库和工具链见[公共资料](#/c/mit-6.s081-2020)「实验环境」「实验代码与 11 个实验」。

## 2. mmap：本实验支持的接口子集

手册页（运行 `man 2 mmap`）给出的声明是：

```c
void *mmap(void *addr, size_t length, int prot, int flags,
           int fd, off_t offset);
```

`mmap` 有很多用法，但本实验只要求与文件映射有关的一部分功能：

| 参数或返回值 | 2020 实验约定 |
|---|---|
| `addr` | 可以假设总是 0，表示由内核选择映射文件的虚拟地址。 |
| 返回值 | 成功返回选定地址；失败返回 `0xffffffffffffffff`。 |
| `length` | 要映射的字节数，可能与文件长度不同。 |
| `prot` | 表示映射是否可读、可写和／或可执行；本实验可以假设只出现 `PROT_READ`、`PROT_WRITE` 或两者的组合。 |
| `flags` | 只会是 `MAP_SHARED` 或 `MAP_PRIVATE`。前者要求把对映射内存的修改写回文件，后者不写回；不必实现其他标志位。 |
| `fd` | 被映射文件的已打开文件描述符。 |
| `offset` | 文件中映射的起点；可以假设总是 0。 |

**不同进程映射同一个 `MAP_SHARED` 文件时，可以不共享物理页。**

> 编者注：声明展示的是手册接口，不要求把宿主系统的全部类型、标志和 POSIX 语义搬进 xv6。本实验也没有要求为了 `MAP_PRIVATE` 实现写时复制；具体机制见「实验指导」。

## 3. munmap：解除整个区域或一端

`munmap(addr, length)` 应移除指定地址范围中的 mmap 映射。如果进程修改了这段内存，而且映射采用 `MAP_SHARED`，就应先把修改写回文件。

一次 `munmap` 可能只覆盖某个映射的一部分，但可以假定它只解除以下三种范围之一：

- 映射的开头部分；
- 映射的末尾部分；
- 整个映射。

不必处理在一个映射的中间挖洞的情况。

## 4. 必做任务与成功示例

实现足够的 `mmap`、`munmap` 功能，让 `mmaptest` 工作。**`mmaptest` 没有使用的 mmap 特性，不要求实现。**

完成后应看到以下输出。它是官方页的完整示例，**不是本站实际运行结果**；`usertests` 中的省略号也来自原页。

```text
$ mmaptest
mmap_test starting
test mmap f
test mmap f: OK
test mmap private
test mmap private: OK
test mmap read-only
test mmap read-only: OK
test mmap read/write
test mmap read/write: OK
test mmap dirty
test mmap dirty: OK
test not-mapped unmap
test not-mapped unmap: OK
test mmap two files
test mmap two files: OK
mmap_test: ALL OK
fork_test starting
fork_test OK
mmaptest: all tests succeeded
$ usertests
usertests starting
...
ALL TESTS PASSED
$
```

## 5. 官方提示

### 提示 1：先接通系统调用

把 `_mmaptest` 加入 `UPROGS`，并添加 `mmap`、`munmap` 系统调用，使 `user/mmaptest.c` 能编译。暂时让两个系统调用只返回错误。`PROT_READ` 等常量已在 `kernel/fcntl.h` 中定义。运行 `mmaptest`，此时应在第一次 mmap 调用处失败。

### 提示 2：惰性填充页表

通过缺页异常按需填充页表。也就是说，`mmap` 本身不应分配物理内存或读取文件，而应在 `usertrap` 内部或它调用的缺页处理代码中完成，方式类似惰性页分配实验。

这样做是为了让映射大文件的操作足够快，也让映射比物理内存更大的文件成为可能。

### 提示 3：为每个进程记录 VMA

记录每个进程通过 `mmap` 建立了哪些映射。定义一个对应于原文所称「Lecture 15」中 VMA（virtual memory area，虚拟内存区域）的结构，保存 mmap 创建的虚拟地址范围的地址、长度、权限、文件等信息。

由于 xv6 内核没有通用动态内存分配器，可以声明一个固定大小的 VMA 数组，按需从中分配；大小为 16 应当足够。

> 编者注：原页确实写的是 Lecture 15，保留这一称呼。但本站 2020 LEC 15 的主题是崩溃恢复，不能把它当成该句的 VMA 阅读定位。相关虚拟内存背景见 [LEC 17](#/c/mit-6.s081-2020/lec/lec17?v=notes)；[LEC 24](#/c/mit-6.s081-2020/lec/lec24?v=notes) §5 讨论 mmap 的接口动机，并非完整实现教程。这里的“没有分配器”指没有通用的 malloc 式内核分配器；xv6 仍有 `kalloc` 页分配器。

### 提示 4：实现 mmap 的区域登记

在进程地址空间中找一段尚未使用的区域映射文件，并在进程的映射区域表里添加一个 VMA。

VMA 应保存指向被映射文件的 `struct file` 指针。`mmap` 应增加文件的引用计数，使得关闭文件描述符后，该结构也不会消失。提示：查看 `filedup`。

运行 `mmaptest`：第一次 `mmap` 应成功，但第一次访问映射内存时会发生缺页异常，并杀死 `mmaptest`。

### 提示 5：缺页时从文件装入一页

添加代码，使映射区域中的缺页异常触发以下操作：分配一个物理页，从对应文件读取 4096 字节到该页，再把它映射进用户地址空间。

使用 `readi` 读文件；它接收文件中的读取偏移量，但你必须对传入 `readi` 的 inode 加锁、解锁。不要忘记设置正确的页权限。

运行 `mmaptest`，现在应能执行到第一次 `munmap`。

### 提示 6：实现 munmap 和共享写回

找到地址范围对应的 VMA，解除指定页的映射。提示：使用 `uvmunmap`。

如果 `munmap` 移除了此前一次 `mmap` 的全部页，应减少相应 `struct file` 的引用计数。如果被解除映射的页已经修改，而且文件采用 `MAP_SHARED` 映射，就把该页写回文件。可以参考 `filewrite` 的做法。

### 提示 7：脏位优化不是必需条件

理想实现只写回程序实际修改过的 `MAP_SHARED` 页。RISC-V PTE 的 dirty 位（`D`）表示一页是否被写过。

不过，`mmaptest` 不检查“未修改的页是否避免了写回”；因此可以不检查 `D` 位而写回页面。

### 提示 8：退出时清理映射

修改 `exit`，使进程退出时解除它的所有映射区域，就像调用了 `munmap` 一样。

运行 `mmaptest`：此时 `mmap_test` 应能通过，但 `fork_test` 可能还不能通过。

### 提示 9：fork 继承映射

修改 `fork`，保证子进程拥有与父进程相同的映射区域。不要忘记增加每个 VMA 所引用的 `struct file` 的引用计数。

子进程发生缺页时，可以分配一个新的物理页，而不与父进程共享页面。共享页会更出色，但需要更多实现工作。

运行 `mmaptest`，此时 `mmap_test` 和 `fork_test` 都应通过。

最后运行 `usertests`，确认原有功能仍然正常。

## 6. 验收与提交

实验专用验收是在 xv6 shell 中运行 `mmaptest` 和 `usertests`，达到上面的成功输出；随后在宿主机实验目录运行 `make grade`，确认全部评分测试通过。

原页的 **Submit the lab、Time spent、Submit** 与其他实验共用。完整要求归[公共资料](#/c/mit-6.s081-2020)「实验的共同验收与提交步骤」：包括条件式答案文件说明、`time.txt`、Git 跟踪与提交、`make handin`、API key 与 `myapi.key`、未跟踪文件提醒、`make tarball` 备用提交及网页状态查询。

> 编者注：本页没有独立书面问题，也没有指定 `answers-mmap.txt`；原文的 `answers-lab-name.txt` 是“如果本实验有问题”的通用模板。提交示例中的 `[util c2e3c8b]` 同样是通用样例，不改变本实验的 `mmap` 分支。共同提交段已与公共资料使用的 pgtbl 原文核对一致。

## 7. 选做挑战

以下五项均为官方选做，不属于上面的基本任务：

1. **共享物理页。** 两个进程映射同一个文件时（例如 `fork_test`），让它们共享物理页。需要为物理页维护引用计数。
2. **直接使用 buffer cache 的内存。** 你的方案可能为从映射文件读出的每一页另分配物理页，尽管同样的数据已经在内核的 buffer cache 中。修改实现，直接使用那里的物理内存。这要求文件块大小与页面大小相同，即把 `BSIZE` 设为 4096；还需要把映射的块固定在 buffer cache 中，并处理引用计数。
3. **统一惰性分配与文件映射。** 消除 lazy allocation 与 mmap 文件实现中的重复。提示：也为惰性分配区域创建 VMA。
4. **按需调页的可执行文件。** 修改 `exec`，为二进制文件的不同节使用 VMA，得到按需调页的可执行程序。原文说明，这样启动程序会更快，因为 `exec` 不必从文件系统读取任何数据。编者注：应区分“推迟装入程序段内容”和“完全不读文件”；识别可执行文件布局仍需读取相应元数据，不应把原句理解为连 ELF 头也不必读取。
5. **换出与换入。** 实现 page-out 与 page-in：物理内存不足时，由内核把进程的一部分移到磁盘；进程再次引用这些内存时，再把它们调入。

## 引用与许可

- **[M1] MIT 6.S081 课程团队，Fall 2020，[Lab: mmap](https://pdos.csail.mit.edu/6.S081/2020/labs/mmap.html)。** 本文为该页要求、全部提示、实验测试示例及选做题的中文翻译；通用提交内容按本站归属集中于公共资料，编者注显式标识。
- 课程网站采用 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)，许可标识见 [2020 课表页底](https://pdos.csail.mit.edu/6.S081/2020/schedule.html)。保留 MIT 课程团队署名；本译文未获官方审校。
- 本地原页于 2026-11-06 抓取，已全文核对 HTML 与文本，并校验 HTML SHA-256；历史 URL 不证明内容自 2020 年起从未更新。来源和逐段覆盖记录见本目录 `sources/manifest.json`、`sources/coverage.json`。
- `man 2 mmap` 保留为原页建议的手册查阅命令；未翻译外部手册，也未把官网许可套用于手册或课堂视频。未运行 QEMU、`mmaptest`、`usertests`、`make grade` 或提交命令。
