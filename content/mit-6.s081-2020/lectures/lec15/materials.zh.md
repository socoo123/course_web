---
source: Russ Cox、Frans Kaashoek、Robert Morris，xv6 book rev1（2020-08-31），§8.4–8.6，印刷页84–87至§8.7前
license: 教材MIT许可；原始版权声明与许可全文见页底
status: 指定三节完整中译，含两段代码；已查看84–87原页，本范围没有独立编号图表
---

# 第15讲 · 日志层、日志设计与实现

## §8.4 日志层

文件系统设计中最有趣的问题之一，是崩溃恢复。问题的根源在于，许多文件系统操作涉及多次磁盘写；如果只完成其中一部分就发生崩溃，磁盘上的文件系统可能处于不一致状态。例如，假设系统在截断文件时崩溃——截断是把文件长度设为零，并释放它的内容块。根据磁盘写入的先后顺序，崩溃后可能留下一个仍然引用已被标为空闲的内容块的 inode；也可能留下一个已分配、却没有任何引用指向它的内容块。

后一种情况相对温和，但 inode 引用已经释放的块，很可能在重启后造成严重问题。重启后，内核可能把这个块分配给另一个文件，于是两个不同文件无意间指向同一个块。如果 xv6 支持多个用户，这还可能成为安全问题：旧文件的所有者能够读写另一个用户的新文件中的块。

xv6 用一种简单的日志机制，解决文件系统操作期间的崩溃问题。一个 xv6 系统调用不会直接写磁盘上的文件系统数据结构。相反，它先把所有准备进行的磁盘写的描述，放进磁盘上的日志。当系统调用已经把全部写入记录到日志后，再向磁盘写入一个特殊的**提交记录**，表示日志中包含一个完整操作。随后，系统调用把这些写入复制到磁盘上的文件系统数据结构。完成这些写后，系统调用清除磁盘日志。

如果系统崩溃并重新启动，文件系统代码会在运行任何进程之前，按以下方式恢复：如果日志被标记为包含一个完整操作，恢复代码就把日志中的写入复制到它们在磁盘文件系统中应该出现的位置。如果日志没有被标记为包含完整操作，恢复代码就忽略日志。最后，恢复代码清除日志。

为什么 xv6 的日志能解决文件系统操作中的崩溃问题？如果崩溃发生在操作提交之前，磁盘日志就不会被标为完整，恢复代码会忽略它；磁盘状态将与操作从未开始时一样。如果崩溃发生在操作提交之后，恢复代码会重放该操作的全部写入；若操作此前已经开始向磁盘文件系统结构写入，重放可能会重复其中一些写。无论哪种情况，日志都让操作相对于崩溃具有原子性：恢复后，该操作的写入要么全部出现在磁盘上，要么全部不出现。

## §8.5 日志设计

日志位于一个已知的固定位置，具体位置由超级块指定。日志由一个头部块，以及紧随其后的一串已更新块的副本组成；后者称为“已记入日志的块”。头部块包含一个扇区号数组，每个已记录块对应一个编号，同时还包含日志块的数量。

磁盘头部块中的数量有两种含义：为零，表示日志中没有事务；非零，表示日志中有一个完整、已经提交的事务，包含指定数量的日志块。xv6 在事务提交时才写头部块，不会提前写；把日志块复制到文件系统之后，再将数量设为零。因此，在事务执行中途、尚未提交时崩溃，日志头里的数量会是零；提交之后、清理之前崩溃，数量会非零。

每个系统调用的代码会标出一串写入的开始和结束，这串写入必须相对于崩溃保持原子性。为了让不同进程的文件系统操作并发执行，日志系统可以把多个系统调用的写入累积到同一个事务中。因此，一次提交可能包含多个完整系统调用的写入。为了避免把一个系统调用拆进不同事务，日志系统只在没有文件系统调用仍在执行时提交。

