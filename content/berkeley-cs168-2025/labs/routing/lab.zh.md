# 距离向量路由：让局部信息形成可用路径

本实验要构造一个逐步响应网络变化的 `DVRouter`：先让直连主机互通，再交换距离信息，最后控制环路、传播不可达状态并减少冗余更新。路由的目的地是**主机**，不要求计算到路由器的路径；转发表保存编号端口，而不是下一跳路由器对象。

配套[实现思路与排错指南](#/c/berkeley-cs168-2025/lab/routing?v=guide)帮助你检查不变量，不提供可提交实现。

## 开始前：版本、边界与提交规则

- 先学 [L4 路由原理](#/c/berkeley-cs168-2025/lec/lec04?v=notes)、[L5 距离向量](#/c/berkeley-cs168-2025/lec/lec05?v=notes)、[L6 距离向量续讲](#/c/berkeley-cs168-2025/lec/lec06?v=notes)。官网开头的“Lecture 6 Routing States / Lecture 7 Distance-Vector”是遗留编号，不能直接套在 2025 课表上。
- 官方测试环境为 **Python 3.8**；更新版本由学习者自行承担兼容性风险。本资料只做静态源代码阅读，未运行本机 Python、模拟器或学生测试，未验证任何本机运行时兼容性。
- 可以独立完成，或与一位搭档合作；搭档可沿用 Project 1，也可以更换。遵守[课程合作政策](https://sp25.cs168.io/policies)，不要把他人答案当作自己的实现。
- 仅修改 starter 的 `simulator/dv_router.py`，且只在标记的可填写区域内修改；不得改其他文件、加新文件、加 import、加硬编码全局变量。可以增加 helper methods；Stage 10A 可在构造函数指定区域增加实例状态，但不能删改已有初始化代码。
- 不要由协议代码重设功能开关。测试会选择开关组合。官网演示中临时切换开关是观察实验，不是提交代码中强制开启功能的许可。
- 分阶段保存备份，尤其在 Stage 10 前；后续阶段会改动先前方法。最终只向 Gradescope 的 Project 2 提交 `dv_router.py`。

### 获取与固定版本

下载 [Spring 2025 starter ZIP](https://sp25.cs168.io/assets/projects/proj2/cs168-sp25-proj2-routing.zip)。本次于 2026-11-15 获取的原始压缩包 SHA-256：

```text
6f876ad1703ace22b0f3b43f1e69066f5888784bc63b91a0d31e6ed055e84940
```

文件名中的 2025 是实验版本；获取日期不是授课日期。官网注明题面于 Fall 2024 重写，可能保留错误；旧 Spring 2024 PDF 只作为官网提供的历史入口，不替换本实验要求。

所有下述 Python 命令都从下载包解压后的 **`simulator` 目录**执行。官网示例外层目录名为 `cs168-sp25-proj2-routing`，实际解压工具可能不同，找到包含 `dv_router.py` 的目录即可。

## 先认识运行模型

`self.table` 是 `Table`，以主机对象为键，以不可变的 `TableEntry(dst, port, latency, expire_time)` 为值。更新条目应替换整个条目；键与 `entry.dst` 必须一致。`latency` 是本路由器到目的地的总代价，`expire_time` 是模拟时钟的绝对时间点，不是剩余时长。

`self.ports.get_latency(p)` 给出本地链路代价，`self.ports.get_all_ports()` 给出当前端口。只使用 `api.current_time()` 获取时间；不能使用墙上时钟 `time.time()`。

- `FOREVER = float('+inf')`：时间永不过期，用于直连静态路由。
- `INFINITY = 100`：距离不可达哨兵，不等于 `FOREVER`，也不能机械照搬 RIP 的 16。
- `ROUTE_TTL = 15` 秒；基类定时器间隔为 5 秒。
- `self.send(packet, port=p)` 发数据；`self.send_route(p, dst, latency)` 发一条目的地通告。
- `SPLIT_HORIZON` 与 `POISON_REVERSE` 至多一个为真；二者也可都为假。`POISON_EXPIRED`、`POISON_ON_LINK_DOWN`、`SEND_ON_LINK_UP` 各自控制独立行为。

基类定时回调先 `expire_routes()`，再 `send_routes(force=True)`。收到路由通告时也先处理过期，再调用 `handle_route_advertisement`。不要修改基类或自己重写框架的收包分发。

### 热身：为什么 hub 不够用

`examples/hub.py` 把数据洪泛到所有非入端口。在线性拓扑上可以送达，却也把不属于中间主机的包送给它；有环时会产生大量多余转发。热身不需修改或提交代码。

学习者可自行运行（本资料未执行）：

```sh
python3 simulator.py --start --default-switch-type=examples.hub topos.linear --n=3
python3 simulator.py --start --default-switch-type=examples.hub topos.candy
```

每次启动一个场景，在浏览器打开 `http://127.0.0.1:4444`。在线性场景用终端 `h1.ping(h3)`；也可在图中选源按 `A`、选目标按 `B`，按 `P` 发 ping。观察 ping/pong 和错误接收者日志；无需处理日志中的包 TTL。candy 场景可从 h1a 向 h2b 发包，观察环路。

## 第一部分：本地转发（Stages 1–2）

### Stage 1：安装静态路由

**入口：`add_static_route(host, port)`。** 框架在发现直连主机时调用。端口已由 `handle_link_up` 注册，保留已有断言。为主机建立经该端口、代价等于直连链路代价、到期时间为 `FOREVER` 的条目。

验收重点：先后加入多个直连主机不会覆盖其他目的地；允许非整数链路代价。此时只有表项而没有数据转发逻辑，不能把“表里存在路径”等同于“ping 能到”。

### Stage 2：按表转发

**入口：`handle_data_packet(packet, in_port)`。** 根据 `packet.dst` 查表；没有条目就丢弃（不发送）。条目总代价 **大于或等于 `INFINITY`** 也丢弃；其余情况将原数据包发到选定端口，不洪泛。

官网 Stage 2 的一句描述把判断对象称为“outgoing link latency”，但 Stage 8 的提醒及本 ZIP 的 `test_infinity`、`test_bigger_than_infinity` 明确检查**转发表中的目的地距离**。只检查物理链路成本是不够的。

可用 `topos.simple` 思考同一路由器下的两台主机；Stage 1 时不能转发，Stage 2 后应具备直连互通能力。观察表可用 `print(s1.table)`；自己方法中的调试输出可用 `print(self.table)`。

## 第二部分：学习路径与处理陈旧信息（Stages 3–5）

### Stage 3：发送通告

**入口：`send_routes(force=False, single_port=None)`。** 本阶段暂按调用参数 `force=True, single_port=None` 理解：将每个已知目的地及本机到它的距离向所有当前端口通告。框架负责周期调用，不需创建新的定时机制。发送时不要再次加链路代价；那是接收方的工作。

对比 `h1—s1—h2` 与 `h1—s1—s2—h3`：前者只需静态路由，后者需要学习远端目的地。仅发送而尚未处理通告时，第二种拓扑仍不能正常互通。

### Stage 4：接收通告

**入口：`handle_route_advertisement(route_dst, route_latency, port)`。** 候选总代价是邻居通告值加接收端口的链路成本。以下三种情况接受：

1. 表里尚无该目的地；
2. 通告来自当前所选端口，无论变好、相等还是变坏；
3. 来自其他端口，且候选总代价严格小于当前总代价。

接受后设置到期时间为 `api.current_time() + self.ROUTE_TTL`。其他端口的等价或更差通告应保留当前路由，不能借机延长它的寿命。不要把“严格更优才替换”错误用于当前下一跳的消息；否则坏消息永远无法传播。

等价时保持原路径是稳定性选择。官网建议在 square 上临时试验“相等也换路”，观察同一对主机的包路径变化、可能乱序，再**恢复保持原路的规则**；本实验不要求实现多路径或缓存所有邻居的备用路由。

### Stage 5：删除过期路由

**入口：`expire_routes()`。** 遍历表并删除过期条目，保留未过期和 `FOREVER` 条目。可选用 `self.s_log` / `self.log` 记录删除事件，不计分。

固定骨架 `TableEntry.has_expired` 使用 `current_time() > expire_time`；官网没明确“刚好相等”的边界，现有阶段测试检查的是越过到期时间的情形。设计时写清边界约定，不要把 15 秒理解成每条路由独有的准点回调：真正清理由框架事件触发。

在 candy 中先等收敛，再用 `s4.unlinkTo(s5)`（图形界面选择两路由器后按 `E` 也可）断开链路。没有过期机制时仍使用旧路径；有过期机制后可等待其他路径的通告恢复。此时并未承诺立即收敛。

## 第三部分：环路控制与事件驱动（Stages 6–10）

### Stage 6：Split Horizon，水平分割

**修改 `send_routes`。** 当 `SPLIT_HORIZON` 为真时，不向某目的地的当前下一跳端口通告该目的地；其他端口照常。省略一条通告不等于发一个零代价或无穷代价消息。

在线性三主机场景，收敛后断开 s1—s2，观察 s2、s3 是否会把对方当作到 h1 的出口。这一规则针对相互欺骗的二节点环；不能保证任意拓扑无环。

### Stage 7：Poison Reverse，毒性逆转

**修改 `send_routes`。** 当 `POISON_REVERSE` 为真时，向当前下一跳端口发送该目的地的 `INFINITY`，向其他端口通告正常距离。这只是**该端口的通告视图**，不应污染本机原来可用的转发表条目。

在 double_triangle 中删除 s2—s1、s2—s3、s2—s4，对比不开启规则、水平分割和毒性逆转时的坏消息传播。二者互斥，由配置决定；不要同时启用，更不要认为它们能阻止所有较长环路。

### Stage 8：限制计数到无穷

**修改 `send_routes`。** 任何大于 `INFINITY` 的距离，对外通告时压到 `INFINITY`；等于阈值的值仍然代表不可达。与此同时，Stage 2 必须拒绝总代价达到或超过阈值的数据转发。

在 loopy 中收敛后断开 s1—s2，观察长环中的距离增长。有限阈值限制了增长范围，不是对任意拓扑瞬时无环的证明。内部表值可能是 `INFINITY + 链路代价`，不能因此漏掉不可达判断，也不必为“数值好看”另改接收规则。

### Stage 9：过期时传播 poison

**修改 `expire_routes`。** `POISON_EXPIRED=False` 时继续删除；为真时，将过期条目替换为距离 `INFINITY` 的条目，保留目的地和原端口，并把到期时间设置为当前时间加 `ROUTE_TTL`。这样后续周期通告能继续传播失效信息，而不只是安静地遗忘。

官方把“过一段时间后停止重复通告并最终清除 poison”列为可选、不计分优化，不要误标成必须完成的垃圾回收。有效新通告到来时，仍按 Stage 4 规则允许恢复可达状态。

在线性七主机场景等 s7 学到 h1，再断开 s1—s2。比较只等各节点超时与逐跳传播 poison：恢复速度不再只能依赖每台路由器各自耗尽旧计时器，但传播仍需事件与链路时间。

### Stage 10A：触发式、增量式更新

**修改 `send_routes` 和 `handle_route_advertisement`。** 表因接收通告而更新后，调用 `self.send_routes(force=False)`。`force=False` 时，对每个“出端口、目的地”组合，只发送从未发过或与上一次实际发送内容不同的通告。可以在构造函数 Stage 10A 区域增加 `self.history` 等实例状态。

关键不是“表对象是否换了”，而是“这个邻居将听见的距离是否变了”：仅更新时间戳不需要重新发；毒性逆转后的距离没变也不需要重新发。`force=True` 仍发送所有符合通告策略的条目，并更新发送历史。可使用 helper methods 避免复制多套分支。

官网预期完成 10A 后，Stage 10 的 31 个测试中先通过 28 个，显示 `.........FF.F..................`；这是**官网阶段性预期，不是本资料运行结果**，也不能作为最终完成标准。

### Stage 10B：链路上下线触发

- **`handle_link_up(port, latency)`**：保留已有 `self.ports.add_port`。`SEND_ON_LINK_UP=True` 时，立即向新端口通告完整的当前路由视图，不向其他端口广播；为假时不做这次立即同步。
- **`send_routes(..., single_port=...)`**：参数非 `None` 时只能向指定端口发送。它限制发送范围，与 `force` 的全量/增量含义不同，不能用端口的真假判断替代 `None` 判断。
- **`handle_link_down(port)`**：保留已有 `self.ports.remove_port`。只处理经断开端口的条目；`POISON_ON_LINK_DOWN=False` 时删除它们。为真时改为 poison，采用有限的更新寿命，使失效条目能继续传播，并立即通过 `force=False` 向仍在线邻居做增量通告。不要向已移除端口发包；不受影响的目的地保持不变。

断链 poison 与过期 poison、毒性逆转是三个不同概念。官网 10B 对 poison 的到期时间未重复给出公式；保持与 Stage 9 一致的 `当前时间 + ROUTE_TTL` 是合理状态设计，而不是声称网页对此另有明确边界测试。

完成后 Stage 10 应达到 31/31；仍须保留周期定时器，用于刷新信息和弥补未收到的更新，不能用事件触发完全替代它。

## 验证入口与评分

以下是**供学习者运行的命令**；本次资料制作没有执行它们：

```sh
python3 dv_unit_tests.py 1
python3 dv_unit_tests.py 2
python3 dv_unit_tests.py 3
python3 dv_unit_tests.py 4
python3 dv_unit_tests.py 5
python3 dv_unit_tests.py 6
python3 dv_unit_tests.py 7
python3 dv_unit_tests.py 8
python3 dv_unit_tests.py 9
python3 dv_unit_tests.py 10
```

静态核对测试入口可知，参数 N 实际运行 **Stage 0 到 N 的累计测试**，并非只跑第 N 组。Stage 0 检查未被破坏的骨架，不计分。省略参数默认跑到 10；增加 `-v` 提高详细程度。最终命令 `python3 dv_unit_tests.py 10` 的官方目标是 100/100。每阶段占 10%，阶段内各测试等权；官网明确没有隐藏测试。不能用某个演示 ping 成功代替完整阶段验收，也不能修改测试“修复”协议。

模拟器统一启动形式：

```sh
python3 simulator.py --start --default-switch-type=dv_router topos.simple
```

将最后一个拓扑替换为 `topos.square`、`topos.candy`、`topos.double_triangle`、`topos.loopy`；线性场景使用 `topos.linear --n=3` 或 `--n=7`。这些是官方学习演示，不是本次已经验证的运行结果。

## 引用与来源

- UC Berkeley CS168 Spring 2025，[Project 2: Distance-Vector Routing](https://sp25.cs168.io/proj2/)，完整阅读 Setup、Overview、Hub、Code Overview、Stages 1–10A/10B、Submission。
- 本文为依据官方要求独立编写的中文任务说明，不是获授权的全文译本。
- 同页链接的 [2025 ZIP](https://sp25.cs168.io/assets/projects/proj2/cs168-sp25-proj2-routing.zip)：完整静态阅读 `simulator/dv_router.py`、`cs168/dv.py`、`dv_unit_tests.py`；另核对 `sim/api.py`、`sim/core.py` 的时间/发送接口及 `examples/hub.py`。
- [Spring 2025 官方课表](https://sp25.cs168.io/)用于纠正先修课编号。教材与实验不是同一版本或同一许可对象。
- 实验网页和 starter 的整体再发布/翻译许可未确认，不套用教材 CC BY-SA。本文为独立中文学习说明；源文件归原作者所有。未提供学生实现，未执行任何测试或模拟器。
