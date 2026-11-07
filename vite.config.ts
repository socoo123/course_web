import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" + HashRouter: 部署到 GitHub Pages 的任意仓库子路径都能直接用，刷新不 404
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5310, strictPort: true },
  build: {
    chunkSizeWarningLimit: 1500,
  },
});
