---
source: Russ Cox、Frans Kaashoek、Robert Morris，xv6: a simple, Unix-like teaching operating system，2020-08-31 rev1，§7.5–7.10，印刷页 71–80
license: xv6 教材 MIT 许可；版权声明及许可全文见页底
status: 六节正文、四版信号量代码、脚注与全部 8 道习题已译；已查看 PDF 71–80 页；本范围无编号图表
---

# 第 13 讲 · 等待、唤醒与进程终止

## §7.5 睡眠与唤醒

调度和锁帮助一个进程不必关心另一个进程的存在，但到目前为止，我们还没有帮助进程有意交互的抽象。人们为此发明了许多机制。xv6 使用其中一种，称为 **sleep 与 wakeup**：一个进程可以睡眠，等待某个事件；另一个进程在事件发生后唤醒它。sleep 与 wakeup 常被称为**顺序协调**（sequence coordination）或**条件同步**（conditional synchronization）机制。

用信号量（semaphore，原书引用 [4]）协调生产者和消费者，可以说明这个问题。信号量维护一个计数，提供两种操作：生产者的 V 操作增加计数；消费者的 P 操作等到计数非零，随后减一并返回。如果只有一个生产者线程和一个消费者线程，它们运行在不同 CPU 上，且编译器不进行过于激进的优化，那么下面这个实现可以工作：

```c
// 原书第 100–121 行：仅用于引出忙等问题的第一版
struct semaphore {
  struct spinlock lock;
  int count;
};

void
V(struct semaphore *s)
{
  acquire(&s->lock);
  s->count += 1;
  release(&s->lock);
}

void
P(struct semaphore *s)
{
  while(s->count == 0)
    ;
  acquire(&s->lock);
  s->count -= 1;
  release(&s->lock);
}
```

> 编者注：上面保留教材的限制性假设与演进过程。对 `count` 的无锁轮询不是可直接推广到现代 C 并发程序的正确模板，也不能扩展成任意多个消费者的实现。

这种实现代价很高。如果生产者很少行动，消费者会把大部分时间花在 while 循环中，希望计数变为非零。与其反复查询 `s->count` 忙等，消费者占据的 CPU 本来可以做更有价值的工作。要避免忙等，需要让消费者交出 CPU，直到 V 增加计数后才恢复。

下面朝这个方向迈出一步，但还不够。设想有一对调用 `sleep` 和 `wakeup`：`sleep(chan)` 在一个任意值 chan 上睡眠，这个值称为**等待通道**（wait channel）。sleep 使调用进程睡眠，把 CPU 留给其他工作。`wakeup(chan)` 唤醒所有睡在该 channel 上的进程，使它们的 sleep 调用能够返回；如果无人等待，它什么也不做。可以把信号量改成：

```c
// 原书第 200–217 行：增加 sleep/wakeup，但仍然错误
void
V(struct semaphore *s)
{
  acquire(&s->lock);
  s->count += 1;
  wakeup(s);                 // 本版新增
  release(&s->lock);
}

void
P(struct semaphore *s)
{
  while(s->count == 0)
    sleep(s);                // 用睡眠替代自旋
  acquire(&s->lock);
  s->count -= 1;
  release(&s->lock);
}
```

P 现在交出 CPU 而不自旋，这是进步。但用这样的接口设计 sleep 与 wakeup，并不能轻易避免**丢失唤醒**（lost wake-up）。假设 P 在原书第 212 行发现 `s->count == 0`。当 P 位于第 212、213 行之间时，另一 CPU 上的 V 把计数改成非零，调用 wakeup；wakeup 没发现睡眠者，于是什么也没做。然后 P 执行第 213 行，调用 sleep 并睡着。

结果是 P 等待一次已经发生过的 V 调用。除非运气好，生产者后来再调用一次 V，否则即使计数非零，消费者也会永远等下去。

根本问题在于：“P 只在计数为零时睡眠”这个不变式，被恰好在不合适时间执行的 V 破坏了。一种错误的保护办法是提前取得 P 中的锁，让检查计数与调用 sleep 之间无法插入 V：

```c
// 原书第 300–317 行：避免了这个窗口，却引入死锁
void
V(struct semaphore *s)
{
  acquire(&s->lock);
  s->count += 1;
  wakeup(s);
  release(&s->lock);
}

void
P(struct semaphore *s)
{
  acquire(&s->lock);          // 本版把加锁移到检查之前
  while(s->count == 0)
    sleep(s);
  s->count -= 1;
  release(&s->lock);
}
```

