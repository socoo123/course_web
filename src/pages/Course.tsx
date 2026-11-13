import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Footer, TopBar } from "../components/TopBar";
import { Icon } from "../components/Icon";
import { Bar, CopyButton, SchoolBadge, StatusPill, courseStyle } from "../components/bits";
import { DocView, Missing, ReaderShell, References, Toc, type TocItem } from "../components/Reader";
import { courseResourcesPath, getCourse } from "../lib/content";
import { courseStats, nextLecture } from "../lib/courseStats";
import { useCourseProgress } from "../lib/progress";
import type { CourseDetail, CourseSummary } from "../lib/types";
import NotFound from "./NotFound";

function CourseHeader({ course, detail }: { course: CourseSummary; detail: CourseDetail }) {
  const p = useCourseProgress(course.id);
  const stats = courseStats(detail, p);
  const next = nextLecture(detail, p);
  return (
    <header className="pb-8 pt-8 lg:pt-10">
      <div className="flex items-center gap-2">
        <SchoolBadge school={course.school} />
        <StatusPill status={course.status} />
      </div>
      <div className="mt-4 flex flex-wrap items-baseline gap-x-3">
        <span className="font-mono text-4xl font-semibold tracking-tight text-course sm:text-5xl">{course.code}</span>
        {course.altCode && <span className="font-mono text-base text-ink-3">/ {course.altCode}</span>}
      </div>
      <h1 className="mt-3 font-serif text-[28px] font-bold text-ink">{course.title}</h1>
      <p className="text-sm text-ink-3">{course.titleEn}</p>
      <p className="mt-5 max-w-2xl text-[15px] leading-[1.85] text-ink-2">{detail.intro || course.blurb}</p>

      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-3 text-sm">
        <div>
          <div className="eyebrow mb-1">讲师</div>
          <div className="text-ink-2">{detail.instructors.join("、")}</div>
        </div>
        {detail.versions.map((v) => (
          <div key={v.label}>
            <div className="eyebrow mb-1">{v.label}</div>
            <div className="text-ink-2">{v.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-7 grid max-w-2xl gap-4 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div>
          <div className="flex justify-between text-[13px] text-ink-3">
            课程 <span className="font-mono text-ink-2">{stats.lecDone}/{stats.lecTotal}</span>
          </div>
          <Bar value={stats.lecDone} total={stats.lecTotal} className="mt-2" />
        </div>
        <div>
          <div className="flex justify-between text-[13px] text-ink-3">
            实验任务 <span className="font-mono text-ink-2">{stats.taskDone}/{stats.taskTotal}</span>
          </div>
          <Bar value={stats.taskDone} total={stats.taskTotal} className="mt-2" />
        </div>
        {next && (
          <Link to={`/c/${course.id}/lec/${next.id}`} className="btn-primary justify-center">
            {stats.lecDone ? "继续" : "开始"} · LEC {next.num}
            <Icon name="arrowRight" className="h-4 w-4" />
          </Link>
        )}
      </div>
    </header>
  );
}

/** 还没写公共资料章时，用 course.json 里的链接和资源兜底 */
function ResourcesFallback({ course, detail }: { course: CourseSummary; detail: CourseDetail }) {
  const links = detail.links ?? [];
  const resources = detail.resources ?? [];
  return (
    <div className="pt-8">
      <h2 className="font-serif text-xl font-semibold text-ink">公共资料</h2>
      <p className="mt-2 text-sm text-ink-3">各讲、各实验共用的教材、工具和课程网站。</p>
      {resources.length > 0 && (
        <ul className="mt-5 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          {resources.map((r) => (
            <li key={r.label} className="flex items-start gap-3 px-4 py-3.5">
              <Icon name={r.url ? "link" : "book"} className="mt-0.5 h-4 w-4 shrink-0 text-ink-3" />
              <div className="min-w-0">
                {r.url && /^https?:/.test(r.url) ? (
                  <a href={r.url} target="_blank" rel="noreferrer" className="text-[14.5px] text-ink hover:text-course">
                    {r.label}
                  </a>
                ) : (
                  <span className="text-[14.5px] text-ink">{r.label}</span>
                )}
                {r.desc && <p className="mt-0.5 text-[13px] text-ink-3">{r.desc}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {detail.workflow && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-[rgb(var(--code-bg))]">
          <div className="flex items-center justify-between border-b border-line px-3 py-1">
            <span className="font-mono text-[11px] uppercase tracking-wider text-ink-3">实验通用流程</span>
            <CopyButton text={detail.workflow.join("\n")} />
          </div>
          <pre className="overflow-x-auto px-4 py-3 font-mono text-[12.5px] leading-[1.8] text-ink">
            {detail.workflow.map((l) => (
              <div key={l}>
                <span className="select-none text-ink-3">$ </span>
                {l}
              </div>
            ))}
          </pre>
        </div>
      )}
      <Missing path={courseResourcesPath(course.id)} what="公共资料章" />
      {links.length > 0 && (
        <References
          extra={links.map((l) => ({
            label: l.label,
            content: (
              <a href={l.url} target="_blank" rel="noreferrer" className="break-all underline decoration-line-strong underline-offset-2 hover:text-course">
                {l.url}
              </a>
            ),
          }))}
        />
      )}
    </div>
  );
}

function Planned({ course }: { course: CourseSummary }) {
  return (
    <div data-course style={courseStyle(course)} className="min-h-screen">
      <TopBar crumbs={[{ label: course.title }]} />
      <main className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
        <div className="flex items-center gap-2">
          <SchoolBadge school={course.school} />
          <StatusPill status={course.status} />
        </div>
        <div className="mt-4 font-mono text-5xl font-semibold tracking-tight text-ink-3">{course.code}</div>
        <h1 className="mt-3 font-serif text-[28px] font-bold text-ink">{course.title}</h1>
        <p className="text-sm text-ink-3">{course.titleEn}</p>
        <p className="mt-5 text-[15px] leading-[1.85] text-ink-2">{course.blurb}</p>
        <div className="hatch mt-10 rounded-2xl border border-dashed border-line-strong p-10 text-center">
          <div className="font-serif text-xl font-semibold text-ink">课程内容筹备中</div>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-3">写好下面这个文件后，侧栏会出现这门课的课程和实验。</p>
          <code className="mt-4 inline-block rounded-lg bg-surface px-3 py-1.5 font-mono text-xs text-ink-2">content/{course.id}/course.json</code>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function Course() {
  const { courseId = "" } = useParams();
  const bundle = getCourse(courseId);
  const [toc, setToc] = useState<TocItem[]>([]);
  const onToc = useCallback((t: TocItem[]) => setToc(t), []);

  if (!bundle) return <NotFound />;
  const { summary: course, detail } = bundle;
  if (!detail) return <Planned course={course} />;

  return (
    <ReaderShell course={course} detail={detail} active={{ kind: "home" }} header={<CourseHeader course={course} detail={detail} />} rail={<Toc items={toc} />}>
      <div className="max-w-prose border-t border-line">
        <DocView
          path={courseResourcesPath(course.id)}
          what="公共资料章"
          onToc={onToc}
          missing={<ResourcesFallback course={course} detail={detail} />}
        />
      </div>
    </ReaderShell>
  );
}
