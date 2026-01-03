# 开发与运行

## 命令与端口
- 开发：`npm run dev`（默认端口 `5173`，d:\ResumeAssistant\web\vite.config.ts:6-8）
- 构建：`npm run build`
- 预览：`npm run preview`（端口 `5174`，d:\ResumeAssistant\web\package.json:9）

## 依赖与工具
- 运行时依赖：`react`、`react-dom`、`scheduler`、`html2pdf.js`、`html2canvas`、`jspdf`（d:\ResumeAssistant\web\package.json:11-18）
- 开发依赖：`vite`、`@vitejs/plugin-react`、`typescript`（d:\ResumeAssistant\web\package.json:19-25）
- 模块别名：`scheduler` 指向开发版 CJS（d:\ResumeAssistant\web\vite.config.ts:10-14）
- 依赖用途：
  - `html2pdf.js`：首选 PDF 导出方案（d:\ResumeAssistant\web\src\utils\export.ts:80-99）。
  - `html2canvas` + `jspdf`：作为导出回退方案（d:\ResumeAssistant\web\src\utils\export.ts:158-185）。

## TypeScript 配置要点
- 严格模式开启：`strict: true`
- JSX 转换：`jsx: react-jsx`
- 模块与解析：`module: ESNext`、`moduleResolution: Bundler`、`noEmit: true`
- `lib`：`ES2020`、`DOM`、`DOM.Iterable`（d:\ResumeAssistant\web\tsconfig.json:2-14）

## 项目结构与入口
- HTML 模板：`index.html`（d:\ResumeAssistant\web\index.html:1-12）
- 应用入口：`src/main.tsx`（d:\ResumeAssistant\web\src\main.tsx:1-7）
- 页面壳：`src/App.tsx`（d:\ResumeAssistant\web\src\App.tsx:8-62）
- 样式：`src/styles/global.css`（d:\ResumeAssistant\web\src\styles\global.css:1-66）

## 环境变量
- 开发环境文件：`.env.development`（d:\ResumeAssistant\web\.env.development:1）
- `VITE_API_BASE`：后端基地址，默认 `http://localhost:8000`

## 注意事项
- 简历渲染器采用内联样式，外部全局样式用于布局与容器；导出依赖 `.resume-container` 固定宽度（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-139）。
- SSE 请求跨域需在后端配置 CORS 并允许 `text/event-stream`。
- 本地存储：持久化 `messages`、`resumeData`、`editorMode`、`markdownText` 到 `localStorage.ra_state`（d:\ResumeAssistant\web\src\App.tsx:131-134）。