把多个事务一起提交的思想称为**组提交**（group commit）。组提交把一次提交的固定开销分摊给多个操作，从而减少磁盘操作次数。它还一次性把更多并发写交给磁盘系统，可能让磁盘在旋转一周的过程中完成这些写。xv6 的 virtio 驱动不支持这样的批处理，但 xv6 的文件系统设计允许采用它。

xv6 在磁盘上划出固定大小的空间保存日志。一个事务中，各系统调用写入的块总量必须能放进这片空间。这会带来两个后果。

首先，不能允许任何单个系统调用写入的不同块数超过日志容量。对大多数系统调用，这不是问题；但 `write` 和 `unlink` 都有可能修改很多块。一次大文件写入可能涉及许多数据块、许多位图块以及一个 inode 块；删除大文件可能修改许多位图块和一个 inode。xv6 的 `write` 把大写入拆成多个可以放进日志的小写入；`unlink` 在实践中不会因此出问题，因为 xv6 文件系统只使用一个位图块。

其次，由于日志空间有限，日志系统只有在确定某个系统调用的写入能放进日志剩余空间时，才允许该系统调用开始。

> 编者注：上文“避免拆分系统调用”描述常规的 `begin_op` / `end_op` 操作边界；同一节随后明确指出，大 `write` 是例外，它在实现中被主动分段。不要由前一句推出“任意大小的用户 `write` 都具有整体崩溃原子性”。单个位图块的结论也针对这版小文件系统，不能直接推广到扩容后的实现。

## §8.6 代码：日志

系统调用通常按下面的方式使用日志：

```c
begin_op();
...
bp = bread(...);
bp->data[...] = ...;
log_write(bp);
...
end_op();
```

`begin_op`（`kernel/log.c:126`）会等待，直到日志系统当前没有在提交，并且还有足够的未预留日志空间，能够容纳本次调用将产生的写入。`log.outstanding` 统计已经预留日志空间的系统调用数量；总预留量是 `log.outstanding` 乘以 `MAXOPBLOCKS`。增加 `log.outstanding`，既为本次调用预留空间，也防止它执行期间发生提交。代码保守地假定，每个系统调用最多会写 `MAXOPBLOCKS` 个不同的块。

`log_write`（`kernel/log.c:214`）充当 `bwrite` 的代理。它在内存中记录块的扇区号，为该块在磁盘日志里保留一个槽位，同时把 buffer 固定在块缓存中，防止缓存淘汰它。

这个块必须留在缓存中，直到提交：在此之前，缓存副本是修改的唯一记录；提交前，它不能被写入磁盘上的原位置；并且同一个事务内的其他读取必须能看到这些修改。`log_write` 会注意到同一个块是否在一个事务中被多次写入，并让这个块重复使用同一个日志槽位。这种优化通常叫**吸收**（absorption）。例如，某个磁盘块同时包含几个文件的 inode，它很可能在同一个事务里被多次修改。把多次磁盘写吸收成一次，既能节省日志空间，也能改善性能，因为只需把这个块的一个副本写到磁盘。

`end_op`（`kernel/log.c:146`）先减少尚未结束的系统调用数量。如果数量降为零，就调用 `commit()` 提交当前事务。这个过程有四个阶段：

1. `write_log()`（`kernel/log.c:178`）把本事务修改的每个块，从 buffer cache 复制到它在磁盘日志中的槽位。
2. `write_head()`（`kernel/log.c:102`）把头部块写到磁盘。这就是提交点；如果在这次写之后崩溃，恢复会从日志重放该事务的写入。
3. `install_trans`（`kernel/log.c:69`）从日志读取每个块，再将其写入文件系统中的正确位置。
4. 最后，`end_op` 写入一个数量为零的日志头。必须先完成这一步，下一事务才能开始写日志数据块，否则一旦崩溃，恢复代码可能把前一事务的头部，与后一事务的日志数据错误地组合起来。

