## 答复
- 仅靠提示词可以引导模型“何时调用哪个工具”，但无法保证严格的“单轮仅调用一个功能工具”的互斥约束与你当前自定义事件协议。因此需要结合 LangChain 的内置 Agent/工具机制与一个很薄的运行期约束/回调层。
- LangChain 内部已提供：工具编排（Functions Agent）、流式输出（回调/stream）、错误重试（Runnable/Retry/Fallback）。我们用这些完成 90% 的工作，剩下 10% 通过提示+回调实现你定制的行为。

## 方案概览
- 使用 `langchain_openai.ChatOpenAI(streaming=True)` + `create_openai_tools_agent` + `AgentExecutor`。
- 工具以 `StructuredTool` 封装，内部委托到你现有的 `ToolRegistry.execute_tool(...)`，复用全部 Schema 与数据结构。
- 互斥约束通过两层实现：
  1) 提示词明确“本轮仅可选择 askHuman、stop 或执行类工具之一”；
  2) 自定义 Callback/中间件在触发多个工具时拦截，返回错误信息并触发一次重试（与现有行为一致）。
- 流式输出通过 `AsyncIteratorCallbackHandler`/`on_chat_model_stream`，持续发出 `think` 与 `answer` 事件；从 `additional_kwargs` 读取 `reasoning_content`（若模型提供）。

## 架构
- **LLM**：`ChatOpenAI(model="Pro/deepseek-ai/DeepSeek-V3.2", base_url=https://api.siliconflow.cn/v1, api_key=...)`。
- **Agent**：`create_openai_tools_agent(llm, tools, prompt=系统Prompt)` → `AgentExecutor`，自动处理工具调用与消息追加。
- **工具封装**：用 `StructuredTool` 将 `UpdateBasicsTool` 等统一包装为 LangChain 工具；执行时转到 `ToolRegistry.execute_tool(...)`，并把返回的 `ToolMessage` 注入会话。
- **事件协议**：自定义 Callback 将模型流式 token映射为你的事件类型：`think`（reasoning）、`answer`（正文）、`tool`（工具结果）、`error`（互斥/参数校验失败）、`data`（`resume.model_dump()`）。
- **互斥与自纠**：Callback 在收到多工具调用时，注入错误提示，要求模型对照 Schema 修复并仅选择一个工具，再由 `AgentExecutor` 重试一次。

## 实施步骤
1. 新增 `backend/langchain_agent.py`：初始化 `ChatOpenAI`、`ToolRegistry`、`Resume`，加载系统 Prompt（复用 `backend/editor_agent.py:213-263`）。
2. 将现有工具适配为 `StructuredTool`：每个工具的 `func(args)` 内部调用 `registry.execute_tool(...)`，透传返回内容。
3. 构建 `agent = create_openai_tools_agent(llm, tools, prompt=...)` 并封装为 `AgentExecutor`，设置 `return_intermediate_steps=True`。
4. 实现 `StreamingCallbackHandler`：
   - 在 `on_chat_model_stream` 中读取 `chunk.additional_kwargs.get("reasoning_content")` → 发出 `think`；读取 `chunk.content` → 发出 `answer`。
   - 在 `on_tool_start/on_tool_end` 中发出 `tool` 事件；当检测到同轮多工具请求时发出 `error` 并触发一次性重试。
   - 在执行类工具结束后追加 `data`（`resume.model_dump()`）。
5. 编写 `run(user_input, current_resume)`：
   - 维护 `messages` 与单轮重试预算（最多 2 次）。
   - 调用 `AgentExecutor.stream(...)` 或 `agent_executor.invoke(...)`+回调，持续产出事件。
6. SiliconFlow 适配：读取 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，或允许通过构造参数传入。

## 验证
- 流式：观察 `think/answer` 交替输出，正文连续累积，最终汇总为完整回复。
- 工具互斥：对比含 `askHuman` 与执行工具的同时调用，确认被拦截并重试（参考现有 `backend/editor_agent.py:148-181`）。
- 参数错误：故意传错字段，确认返回 Schema 提示并仅一次自纠重试（参考 `backend/tool_framework.py:223-244`、`backend/editor_agent.py:166-173,193-200`）。
- 数据校验：调用 `update_basics/add_experience_item` 等，收到 `type=data` 携带 `resume.model_dump()`。

## 配置与交付
- 代码：`backend/langchain_agent.py`、最小 CLI/HTTP 入口。
- 配置：`OPENAI_BASE_URL=https://api.siliconflow.cn/v1`、`OPENAI_API_KEY`。
- 文档：如何接入与替换现有 Agent，保留现有事件协议。