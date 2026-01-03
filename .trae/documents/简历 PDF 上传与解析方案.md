## 一、目标
- 在后端现有 FastAPI 路由文件中（包含 `/run`）新增一个接口：`POST /resume/upload-parse`。
- 该接口独立完成：接收 PDF → 调用 OpenAI 多模态模型解析 → 得到满足现有 Resume 结构的 JSON → 更新后端全局 Resume 对象 → 将 PDF 与 JSON 持久化 → 返回 `{ resume, id }` 给前端。
- 前端在 `web` 中做最小改动：增加上传入口与一个 API 封装，复用当前 `resumeData` 渲染链路。

## 二、后端设计（FastAPI + OpenAI）
### 1. 接口定义
- 路径：`POST /resume/upload-parse`，与 `/run` 在同一 FastAPI 文件中。
- 请求：`multipart/form-data`，字段 `file: UploadFile`（PDF）。
- 响应：`{ resume: ResumeJson, id: string }`，其中 `ResumeJson` 结构 **复用你已有的 Resume 定义**。

### 2. Resume 结构复用策略
- 不重新定义新的 Resume 模型，只使用当前已有的 Resume 结构（无论是 Pydantic 模型还是约定的 dict 结构）。
- OpenAI Prompt 中：
  - 提供一份“标准 Resume JSON 示例”（来自你现有的 Schema/示例）。
  - 要求模型严格按该结构输出 JSON：字段名、嵌套、section 类型等完全一致，不额外增加字段，不返回解释文字或 Markdown。
- 使用一个 `normalize_resume_json(raw_json)` 函数做轻量归一化，确保最终对象与现有 Resume 完全兼容，可与前端 `resumeData` 互转。

### 3. 单接口内部功能块拆分
在 `upload_and_parse_resume` 中只做编排，具体逻辑拆为可单测的函数，每个函数前按格式写注释块（功能名（第xx-xx行）\n作用：xxx，输入：xxx，输出：xxx），函数内部使用 `logger`：

1. `validate_upload_file(file: UploadFile) -> None`
   - 校验文件是否存在、MIME 是否为 PDF、大小是否在上限内；错误抛 HTTPException。
2. `save_pdf_to_storage(file: UploadFile, base_dir: Path) -> tuple[str, Path]`
   - 生成 `resume_id`，创建目录，保存 `resume.pdf`，返回 `(resume_id, pdf_path)`。
3. `parse_resume_with_openai(pdf_path: Path) -> dict`
   - 调用 OpenAI 多模态接口（使用官方 SDK 和你可用的模型），传入 PDF + Prompt，返回原始 JSON dict。
4. `normalize_resume_json(raw: dict) -> ResumeObject`
   - 依据现有 Resume 结构，删除多余字段、填充默认值，返回与你现有 Resume 类型兼容的对象。
5. `save_resume_json(resume_id: str, resume_obj, base_dir: Path) -> Path`
   - 将 Resume 对象序列化写入 `resume.json`，返回路径。
6. `update_global_resume(resume_obj) -> None`
   - 更新文件内的全局 Resume 变量（当前会话使用的简历）。
7. `build_response(resume_id: str, resume_obj) -> dict`
   - 构造 `{ "resume": ResumeJson, "id": resume_id }` 的返回体。

- `upload_and_parse_resume` 路由函数：
  - 依次调用上述函数，使用 `logger` 记录关键步骤和异常，保持函数体简短、易读、易测。

### 4. 持久化目录与全局状态
- 根目录：`storage/resumes/`。
- 每次调用：生成唯一 `resume_id`，目录为 `storage/resumes/{resume_id}/`：
  - `resume.pdf`：原始上传 PDF。
  - `resume.json`：解析后的 Resume JSON。
- 全局变量：`CURRENT_RESUME`（类型为你现有的 Resume 类型），在解析成功后更新，用于后续全局访问。

### 5. 日志与单元测试
- 日志：
  - 模块级 `logger = logging.getLogger(__name__)`；
  - 每个功能块内部记录 `[block_name] start/end`，关键参数（如 `resume_id`、路径）、异常用 `logger.exception`。
- 单元测试：
  - 各功能块函数可在不启动 FastAPI 的情况下独立测试（上传校验、文件保存、JSON 归一化等）。
  - 路由层用 FastAPI `TestClient` 做集成测试（上传假 PDF + mock OpenAI 调用）。

## 三、前端最小改动设计（web）
### 1. 新增 API 封装
- 新建 `web/src/api/uploadResume.ts`：
  - 读取 `VITE_API_BASE`；
  - 导出 `uploadAndParseResume(file: File): Promise<{ resume: any; id: string }>`：
    - 使用 `FormData` 调用 `POST /resume/upload-parse`；
    - 返回解析后的 JSON。

### 2. App 组件改动（保持现有聊天逻辑不动）
- 文件：`web/src/App.tsx`。
- 改动点：
  1. 引入 `uploadAndParseResume`。
  2. 在右栏标题区“📄 右栏 + 导出”附近，增加“上传 PDF”按钮 + 隐藏的 `input[type="file"]`：
     - 按钮点击触发 `input.click()`；
     - `onChange` 事件中拿到选中的 `file`。
  3. 新增函数 `handleUploadResume(file: File)`：
     - 调用 `uploadAndParseResume(file)`；
     - 从响应中取出 `resume`，调用 `setResumeData(resume)`。
- 其余部分（Chat、SSE `/run`、Markdown 编辑、导出菜单）完全不变。

### 3. 数据联动
- 一旦 `setResumeData` 被调用：
  - 现有 `useEffect` 自动：
    - 调用 `renderResumeHtmlFromSchema` 生成 HTML；
    - 调用 `resumeToMarkdown` 生成 Markdown；
    - 右栏切换至预览模式。
- `ResumePreview` 使用 `iframe srcDoc` 立即展示多模态解析后的简历。

## 四、实现顺序
1. 在后端 FastAPI 路由文件中：
   - 配置 logger、全局 `CURRENT_RESUME` 和持久化根目录常量。
   - 按步骤实现各个功能块函数，并添加指定格式的注释与日志。
   - 实现 `@app.post("/resume/upload-parse")`，只负责调用这些函数并返回结果。
2. 在前端 `web` 中：
   - 添加 `uploadResume.ts` 封装；
   - 修改 `App.tsx` 增加“上传 PDF”入口和 `handleUploadResume` 调用。
3. 通过简单的本地请求 / 前端操作验证链路可用，再逐步补充单元测试和必要的异常处理。