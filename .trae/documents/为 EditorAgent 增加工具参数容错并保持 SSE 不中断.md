## 改动目标
- 防止 `JSONDecodeError` 导致 SSE/前端断流。
- 兼容新模型的非稳定 `function.arguments`（空串、自然语言、非 JSON）。
- 按需添加中文注释，解释每处改动的原因与行为。

## 代码改动点（含注释约定）
- 文件：`backend/editor_agent.py`
- 新增辅助函数（放在现有 `_safe_iter`/`_safe_call` 下方）：
```python
def _safe_json_args(raw: str) -> dict:
    """
    目的：在解析工具调用参数时提供容错，避免非法 JSON 直接导致会话中断。
    行为：
    1) 空字符串/空白 → 返回空字典 `{}` 作为兜底入参；
    2) 尝试 `json.loads(raw)`；若失败，记录警告并返回 `{}`；
    3) 若解析结果非 `dict`（例如解析成列表/字符串），同样兜底为 `{}`；
    说明：空字典会由工具层（pydantic 校验）生成结构化错误信息，反馈给模型以促使其自我纠错。
    """
    if not raw or not str(raw).strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        logger.warning("工具参数非法，已使用空对象兜底: %s", raw)
        return {}
```
- 替换两处直接解析为安全解析：
  - 位置一（独占工具分支）：`c:\\Users\\admin\\Desktop\\ResumeAssistant\\backend\\editor_agent.py:133`
    - 原：`arguments = json.loads(tc.function.arguments)`
    - 改：`arguments = _safe_json_args(tc.function.arguments)`
    - 注释：`# 安全解析工具参数，非法时以 {} 兜底，避免中断`
  - 位置二（多工具分支）：`c:\\Users\\admin\\Desktop\\ResumeAssistant\\backend\\editor_agent.py:153`
    - 原：`arguments = json.loads(tool_call.function.arguments)`
    - 改：`arguments = _safe_json_args(tool_call.function.arguments)`
    - 注释：`# 同上：逐个工具调用安全解析`

## 运行时行为（对用户与模型的可见影响）
- 非法/空参数：不会抛出异常；工具层会返回 `参数校验失败: ...` 的 `ToolMessage`，SSE 正常持续，模型通常会在下一轮修正参数。
- `askHuman`/`think` 参数缺失：产生最小可用消息（提问/思考提示），保证对话连贯。

## 为什么采用此方案（MVP 友好）
- 改动极小、集中于单文件，无需改动工具注册或前端。
- 充分复用现有 `ToolRegistry` 的 pydantic 校验与错误回传机制，减少重复逻辑。
- 通过注释明确容错策略与边界，便于后续扩展（如引入更强的 JSON 修复）。

## 可选扩展（如需加强但保持轻量）
- 在 `_safe_json_args` 中增加一次轻度修复尝试（去除尾逗号、单引号转双引号），默认关闭，按需开启。

## 验证与回归
- 人工构造非法参数（空串/自然语言/半截 JSON）：后端不报错不中断；日志含警告；前端收到校验失败或最小提示；会话继续。
- 正常参数路径保持不变。