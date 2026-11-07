---
source: Russ Cox、Frans Kaashoek、Robert Morris，xv6 book rev1（2020-08-31），第 4 章导言、§4.1–4.5、§4.7–4.8，印刷页 41–46、48
license: 教材 MIT 许可；完整版权及许可声明见页底
status: 分配范围全文中译，保留寄存器清单、硬件步骤及三道习题；已查看全部对应 PDF 原页；§4.6 由第 8 讲独占
---

# 第 4 章 · 陷入与系统调用

## 第 4 章导言：哪些事件会打断正常执行？

有三类事件会让 CPU 暂时放下通常的指令执行，强制转移到处理事件的特殊代码。第一类是**系统调用**：用户程序执行 `ecall` 指令，请求内核替它完成某项工作。第二类是**异常（exception）**：用户或内核中的某条指令执行了非法操作，例如除以零或使用无效虚拟地址。第三类是**设备中断（device interrupt）**：设备发出信号，表示需要处理，例如磁盘硬件完成一次读写请求。

> **编者校注：** “除以零”是原书用于说明异常的一般例子，不是 RISC-V 整数除法的实际陷入行为。RISC-V 的整数 `DIV`/`DIVU` 对零除数给出架构规定的结果，不产生除零异常。本章适合用无效地址、非法指令等说明 xv6 上的异常。

本书用 **trap（陷入）**统称这些情况。发生陷入时正在执行的代码，通常还需要继续运行，而且不应被迫知道中间发生过什么特殊事件。也就是说，我们通常希望陷入具有**透明性**；对被中断代码通常无法预料的设备中断，这一点尤其重要。

通常的处理顺序是：陷入把控制权交给内核；内核保存寄存器及其他状态，以便稍后恢复执行；内核运行适当的处理代码，例如系统调用实现或设备驱动；内核恢复已保存的状态并从陷入返回；原来的代码从暂停处继续运行。

xv6 内核处理所有陷入。系统调用自然应由内核处理。设备中断也应如此：隔离要求用户进程不能直接操作设备，而且只有内核掌握处理设备所需的状态。异常交给内核也很合理，因为初始 xv6 对用户空间异常的处理，就是终止出错的程序。

xv6 的陷入处理分成四个阶段：RISC-V CPU 执行硬件动作；汇编编写的“向量”入口为内核 C 代码准备环境；C 陷入处理程序决定如何处理；最后执行系统调用或设备驱动的服务例程。三类陷入的共性看起来允许用一条路径统一处理，但实践中，为**来自用户空间的陷入、来自内核空间的陷入、定时器中断**分别安排汇编入口和 C 处理程序更方便。

## §4.1 RISC-V 的陷入机制

每个 RISC-V CPU 都有一组控制寄存器。内核写这些寄存器，告诉 CPU 怎样处理陷入；内核也可以读取它们，了解已经发生的陷入。完整机制由 RISC-V 文档规定，`kernel/riscv.h` 包含 xv6 使用的相关定义。最重要的寄存器如下：

- **`stvec`**：内核把陷入处理程序的地址写入这里；发生陷入时，RISC-V 跳到这里处理。
- **`sepc`**：陷入发生时，RISC-V 把程序计数器保存到这里，因为接下来 `pc` 会被 `stvec` 覆盖。`sret`（从陷入返回）把 `sepc` 复制到 `pc`。内核可以写 `sepc`，控制 `sret` 返回的位置。
- **`scause`**：RISC-V 在这里放入一个数字，说明陷入原因。
- **`sscratch`**：内核在这里放置一个值，供陷入处理程序刚开始执行时使用。
- **`sstatus`**：其中的 `SIE` 位控制设备中断是否启用。内核清除 `SIE` 时，RISC-V 推迟设备中断，直到内核再次设置该位。`SPP` 位记录陷入来自用户模式还是监管者模式，也控制 `sret` 返回到哪种模式。

以上寄存器与监管者模式处理的陷入有关，用户模式不能读写。机器模式处理的陷入有一套对应控制寄存器；xv6 只在定时器中断这个特殊场景使用它们。多核芯片中的每个 CPU 都有自己的一套寄存器，因此多个 CPU 可以同时处理陷入。

需要强制发生陷入时，RISC-V 硬件执行下列步骤。原书在这里讨论的是除定时器中断特殊路径之外的情况：

