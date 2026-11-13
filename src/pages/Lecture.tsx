import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Icon } from "../components/Icon";
import { LectureBadges } from "../components/bits";
import { DocView, MaterialTabs, PrevNext, ReaderShell, Toc, useView, type MaterialTab, type RefExtra, type TocItem } from "../components/Reader";
import { findLab, getCourse, lectureDir, lectureMaterials, weekOfLecture } from "../lib/content";
import { orderedLectures } from "../lib/courseStats";
import { recordVisit, toggleLecture, useCourseProgress } from "../lib/progress";
import { LECTURE_MATERIALS, type Lecture as Lec, type LectureMaterial } from "../lib/types";
import NotFound from "./NotFound";

const tag = (l: Lec) => (/^\d+$/.test(l.num) ? `LEC ${l.num}` : l.num);

export default function Lecture() {
  const { courseId = "", lecId = "" } = useParams();
  const bundle = getCourse(courseId);
  const detail = bundle?.detail;
  const lec = detail?.lectures.find((l) => l.id === lecId);
  const p = useCourseProgress(courseId);
  const [toc, setToc] = useState<TocItem[]>([]);
  const onToc = useCallback((t: TocItem[]) => setToc(t), []);

  useEffect(() => {
    if (lec) recordVisit(courseId, "lecture", lec.id);
  }, [courseId, lec]);

  const m = lectureMaterials(courseId, lecId);
  const draftLabel = lec?.video?.language === "zh" ? "课堂整理" : LECTURE_MATERIALS.draft.label;
  const tabs: MaterialTab[] = [
    { id: "notes", label: LECTURE_MATERIALS.notes.label, icon: "pen", ready: m.notes },
    { id: "draft", label: draftLabel, icon: "lang", ready: m.draft },
    { id: "materials", label: LECTURE_MATERIALS.materials.label, icon: "book", ready: m.materials },
  ];
  const [view, setView] = useView(tabs);

  if (!bundle || !detail || !lec) return <NotFound />;
  const course = bundle.summary;
  const dir = lectureDir(courseId, lecId);
  const week = weekOfLecture(detail, lec.id);
  const lab = lec.lab ? findLab(detail, lec.lab) : undefined;
  const done = !!p.lectures[lec.id];
  const videoUrl = lec.video?.youtube ?? lec.video?.bilibili;

  const list = orderedLectures(detail);
  const i = list.findIndex((l) => l.id === lec.id);
  const link = (l?: Lec) => l && { to: `/c/${courseId}/lec/${l.id}`, tag: tag(l), title: l.title };

  const extraRefs: RefExtra[] = [];
  if (lec.video)
    extraRefs.push({
      label: "视频",
      content: videoUrl ? (
        <a href={videoUrl} target="_blank" rel="noreferrer" className="underline decoration-line-strong underline-offset-2 hover:text-course">
          {lec.video.label}
          {lec.video.duration ? ` · ${lec.video.duration}` : ""}
        </a>
      ) : (
        lec.video.label
      ),
    });
  if (lec.readings?.length) extraRefs.push({ label: "指定阅读", content: lec.readings.join("；") });
  if (lec.note) extraRefs.push({ label: "备注", content: lec.note });

  const header = (
    <header className="pb-6 pt-8 lg:pt-10">
      <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-ink-3">
        <span className="font-semibold text-course">{tag(lec)}</span>
        {week && (
          <>
            <span>·</span>
            <span>第 {week.n} 周</span>
          </>
        )}
        <LectureBadges lec={lec} />
      </div>
      <h1 className="mt-3 font-serif text-[30px] font-bold leading-tight text-ink sm:text-[34px]">{lec.title}</h1>
      <p className="mt-1 text-[15px] text-ink-3">{lec.titleEn}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {videoUrl && (
          <a href={videoUrl} target="_blank" rel="noreferrer" className="btn">
            <Icon name="play" className="h-3.5 w-3.5 text-course" />
            {lec.video?.youtube ? "在YouTube打开" : "在B站打开"}
            {lec.video?.duration && <span className="font-mono text-xs text-ink-3">{lec.video.duration}</span>}
          </a>
        )}
        {lab && (
          <Link to={`/c/${courseId}/lab/${lab.id}`} className="btn">
            <Icon name="flask" className="h-3.5 w-3.5 text-course" />
            对应实验 · Lab {lab.num} {lab.branch}
          </Link>
        )}
      </div>
    </header>
  );

  const markButton = (
    <button
      type="button"
      onClick={() => toggleLecture(courseId, lec.id)}
      aria-pressed={done}
      className={
        "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] transition " +
        (done ? "bg-course/10 font-medium text-course" : "border border-line text-ink-2 hover:border-course/50 hover:text-ink")
      }
    >
      <Icon name="check" className="h-3.5 w-3.5" strokeWidth={2.4} />
      <span className="hidden sm:inline">{done ? "已学完" : "标记已学"}</span>
    </button>
  );

  const current = view as LectureMaterial;

  return (
    <ReaderShell course={course} detail={detail} active={{ kind: "lecture", id: lec.id }} crumb={tag(lec)} header={header} rail={<Toc items={toc} />}>
      <MaterialTabs tabs={tabs} view={view} onChange={setView} right={markButton} />
      <div className="max-w-prose">
        <DocView
          key={view}
          path={dir + LECTURE_MATERIALS[current].file}
          what={current === "draft" ? draftLabel : LECTURE_MATERIALS[current].label}
          onToc={onToc}
          extraRefs={extraRefs}
          missing={current === "draft" && lec.video?.language === "zh" ? (
            <section className="mt-8 rounded-2xl border border-line bg-surface p-6">
              <h2 className="font-serif text-xl font-semibold text-ink">完整课堂整理尚未就绪</h2>
              <p className="mt-3 text-sm leading-7 text-ink-2">
                这里应按讲授顺序整理解释、演示和问答，而不是重复教材笔记。当前可通过页头的原站链接观看课程。
              </p>
            </section>
          ) : undefined}
        />
      </div>
      <PrevNext prev={link(list[i - 1])} next={link(list[i + 1])} />
    </ReaderShell>
  );
}
