---
source: UC Berkeley CS168 Spring 2025 官方课表、课程教材及项目页面
license: 教材译文 CC BY-SA 4.0；其他材料逐来源标注，不继承教材许可
status: 本页说明学习路线与版本边界；逐项获取、阅读、内容和验证状态见 status.json
---

# 公共资料

## 先明确要解决的问题

互联网不承诺每个包都按时、按序、恰好一次到达。学习这门课的主线是：**每一层向上提供什么服务，需要保存什么状态，在丢包、变化和资源不足时怎样维持其约束。**

三个实验分别让你观察网络、在模拟器中选路、在不可靠网络上实现可靠传输。它们不是完整生产协议栈，也不要求实现后续讲到的全部优化。

## 学习路线

|阶段|主课|配套练习|实验落点|
|---|---|---|---|
|把一个包送入网络|L1–3：分层、设计原则、链路|讨论 01–02|Traceroute 1A/1B：解析响应，区分观测与推断|
|在变化的图上选路|L4–8：路由状态、DV、LS、编址、路由器|讨论 03–04|Distance-Vector：逐阶段维护路由表与通告|
|跨自治系统协作|L9–10：BGP 策略与实现|讨论 05|用策略解释可达性，而不是只找最短路|
|从数据包到可靠字节流|L11–12：可靠性与 TCP|讨论 06|Transport 3A/3B：连接、序号、窗口、重传|
|共享有限带宽|L13–15：拥塞控制|讨论 07|与流量控制区分；**不属于 Transport 必做实现**|
|一次 Web 请求如何发生|L16–20：DNS、HTTP、以太网及端到端协议|讨论 08–09|把名称、地址、端口、邻居和安全身份串起来|
|大规模协作与特殊介质|L21–27：数据中心、SDN、主机、组播、集体通信、无线、蜂窝|讨论 10–12|分析拓扑、路径、同步与介质限制|

以「课程资料」中的官方文字教材为学习主线；「课程笔记」用于抓住核心问题、推导与自测，视频按需回看，不必等字幕才能继续学习。讨论先自行推导，再展开解析。期中、期末用于诊断知识缺口，不以历史考试日期安排个人进度。

