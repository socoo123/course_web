import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Icon, type IconName } from "./Icon";
import { Markdown } from "./Markdown";
import { Footer, TopBar } from "./TopBar";
import { courseStyle } from "./bits";
import { loadFile } from "../lib/content";
import { orderedLectures } from "../lib/courseStats";
import { parseFrontmatter, splitReferences } from "../lib/markdown";
import { useCourseProgress } from "../lib/progress";
import type { CourseDetail, CourseSummary } from "../lib/types";

/* ---------- 加载 ---------- */

type FileState = { status: "loading" } | { status: "ready"; text: string } | { status: "missing" };

export function useFile(path: string | undefined): FileState {
  const [state, setState] = useState<FileState>({ status: "loading" });
  useEffect(() => {
    if (!path) {
      setState({ status: "missing" });
      return;
    }
    let alive = true;
    setState({ status: "loading" });
    loadFile(path).then(
      (text) => alive && setState({ status: "ready", text }),
      () => alive && setState({ status: "missing" }),
    );
    return () => {
      alive = false;
    };
  }, [path]);
  return state;
}

export function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------- 目录 ---------- */

export interface TocItem {
  id: string;
  text: string;
  level: number;
}

export const REFERENCES_ID = "references";

export function Toc({ items }: { items: TocItem[] }) {
  const [active, setActive] = useState<string>();
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        let cur: string | undefined;
        for (const it of items) {
          const el = document.getElementById(it.id);
          if (el && el.getBoundingClientRect().top < 160) cur = it.id;
        }
        setActive(cur ?? items[0]?.id);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
    };
  }, [items]);

  if (!items.length) return null;
  return (
    <nav aria-label="本页目录">
      <div className="eyebrow mb-3">本页目录</div>
      <ul className="space-y-0.5 border-l border-line">
        {items.map((it) => (
          <li key={it.id}>
            <button
              type="button"
              onClick={() => scrollToId(it.id)}
              className={
                "-ml-px block w-full border-l-2 py-1 pr-2 text-left text-[13px] leading-snug transition " +
                (it.level > 2 ? "pl-6 " : "pl-3 ") +
                (it.id === REFERENCES_ID ? "mt-2 " : "") +
                (active === it.id ? "border-course text-ink" : "border-transparent text-ink-3 hover:text-ink-2")
              }
            >
              {it.id === REFERENCES_ID && <Icon name="link" className="mr-1 inline h-3 w-3 -translate-y-px" />}
              {it.text}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* ---------- 侧栏：公共资料 + 课程 + 实验 ---------- */

export type ActiveItem = { kind: "home" } | { kind: "lecture" | "lab"; id: string };

function CourseOutline({ course, detail, active, onNavigate }: { course: CourseSummary; detail: CourseDetail; active: ActiveItem; onNavigate?: () => void }) {
  const p = useCourseProgress(course.id);
  const activeRef = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest" });
  }, []);

  const isActive = (kind: ActiveItem["kind"], id?: string) => active.kind === kind && (!id || ("id" in active && active.id === id));

  const item = (to: string, on: boolean, done: boolean, tag: ReactNode, title: string, muted = false) => (
    <Link
      key={to}
      to={to}
      ref={on ? activeRef : undefined}
      onClick={onNavigate}
      aria-current={on ? "page" : undefined}
      className={
        "group flex items-center gap-2 rounded-md px-2 py-[5px] text-[13px] transition " +
        (on ? "bg-course/10 text-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink")
      }
    >
      <span className={"w-9 shrink-0 font-mono text-[10.5px] " + (on ? "font-semibold text-course" : "text-ink-3")}>{tag}</span>
      <span className={"min-w-0 flex-1 truncate " + (muted ? "text-ink-3" : "")}>{title}</span>
      {done && <Icon name="check" className="h-3.5 w-3.5 shrink-0 text-course" strokeWidth={2.6} />}
    </Link>
  );

  return (
    <div className="flex h-full flex-col">
      <Link to={`/c/${course.id}`} onClick={onNavigate} className="mb-3 block rounded-lg px-2 py-1 hover:bg-surface-2">
        <div className="font-mono text-lg font-semibold text-course">{course.code}</div>
        <div className="truncate text-xs text-ink-3">{course.title}</div>
      </Link>
      <div className="space-y-px">{item(`/c/${course.id}`, isActive("home"), false, <Icon name="book" className="h-3.5 w-3.5" />, "公共资料")}</div>

      <div className="eyebrow mb-1.5 mt-6 px-2">课程</div>
      <div className="space-y-px">
        {orderedLectures(detail).map((l) =>
          item(
            `/c/${course.id}/lec/${l.id}`,
            isActive("lecture", l.id),
            !!p.lectures[l.id],
            /^\d+$/.test(l.num) ? `L${l.num.padStart(2, "0")}` : "选读",
            l.title,
            l.optional,
          ),
        )}
      </div>

      {detail.labs.length > 0 && (
        <>
          <div className="eyebrow mb-1.5 mt-6 px-2">实验</div>
          <div className="space-y-px">
            {detail.labs.map((lab) =>
              item(
                `/c/${course.id}/lab/${lab.id}`,
                isActive("lab", lab.id),
                lab.tasks.length > 0 && lab.tasks.every((t) => p.tasks[`${lab.id}/${t.id}`]),
                `Lab${lab.num}`,
                `${lab.branch} · ${lab.title}`,
              ),
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* ---------- 材料切换 ---------- */

export interface MaterialTab {
  id: string;
  label: string;
  icon: IconName;
  ready: boolean;
}

export function useView(tabs: MaterialTab[]): [string, (id: string) => void] {
  const [params, setParams] = useSearchParams();
  const requested = params.get("v");
  const fallback = tabs.find((t) => t.ready)?.id ?? tabs[0].id;
  const view = tabs.some((t) => t.id === requested) ? requested! : fallback;
  return [view, (id) => setParams({ v: id }, { replace: true })];
}

export function MaterialTabs({ tabs, view, onChange, right }: { tabs: MaterialTab[]; view: string; onChange: (id: string) => void; right?: ReactNode }) {
  return (
    <div className="sticky top-14 z-20 -mx-4 border-b border-line bg-bg/90 px-4 backdrop-blur-md sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0">
      <div className="flex items-center gap-3 py-2.5">
        <div role="tablist" aria-label="材料" className="flex min-w-0 gap-1 overflow-x-auto rounded-xl bg-surface-2 p-1">
          {tabs.map((t) => {
            const on = t.id === view;
            return (
              <button
                key={t.id}
                role="tab"
                type="button"
                aria-selected={on}
                onClick={() => onChange(t.id)}
                className={
                  "relative flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] transition " +
                  (on ? "bg-surface font-medium text-ink shadow-[0_1px_2px_rgb(0_0_0/0.08),0_0_0_1px_rgb(var(--line))]" : "text-ink-3 hover:text-ink")
                }
              >
                <Icon name={t.icon} className={"h-3.5 w-3.5 " + (on ? "text-course" : "")} />
                {t.label}
                {!t.ready && <span className="rounded bg-surface-3 px-1 text-[10px] leading-4 text-ink-3">待生成</span>}
              </button>
            );
          })}
        </div>
        <div className="ml-auto shrink-0">{right}</div>
      </div>
    </div>
  );
}

/* ---------- 引用与来源（页底） ---------- */

const META_LABEL: Record<string, string> = { source: "来源", video: "视频", license: "许可", status: "状态" };

export interface RefExtra {
  label: string;
  content: ReactNode;
}

export function References({
  meta = {},
  notes = [],
  refs = [],
  extra = [],
  baseDir = "/",
}: {
  meta?: Record<string, string>;
  notes?: string[];
  refs?: { title: string; body: string }[];
  extra?: RefExtra[];
  baseDir?: string;
}) {
  const extraLabels = new Set(extra.map((e) => e.label));
  const metaEntries = Object.entries(meta).filter(([k]) => k in META_LABEL && !extraLabels.has(META_LABEL[k]));
  if (!metaEntries.length && !notes.length && !refs.length && !extra.length) return null;
  return (
    <section id={REFERENCES_ID} aria-labelledby="ref-title" className="mt-16 scroll-mt-32 rounded-2xl border border-line bg-surface/60 px-5 py-6 sm:px-7">
      <h2 id="ref-title" className="flex items-center gap-2 font-serif text-lg font-semibold text-ink">
        <Icon name="link" className="h-4 w-4 text-ink-3" />
        引用与来源
      </h2>
      {(metaEntries.length > 0 || extra.length > 0) && (
        <dl className="mt-4 grid gap-x-6 gap-y-2.5 text-[13px] sm:grid-cols-[5rem_1fr]">
          {extra.map((e) => (
            <div key={e.label} className="contents">
              <dt className="text-ink-3">{e.label}</dt>
              <dd className="min-w-0 text-ink-2">{e.content}</dd>
            </div>
          ))}
          {metaEntries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-ink-3">{META_LABEL[k]}</dt>
              <dd className="min-w-0 break-words text-ink-2">
                {/^https?:/.test(v) ? (
                  <a href={v} target="_blank" rel="noreferrer" className="break-all underline decoration-line-strong underline-offset-2 hover:text-course">
                    {v}
                  </a>
                ) : (
                  v
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {notes.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <Markdown source={notes.join("\n\n")} baseDir={baseDir} className="reading-sm" />
        </div>
      )}
      {refs.map((r) => (
        <div key={r.title} className="mt-5 border-t border-line pt-4">
          <h3 className="mb-2 text-[13.5px] font-semibold text-ink">{r.title}</h3>
          <Markdown source={r.body} baseDir={baseDir} className="reading-sm" />
        </div>
      ))}
    </section>
  );
}

/* ---------- 文档 / 空状态 ---------- */

export function Missing({ path, what }: { path: string; what: string }) {
  return (
    <div className="hatch mt-8 rounded-2xl border border-dashed border-line-strong px-6 py-14 text-center">
      <Icon name="file" className="mx-auto h-6 w-6 text-ink-3" />
      <div className="mt-3 font-serif text-lg font-semibold text-ink">{what}还没生成</div>
      <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-3">把文件放到下面这个位置，刷新即可在这里阅读。</p>
      <code className="mt-4 inline-block max-w-full break-all rounded-lg bg-surface px-3 py-1.5 font-mono text-xs text-ink-2">{path.slice(1)}</code>
    </div>
  );
}

function Loading() {
  return (
    <div className="mt-8 space-y-3" aria-busy="true">
      {[90, 100, 75, 95, 60].map((w, i) => (
        <div key={i} className="h-3.5 animate-pulse rounded bg-surface-2" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

/** 渲染一份材料：正文在上，头信息 / 来源段落 / 引用节 统一放到页底 */
export function DocView({ path, what, onToc, extraRefs = [], missing }: { path: string; what: string; onToc: (t: TocItem[]) => void; extraRefs?: RefExtra[]; missing?: ReactNode }) {
  const file = useFile(path);
  const ref = useRef<HTMLDivElement>(null);
  const baseDir = path.slice(0, path.lastIndexOf("/") + 1);
  const parsed = file.status === "ready" ? parseFrontmatter(file.text) : undefined;
  const split = parsed ? splitReferences(parsed.body) : undefined;
  const hasRefs = !!split && (split.refs.length > 0 || split.notes.length > 0 || extraRefs.length > 0 || Object.keys(parsed!.meta).some((k) => k in META_LABEL));

  useEffect(() => {
    if (file.status !== "ready" || !ref.current) {
      onToc([]);
      return;
    }
    const hs = ref.current.querySelectorAll<HTMLElement>(".doc-main h2[id], .doc-main h3[id]");
    const items: TocItem[] = [...hs].map((h) => ({ id: h.id, text: h.textContent ?? "", level: h.tagName === "H2" ? 2 : 3 }));
    if (hasRefs) items.push({ id: REFERENCES_ID, text: "引用与来源", level: 2 });
    onToc(items);
  }, [file, onToc, hasRefs]);

  if (file.status === "loading") return <Loading />;
  if (file.status === "missing")
    return (
      <>
        {missing ?? <Missing path={path} what={what} />}
        <References extra={extraRefs} />
      </>
    );
  return (
    <div ref={ref} className="pt-8">
      <div className="doc-main">
        <Markdown source={split!.main} baseDir={baseDir} />
      </div>
      <References meta={parsed!.meta} notes={split!.notes} refs={split!.refs} extra={extraRefs} baseDir={baseDir} />
    </div>
  );
}

/* ---------- 上一篇 / 下一篇 ---------- */

type NavLink = { to: string; tag: string; title: string };

export function PrevNext({ prev, next }: { prev?: NavLink; next?: NavLink }) {
  return (
    <div className="mt-12 grid gap-3 border-t border-line pt-8 sm:grid-cols-2">
      {prev ? (
        <Link to={prev.to} className="rounded-xl border border-line p-4 transition hover:border-course/50">
          <div className="flex items-center gap-1 text-xs text-ink-3">
            <Icon name="arrowLeft" className="h-3.5 w-3.5" /> 上一篇
          </div>
          <div className="mt-1 truncate text-[15px] text-ink">
            <span className="mr-2 font-mono text-xs text-course">{prev.tag}</span>
            {prev.title}
          </div>
        </Link>
      ) : (
        <span />
      )}
      {next && (
        <Link to={next.to} className="rounded-xl border border-line p-4 text-right transition hover:border-course/50">
          <div className="flex items-center justify-end gap-1 text-xs text-ink-3">
            下一篇 <Icon name="arrowRight" className="h-3.5 w-3.5" />
          </div>
          <div className="mt-1 truncate text-[15px] text-ink">
            <span className="mr-2 font-mono text-xs text-course">{next.tag}</span>
            {next.title}
          </div>
        </Link>
      )}
    </div>
  );
}

/* ---------- 页面骨架 ---------- */

export function ReaderShell({
  course,
  detail,
  active,
  crumb,
  header,
  rail,
  children,
}: {
  course: CourseSummary;
  detail: CourseDetail;
  active: ActiveItem;
  crumb?: string;
  header: ReactNode;
  rail: ReactNode;
  children: ReactNode;
}) {
  const [drawer, setDrawer] = useState(false);
  const activeKey = active.kind === "home" ? "home" : `${active.kind}/${active.id}`;
  useEffect(() => {
    setDrawer(false);
  }, [activeKey]);

  const crumbs = [{ label: `${course.school} ${course.code}`, to: crumb ? `/c/${course.id}` : undefined }, ...(crumb ? [{ label: crumb }] : [])];

  return (
    <div data-course style={courseStyle(course)} className="min-h-screen">
      <TopBar crumbs={crumbs} onMenu={() => setDrawer(true)} />
      <div className="mx-auto grid max-w-[1440px] grid-cols-1 lg:grid-cols-[16.5rem_minmax(0,1fr)] xl:grid-cols-[16.5rem_minmax(0,1fr)_15rem]">
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] overflow-y-auto border-r border-line px-3 py-6 lg:block">
          <CourseOutline course={course} detail={detail} active={active} />
        </aside>
        <main className="min-w-0 px-4 pb-10 sm:px-6 lg:px-10">
          {header}
          {children}
        </main>
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] overflow-y-auto py-8 pr-6 xl:block">{rail}</aside>
      </div>
      <Footer />

      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="课程目录">
          <button type="button" className="absolute inset-0 bg-black/40" onClick={() => setDrawer(false)} aria-label="关闭" />
          <div className="absolute inset-y-0 left-0 w-[19rem] max-w-[85vw] overflow-y-auto border-r border-line bg-bg px-3 py-5 shadow-2xl">
            <button type="button" onClick={() => setDrawer(false)} className="absolute right-3 top-4 grid h-8 w-8 place-items-center rounded-lg text-ink-3 hover:bg-surface-2" aria-label="关闭目录">
              <Icon name="x" />
            </button>
            <CourseOutline course={course} detail={detail} active={active} onNavigate={() => setDrawer(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
