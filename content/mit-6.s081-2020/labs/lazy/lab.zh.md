---
source: MIT 6.S081 Fall 2020 · Lab xv6 lazy page allocation
license: CC BY 3.0 US；MIT 课程团队署名，中文翻译与编者说明见页底
status: 官方任务、提示、问题、报错、测试与选做已译；共同提交步骤链接公共资料；未运行实验
---

# Lab lazy：xv6 惰性页分配

## 实验目标与准备

操作系统可以借助页表硬件，为用户空间的堆内存实现**惰性分配（lazy allocation）**。xv6 应用通过 `sbrk()` 向内核申请堆空间。给定的初始内核会立即分配物理内存，并将其映射到进程虚拟地址空间。大额申请的分配、映射可能很慢：例如 1 GiB 包含 262,144 个 4096 字节页，即使单次分配很便宜，累计次数仍然很多。

此外，一些程序申请的内存多于实际使用量，例如稀疏数组；另一些程序很早就申请内存，之后才使用。为了让这些情况下的 `sbrk()` 更快，内核可以只记录获准使用的用户地址，让相应用户页表项保持无效，而不立即分配物理页。进程第一次使用某一页时，CPU 产生缺页异常；内核随后分配物理页、清零并建立映射。本实验就是给 xv6 添加这一功能。

编码前阅读 xv6 教材第 4 章，特别是 **§4.6 缺页异常**，并阅读可能需要修改的文件：

- `kernel/trap.c`
- `kernel/vm.c`
- `kernel/sysproc.c`

