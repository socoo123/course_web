import { Link } from "react-router-dom";
import { Icon } from "./Icon";
import { toggleTheme, useDark } from "../lib/theme";

export interface Crumb {
  label: string;
  to?: string;
}

export function Logo() {
  return (
    <Link to="/" className="group flex items-center gap-2.5" aria-label="自修大学 首页">
      <span className="grid h-7 w-7 place-items-center rounded-[7px] bg-ink text-bg">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 7l5 5-5 5" stroke="currentColor" />
          <path d="M13 17h6" stroke="rgb(var(--course))" />
        </svg>
      </span>
      <span className="font-serif text-[17px] font-semibold tracking-wide text-ink">自修大学</span>
    </Link>
  );
}

export function ThemeToggle() {
  const dark = useDark();
  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="grid h-8 w-8 place-items-center rounded-lg text-ink-2 transition hover:bg-surface-2 hover:text-ink"
      aria-label={dark ? "切换到浅色" : "切换到深色"}
      title={dark ? "切换到浅色" : "切换到深色"}
    >
      <Icon name={dark ? "sun" : "moon"} />
    </button>
  );
}

export function TopBar({ crumbs = [], onMenu }: { crumbs?: Crumb[]; onMenu?: () => void }) {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:px-6">
        {onMenu && (
          <button
            type="button"
            onClick={onMenu}
            className="-ml-1 grid h-8 w-8 place-items-center rounded-lg text-ink-2 hover:bg-surface-2 lg:hidden"
            aria-label="打开课程目录"
          >
            <Icon name="menu" />
          </button>
        )}
        <Logo />
        {crumbs.length > 0 && (
          <nav aria-label="位置" className="hidden min-w-0 items-center gap-1.5 text-sm text-ink-3 sm:flex">
            {crumbs.map((c, i) => (
              <span key={i} className="flex min-w-0 items-center gap-1.5">
                <Icon name="chevronRight" className="h-3.5 w-3.5 shrink-0 opacity-60" />
                {c.to ? (
                  <Link to={c.to} className="truncate hover:text-ink">
                    {c.label}
                  </Link>
                ) : (
                  <span className="truncate text-ink-2">{c.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <div className="ml-auto flex items-center gap-1">
          <Link to="/" className="hidden rounded-lg px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2 hover:text-ink sm:block">
            课程目录
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-2 px-4 py-8 text-xs leading-relaxed text-ink-3 sm:flex-row sm:justify-between sm:px-6">
        <p>课程材料版权归原课程所有，按原许可署名；中文译稿与笔记为个人学习整理，非官方译本。</p>
        <p className="font-mono">static · GitHub Pages</p>
      </div>
    </footer>
  );
}
