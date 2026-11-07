import { useEffect, useId, useState } from "react";
import { useDark } from "../lib/theme";

type MermaidApi = typeof import("mermaid").default;
let mermaidPromise: Promise<MermaidApi> | null = null;
const loadMermaid = () => (mermaidPromise ??= import("mermaid").then((m) => m.default));

export function Mermaid({ code }: { code: string }) {
  const dark = useDark();
  const id = "m" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let cancelled = false;
    loadMermaid()
      .then(async (m) => {
        m.initialize({
          startOnLoad: false,
          theme: dark ? "dark" : "neutral",
          securityLevel: "loose",
          fontFamily: '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
        });
        const out = await m.render(`${id}-${dark ? "d" : "l"}`, code);
        if (!cancelled) setSvg(out.svg);
      })
      .catch((e: unknown) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [code, dark, id]);

  if (error)
    return (
      <pre className="overflow-x-auto rounded-xl border border-line p-4 text-xs text-ink-3">
        Mermaid 渲染失败{"\n"}
        {code}
      </pre>
    );
  return (
    <figure className="not-prose my-6 overflow-x-auto rounded-xl border border-line bg-surface p-4">
      {svg ? (
        <div className="flex justify-center [&_svg]:h-auto [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <div className="h-40 animate-pulse rounded-lg bg-surface-2" />
      )}
    </figure>
  );
}
