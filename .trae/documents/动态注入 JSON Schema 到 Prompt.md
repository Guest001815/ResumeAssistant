# 动态生成 System Prompt 中的 JSON Schema

根据您的指示，我将修改 `backend/plan_agent.py`，使用 `TaskList` 类的 `model_json_schema()` 方法动态生成 JSON Schema，并拼接到 System Prompt 中。这样，未来修改 `schema.py` 中的 `TaskList` 定义时，Prompt 会自动同步更新。

## 1. 修改 PlanAgent (`backend/plan_agent.py`)

*   **修改 `_get_system_prompt` 方法**:
    *   使用 `TaskList.model_json_schema()` 获取标准的 JSON Schema 字典。
    *   使用 `json.dumps(..., indent=2, ensure_ascii=False)` 将其转换为字符串。
    *   将 System Prompt 改为 f-string（或格式化字符串），将生成的 Schema 字符串插入到 `# JSON Schema` 章节下方。
    *   移除原有硬编码的 JSON 文本。

## 2. 验证

*   运行 `backend/plan_agent.py`（它包含 `__main__` 测试代码），打印生成的 Prompt 或观察输出，确保 LLM 能够理解并返回符合新 Schema 的 JSON。
*   确认生成的 Prompt 中包含 `TaskList` 的完整结构定义。

这样处理后，`schema.py` 将成为单一真值源（Single Source of Truth）。