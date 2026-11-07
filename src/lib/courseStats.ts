import type { CourseDetail, Lecture } from "./types";

interface Progress {
  lectures: Record<string, true>;
  tasks: Record<string, true>;
}

/** 讲座阅读顺序：有课表按课表排，否则按 course.json 里的顺序 */
export function orderedLectures(detail: CourseDetail): Lecture[] {
  if (!detail.weeks?.length) return detail.lectures;
  const byId = new Map(detail.lectures.map((l) => [l.id, l]));
  const out: Lecture[] = [];
  for (const w of detail.weeks) for (const id of w.lectures) if (byId.has(id)) out.push(byId.get(id)!), byId.delete(id);
  return [...out, ...byId.values()];
}

export function courseStats(detail: CourseDetail | undefined, p: Progress) {
  if (!detail) return { lecDone: 0, lecTotal: 0, taskDone: 0, taskTotal: 0 };
  const required = detail.lectures.filter((l) => !l.optional);
  const tasks = detail.labs.flatMap((lab) => lab.tasks.map((t) => `${lab.id}/${t.id}`));
  return {
    lecDone: required.filter((l) => p.lectures[l.id]).length,
    lecTotal: required.length,
    taskDone: tasks.filter((k) => p.tasks[k]).length,
    taskTotal: tasks.length,
  };
}

export function nextLecture(detail: CourseDetail | undefined, p: Progress): Lecture | undefined {
  if (!detail) return undefined;
  return orderedLectures(detail).find((l) => !l.optional && !p.lectures[l.id]);
}
