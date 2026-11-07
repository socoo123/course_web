---
source: Russ Cox、Frans Kaashoek、Robert Morris，xv6 book rev1（2020-08-31），第 5 章，印刷页 49–54
license: 教材 MIT 许可；署名与许可全文见页底
status: 第 5 章导言及 §5.1–5.6 全文中文译文，含两道习题；本章无图表，p.54 为空白页；代码校注另行标记
---

# 第 5 章 · 中断与设备驱动

## 第 5 章导言

**驱动程序**是操作系统中管理某个特定设备的代码：它配置设备硬件，要求设备执行操作，处理由此产生的中断，并与可能正在等待该设备 I/O 的进程交互。驱动程序不好写，因为它与自己管理的设备并发执行。此外，驱动程序必须理解设备的硬件接口，而接口可能很复杂，文档也可能不够清楚。

需要操作系统处理的设备，通常可以配置为产生**中断**；中断是 trap 的一种。内核的 trap 处理代码识别出设备发来了中断，便调用该驱动的中断处理程序。在 xv6 中，这一步分派发生在 `devintr`（`kernel/trap.c:177`）。

许多设备驱动的代码在两种上下文中执行：**上半部**运行在某个进程的内核线程中，**下半部**在发生中断时执行。上半部由 `read`、`write` 等希望设备进行 I/O 的系统调用进入。它可能要求硬件开始一个操作，例如让磁盘读取一个块，然后等待操作完成。设备最终完成操作并产生中断。作为下半部的驱动中断处理程序查明完成的是哪个操作，在适当时唤醒等待进程，并要求硬件开始下一个等待中的操作。

## §5.1 代码：控制台输入

控制台驱动 `console.c` 是驱动结构的一个简单例子。它通过连接到 RISC-V 的 UART 串口硬件接收人输入的字符，一次积累一行，并处理退格、Control-U 等特殊输入字符。Shell 等用户进程通过 `read` 系统调用从控制台获取输入行。在 QEMU 中给 xv6 输入内容时，按键经过 QEMU 模拟的 UART 硬件交给 xv6。

驱动与之通信的 UART 硬件，是 QEMU 模拟的 16550 芯片 [原书参考文献 11]。在真实计算机上，16550 管理一条连接终端或另一台计算机的 RS232 串行链路；在 QEMU 环境中，它连接的是你的键盘和显示器。

在软件看来，UART 硬件表现为一组**内存映射控制寄存器**。也就是说，RISC-V 硬件把一些物理地址连接到 UART 设备；对这些地址执行 load、store，是在与设备硬件交互，而非访问 RAM。UART 的内存映射地址从 `0x10000000`，即 `UART0` 开始（`kernel/memlayout.h:21`）。UART 只有少数几个控制寄存器，每个宽一字节；它们相对于 `UART0` 的偏移定义在 `kernel/uart.c:22` 附近。

例如，`LSR` 寄存器中的位指出是否有输入字符等待软件读取；如果有，就可以从 `RHR` 寄存器读取。每读取一次，UART 硬件都会从内部保存待处理字符的 FIFO 中删除该字符；FIFO 为空时，硬件清除 `LSR` 中的“就绪”位。UART 的发送硬件与接收硬件大体独立：软件向 `THR` 写入一个字节，UART 就发送该字节。

xv6 的 `main` 调用 `consoleinit`（`kernel/console.c:184`）初始化 UART。初始化代码把 UART 配置为：每接收一个输入字节就产生接收中断，每完成一个输出字节的发送就产生发送完成中断（`kernel/uart.c:53`）。

xv6 shell 通过 `init.c` 打开的文件描述符读取控制台（`user/init.c:19`）。`read` 系统调用沿内核中的调用链最终到达 `consoleread`（`kernel/console.c:82`）。`consoleread` 等待输入通过中断到达并存入 `cons.buf`，把输入复制到用户空间，并在完整的一行到达后返回用户进程。如果用户还没有输入完整一行，正在读取的进程便在 `sleep` 调用中等待（`kernel/console.c:98`）；第 7 章会解释 `sleep` 的细节。

用户输入一个字符时，UART 硬件请求 RISC-V 产生中断，从而进入 xv6 的 trap 处理程序。处理程序调用 `devintr`（`kernel/trap.c:177`）；`devintr` 查看 RISC-V 的 `scause` 寄存器，发现中断来自外部设备，然后询问名为 PLIC 的硬件单元 [原书参考文献 1]：究竟是哪个设备发出的中断（`kernel/trap.c:186`）。如果是 UART，`devintr` 就调用 `uartintr`。

`uartintr`（`kernel/uart.c:180`）读取 UART 硬件中当前所有等待处理的输入字符，把它们交给 `consoleintr`（`kernel/console.c:138`）。它不会等待未来的字符，因为后续输入会再次产生中断。`consoleintr` 的工作是把字符积累到 `cons.buf`，直到收齐一行。它会特殊处理退格及另外几个字符。换行到达时，`consoleintr` 唤醒等待中的 `consoleread`，如果确实有这样的等待者。