1. 如果是设备中断，而 `sstatus.SIE` 为 0，就不执行后面的步骤。
2. 清除 `SIE`，关闭中断。
3. 把 `pc` 复制到 `sepc`。
4. 把当前模式——用户或监管者——保存到 `sstatus.SPP`。
5. 设置 `scause`，记录陷入原因。
6. 把当前模式设置为监管者模式。
7. 把 `stvec` 复制到 `pc`。
8. 开始从新的 `pc` 执行。

> **编者补充：** 这是教材的简化步骤表。与本课最后的问答相关，陷入还把原 `SIE` 保存到 `SPIE`；`sret` 将 `SPIE` 恢复到 `SIE`。`SIE` 对 S 态中断的全局屏蔽规则，不能简单套成“在 U 态时 `SIE=0` 就屏蔽所有送往 S 态的中断”：处于较低特权级时，更高特权级中断有不同的使能规则。本课 xv6 没有用 UIE 来完成这里的返回过程。

注意，CPU **没有**切换到内核页表，**没有**切换到内核栈，也**没有**保存除 `pc` 以外的通用寄存器。内核软件必须自己完成这些任务。让 CPU 在陷入时只做少量工作的一个原因，是给软件保留灵活性；例如，有些操作系统在某些情况下不需要切换页表，就可以省去这项开销。

能不能进一步简化硬件步骤？假设 CPU 不切换程序计数器，那么陷入就可能在仍执行用户指令时进入监管者模式。那些用户指令可以破坏用户与内核的隔离，例如修改 `satp`，让它指向允许访问全部物理内存的页表。因此，CPU 必须切换到**内核指定的指令地址**，也就是 `stvec` 所指定的位置。

## §4.2 来自用户空间的陷入

用户程序执行系统调用指令 `ecall`、执行非法操作，或遭遇设备中断，都可能在用户空间执行期间触发陷入。总体路径是先执行 `kernel/trampoline.S` 中的 `uservec`，再执行 `kernel/trap.c` 中的 `usertrap`；返回时先执行 `usertrapret`，再执行 `userret`。

来自用户代码的陷入，比来自内核的陷入更难处理：此时 `satp` 指向用户页表，这张表没有映射内核主体；栈指针也可能无效，甚至是恶意构造的值。

### 让第一条内核指令有处可去

RISC-V 硬件在陷入时不切换页表，因此用户页表必须包含 `uservec` 的映射，也就是 `stvec` 指向的那些陷入入口指令。`uservec` 要把 `satp` 改为内核页表；为了在切换后继续执行，`uservec` 在内核页表与用户页表中的映射地址必须相同。

xv6 使用包含 `uservec` 的 **trampoline 页**满足这些条件。它把这个页映射到内核页表和每张用户页表的同一虚拟地址 `TRAMPOLINE`。第 2 章图 2.3 与第 3 章图 3.3 已经展示这一布局。Trampoline 的内容由 `trampoline.S` 定义；执行用户代码时，`stvec` 指向 `uservec`。

