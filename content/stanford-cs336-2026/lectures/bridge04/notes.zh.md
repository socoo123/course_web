---
title: "Python 实验工程：让一个小结果有来路"
lectureId: bridge04
kind: "编者先修桥接；非 Stanford 官方讲次"
before: lec01
sourceVersion: "CPython v3.14.0；CS336 讲义 de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e；A1 a158843b20107949f1a8d7df1b05cd33b9166712"
status: "三个标准库微例已在 Python 3.11.8 执行并核对结果；不是官方作业实现或复现。"
---

# Python 实验工程：让一个小结果有来路

## 学习门槛与出口

会写变量、`if`、`for`、函数，能从终端运行一个 `.py` 文件即可。本文补齐四件事：**用了哪个 Python、正在处理什么单位、数据能否再读一遍、结论留下了什么证据。** 不搭实验平台，不下载训练数据，也不实现 A1 的 tokenizer。

学完后应能解释：“同一文件为什么有三种长度”“第二遍统计为何变成零”“别人怎样知道我统计的确实是那份输入”。

## 1. 环境隔离：先确认解释器，再讨论依赖

虚拟环境是在现有 Python 上建立的独立包目录。它默认隔离第三方包，不是虚拟机，也不是不可信代码的安全沙箱。**激活只是调整命令查找路径，不是使用虚拟环境的必要条件。**

下面是 POSIX shell 的教学操作；选择一个新的练习目录，环境尚不存在时再创建：

```bash
python3 -m venv .venv
.venv/bin/python -c 'import sys; print(sys.executable); print(sys.version); print(sys.prefix != sys.base_prefix)'
```

最后一项预期为 `True`；解释器路径应指向这个环境。Windows 对应可执行文件通常是 `.venv\Scripts\python.exe`。

- 用同一个解释器运行脚本与包管理：若确有安装需要，使用“解释器路径 `-m pip`”，不要相信另一个终端里裸 `pip` 的去向。
- 环境目录不放项目代码、不提交，也不要靠搬运 `.venv` 复现；记录 Python 版本和项目依赖约束后重建。
- **隔离不等于复现。** 两个环境若解析到不同版本的依赖，结果仍可能不同。实际实验应保存项目已有的依赖声明、锁文件及代码版本，而不是只写“装好了”。
- 本课 A1 固定仓库使用 `uv` 管理项目；进入作业时遵循它已有的环境约定，不在同一仓库叠加另一套依赖流程。上面仅说明虚拟环境机制，不取代官方配置，也不要求为这些标准库例子安装第三方包。

## 2. 文本、字节与 token 是三层单位

| 对象 | Python 表示 | 长度表示什么 |
| --- | --- | --- |
| Unicode 文本 | `str` | 码点数，不保证等于屏幕上的字形数 |
| UTF-8 编码结果 | `bytes` | 字节数；迭代得到 0–255 的整数 |
| tokenizer 输出 | 通常是整数序列 | 特定词表与切分规则下的 token 数 |

`encode` 是文本到字节，`decode` 是字节到文本。编码名必须在往返时一致；tokenization 是另外一层映射，不能把“UTF-8 编码”叫作“训练了一个 tokenizer”。

独立机制片段 A，仅用标准库：

```python
text = "A你\n"
raw = text.encode("utf-8")
assert len(text) == 3
assert len(raw) == 5
assert raw.decode("utf-8") == text
print(list(raw))
```

手算预期为 `[65, 228, 189, 160, 10]`：`A` 一字节，`你` 三字节，换行一字节。`text[:2]` 是两个完整码点；`raw[:2]` 却截在 `你` 的编码中间，默认 UTF-8 解码会失败。不能为了“跑通”就加 `errors="ignore"`：那会丢信息，改变输入。

两个实用边界：

1. `len("e\u0301")` 为 2；看起来像一个带重音字母，不意味着只有一个码点。这里不自动做 Unicode 规范化。
2. 文本模式可能把 `\r\n` 转为 `\n`。精确识别原文件时，对**原始字节**求哈希；统计文本时，另外声明编码和换行规则。二者不要混成“文件长度”。