分 P 较多的讲次已有连续阅读入口：[L10：BGP 与 IP 首部](#/c/berkeley-cs168-2025/lec/lec10?v=notes)把 19 P 对应主题串成三条主线；[L11：可靠传输](#/c/berkeley-cs168-2025/lec/lec11?v=notes)把 15 P 涉及的服务抽象与可靠性机制接到现有文字章节。无需把每个短视频当成一门独立的小课，也不另造一份重复资料。

### 先修与跨课衔接

- Python：类、容器、字节与位运算；能阅读函数接口、异常和测试输出。
- Unix：工作目录、解压、终端命令与虚拟环境。网络抓包涉及的权限与外网访问不是普通单元测试。
- 基本算法：图、最短路径、数量级分析；公式中区分 bit 与 byte、秒与毫秒。
- [操作系统工程](#/c/mit-6.s081-2020)：系统调用、缓冲区与并发是主机网络的基础。
- [分布式系统](#/c/mit-6.824-2021)：网络可靠性不等于 RPC 恰好执行一次，更不等于复制一致性。
- [从零构建语言模型](#/c/stanford-cs336-2026)：集体通信解释分布式训练中的数据交换；本课程不扩展训练实现任务。

## 固定版本，不混用学期

|对象|本路线版本|如何复现|
|---|---|---|
|讲次、讨论、考试|Spring 2025|保留官方 L1–27 编号；12 组讨论与两套考试均按当学期题号|
|视频|2025 课表实际链接|25 个单片，加 L10 的 19 P 和 L11 的 15 P，共 59 个视频条目|
|教材|`0b8208742d31df7fc3d53a0cd94fdd4e04f8d47e`|2026-11-15 固定源码快照；**不是 2025 历史版**|
|项目|Spring 2025 三份 starter ZIP|各实验说明与来源清单登记下载 URL 和 SHA-256，不虚构 Git commit|
|参考卡|无年份的官方 URL 快照|与 2025 试卷区分；具体版本和勘误见考试复习资料|

教材源码最新提交日期为 2026-10-01，含 IPv4 协议号 TCP=6、UDP=17 的勘误。PDF 入口自述更新于 2024-11，不把它视为比固定 HTML/源码更完整。若课堂与后来的教材表达不同，分别记录而不改写成同一年代的材料。

L10、L11 的页头入口指向官方播放列表，显示已核实分 P 的合计时长；分 P 索引各按自身时长记录，不拼成不存在的长视频。字幕受阻时不生成课堂分段时间轴。其他平台没有经官网确认的入口时不添加转载。

官网课表与上传标题有三处需要区分：L17 指定的是 FA24 录像；L20 的录像题名为 Datacenter Topology，与课表续讲题名不同；L24 的上传标题标作 Lecture 25。页头保留官网链接并注明差异，不据标题猜测课堂内容或擅自换片。

## 教材索引：每个小节只展开一次

课程资料承载指定教材中文译文，课堂整理承载可核实的课堂内容，课程笔记承载独立推导和自测。公共资料不复制整本教材。L6、L15、L20 的指定阅读分别复用 L5、L14、L19；这些讲次没有独立教材正文不是漏章。

|归属讲次|独占章节|共享讲次|
|---|---|---|
|[L1：互联网分层](#/c/berkeley-cs168-2025/lec/lec01?v=materials)|intro、layers、headers|—|
|[L2：互联网设计原则](#/c/berkeley-cs168-2025/lec/lec02?v=materials)|architecture、sharing-resources|L3|
|[L3：链路与资源共享](#/c/berkeley-cs168-2025/lec/lec03?v=materials)|links|—|
|[L4：路由原则与状态](#/c/berkeley-cs168-2025/lec/lec04?v=materials)|intro、model、solutions|—|
|[L5：距离向量路由](#/c/berkeley-cs168-2025/lec/lec05?v=materials)|distance-vector|L6|
|[L7：链路状态与编址](#/c/berkeley-cs168-2025/lec/lec07?v=materials)|link-state、addressing|—|
|[L8：路由器实现](#/c/berkeley-cs168-2025/lec/lec08?v=materials)|router|—|
|[L9：BGP：自治系统与策略](#/c/berkeley-cs168-2025/lec/lec09?v=materials)|autonomous-systems、bgp|—|
|[L10：BGP 实现与 IP 首部](#/c/berkeley-cs168-2025/lec/lec10?v=materials)|bgp-implementation、ip-header|—|
|[L11：可靠传输原理](#/c/berkeley-cs168-2025/lec/lec11?v=materials)|reliability|—|
|[L12：TCP 设计与实现](#/c/berkeley-cs168-2025/lec/lec12?v=materials)|tcp-design、tcp-implementation|—|
|[L13：拥塞控制原理](#/c/berkeley-cs168-2025/lec/lec13?v=materials)|cc-principles、cc-design、cc-implementation|—|
|[L14：拥塞控制模型与路由器辅助](#/c/berkeley-cs168-2025/lec/lec14?v=materials)|throughput-model、cc-issues、router-based-cc|L15|
|[L16：DNS：分布式命名](#/c/berkeley-cs168-2025/lec/lec16?v=materials)|dns|—|
|[L17：HTTP：Web 协议](#/c/berkeley-cs168-2025/lec/lec17?v=materials)|http|—|
|[L18：以太网与生成树](#/c/berkeley-cs168-2025/lec/lec18?v=materials)|ethernet、l2-routing|—|
|[L19：ARP、DHCP、NAT 与 TLS](#/c/berkeley-cs168-2025/lec/lec19?v=materials)|arp、dhcp、nat、tls、end-to-end|L20|
|[L21：数据中心拓扑与拥塞](#/c/berkeley-cs168-2025/lec/lec21?v=materials)|topology、datacenter-cc|—|
|[L22：数据中心路由、编址与虚拟化](#/c/berkeley-cs168-2025/lec/lec22?v=materials)|datacenter-routing、datacenter-addressing、virtualization|—|
|[L23：SDN 与主机网络](#/c/berkeley-cs168-2025/lec/lec23?v=materials)|datacenter/sdn、datacenter/host-networking|—|
|[L24：组播](#/c/berkeley-cs168-2025/lec/lec24?v=materials)|index、intro、ip-multicast-service-model、dvmrp、cbt、ip-multicast-challenges、overlay-multicast|—|
|[L25：集体通信](#/c/berkeley-cs168-2025/lec/lec25?v=materials)|collective-operations、collective-implementations|—|
|[L26：无线网络](#/c/berkeley-cs168-2025/lec/lec26?v=materials)|wireless/wireless-links|—|
|[L27：蜂窝网络](#/c/berkeley-cs168-2025/lec/lec27?v=materials)|wireless/cellular|—|

Multicast 的指定入口是一个目录，阅读范围包括其六个实质子章，而不是只翻译目录标题；两篇集体通信章节归 L25。

Host Networking、Wireless、Cellular 的旧 special-topics 页面在固定版本仅有迁移链接；材料已沿链接取得同一提交的真实正文。SDN 末节原作者未写完，材料保留全部现存正文并明确标记源缺口，不把迁移空壳或未写内容算作完整章节。

## 实验环境与边界

|实验|官方测试过的 Python 版本|编辑入口|本路线边界|
|---|---|---|---|
|[Traceroute](#/c/berkeley-cs168-2025/lab/traceroute?v=zh)|3.11|`traceroute.py`|1A/1B 测试不公开提供本地版，官方入口为 Gradescope；不擅自执行 raw socket 或公网探测|
|[Distance-Vector](#/c/berkeley-cs168-2025/lab/routing?v=zh)|3.8|`simulator/dv_router.py`|十阶段协议实现；本地模拟器而非修改真实路由器|
|[Transport](#/c/berkeley-cs168-2025/lab/transport?v=zh)|3.7|`ext/cs168p2/student_socket.py`|3A=Stages 1–5，3B=Stages 6–9；可靠传输，不含拥塞控制|

这些版本是官方说明的历史测试环境，不代表本机已验证，也不保证任意新版本兼容。按实验页实际入口建立独立环境，保留 starter ZIP。不要把不同学期的框架、测试和说明混拼。

Traceroute ZIP 只含 `README.md`、`traceroute.py`、`util.py`。官方 1A/1B 自动评分在 Gradescope，离线自学者不能把自行编写的检查当作官方验收通过。固定 ZIP 的 SHA-256：

```text
ed5848a5914f4f321167f96c2c0708a5140eb4f2555252308b57680014f105a6
```

Distance-Vector 固定 ZIP 的 SHA-256：

```text
6f876ad1703ace22b0f3b43f1e69066f5888784bc63b91a0d31e6ed055e84940
```

Transport 固定 ZIP 的 SHA-256：

```text
10f7d6ede628be7c0769e03470e598c1046c222e08d1fdafbf663a80ca8aded3
```

Transport 的 30 个阶段配置对应 25 个实际 Python 测试模块，部分配置复用模块；这不等于测试文件缺失。仅提交 `student_socket.py`，所有实验命令从其所在的 `ext/cs168p2` 目录运行。此处只记录静态来源，不报告运行通过。

实验页的通用命令卡来自站点共享界面，若显示 `make qemu` / `make grade`，**不要用于 CS168**。以实验说明内的 Python/POX 命令和工作目录为准。实验指导只给状态、接口、分阶段思路与错误定位，不提供可提交解答。

准备说明和静态核对代码，不等于学习者实现通过。三个项目的学习者完成情况独立记录为 `not_attempted`；本站构建通过也不能当作实验测试通过。官方要求不得公开项目答案。

## 讨论与考试用法

讨论顺序与主课对应。每组先定位官方题号，自己画状态/拓扑或列事件序列，最后再展开答案检查理由。图题必须使用题面的连边、方向、成本与初始状态，不能按常见教材例题补猜。

|练习入口|实际题卷主题|
|---|---|
|[讨论 01](#/c/berkeley-cs168-2025/lec/disc01?v=notes)|分层观察、体系结构取舍、Traceroute|
|[讨论 02](#/c/berkeley-cs168-2025/lec/disc02?v=notes)|链路时延、流水线、统计复用|
|[讨论 03](#/c/berkeley-cs168-2025/lec/disc03?v=notes)|距离向量、水平分割、失效与超时|
|[讨论 04](#/c/berkeley-cs168-2025/lec/disc04?v=notes)|链路状态、暂态环路、CIDR|
|[讨论 05](#/c/berkeley-cs168-2025/lec/disc05?v=notes)|BGP 信息传播、商业策略与可达性|
|[讨论 06](#/c/berkeley-cs168-2025/lec/disc06?v=notes)|TCP 字节编号、重传、窗口与 ACK 语义|
|[讨论 07](#/c/berkeley-cs168-2025/lec/disc07?v=notes)|拥塞窗口事件、吞吐模型、DNS 缓存|
|[讨论 08](#/c/berkeley-cs168-2025/lec/disc08?v=notes)|DNS、HTTP 连接、代理缓存；实际无 Ethernet/STP 题|
|[讨论 09](#/c/berkeley-cs168-2025/lec/disc09?v=notes)|DHCP、ARP、逐跳地址与 NAT|
|[讨论 10](#/c/berkeley-cs168-2025/lec/disc10?v=notes)|STP、Clos、ECMP、虚拟网络封装|
|[讨论 11](#/c/berkeley-cs168-2025/lec/disc11?v=notes)|主机性能、SDN 抽象、租户解复用、RDMA|
|[讨论 12](#/c/berkeley-cs168-2025/lec/disc12?v=notes)|组播树、集体通信正确性与成本模型|

- [期中复习](#/c/berkeley-cs168-2025/lec/review-midterm?v=notes)：按 2025 期中全部 64 个小题定位，保留官方评分歧义。
- [期末复习](#/c/berkeley-cs168-2025/lec/review-final?v=notes)：按 2025 期末全部 64 个小题定位，区分题设模型与真实协议边界。
- 六次 HW 的主题依次为 Architecture、Routing、Transport、Applications/End-to-End、Datacenters、Special Topics。课表只列名称和截止日，Policies 指向 Gradescope 提交；这些条目不是已取得的公开题面。不要把自测题或讨论题标作官方 HW。

### 六次 HW 的公开性边界

|作业|主题|获取结果|
|---|---|---|
|HW1|Architecture|公告有官方作业入口；匿名访问跳转登录，未取得题面|
|HW2|Routing|公告有官方作业入口；匿名访问跳转登录，未取得题面|
|HW3|Transport|课表与公告列出名称和截止日；未找到对应公开题面或直接作业 URL|
|HW4|Applications / End-to-End|公告有官方作业入口；匿名访问跳转登录，未取得题面|
|HW5|Datacenters|公告有官方作业入口；匿名访问跳转登录，未取得题面|
|HW6|Special Topics|公告有官方作业入口；匿名访问跳转登录，未取得题面|

自学者可用公开讨论与考试练习这些主题，但它们不能替代“官方 HW 已完成”的记录。不要为访问题面使用他人凭证。2025-04-28 公告将期末范围排除无线、蜂窝；本路线仍学习 L26–27，不因历史考试范围删课。

## 协议速查卡：单位与适用条件

用速查卡确认字段宽度、偏移单位和公式假设，不以记住图形替代协议推理。

### 首部定位：字节偏移不是看图量出来的

- 第一页列 IPv4、IPv6、UDP、TCP，第二页列 ICMP。协议首部图的括号数字和左边偏移以 bit 为单位；IPv4/TCP 的 Hdr Len 值却按 4-byte word 计。值为 5 才对应 20 字节，Options 会改变实际载荷起点，不能永远从第 20 字节后解析 UDP/TCP。
- IPv4 的 Total Length 包括 IPv4 首部与载荷；UDP Length 包括 UDP 首部与载荷；IPv6 Payload Length 不含基本 40 字节 IPv6 首部。名称里都出现 length，不代表相同计数范围。IPv6 图是基本首部，扩展首部需顺着 Next Header 理解，不能把 Next Header 永远直接当成最终传输层编号。
- IPv4 图包含版本、IHL、服务字段、总长度、标识、标志、分片偏移、TTL、Protocol、首部校验和、源/目的地址与可选项。Protocol 的 1/6/17 分别是 ICMP/TCP/UDP，不是端口号；IPv4 checksum 只保护首部，不保护 IP 载荷。分片偏移字段的位宽为 13 bit，不代表它的数值按单字节计（IPv4 片偏移用 8 字节单位）。
- IPv6 图包含版本、Traffic Class、Flow Label、Payload Length、Next Header、Hop Limit 与 128-bit 源/目的地址；不要把 IPv4 的首部 checksum、路由器分片行为搬到此基本首部。
- UDP 端口各 16 bit，首部共 8 字节；TCP 的序号/确认号各 32 bit，ACK 是下一期待序号，不是“刚收到的包号”。TCP 图中的 advertised window 是接收端通告的流量控制窗口，不是发送端拥塞窗口 CWND。图把 reserved/flags 作课程级简化，字段占位不是全部标准标志与扩展行为说明。
- ICMP 的 Type/Code/Checksum 与后续 32-bit 区域按具体消息类型解释；卡片的“rest 全零”明确限定 **for this class**，不能推广成所有 ICMP。所列 Port Unreachable 为 Type 3/Code 3，TTL Exceeded 为 Type 11/Code 0。ICMP 错误载荷可引用原 IP/传输首部，所以引用中的 UDP 端口不应因为外层回复方向而交换。

### 以太网和速率：同一张卡也会换单位

以太网示意图使用 byte，而不是 bit：前导码、SFD、MAC、Type、FCS 等尺寸不能照搬上方首部图单位。IPG 标作 12，表示 12 字节时间的帧间间隔，不是实际传输的 12 字节帧字段；前导码/SFD 也不应混入通常从目的 MAC 开始计算的 MAC 帧长度。求在线吞吐时是否计入这些开销，必须先说明统计边界。FCS 是帧校验，不是确认或重传机制。

SI 表采用十进制幂：m、μ、n、p 对应 10^-3 到 10^-12，k、M、G、T 对应 10^3 到 10^12。bps 是 bit/s，B/s 是 byte/s，相差 8 倍；不要把 kilo 自动替换为 1024。

### TCP 吞吐公式：根号里外不要串位

第二页实际图形中公式为：

$$
T\approx\sqrt{\frac{3}{2}}\,
\frac{\mathrm{MSS}}{\mathrm{RTT}\sqrt p}.
$$

其中 p 为丢包概率。纯文本抽取遗漏了该公式，不能把缺失文本误记成卡片没有公式，也不能误读为 MSS/(RTT·p) 或把 3/2 移到根号外。MSS 若用字节、RTT 用秒，结果为 B/s；需要 bit/s 时再乘 8。

这是一类长流、稳定 RTT、拥塞避免锯齿、以快速恢复为主且忽略超时等因素的近似模型，不是所有 TCP/短流/无线链路的保证。p=0 不能直接作为有限链路的无限吞吐结论；实际还受瓶颈容量、接收窗口、主机与应用限制。推导和假设见[第 14 讲](#/c/berkeley-cs168-2025/lec/lec14?v=notes)。

## 已知版本陷阱

1. 2025 首页的 Project 1B 链到 `/proj2/`；正确内容在 `/proj1/proj1b/`。
2. Project 2 页面残留旧讲次编号；按距离向量主题回到本路线 L4–6，而不是套用它的数字。
3. 考试页面含期末标题与 “scope of the midterm” 等行政残留；复习范围以实际卷面为准。
4. 参考卡曾修正 UDP length 名称、TCP checksum 与 urgent pointer 的 16-bit 宽度；不能只看图的版本号。
5. 字幕间隙不等于静音。没有音画核验，不能据字幕缺字断言老师没有讲。

## 引用与来源

- UC Berkeley，CS168 Spring 2025：[课表](https://sp25.cs168.io/)、[Policies](https://sp25.cs168.io/policies/)、[Resources](https://sp25.cs168.io/resources/)。教师为 Peyrin Kao、Sylvia Ratnasamy；嘉宾 Rob Shakir。具体视频讲者以逐视频核验为准。
- Peyrin Kao，基于 Sylvia Ratnasamy、Rob Shakir 等人的讲授：[Introduction to the Internet: Architecture and Protocols](https://textbook.cs168.io/)。固定 [源码提交](https://github.com/berkeley-cs168/textbook/tree/0b8208742d31df7fc3d53a0cd94fdd4e04f8d47e)，[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。本站指定教材译文为中文改编，沿用该许可；翻译、校注和图注变更在各资料页标明。
- 视频、幻灯片、题卷、项目说明和 starter code 各有独立版权边界。公开访问不等于获准全文再发布；未核实许可者只提供原创导读、约束整理、题号定位与必要短引，不冒称授权全文译本。
- [官方两页参考卡](https://assets.cs168.io/cs168-reference-card.pdf)：已读全部文字与两页图形。可见标识为 Version 1.2、Revised May 07, 2025，但 PDF 元标题仍为 `[CS168 FA24] Exam Reference Card`；不因旧元标题改归学期，也不据可见日期声称已取得考试当日相同字节的历史存档，尤其不能倒推为期中随卷版本。参考卡未确认开放再发布许可，此处仅作原创阅读提示。
- 12 份讨论、两套考试均提供原创逐题导读，而非原题全文翻译。期中卷与解答还明确禁止分享、上传、分发；本站仅链接官方原件，不复制原图、整套选项或代码框架，教材许可不扩展到这些试题。
- `sources/` 保存本地研究证据，不由站点 Markdown 收集。许可不明的字幕与原件不因此获得公开提交许可；本轮不提交或推送。
- 来源、阅读范围、字幕/音画缺口和页面验证分别记入 `sources/manifest.json` 与 `status.json`；下载、阅读、成品、验收不是同一个状态。
- [2025 官方公告](https://sp25.cs168.io/announcements/)：全文核对。HW 官方入口为 [HW1](https://www.gradescope.com/courses/943003/assignments/5719288)、[HW2](https://www.gradescope.com/courses/943003/assignments/5807210)、[HW4](https://www.gradescope.com/courses/943003/assignments/5972093)、[HW5](https://www.gradescope.com/courses/943003/assignments/5972127)、[HW6](https://www.gradescope.com/courses/943003/assignments/5972161)，2026-11-15 逐个匿名访问均重定向 Gradescope 登录页，未取得题面。HW3 无已核实直达链接。公告 HW6 截止日与首页不一致，不用该历史日期安排自学。