`consoleread` 被唤醒后，就能在 `cons.buf` 中看到完整的一行；它把这行复制到用户空间，然后通过系统调用返回机制回到用户空间。

> **编者校注：行缓冲的边界。** 上面是原书对通常路径的叙述。固定 2020 源码还会在 Control-D 或输入缓冲区填满时提交输入并唤醒读者；`read` 的长度参数也限制本次复制的字节数，因此不是任何一次 `read` 都必定返回完整一行。`cons.e` 是编辑位置，`cons.w` 是已提交位置，`cons.r` 是读位置。普通字符可以先回显并写入编辑区，但尚未供等待中的读者读取。

## §5.2 代码：控制台输出

对连接到控制台的文件描述符调用 `write`，最终会到达 `uartputc`（`kernel/uart.c:87`）。设备驱动维护一个输出缓冲区 `uart_tx_buf`，因此写入进程无需等待 UART 真正完成发送。`uartputc` 把每个字符追加到缓冲区，调用 `uartstart`，让尚未开始发送的设备开始发送，然后返回。只有缓冲区已经满了时，`uartputc` 才会等待。

UART 每完成一个字节的发送，就产生中断。`uartintr` 调用 `uartstart`；后者检查设备确实已经完成发送，再把缓冲区中的下一个输出字符交给设备。因此，进程向控制台写入多个字节时，通常第一个字节由 `uartputc` 调用 `uartstart` 发出；剩余缓冲字节则在发送完成中断陆续到来时，由 `uartintr` 调用 `uartstart` 继续发出。

值得注意的一般模式是：**用缓冲和中断，把设备活动与进程活动解耦。** 即使当前没有进程等待读取，控制台驱动仍可处理输入；以后发起的 `read` 会看到这些输入。同样，进程可以提交输出，而无需等待设备完成。进程执行与设备 I/O 因而能够并发进行，提高性能。当设备很慢，例如 UART，或需要及时响应，例如回显刚输入的字符时，这种解耦尤其重要。这种思想有时称为 **I/O 并发**。

> **编者校注：发送“完成”的精度。** 本版本代码检查的是 `LSR_TX_IDLE`，即 `LSR` 的位 5，含义是发送保持寄存器可以接收下一个字符。原书用“发送完成”解释驱动的推进过程；不应据此断言上一字节的最后一位已经在物理线路上发送完毕。软件缓冲区、设备 FIFO／保持寄存器、实际串行线路是不同层次。

## §5.3 驱动中的并发

你可能已经注意到，`consoleread` 和 `consoleintr` 都调用了 `acquire`。这些调用获取一把锁，保护控制台驱动的数据结构不被并发访问破坏。这里有三种并发危险：

1. 不同 CPU 上的两个进程可能同时调用 `consoleread`。
2. 某个 CPU 已在执行 `consoleread` 时，硬件又要求它接收控制台中断，准确说是 UART 中断。
3. `consoleread` 正在一个 CPU 上执行时，硬件可能把控制台中断交给另一个 CPU。

第 6 章会研究锁如何帮助处理这些情况。

驱动还必须留意另一种并发问题：一个进程正在等待设备输入，而报告输入到达的中断发生时，CPU 上可能正在运行另一个进程，甚至没有进程运行。因此，中断处理程序不能以它所打断的进程或代码来推断这次 I/O 的归属。例如，中断处理程序不能安全地拿“当前进程”的页表调用 `copyout`。中断处理程序通常只做少量工作，例如把输入数据复制到缓冲区，再唤醒上半部代码完成其余工作。

## §5.4 定时器中断

xv6 使用定时器中断维护时钟，并在计算密集型进程之间切换；`usertrap` 和 `kerneltrap` 中调用 `yield` 会引发这种切换。定时器中断来自连接到每个 RISC-V CPU 的时钟硬件。xv6 对时钟硬件进行编程，让它周期性地中断每个 CPU。

原书这里使用的 RISC-V 平台要求在 machine 模式，而非 supervisor 模式，接收定时器中断。RISC-V 的 machine 模式不使用分页，并有另一组控制寄存器；因此，在 machine 模式中运行普通 xv6 内核代码并不实际。为此，xv6 对定时器中断采用了与前述 trap 机制分开的处理路径。

在进入 `main` 之前，`start.c` 中运行于 machine 模式的代码设置定时器中断的接收方式（`kernel/start.c:57`）。其中一部分工作，是编程 CLINT（core-local interruptor，核本地中断器），让它在一段延迟后产生中断。另一部分工作，是建立一块类似 trapframe 的 scratch 暂存区，以帮助定时器中断处理程序保存寄存器及 CLINT 寄存器地址。最后，`start` 把 `mtvec` 设置为 `timervec` 并启用定时器中断。

