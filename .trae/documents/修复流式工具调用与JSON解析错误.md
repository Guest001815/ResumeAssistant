**问题诊断**

* 触发点：OpenAI SDK 流式迭代断言 `new_tool.type == "function"`，随后在解析工具参数时报 `JSONDecodeError`。

* 断言原因：所用模型 `Pro/deepseek-ai/DeepSeek-V3.2`（硅基流兼容层）在流式工具事件的 `type` 可能不是 `function`；当前强制 `tool_choice="required"` 会推动模型必须走工具事件路径，导致 SDK 内部断言失败。见 `backend/editor_agent.py:84`。

* JSON 解析原因：`tool_call.function.arguments` 返回的字符串不是严格 JSON（如未闭合引号、单引号、尾逗号等），直接 `json.loads` 失败。见 `backend/editor_agent.py:130`、`backend/editor_agent.py:150`。

* SSE 包装层已正确捕获并转发异常，见 `backend/api.py:54-59`。

**改动方案**

* 放宽工具决策：将 `tool_choice` 从 `"required"` 改为 `"auto"`（或移除）以避免非兼容模型被强制走工具流事件，降低 SDK 断言触发概率。位置：`backend/editor_agent.py:84`。

* 增强参数解析健壮性：

  * 在 `json.loads(...)` 外包裹 `try/except`，捕获 `JSONDecodeError`。

  * 失败时：

    * 生成一条面向模型的错误提示消息，包含原始 `arguments` 字符串与该工具完整 Schema（可复用 `tool_framework.ToolRegistry.to_openai_schema()`），要求模型按 `parameters` 返回合法 JSON 再次调用。

    * 将该提示 `self.messages.append(...)` 后进入下一轮（`max_circle -= 1; continue`）。位置：`backend/editor_agent.py:130`、`backend/editor_agent.py:150`。

* 提示规范输出：在系统提示中补充一句“所有工具 `arguments` 必须是合法 JSON 字符串，与 `parameters` 严格匹配”。位置：`backend/editor_agent.py:170-215`。

* 兼容事件增量：保持当前对 `message.delta` / `response.output_text.delta` / `content.delta` 的处理，但仅将文本累积到 `assistant_msg["content"]`，避免对 reasoning 进行误拼接（现状合理）。

**验证步骤**

* 启动后用简单输入触发工具（如更新基本信息），观察：

  * 流式事件不再抛断言；

  * 若模型返回不合规参数，SSE 中出现错误提示并自动重试；

  * 最终工具调用成功，返回 `tool` 与 `data` 事件；

* 日志检查：`editor_agent` 不再出现“流式迭代异常”，`api` 不再出现 `JSONDecodeError`。

**问题成因结论**

* 主要是 SDK 兼容与解析策略问题，而非“模型工具使用能力本身不行”。当前强制工具决策与严格 JSON 解析在异构模型/网关下易出错；通过放宽 `tool_choice` 与增加解析回退即可规避。