我们可能希望这能避免丢失唤醒，因为锁阻止 V 在检查与 sleep 之间执行。它确实做到这一点，却还造成了死锁：P 睡眠期间持有锁，所以 V 会永远等待这把锁。

修复方法是改变 sleep 的接口。调用者必须把**条件锁**传给 sleep，使 sleep 能以不会漏掉唤醒的方式，在进程登记到睡眠通道的过程中交出锁。锁会迫使并发的 V 等到 P 完成睡眠登记，使 wakeup 找到睡眠的消费者并唤醒它。消费者再次醒来后，sleep 在返回之前重新取得这把锁。正确的用法如下：

```c
// 原书第 400–417 行：正确的双参数 sleep 接口
void
V(struct semaphore *s)
{
  acquire(&s->lock);
  s->count += 1;
  wakeup(s);
  release(&s->lock);
}

void
P(struct semaphore *s)
{
  acquire(&s->lock);
  while(s->count == 0)
    sleep(s, &s->lock);       // 本版把条件锁交给 sleep
  s->count -= 1;
  release(&s->lock);
}
```

P 持有 `s->lock`，因此 V 不能在 P 检查计数与调用 sleep 之间尝试唤醒它。但还需要 sleep **原子地释放 `s->lock` 并使消费者睡眠**。

> 编者校订：原书此处有一处 `c->count`，上下文实际指 `s->count`。另外，“原子地释放并睡眠”是对唤醒者的可观察效果，不要求源码先写 `SLEEPING` 再释放条件锁；下一节的真实实现是在持有 `p->lock` 后先释放条件锁，再登记睡眠。

## §7.6 代码：sleep 与 wakeup

现在查看 `kernel/proc.c` 的 `sleep` 与 `wakeup`。基本办法是：sleep 把当前进程标记为 `SLEEPING`，调用 `sched` 释放 CPU；wakeup 寻找睡在指定 channel 上的进程，把它们标记为 `RUNNABLE`。双方可以选用任何共同方便的值作为 channel。xv6 经常使用与等待有关的某个内核数据结构的地址。

sleep 先取得 `p->lock`。此时将要睡眠的进程同时持有进程锁和条件锁 `lk`。调用者——前例的 P——原先必须持有 lk，确保另一个进程——前例中执行 V 的进程——还不能开始调用 `wakeup(chan)`。现在 sleep 持有进程锁，就可以安全释放 lk：另一进程可能开始调用 wakeup，但 wakeup 会等待取得 `p->lock`，因而要等 sleep 完成睡眠登记，不能错过这次 sleep。

有一个小复杂点：如果 lk 本来就是 `&p->lock`，sleep 再次取得同一把锁就会自我死锁。不过调用者既然已经持有自己的进程锁，就无需额外动作来防止错过并发唤醒。`wait` 把自己的进程锁传给 sleep 时就属于这种特殊情况。

> 编者核对：rev1 这里给 `wait` 标了不对应的源码行号；固定快照中 `wait` 从 `proc.c:398` 开始，调用 `sleep(p, &p->lock)` 在第 445 行。以函数与调用定位为准。

现在 sleep 只持有自己的进程锁，可以记录 channel，把状态改为 `SLEEPING`，然后调用 `sched`。进程锁要到进程已被标为睡眠、并完成切换后，才由 scheduler 释放；这个时机非常重要。

在某个时间点，另一个进程取得条件锁，使等待条件成立，并调用 `wakeup(chan)`。按常规用法，调用 wakeup 时应持有条件锁。wakeup 遍历进程表，每检查一个进程就取得它的 `p->lock`：一方面它可能修改该进程状态，另一方面这把锁确保 sleep 与 wakeup 不会错过彼此。找到状态为 `SLEEPING`、channel 匹配的进程后，它将状态改为 `RUNNABLE`，之后调度器便能发现这个进程已经可以运行。

**原书脚注：** 严格说，只要 wakeup 在取得条件锁之后发生即可；也可以在释放条件锁之后再调用 wakeup。

> 编者说明：脚注不允许省掉“用同一条件锁保护条件的检查与修改”这一步。正文采用更直接的持锁更新、持锁唤醒写法。

