## 变更目标
- 保持官方文档的流式输出：仅使用 `stream: true`，按增量解析 `delta.content`、`delta.reasoning_content` 与 `delta.tool_calls`。
- 工具优先：强制模型进行工具调用，文本增量作为“think”渲染到前端。
- 避免 400/20015：移除严格 `response_format={"type":"json_object"}` 导致的前缀冲突。

## 改动范围（极小）
- `backend/editor_agent.py:162-168`
  - 启用 `tool_choice="required"`（当前在 `backend/editor_agent.py:166` 被注释）。
  - 删除传入的 `response_format={"type":"json_object"}`（在 `backend/editor_agent.py:167`）。
- 其它文件无需改动：现有流式增量与事件封装已满足“文本→think、工具→执行”的分路。
  - 文本增量：通过 `EventEmitter.emit_think` 直接推到前端（`backend/agentkit/events.py:5-7`）。
  - 工具增量：按 `index` 聚合 `id/name/arguments`，无需从文本抽取（`backend/editor_agent.py:169-197` + `backend/agentkit/messages.py:12-27`）。

## 前端配合（基本无改动）
- SSE 事件格式保持不变：`{"role":"assistant","type":"think|tool|error|data","content":...}`（由后端封装，`backend/api.py:36-57`）。
- 若已渲染 `type: "think"`，则无需调整；如需更好体验，可将“思考”区与“工具执行”区分栏显示。

## 验证步骤
- 触发一次需要工具的交互：观察 `delta.tool_calls` 被正确组装与执行；`think` 文本持续流式展示。
- 确认无 `400/20015` 报错，SSE 持续输出，工具结果与数据事件 (`type: "data"`) 正常到达。
- 回归测试：仅思考、不触发工具的轮次也正常结束（`type: "tool"` 收敛为“生成完成”路径，`backend/editor_agent.py:243-246`）。

## 兼容与扩展
- 如未来必须结构化 JSON：可切换为 `json_schema` 严格模式并禁止任何非 JSON 输出；但这与工具增量流同用需新协议，改动大。
- 安全优化（可选）：将 API Key 移至环境变量与配置文件，避免硬编码泄露。

## 交付结果
- 后端：两处参数调整，无协议变更；工具优先与思考文本并行流式输出。
- 前端：沿用现有 `type: "think"` 渲染即可；无必需改动。