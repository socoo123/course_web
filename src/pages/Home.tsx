import { Link } from "react-router-dom";
import { Footer, TopBar } from "../components/TopBar";
import { Icon, type IconName } from "../components/Icon";
import { Bar, SchoolBadge, StatusPill, courseStyle } from "../components/bits";
import { findLab, findLecture, getCatalog, getCourse } from "../lib/content";
import { courseStats, nextLecture } from "../lib/courseStats";
import { useProgress } from "../lib/progress";
import type { CourseSummary } from "../lib/types";

function ContinueCard() {
  const progress = useProgress();
  const catalog = getCatalog();
  const courseId = progress.lastCourse ?? catalog.courses.find((c) => c.status === "active")?.id;
  const bundle = courseId ? getCourse(courseId) : undefined;
  if (!bundle) return null;
  const { summary, detail } = bundle;
  const p = progress.courses[summary.id] ?? { lectures: {}, tasks: {} };
  const stats = courseStats(detail, p);

  const last = p.last;
  const lastLec = last?.kind === "lecture" ? findLecture(detail, last.id) : undefined;
  const lastLab = last?.kind === "lab" ? findLab(detail, last.id) : undefined;
  const next = nextLecture(detail, p);
  const target = lastLec
    ? { to: `/c/${summary.id}/lec/${lastLec.id}`, tag: `LEC ${lastLec.num}`, title: lastLec.title, hint: "上次读到" }
    : lastLab
      ? { to: `/c/${summary.id}/lab/${lastLab.id}`, tag: `LAB ${lastLab.num}`, title: lastLab.title, hint: "上次做到" }
      : next
        ? { to: `/c/${summary.id}/lec/${next.id}`, tag: `LEC ${next.num}`, title: next.title, hint: "从这里开始" }
        : { to: `/c/${summary.id}`, tag: summary.code, title: summary.title, hint: "课程主页" };

  return (
    <div data-course style={courseStyle(summary)} className="card relative overflow-hidden p-5 shadow-[0_1px_0_rgb(var(--line))] sm:p-6">
      <div className="absolute inset-x-0 top-0 h-1 bg-course" />
      <div className="flex items-center justify-between">
        <span className="eyebrow">继续学习</span>
        <SchoolBadge school={summary.school} />
      </div>
      <Link to={`/c/${summary.id}`} className="mt-4 block font-mono text-sm font-semibold text-course hover:underline">
        {summary.code} · {summary.title}
      </Link>
      <Link to={target.to} className="group mt-3 block rounded-xl border border-line bg-bg/60 p-4 transition hover:border-course/50">
        <div className="text-xs text-ink-3">{target.hint}</div>
        <div className="mt-1 flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-course">{target.tag}</span>
          <span className="truncate font-serif text-lg font-semibold text-ink">{target.title}</span>
          <Icon name="arrowRight" className="ml-auto h-4 w-4 shrink-0 text-ink-3 transition group-hover:translate-x-0.5 group-hover:text-course" />
        </div>
      </Link>
      <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="flex justify-between text-ink-3">
            讲座 <span className="font-mono text-ink-2">{stats.lecDone}/{stats.lecTotal}</span>
          </dt>
          <dd className="mt-2">
            <Bar value={stats.lecDone} total={stats.lecTotal} />
          </dd>
        </div>
        <div>
          <dt className="flex justify-between text-ink-3">
            Lab 任务 <span className="font-mono text-ink-2">{stats.taskDone}/{stats.taskTotal}</span>
          </dt>
          <dd className="mt-2">
            <Bar value={stats.taskDone} total={stats.taskTotal} />
          </dd>
        </div>
      </dl>
    </div>
  );
}

