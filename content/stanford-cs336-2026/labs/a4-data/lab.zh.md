---
title: A4 预训练数据流水线：完整实验说明
kind: 固定 2026 官方第一方要求的中文重述；非解答
source: CS336 Assignment 4 (data), Spring 2026, Version 26.0.1
source_commit: 0555bea66369872d912652debf10b115ca0688c8
source_read_scope: 全部 16 页提取文本；README、LICENSE、完整 CHANGELOG、AGENTS、全部 adapter 与测试源码、下载与训练相关源码；非 PDF 逐页视觉审校
status: P6 作者交接；13 个计分任务、27 个字母子问、总计 71 分；页面验收由主审记录
execution: 仅静态阅读；未执行官方代码、下载数据或模型、启动 Modal 或训练、访问私有卷或提交接口
license: Stanford 第一方软件及文档为 MIT；完整通知见页底；不覆盖网页、数据、论文、分类器权重
---

# A4 要交付什么

本作业把 Common Crawl 网页转成语言模型训练数据：观察原始记录、提取正文、识别语言、掩码个人信息、处理有害内容、规则与学习型质量过滤、精确与近似去重，最后比较**只改变数据**时固定模型的表现。它不是“写几个过滤器”就完成的任务：人工观察、流水线计时、token 统计、训练曲线和误差分析都属于正式交付。

