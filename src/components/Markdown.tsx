import { isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeSlug from "rehype-slug";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import "katex/dist/katex.min.css";
import { resolveAsset } from "../lib/content";
import { Mermaid } from "./Mermaid";
import { CopyButton } from "./bits";

function textOf(node: ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children);
  return "";
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const child = Array.isArray(children) ? children[0] : children;
  const className = isValidElement<{ className?: string }>(child) ? child.props.className ?? "" : "";
  const lang = /language-([\w+-]+)/.exec(className)?.[1];
  const code = textOf(children).replace(/\n$/, "");

  if (lang === "mermaid") return <Mermaid code={code} />;

  return (
    <div className="not-prose group relative my-5 overflow-hidden rounded-xl border border-line bg-[rgb(var(--code-bg))]">
      <div className="flex items-center justify-between border-b border-line/70 px-3 py-1">
        <span className="font-mono text-[11px] uppercase tracking-wider text-ink-3">{lang ?? "text"}</span>
        <CopyButton text={code} className="opacity-70 group-hover:opacity-100" />
      </div>
      <pre className="overflow-x-auto px-4 py-3 font-mono text-[13px] leading-[1.7] text-ink">{children}</pre>
    </div>
  );
}

export function Markdown({ source, baseDir = "/", className = "" }: { source: string; baseDir?: string; className?: string }) {
  const components: Components = {
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    img: ({ node: _node, src, alt, ...rest }) => (
      <img {...rest} src={resolveAsset(baseDir, src)} alt={alt ?? ""} loading="lazy" decoding="async" />
    ),
    a: ({ node: _node, href, children, ...rest }) => {
      if (href?.startsWith("#") && !href.startsWith("#/")) {
        // HashRouter 下 "#xxx" 会被当成路由，改为页内滚动
        const id = decodeURIComponent(href.slice(1));
        return (
          <a
            href={href}
            {...rest}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            {children}
          </a>
        );
      }
      const external = !!href && /^https?:/.test(href);
      return (
        <a href={href} {...rest} {...(external ? { target: "_blank", rel: "noreferrer" } : {})}>
          {children}
        </a>
      );
    },
    table: ({ children }) => (
      <div className="not-prose my-6 overflow-x-auto rounded-xl border border-line">
        <table className="reading-table w-full border-collapse text-left text-[14.5px] leading-relaxed">{children}</table>
      </div>
    ),
  };

  return (
    <div className={`reading prose ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          rehypeRaw,
          rehypeSlug,
          rehypeKatex,
          [rehypeHighlight, { detect: false, plainText: ["mermaid", "text", "txt"] }],
        ]}
        components={components}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