用户代码或内核代码执行到任何位置，都可能发生定时器中断；内核无法在关键操作期间靠通常的 supervisor 中断屏蔽机制禁用这种 machine 定时器中断。因此，定时器中断处理程序必须保证它做的工作不会干扰被中断的内核代码。基本策略是请求 RISC-V 产生一次“软件中断”，随后立即返回。RISC-V 使用通常的 trap 机制把软件中断交给内核，并允许内核禁用它。由定时器中断产生的软件中断，其处理代码位于 `devintr`（`kernel/trap.c:204`）。

machine 模式的定时器中断入口是 `timervec`（`kernel/kernelvec.S:93`）。它把少量寄存器保存到 `start` 准备好的 scratch 区，告诉 CLINT 下一次应在何时产生定时器中断，请求 RISC-V 产生软件中断，恢复寄存器，然后返回。定时器中断处理程序中没有 C 代码。

> **编者校注：版本范围。** 本节描述 rev1 与课程 2020 平台的 CLINT→M 模式→S 模式软件中断实现，不是断言所有后来 RISC-V 平台都必须采用相同路径。固定快照 `timervec` 通过设置 `sip.SSIP` 发出 S 模式软件中断；`devintr` 清除该位，仅在 CPU 0 上增加全局 `ticks`，并返回 2，供上层判断是否让出 CPU。

## §5.5 现实世界

xv6 既允许在用户程序执行期间发生设备和定时器中断，也允许在内核执行期间发生这些中断。定时器中断处理程序会通过调用 `yield` 强制切换线程，即使中断发生时正在执行内核代码。如果内核线程有时会长时间计算、不返回用户空间，能够公平地在这些线程之间分配 CPU 时间片就很有用。不过，内核代码必须考虑自己可能因定时器中断而暂停，稍后又在另一个 CPU 上恢复；这也是 xv6 复杂性的一部分。如果设备中断与定时器中断只在执行用户代码时发生，内核就可以简化一些。

完整支持一台典型计算机上的全部设备，是一项很大的工作：设备很多，功能众多，设备与驱动之间的协议又可能复杂且文档欠佳。在许多操作系统中，驱动程序的代码量比核心内核还大。

UART 驱动通过读取 UART 控制寄存器，一次取一个字节。这种方式称为 **programmed I/O，程序控制 I/O**，因为数据移动由软件驱动。程序控制 I/O 很简单，但用于高数据速率设备时太慢。需要高速移动大量数据的设备，通常使用 **DMA（direct memory access，直接内存访问）**。DMA 设备硬件直接把输入数据写入 RAM，也直接从 RAM 读取输出数据。现代磁盘和网络设备使用 DMA。DMA 设备驱动先在 RAM 中准备好数据，再向某个控制寄存器写入一次，通知设备处理准备好的数据。

设备在不可预测、而且不太频繁的时刻需要处理时，中断很合适。但中断的 CPU 开销很高。因此，高速网络设备、磁盘控制器会使用减少中断需求的技巧。一种技巧是为一整批输入或输出请求只产生一次中断；另一种是让驱动完全禁用中断，转而周期性检查设备是否需要处理。这称为**轮询**。设备执行操作非常快时，轮询是合理的；如果设备大部分时间都空闲，轮询就浪费 CPU。有些驱动会根据当前设备负载，在轮询与中断之间动态切换。

UART 驱动先把输入数据复制到内核缓冲区，再复制到用户空间。低数据速率时这样做合理；但对高速产生或消耗数据的设备，这两次复制可能显著降低性能。有些操作系统能够直接在用户空间缓冲区与设备硬件之间移动数据，通常借助 DMA。

## §5.6 习题

1. 修改 `uart.c`，使它完全不使用中断。你可能还需要修改 `console.c`。
2. 为一块以太网卡添加驱动程序。

## 引用、版本与许可

- 作者：Russ Cox、Frans Kaashoek、Robert Morris，Massachusetts Institute of Technology。
- 教材：[xv6: a simple, Unix-like teaching operating system，rev1，2020-08-31](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)，第 5 章，印刷页 49–53；p.54 为空白。已读全文并查看 pp.49–54 原页，本章没有图表。
- 原书文献 [1] 指 RISC-V 特权体系结构说明，[11] 指 16550 UART 文档；本页不把这些外部文档当作已独立全文核验的阅读物。
- 行号沿用教材；编者校注核对固定提交 [`e23d53f27f6e187732a92a2b4705639d1c260f05`](https://github.com/mit-pdos/xv6-riscv/tree/e23d53f27f6e187732a92a2b4705639d1c260f05)。该参考快照不是对录课工作树或实验分支的认定。
- 修改：中文翻译、术语强调、段落排版及明确标记的技术校注；未运行本章练习。许可复用共享存档 `sources/xv6-book-license.txt`，其版权年份范围为当前上游声明，不代表教材改用了新版。

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
