import { useState } from "react";
import type { Lecture } from "../lib/types";
import { Icon } from "./Icon";

export function LectureVideo({ video, title }: { video: NonNullable<Lecture["video"]>; title: string }) {
  const [loaded, setLoaded] = useState(false);
  const youtube = video.youtube ? new URL(video.youtube) : undefined;
  const youtubeId = youtube?.hostname === "youtu.be" ? youtube.pathname.slice(1) : youtube?.searchParams.get("v");
  const bvid = video.bilibili?.match(/\/video\/(BV[0-9A-Za-z]+)/)?.[1];
  const page = video.bilibili ? new URL(video.bilibili).searchParams.get("p") ?? "1" : "1";
  const provider = youtubeId ? "YouTube" : "B站";
  const originalUrl = youtubeId ? video.youtube : video.bilibili;
  const embedUrl = youtubeId
    ? `https://www.youtube-nocookie.com/embed/${encodeURIComponent(youtubeId)}?autoplay=0&playsinline=1&rel=0`
    : bvid
      ? `https://player.bilibili.com/player.html?${new URLSearchParams({ bvid, page, autoplay: "0", danmaku: "0" })}`
      : undefined;

  return (
    <div className="pt-8">
      <section id="watch-video" aria-labelledby="watch-video-title" className="scroll-mt-32">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="watch-video-title" className="font-serif text-xl font-semibold text-ink">课程视频</h2>
          <span className="text-sm text-ink-3">先看课，再用笔记复习</span>
        </div>
        <div className="overflow-hidden rounded-2xl border border-line bg-surface">
          {loaded && embedUrl ? (
            <iframe
              src={embedUrl}
              title={`${title} · ${provider}课程视频`}
              className="block aspect-video min-h-[200px] w-full border-0"
              allow="fullscreen; picture-in-picture; encrypted-media"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
              sandbox="allow-scripts allow-same-origin allow-presentation allow-popups allow-popups-to-escape-sandbox"
            />
          ) : (
            <div className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center sm:aspect-video">
              <Icon name="play" className="mb-4 h-8 w-8 text-course" />
              <p className="font-serif text-xl font-semibold text-ink">{title}</p>
              <p className="mt-2 text-sm text-ink-3">{video.label}{video.duration ? ` · ${video.duration}` : ""}</p>
              {embedUrl && (
                <button type="button" onClick={() => setLoaded(true)} className="btn mt-5">
                  加载{provider}播放器
                </button>
              )}
              <p className="mt-3 max-w-sm text-xs leading-6 text-ink-3">点击后连接{provider}；不自动播放，不把观看结束当作学会。</p>
            </div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-xs leading-6 text-ink-3">
            <span>播放受网络或平台限制时，可打开原站{youtubeId && video.bilibili ? "或B站备用入口" : ""}。</span>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              <a href={originalUrl} target="_blank" rel="noreferrer" className="font-medium text-course underline underline-offset-4">在{provider}打开</a>
              {youtubeId && video.bilibili && (
                <a href={video.bilibili} target="_blank" rel="noreferrer" className="font-medium text-course underline underline-offset-4">B站备用</a>
              )}
            </div>
          </div>
        </div>
      </section>

      {!!video.checkpoints?.length && (
        <section id="watch-guide" aria-labelledby="watch-guide-title" className="mt-10 max-w-prose scroll-mt-32">
          <h2 id="watch-guide-title" className="font-serif text-xl font-semibold text-ink">课堂导览</h2>
          <p className="mt-2 text-sm leading-7 text-ink-3">时间是已核对的画面定位点，不代表章节起止；这是简要导览，不是完整讲稿。</p>
          <ol className="mt-5 divide-y divide-line rounded-2xl border border-line bg-surface px-5">
            {video.checkpoints.map((point) => (
              <li key={point.time} className="py-5">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-mono text-sm font-semibold text-course">{point.time}</span>
                  <h3 className="font-semibold leading-7 text-ink">{point.title}</h3>
                </div>
                <p className="mt-2 text-sm leading-7 text-ink-2">{point.summary}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
