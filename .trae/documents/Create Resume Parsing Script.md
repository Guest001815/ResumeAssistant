我将严格按照您提供的 DeepSeek OCR / 多模态调用示例，编写 Python 脚本 `backend/parse_resume.py`。

**脚本实现方案**：

1.  **直接读取 PDF**：不再依赖 PyPDF2 进行文本提取，而是直接以二进制模式读取 PDF 文件。
2.  **Base64 编码**：将 PDF 文件内容转换为 Base64 编码字符串。
3.  **构造多模态 Payload**：
    *   按照您提供的格式，将 Base64 字符串封装在 `image_url` 字段中（格式为 `data:application/pdf;base64,...`）。
    *   **Prompt**：将原来的“转 Markdown”提示词替换为**简历解析专用提示词**。我会将 `Resume` 的 JSON Schema 放入提示词中，要求模型直接输出符合 Schema 结构的 JSON 数据。
4.  **API 调用**：
    *   使用 `backend/editor_agent.py` 中的 SiliconFlow 配置。
    *   调用 `chat.completions.create` 接口发送请求。
5.  **结果处理**：
    *   接收模型返回的 JSON 字符串。
    *   使用 `Resume.model_validate` 验证并转换为对象。
    *   输出结果。

**依赖**：仅需 `openai` 和 Python 内置库 (`base64`, `json` 等)。无需安装 PDF 解析库。