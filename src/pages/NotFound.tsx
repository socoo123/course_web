import { Link } from "react-router-dom";
import { TopBar } from "../components/TopBar";

export default function NotFound() {
  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-md px-6 py-32 text-center">
        <div className="font-mono text-5xl font-semibold text-ink-3">404</div>
        <p className="mt-4 text-ink-2">这一页不存在，可能课程或讲次 ID 写错了。</p>
        <Link to="/" className="btn-primary mt-8">
          回到课程目录
        </Link>
      </main>
    </div>
  );
}
