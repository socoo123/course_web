# 经典大学课程中文学习站 · 执行计划

更新：2026-11-06。阶段：可行性验证、MIT 6.S081 2020 Lecture 1 样本、前端接入检查。

## 1. 结论

**可行，官方资料与 YouTube 字幕的获取链路已跑通。** 以中文正文解释原理和课堂例子，配合总结、官方讲义中文稿、实验要求及可追溯引用，可以让学习以阅读为主。

质量目标是“读完能理解原理、推导例子并开始实验”，不能用一页摘要代替一堂课。板书、演示和字幕缺口仍需核对；字幕获取成功不代表已完整复现视频。

后续多 agent 在样本深度与目录协议确认后执行；本轮没有启动批量抓取 agent。用户已确认另一会话负责前端。

## 2. 当前本地基础

### 前端

另一会话已完成 `src/pages/{Home,Course,Lecture,Lab}.tsx` 及阅读器组件，支持课程目录、课表、实验、Markdown、Mermaid、公式、深浅主题、进度保存与中英对照。

本轮并行编辑时写入了临时样本入口，导致这些页面未被引用，并出现两处 TS2774。已撤掉临时独立入口及 `site.css`，`src/main.tsx` 仅连接现有页面组件的 `/c/:courseId`、`/lec/:lecId`、`/lab/:labId` 路由。后续前端设计与功能扩展由前端会话负责。

内容规范以根目录 `AGENTS.md` 和 `src/lib/types.ts` 为准。**内容 worker 只改 content，不碰 src。**

### 旧 6.S081 内容

早期的演示目录 `content/mit-6.s081/`（2020 视频 + 2025 实验 + 2026 课表的混合路线）已于 2026-11-06 删除，课程统一使用 `mit-6.s081-2020`。

本轮新增独立 courseId：`mit-6.s081-2020`，避免混用编号与实验。24 讲对应官方原始编号；2020 全课 11 个实验，本轮仅导入 util 元数据与导读。

### 6.824 可复用材料

`/Users/zy/ai_learn/mit6.824/` 中：

- `docs/` 有 Introduction、RPC/Threads、GFS 大纲和 MapReduce 指南。
- `lecture5 raft1/`、`lecture7 raft2/`、`lecture9 zookeeper/`、`lecture10 go/` 有 draft/notes 内容包。
- 已查看 Raft 2 的目录与 draft：含逐段正文、问答、编者注、截图和来源，可作为深度参照。
- 后续先逐包核实年份、视频 ID、图片相对路径与覆盖情况，再导入已有内容，避免重复生成。

### Skill 已迁入并优化

原版：`/Users/zy/.codex/skills/technical-video-notes/`。

OpenCode：`/Users/zy/.config/opencode/skills/technical-video-notes/`。

原 skill 也存在于兼容目录 `~/.agents/skills`；本轮迁入 OpenCode 原生目录并扩展课程网页模式，保留单视频双稿模式。新增来源清单、版本绑定、课堂/讲义范围区别、项目内容协议优先与 agent 写入边界。本会话已收到 skill 更新发现通知。