## 3. Iterable 能提供遍历，iterator 会前进

列表是可迭代对象（iterable）；`iter(列表)` 返回带当前位置的迭代器（iterator）。`next(it)` 取一个元素并推进；耗尽后触发 `StopIteration`，`for` 会据此结束。生成器也是迭代器，通常不是自动回放的容器。

独立机制片段 B：

```python
values = [2, 3, 5]
it = iter(values)
print(sum(it), sum(it))
print(sum(values), sum(values))
```

手算预期依次是 `10 0` 和 `10 10`。第二个 `sum(it)` 没有读到坏数据，只是已无数据可读；对列表重新遍历则会取得新的迭代器。

文件也有当前位置。`for line in f` 到文件末尾后，再循环同一个文件对象通常不会从头开始。若确实需要第二遍，可重新打开文件；不能用“再套一个 `for`”代替重读。

**流式不等于零内存。** 逐行读取只保留当前行及统计状态；若一行本身很大，仍然占内存。`list(f)`、`f.read()` 则会把全部内容收集起来。先说明算法是否需要回看，再决定保存多少，而不是一律转成列表。

## 4. 文件、配置、日志各回答一个问题

- **文件：读写生命周期。** `with open(...)` 保证离开代码块时关闭文件，包括异常路径。文本显式指定 `encoding`；二进制模式不传编码。`"w"` 会覆盖已有文件，不能拿输入路径当输出路径。
- **配置：这次究竟采用什么规则。** 对这个小实验，一个普通字典足够；用 JSON 保存数值、布尔量和字符串，不用手拼格式，也不要把密码或访问令牌写进记录。
- **日志：运行经过了什么事件。** 默认日志级别是 `WARNING`，所以看不到 `INFO` 不等于代码没执行。独立脚本在入口配置级别，库函数不要反复改全局日志设置。
- **结果记录：什么数据支持这个结论。** “成功”没有单位；`lines=2, code_points=5, bytes=7` 才能和输入核对。输入摘要能识别字节是否相同，不能证明统计逻辑正确。

下面把它们连成一个微型实验。输入只有两行，在临时目录中生成和读取；退出后临时文件删除，结果 JSON 输出到标准输出。若要保留证据，由运行者把输出保存到自己的实验目录。它不接触官方作业数据。

独立机制片段 C，标准库即可，建议作为新脚本单独运行：

```python
import hashlib
import json
import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

config = {"encoding": "utf-8", "newline": ""}
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)
raw = "A你\nB\n".encode(config["encoding"])

with TemporaryDirectory() as directory:
    path = Path(directory) / "sample.txt"
    path.write_bytes(raw)
    lines = code_points = 0
    with path.open("r", **config) as stream:
        for line in stream:
            lines += 1
            code_points += len(line)
    record = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "config": config,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "lines": lines,
        "code_points_including_newlines": code_points,
    }
    logger.info("counted lines=%d code_points=%d", lines, code_points)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
```

解析预期：两行、五个码点、七个字节。`newline=""` 表示识别通用换行，但不把读到的行结束符改写；此输入本来就是 `\n`，因此不改变长度。解释器字段随运行环境变化。哈希针对程序写入的那串字节；这里没有宣称重新读取磁盘后校验，也没有把日志当成性能基准。

**最小证据包**可以很小：脚本或其版本、实际配置、输入标识/哈希、带单位的结果、Python/依赖版本。没有随机过程就不必硬塞随机种子；有随机过程时，种子也只是复现条件之一，不保证跨设备逐位相同。

## 5. 易错点与自测

