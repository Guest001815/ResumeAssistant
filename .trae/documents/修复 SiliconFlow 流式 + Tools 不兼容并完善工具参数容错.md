## 问题复盘
- `tool_choice="required"` 在 SiliconFlow 不支持，直接 400。
- SiliconFlow 的 SSE + tools 增量格式与 OpenAI Python SDK 的内部假设不一致，触发 `assert new_tool.type == "function"`，导致流式迭代异常。
- 模型偶发返回空串、半截 JSON、非对象的 `arguments`，原地 `json.loads` 会中断；现有 `_safe_json_args` 已能容错并反馈错误。

## 解决方案总览
- 分离“内容流式输出”和“工具调用执行”：
  - 对 SiliconFlow：工具开启时禁用 SDK 流式，采用非流式轮询工具调用；仅在不需要工具时保持内容流式。
  - 替换 `tool_choice="required"` 为省略或 `"auto"`，通过系统提示与校验引导模型必须先调用 `think` 再调用其它工具。
- 为提升用户体验：在非流式模式下，对 `assistant.content` 做“伪流式”分片输出，保证前端仍有渐进反馈。
- 增强回退：一旦流式出现断言或迭代异常，自动降级为非流式一次性调用，不中断会话。
- 安全与可维护：移除硬编码密钥，改用环境变量；引入“提供商能力表”，针对不同 base_url 决定是否允许“流式+tools”。

## 代码改动点
- `backend/editor_agent.py`：
  1) 在 `EditorAgent.__init__` 中读取 `SILICONFLOW_API_KEY` 环境变量；保留 `base_url`。
  2) 增加提供商能力标识：例如 `_provider_supports_stream_tools = not self.client.base_url.startswith("https://api.siliconflow.cn/")`。
  3) 重构 `run(...)` 的主循环（约 145–156 行）：
     - 当 `tools` 启用且提供商不支持“流式+tools”时：改用 `self.client.chat.completions.create(..., stream=False, tools=..., tool_choice="auto")`；
     - 解析 `response.choices[0].message`，将 `assistant.content` 以分片形式输出到前端（伪流式）；
     - 按现有逻辑读取 `tool_calls`，逐个执行，沿用 `_safe_json_args` 与 `ToolMessage` 错误反馈；
     - 保持 `stop/askHuman` 的互斥校验与提示；
     - 完成一次调用后，根据是否还有工具触发决定是否继续循环。
  4) 保留原有流式路径，仅在“提供商支持且未开启 tools”时使用，以避免断言。
  5) 全局移除/替换 `tool_choice="required"`（约 149 行），统一改为省略或 `"auto"`。
- `backend/tool_framework.py`：无需改动；沿用现有 Pydantic 校验和 `ToolMessage` 构造。

## 交互与体验
- 思考过程：继续使用 `think` 工具；若模型未按要求调用 `think`，在会话中插入提示并重试一轮。
- 内容输出：
  - 流式可用时：保持增量输出。
  - 非流式时：对完整文本按句子/标点分片，逐段输出，保留“正在思考...”提示。
- 工具错误：保留详细错误回传给模型，引导其重新构造参数并再次调用。

## 验证方案
- 单测：为 `_safe_json_args` 增加用例（空串、半截 JSON、数字/列表），确保返回 `({}, error)` 并记录日志。
- 集成测试：
  - 伪造返回包含 `tool_calls` 的非流式响应，验证多工具顺序执行与互斥校验；
  - 注入异常触发流式断言，确认自动降级到非流式仍能完成会话。
- 手动验证：
  - SiliconFlow 模型（DeepSeek/Qwen）实际跑通“think → 调工具 → 更新简历 → 输出结果”，不再出现 SDK 断言。

## 风险与回滚
- 风险：非流式下无法拿到真实 token 级增量；通过伪流式提升体验。
- 回滚：保留原流式路径与能力表开关，随时切回旧逻辑（仅在 OpenAI 官方端点且无需 tools 时启用）。

## 额外改进（可选）
- 为不同模型添加提示模板微调，强调“参数必须是对象 JSON”，降低半截/非对象概率。
- 将 resume 的结构变化事件（`type: "data"`）节流或合并，减少前端渲染压力。
