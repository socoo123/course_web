import { StrictMode, Suspense, lazy, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Route, Routes, useLocation } from "react-router-dom";
import "./styles/index.css";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";

// 课程 / 讲座 / 实验页带 Markdown、KaTeX、高亮，单独分包，首页不加载
const Course = lazy(() => import("./pages/Course"));
const Lecture = lazy(() => import("./pages/Lecture"));
const Lab = lazy(() => import("./pages/Lab"));

function App() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/c/:courseId" element={<Course />} />
        <Route path="/c/:courseId/lec/:lecId" element={<Lecture />} />
        <Route path="/c/:courseId/lab/:labId" element={<Lab />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