本页重述题目与接口，不提供实现、阈值答案、训练好的分类器、采样观察结果或可提交报告。[指导页](#/c/stanford-cs336-2026/lab/a4-data?v=guide) 只讲概念、证据边界和检查问题。下文“运行／提交”均指**学生待完成的官方要求**，不是本站运行记录。

| 官方任务 ID | 中文任务 | 分值 |
|---|---|---:|
| `look_at_cc` | 观察 WARC 与 WET | 4 |
| `extract_text` | HTML 转文本 | 3 |
| `language_identification` | 语言识别 | 6 |
| `mask_pii` | 个人信息掩码 | 3 |
| `harmful_content` | NSFW 与有毒言论识别 | 6 |
| `gopher_quality_filters` | Gopher 质量规则 | 3 |
| `quality_classifier` | 自行训练质量分类器 | 15 |
| `exact_deduplication` | 精确行去重 | 3 |
| `minhash_deduplication` | MinHash 与 LSH 文档去重 | 8 |
| `filter_data` | 并行过滤与耗时 | 6 |
| `inspect_filtered_data` | 人工检查与迭代 | 4 |
| `tokenize_data` | 分词与二进制序列化 | 2 |
| `train_model` | 固定模型训练与验证 | 8 |

以上 **71 分**是本固定 handout 各 Problem 分数之和，不是另造百分制。题目没有为每个字母子问单独分配分值。

## 0．版本、政策和执行边界

### 0.1 固定版本与提交物

来源为 **Spring 2026、handout v26.0.1、16 页**；仓库 package 为 **26.0.0**。CHANGELOG 26.0.0（2026-05-06）把旧版 5,000 原始 WET 改为来自 **2,500 原始 WET 的 English-only 输入**，并把最终训练改为 8 B200、16,384 步、约 8.6B tokens；26.0.1（2026-05-07）增加本地数据目录自动创建。不要将 2025／2024 的历史配置混入本题。

官方仓库分工：`cs336_basics` 是经过优化的 staff A1 模型与训练实现；`cs336_data` 是学生实现数据处理的位置；`tests` 通过 `tests/adapters.py` 调用你的实现。可自行补充调试检查，但交付仍须满足原始测试合同，不能通过改弱测试解决问题。环境以 `uv` 管理，固定 package 要求 Python ≥3.12；没有在本站安装或验证其依赖。

Gradescope 交付：

- **`writeup.pdf`**：排版后的全部书面回答。
- **`code.zip`**：自己写的全部代码。

README 指向 `test_and_make_submission.sh`。固定脚本生成名为 `cs336-assignment4-submission.zip` 的 zip；手册的 `code.zip` 是提交项名称，不能据 README 中残留的 “tarball” 字样认为它生成 tar 文件。打包脚本会调用 pytest，但用了 `|| true`：**出现 zip 或 “Done running tests” 不等于测试通过**。它还排除 `.bin`、`.pt`、`.txt`、`.json` 等多类文件；学生须自行确认交付内容和助教复现所需的路径／资产说明，不把模型权重或私有数据误当默认已打包。

### 0.2 AI 帮助只限概念与 API

官方 AI 政策允许高层概念问答和底层函数签名／库 API 文档辅助；**禁止 AI 实现任何作业或排行榜部分，包含 coding agent 和 AI 自动补全**。代码、实验、报告由学生独立完成，关闭 AI 自动补全。固定仓库 `AGENTS.md` 更明确禁止代写 Python／伪代码、完成占位实现、代写 writeup、给计分题答案；不得修改该政策文件。本页是作业说明翻译，不是提交用答案。任何概念自测也不替代学生实际观察与实验。

### 0.3 三类路径不能混为公共下载链接

1. **课程环境**：`/shared-data` 是课程远端挂载路径，不是网站；`a4-shared-data` 是指定 Modal environment 下的卷，不向公众承诺可访问。
2. **非学生本地路线**：固定 `get_shared_assets_path()` 在本地返回当前工作目录下的 `local-shared-data` 的绝对路径，并创建目录；手册的 `/shared-data/...` 不能原样假定本地存在。
3. **个人训练输出**：远端 `/root/data` 挂载个人 `data-{SUNET_ID}` 卷；训练输入和输出在此，与只读共享卷不同。真实路径须由有授权的操作者核实。

**静态入口限制：** `modal_utils.py` 顶层有 `SUNET_ID = "TODO"` 检查，未配置即抛出异常。下载、训练和生成脚本都会导入它，因而 README 的本地命令也不能视作无需配置就能运行。本站不索要 SUNET、凭据或课程卷权限，也不为非学生提供伪造身份办法。

README 的 `--offline-only` 意为“只下载之后离线练习需要的文件”，**不是不联网**：脚本仍会获取 Paloma 验证 `.bin`、示例 WARC／WET、`lid.176.bin` 和两个 Dolma 分类器。完整路线还会处理 Wikipedia dump 与大规模 WET。非学生 README 所述移除 `environment_name` 或修改本地路径只是其分支说明，不保证解决全部 import、权限、卷内容和存储问题；这些源码本次均保持不变。

**本站执行范围：**只读静态源码和授权文档；不下载样例或 2,500 WET、不抓 Wikipedia 或外链网页、不下载 tokenizer／分类器／模型、不运行官方 pytest 或打包脚本、不启动 Modal／GPU、不访问私有卷、不提交作业。后文保留的官方命令仅为来源导航，不是建议读者直接启动的操作清单。

## 1．观察 Common Crawl：`look_at_cc`（4 分）

Common Crawl 提供公开抓取结果，而非已完成质量控制的训练集。

- **WARC**：原始记录，含网页 URL、ID、元信息、HTTP 请求相关信息及 HTML 等内容。
- **WAT**：从 WARC 提取的高层元数据 JSON，如标题与外链。
- **WET**：从 HTML 提取的纯文本，但记录头不是正文，也可能残留导航、页脚等内容。

本题观察 **CC-MAIN-2026-12** 的一个 WARC 与对应 WET，课程路径分别是 `/shared-data/CC/example.warc.gz`、`/shared-data/CC/example.warc.wet.gz`。手册写出的来源位于该 crawl 的 `segments/1741613651012.6/` 下，文件基名为 `CC-MAIN-20260310152245-20260310182245-00000`，后缀分别为 `.warc.gz` 和 `.warc.wet.gz`。固定下载脚本则读取该 crawl 的 `warc.paths.gz`／`wet.paths.gz` 各自第一条路径；**它没有把手册的示例 URL 硬编码进去，也没有在代码中校验两份第一条路径配对**。学生实际比较时应核实记录身份，本站未下载验证。

未经筛选的网页可能含令人不适的内容；官方允许跳过不愿阅读的文档。公共报告也不应再次公开真实 PII 或不必要的有害原文。

### （a）首个 WARC 网页

用手册提供的 `zcat` 配合 `less` 浏览压缩文件；`less` 可用方向键、Page Up／Down 浏览，以 `q` 退出。找出**第一个网页**的 URL，检查它是否仍可访问，并判断从原始 HTML 能否看出网页主题。不是把首个任意元数据记录当网页。

**交付：2–3 句回答。**

### （b）对应 WET 文本

查看对应 WET 的第一个例子，注意 `Content-Length` 等记录头不属于抽取正文。哪些片段看似本该被提取器剔除？以这种文本训练会有什么问题？反过来，模型仍可能从中获取什么有用信息？

**交付：3–4 句回答。**

### （c）质量的使用场景

提出一个该例子可能有用的应用领域，以及一个可能不适合的领域。

**交付：1–2 句回答。**

### （d）另外 25 条 WET 记录

再浏览 **25 条** WET 记录；对每条简要记录可识别的语言、域名、网页类型及其他观察，并报告到第几个例子才出现你认定的“高质量”网页。

**交付：25 份简短文档注释，以及首次遇到高质量例子所需的观察数。**不能用 25 个句子或同一文档的 25 行代替，也不能把首页例子直接混作“另外 25 条”。

## 2．HTML 转文本：`extract_text`（3 分）

可见文字不等于主内容：导航、登录链接、菜单和页脚可能与问答正文一起被抽出。作业指定 **Resiliparse**；另建议用 FastWARC 的 `ArchiveIterator`、`WarcRecordType` 遍历 WARC 记录。

### （a）字节输入与编码

实现函数：输入包含原始 HTML 的 **bytes**，输出抽取后的字符串。先把 bytes 解码成 Unicode；不能只支持 UTF-8，UTF-8 解码失败时要能检测编码。指定抽取 API 是 `resiliparse.extract.html2text` 模块的 `extract_plain_text`；编码检测可参考 `resiliparse.parse.encoding` 模块的 `detect_encoding()`。

**交付：函数及 adapter `run_extract_text_from_html_bytes`；满足 `test_extract_text_from_html_bytes`。** 固定 adapter 注解允许 `str | None`，但本题描述与提供的正常 HTML 测试要求抽取字符串；该注解不把失败输入静默丢弃定义成完整任务。

### （b）与 WET 比较

在**一个 WARC 文件**上运行自己的抽取函数，比较对应 WET 的文本，指出异同与哪种抽取更好。

**交付：2–3 句比较。**本子问没有指定“20 例”，不要凭空给官方增减样本量。

## 3．语言识别：`language_identification`（6 分）

有限预算下的训练常选择有限语言集合；本题使用 fastText 预训练语言识别模型 `lid.176.bin`，课程资产为 `/shared-data/classifiers/lid.176.bin`。分类器同时给语言标识和置信度，分数不是经过当前网页分布校准的真值保证。

### （a）主语言与分数

输入 Unicode 字符串，返回**主语言预测与 0–1 分数**。

**交付：函数及 `run_identify_language`；满足 `test_identify_language` 匹配的两个测试。** 测试期望英文 `en`、中文 `zh`，必要的标签映射放在 adapter 接口边界；固定测试还要求分数为正的 `float`。测试条件比题目总体的 0–1 合同更窄，不能只满足类型就忽略分数含义。

### （b）下游风险

语言识别出错可能在后续语言模型中造成什么问题？若部署面向用户的高风险产品，你如何缓解这些问题？

**交付：2–5 句回答。**

### （c）20 例人工比较

在自己从 WARC 抽出的文本上运行识别器，随机选 **20 个例子**，人工识别语言并和预测比较；报告错误、英文文档占比，以及据观察认为适合过滤的置信度阈值。

**交付：2–5 句回答。**这里的人工观察阈值讨论不改变后面 staff English-WET 输入已经使用的 **P(English) ≥0.7** 预过滤规则。

## 4．个人信息：`mask_pii`（3 分）

作业要求**掩码**而不是自动整篇删除。三类函数都输入字符串，返回“新字符串、实际替换次数”二元组。

### （a）Email

把所有检测到的 email 地址替换为 **`|||EMAIL_ADDRESS|||`**。官方允许查阅可靠的 email 正则文档；本页不提供正则实现。

**交付：函数及 `run_mask_emails`；满足所有 `test_mask_emails` 测试。** 原文已存在的占位符不是此次新检测到的地址，不应计入替换次数。

### （b）美国电话号码

将电话号码替换为 **`|||PHONE_NUMBER|||`**。可靠检测所有全球格式很难；题目至少要求覆盖常见美国格式，对轻微语法差异有鲁棒性。

**交付：函数及 `run_mask_phone_numbers`；满足 `test_mask_phones`。** 测试覆盖连续数字、连字符与括号／空格形式，不代表已经覆盖全部真实电话号码。

### （c）IPv4

本题只要求 IPv4：四个以点分隔的数，每个在 0–255 范围。替换为 **`|||IP_ADDRESS|||`**。

**交付：函数及 `run_mask_ips`；满足 `test_mask_ips`。** 不把句尾标点当地址的一部分；不把本题扩大成“已全面消除个人信息”。

### （d）下游风险

这些过滤器若被朴素地应用在训练集上，可能引发哪些下游问题，如何缓解？

**交付：2–5 句回答。**

### （e）20 个发生替换的例子

在自己从 WARC 抽出的文本上运行掩码函数，检查 **20 个随机、且发生过替换的例子**，举出误报与漏报。

**交付：2–5 句回答。**采样总体是“发生过替换的文档”，不是所有文档；它也无法独自覆盖“完全没有命中但实际仍有 PII”的漏报区域。公开举例应匿名化，保留错误机制而非真实联系信息。

## 5．有害内容：`harmful_content`（6 分）

题目区分 **NSFW**（色情、粗俗或其他可能令人不适的内容）与 **toxic speech**（可能使人退出讨论的粗鲁、不尊重或不合理语言）。边界并不绝对；本题采用 Dolma 提供、基于 **Jigsaw Wikipedia toxic comments** 的两种 fastText 分类器。

课程资产分别是 classifiers 目录下的 <code>dolma_fasttext_nsfw_<wbr>jigsaw_model.bin</code> 和 <code>dolma_fasttext_hatespeech_<wbr>jigsaw_model.bin</code>。文件名含 hatespeech，不意味着所有 hate、toxicity、NSFW 概念可互换。仓库下载源和模型文件是第三方资产，不因作业 MIT 获得统一许可。

### （a）NSFW 分类

输入 Unicode 网页文本，返回是否 NSFW 的标签与置信度。

**交付：函数及 `run_classify_nsfw`；满足 `test_classify_nsfw`。** 固定 adapter 测试标签为 `nsfw`／`non-nsfw`，分数为正的 `float`。

### （b）有毒言论分类

输入文本，返回 toxic 与否的标签和置信度。

**交付：函数及 `run_classify_toxic_speech`；满足 `test_classify_toxic_speech`。** 固定标签为 `toxic`／`non-toxic`。

这两项测试直接使用 Jigsaw 中的 sanity-check 例子；**不是独立泛化评测，更不证明分类器准确或训练数据无毒**。本站不复刻测试中的不必要有害原文。

### （c）下游风险

这些过滤器改变训练集后可能造成什么问题，如何缓解？

**交付：2–5 句回答。**

### （d）20 例人工比较

在自己从 WARC 抽出的文本上运行过滤器；随机看 **20 个例子**，对比模型预测与自己的判断，报告分类错误、有害文档比例，以及适合过滤的一个或多个阈值。

**交付：2–5 句回答。**NSFW 和 toxicity 的阈值及错误不应不加区分地合成一个“安全率”。

## 6．Gopher 规则：`gopher_quality_filters`（3 分）

语言正确且没有明显有害内容，仍可能是付费墙、坏链接占位页、登录／注册／联系表单，或抽取后只剩少量文字的图片／视频页。官方要求实现 Gopher 全套规则的**至少以下子集**，不是声称完整复现 Gopher Appendix A。

拒绝满足任一条件的文档：

- 少于 **50** 或多于 **100,000** 个词。
- 平均词长不在 **3–10 个字符**范围。
- **超过 30%** 的行以省略号 `...` 结尾。
- 含至少一个字母字符的词**少于 80%**。

严格保留“少于／超过”的边界，不把 50、100,000、3、10、30%、80% 的端点任意翻转。

### （a）规则函数

输入一个字符串，返回是否通过质量规则的 **bool**。可以参考 `nltk.word_tokenize`，但官方不强制使用 NLTK。

**交付：函数及 `run_gopher_quality_filter`；满足 `test_gopher` 匹配的测试。** 词、字符、行是不同统计单位，题目没有指定 tokenizer 的地方应在自己的记录中说明约定，而不是凭库名推断语义。

### （b）20 例人工比较

对自己从 WARC 抽出的文本运行规则过滤器，随机查看 **20 个例子**，比较过滤结果与自己的质量判断，评论不一致的情况。

**交付：2–5 句回答。**

## 7．学习型质量：`quality_classifier`（15 分）

手册提出以可信来源链接为弱质量信号：WebText 采用达到 karma 条件的 Reddit 外链；本题提供英文 Wikipedia 外链作为另一条参考来源。**外链不等于 Wikipedia 正文本身，也不自动等于可靠／安全／有授权的文本。**

课程文件 `/shared-data/wiki/enwiki-20260501-extracted_urls.txt.gz` 收录 **2026 年 5 月英文 Wikipedia** 的外链 URL。学生需要**自行抽样这些 URL、获取相应网页、抽取文本**，作为高质量正例；可使用此前的语言与质量等原语进一步清理。手册给出的抓取方式是 `wget` 的 URL 列表输入 `-i`、5 秒超时 `--timeout=5`、WARC 输出 `--warc-file` 及丢弃普通输出 `-O /dev/null`。这是官方采集说明，不是本站进行了抓取；网络与网站使用条款需由实际操作者遵守。

相对地，以随机 Common Crawl 网页作为负例，**由学习者训练 fastText 质量分类器**，将参考数据的信号推广到更大的 CC 集合。质量阈值会在 precision 与 recall 之间取舍；负例中可能有好文档，正例中也可能有不良内容。不能把预训练语言识别器、现成质量模型或 Gopher bool 返回值当成本题训练过的质量分类器。

### （a）训练自己的分类器

训练一个给定文本后返回数值质量分数的分类器。

**交付：供下一子问使用的、由自己训练的质量分类器。**手册不固定训练例数、超参数或最优阈值，本页也不替学生选择。

### （b）标签与置信度接口

输入字符串，输出“高质量或非高质量标签、置信度”二元组。

**交付：函数及 `run_classify_quality`；通过 `test_classify_quality` 对两个给定例子的 sanity check。**固定测试用 `wiki` 表示高质量参考例、`cc` 表示低质量 CC 例，并要求正的 `float` 分数。这只是 adapter 标签合同，不是“所有 Wikipedia 外链都优质、所有 CC 都低质”的事实判断。本题没有另设 20 例书面子问，不能用下文的检查替代分类器训练。

## 8．精确行去重：`exact_deduplication`（3 分）

网页常共享菜单、标题和页脚。题目要求先统计整个输入语料中每一行的出现次数，使用**行的哈希**作为计数键以减少存储；再重写每份文档，**仅保留全语料出现一次的行**。

**注意：不是重复行保留第一次，而是出现多次的行全部移除。** 同一文档内部的重复也属于整个输入集合中的重复，不只考虑跨文档。

**交付合同：**函数接收输入文件路径列表和输出目录；对每个输入文件，在输出目录以**同名文件**写出去重结果。例如输入 `a/1.txt`、`a/2.txt`，输出目录 `b/`，对应输出 `b/1.txt`、`b/2.txt`。实现 `run_exact_line_deduplication`，满足 `test_exact_line_deduplication`。

固定测试要求五份输出对应五份行去重后的文档。它与下一题文档级去重的“被删除文档不写文件”不同；不能把行级与文档级输出合同混用。

## 9．MinHash＋LSH：`minhash_deduplication`（8 分）

不同作者／年份的许可证等模板文本可能并非逐字相同；本题以**词 n-gram 集合的 Jaccard 相似度**衡量近似重复。

$$
J(S,T)=\frac{|S\cap T|}{|S\cup T|}.
$$

手册的方法说明：用 $k$ 个不同哈希函数生成每个集合的 MinHash 签名；两份签名相同位置的比例近似其 Jaccard。再将签名分为 $b$ 个 band，每个有 $r$ 个位置，满足 $k=br$。两文档在**同一个 band**的整段值相同，就成为候选重复；不需要所有 band 都匹配。固定签名长度时，更多 band 通常提高候选召回、降低候选精确率。

**候选不是最终重复判定。**题目明确要求对候选计算**真实的词 n-gram Jaccard**，按给定阈值判断；不能只比较签名相等率或“共享一个桶”便删文档。之后跨桶聚类：A–B 与 B–C 两条已验证重复关系可把 A、B、C 连在同一簇；每簇随机保留一个文档，不要求 A–C 也超过阈值。

在计算签名及／或比较 Jaccard 前，按题意归一化文本以提高召回：**转小写、去标点、规范空白、去重音、NFD Unicode 规范化**。归一化是比对表示，不能不说明就把最终保留的原文改写成该表示。

**交付合同：**实现模糊文档去重函数与 `run_minhash_deduplication`。实际 adapter 参数为：

- `input_files`：输入文件路径列表。
- `num_hashes`：MinHash 哈希数。
- `num_bands`：LSH band 数，可假设哈希数被 band 数整除。
- `ngrams`：**以词为单位**的 n-gram 长度。
- `jaccard_threshold`：真实 Jaccard 阈值；手册参数列举未列全，但实际 adapter 明确要求它。
- `output_directory`：输出目录。

保留非重复文档及每个重复簇随机选中的代表；写到输出目录时保持原文件名。未超过阈值的候选仍应保留，而被删除的文档不写出。满足 `test_minhash_deduplication`：固定测试包含精确重复与模糊许可证两类，分别用 100 hashes／10 bands 和 500 hashes／50 bands，均为 5-word n-grams、Jaccard 0.8。**这些是测试配置，不是官方声称的最佳真实语料超参数。**

## 10．并行过滤：`filter_data`（6 分）

此阶段从**已经按英文过滤的 WET** 开始，不再从前面的单 WARC 观察样例扩充而来，也不是重新抽取 2,500 份 HTML。

### 10.1 真实输入来源与分组

固定 `EnglishWetFiles` 对 **CC-MAIN-2026-17** 的 WET 路径无放回抽样：`n_files=2500`、`shuffle_seed=336`、`group_size=4`。每组四份原始 WET 合并处理，用 `lid.176.bin` 的 **P(English) ≥0.7** 保留英文 conversion 正文。因此默认会形成 **625 个分组产物**；2,500 指原始输入文件数，不是 English-WET 产物数，也不是文档数。

`is_english` 在公开源码中仍需学生自行实现；存在断言，不是可运行的预填答案。本地与远端的实际路径也不同：

- Furu 存储根在共享资产根下的 `furu`；每个分组产物名为 `data.warc.wet.gz`，具体缓存子路径由 Furu 管理。函数返回的是这些实际产物的 `Path` 列表。
- **只有远端分支**会创建 `english-wet-data`，放入指向产物的 `00000-...` 等软链，以及 `.source` 链接。不能假设本地分支也会自动创建同样目录。
- 远端目录创建使用 `exist_ok=False`，且共享卷挂载在当前配置中是只读；权限、目录已存在与远端写入条件需由环境所有者核实，不能凭 README 保证创建成功。
- README 建议非学生可减小 `n_files`，但实际代码断言其能被 `group_size=4` **整除**。缩规模属于教学改编，不能冒充完成原 2,500 原始 WET 任务；也不会自动解除下载、权限、存储或 AI 政策限制。

远端函数的 `max_containers=128` 是配置上界，不是建议直接开 128 个实例，也不是本站资源使用记录。

### 10.2 固定验证目标

目标是让固定 Transformer 在 **Paloma 的 C4 100 domains 子集**上具有尽可能低的验证 perplexity。它包含 C4 中最常见的 100 个域的数据。课程已提供 GPT-2 tokenized 的 <code>tokenized_paloma_c4_100_<wbr>domains_validation.bin</code>；按 `np.uint16` 读取，必要时借助 GPT-2 tokenizer 查看文本。

官方**允许观察该验证集来构造过滤器或分类器**，但**绝不允许把其中的数据直接复制进训练集，语言模型不得见到验证集数据**。这项作业许可不等于所有 benchmark 都允许同样做法；反复针对验证集选择数据，也不等于获得独立测试证据。禁止为成绩修改模型架构、训练过程或 staff 脚本。

### （a）并行流水线与逐步统计

写一个或一组脚本，并行过滤 `/shared-data/english-wet-data` 的输入。可选用前面实现的原语，也可探索其他数据方法，例如 n-gram LM perplexity 过滤；目标仍是 C4 100 验证表现，不是强制把所有原语按固定顺序串一次。

脚本要报告**每个过滤器保留的例子数**，让各步骤贡献可解释。官方建议本地大文本块使用 `concurrent.futures`／`multiprocessing`，Modal 跨 worker 可参考 `.map(...)`；WET 遍历可参考 FastWARC，域名解析可参考 `tldextract.TLDExtract`。这些是 API 导航，不是实现方案或现成脚本。

**交付：并行过滤脚本（或脚本序列），以及“所有被丢弃例子中，各步骤分别移除了多大比例”的书面分解。**单独报告“该步相对入站的拒绝率”不等于这一分母；有修改但未丢弃的文档也应与删除区分。

### （b）真实耗时与外推

处理题设 English-WET 集合（来源于 **2,500 原始 WET**）实际需要多久？估计处理完整 Common Crawl dump 需要多久？

**交付：流水线 runtime。**区分真实测量与基于吞吐的外推，说明输入规模、并行度、计时范围和假设；不能把 staff 训练耗时当过滤耗时，也不能拿微型文本算例的计时回答原规模任务。

## 11．人工检查：`inspect_filtered_data`（4 分）

生成了数据之后，还需观察它是否适合目标语言建模任务。

### （a）随机 5 条保留文档

从最终过滤数据中随机选 **5 个例子**，讨论质量及是否适合语言建模，尤其是 C4 100 目标。

**交付：5 条例子（允许只展示有关片段），每条 1–2 句描述与是否值得训练的判断。**

### （b）随机 5 条删除／修改文档

从原始 WET 中随机选 **5 个被删除或被修改的文档**；指出由哪一步删除／修改，判断是否合理。这里不是随机选五个 WET 压缩文件代替五篇例子。

**交付：5 条被舍弃例子或相关修改例子（可用片段），每条 1–2 句说明及合理性判断。**保留完整记录身份用于内部复查；对外输出避免泄露真实个人信息。

### （c）迭代说明

若前面的分析促使你在训练前调整流水线，可以调整；报告实验过的变化与数据迭代。

**交付：实际修改／迭代的说明。**没有迭代也应如实说明，不虚构改善结果。

## 12．分词与序列化：`tokenize_data`（2 分）

用 Transformers 的 **GPT-2 tokenizer** 把过滤后的文档编码为 token ID 序列，并在**每篇文档后**加入 GPT-2 的 EOS token **`<|endoftext|>`**。手册示例逐行处理，是在其输入表示中按行组织文档；不能未经确认就把任意多行文档的每一行都当一篇，或在换行处漏掉文档边界。

序列化必须与 staff reader 相容：整数 ID 的 NumPy **`np.uint16`** 数组，通过 **`ids_array.tofile(output_path)`** 写出裸二进制 `.bin`。不是 `.npy` 容器、文本数字、pickle 或 `int64` 字节；文件扩展名相同不代表格式相同。对应验证集也按 `uint16` 读取。

**交付：自己的分词／序列化脚本，以及产出数据集的实际 token 总数。**计数应包括每篇文档添加的 EOS。数据集存储的 token 数与训练抽样看过的 token 数是两个量：staff 从数组随机抽上下文片段，可重复看到数据，不能把固定 8.6B 训练预算当作自己的数据集规模。

## 13．固定训练：`train_model`（8 分）

具体数值以固定 `train_config.py` 与 `scripts/train.py` 为准。手册称 “GPT-2 small-shaped”，但它明确是**约 430M 参数**，不能误译成标准 GPT-2 small 的约 124M 模型。

| 项目 | 固定配置 |
|---|---|
| 词表／上下文 | 50,257／512 |
| 宽度／前馈 | `d_model=1024`／`d_ff=3072` |
| 层数／头数 | 24／16 |
| 位置编码 | RoPE，theta 10,000 |
| 数值类型 | BF16 autocast |
| GPU／并行 | **8×B200**，DDP |
| 每设备 batch／梯度累积 | 128／1 |
| 优化步数 | **16,384** |
| 学习率 | 6e-4；warmup 比例 0.03；余弦降至最大值的 0.1 倍 |
| AdamW | betas 0.9／0.98；epsilon 1e-9；weight decay 0.1（源码对一维参数不衰减） |
| 梯度裁剪／seed | 1.0／0（DDP 各 rank 加自身 rank） |
| 验证 | batch 128；每 2,000 步评估；每次 1,000 个采样 batch；结束再评估 |
| 其他默认 | compile 开启；中间 checkpoint 保存默认关闭；最终保存权重与配置 |

训练预算按下式计数，拆开书写以区分每步与全程：

$$
T_{\text{step}}=8\times128\times512
=524{,}288,
$$

$$
T_{\text{run}}=16{,}384\times T_{\text{step}}
=2^{33}\approx8.6\text{B}.
$$

staff 报告此设置约 **2:00 小时**完成，是历史运行时间，不是本站实测、免费额度、SLA 或对本机的预估。远端脚本申请 **524,288 MB** 临时磁盘；这是请求／容量检查值，不是输入数据实际大小或推荐立即申请的资源。

官方训练入口为 `scripts/train.py` 的 Modal entrypoint，参数 `--train-bin` 指向 GPT-2-tokenized 训练 `.bin`；handout 展示的命令是 `uv run modal run scripts/train.py --train-bin /root/data/your_data.bin`。固定脚本把训练／验证文件复制到 `/tmp/data` 后以 `torchrun` 启动八卡，输出根为 `/root/data/output/your_data`。执行前必须由有权限且独立完成实现的学生确认个人路径与资源；本站没有执行。

README 说 Modal entrypoint 包含完整配置，但实际模型／训练默认值定义在 `cs336_basics/train_config.py`，entrypoint 负责设备数与路径；旧 `configs/*.yaml` 没有被当前 `train.py` 读取，不能认为编辑 YAML 会自动改变运行。更重要的是，本题本来就**不允许为了提升分数改变模型、训练 procedure 或 staff 训练脚本**；单 GPU 调试入口也不等价于正式八卡预算。

官方还提供 `scripts/generate_with_gpt2_tok.py`，可用 `--model-path` 指向保存模型；该入口同样会加载 tokenizer、模型并申请 GPU，不能当离线无成本检查。生成样例不是本任务要求的 loss／learning curve 的替代物。

**交付：在自己的 tokenized 数据上训练固定模型，定期测 C4 100 验证 loss，报告实际记录的最佳 validation loss、相应学习曲线及做法说明。**不虚构最佳值，不只展示训练 loss，不把 perplexity 与交叉熵 loss 数值混用；曲线需来自真实记录。固定代码在验证时从验证数组采样 batch，所谓 best 是记录到的评估值，不是对每个验证 token 逐个遍历的全量精确估计。

最佳日志观测不自动对应保存好的最佳 checkpoint：默认 `save_checkpoints=False`，周期评估只在启用该项时保存中间权重；最终 `model.pt` 则保存最终状态，不能未经证据称为最佳观测时的模型。

## 14．交付数量与完整性清单

- 观察：首次 WARC／WET 的 2–3、3–4、1–2 句；**另外 25 条 WET 注释**与首次优质例位置。
- 抽取：指定 API 的函数、adapter、单 WARC 与对应 WET 的 **2–3 句比较**。
- 语言：函数；风险 **2–5 句**；随机 **20 例**、英文比例／错误／阈值的 **2–5 句**。
- PII：三个掩码函数与计数；风险 **2–5 句**；**20 个发生替换的随机例子**、误报／漏报的 **2–5 句**。
- 有害内容：两个分类函数；风险 **2–5 句**；随机 **20 例**、错误／比例／阈值的 **2–5 句**。
- Gopher：规则 bool 函数；随机 **20 例**不一致分析 **2–5 句**。
- 质量分类：**学生自己训练的 fastText 分类器**与标签／分数接口。
- 去重：精确行函数；MinHash＋LSH 候选、真实 Jaccard、跨桶聚类及随机留一的文档函数。
- 流水线：并行脚本；每步保留数量、丢弃归因比例；全输入实际 runtime 与整 crawl 外推。
- 人工复查：随机 **5 条保留＋5 条删除／修改**，每条 **1–2 句**；真实迭代记录。
- 分词：GPT-2、每文档 EOS、`uint16` 裸 `.bin`；实际数据 token 数。
- 固定训练：真实 best C4 100 validation loss、学习曲线、做法；不改变训练配方。
- 最终：独立完成的 `writeup.pdf` 与代码 zip；声明数据、资源及未执行范围。

本页没有填任何实际文档观察、过滤比例、耗时、token 数、最优阈值或验证结果；这些必须来自学生自己的合规工作。**全文说明已制作，不等于官方作业已完成或运行通过。**

## 来源、延伸阅读与权利

- [固定 handout v26.0.1](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/cs336_assignment4_data.pdf)：本页任务唯一依据，完整读取 16 页提取文本；未做 PDF 逐页视觉校对。
- [README](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/README.md)、[CHANGELOG](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/CHANGELOG.md)、[adapters](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/tests/adapters.py)、[测试目录](https://github.com/stanford-cs336/assignment4-data/tree/0555bea66369872d912652debf10b115ca0688c8/tests)：版本、接口与测试边界。
- [下载脚本](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/scripts/download_data.py)、[WET 源码](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/cs336_data/wet_files.py)、[Modal 配置](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/cs336_data/modal_utils.py)、[训练脚本](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/scripts/train.py)、[训练配置](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/cs336_basics/train_config.py)：本页静态差异说明依据。
- [官方 AI 政策](https://docs.google.com/document/d/1SZAlExB1qAc9izHt54gwunNpjKE6wXb8Y7yA_e-baK8/edit) 与 [固定 AGENTS](https://github.com/stanford-cs336/assignment4-data/blob/0555bea66369872d912652debf10b115ca0688c8/AGENTS.md)。
- 手册参考文献包括 Dolma（Soldaini 等，2024）、Gopher（Rae 等，2021）、PageRank（Page 等，1998）、GPT-2（Radford 等，2019）、LLaMA（Touvron 等，2023）、Mining of Massive Datasets（Leskovec、Rajaraman、Ullman，2014）、**RefinedWeb**（Penedo 等，2023）、Paloma（Magnusson 等，2023）及 C4／T5（Raffel 等，2020）。本页实际核读的是手册引用与任务，不声称为这些论文逐篇全文译文。
- 编者关联：[L13](#/c/stanford-cs336-2026/lec/lec13)、[L14](#/c/stanford-cs336-2026/lec/lec14)、[ext13 数据配方与污染审计](#/c/stanford-cs336-2026/lec/ext13)。[FineWeb 与 DataComp-LM 中文材料](#/c/stanford-cs336-2026/lec/lec14?v=materials) 唯一正文在 L14；它们是编者扩展，**不是 A4 明列的全文必读**，FineWeb 不等于手册引用的 RefinedWeb。
- 轻量证据：`sources/p6-a4/task-coverage.json` 逐题映射全部字母子问与交付；`manifest-fragment.json` 记录 URL、固定版本、读取范围、SHA256 和许可；`review.txt` 记录静态发现与未执行边界。

### 原文定位表

| 本页章节 | 手册节／物理页 |
|---|---|
| 概览、交付 | §1，p.1 |
| 观察 WARC／WET | §2.1，pp.2–3 |
| HTML 提取 | §2.2，pp.3–4 |
| 语言识别 | §2.3，pp.4–5 |
| PII 掩码 | §2.4，pp.5–6 |
| 有害内容 | §2.5，pp.6–7 |
| Gopher 规则 | §2.6，pp.7–8 |
| 自训质量分类器 | §2.7，pp.8–9 |
| 精确行去重 | §3.1，pp.9–10 |
| MinHash＋LSH | §3.2，pp.10–12 |
| 输入、验证目标、流水线 | §4，pp.12–14 |
| 5＋5 检查与迭代 | §4，p.14 |
| 分词与序列化 | §4，pp.14–15 |
| 固定训练与结果 | §4，pp.15–16 |
| 参考文献 | p.16 |

以下保留第一方软件与相应文档的完整 MIT 通知。中文重述与结构调整由本站编者完成，非 Stanford 官方中文译本。MIT 不延伸到 Common Crawl 网页、Wikipedia／Paloma 数据、第三方模型、论文、图片或外部服务。

### MIT 完整版权与许可通知

> Copyright 2026 Stanford University
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
