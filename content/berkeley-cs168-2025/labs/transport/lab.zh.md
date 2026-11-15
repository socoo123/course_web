---
source: UC Berkeley CS168 Spring 2025 Project 3；官方页面、五幅题面图、固定 starter 和本地测试静态阅读，入口见页底
version: Spring 2025 URL 于 2026-11-15 获取；不把链接的 Spring 2024 PDF 当作本学期规范
license: 题面与课程专用代码未确认开放再利用许可；本页为原创中文要求导读，不是整份题面的授权翻译或近义复制
status: 可达要求导读 complete；3A stages 1–5、3B stages 6–9 均覆盖；实验完成状态 not_attempted；未执行学生代码、测试或模拟器
---

# Transport：让不可靠分组承载可靠字节流

## 实验交付的抽象

实现一个用户空间 TCP 客户端子集：应用交给 socket 的字节，可以经过分段、丢失、乱序和重传，最终仍按原顺序交给对端。你负责连接建立、发送与接收、流量控制、关闭以及重传计时；应用、虚拟网络、服务端 TCP 和大部分 socket 外壳已经提供。

这不是完整互联网 TCP。**无需且不包含拥塞控制**，不要求实现 `LISTEN`、`SYN_RECEIVED` 的服务端握手路径。对应先修是 [Lecture 11：可靠传输](#/c/berkeley-cs168-2025/lec/lec11?v=notes) 与 [Lecture 12：TCP](#/c/berkeley-cs168-2025/lec/lec12?v=notes)。Lecture 13–15 的拥塞窗口、慢启动等不是额外必做阶段；接收方通告窗口与网络拥塞控制是不同问题。

同一个文件分两次交付：**3A 完成 Stage 1–5，3B 继续完成 Stage 6–9**。下文保留阶段和子阶段编号作为检索锚点，但用“应有行为—代码边界—可观察证据”重新组织，方法体由学习者独立完成。

## 一、环境、版本和操作边界

### 固定版本

官方 starter 的下载文件名为：

```text
cs168-sp25-proj3-transport.zip
SHA-256:
10f7d6ede628be7c0769e03470e598c1046c222e08d1fdafbf663a80ca8aded3
```

ZIP 内直接包含 `ext/`、`pox/`、`pox.py`，没有额外的同名顶层目录。解压时自行创建容器目录，再进入：

```text
cs168-sp25-proj3-transport/ext/cs168p2
```

本页全部 Python 命令均以此目录为工作目录，不是在仓库根目录执行。归档原件只在本站 `sources/labs/transport/` 中保留，未填写任何学生实现。

| 项目 | 官方 Spring 2025 说明 | 本次实际边界 |
|---|---|---|
| 系统 | 已测试 Linux、Mac；Windows 推荐 WSL | 本机为 Darwin/arm64，未验证实验兼容性 |
| Python | 已测试 **Python 3.7**；较新版本风险自担 | 没有建立或运行 Python 3.7 实验环境 |
| 实现文件 | 只提交 `student_socket.py` | 保留空白 starter，没有实现与提交 |
| 执行方式 | POX 虚拟网络，本地阶段配置 | 未启动 POX、autograder、服务或抓包 |
| 完成状态 | 应以学习者的实际测试与提交为准 | **not_attempted**，不能把文档完成算作实验通过 |

官方环境自检步骤如下，仅作为将来自行开展实验时的操作说明，本次未执行：

```bash
chmod +x ../../pox.py
python ../../pox.py config=tests/sanity_test.cfg
```

`sanity_test.cfg` 没有装入学生 socket 替换模块，因此它检查的是框架握手环境，不是证明你的 Stage 1 完成。阶段测试则通过配置安装 `StudentUSocket`。

另外，autograder 直接执行 `../../pox.py`，而这个文件是 shell/Python 双用启动器，会优先查找 PyPy，再找 `python3`，最后找 `python`。**启动 autograder 的解释器与它启动 POX 的解释器可能不同**；“我用 Python 3.7 启动了 autograder”本身不能证明子进程也用了 3.7。不要把 ZIP 自带的 `cpython-312` 缓存当作官方支持 3.12 的声明。

### 允许修改什么

- 仅在 `student_socket.py` 标记的阶段区块内填写；可以添加辅助方法。
- 不改其他文件，不新建实现依赖文件，不增加 import，不加硬编码全局变量，不修改标记区块外的既有代码。
- 不更改测试、模拟器、框架常量来“修复”分数；不通过共享全局状态绕过报文通信。
- 可独立完成或与一位搭档同步结对编程；双方对全部提交负责。
- 官方政策禁止公开解答、查阅他人/往年解答以及使用 ChatGPT、Copilot 等自动代码生成器完成作业。本材料仅供概念与要求学习，不提供可提交代码；正式修课须遵循当学期政策。

## 二、从字节到框架对象

`StudentUSocket` 继承的外壳负责应用调用、绑定与唤醒。应用发送的内容先进入 `tx_data`；已连续收到、可交给应用的内容进入 `rx_data`。两个缓冲区在此骨架中初始化为 Python `bytes`，不是可以按下标就地改写的数组。

| 对象或字段 | 含义 | 切勿混淆 |
|---|---|---|
| `snd.iss` | 本端初始序号 | 对端初始序号属于接收方向 |
| `snd.una` | 最早尚未累计确认的位置 | 不是最近一次 ACK 包的序号 |
| `snd.nxt` | 首次发送新内容的下一个位置 | 重发同一段不消耗新位置 |
| `snd.wnd` | 对端通告给本端的发送额度 | 不是 `tx_data` 的长度，也不是 cwnd |
| `rcv.nxt` | 下一处尚未连续接收的位置 | 已缓存的最高乱序序号不等于它 |
| `rcv.wnd` | 本端还可接收的空间 | 应用 `recv()` 取走内容后会恢复 |
| `rx_queue` | 尚待按序处理的报文 | 不等于已经可以交付的 `rx_data` |
| `retx_queue` | 已发送而未被累计确认的报文 | 不等于尚未发送的 `tx_data` |

序号是 32 位环形空间。运算与比较使用骨架的 `PLUS`、`MINUS`、`EQ`、`NE`、`GT`、`GE`、`LT`、`LE` 中缀运算对象，不用 Python 普通大小比较判断跨回绕的前后顺序。普通长度、时间与计数仍是普通数值。

收到的 `p` 是 IP 包，`p.tcp` 是 TCP 段，`p.app` 是载荷字节；段有 `seq`、`ack`、`win` 及 `ACK/SYN/FIN` 标志。`new_packet()` 默认带 ACK，从当前控制块写入本端发送序号、确认号和接收窗口；建包本身不等于发送。发送需经过 `tx()`，最后由 manager 接入模拟器。

## 三、3A：建立连接并交换数据

### Stage 1 — 三次握手

**目标行为：** 本端从 `CLOSED` 主动连接，发 SYN 后处于 `SYN_SENT`；收到有效 SYN-ACK 后确认双方的起点，最后发 ACK 并进入 `ESTABLISHED`。SYN 没有应用数据，但占一个序号。

**定位：** 1.1 在 `connect()` 组织初始 SYN 与发送方向的初值/推进；1.2 在 `rx()` 按 `SYN_SENT` 分派；1.3 在 `handle_synsent()` 已给出的 ACK 合法性检查之后协调收发边界、建立状态、待发 ACK 和窗口更新。不要绕过前面的无效 ACK 检查，也不要把两个方向的序号互相代入。

**静态验收证据：** `s1_t1` 检查恰好三个握手包、方向和标志：首包 SYN 非 ACK，次包 SYN+ACK，末包 ACK 非 SYN；两个 ACK 都确认对应 SYN 后的一个位置，并核对抓包时的状态。`s1_t2` 把服务端 ISN 设为 `0xFFFFFFFF`，要求跨回绕仍正确。

### Stage 2 — 只交付按序数据

**目标行为：** 能连续接收的数据进入应用缓冲；缺少中间一段时，不可把后续内容直接接上。此阶段暂时丢弃乱序数据，并用当前累计 ACK 表达仍在等待的边界。

**定位：** 2.1 是 `rx()` 在 `acceptable_seg()` 放行之后的顺序检查；2.2 是 `handle_accepted_seg()` 中对状态和非空载荷的限定；2.3 是 `handle_accepted_payload()` 中接收边界、缓冲占用及待发 ACK 的一致性维护。处理载荷允许的状态为 `ESTABLISHED`、`FIN_WAIT_1`、`FIN_WAIT_2`。已有代码会先按接收窗口裁掉过长载荷。

**约束：** 不要从阶段区块提前退出整个 `rx()` 或 `handle_accepted_seg()`；它们还有发送、ACK、FIN、唤醒等后续工作。这里的 ACK 不是另造一种“请求丢包”的报文，而是 TCP 累计确认号。

**静态验收证据：** 六个配置覆盖单包、3 包、50 包及损失情形；除了应用收到的字节完全一致，部分测试检查抓包数量。Stage 2 的恢复依靠对端重传，本端重传队列要到 Stage 8 才完成。

### Stage 3 — 缓存乱序，去除重叠

**目标行为：** 乱序报文先留在 `rx_queue`；缺口补齐后，在同一轮处理中尽可能交付连续前缀。重复或重叠区不能重复进入 `rx_data`。

**定位：** 3.1 替换 Stage 2 在 `rx()` 中直接处理/丢弃的策略；3.2 处理队列。`RecvQueue` 已提供按模序号排序的 `push()`，以及 `peek()`、`pop()`、`empty()`。队首还在缺口之后时停止本轮取数并保留累计 ACK；队首覆盖当前边界时，只处理未交付的部分。退出队列循环不等于退出整个接收函数。

**静态验收证据：** 五个配置最后都比较完整应用数据；`s3_t4`、`s3_t5` 复用 `s3_t2.py`、`s3_t3.py`，只改变 ISN 等配置，**没有同名 `.py` 并非缺文件**。关键差异是 dropper 记录已经成功放行的起始序号，之后该序号的再次发送会被丢弃，迫使接收方保留那次成功到达的乱序段，而不能永远等第二份副本。

### Stage 4 — 分段发送与累计 ACK

**目标行为：** 发送只能消耗尚未发送的应用数据、当前窗口剩余额度及 MSS 三者共同允许的空间。已发未确认的字节也占窗口。有效新 ACK 推进累计确认边界；重复/过旧 ACK 不能使它后退；超出已发送范围的 ACK 不能让你相信未发数据已送达。

**定位：** 4.1 `check_ack()` 决定 ACK 类别及后续是否还能处理同段载荷；4.2 `handle_accepted_ack()` 维护已确认边界；4.3 `maybe_send()` 负责分段与移除已首次发送的 `tx_data` 前缀；4.4 `tx()` 负责数据首次发出时的序号推进。`continue_after_ack` 与函数返回是两个层级的控制，不可互换。

**静态验收证据：** 五个配置核对服务端收到 17、4080、69000 字节的完整内容，后两种数据量各有回绕配置。源码中若干包数断言被注释掉；不能把注释当成实际评分检查。

### Stage 5 — 使用对端通告窗口

**目标行为：** Stage 4 的额度现在应来自对端段的 `win`，而不是骨架暂用的发送缓冲上限。小窗口会约束每次可以在途的内容，不能为了迅速发完数据而忽略它。

**定位：** 5.1 `update_window()`；保留已有窗口更新的序号记录 `wl1/wl2`。调用方 `check_ack()` 已有新旧窗口通告的选择条件，握手也会初始化窗口。

**静态验收证据：** `s5_t1` 将服务端缓冲设为 1 字节，验证 300 字节完整到达且有 300 个带数据报文；`s5_t2` 将其设为 199 字节，验证 1990 字节完整到达且有 10 个带数据报文。

完成 Stage 1–5 后对应 **Project 3A**，只向其 Gradescope 入口提交 `student_socket.py`，不是整个 ZIP。

## 四、3B：关闭、重传及自适应超时

### Stage 6 — 被动关闭

**目标行为：** 对端先说“发送结束”，并不等于本端立刻不能发送。典型路径为 `ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED`：收到对端 FIN 后确认；等本端应用关闭、剩余待发数据发出后发本端 FIN；其被确认后释放连接。

**定位：** 6.1 `handle_accepted_fin()` 处理接收 FIN 所占序号、ACK 与状态；6.2 `close()` 的 `CLOSE_WAIT` 分支表达 FIN 意图；6.3 `check_ack()` 的 `LAST_ACK` 分支判断本端 FIN 是否被确认并调用 `_delete_tcb()`。

`FinControl.set_pending(next_state)` 会等待 `tx_data` 清空，真正发出 FIN 后才转入给定状态；`acks_our_fin()` 判断累计确认边界是否已越过 FIN。不要重复实现这些 helper 已做的 FIN 发送序号推进。

**静态验收证据：** `s6_t1` 核对握手后的 FIN/ACK 往返顺序与最后 `CLOSED`；`s6_t2` 复用它的 Python 模块并改变服务端 ISN。抓包状态是包经过 r1 时的快照，可能早于客户端处理该包，不可把日志时间点混为一谈。

### Stage 7 — 主动关闭

**目标行为：** 本端先发 FIN 后进入 `FIN_WAIT_1`。必须考虑三个事件次序：

- 本端 FIN 先被确认：`FIN_WAIT_2`，继续等对端剩余数据及 FIN；
- 对端 FIN 与对本端 FIN 的有效确认同时到达：进入 `TIME_WAIT`；
- 对端已发 FIN、但尚未确认本端 FIN：先 `CLOSING`，之后收到有效确认才进 `TIME_WAIT`。

进入 `TIME_WAIT` 应使用 `start_timer_timewait()`，而不是只改状态。骨架等待时长为 30 秒模拟时间，之后删除 TCB。

**定位：** 7.1 `close()` 的 `ESTABLISHED` 分支；7.2 `handle_accepted_fin()` 的主动关闭路径；7.3 `check_ack()` 的 FIN 确认状态转换。对端 FIN 消耗接收方向一个位置，ACK 是否确认“本端的 FIN”则属于发送方向；两件事都要成立。

**重要题面差异：** 网页把其中一路写成“FIN 包 ACK 标志未设”，但本版本 `handle_accepted_seg()` 会在 `seg.ACK` 为假时直接返回。应以实际调用链理解：ACK 标志存在也不代表 ACK 号已经确认本端 FIN。此处保留为上游文字与骨架的冲突，不擅改框架来迎合该句。

**静态验收证据：** `s7_t1` 覆盖先 ACK、后 FIN 的常见主动关闭，结束时检查 `CLOSED`；`s7_t2` 将服务端窗口设为 10 字节，本端发 100 字节后关闭，检查完整载荷以及 FIN 后无载荷。两项并未穷举上面三条路径。

### Stage 8 — 对未确认内容重传

**目标行为：** 首次发送 SYN、FIN 或非空数据时记录模拟时间并进入 `retx_queue`；纯 ACK 不入队。累计确认到来时移除已确认段。周期检查最早发送时间对应的段，超时则重发同一个报文，不再次入队、不再次消耗序号。

**定位：** 8.1 `tx()`；8.2 `handle_accepted_ack()`；8.3 `check_timer_retx()`。本阶段 RTO 初始固定为 1 秒；判断分支在骨架中采用严格大于。定时调用由 manager 提供，精确间隔为 **0.1001 秒**，不是另起系统线程或调用真实时间函数。

`RetxQueue.pop_upto()` 按起始序号删除队首的已确认项；`get_earliest_pkt()` 按 `tx_ts` 选最早时间，不是重新扫描接收队列。队列保留原始报文对象，重传标记供下一阶段排除歧义样本。

**静态验收证据：** `s8_t1` 丢掉前六个适用 ACK，但之后累计 ACK 足够，断言 13800 字节到达且恰好 10 个数据包；`s8_t2` 丢首个 1000 字节数据包，检查最终内容和 r1 处一个可见数据包；`s8_t3` 对 13800 字节交错丢包，检查完整到达及 r1 抓包中 14–17 个带数据包。`s8_t2` 的“1 retransmission”文字不等于全路径只发一个包，也没有直接断言精确一秒。

### Stage 9 — RTT 估计与 RTO 退避

**目标行为：** 根据首次发送后获得的无歧义确认样本估计 RTT，用平滑值和波动量设置 RTO；发生超时重传则退避。不能把已经重传的报文用作普通 RTT 样本，因为无法确定 ACK 对应哪次发送。

**定位：** 9.1 `update_rto(acked_pkt)` 的参数是**已获确认的原始发送 IP 包**，不是收到的 ACK 包；9.2 `handle_accepted_ack()` 用本次累计确认移出的队列项供已有 `not p.retxed` 过滤；9.3 `check_timer_retx()` 的超时分支负责 RTO 倍增与上限。

算法采用 RFC 6298 §2 的初次样本初始化和后续平滑更新，固定 `alpha=1/8`、`beta=1/4`、`K=4`。RTTVAR 更新须使用旧 SRTT；计算结果夹在 `MIN_RTO=1` 与 `MAX_RTO=60` 秒之间。源码构造函数将 `G` 设为 manager 粒度 **0.1001 秒**，虽网页示例列出类级初值 `G=0`，不要把实际实例值强行改回零。

**静态验收证据：** 三个测试以 25 ms 间隔交付 100 份、每份 1300 字节。前两项检查全部 130000 字节到达，及 SRTT 分别落在 **0.36–0.44 秒**、**0.95–1.05 秒**。第三项在主链路用固定随机种子、约 4% 概率丢数据包，同一序号最多丢一次；检查完整内容及 `rto < 32`、`srtt < 16`、`rttvar > 1.5`。这些是评分断言，不是任意网络上的性能保证。

## 五、官方命令和测试完整性

所有以下命令仍在前述 `ext/cs168p2` 目录执行；此文仅记录，不代表已经运行。

```bash
python autograder.py s1
python autograder.py s2
python autograder.py s3
python autograder.py s4
python autograder.py s5
python autograder.py all 5
python autograder.py s6
python autograder.py s7
python autograder.py s8
python autograder.py s9
python autograder.py all 9
python autograder.py all
```

单项定位与详细输出示例：

```bash
python autograder.py s5_t1
../../pox.py config=./tests/s5_t1.cfg tcpip.pcap --node=r1 --no-tx
```

autograder 会扫描 `.cfg`，按 `sN_` 前缀组织测试，自动建 `trace/`，对子进程检查：五秒现实时间内结束、返回码为零、stderr 中含通过标记。配置里的 `run_time=600` 是**模拟时间**，并不等于外层给子进程 600 秒。不能只看进程返回零而忽略测试日志。

本 ZIP 共 **30 个阶段配置、25 个阶段 Python 测试模块**，按阶段数量为 **2、6、5、5、2、2、2、3、3**。五个没有同名 Python 文件的配置均复用已有模块，因此网页列出的阶段测试未发现文件缺失。另有 sanity 和历史演示配置，不属于这 30 项；其中 `rx_fin.py` 有过时 API/变量问题，不能当作正式阶段入口。

**覆盖不等于完备。** 没有专门独立穷举所有重叠布局、无 ACK 标志 FIN、主动同时关闭、零窗口恢复、任意部分段 ACK、所有 RTO 重启规则的测试。官方称没有隐藏测试，不等于本地集合证明完整 TCP 正确。

3B 只提交 `student_socket.py` 到 Project 3B；官方说明九个阶段等权、阶段内测试等权，并以诚信完成为前提。本站未登录 Gradescope，没有成绩或通过记录。

## 引用与来源

- [Spring 2025 Project 3 官方现有题面](https://sp25.cs168.io/proj3/)：完整阅读 Setup、Code Overview、全部九阶段和 Submission；五幅窗口/握手/关闭图均已查看。
- [固定 starter 下载入口](https://sp25.cs168.io/assets/projects/proj3/cs168-sp25-proj3-transport.zip)：已下载、计算 SHA-256、解压静态阅读。README 中 `cs168.io/proj3` 是可随年份变化的地址，应继续使用本页 Spring 2025 链接。
- [课程政策](https://sp25.cs168.io/policies/#collaboration-policy)：已阅读 Projects、Collaboration 及其上下文；政策不构成转载许可。
- [网页链接的旧版 Spring 2024 PDF](https://sp24.cs168.io/assets/projects/transport3.pdf)：21 页文字已读，主要图已检查，仅作历史对照。它的个人完成、环境措辞、允许 import 等约定与 2025 不同，不覆盖本学期规则。
- V. Paxson、M. Allman、H. K. J. Chu、M. Sargent，2011，[RFC 6298](https://www.rfc-editor.org/rfc/rfc6298)，特别是 §2–5；全文已读。
- 阅读与静态断言证据保存于 `sources/packages/TcpLab/`。本页及[无答案指导](#/c/berkeley-cs168-2025/lab/transport?v=guide)为独立中文学习材料；没有授权全文翻译，不公开英文题面副本或学生解答。教材 CC BY-SA 4.0 不适用于本实验题面。
