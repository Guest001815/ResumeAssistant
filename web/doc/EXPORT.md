# 导出实现（PDF/HTML）

## 概览
- 导出入口：右栏标题区的导出菜单，支持 `pdf` 与 `html`（d:\ResumeAssistant\web\src\App.tsx:230-252）。
- API：`exportResume(format, payload)` 分发到对应处理器（d:\ResumeAssistant\web\src\utils\export.ts:191-199）。
- 目标元素：优先使用 `.resume-container`，保证版心宽度与分页可控（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-139）。

## PDF 导出路径
- 首选路径：`html2pdf.js`
  - 加载模块并从目标元素生成与保存 PDF（d:\ResumeAssistant\web\src\utils\export.ts:80-99）。
  - 关键参数：`margin`、`image.quality`、`html2canvas.scale`、`jsPDF.format=a4`、`pagebreak.avoid=[".section",".item"]`（d:\ResumeAssistant\web\src\utils\export.ts:82-96）。
- 回退路径：`html2canvas + jspdf`
  - 使用 `html2canvas` 渲染目标元素为画布，再通过 `jspdf` 添加图片与分页（d:\ResumeAssistant\web\src\utils\export.ts:158-185）。
  - 计算分页：以 A4 高度逐页添加相同位图，避免内容被截断（d:\ResumeAssistant\web\src\utils\export.ts:169-183）。

## 资源与字体就绪
- 字体：优先等待 `document.fonts.ready`（或 `iframe` 中的 `fonts.ready`）（d:\ResumeAssistant\web\src\utils\export.ts:58-66,136-144）。
- 图片：遍历 `<img>` 等待 `onload/onerror`，确保导出时资源完整（d:\ResumeAssistant\web\src\utils\export.ts:68-79,146-156）。
- 宽度：固定导出宽度 `794px`，保证像素到毫米转换稳定（d:\ResumeAssistant\web\src\utils\export.ts:82-93,159-166）。

## HTML 导出
- 方式：获取 `iframe` 中完整文档或直接使用 `resumeHtml`，打包为 `Blob` 并触发下载（d:\ResumeAssistant\web\src\utils\export.ts:12-32）。
- 文件名：`resume.html`。

## 使用指引
- 打开右栏预览，点击导出按钮，选择 `pdf` 或 `html`。
- 如果页面包含网络图片，建议稍候至图片加载完成以提升导出质量。
- 不同浏览器的 `devicePixelRatio` 会影响清晰度，可通过 `html2canvas.scale` 自适应（d:\ResumeAssistant\web\src\utils\export.ts:88,161）。

## 依赖与版本
- `html2pdf.js`、`html2canvas`、`jspdf`（d:\ResumeAssistant\web\package.json:11-18）。

