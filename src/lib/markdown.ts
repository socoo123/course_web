/** 解析材料文件：可选的 `---` 头信息 + 正文；引用类内容统一挪到页底 */

export interface ParsedDoc {
  meta: Record<string, string>;
  body: string;
}

export function parseFrontmatter(src: string): ParsedDoc {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(src);
  if (!m) return { meta: {}, body: src };
  const meta: Record<string, string> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const i = line.indexOf(":");
    if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return { meta, body: src.slice(m[0].length) };
}

export interface RefSection {
  title: string;
  body: string;
}

export interface SplitDoc {
  main: string;
  /** 正文里以「来源：」起头的段落 */
  notes: string[];
  /** 标题为 引用 / 参考 / 来源 / 许可 等的二级节 */
  refs: RefSection[];
}

const REF_HEADING = /(引用|参考|来源|出处|许可|版权|致谢|references?|sources?|credits?|bibliography|license)/i;
const REF_PARAGRAPH = /^(来源|出处|资料来源|source)\s*[：:]/i;

/** 把引用类内容从正文中拆出来，正文顺序不变 */
export function splitReferences(body: string): SplitDoc {
  const lines = body.split(/\r?\n/);
  const blocks: { heading?: string; lines: string[] }[] = [{ lines: [] }];
  let fence = false;
  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) fence = !fence;
    const h = !fence && /^##\s+(.+?)\s*#*\s*$/.exec(line);
    if (h) blocks.push({ heading: h[1], lines: [] });
    else blocks[blocks.length - 1].lines.push(line);
  }

  const main: string[] = [];
  const refs: RefSection[] = [];
  const notes: string[] = [];

  /** 按空行切段，挑出代码块之外的「来源：」段落 */
  const pickNotes = (text: string) => {
    let inFence = false;
    return text
      .split(/\n\s*\n/)
      .filter((p) => {
        const isNote = !inFence && REF_PARAGRAPH.test(p.trim());
        if ((p.match(/^\s*(```|~~~)/gm)?.length ?? 0) % 2) inFence = !inFence;
        if (isNote) notes.push(p.trim());
        return !isNote;
      })
      .join("\n\n");
  };

  blocks.forEach((b, i) => {
    if (i === 0) main.push(pickNotes(b.lines.join("\n")));
    else if (b.heading && REF_HEADING.test(b.heading)) refs.push({ title: b.heading, body: b.lines.join("\n").trim() });
    else main.push(`## ${b.heading}\n${pickNotes(b.lines.join("\n"))}`);
  });

  return { main: main.join("\n\n"), notes, refs };
}