依据：[OpenCode V2 skills 文档](https://opencode.ai/v2/docs/skills)。

## 3. 试抓实际结果

| 项目 | 结果 |
|---|---|
| 官方学期 | Fall 2020 |
| 课表 | 24 个正式讲次，含 Q&A；LEC 2 没有挂课堂视频链接 |
| 官方资料 | 16/16 成功：课表、讲义、示例索引、10 个 C 文件、实验、工具页、教材 |
| 视频 | 官方课表链接 `L6YqHxYHa7A`；标题、频道、上传日期已核实 |
| 时长 | 4,797 秒，即 79:57 |
| 字幕 | 无人工字幕；en-orig 自动字幕 2,119 条，保存 json3/JSON/VTT/英文文本 |
| 时间异常 | 起点 1.920 秒，末尾 4,799.199 秒；超时 2.199 秒，网页阅读窗口按 79:57 截止 |
| 视频实际范围 | 到重定向结束；管道和目录来自讲义/教材补充 |
| 中文内容 | 学习正文、总结、自测、官方讲义中文整理稿、util 导读、引用、1 张 SVG |
| 尚未完成 | 全片视频译稿、画面核对、实验运行、其他讲次正文 |

官网按页面 CC 标识署名翻译；视频元数据无明确许可字段，因此交付自主学习讲解，未发布全文视频字幕译文。官网许可不自动延伸至外链视频、教材和论文。

示例目录虽在 2020 路径下，当前显示 2025 修改时间。来源快照保留 Last-Modified 与哈希；若逐行匹配录课源码，需要另查历史版本。

## 4. 阅读结构与当前前端映射

用户期望每讲：**课程正文 → 总结 → 官方中文资料 → 实验 → 引用**。

当前前端已经可以承载这些内容，采用下列映射，不要求先改 UI：

| 阅读内容 | 当前文件与入口 |
|---|---|
| 正文、总结、自测、引用 | `lectures/lec01/notes.zh.md`，课程笔记标签；引用节放文末，页面自动收进页底「引用与来源」 |
| 视频逐段中文整理 | `lectures/lec01/draft.zh.md`，中文译稿标签；未制作时不建文件 |
| 课堂之外的阅读材料（指定教材章节、论文）的译文 | `lectures/lec01/materials.zh.md`，课程资料标签；只是课堂提纲的官方讲义不再单独翻译，课堂截图只放译稿（规则见 AGENTS.md「三份讲座材料不重复」） |
| 各讲共用资料（教材、工具链、实验仓库） | `resources.zh.md`，侧栏「公共资料」 |
| 实验与练习 | 页头对应 Lab 链接 → `labs/util/guide.zh.md`，指导标签 |
| 英文视频原始字幕 | `sources/video/`，不使用 `.md`，本轮不发布到阅读标签 |
| 覆盖与缺口 | `lectures/lec01/status.json`，并在笔记正文显示重要状态 |

未来若希望五个独立标签，由前端会话统一扩展类型和阅读器；内容 worker 不自行注册路由。`draft.zh.md` 当前是讲义译文，不能与视频自动字幕配成中英对照。真正的双语视频稿必须按项目规范对齐时间标题。

```text
content/
  catalog.json
  mit-6.s081-2020/
    course.json
    lecture-index.json          # 抓取的官方 24 讲与原始链接
    sources/
      manifest.json            # 原始资料 URL/时间/状态/sha256
      video-metadata.json
      video/                   # 本轮 Lecture 1 字幕；后续放各讲独占目录
      examples/
      book-riscv-rev1.pdf
    lectures/lec01/
      notes.zh.md
      draft.zh.md
      status.json
      assets/redirection.svg
    labs/util/guide.zh.md
```

后续每讲独占 `lectures/lecNN/sources/`；教材、论文等共享资料由一个负责人维护。原始字幕不用 `.md`，避免被站点自动打包为阅读材料。

## 5. 分阶段执行

### P0 · 本轮验证

获取来源、完成中文样本、迁入 skill、对接现有前端并运行构建。验收：资料可追溯、图片与内容路径有效、站点构建通过；未经浏览器或实验验证的项目不声称通过。

本轮最终验证：`npm run build` 通过；16 个来源哈希、24 个讲次 ID/视频链接映射、本地图片、SVG 解析、字幕时间结构与状态文件检查通过。5310 端口已有开发服务器。没有进行浏览器视觉/交互测试或 xv6 实验测试。

### P1 · 冻结来源清单

主 agent 从 `lecture-index.json` 核对 24 讲及 11 个实验的对应。明确年份、讲师、视频有无、指定阅读、实验版本；实验截止时间不等于讲次关联。

优先复用 P0 文件，准备共享教材、实验、论文和代码。每个来源分别记 discovered/fetched/partial/blocked/reviewed；链接发现不等于读过。字幕失败后继续整理官网材料，保留缺口，不猜时间轴。

### P2 · 第一批多 agent

建议先 **3 个讲次 worker + 1 个实验 worker**，主 agent 负责整合。共享来源先准备好，再分发只读路径。

| 角色 | 首批任务 | 唯一可写范围（课程目录内） |
|---|---|---|
| Worker A | LEC 2：C 与 GDB；按官方 PDF、代码整理 | `lectures/lec02/` |
| Worker B | LEC 3：OS organization and system calls | `lectures/lec03/` |
| Worker C | LEC 4：Page tables | `lectures/lec04/` |
| Worker D | util 材料补全；syscall/pgtbl 实验中文材料 | `labs/util/`、`labs/syscall/`、`labs/pgtbl/` |
| 主 agent | 来源清单、课程元数据、完成度、最终核对 | `course.json`、共享 `sources/` 与任务清单 |
| 前端会话 | 页面分区、样式、路由及功能 | `src/` 等站点代码 |

实验 worker 写公共正文，讲次 worker 只写实验衔接；子 agent 不改 catalog 或总索引。完成后主 agent 统一合并元数据。

之后按 3–4 讲一批扩展 LEC 5–24。Q&A 保留真实问答性质，缺讲义时不能自动生成教材章节代替。

### P3 · 每批一次核对

检查来源与年份、课堂/讲义边界、关键例子、图片/文档链接和构建。复杂公式与板书需要对照页面或视频画面。字幕时间检查只能证明结构有效，不能证明译文完整。

实验测试在实际搭好工具链并实现代码后运行；抓内容不等于实验通过。

### P4 · 6.824 与更多大学课程

先复用 6.824 已有稿件与资产，建立明确的学期来源表，再补官网译文和实验链接。随后使用同一协议引入 CMU 15-445、Stanford CS336 等课程，每个学期独立管理。

## 6. 可直接分发的 agent 任务模板

```text
目标：整理 MIT 6.S081 Fall 2020 LEC <N>，产出可独立阅读的中文内容包。
先读根目录 AGENTS.md、docs/PLAN.md，并加载 technical-video-notes。
只读：lecture-index.json、已分配来源、共享教材和实验材料。
可写：content/mit-6.s081-2020/lectures/lec<NN>/。
不得改：catalog/course.json、共享来源、其他讲次、前端、skill。
交付：notes.zh.md（提炼、推导、自测、文末引用）、materials.zh.md（指定教材章节/论文译文）、draft.zh.md（视频逐段整理）、status.json、assets/。
三份不重复：课堂截图只放 draft；课堂提纲式的官方讲义不单独翻译；notes 不复述课堂流水，用“见中文译稿 MM:SS–MM:SS”指过去。正文开头不写来源与覆盖说明，统一放文末引用节。
正文保留因果、推导和具体例子；摘要不替代正文。
无字幕/无视频时明示缺口，不猜时间；实验引用指定公共目录。
只把实际读过的材料记为 reviewed，给出 URL、章节或时间。
验收：相对图片可达、来源与版本一致；不虚报实验运行或全片覆盖。
汇报：产物路径、来源、覆盖范围、阻塞；共享修改建议交主 agent。
```

## 7. 运行、复现与交接

```sh
npm run dev
# http://localhost:5310/
npm run build
```

样本：`/#/c/mit-6.s081-2020/lec/lec01`。

实验：`/#/c/mit-6.s081-2020/lab/util`，选择“指导”。

重新获取来源：`python3 scripts/fetch_s081_pilot.py`，依赖 Python 3、yt-dlp 和网络。此命令会更新快照与时间；更新后需重新核对依赖它的正文。

字幕规范化脚本位于 OpenCode skill 的 `scripts/normalize_captions.py`；教材文本用 pdftotext 提取。仅处理文本的本轮没有下载音视频。

建议下一步：先读 Lecture 1 确认内容深度，再执行 P1/P2 首批。独立五分区 UI 的调整交前端会话，内容按当前协议即可继续生产。

## 2026-11-13：D2L单讲听课试点

- 用户要求中文课程不能只提供教材导读，先试一讲的页内视频与课堂内容，不批量铺开。
- `Lecture.video` 新增可选 `embed`、`language` 与 `checkpoints`；只在D2L LEC1配置。`embed: true`且有B站链接时，默认进入“课程视频”，`?v=notes`仍直接阅读旧笔记。中文视频的稿件标签显示“课堂整理”，不改文件协议或伪造`draft.zh.md`。
- 播放器点击后才连接B站，不自动播放；切换材料或讲次会卸载。原站链接始终保留，以处理登录、清晰度或第三方不可用；不把iframe加载或看完视频等同于学习完成。
- 第1讲导览依据实际抽查画面，只有定位点和简短改写，未转写音频、未完整审读口述，不冒充讲稿；来源与验收记录在`content/d2l-pytorch-2021/sources/video-pilot-lec01.json`。不发布课堂截图或媒体。
- 讲座页头/来源区补齐已有B站链接；其他讲次仍维持阅读优先，MIT的YouTube入口和“中文译稿”保持。
- 真实浏览器确认：初始不请求B站，点击可加载并播放，时间实际推进；切换笔记卸载iframe；390px无整页横向溢出，明暗主题可读，非试点讲次与MIT正常。本次是界面试点，不推进P4内容批次。

