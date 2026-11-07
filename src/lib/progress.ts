import { useSyncExternalStore } from "react";

/** 学习进度只存在浏览器 localStorage，静态站无需后端 */

export interface LastVisit {
  kind: "lecture" | "lab";
  id: string;
  at: number;
}

interface CourseProgress {
  lectures: Record<string, true>;
  tasks: Record<string, true>; // key: `${labId}/${taskId}`
  last?: LastVisit;
}

interface ProgressState {
  courses: Record<string, CourseProgress>;
  lastCourse?: string;
}

const KEY = "cw:progress:v1";
const EVENT = "cw:progress";
const EMPTY: CourseProgress = { lectures: {}, tasks: {} };

let cache: ProgressState | null = null;

function read(): ProgressState {
  if (cache) return cache;
  try {
    cache = JSON.parse(localStorage.getItem(KEY) || "") as ProgressState;
  } catch {
    cache = { courses: {} };
  }
  if (!cache?.courses) cache = { courses: {} };
  return cache;
}

function write(next: ProgressState) {
  cache = next;
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(EVENT));
}

function update(courseId: string, fn: (c: CourseProgress) => CourseProgress, touchCourse = false) {
  const s = read();
  const cur = s.courses[courseId] ?? EMPTY;
  write({
    ...s,
    lastCourse: touchCourse ? courseId : s.lastCourse,
    courses: { ...s.courses, [courseId]: fn({ ...cur, lectures: { ...cur.lectures }, tasks: { ...cur.tasks } }) },
  });
}

function subscribe(cb: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY) {
      cache = null;
      cb();
    }
  };
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", onStorage);
  };
}

export function useProgress(): ProgressState {
  return useSyncExternalStore(subscribe, read, read);
}

export function useCourseProgress(courseId: string): CourseProgress {
  return useProgress().courses[courseId] ?? EMPTY;
}

export function toggleLecture(courseId: string, lecId: string) {
  update(courseId, (c) => {
    if (c.lectures[lecId]) delete c.lectures[lecId];
    else c.lectures[lecId] = true;
    return c;
  });
}

export function toggleTask(courseId: string, labId: string, taskId: string) {
  const k = `${labId}/${taskId}`;
  update(courseId, (c) => {
    if (c.tasks[k]) delete c.tasks[k];
    else c.tasks[k] = true;
    return c;
  });
}

export function recordVisit(courseId: string, kind: LastVisit["kind"], id: string) {
  const prev = read().courses[courseId]?.last;
  if (prev && prev.kind === kind && prev.id === id && read().lastCourse === courseId) return;
  update(courseId, (c) => ({ ...c, last: { kind, id, at: Date.now() } }), true);
}
