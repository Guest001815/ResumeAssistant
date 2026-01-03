# Resume Assistant Web 架构说明

## 文档索引
- [API 事件协议](./API_SSE.md)
- [简历数据 Schema](./RESUME_SCHEMA.md)
- [开发与运行](./DEVELOPMENT.md)
- [导出实现](./EXPORT.md)
- [Markdown 编辑与解析](./MARKDOWN.md)

## 项目概览
- 该前端是一个基于 React + Vite 的单页应用（SPA），用于与后端进行对话并实时生成与预览简历 HTML。
- 页面采用双栏布局：左侧聊天、右侧简历预览，通过 `iframe srcDoc` 隔离展示。

## 技术栈与构建
- 依赖：`react`、`react-dom`、`scheduler`（d:\ResumeAssistant\web\package.json:11-15）
- 构建：`vite`、`@vitejs/plugin-react`、`typescript`（d:\ResumeAssistant\web\package.json:16-22）
- TypeScript：严格模式、`jsx: react-jsx`、`module: ESNext`（d:\ResumeAssistant\web\tsconfig.json:2-14）
- 开发端口：`5173`（d:\ResumeAssistant\web\vite.config.ts:6-8），预览端口：`5174`（d:\ResumeAssistant\web\package.json:9）
- 模块别名：`scheduler` 指向开发版 CJS（d:\ResumeAssistant\web\vite.config.ts:10-14）

## 目录结构
- `src/main.tsx`：应用入口（d:\ResumeAssistant\web\src\main.tsx:1-7）
- `src/App.tsx`：页面壳与顶层状态（d:\ResumeAssistant\web\src\App.tsx:8-62）
- `src/components/Chat.tsx`：聊天组件与 SSE 事件处理（d:\ResumeAssistant\web\src\components\Chat.tsx:1-95）
- `src/components/ResumePreview.tsx`：简历预览，`iframe srcDoc`（d:\ResumeAssistant\web\src\components\ResumePreview.tsx:3-7）
- `src/api/sse.ts`：SSE 客户端（d:\ResumeAssistant\web\src\api\sse.ts:1-43）
- `src/utils/renderResume.ts`：简历数据到 HTML 的渲染器（d:\ResumeAssistant\web\src\utils\renderResume.ts:43-153）
- 样式：`src/styles/global.css`（d:\ResumeAssistant\web\src\styles\global.css:1-66）
- 模板：`index.html`（d:\ResumeAssistant\web\index.html:1-12）
- 环境：`.env.development`（d:\ResumeAssistant\web\.env.development:1）

## 应用架构
- 入口与挂载：`createRoot` 挂载 `App`（d:\ResumeAssistant\web\src\main.tsx:2-7）
- 页面壳：双栏网格布局（d:\ResumeAssistant\web\src\App.tsx:45-60；样式 d:\ResumeAssistant\web\src\styles\global.css:5-11）
- 状态层：
  - `messages`（消息历史）（d:\ResumeAssistant\web\src\App.tsx:9-15）
  - `resumeData`（结构化简历数据）（d:\ResumeAssistant\web\src\App.tsx:16）
  - `resumeHtml`（渲染后的 HTML）（d:\ResumeAssistant\web\src\App.tsx:17-19,39-43）
- 持久化：`localStorage.ra_state` 读写（d:\ResumeAssistant\web\src\App.tsx:20-37）
- 视图层：`Chat`、`ResumePreview` 通过 props 与顶层状态交互（d:\ResumeAssistant\web\src\App.tsx:49-58）

## 数据流
- 输入提交：`Chat` 表单 `onSubmit`（d:\ResumeAssistant\web\src\components\Chat.tsx:20-64）
- 建立 SSE：`streamRun(input, resumeData, onEvent, signal)`（d:\ResumeAssistant\web\src\components\Chat.tsx:51-56；d:\ResumeAssistant\web\src\api\sse.ts:10-18）
- 事件处理：`think`/`tool`/`error`/`data`（d:\ResumeAssistant\web\src\components\Chat.tsx:30-44）
- 渲染更新：`resumeData` 变化→`renderResumeHtmlFromSchema` 生成 `resumeHtml`（d:\ResumeAssistant\web\src\App.tsx:39-43；d:\ResumeAssistant\web\src\utils\renderResume.ts:43-153）
- 历史记录：请求完成后将 `toolLines` 合并为助手消息（d:\ResumeAssistant\web\src\components\Chat.tsx:45-49）

## 状态持久化
- 首渲染读取 `localStorage.ra_state` 恢复消息与简历数据（d:\ResumeAssistant\web\src\App.tsx:20-32）
- 每当 `messages` 或 `resumeData` 变化即写回（d:\ResumeAssistant\web\src\App.tsx:34-37）

## 简历渲染
- Schema 输入：`basics` + `sections`（`experience`、`generic`、`text`）（d:\ResumeAssistant\web\src\utils\renderResume.ts:24-33）
- 安全转义：`esc` 防止 XSS（d:\ResumeAssistant\web\src\utils\renderResume.ts:34-41）
- 输出结构：完整 HTML 文档 + 内联样式（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-153）
- 预览方式：`iframe srcDoc` 隔离（d:\ResumeAssistant\web\src\components\ResumePreview.tsx:5-7）

