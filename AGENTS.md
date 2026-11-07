# AGENTS.md — 自修大学（课程站）内容约定

纯静态站：Vite + React + Tailwind，HashRouter，部署到 GitHub Pages。
**内容 agent 只改 `content/`，不碰 `src/`。** 放进去的文件在构建时自动被收集，不需要注册或改代码。

```bash
npm install
npm run dev      # http://localhost:5310
npm run build    # 类型检查 + 构建到 dist/，提交前必须通过
```

## 页面结构

每门课是一个阅读页，左侧栏三块：

1. **公共资料**：课程首页。教材、实验环境、代码仓库、课程网站等各讲共用的资料，写成一章。
2. **课程**：每讲三个标签——**课程笔记** / **中文译稿** / **课程资料**。
3. **实验**：每个实验两个标签——**实验说明**（官方要求中译）/ **实验指导**；提供了英文原文才多出一个「英文原文」标签。

## 目录

```
content/
├── catalog.json                      # 课程目录：方向（tracks）+ 课程卡片（courses）
└── <courseId>/                       # 如 mit-6.s081-2020；不同学期用不同 courseId
    ├── course.json                   # 讲座 / 实验元数据（有了它侧栏才出现内容）
    ├── resources.zh.md               # 公共资料章
    ├── lectures/<lectureId>/
    │   ├── notes.zh.md               # 课程笔记：自主整理的学习讲解、推导、自测
    │   ├── draft.zh.md               # 中文译稿：课堂视频的逐段中文整理（按原片时间顺序）
    │   ├── materials.zh.md           # 课程资料：课堂之外的阅读材料（指定教材章节、论文）的中文译文
    │   └── assets/                   # 图片，md 里用相对路径 ![](assets/x.svg)
    ├── labs/<labId>/
    │   ├── lab.zh.md                 # 实验说明：官方实验页中译
    │   ├── guide.zh.md               # 实验指导：思路骨架、常见坑，不给完整答案
    │   ├── lab.en.md                 # 可选：英文原文
    │   └── assets/
    └── sources/                      # 原始抓取物（html/pdf/字幕 json），不上线
```

- 文件存在 = 该标签有内容；不存在就显示“待生成”和应放的路径。
- `<lectureId>` / `<labId>` 必须和 `course.json` 里的 `id` 一致。
- `content/` 下**所有** `.md` 都会被打包上线；原始资料放 `sources/`，且不要用 `.md` 后缀。
- 一份资料被多讲共用（教材、工具链、实验仓库）就写进 `resources.zh.md`，各讲只链接过去。

### 三份讲座材料不重复

三份材料各管一件事，同一内容只在一处展开，其他地方写“见中文译稿 MM:SS–MM:SS”或“见课程资料 §x.y”：

| 文件 | 只放 | 不放 |
|---|---|---|
| `draft.zh.md` 中文译稿 | 课堂本身：按时间顺序的完整讲授、演示、问答；**课堂截图只放这里** | 讲义、教材译文 |
| `materials.zh.md` 课程资料 | 课堂之外的阅读：指定教材章节、论文、补充资料的译文 | 课堂截图；只是课堂提纲的官方讲义（课上逐项讲过的，不再译一遍） |
| `notes.zh.md` 课程笔记 | 提炼：核心问题、推导、易错点、自测；需要图时用自绘示意图（`assets/*.svg`） | 课堂截图；按课堂顺序复述讲授内容；整段贴课上演示过的代码 |

官方讲义里有、课上没讲到的部分（例如第 1 讲的管道与目录），在课程笔记里点明，并指向课程资料中对应的教材小节。

## course.json

字段以 `src/lib/types.ts` 的 `CourseDetail` 为准，参考 `content/mit-6.s081-2020/course.json`：

- `intro`：写给学习者的一段课程介绍。**不要写抓取进度、覆盖率、缺口**——这些写进 `status.json` 或各文件的 `status` 头信息。
- `versions[]`：`{label, value}`，如 学期、教材版本。
- `lectures[]`：`id`、`num`（"1" 或 "选读"）、`title`、`titleEn`，可选 `video{label,youtube,duration}`、`readings[]`（指定阅读）、`lab`（对应实验 id）、`note`、`core`、`isNew`、`optional`。
- `labs[]`：`id`、`num`、`title`、`titleEn`、`stars`(1–5)、`hours`、`branch`、`url`、`goal`、`tasks[]{id,title,titleEn?,grade?}`。
- 可选：`links[]`、`resources[]`、`workflow[]`（没写 `resources.zh.md` 时用来兜底展示）；`weeks[]`（只用来给讲座排序和显示“第 N 周”，不展示课表）。

新增课程：在 `catalog.json` 的 `courses` 加卡片（`status: active|planned|done`，`accent` 填浅/深两套 RGB 三元组），并放进某个 `tracks[].courses`。

## Markdown 写法

**引用一律放页底。** 页面会把下面三类内容自动收进底部的「引用与来源」区，正文开头只写学习内容：

1. 头信息（显示为来源 / 视频 / 许可 / 状态）：

   ```markdown
   ---
   source: 官方讲义 URL / 教材版本
   video: 视频标题 · 时长
   license: CC BY 3.0 US
   status: 一句话说明完成度与缺口
   ---
   ```

2. 标题含 **引用 / 参考 / 来源 / 出处 / 许可 / 版权 / 致谢 / References / Sources** 的 `##` 节——所以正文小节不要用这些词起标题。
3. 以「来源：」开头的段落。

正文开头不要写“本文依据……”“当前覆盖……”这类说明，放进上面的引用节。

其他：支持 GFM 表格、```mermaid 代码块、`$…$` / `$$…$$` 公式（KaTeX）、`<details><summary>` 折叠答案。文件开头的 `# 一级标题` 会被隐藏（页头已有标题）。站内跳转用 `#/c/<courseId>/lec/<id>?v=notes|draft|materials`、`#/c/<courseId>/lab/<id>?v=zh|guide`。

## 版权

站点公开。CC 授权的材料（如 6.S081 课程网站，CC BY 3.0）可全文翻译，保留署名与许可链接；授权不明的视频字幕只做译述和笔记，不整段搬运原文。

## 部署

推送到 `main` 后 `.github/workflows/pages.yml` 自动构建发布。首次需在仓库 Settings → Pages 把 Source 设为 **GitHub Actions**。