`recover_from_log`（`kernel/log.c:116`）由 `initlog`（`kernel/log.c:55`）调用，后者又在启动期间由 `fsinit`（`kernel/fs.c:42`）调用；这发生在第一个用户进程开始运行之前（`kernel/proc.c:539`）。它读入日志头；如果头部表明日志包含已提交事务，就模仿 `end_op` 的相应动作进行恢复。

`filewrite`（`kernel/file.c:135`）是使用日志的一个例子，其事务形式如下：

```c
begin_op();
ilock(f->ip);
r = writei(f->ip, ...);
iunlock(f->ip);
end_op();
```

这段代码被包在一个循环里，循环把大写入拆成若干独立事务，每次只处理少量扇区，以免日志溢出。对 `writei` 的调用会在这个事务中写入多个块：文件的 inode、一个或多个位图块，以及一些数据块。

> 编者注：本节保留 rev1 的源码定位。原文把最后清零概括为 `end_op` 的动作，实际由它调用的 `commit()` 完成；“第一个用户进程开始运行之前”是指进入其用户代码之前，初始化路径已处在启动该进程的内核执行过程中。正文代码是教材的省略式伪调用，不是可直接编译的完整程序。

## 阅读衔接

本讲三节结束于第87页 §8.7 标题之前。块分配器、inode、目录、路径及其他第8章内容统一见[第14讲课程资料](#/c/mit-6.s081-2020/lec/lec14?v=materials)。

课堂如何逐个放置崩溃点、解释 `write_head` 及实际磁盘轨迹，见[中文译稿](#/c/mit-6.s081-2020/lec/lec15?v=draft)30:00–39:00、48:00–63:00。容量推导与自测见[课程笔记](#/c/mit-6.s081-2020/lec/lec15?v=notes)。

需要实现大文件与符号链接时，使用已有[fs 实验说明](#/c/mit-6.s081-2020/lab/fs?v=zh)和[实验指导](#/c/mit-6.s081-2020/lab/fs?v=guide)。本页不是实验分支源码的替代文档。

## 来源、版本与教材许可

- Russ Cox、Frans Kaashoek、Robert Morris，*xv6: a simple, Unix-like teaching operating system*，rev1，2020-08-31。[2020课程指定PDF](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)，§8.4–8.6，印刷页84–87，止于 §8.7 前。三节全部段落与两段代码均已译入；84页前部的 §8.3 及87页之后的 §8.7–8.8 不在本页范围。
- 已逐页查看PDF第84–87页，核对章节边界、代码、标点和页内衔接；本范围没有独立编号的图或表。原页图保存在本讲 `sources/`，不作为正文截图使用。
- 翻译是对原文的中文改编；编者的边界说明独立标注。引用的代码行号属于本版教材，可结合固定2020快照定位，不用于推断新版行号。课堂画面显示的 `install_trans(1)` 与参考快照 `install_trans(void)` 不同，不能把教材代码、参考快照和录课工作树当成完全相同的版本。
- 教材许可来自[官方教材仓库LICENSE](https://github.com/mit-pdos/xv6-riscv-book/blob/xv6-riscv/LICENSE)，复用项目已抓取的 `sources/xv6-book-license.txt`。许可文件的版权年份保留其原样，并不把教材正文改称2024版。
- 官方 `l-crash.txt` / `l-crash.pdf` 是课堂提纲与板书，用于核对课堂，不在本页重复翻译。原始获取时间、SHA-256及实际阅读范围见 `sources/manifest.json`。

<details><summary>教材原始版权声明与MIT许可全文</summary>

```text
The xv6 book sources are:

Copyright (c) 2006-2024 Russ Cox, Frans Kaashoek, and Robert Morris,
                        Massachusetts Institute of Technology

Permission is hereby granted, free of charge, to any person obtaining a copy of
this source and associated documentation files (the "Book"), to deal in the Book
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Book,
and to permit persons to whom the Book is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Book.

THE BOOK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE BOOK OR THE USE OR OTHER DEALINGS IN THE BOOK.
```

</details>
