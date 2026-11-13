export type CourseStatus = "active" | "planned" | "done";

export interface CourseSummary {
  id: string;
  school: string;
  code: string;
  altCode?: string;
  title: string;
  titleEn: string;
  status: CourseStatus;
  accent: { light: string; dark: string };
  tags: string[];
  blurb: string;
  counts?: { lectures: number; labs: number };
  effort?: string;
}

export interface Track {
  id: string;
  name: string;
  nameEn: string;
  desc: string;
  courses: string[];
}

export interface Catalog {
  tracks: Track[];
  courses: CourseSummary[];
}

export interface Lecture {
  id: string;
  num: string;
  title: string;
  titleEn: string;
  video?: {
    label: string;
    youtube?: string;
    bilibili?: string;
    duration?: string;
    language?: "zh" | "en";
    /** 按讲启用站内播放器，优先YouTube；不自动扩展到整门课。 */
    embed?: boolean;
    /** 实际核对过的画面定位点，不是完整讲稿或章节起止。 */
    checkpoints?: { time: string; title: string; summary: string }[];
  };
  readings?: string[];
  lab?: string;
  note?: string;
  core?: boolean;
  isNew?: boolean;
  optional?: boolean;
}

export interface LabTask {
  id: string;
  title: string;
  titleEn?: string;
  grade?: string;
}

export interface Lab {
  id: string;
  num: number;
  title: string;
  titleEn: string;
  stars: number;
  hours: string;
  branch: string;
  url: string;
  goal: string;
  tasks: LabTask[];
}

export interface WeekEvent {
  type: "assign" | "due" | "exam" | "note";
  lab?: string;
  label?: string;
  date?: string;
}

export interface Week {
  n: number;
  date: string;
  lectures: string[];
  events: WeekEvent[];
}

export interface Resource {
  group: string;
  label: string;
  url?: string;
  desc?: string;
}

export interface CourseDetail {
  id: string;
  /** 课表所在年份，用于推算“本周” */
  year?: number;
  instructors: string[];
  versions: { label: string; value: string }[];
  intro: string;
  links?: { label: string; url: string }[];
  workflow?: string[];
  lectures: Lecture[];
  labs: Lab[];
  weeks?: Week[];
  resources?: Resource[];
}

/** 每类条目对应的材料文件。文件存在 = 材料已就绪 */
export const LECTURE_MATERIALS = {
  notes: { file: "notes.zh.md", label: "课程笔记" },
  draft: { file: "draft.zh.md", label: "中文译稿" },
  materials: { file: "materials.zh.md", label: "课程资料" },
} as const;

export const LAB_MATERIALS = {
  zh: { file: "lab.zh.md", label: "实验说明" },
  guide: { file: "guide.zh.md", label: "实验指导" },
  en: { file: "lab.en.md", label: "英文原文" },
} as const;

/** 课程级公共资料章 */
export const COURSE_RESOURCES_FILE = "resources.zh.md";

export type LectureMaterial = keyof typeof LECTURE_MATERIALS;
export type LabMaterial = keyof typeof LAB_MATERIALS;
