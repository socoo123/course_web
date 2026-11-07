import catalogJson from "../../content/catalog.json";
import type {
  Catalog,
  CourseDetail,
  CourseSummary,
  Lab,
  LabMaterial,
  Lecture,
  LectureMaterial,
  Week,
} from "./types";
import { COURSE_RESOURCES_FILE, LAB_MATERIALS, LECTURE_MATERIALS } from "./types";

/*
 * 内容全部在构建期由 Vite 收集：
 *   content/catalog.json                 课程目录
 *   content/<course>/course.json         课程详情（课表 / 讲座 / Lab）
 *   content/<course>/lectures/<id>/*.md  讲座材料
 *   content/<course>/labs/<id>/*.md      Lab 材料
 *   .../assets/*                         图片（md 里用相对路径引用）
 * 新增文件即生效，无需改代码。
 */

const catalog = catalogJson as Catalog;

const details = import.meta.glob<CourseDetail>("/content/*/course.json", {
  eager: true,
  import: "default",
});

const markdown = import.meta.glob<string>("/content/**/*.md", {
  query: "?raw",
  import: "default",
});

const assets = import.meta.glob<string>("/content/**/*.{png,jpg,jpeg,gif,svg,webp,avif}", {
  query: "?url",
  import: "default",
  eager: true,
});

export interface CourseBundle {
  summary: CourseSummary;
  detail?: CourseDetail;
}

export function getCatalog(): Catalog {
  return catalog;
}

export function getCourse(id: string): CourseBundle | undefined {
  const summary = catalog.courses.find((c) => c.id === id);
  if (!summary) return undefined;
  return { summary, detail: details[`/content/${id}/course.json`] };
}

export const lectureDir = (courseId: string, lecId: string) => `/content/${courseId}/lectures/${lecId}/`;
export const labDir = (courseId: string, labId: string) => `/content/${courseId}/labs/${labId}/`;

export function hasFile(path: string): boolean {
  return path in markdown;
}

export function loadFile(path: string): Promise<string> {
  const loader = markdown[path];
  return loader ? loader() : Promise.reject(new Error(`missing ${path}`));
}

export const courseResourcesPath = (courseId: string) => `/content/${courseId}/${COURSE_RESOURCES_FILE}`;

export function lectureMaterials(courseId: string, lecId: string): Record<LectureMaterial, boolean> {
  const dir = lectureDir(courseId, lecId);
  const out = {} as Record<LectureMaterial, boolean>;
  for (const k of Object.keys(LECTURE_MATERIALS) as LectureMaterial[]) out[k] = hasFile(dir + LECTURE_MATERIALS[k].file);
  return out;
}

export function labMaterials(courseId: string, labId: string): Record<LabMaterial, boolean> {
  const dir = labDir(courseId, labId);
  const out = {} as Record<LabMaterial, boolean>;
  for (const k of Object.keys(LAB_MATERIALS) as LabMaterial[]) out[k] = hasFile(dir + LAB_MATERIALS[k].file);
  return out;
}

/** 把 md 里的相对图片路径解析成打包后的 URL */
export function resolveAsset(baseDir: string, src: string | undefined): string | undefined {
  if (!src || /^(https?:|data:|\/\/)/.test(src)) return src;
  const parts = (baseDir + src).split("/");
  const out: string[] = [];
  for (const p of parts) {
    if (p === "..") out.pop();
    else if (p !== "." && p !== "") out.push(p);
  }
  return assets["/" + out.join("/")] ?? src;
}

export function findLecture(detail: CourseDetail | undefined, id: string): Lecture | undefined {
  return detail?.lectures.find((l) => l.id === id);
}

export function findLab(detail: CourseDetail | undefined, id: string): Lab | undefined {
  return detail?.labs.find((l) => l.id === id);
}

export function weekOfLecture(detail: CourseDetail | undefined, lecId: string): Week | undefined {
  return detail?.weeks?.find((w) => w.lectures.includes(lecId));
}

/** 引用了某个 Lab 的讲座 */
export function lecturesOfLab(detail: CourseDetail | undefined, labId: string): Lecture[] {
  return detail?.lectures.filter((l) => l.lab === labId) ?? [];
}
