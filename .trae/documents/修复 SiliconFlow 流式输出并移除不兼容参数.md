## 问题定位

* 后端在进行流式迭代时抛出 400 错误：`prefix is not allowed when the response format is json_schema`。结合当前实现，最可能由向 SiliconFlow 传入工具相关参数触发其内部的 `json_schema` 响应格式校验。

* 现状：

  * 流创建在 `backend/agentkit/streaming.py:17` 使用 `client.chat.completions.create(..., tools=..., tool_choice="required", stream=True)`。

  * SSE 封装与迭代在 `backend/api.py:53-61`，将 Agent 事件包装为 `data: ...\n\n`。

  * 流式解析在 `backend/editor_agent.py:167-176`，正确处理 `delta.content` 与 `delta.reasoning_content`。

## 改动目标

* 与您给的 SiliconFlow 示例保持一致：仅使用 `model + messages + stream=True` 进行纯流式输出，逐块读取 `choices[0].delta.content` 与 `choices[0].delta.reasoning_content`。

* 避免触发 `json_schema` 前缀校验：在不需要工具调用时不传 `tools` 和 `tool_choice` 参数；需要工具时再显式开启，并使用更兼容的选择策略。

## 具体修改

* `backend/agentkit/streaming.py`

  * 将 `create_stream(model, messages, tools)` 改为工具参数可选：`tools: Optional[List[dict]] = None, tool_choice: Optional[str] = None`。

  * 组装调用参数时：

    * 基本参数：`model`, `messages`, `stream=True`, `temperature=0`。

    * 必须强制使用工具。

  * 代码位置：`backend/agentkit/streaming.py:17-24`。

* `backend/agents/streaming.py`（存在同名聚合器的重复实现）

  * 与上述同改，保持两处实现一致，防止未来从另一处被调用造成行为不一致。

  * 代码位置：`backend/agents/streaming.py:31-38`。

* `backend/editor_agent.py`

  * 在不需要工具调用的纯对话场景下，按示例改为不传 `tools` 与 `tool_choice`：

    * `stream_resp = streamer.create_stream(model=self.model, messages=self.messages)`（省略 `tools`）。

  * 维持现有块处理逻辑：

    * 处理 `choices[0].delta.content` 与 `choices[0].delta.reasoning_content` 并持续 `emit_think`，当前实现已符合示例要求（`backend/editor_agent.py:171-176`）。

  * 如确需工具（函数调用），再以显式参数开启：`streamer.create_stream(..., tools=self.registry.get_openai_tools(), tool_choice="auto")`，尽量避免使用 `required` 以提升兼容性。

## 验证方案

* 启动后端，向 `/run` 发送简单消息（无工具调用需求），观察：

  * 终端无 400 报错；SSE 正常持续输出，前端事件 `think` 连续累积。

  * 后端日志显示逐块追加 `delta.content`/`delta.reasoning_content`，无 `response_format` 相关错误。

* 若切回含工具调用流程：

  * 使用 `tool_choice="required"` 。

## 可选调整

* 模型：保留现有 `Pro/deepseek-ai/DeepSeek-V3.1-Terminus`，或按示例切换为 `deepseek-ai/DeepSeek-V2.5`；两者流式字段相同，`reasoning_content` 仅在推理模型可用时出现。

* 兼容性：后续如需结构化强约束，可考虑 OpenAI `response_format={"type":"json_object"}`，避免 `json_schema + prefix` 限制（本次先不启用）。

## 交付结果

* 使流式输出与 SiliconFlow 示例对齐，移除不必要的工具参数以规避 400 错误；保留工具能力为可选项，按需开启。

