import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 后端地址：开发时 vite 把 /api 和 /ws 代理过去，页面里只写相对路径。
// 后端在别的机器上就 VITE_BACKEND=http://192.168.1.8:8766 npm run dev
const backend = process.env.VITE_BACKEND || "http://127.0.0.1:8766";

export default defineConfig({
  base: "/h5/",                       // 构建产物由后端挂在 /h5 下
  build: {
    outDir: "../static/h5",            // 直接产出到后端静态目录，python run_local.py 即可访问
    emptyOutDir: true,
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  server: {
    host: "0.0.0.0",
    proxy: {
      "/api": backend,
      "/ws": { target: backend, ws: true },
    },
    warmup: {
      clientFiles: ["./src/main.jsx"],
    },
  },
  plugins: [react()],
});