## 样式与布局
- 双栏网格、滚动历史、输入区样式、预览区边框与圆角（d:\ResumeAssistant\web\src\styles\global.css:5-66）

## 错误处理与取消
- SSE 请求错误：`!resp.ok` 抛异常（d:\ResumeAssistant\web\src\api\sse.ts:19）
- 并发取消：`AbortController` 避免多流并发（d:\ResumeAssistant\web\src\components\Chat.tsx:27-33）
- 异常输出：错误信息追加到工具输出区并记录为助手消息（d:\ResumeAssistant\web\src\components\Chat.tsx:58-63）

## 安全性与健壮性
- 全量转义简历输出字段，降低 XSS 风险（d:\ResumeAssistant\web\src\utils\renderResume.ts:34-41）
- 预览通过 `iframe srcDoc` 与主 DOM 隔离，样式与脚本互不影响（d:\ResumeAssistant\web\src\components\ResumePreview.tsx:5-7）
- SSE 行解析忽略无效 JSON，提升容错（d:\ResumeAssistant\web\src\api\sse.ts:35-41）

## 扩展建议
- 路由与多页：引入 `react-router` 扩展模板选择/历史版本
- 模板系统：将内联样式抽象为可切换主题与模板
- 结构化编辑：右侧增加表单编辑器，与对话输出合并
- 错误分级与重试：改善用户反馈与交互体验

## 右栏双模式与导出菜单
- 模式切换：右栏支持 `编辑`/`预览` 两种模式，通过单选按钮切换（d:\ResumeAssistant\web\src\App.tsx:183-204；样式 d:\ResumeAssistant\web\src\styles\global.css:176-203）。
- 预览渲染：`resumeHtml` 传递到 `ResumePreview` 的 `iframe srcDoc`（d:\ResumeAssistant\web\src\components\ResumePreview.tsx:5-9）。
- 编辑模式：`MarkdownPane` 提供 Markdown 文本编辑（d:\ResumeAssistant\web\src\components\MarkdownPane.tsx:10-18）。
- 导出菜单：标题区右上角弹出菜单，支持 `pdf` 与 `html` 导出（d:\ResumeAssistant\web\src\App.tsx:230-252）。
- 导出实现：`exportResume` 调用注册的处理器，首选 `html2pdf.js`，失败时回退 `html2canvas + jspdf`（d:\ResumeAssistant\web\src\utils\export.ts:34-189）。

## 分栏拖拽与可访问性
- 拖拽实现：通过 `pointerdown/move/up` 记录起点与比例，限制左右比例在 `0.3–0.5`，使用 `requestAnimationFrame` 平滑更新（d:\ResumeAssistant\web\src\App.tsx:36-47,49-78）。
- 键盘支持：`splitter` 接受左右箭头按键进行微调（d:\ResumeAssistant\web\src\App.tsx:80-92）。
- 可访问属性：`role="separator"`、`aria-orientation="vertical"`、`aria-valuemin/max/now` 提示当前值与范围（d:\ResumeAssistant\web\src\App.tsx:169-178）。
- 样式提示：悬停与拖拽态的可视指示（d:\ResumeAssistant\web\src\styles\global.css:237-244）。

## 状态持久化与恢复
- 持久化字段：`messages`、`resumeData`、`editorMode`、`markdownText` 写入 `localStorage.ra_state`（d:\ResumeAssistant\web\src\App.tsx:131-134）。
- 首渲染恢复：解析存储对象并恢复对应状态，含 `resumeHtml` 重新渲染（d:\ResumeAssistant\web\src\App.tsx:111-129）。
- 模式联动：当接收到新的 `resumeData`，自动渲染 `resumeHtml`、同步 `markdownText`、右栏切回 `预览`（d:\ResumeAssistant\web\src\App.tsx:136-142）。

## 渲染链路与样式约束
- Schema→HTML：`renderResumeHtmlFromSchema` 生成完整 HTML 文档，包含内联样式块与 `.resume-container` 根容器（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-158）。
- 导出宽度：`.resume-container` 使用 `794px` 固定宽度，便于 A4 导出与分页控制（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-139）。
- 安全转义：所有字段经 `esc` 转义后输出，防止恶意注入（d:\ResumeAssistant\web\src\utils\renderResume.ts:34-41）。

## 依赖与配置
- 导出依赖：`html2pdf.js`、`html2canvas`、`jspdf`（d:\ResumeAssistant\web\package.json:11-18）。
- 运行端口：开发 `5173`、预览 `5174`（d:\ResumeAssistant\web\vite.config.ts:6-8；d:\ResumeAssistant\web\package.json:9）。
- 模块别名：`scheduler` 指向开发版 CJS（d:\ResumeAssistant\web\vite.config.ts:10-14）。
- 后端地址：`VITE_API_BASE` 默认 `http://localhost:8000`（d:\ResumeAssistant\web\.env.development:1；d:\ResumeAssistant\web\src\api\sse.ts:1-3）。