> 图像定位：本章没有新增编号图表。上述原图分别保留在[第 3 讲课程资料 §2.5](#/c/mit-6.s081-2020/lec/lec03?v=materials)与[第 4 讲课程资料](#/c/mit-6.s081-2020/lec/lec04?v=materials)，本页不重复复制。

### 获得第一个可用寄存器

`uservec` 开始时，通用寄存器里装着被打断代码的值。但是，`uservec` 要设置 `satp`，还要形成保存寄存器所用的内存地址，因此必须能够修改某些寄存器。RISC-V 提供 `sscratch` 帮助解决这个问题。`uservec` 开头的 `csrrw` 指令交换 `a0` 与 `sscratch` 的内容：用户的 `a0` 已被保存，`uservec` 得到了一个可以使用的寄存器；现在 `a0` 装着内核预先放入 `sscratch` 的值。

接下来要保存用户寄存器。内核在进入用户空间之前，就把 `sscratch` 设置为指向**每进程的 trapframe（陷入帧）**。这个结构除了其他用途，还留有保存用户寄存器的空间，定义在 `kernel/proc.h`。

由于 `satp` 仍指向用户页表，trapframe 必须映射在用户地址空间里。xv6 创建每个进程时分配一个 trapframe 页，并总把它映射到 `TRAMPOLINE` 正下方的用户虚拟地址 `TRAPFRAME`。进程的 `p->trapframe` 也指向同一页，但保存的是物理地址，内核可以通过自己的直接映射使用它。

所以，交换 `a0` 与 `sscratch` 以后，`a0` 指向当前进程的 trapframe。`uservec` 把用户寄存器保存进去，也从 `sscratch` 读取原用户 `a0` 并保存。

> **编者校注：** 原书与课堂常用“全部 32 个寄存器”作概括。RISC-V 有 32 个整数寄存器，但 `x0` 恒为零，无须保存；固定源码的 trapframe 保存 31 个可变整数寄存器，另有 `epc` 等字段。

Trapframe 还保存当前进程内核栈的地址、当前 CPU 的 hartid、`usertrap` 地址，以及内核页表信息。`uservec` 取出这些值，切换 `satp` 到内核页表，并进入 `usertrap`。

### C 代码判断并处理原因

`usertrap` 负责判断陷入原因、处理陷入，再安排返回。首先，它修改 `stvec`，使内核执行期间发生的陷入转交 `kernelvec`。它还保存 `sepc`，也就是已保存的用户程序计数器；这是因为 `usertrap` 中可能发生进程切换，导致硬件中的 `sepc` 被覆盖。

如果原因是系统调用，就调用 `syscall`；如果是设备中断，就调用 `devintr`；否则是异常，内核终止出错的进程。系统调用路径还把保存的用户 `pc` 加 4，因为发生系统调用时，RISC-V 留下的地址仍指向 `ecall` 指令本身。处理结束时，`usertrap` 检查进程是否已被终止，以及是否应让出 CPU——若本次是定时器中断，就需要让其他进程获得运行机会。

### 返回用户空间

返回的第一步是调用 `usertrapret`。它设置 RISC-V 控制寄存器，为下一次来自用户空间的陷入做准备：让 `stvec` 重新指向 `uservec`；准备 `uservec` 将要使用的 trapframe 字段；把 `sepc` 设置为此前保存的用户程序计数器。最后，`usertrapret` 调用同时映射在两张页表中的 trampoline 页上的 `userret`，因为 `userret` 的汇编代码即将切换页表。

**原书此处的参数叙述是：把用户页表指针放入 `a0`，把 `TRAPFRAME` 放入 `a1`。** `userret` 切换 `satp` 到用户页表。用户页表映射了 trampoline 与 trapframe，而没有映射内核其他内容；trampoline 在两张页表中的虚拟地址相同，使切换 `satp` 后仍能继续执行。

> **编者校注——rev1 p.44 参数次序与源码相反：** 已核对 PDF 原页，原书确实写为“页表在 a0、TRAPFRAME 在 a1”，不是文本抽取错误。固定参考提交 `e23d53f27f6e187732a92a2b4705639d1c260f05` 的 `kernel/trap.c:128` 调用的是 `fn(TRAPFRAME, satp)`；`kernel/trampoline.S:89–96` 明写 `userret(TRAPFRAME, pagetable)`，并用 `csrw satp, a1` 切换。所以阅读该源码时，应采用 **`a0 = TRAPFRAME`，`a1 = MAKE_SATP(p->pagetable)`**。课堂 45:00–48:00、75:00–78:00 的讲解也采用这个次序。另外，原书这里说“使 uservec 继续执行”，按返回路径上下文应为 **userret**。这些差异单独标出，不暗改成原书没有写过的话。

`userret` 把 trapframe 中保存的用户 `a0` 复制到 `sscratch`，为稍后的交换做准备。从此时起，它能依靠的只有寄存器和 trapframe 的内容。接着，它从 trapframe 恢复用户寄存器，最后交换 `a0` 与 `sscratch`，既恢复用户的 `a0`，又把 `TRAPFRAME` 留给下一次陷入；最后执行 `sret` 返回用户空间。

## §4.3 代码：调用系统调用

第 2 章最后介绍了 `user/initcode.S` 如何发起 `exec` 系统调用。现在来追踪，这个用户调用怎样抵达内核中的 `exec` 实现。

用户代码把 `exec` 的参数放进 `a0` 和 `a1`，把系统调用号放进 `a7`。系统调用号对应 `kernel/syscall.c` 的函数指针数组 `syscalls` 中的表项。`ecall` 指令陷入内核，依次执行前面介绍的 `uservec`、`usertrap` 和 `syscall`。

`syscall` 从 trapframe 保存的 `a7` 取出系统调用号，用它索引 `syscalls`。第一个系统调用的 `a7` 是 `SYS_exec`，因此最终调用 `sys_exec`。

系统调用实现函数返回后，`syscall` 把返回值记录到 `p->trapframe->a0`。这样，用户空间调用就会得到这个返回值，因为 RISC-V 的 C 调用约定使用 `a0` 传递返回值。系统调用通常以负数表示错误，以零或正数表示成功。系统调用号无效时，`syscall` 打印错误并返回 -1。

> **编者校注：** 原书用 `exec()` 解释通用返回机制，但 `exec` 成功时已经替换用户映像，用户执行不会回到原来的 `exec` 调用点。这里的“返回值写入 a0”描述内核分派及返回寄存器机制，不改变第 1 章“exec 仅失败才返回原调用者”的接口语义。

## §4.4 代码：系统调用参数

内核里的系统调用实现必须找到用户传来的参数。用户代码调用系统调用封装函数，因此参数最初位于 RISC-V C 调用约定规定的地方，也就是寄存器中。陷入入口把用户寄存器保存到当前进程的 trapframe，内核便可以在那里找到参数。

`argint`、`argaddr` 和 `argfd` 分别以整数、指针或文件描述符的形式取得第 n 个系统调用参数。它们通过 `argraw` 取得对应的已保存用户寄存器。

> **编者补充：** 固定源码中，`argfd` 位于 `kernel/sysfile.c`，经 `argint` 间接调用 `argraw`；它还检查 fd 范围和表项。`argaddr` 只是取出地址值，并不在这里证明地址可以安全访问，实际内存传输函数负责后续检查。

有些系统调用用指针传参，内核必须通过这些指针读写用户内存。例如，`exec` 会把一个指针数组传给内核，数组元素指向用户空间中的参数字符串。这带来两个困难：

1. 用户程序可能出错或有意作恶，传入无效指针，或者试图诱骗内核访问内核内存，而不是用户内存。
2. xv6 内核页表与用户页表的映射不同，内核不能直接对用户传入的地址使用普通 load/store。

内核因此实现了安全地向用户地址或从用户地址传递数据的函数。`fetchstr` 是一个例子：`exec` 等文件系统调用用它取得用户空间中的文件名字符串；真正复杂的工作由它调用的 `copyinstr` 完成。

`copyinstr(pagetable, dst, srcva, max)` 从用户页表 `pagetable` 中的虚拟地址 `srcva` 复制字符串到 `dst`，最多复制 `max` 个字节。它通过 `walkaddr`——后者又调用 `walk`——在软件中遍历页表，确定对应物理页地址 `pa0`。内核把物理 RAM 直接映射到数值相同的内核虚拟地址，因此可以从该物理页对应的内核地址向 `dst` 复制字符串字节。

`walkaddr` 检查用户提供的虚拟地址是否属于进程的用户地址空间，防止程序诱骗内核读取其他内存。类似地，`copyout` 从内核向用户指定的地址复制数据。

> **编者补充：** `pa0` 是页起始地址；实际复制还要加上 `srcva` 的页内偏移，并在跨页时重新查表。固定源码的 `walkaddr` 检查 `MAXVA`、`PTE_V` 和 `PTE_U`。不要把“拿到一个 uint64 地址”与“验证并读取该地址”混为一件事。

## §4.5 来自内核空间的陷入

xv6 根据 CPU 正在执行用户代码还是内核代码，以不同方式配置陷入寄存器。执行内核代码时，`stvec` 指向 `kernel/kernelvec.S` 中的 `kernelvec`。因为已经位于内核，`kernelvec` 可以依赖两件事：`satp` 已设置为内核页表，栈指针指向有效的内核栈。它保存寄存器，使被打断的代码稍后能够不受干扰地继续执行。

`kernelvec` 把寄存器保存在**被打断的内核线程自己的栈**上，因为这些寄存器值属于该线程。如果陷入导致切换到其他线程，这尤其重要：执行可能沿另一个线程的栈继续并从那里的陷入返回，而原线程的寄存器仍安全地留在自己的栈上。

保存寄存器后，`kernelvec` 跳到 `kerneltrap`。后者处理两类陷入：设备中断和异常。它调用 `devintr` 检查并处理设备中断。如果不是设备中断，那就是异常；在初始 xv6 内核中，异常总是致命错误，内核调用 `panic` 并停止执行。

如果 `kerneltrap` 是由定时器中断触发，而且当前运行的是某个进程的内核线程，而非调度器线程，它就调用 `yield`，让其他线程有机会运行。稍后某个线程让出 CPU，我们的线程及其 `kerneltrap` 才会继续。第 7 章解释 `yield` 内部的切换过程。

处理完以后，`kerneltrap` 要返回被打断的代码。由于 `yield` 可能改变硬件中的 `sepc` 和 `sstatus` 保存的先前模式，`kerneltrap` 在开始时把它们保存下来，此时重新恢复这些控制寄存器，再返回 `kernelvec`。后者从栈恢复寄存器并执行 `sret`，把 `sepc` 复制到 `pc`，继续执行原来的内核代码。值得仔细推演的是：当 `kerneltrap` 曾因定时器中断调用 `yield`，最终的陷入返回怎样发生。

xv6 从用户空间进入内核时，会在 `usertrap` 中把 `stvec` 设置为 `kernelvec`。进入内核之后、完成这一设置之前，有一个短暂窗口：CPU 已在执行内核代码，但 `stvec` 仍指向 `uservec`。此时必须禁用设备中断。RISC-V 在开始处理陷入时会关闭中断，xv6 则等设置好 `stvec` 以后才重新启用。

## §4.6 阅读位置

“缺页异常”按课程分工单独放在[第 8 讲课程资料](#/c/mit-6.s081-2020/lec/lec08?v=materials)。这里直接接续 §4.7，不重复翻译该节。

## §4.7 真实世界

如果把内核内存以适当的 PTE 权限映射到每个进程的用户页表里，就可以消除特殊 trampoline 页的需要，也不必在从用户空间陷入内核时切换页表。进一步说，当前进程的用户内存仍然映射着，内核中的系统调用实现便可以直接解引用用户指针。

许多操作系统曾用这些办法提高效率。xv6 没有采用它们，是为了减少内核意外使用用户指针而造成安全错误的机会，也为了减少确保用户与内核虚拟地址不重叠所需的复杂性。

## §4.8 习题

1. `copyin` 和 `copyinstr` 在软件中遍历用户页表。设置内核页表，让它也映射用户程序，使这两个函数能够用 `memcpy` 将系统调用参数复制进内核空间，依靠硬件完成页表遍历。
2. 实现惰性内存分配（lazy memory allocation）。
3. 实现写时复制的 `fork`（COW fork）。

> **编者说明：** 三题均按原章保留；第 2、3 题需要 §4.6 的背景。教材习题不等于本讲发布的 traps 实验全部任务，实验具体要求见[Lab traps](#/c/mit-6.s081-2020/lab/traps?v=zh)。

## 来源、版本与教材许可

- **B4：** Russ Cox、Frans Kaashoek、Robert Morris，*xv6: a simple, Unix-like teaching operating system*，2020-08-31 rev1，[官方 PDF](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)。本页翻译第 4 章导言、§4.1–4.5、§4.7–4.8；已读文本并实际查看印刷页 41、42、43、44、45、46、48 的原页渲染。本范围没有新增编号图表，保留寄存器项目、八步硬件序列及三道习题。
- **C2020：** [固定参考提交](https://github.com/mit-pdos/xv6-riscv/tree/e23d53f27f6e187732a92a2b4705639d1c260f05)，重点核对 `kernel/trampoline.S`、`kernel/trap.c`、`kernel/riscv.h`、`kernel/proc.h`、`kernel/syscall.c`、`kernel/sysfile.c`、`kernel/vm.c`。这是上游 2020 快照，**不声称是录课工作树或任一实验分支**。教材行号不作为其他版本的定位依据。
- **修改说明：** 中文翻译与编者校注；rev1 `userret` 参数反序、返回路径函数名、`exec` 成功不返回、RISC-V 除零及中断位的边界均显式区分。源文件与摘要见本讲 `sources/manifest.json`。
- **R-S / R-M（编者校核）：** RISC-V International，[Supervisor-Level ISA](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html) 的 `sstatus`、`SUM` 和中断条件，以及 [M 扩展 Division Operations](https://docs.riscv.org/reference/isa/v20260120/unpriv/m-st-ext.html)。使用明确标识的 20260120 文档核对基础规则，不将其冒充 2020 指定阅读，不把较新扩展加入本课 xv6。
- **许可依据：** [教材仓库 LICENSE](https://github.com/mit-pdos/xv6-riscv-book/blob/xv6-riscv/LICENSE)，本地复用 `sources/xv6-book-license.txt`。下列版权年份保留实际取得的许可文本，不把它改写成 2020 原页的版权年份；教材许可不延伸到视频。

<details><summary>教材 MIT 版权及许可全文</summary>

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
