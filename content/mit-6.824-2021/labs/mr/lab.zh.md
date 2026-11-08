---
source: MIT 6.5840 Spring 2026，Lab 1: MapReduce；2026-11-08 官方页面快照
status: 官方实验要求与提示中译完成，覆盖 Introduction 至 No-credit challenge exercises；合并重复示例输出，环境安装集中在公共资料。接口已对照固定代码；实验测试未运行。
license: MIT 6.5840 课程网站 CC BY 3.0 US；中文翻译与排版整理，编者补充另行标明。
---

# Lab 1：MapReduce 实验说明

## 1. 你要构建什么

在这个实验中，你将构建一个 MapReduce 系统：实现 worker 进程，让它调用应用的 Map、Reduce 函数，并负责读写文件；实现 coordinator（协调器）进程，让它向 worker 分配任务，并处理 worker 失败。

系统与 MapReduce 论文描述的设计相近。实验使用 **coordinator** 一词，对应论文中的 **master**。

## 2. 开始之前

先完成 Go 环境配置并获取实验仓库。本课程采用 **Go 1.22 或更新版本**，固定 2026 代码提交 `513cac0aef010750fc74688da8a395974a83cf7a`；完整克隆与版本切换命令见[公共资料](#/c/mit-6.824-2021)。以下假设你的仓库位于 `~/6.5840`。

官方提供一个顺序实现 `src/main/mrsequential.go`：它在单个进程里逐个执行 Map 和 Reduce。还提供了词频应用 `src/mrapps/wc.go` 和文本索引应用 `src/mrapps/indexer.go`。

先运行顺序词频程序：

```bash
cd ~/6.5840/src/main
go build -buildmode=plugin ../mrapps/wc.go
go run mrsequential.go wc.so pg*.txt
LC_COLLATE=C sort mr-out-0
```

输入是名为 `pg-xxx.txt` 的文本文件；输出写在 `mr-out-0`。排序后的开头应类似：

```text
A 509
ABOUT 2
ACT 8
ACTRESS 1
```

可以借用 `mrsequential.go` 中的代码，并阅读 `mrapps/wc.go`，理解 MapReduce 应用的写法。

官方可能更新实验代码。请保留提供的文件位置，以便接收和合并更新；可以按要求增加实现，也可以把自己的新函数放在新文件中，不要搬走原有代码。

**编者版本说明**：官网建议学期内通过 `git pull` 接收更新；本学习路线先固定上述提交，升级步骤统一见公共资料，避免代码和教程接口漂移。官网示例会先删除旧的 `mr-out*`；手动重跑时也应先清理自己上一次实验的输出，避免与本次结果混在一起。

## 3. 你的任务

实现一个分布式 MapReduce，由一个协调器和一个或多个并行 worker 构成。真实系统把 worker 放在不同机器上，本实验把所有进程运行在同一台机器上，并通过 RPC 通信。

每个 worker 循环完成这些动作：请求任务，读取任务输入，执行计算，把结果写到一个或多个文件，再请求新任务。协调器必须发现某个任务在合理时间内尚未完成，并把它重新交给其他 worker。**本实验的等待时间取 10 秒。**

主要程序入口为：

- `src/main/mrcoordinator.go`；
- `src/main/mrworker.go`。

**不要修改这两个入口文件。** 实现应放在 `src/mr/coordinator.go`、`src/mr/worker.go` 和 `src/mr/rpc.go` 中。

### 3.1 手动运行分布式词频

在 `src/main/` 构建词频插件：

```bash
cd ~/6.5840/src/main
go build -buildmode=plugin ../mrapps/wc.go
```

确认已清理前一次运行的输出后，在一个终端启动协调器：

```bash
go run mrcoordinator.go sock123 pg-*.txt
```

`sock123` 是协调器接收 RPC 的 socket 名称。后面的每个输入文件对应一个 split，也就是一个 Map 任务。

在其他终端进入**同一个 `src/main/` 目录**，启动一个或多个 worker：

```bash
go run mrworker.go wc.so sock123
```

worker 与协调器都结束后，检查各个 `mr-out-*` 文件。把这些输出合在一起排序，应与顺序实现的结果一致：

```bash
cat mr-out-* | LC_COLLATE=C sort
```

**编者核对**：2026 入口实际要求显式 socket 参数。源码顶部的旧运行注释省略了它，不能照那条注释启动；这里的命令已核对 `os.Args` 的实际解析。

### 3.2 官方测试

官方提供全部评分测试，代码在 `src/mr/mr_test.go`。在实验仓库 `src/` 运行：

```bash
cd ~/6.5840/src
make mr
```

测试检查词频、倒排索引的输出正确性，Map 与 Reduce 的并行执行，以及 worker 在任务中途崩溃后的恢复。固定版本中的测试名称为：

```text
TestWc
TestIndexer
TestMapParallel
TestReduceParallel
TestJobCount
TestEarlyExit
TestCrashWorker
```

初始骨架还没有实现调度和输出，直接运行会卡在第一个测试。官网给出一个用于观察失败的临时改动：把 `Done()` 中的 `ret := false` 改为 true，让协调器立即退出；此时测试会报告没有产生 `mr-out-X`。这只是在演示骨架尚未完成，不是正确实现方式。

完成后，这七项测试应全部通过，末尾出现 `PASS`。官网展示的运行秒数和日期只是一次示例，不是验收阈值。

取决于你的 worker 退出方式，协调器结束后可能出现少量连接拒绝错误，例如：

```text
dial unix ...: connect: connection refused
```

每项测试结束时少量此类消息可以接受：此时协调器的 RPC 服务已经退出。

**编者提示**：使用本节的 Go 命令。页面通用命令框里的 `make qemu`、`make grade` 是其他课程的命令，不适用于本实验。

## 4. 必须遵守的规则

1. **Map 输出要分成 `nReduce` 个桶。** `nReduce` 是 `main/mrcoordinator.go` 传给 `MakeCoordinator()` 的 Reduce 任务数量。每个 Map 任务生成 `nReduce` 个中间文件，供对应的 Reduce 任务读取。
2. **最终输出命名为 `mr-out-X`。** `X` 是 Reduce 任务编号。
3. **每次 Reduce 函数的输出占一行。** 用键和值按 Go 的 `"%v %v"` 格式输出，并换行；可查看 `mrsequential.go` 中标注正确格式的位置。偏离格式会导致测试失败。
4. **修改范围以 `mr/` 的三个实现文件为主。** 可以临时修改其他文件帮助测试，但最终必须能与官方原始文件配合运行，评分使用原始版本。
5. **中间 Map 输出放在当前目录。** 之后执行 Reduce 的 worker 要能读取它们。
6. **实现 `Coordinator.Done()`。** 仅当整个 MapReduce 作业完全结束时返回 true；主程序随后退出。
7. **作业完全结束后 worker 也应退出。** 官方建议利用 RPC 联系失败判断协调器已退出，或者由协调器返回一种“请退出”的伪任务。暂时没有可分配任务时，不应将其误当成整个作业完成。

## 5. 官方提示

### 5.1 从一次任务请求开始

先修改 `Worker()`，让它通过 RPC 向协调器请求任务；再让协调器回复一个尚未开始的 Map 输入文件名；然后让 worker 读取这个文件，并仿照顺序实现调用应用 Map。

应用的 Map 和 Reduce 函数由 Go 的 plugin 包从 `.so` 文件中动态加载。修改 `mr/` 内的内容后，通常需要重新编译插件，例如：

```bash
go build -buildmode=plugin ../mrapps/wc.go
```

`make mr` 会自动构建测试所需的插件。可以只运行匹配名称的单项测试，例如在 `src/` 下：

```bash
make RUN="-run Wc" mr
```

这里 `RUN` 的内容被传给 `go test`。（官网该命令后的多余反引号已修正。）

### 5.2 中间文件与数据编码

实验依赖 worker 共享文件系统。在同一机器上运行很直接；如果分布在不同机器上，就需要 GFS 一类的共享存储方案。

一种合理的中间文件命名是 `mr-X-Y`：`X` 表示 Map 任务编号，`Y` 表示 Reduce 任务编号。

中间键值对必须采用能够正确读回的编码。一种选择是 Go 的 `encoding/json`：对每个键值对调用 `json.Encoder.Encode`，读取时逐个调用 `json.Decoder.Decode`。官方提示的核心片段是：

```go
enc := json.NewEncoder(file)
// 对每个要写入的键值对 kv：
err := enc.Encode(&kv)
```

```go
dec := json.NewDecoder(file)
// 反复读取 KeyValue，直到文件结束：
var kv KeyValue
err := dec.Decode(&kv)
```

**编者补充**：以上只是 API 提示，不是完整循环。实际实现要区分正常 `io.EOF` 与损坏数据、I/O 错误；官方简短示例把遇到任意解码错误都写成停止读取，不能据此把半个文件当成成功。

Map 可使用 `worker.go` 中的 `ihash(key)` 为键选择 Reduce 任务。读取 Map 输入、排序中间键值对、写最终输出等操作，可以借用顺序实现中的代码。

### 5.3 并发与等待

协调器作为 RPC 服务器，会并发处理请求。不要忘记给共享数据加锁。

worker 有时需要等待，例如最后一个 Map 完成前不能开始 Reduce。一种方式是 worker 在请求之间 `time.Sleep()`，定期询问；另一种方式是协调器的相关 RPC handler 等待，使用 `time.Sleep()` 或 `sync.Cond`。Go 会并发执行各个 RPC handler，某个 handler 等待本身不必阻止其他请求处理。

**编者补充**：这不意味着可以持有全局互斥锁一直睡眠；若等待者不释放别人完成任务所需的锁，系统仍会卡住。

### 5.4 超时重派与崩溃

协调器无法可靠区分已崩溃、仍存活但停滞、或正在执行却过慢的 worker。可行办法是等待一定时间后重新派发任务。**本实验等待 10 秒后可假定 worker 已失效，尽管它实际可能还活着。**

若实现论文 §3.6 的备份任务，请注意：测试会检查无崩溃时是否调度了多余任务。备份只能在较长等待之后启动，例如 10 秒后。

可用 `mrapps/crash.go` 插件测试恢复，它会在 Map 和 Reduce 函数中随机退出。

为避免崩溃留下半写文件，论文使用临时文件，全部写完后再原子重命名。Go 可以通过 `ioutil.TempFile`，或 Go 1.17 之后的 `os.CreateTemp` 创建临时文件，再用 `os.Rename` 发布。

### 5.5 RPC 结构体

Go RPC 只传输名称以大写字母开头的结构体字段，嵌套结构里的字段同样如此。

每次调用 `call()` 时，回复结构体都应处于零值状态：

```go
reply := SomeType{}
call(..., &reply)
```

不要预先给 reply 填入非零字段，或不清空就复用旧回复；RPC 编解码可能让你静默得到错误值。

## 6. 不计分挑战

- 自己实现一个 MapReduce 应用。可参考 `mrapps/`，例如论文 §2.3 的 Distributed Grep。
- 让协调器与 worker 真正在不同机器上运行。需要把 Unix socket RPC 改为 TCP/IP，并解决文件共享；官方给出的环境例子包括共享 AFS 的 MIT Athena 机器，或云主机与 S3 存储。

这些是开放扩展，不是完成基础实验的前提。若选择对象存储，要重新设计读写和发布方式，不能直接假设它具有本地文件系统的 `rename` 接口。

## 引用与来源

- MIT 6.5840 教学团队，Spring 2026，[Lab 1: MapReduce](https://pdos.csail.mit.edu/6.824/labs/lab-mr.html)。官方[课程首页](https://pdos.csail.mit.edu/6.824/)标注 [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/)。本页翻译并重新排版，合并重复终端输出，省略导航与重复安装命令；编者差异说明均已标出，不代表 MIT 审核或认可。
- 官方公共入口：[Go 环境](https://pdos.csail.mit.edu/6.824/labs/go.html)、[实验建议](https://pdos.csail.mit.edu/6.824/labs/guidance.html)、[合作政策](https://pdos.csail.mit.edu/6.824/labs/collab.html)、[课程提交入口](https://pdos.csail.mit.edu/6.824/labs/submit.html)。这些作为官方链接保留，本页不声称翻译了它们。
- 页面快照 `sources/lab-mr-2026.html`，抓取于 2026-11-08；Last-Modified 为 2026-02-01。固定代码来自 `git://g.csail.mit.edu/6.5840-golabs-2026`，提交 `513cac0aef010750fc74688da8a395974a83cf7a`。
- 已核对 `src/Makefile`、`src/main/mrcoordinator.go`、`mrworker.go`、`src/mr/` 骨架与 `mr_test.go`。本批只制作学习资料，未实现或运行实验测试。
