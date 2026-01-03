我将把 `parse_resume.py` 脚本转换为集成到现有 `backend/api.py` 应用中的 FastAPI 接口。

计划如下：

1.  **更新依赖**:
    *   在 `backend/requirements.txt` 中添加 `pymupdf` (用于 PDF 处理) 和 `python-multipart` (用于文件上传)。

2.  **重构 `backend/parse_resume.py`**:
    *   将核心解析逻辑提取到一个新函数 `parse_resume_content(file_content: bytes) -> Resume` 中。
    *   这个新函数将接收原始 PDF 字节数据（适配文件上传场景），而不是文件路径。
    *   它将直接返回 `Resume` 对象，而不是写入文件。
    *   保留现有的 `parse_resume(pdf_path)` 函数以保持向后兼容性（CLI 用法），但更新它以调用新的 `parse_resume_content` 函数。

3.  **更新 `backend/api.py`**:
    *   从 `fastapi` 导入 `UploadFile` 和 `File`。
    *   从 `parse_resume` 导入新的 `parse_resume_content` 函数。
    *   添加一个新的 `POST /parse_resume` 接口，该接口接收文件上传，调用解析逻辑，并返回结构化的 JSON 响应。

这种方法确保了现有的命令行（CLI）功能仍然可用，同时增加了新的 Web API 能力。