function CourseCard({ c }: { c: CourseSummary }) {
  const progress = useProgress();
  const detail = getCourse(c.id)?.detail;
  const stats = courseStats(detail, progress.courses[c.id] ?? { lectures: {}, tasks: {} });
  const planned = c.status === "planned";
  const done = stats.lecDone + stats.taskDone;
  const total = stats.lecTotal + stats.taskTotal;

  return (
    <Link
      to={`/c/${c.id}`}
      data-course
      style={courseStyle(c)}
      className={
        "group relative flex flex-col overflow-hidden rounded-2xl border bg-surface p-5 transition duration-200 " +
        (planned ? "border-line hover:border-line-strong" : "border-line hover:-translate-y-0.5 hover:border-course/50 hover:shadow-[0_10px_30px_-12px_rgb(var(--course)/0.35)]")
      }
    >
      <div className="flex items-center justify-between">
        <SchoolBadge school={c.school} />
        <StatusPill status={c.status} />
      </div>
      <div className="mt-6 flex items-baseline gap-2">
        <span className={"font-mono text-[34px] font-semibold leading-none tracking-tight " + (planned ? "text-ink-3" : "text-course")}>
          {c.code}
        </span>
        {c.altCode && <span className="font-mono text-sm text-ink-3">/ {c.altCode}</span>}
      </div>
      <h3 className="mt-3 font-serif text-xl font-semibold text-ink">{c.title}</h3>
      <p className="text-[13px] text-ink-3">{c.titleEn}</p>
      <p className="mt-3 flex-1 text-sm leading-relaxed text-ink-2">{c.blurb}</p>
      <div className="mt-4 flex flex-wrap gap-1.5">
        {c.tags.map((t) => (
          <span key={t} className="rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-ink-2">
            {t}
          </span>
        ))}
      </div>
      <div className="mt-5 border-t border-line pt-4">
        {planned ? (
          <div className="hatch flex h-7 items-center rounded-md px-2 text-xs text-ink-3">内容抓取中，课表与材料待生成</div>
        ) : (
          <>
            <div className="mb-2 flex justify-between text-xs text-ink-3">
              <span>
                {detail?.lectures.length ?? c.counts?.lectures ?? 0} 讲 · {detail?.labs.length ?? c.counts?.labs ?? 0} 个实验
                {c.effort ? ` · ${c.effort}` : ""}
              </span>
              <span className="font-mono">{total ? Math.round((done / total) * 100) : 0}%</span>
            </div>
            <Bar value={done} total={total} />
          </>
        )}
      </div>
    </Link>
  );
}

const MATERIAL_INTRO: { icon: IconName; title: string; desc: string }[] = [
  { icon: "pen", title: "课程笔记", desc: "图文学习笔记：核心概念、推导、代码导读和自测题。" },
  { icon: "lang", title: "中文译稿", desc: "课堂视频的逐段中文整理，按原片时间顺序。" },
  { icon: "book", title: "课程资料", desc: "官方讲义、指定教材章节等英文资料的中文译文。" },
  { icon: "flask", title: "实验", desc: "实验说明中译 + 实验指导 + 任务清单，进度存在本地浏览器。" },
];

export default function Home() {
  const catalog = getCatalog();
  const byId = new Map(catalog.courses.map((c) => [c.id, c]));

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1200px] px-4 sm:px-6">
        <section className="grid grid-cols-1 gap-10 pb-16 pt-14 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:items-center lg:pt-20">
          <div>
            <div className="eyebrow">Self-taught CS · 中文精读</div>
            <h1 className="mt-4 font-serif text-[40px] font-bold leading-[1.15] tracking-tight text-ink sm:text-[52px]">
              把名校的 CS 课，
              <br />
              修成自己的<span className="relative whitespace-nowrap">
                学位
                <span className="absolute inset-x-0 -bottom-1 h-[6px] rounded-full bg-course/35" />
              </span>
              。
            </h1>
            <p className="mt-6 max-w-xl text-[15.5px] leading-[1.9] text-ink-2">
              MIT、CMU、Stanford 的原版讲座和 Lab，配上逐段中文译稿、学习笔记和中译实验说明，按真实课表一周一周往前推。
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#catalog" className="btn-primary">
                浏览课程 <Icon name="arrowRight" className="h-4 w-4" />
              </a>
            </div>
          </div>
          <ContinueCard />
        </section>

        <section className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {MATERIAL_INTRO.map((m) => (
            <div key={m.title} className="bg-surface p-5">
              <div className="flex items-center gap-2 text-ink">
                <Icon name={m.icon} className="h-4 w-4 text-ink-3" />
                <span className="font-medium">{m.title}</span>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-3">{m.desc}</p>
            </div>
          ))}
        </section>

        <div id="catalog" className="scroll-mt-20" />
        {catalog.tracks.map((t, ti) => (
          <section key={t.id} className="mt-20">
            <div className="mb-6 grid gap-2 border-b border-line pb-4 sm:grid-cols-[auto_1fr] sm:items-end sm:gap-8">
              <div>
                <div className="eyebrow">
                  方向 {String(ti + 1).padStart(2, "0")} · {t.nameEn}
                </div>
                <h2 className="mt-1.5 font-serif text-[26px] font-semibold text-ink">{t.name}</h2>
              </div>
              <p className="text-sm leading-relaxed text-ink-3 sm:text-right">{t.desc}</p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {t.courses.map((id) => {
                const c = byId.get(id);
                return c ? <CourseCard key={id} c={c} /> : null;
              })}
            </div>
          </section>
        ))}
      </main>
      <Footer />
    </div>
  );
}