为什么这个协议保证不丢失唤醒？从检查条件之前，到被标记为 `SLEEPING` 之后，睡眠方一直持有条件锁、自己的进程锁，或者同时持有两者。按照正文的常规调用方式，唤醒方在 wakeup 的循环中需要两把锁。因此只有两种可能：唤醒方先使条件成立，消费者随后检查到它；或者唤醒方对消费者的检查严格发生在消费者已被标记为 `SLEEPING` 之后。后一种情况下，wakeup 会找到并唤醒它，除非它已被别的事情唤醒。

有时多个进程睡在同一 channel 上，例如多个进程读取同一管道。一次 wakeup 会唤醒所有这些进程。其中一个先运行并取得传给 sleep 的锁，然后读走管道中等待的数据。其他进程醒来后发现已经没有数据可读。对它们而言，这次唤醒是“虚假的”（spurious），必须再次睡眠。因此，sleep 总应放在重新检查条件的循环中。

两个不相关的 sleep/wakeup 用途若偶然选中了同一个 channel，也不会因此破坏正确性：它们会遭遇额外唤醒，但上述循环能够容忍这种情况。sleep/wakeup 的吸引力在于它轻量，不必专门创建对象充当睡眠通道；同时提供间接层，让调用者不必知道自己正在与哪一个具体进程交互。

## §7.7 代码：管道

管道是使用 sleep/wakeup 同步生产者和消费者的更复杂例子。第 1 章已经介绍管道接口：写入一端的字节复制到内核缓冲区，然后从另一端读出。围绕管道的文件描述符支持将在后续章节讨论，这里先看 `pipewrite` 和 `piperead`。

每条管道由一个 `struct pipe` 表示，其中包含锁和数据缓冲区。`nread`、`nwrite` 分别累计已经读出、写入缓冲区的字节数。缓冲区是环形的：写到 `buf[PIPESIZE-1]` 后，下一个位置回到 `buf[0]`。计数并不随缓冲区边界回绕。这样可以区别：

- 满：`nwrite == nread + PIPESIZE`；
- 空：`nwrite == nread`。

代价是访问缓冲区必须使用 `buf[nread % PIPESIZE]`，不能直接使用 `buf[nread]`；写入下标同理。

> 编者注：原书用 `buf` 泛指缓冲区，固定源码的字段名是 `data`。“计数不回绕”指不按 PIPESIZE 回绕；实际 `uint` 计数仍有整数位宽，不能解释为无限精度整数。

假设两个 CPU 同时调用 piperead 与 pipewrite。pipewrite 先取得管道锁，它保护计数、数据以及相关不变式。piperead 也尝试取得锁，但暂时失败，只能在 acquire 中自旋。此时 pipewrite 遍历待写的 `addr[0..n-1]`，把字节逐个加入管道。

循环中缓冲区可能填满。遇到这种情况，pipewrite 先调用 wakeup，告诉可能睡着的读者已经有数据可取；然后睡在 `&pi->nwrite` 上，等读者腾出空间。sleep 在把写者睡下去的过程中释放 `pi->lock`。

锁可用以后，piperead 就能取得它，进入临界区。它看到 `pi->nread != pi->nwrite`——写者刚才是因为缓冲区满而睡眠——于是跳过等待，进入 for 循环，把数据从管道复制出去，并按实际读取量增加 nread。现在同样数量的位置可用于新写入，因此 piperead 在返回前调用 wakeup，通知睡眠中的写者。

wakeup 找到睡在 `&pi->nwrite` 的进程，也就是刚才因缓冲区满而停止的 pipewrite 调用者，将其标记为 `RUNNABLE`。

管道为读者和写者使用两个不同的等待通道，分别对应 `nread` 和 `nwrite` 的地址。若碰巧有很多读者、写者等待同一管道，这能减少无关唤醒。两侧都在检查等待条件的循环里调用 sleep；当多个读者或写者被唤醒时，后续获得锁的进程可能发现可继续条件又不成立，于是再次睡眠。

> 编者校订：原书这一段括号简写成 `pi->nread`、`pi->nwrite`；实际传递的是地址 `&pi->nread`、`&pi->nwrite`，不是随数据流变化的计数值。

## §7.8 代码：wait、exit 与 kill

sleep/wakeup 可用于许多等待。一个有趣例子是第 1 章介绍过的子进程 exit 与父进程 wait 的交互。孩子退出时，父亲可能已经睡在 wait 中，也可能正在做别的工作。后一种情况下，即使很久以后才调用 wait，也必须观察到孩子已经退出。