教材译文位置见[公共资料的教材索引](#/c/mit-6.s081-2020)；页表基础可复习 [LEC 4 课程资料 §3.3、§3.6–3.8](#/c/mit-6.s081-2020/lec/lec04?v=materials)。

在实验仓库中切换到 `lazy` 分支：

```sh
$ git fetch
$ git checkout lazy
$ make clean
```

## 任务一：取消 sbrk() 中的立即分配（easy）

首先删除 `sbrk(n)` 实现中的物理页分配操作。对应函数是 `kernel/sysproc.c` 中的 `sys_sbrk()`。

`sbrk(n)` 将进程内存大小增加 `n` 字节，并返回新增区域的起始地址，也就是修改前的大小。此阶段的新实现只把 `myproc()->sz` 增加 `n`，返回旧大小，**不分配内存**：删除对 `growproc()` 的调用，但仍须更新进程大小。

**先想一想：这样改后，什么会出问题？为什么？**

完成修改、启动 xv6，在 shell 中输入 `echo hi`。原页给出的预期报错示例如下，具体地址可能不同：

```text
init: starting sh
$ echo hi
usertrap(): unexpected scause 0x000000000000000f pid=3
            sepc=0x0000000000001258 stval=0x0000000000004008
va=0x0000000000004000 pte=0x0000000000000000
panic: uvmunmap: not mapped
```

`usertrap(): ...` 来自 `trap.c` 的用户陷阱处理函数，表示它捕获了一个尚不懂得如何处理的异常。请确认自己能解释为什么发生这次缺页。`stval=0x...4008` 表明引发异常的虚拟地址是 `0x4008`。

> 编者提示：这是原页的阶段性失败示例，不是本站运行记录。此阶段的简单修改还没有处理负数 `sbrk`；最终要求见任务三。

## 任务二：缺页时惰性分配（moderate）

修改 `trap.c`：发生来自用户空间的缺页时，在出错地址对应的页上建立到新分配物理页的映射，然后返回用户空间，使进程继续执行。将处理逻辑放在打印 `usertrap(): ...` 的 `printf` 之前。按需要修改其他 xv6 内核代码，直到 `echo hi` 能正常工作。

原页提示：

1. 在 `usertrap()` 中，检查 `r_scause()` 是否为 **13 或 15**，以识别相应的缺页异常。
2. `r_stval()` 读取 RISC-V 的 `stval` 寄存器，其中保存引发缺页的虚拟地址。
3. 借鉴 `vm.c` 中的 `uvmalloc()`；原先 `sbrk()` 通过 `growproc()` 调用它。你需要调用 `kalloc()` 和 `mappages()`。
4. 使用 `PGROUNDDOWN(va)` 将出错地址向下取整到页边界。
5. `uvmunmap()` 会 panic；修改它，使部分页没有映射时不再因此 panic。
6. 如果内核崩溃，在 `kernel/kernel.asm` 中查找 `sepc`。
7. 使用 pgtbl 实验中实现的 `vmprint` 打印页表内容。
8. 如果遇到 `incomplete type proc`，先包含 `spinlock.h`，再包含 `proc.h`。

若进展顺利，`echo hi` 应能正常执行。原页说明，你应观察到至少一次缺页，也可能两次，这些缺页会触发惰性分配。

> 编者补充：第 6 条保留了原页提示。定位时应区分异常来自哪里：内核中的 `sepc` 查 `kernel/kernel.asm`；用户态故障指令的 `sepc` 应查对应用户程序的反汇编，不能一律在内核汇编里找。

## 任务三：通过 Lazytests 与 Usertests（moderate）

实验提供用户程序 `lazytests`，用若干特殊场景检查惰性分配器。修改内核，使 **`lazytests` 和 `usertests` 的全部测试均通过**，并处理以下情况：

- **负数 `sbrk()` 参数**：正确缩小进程内存。
- **超出申请范围的访问**：若进程在超过 `sbrk()` 已申请范围的虚拟地址上缺页，应终止该进程。
- **`fork()`**：正确处理从父进程到子进程的内存复制。
- **系统调用缓冲区**：进程可能把 `sbrk()` 返回的合法地址传给 `read`、`write` 等系统调用，而该地址还没有物理内存；必须支持这种情况。
- **物理内存耗尽**：如果缺页处理函数中的 `kalloc()` 失败，终止当前进程。
- **用户栈下方的无效页**：正确处理对此页的缺页访问。

通过两个测试程序才满足这一部分的验收条件。原页示例输出如下；`...` 是原文省略号，不是固定完整日志：

```text
$  lazytests
lazytests starting
running test lazy alloc
test lazy alloc: OK
running test lazy unmap...
usertrap(): ...
test lazy unmap: OK
running test out of memory
usertrap(): ...
test out of memory: OK
ALL TESTS PASSED
$ usertests
...
ALL TESTS PASSED
$
```

> 上述是官方示例，不是本次测试结果。出现某条 `usertrap()` 输出本身既不能证明失败，也不能证明通过；应结合具体测试及最终结果判断。

## 验收、思考题与提交

本实验保留的思考问题是：**取消 `sbrk()` 的立即分配后，什么会出问题？为什么会出现给定缺页？** 原页没有另列编号问答，也没有给出 lazy 专用的答案文件名；提交段的 `answers-lab-name.txt` 是“如果本实验有问题”的通用模板。

完成本页的 `echo hi`、`lazytests`、`usertests` 检查后，按[公共资料「实验的共同验收与提交步骤」](#/c/mit-6.s081-2020)运行 `make grade`，记录 `time.txt`，跟踪并提交所需文件，再按原课程流程使用 `make handin`。API key、未跟踪文件检查、`make tarball` 及提交状态查询的说明统一放在那里。

> 编者说明：原页通用提交示例中的 `[util c2e3c8b]` 不是本实验的分支要求；本实验起始分支仍是 `lazy`。历史提交网站的当前可用性未验证。

## 选做挑战

让惰性页分配能够与前面实验中实现的简化版 `copyin` 一起工作。

> 编者定位：这里指 pgtbl 实验借助内核页表映射简化用户内存读取的方案。任务三要求普通 `read/write` 能处理尚未实际分配的合法缓冲区；本选做进一步考虑简化 `copyin` 的页表方案如何配合惰性分配。

## 来源、许可与状态

- MIT 6.S081 课程团队，[Lab: xv6 lazy page allocation（Fall 2020）](https://pdos.csail.mit.edu/6.S081/2020/labs/lazy.html)，依据 2026-11-06 抓取的共享 HTML 全页翻译；原始快照与哈希见 `sources/manifest.json`。
- 课程网站采用 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。本页为非官方中文翻译；标题、排版和提交章节做了适配，补充说明均明确标作编者文字。所有报错、命令和测试输出保留其原页示例性质。
- 三阶段任务、八项提示、六项边界要求、思考问题与选做已覆盖；共同提交段转至公共资料，范围映射见 `sources/coverage.json`。
- 未运行 xv6、实验测试或评分脚本；未获取到 lazy 分支的专用测试源码，不据此推断测试内部实现或分值。
