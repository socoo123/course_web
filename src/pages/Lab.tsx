import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Icon } from "../components/Icon";
import { Bar, CheckCircle, CopyButton, Stars } from "../components/bits";
import { DocView, MaterialTabs, PrevNext, ReaderShell, Toc, useView, type MaterialTab, type RefExtra, type TocItem } from "../components/Reader";
import { getCourse, labDir, labMaterials, lecturesOfLab } from "../lib/content";
import { recordVisit, toggleTask, useCourseProgress } from "../lib/progress";
import { LAB_MATERIALS, type Lab as LabT, type LabMaterial } from "../lib/types";
import NotFound from "./NotFound";

function TaskList({ courseId, lab }: { courseId: string; lab: LabT }) {
  const p = useCourseProgress(courseId);
  const done = lab.tasks.filter((t) => p.tasks[`${lab.id}/${t.id}`]).length;
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-center justify-between">
        <span className="eyebrow">任务清单</span>
        <span className="font-mono text-xs text-ink-3">
          {done}/{lab.tasks.length}
        </span>
      </div>
      <Bar value={done} total={lab.tasks.length} className="mt-2.5" />
      <ul className="mt-3 space-y-0.5">
        {lab.tasks.map((t) => {
          const on = !!p.tasks[`${lab.id}/${t.id}`];
          return (
            <li key={t.id}>
              <label className="flex cursor-pointer items-start gap-2.5 rounded-lg px-1.5 py-1.5 hover:bg-surface-2">
                <span className="pt-0.5">
                  <CheckCircle checked={on} onClick={() => toggleTask(courseId, lab.id, t.id)} label={on ? "标记未完成" : "标记完成"} />
                </span>
                <span className="min-w-0">
                  <span className={"block text-[13.5px] " + (on ? "text-ink-3 line-through decoration-line-strong" : "text-ink")}>{t.title}</span>
                  {t.titleEn && t.titleEn !== t.title && <span className="block text-[11.5px] text-ink-3">{t.titleEn}</span>}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Commands({ lab }: { lab: LabT }) {
  const lines = [`git checkout ${lab.branch}`, "make qemu", "make grade", ...lab.tasks.filter((t) => t.grade).map((t) => t.grade!)];
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-[rgb(var(--code-bg))]">
      <div className="flex items-center justify-between border-b border-line px-3 py-1">
        <span className="flex items-center gap-1.5 text-[11px] text-ink-3">
          <Icon name="terminal" className="h-3.5 w-3.5" />
          常用命令
        </span>
        <CopyButton text={lines.join("\n")} />
      </div>
      <pre className="overflow-x-auto px-3 py-2.5 font-mono text-[11.5px] leading-[1.85] text-ink">
        {lines.map((l) => (
          <div key={l}>
            <span className="select-none text-ink-3">$ </span>
            {l}
          </div>
        ))}
      </pre>
    </div>
  );
}

export default function Lab() {
  const { courseId = "", labId = "" } = useParams();
  const bundle = getCourse(courseId);
  const detail = bundle?.detail;
  const lab = detail?.labs.find((l) => l.id === labId);
  const [toc, setToc] = useState<TocItem[]>([]);
  const onToc = useCallback((t: TocItem[]) => setToc(t), []);

  useEffect(() => {
    if (lab) recordVisit(courseId, "lab", lab.id);
  }, [courseId, lab]);

  const m = labMaterials(courseId, labId);
  const tabs: MaterialTab[] = [
    { id: "zh", label: LAB_MATERIALS.zh.label, icon: "lang", ready: m.zh },
    { id: "guide", label: LAB_MATERIALS.guide.label, icon: "compass", ready: m.guide },
    // 英文原文只在提供了文件时出现
    ...(m.en ? [{ id: "en", label: LAB_MATERIALS.en.label, icon: "file" as const, ready: true }] : []),
  ];
  const [view, setView] = useView(tabs);

  if (!bundle || !detail || !lab) return <NotFound />;
  const course = bundle.summary;
  const dir = labDir(courseId, labId);
  const related = lecturesOfLab(detail, lab.id);
  const i = detail.labs.findIndex((l) => l.id === lab.id);
  const link = (l?: LabT) => l && { to: `/c/${courseId}/lab/${l.id}`, tag: `LAB ${l.num}`, title: l.title };

  const extraRefs: RefExtra[] = [
    {
      label: "官方页面",
      content: (
        <a href={lab.url} target="_blank" rel="noreferrer" className="break-all underline decoration-line-strong underline-offset-2 hover:text-course">
          {lab.url}
        </a>
      ),
    },
  ];

  const header = (
    <header className="pb-6 pt-8 lg:pt-10">
      <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-ink-3">
        <span className="font-semibold text-course">LAB {lab.num}</span>
        <span>·</span>
        <span>{lab.branch}</span>
      </div>
      <h1 className="mt-3 font-serif text-[30px] font-bold leading-tight text-ink sm:text-[34px]">{lab.title}</h1>
      <p className="mt-1 text-[15px] text-ink-3">{lab.titleEn}</p>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-ink-2">{lab.goal}</p>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        <span className="chip">
          难度 <Stars n={lab.stars} />
        </span>
        <span className="chip">
          <Icon name="clock" className="h-3 w-3" />
          {lab.hours}
          {/^\d/.test(lab.hours) ? " 小时" : ""}
        </span>
        <span className="chip font-mono">
          <Icon name="branch" className="h-3 w-3" />
          {lab.branch}
        </span>
        {related.map((l) => (
          <Link key={l.id} to={`/c/${courseId}/lec/${l.id}`} className="chip hover:border-course/50 hover:text-ink">
            <Icon name="play" className="h-3 w-3 text-course" />
            LEC {l.num} {l.title}
          </Link>
        ))}
      </div>
    </header>
  );

  const current = view as LabMaterial;

  return (
    <ReaderShell
      course={course}
      detail={detail}
      active={{ kind: "lab", id: lab.id }}
      crumb={`Lab ${lab.num} ${lab.branch}`}
      header={header}
      rail={
        <div className="space-y-6">
          <TaskList courseId={courseId} lab={lab} />
          <Commands lab={lab} />
          <Toc items={toc} />
        </div>
      }
    >
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:hidden">
        <TaskList courseId={courseId} lab={lab} />
        <Commands lab={lab} />
      </div>
      <MaterialTabs tabs={tabs} view={view} onChange={setView} />
      <div className="max-w-prose">
        <DocView key={view} path={dir + LAB_MATERIALS[current].file} what={LAB_MATERIALS[current].label} onToc={onToc} extraRefs={extraRefs} />
      </div>
      <PrevNext prev={link(detail.labs[i - 1])} next={link(detail.labs[i + 1])} />
    </ReaderShell>
  );
}
