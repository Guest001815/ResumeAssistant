## 为什么 GPT 没有这些问题
- OpenAI 官方的 Chat Completions/Responses 对工具调用的兼容性最好，SDK 返回的 `tool_calls` 结构与再次回传到 `messages` 的格式完全一致，容错也更高。
- 第三方兼容端点（如 SiliconFlow）对 `messages` 的校验更严格，且不同模型的支持矩阵不完全一致（有的模型只支持 `responses`，有的对 `assistant` 同时携带 `content`+`tool_calls` 不友好），因此同样的代码在 GPT 正常，在兼容端会报错。

## 改进思路（最小改动优先）
1. 增加消息“清洗层”（Provider 适配）：
   - 针对 SiliconFlow：
     - `assistant` 有 `tool_calls` 时强制 `content=""`；
     - `tool_calls[*].function.arguments` 统一 `json.dumps(...)` 为字符串；
     - 校验所有 `role`/`content` 都是允许类型；
   - 针对 OpenAI 官方：保持原样透传。
2. 端点选择的降级策略：
   - 为模型配置 `endpoint` 偏好：默认 `chat.completions`；若遇到 20015/结构错误，自动切换到 `responses.stream(input=..., tools=...)`（DeepSeek 系列在部分平台更稳定）。
3. 调试与可观测性：
   - 打印将要发送的 `messages` 的首尾与含 `tool_calls` 的片段（仅开发日志，不含敏感信息），快速定位结构问题。
4. 验证用例：
   - 构造一次仅 `tool_calls` 的轮次（`content==""`）；
   - 构造一次含文本与工具调用的轮次（在 SiliconFlow 路径下置空 `content`）；
   - 连续两次工具调用（含 `tool` 消息回传 `tool_call_id`）确保端到端无报错。

## 交付内容
- Provider 适配与 `sanitize_messages(messages)` 实现并接入调用点。
- 端点切换的小型策略（出现特定错误码时回退到 `responses`）。
- 开发日志与最小验证用例，以确保在 GPT 与 SiliconFlow 下都稳定工作。