xv6 用 `ZOMBIE` 状态保存这件事：exit 把调用者放进该状态，直到父进程的 wait 发现它，完成回收，将状态改成 `UNUSED`，复制退出状态，并把子进程 PID 返回给父进程。若父进程先退出，就把孩子交给不断调用 wait 的 init，保证每个孩子都有负责善后的父进程。实现的主要挑战是 wait/exit 之间、以及父子同时 exit 时可能出现的竞争和死锁。

### wait：用父进程自身的锁保护等待协议

wait 用调用进程自己的 `p->lock` 作为条件锁，避免丢失唤醒，并在入口取得它。随后扫描进程表。如果发现一个 `ZOMBIE` 子进程，就回收它的资源和 proc 槽，按需要把退出状态复制到用户提供的地址，并返回子进程 PID。若有子进程但还没有退出者，就调用 sleep 等待，醒来后重新扫描。

这里传给 sleep 的条件锁就是等待进程自己的进程锁，属于上一节的特殊情况。注意 wait 常常同时持有两把锁，而且是先持有自己的锁，再取得孩子的锁。因此 xv6 其他相关代码也必须遵循**先父锁、后子锁**的顺序，避免死锁。

wait 为找孩子，会检查每个进程的 `np->parent`，但检查时还没有取得 `np->lock`。这看起来违反共享变量应受锁保护的常规规则。若 np 恰是当前进程的祖先，贸然先取得它的锁就会违反父到子的锁顺序，可能死锁。这里不先锁 np 的检查被认为可行，是因为进程的 parent 字段只由其父进程改变；若 `np->parent == p` 成立，除了当前父进程自己，没有另一个执行者会把它改走。

> 编者核对：固定快照在发现僵尸后，先保存 PID、尝试复制退出状态，再调用 `freeproc`。复制失败会释放锁并返回 -1，不回收该孩子。教材上述段落列出的是职责，并非用来替代真实语句顺序。

### exit：在两把锁保护下结束，最后交给调度器

exit 记录退出状态、释放部分资源、把自己的孩子交给 init、唤醒可能在 wait 中等待的父进程，把自己标为僵尸，然后永久交出 CPU。最后这段顺序很微妙。

退出者在设置 `ZOMBIE` 和唤醒父进程时必须持有父锁，因为父锁是 wait 防止丢失唤醒的条件锁。它也必须持有自己的进程锁；否则父进程可能看到 `ZOMBIE` 后，在孩子仍执行退出代码时就回收它。锁顺序同样关键：wait 是先父锁后子锁，exit 也必须如此。

exit 使用专门的 `wakeup1`，只唤醒这个父进程，而且仅当它正在 wait 中睡眠时才唤醒。先唤醒父进程、随后才设置 `ZOMBIE`，看似不妥，其实安全：虽然 wakeup1 可以使父进程开始运行，但 wait 的扫描必须等 scheduler 释放子进程的 `p->lock` 才能检查它。那时 exit 早已设置好 `ZOMBIE`。

> 版本说明：本节是 rev1 与固定 2020 快照中的协议：父进程 `p->lock`、父子加锁顺序、`sleep(p, &p->lock)` 和专用 `wakeup1`。不应拿新版代码中的 `wait_lock` 代换。2020 的通用 `wakeup` 会遍历并取得各个进程锁，调用者不得已经持有任意 `p->lock`；专用 wakeup1 则要求调用者已持有目标父锁。

### kill：请目标在安全位置自行退出

exit 允许进程结束自己，kill 则允许一个进程请求另一个结束。让 kill 直接销毁目标太复杂，因为目标可能在另一 CPU 上执行，甚至正在敏感地更新内核数据结构。于是 kill 只设置目标的 `p->killed`；若目标睡着，还唤醒它。

目标最终进入或离开内核时，`usertrap` 中的代码会检查 killed，若已设置便调用 exit。目标若在用户态执行，很快会因系统调用、时钟中断或其他设备中断进入内核。

若目标原本在 sleep，kill 引起的唤醒会使它从 sleep 返回。这可能有危险，因为所等条件未必为真。不过 xv6 的 sleep 调用都在重新检查条件的 while 循环中。有些循环还检查 killed，发现终止请求便放弃当前活动。这只在可以正确中止的位置使用。例如管道读写代码看到 killed 会返回；最终返回 trap 路径，再由那里检查标志并退出。

