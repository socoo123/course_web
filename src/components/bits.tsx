import { useState, type CSSProperties, type ReactNode } from "react";
import type { CourseSummary, Lecture } from "../lib/types";
import { Icon } from "./Icon";

export function CopyButton({ text, className = "" }: { text: string; className?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setDone(true);
          setTimeout(() => setDone(false), 1400);
        });
      }}
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-ink-3 transition hover:bg-surface-3 hover:text-ink ${className}`}
      aria-label="复制"
    >
      <Icon name={done ? "check" : "copy"} className="h-3.5 w-3.5" />
      {done ? "已复制" : "复制"}
    </button>
  );
}

/** 给子树注入课程主题色 */
export function courseStyle(c: Pick<CourseSummary, "accent">): CSSProperties {
  return { "--course-l": c.accent.light, "--course-d": c.accent.dark } as CSSProperties;
}

export function LectureBadges({ lec }: { lec: Lecture }) {
  return (
    <>
      {lec.isNew && <span className="rounded bg-warn/10 px-1.5 py-px text-[11px] font-medium text-warn">新讲次 · 无视频</span>}
      {lec.optional && <span className="rounded border border-dashed border-line-strong px-1.5 py-px text-[11px] text-ink-3">选读</span>}
      {lec.core && <span className="rounded bg-course/10 px-1.5 py-px text-[11px] text-course">核心</span>}
    </>
  );
}

export function SchoolBadge({ school }: { school: string }) {
  return (
    <span className="rounded-[5px] border border-line-strong/70 px-1.5 py-px font-mono text-[10.5px] font-semibold tracking-[0.12em] text-ink-2">
      {school.toUpperCase()}
    </span>
  );
}

export function StatusPill({ status }: { status: CourseSummary["status"] }) {
  if (status === "active")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-course/10 px-2 py-0.5 text-[11.5px] font-medium text-course">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-course opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-course" />
        </span>
        在修
      </span>
    );
  if (status === "done")
    return <span className="rounded-full bg-ok/10 px-2 py-0.5 text-[11.5px] font-medium text-ok">已修完</span>;
  return <span className="rounded-full border border-dashed border-line-strong px-2 py-0.5 text-[11.5px] text-ink-3">筹备中</span>;
}

export function Bar({ value, total, className = "" }: { value: number; total: number; className?: string }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className={`h-1.5 overflow-hidden rounded-full bg-surface-3 ${className}`} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-course transition-[width] duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

/** 材料就绪标记：每个字一个小方块，实心 = 已就绪，虚线 = 待生成 */
export function MaterialMarks({ items }: { items: { label: string; ready: boolean }[] }) {
  return (
    <span className="inline-flex gap-1" aria-label={items.map((i) => `${i.label}${i.ready ? "已就绪" : "待生成"}`).join("，")}>
      {items.map((i) => (
        <span
          key={i.label}
          title={`${i.label}：${i.ready ? "已就绪" : "待生成"}`}
          className={
            "grid h-[18px] w-[18px] place-items-center rounded-[4px] text-[10.5px] leading-none " +
            (i.ready ? "bg-course/15 font-medium text-course" : "border border-dashed border-line-strong text-ink-3/70")
          }
        >
          {i.label[0]}
        </span>
      ))}
    </span>
  );
}

export function Stars({ n, max = 5 }: { n: number; max?: number }) {
  return (
    <span className="inline-flex gap-px text-[11px] tracking-tight" aria-label={`难度 ${n}/${max}`}>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={i < n ? "text-course" : "text-line-strong"}>
          ★
        </span>
      ))}
    </span>
  );
}

export function CheckCircle({ checked, onClick, label }: { checked: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onClick();
      }}
      aria-pressed={checked}
      aria-label={label}
      title={label}
      className={
        "grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border transition " +
        (checked ? "border-course bg-course text-white dark:text-bg" : "border-line-strong text-transparent hover:border-course")
      }
    >
      <Icon name="check" className="h-3 w-3" strokeWidth={3} />
    </button>
  );
}

export function SectionTitle({ eyebrow, title, desc, right }: { eyebrow?: string; title: string; desc?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <h2 className="font-serif text-2xl font-semibold text-ink">{title}</h2>
        {desc && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-3">{desc}</p>}
      </div>
      {right}
    </div>
  );
}
