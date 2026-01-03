# Markdown 编辑与解析

## 概览
- 右栏支持 `编辑`/`预览` 两种模式，切换后持久化到 `localStorage.ra_state`（d:\ResumeAssistant\web\src\App.tsx:144-151,131-134）。
- 编辑组件：`MarkdownPane`，提供纯文本编辑框（d:\ResumeAssistant\web\src\components\MarkdownPane.tsx:10-18）。
- 解析器：`markdownToHtml(md)` 生成完整 HTML 文档（d:\ResumeAssistant\web\src\utils\markdown.ts:1-120）。
- 互转：`resumeToMarkdown(resume)` 从结构化数据生成 Markdown（d:\ResumeAssistant\web\src\utils\markdown.ts:138-193）。

## 解析器支持语法
- 标题：`#`–`######`（d:\ResumeAssistant\web\src\utils\markdown.ts:42-47）。
- 无序列表：`-`/`*` 项；有序列表：`1.` `2.`（d:\ResumeAssistant\web\src\utils\markdown.ts:49-67）。
- 引用：`>` 开头（d:\ResumeAssistant\web\src\utils\markdown.ts:69-73）。
- 代码块：以三反引号包裹；内联代码：单反引号（d:\ResumeAssistant\web\src\utils\markdown.ts:22-31,134）。
- 强调：`**加粗**`、`*斜体*`（d:\ResumeAssistant\web\src\utils\markdown.ts:132-133）。
- 链接与图片：`[text](url)`、`![alt](url)`（d:\ResumeAssistant\web\src\utils\markdown.ts:130-131）。
- 分割线：`---`、`***`、`___`（d:\ResumeAssistant\web\src\utils\markdown.ts:37-41）。

## 安全与样式
- 所有文本均做 HTML 转义，代码块与内联代码分别处理（d:\ResumeAssistant\web\src\utils\markdown.ts:2-7,33-36,122-129）。
- 输出容器：`.md-container`，全局内联样式提高可读性（d:\ResumeAssistant\web\src\utils\markdown.ts:85-101,103-119）。
- 不执行脚本，不解析复杂嵌套，仅覆盖常用语法，保证稳健。

## 模式切换与持久化
- 顶层状态：`editorMode` 与 `markdownText`（d:\ResumeAssistant\web\src\App.tsx:22-24）。
- 切换到 `编辑` 时会用当前 `resumeData` 生成一份最新 Markdown 文本（d:\ResumeAssistant\web\src\App.tsx:144-151）。
- 任一字段变化即写入本地存储，首渲染恢复（d:\ResumeAssistant\web\src\App.tsx:111-134）。

## 与 Schema 的互转
- 当后端返回 `resumeData` 时：渲染 HTML → 同步 Markdown → 切回 `预览`（d:\ResumeAssistant\web\src\App.tsx:136-142）。
- Markdown 主要用于人工调整与审阅；若需要从 Markdown 回写为结构化数据，可后续扩展对应解析器。