> 编者校订：教材把这里口述为 kill 的“wakeup 调用”；固定源码实际在持有目标锁时直接把 `SLEEPING` 改为 `RUNNABLE`，没有调用通用 `wakeup()`。

有些睡眠循环不检查 killed，因为系统调用正在进行一个整体应当完成的多步骤操作。Virtio 驱动就是例子：一次磁盘操作可能属于一组写入，全部完成后才能让文件系统保持正确。等待磁盘 I/O 时被 kill 的进程，不会在中间直接退出；它会完成当前系统调用，随后由 usertrap 观察终止标志。

## §7.9 真实世界

xv6 的调度器采用简单策略，让各进程轮流运行，称为**轮转调度**（round robin）。真实操作系统采用更复杂的策略，例如给进程设置优先级：可运行的高优先级进程会优先于可运行的低优先级进程被选中。

策略很快就会复杂起来，因为目标往往互相竞争，例如系统还希望保证公平性与高吞吐量。复杂策略也会产生意外交互，包括优先级反转与护航效应（convoys）。如果低优先级进程持有一把高优先级进程也需要的锁，就会阻止后者前进，形成优先级反转。很多高优先级进程等待某个取得共享锁的低优先级进程时，还会形成很长的等待队列；一旦形成，这种队列可能持续很久。复杂调度器需要额外机制处理这些问题。

sleep/wakeup 是简单有效的同步办法，但还有很多其他办法。它们首先都要解决本章前面的丢失唤醒问题。最初的 Unix 内核只在 sleep 中关闭中断，因为它运行在单 CPU 上，这样已足够。xv6 在多处理器上运行，因此向 sleep 增加了显式的锁参数。FreeBSD 的 `msleep` 采用同一思路。

Plan 9 的 sleep 使用回调函数：在持有调度锁、即将睡眠之前运行该函数，对睡眠条件做最后检查，避免丢失唤醒。Linux 内核的 sleep 使用显式进程队列，称为等待队列（wait queue），而不是单纯的等待通道；队列有自己的内部锁。

wakeup 为寻找匹配 channel 而扫描全部进程表，效率不高。更好的办法是把 sleep/wakeup 的 channel 换成一个数据结构，在其中维护睡在该对象上的进程链表，例如 Linux 的等待队列。Plan 9 称这样的对象为 rendezvous point 或 `Rendez`。许多线程库把同类结构称为**条件变量**（condition variable），此时 sleep/wakeup 对应 `wait` 与 `signal`。这些机制有共同风格：条件受某种锁保护，而睡眠时原子地交出锁。

当前 wakeup 会唤醒某通道上的所有等待者；它们可能很多。操作系统要调度所有这些进程，它们又竞相检查条件。这种行为称为**惊群**（thundering herd），最好避免。多数条件变量提供两种通知：`signal` 唤醒一个，`broadcast` 唤醒所有等待者。

信号量也常用于同步。计数一般对应某种资源量，例如管道里可读字节数，或某个父进程的僵尸子进程数。把显式计数放进抽象，就能记住已经发生过多少次通知，避免丢失唤醒；计数也有助于避免虚假唤醒与惊群。

> 编者说明：这里描述的是正确实现的信号量所提供的抽象，不是说“只要加一个整数”就自动没有竞态。§7.5 的错误版本已有计数，仍然会漏通知；信号量内部的等待协议必须正确。

终止进程和清理资源已经给 xv6 带来很多复杂性。在多数操作系统里还更复杂，例如目标可能在内核深处睡眠，要小心编写代码才能沿调用栈退回。很多系统通过显式异常处理机制，例如 `longjmp` 一类方式，展开调用栈。

此外，等待事件尚未发生，也可能有其他事件唤醒进程。例如 Unix 进程睡眠时，另一进程可能向它发送信号。被中断的系统调用可能返回 -1，并把错误码设置为 `EINTR`；应用程序检查后决定下一步。xv6 不支持这套信号机制，因此没有这一层复杂性。

xv6 的 kill 支持也不完全令人满意。有些 sleep 循环可能应该检查 killed。相关问题是，即使循环检查了 killed，sleep 与 kill 之间仍有竞态：kill 可能恰好在目标检查 killed 之后、调用 sleep 之前，设置 killed 并尝试唤醒目标。若发生这种交错，目标只有等到原本等待的条件发生，才会再次注意到 killed。

这可能很晚，例如 virtio 驱动返回目标所等磁盘块时；甚至永远不发生，例如进程等待控制台输入，但用户一直不打字。