| 症状 | 优先检查 |
| --- | --- |
| 包已经安装，运行却 `ModuleNotFoundError` | 安装和运行是否使用同一个解释器 |
| 文本看起来相同，长度或哈希不同 | 编码、换行和 Unicode 表示是否相同 |
| 第二遍计数是零 | iterator 或文件游标是否已经耗尽 |
| 日志没有 `INFO` | 日志级别与已有配置，而不是立刻重写逻辑 |
| 统计成功却无法比较两次结果 | 是否记录输入、配置、单位与版本 |

<details>
<summary>自测 1：把片段 A 的 text 换成 "你你"，两种长度是多少？</summary>

`len(text)=2`，UTF-8 字节长度为 6。两个码点都各占三字节；这还没有定义任何 token 数。

</details>

<details>
<summary>自测 2：为了避免第二次 sum(it) 为零，直接改成 list(it) 可以吗？</summary>

若 `it` 已耗尽，转换结果仍是空列表。若在第一次消费前保存为列表，可以多次遍历，但要支付存储全部元素的成本。对大文件，重新打开进行第二遍可能比一次性收集更合适；选择取决于是否能重读及计算目的。

</details>

<details>
<summary>自测 3：文件末尾的空行和文件结束有什么区别？</summary>

在文本文件中，一条空行通常读成 `"\n"`，长度不为零；`readline()` 在真正到达文件末尾才返回 `""`。不要用 `.strip()` 后是否为空判断文件结束，否则会把真实空行抹掉。

</details>

<details>
<summary>自测 4：两次结果具有相同 SHA-256，能推出统计正确吗？</summary>

不能。它支持“输入字节相同”这一判断，不能证明配置相同、程序正确或结果单位一致。需要像片段 C 一样保留明确配置，并用手算的小输入检验统计含义。

</details>

## 回到课程

回到 [L01：从文本进入 token 序列](#/c/stanford-cs336-2026/lec/lec01?v=notes)，先追问每个“长度”的单位，以及编码/解码能否往返；不要在这个桥接中提前实现作业 tokenizer。

## 来源与处理范围

本页是编者组织的先修讲解与原创小例子，不是官方课、课堂逐字译稿或新增作业。未使用录像、未截帧、未核音；三个标准库微例已执行并核对字节、迭代器和文件统计结果，未执行环境创建命令。

- Python 官方文档，固定 **CPython v3.14.0**：[venv](https://github.com/python/cpython/blob/v3.14.0/Doc/library/venv.rst)（环境定义、创建、激活与不可搬移性）；[输入输出](https://github.com/python/cpython/blob/v3.14.0/Doc/tutorial/inputoutput.rst)（文件模式、换行、逐行读取、JSON）；[迭代器与生成器](https://github.com/python/cpython/blob/v3.14.0/Doc/tutorial/classes.rst)（对应两节）；[Logging HOWTO](https://github.com/python/cpython/blob/v3.14.0/Doc/howto/logging.rst)（基础级别、独立脚本配置、格式）。文档采用 [PSF License v2](https://github.com/python/cpython/blob/v3.14.0/LICENSE)，文档代码另有 0BSD 双许可；本文为自主说明，不是文档全文翻译。该版本是补充依据，不是声称课程要求 Python 3.14。
- Stanford CS336 [L01 固定讲义](https://github.com/stanford-cs336/lectures/blob/de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e/lecture_01.py#L579-L673)：实际阅读文本/token、码点、字节与往返段落。讲义固定版晚于学期，不代表逐字对应录像；仓库开放翻译许可未确认。
- [A1 固定 README 的环境段落](https://github.com/stanford-cs336/assignment1-basics/blob/a158843b20107949f1a8d7df1b05cd33b9166712/README.md#setup)：只用于确认 `uv` 工作流。README 标题遗留 2025；学期依据同一固定版讲义封面 **Spring 2026 / 26.0.3**，不据 README 改判学期。仓库 MIT 仅覆盖第一方文档，不外推数据、依赖或课程录像。
- 逐源哈希、获取时间与实际阅读范围见 `sources/p2-bridge-foundations/manifest-fragment.json`；原始资料只作本地来源留存。
