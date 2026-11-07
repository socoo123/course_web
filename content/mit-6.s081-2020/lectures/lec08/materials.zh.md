---
source: Russ Cox、Frans Kaashoek、Robert Morris，xv6 book RISC-V rev1（2020-08-31），§4.6 Page-fault exceptions
license: 教材 MIT 许可，完整版权与许可声明附于页底
status: §4.6 全节中文译文；已核对印刷页 46–48，正文实际在 46–47 页，48 页从 §4.7 开始；本节无图表
---

# 第 8 讲 · 课程资料

## §4.6 缺页异常

xv6 对异常的响应相当单调：如果异常发生在用户空间，内核就终止产生异常的进程；如果异常发生在内核中，内核就 panic。真实操作系统经常采取更有意思的应对办法。

例如，许多内核使用缺页异常实现**写时复制（copy-on-write，COW）fork**。要解释它，先考虑第 3 章介绍的 xv6 `fork`：fork 调用 `uvmcopy`（原书定位 `kernel/vm.c:309`），为子进程分配物理内存，并把父进程的内存复制进去，使子进程拥有与父进程相同的内存内容。如果父子可以共享父进程的物理内存，效率会更高。然而，直接共享并不可行，因为父子对共享栈和堆的写入会干扰彼此的执行。

借助由缺页异常驱动的写时复制 fork，父子进程能够安全地共享物理内存。当 CPU 无法把虚拟地址转换成物理地址时，会产生缺页异常。RISC-V 有三类不同的缺页异常：**load page fault**，即 load 指令的虚拟地址无法转换；**store page fault**，即 store 指令的虚拟地址无法转换；以及 **instruction page fault**，即指令地址无法转换。`scause` 寄存器中的值说明异常类型，`stval` 寄存器保存无法完成转换的地址。

> **编者校注：**这里的“无法转换”也包括访问权限不满足的情况，并不只指 PTE 不存在或有效位为零；下面的只读页写入就是一个例子。

COW fork 的基本方案是，让父子最初共享全部物理页，但把这些页映射为只读。这样，父或子执行 store 指令时，RISC-V CPU 就会产生缺页异常。内核响应异常时，复制包含故障地址的那个页；把一份副本以可读写方式映射到子进程地址空间，另一份以可读写方式映射到父进程地址空间。更新页表后，内核从导致异常的那条指令恢复故障进程。由于相关 PTE 已经更新为允许写入，该指令现在就能执行成功，不再引发同样的异常。

> **编者校注：**原书这里采用只有父子两个共享者的基本模型。若同一物理页还被其他孩子或后代共享，不能无条件把旧页映射恢复为可写；需要结合引用计数保证写入者拥有独立副本，或确认它是唯一剩余使用者。原来就不允许写的页也不能因发生写异常而被随意放开权限。

这个 COW 方案很适合 fork，因为子进程经常紧接着调用 `exec`，以新的地址空间替换原有地址空间。在这种常见情况下，子进程只会经历少数几次缺页异常，内核就能避免完整复制整个地址空间。而且 COW fork 对应用是透明的：应用不需要任何修改，就能从中获益。

页表与缺页异常的组合，还带来了 COW fork 之外的许多有趣可能。另一项广泛使用的功能叫作**惰性分配（lazy allocation）**，分成两部分。第一，应用调用 `sbrk` 时，内核扩展地址空间，但把新增地址在页表中标为无效。第二，当其中某个新地址发生缺页异常时，内核分配物理内存并把它映射到页表。应用经常申请超过实际需要的内存，因此惰性分配能够获益：内核只在应用真正使用内存时才分配它。和 COW fork 一样，这项功能也可以对应用透明地实现。

另一项广泛使用缺页异常的功能是**从磁盘换页（paging from disk）**。如果应用所需内存超过可用的物理 RAM，内核可以换出一些页：把它们写入磁盘等存储设备，再将相应 PTE 标为无效。如果应用读取或写入已换出的页，CPU 就会发生缺页异常。内核随后检查故障地址；如果该地址属于一个保存在磁盘上的页，内核便分配一页物理内存，把该页从磁盘读入，将 PTE 更新为有效并指向这块内存，然后恢复应用。为了给这页腾出空间，内核可能还得换出另一页。这项功能不要求修改应用；如果应用具有访问局部性，也就是在某一时段只使用全部内存的一部分，它就能取得良好效果。

其他结合分页与缺页异常的功能，还包括自动扩展栈，以及内存映射文件。

## 继续阅读

- 第 4 章的 trap 入口、用户／内核陷入、系统调用参数、真实系统讨论与章末习题，见[第 6 讲课程资料](#/c/mit-6.s081-2020/lec/lec06?v=materials)。本页到 §4.7 标题之前结束。
- 零页、引用计数、A/D 位与 mmap 的课堂推导、现场 lazy 修改及问答，见[本讲中文译稿](#/c/mit-6.s081-2020/lec/lec08?v=draft)；它们不是本节教材中额外出现的段落。
- 把这节的惰性分配思想落实到代码，见 [lazy 实验说明](#/c/mit-6.s081-2020/lab/lazy?v=zh)与[实验指导](#/c/mit-6.s081-2020/lab/lazy?v=guide)。

## 来源、版本与许可

原书：Russ Cox、Frans Kaashoek、Robert Morris，*xv6: a simple, Unix-like teaching operating system*，RISC-V rev1，2020-08-31。[官方 PDF](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)。本页完整翻译 §4.6，保留原书论述顺序；为可读性加粗术语，技术限制单独标为编者校注。

已阅读本节全文，并实际查看印刷页 46、47、48。§4.6 从第 46 页下部开始，第 47 页结束，第 48 页顶部即 §4.7；所以任务所写的“46–48、止于 §4.7 之前”实际对应第 46–47 页。本节没有需要重制的原图、表格或单独练习。其余第 4 章归第 6 讲。

教材与视频许可分别处理：教材依共享归档的上游 MIT 许可翻译，不能用课程网站的 CC 许可替代教材声明。下面完整保留共享许可快照中的年份（2006–2024），它不表示把教材正文换成 2024 版。

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

[上游许可位置](https://github.com/mit-pdos/xv6-riscv-book/blob/xv6-riscv/LICENSE)。本地来源与校对范围记录于 `sources/manifest.json`、`sources/coverage.json`。