真实操作系统还会用显式空闲链表，在常数时间找到可用 proc 结构，而不是像 xv6 的 allocproc 那样做线性扫描。xv6 选择后者是为了简单。

## §7.10 习题

### 1. 删除 sleep 特殊分支会怎样？

sleep 必须检查 `lk != &p->lock`，避免死锁。假设把：

```c
if(lk != &p->lock){
  acquire(&p->lock);
  release(lk);
}
```

替换成：

```c
release(lk);
acquire(&p->lock);
```

这样就不再需要特殊分支，却会破坏 sleep。具体怎样破坏？

### 2. 为什么必须由 exit 关闭文件？

进程清理的大部分工作，既可以由 exit 做，也可以由 wait 做。但关闭打开文件必须由 exit 完成。为什么？答案涉及管道。

### 3. 用信号量替换 sleep/wakeup

不使用 sleep/wakeup，在 xv6 中实现信号量；可以使用自旋锁。用信号量替换 xv6 中的 sleep/wakeup 使用点，并评价结果。

### 4. 修复 kill 与 sleep 之间的竞态

修复上一节提到的问题：当 kill 发生在目标的睡眠循环检查 killed 之后、调用 sleep 之前时，也应使目标放弃当前系统调用。

### 5. 让每个等待循环都能响应 kill

设计一个方案，使每个 sleep 循环都检查 killed。例如，正在 virtio 驱动中等待的进程被另一进程 kill 后，也可以迅速离开 while 循环。

### 6. 两个进程之间只做一次上下文切换

修改 xv6：从一个进程的内核线程切换到另一个时，只做一次上下文切换，而不通过调度器线程中转。交出 CPU 的线程必须自行选出下一线程，并调用 swtch。挑战包括：防止多个核意外执行同一个线程，正确加锁，以及避免死锁。

### 7. 没有可运行进程时使用 WFI

修改调度器，在没有可运行进程时使用 RISC-V 的 `WFI`（wait for interrupt，等待中断）指令。尽量保证：只要存在等待运行的可运行进程，就没有核仍停在 WFI 中。

### 8. 拆分 p->lock

`p->lock` 保护许多不变式。阅读某段受它保护的 xv6 代码时，往往难以看出究竟在维护哪个不变式。设计一个更清晰的方案，把这把锁拆成多把锁。

## 阅读衔接

第 7 章导言与 §7.1–7.4 的调度、上下文切换和 CPU/进程定位在[第 11 讲课程资料](#/c/mit-6.s081-2020/lec/lec11?v=materials)，这里从 §7.5 接续。课堂 UART 故障演示及问答见[本讲中文译稿](#/c/mit-6.s081-2020/lec/lec13?v=draft)；`sleeplock.c` 的额外源码阅读与机制自测见[课程笔记](#/c/mit-6.s081-2020/lec/lec13?v=notes)。

## 来源、版本、原页核验与许可

- 作者：Russ Cox、Frans Kaashoek、Robert Morris（MIT）。[指定教材 PDF](https://pdos.csail.mit.edu/6.S081/2020/xv6/book-riscv-rev1.pdf)，2020-08-31 rev1，§7.5–7.10，印刷页与本地 PDF 页序 71–80。按六节顺序翻译；编者说明、纠错与版本提示已独立标注。
- 本地共享原件 `sources/book-riscv-rev1.pdf`、`.txt` 只读复用。逐页渲染并实际查看 71–80 页，核对节界、代码、黄色高亮改动、脚注和全部习题。本范围没有编号图或表；代码示例全部保留，黄色高亮在代码注释中标明。第 71 页上方属于 §7.4 的文字不重复译入。
- 固定 2020 源码提交：`e23d53f27f6e187732a92a2b4705639d1c260f05`。核对 `proc.c`、`pipe.c`、`trap.c` 与 `virtio_disk.c` 的相关路径，区分原书叙述、真实代码和新版本。没有运行教材习题或实验。
- 教材书目中的信号量引用 [4] 指向 Dijkstra 的工作；这里保留原书引用编号，不声称另外读取了该论文。
- 教材许可取自已存档的[官方教材仓库 LICENSE](https://github.com/mit-pdos/xv6-riscv-book/blob/xv6-riscv/LICENSE)。许可证版权年份为上游当前声明，不改写成教材发行年份；此许可不延伸到课程视频。

<details><summary>教材原始 MIT 许可全文</summary>

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
