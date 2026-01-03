# API 事件协议（SSE）

## 环境与基础
- 环境变量：`VITE_API_BASE`（d:\ResumeAssistant\web\.env.development:1）
- 默认后端地址：`http://localhost:8000`（d:\ResumeAssistant\web\src\api\sse.ts:1-3）
- 请求路径：`POST /run`（d:\ResumeAssistant\web\src\api\sse.ts:2）

## 请求格式
- Headers：`Accept: text/event-stream`、`Content-Type: application/json`（d:\ResumeAssistant\web\src\api\sse.ts:12-15）
- Body：`{ input: string, resume: any | null }`（d:\ResumeAssistant\web\src\api\sse.ts:16）
- 取消：传入 `AbortSignal` 支持取消（d:\ResumeAssistant\web\src\api\sse.ts:8-9,17-18）
- 错误：`!resp.ok || !resp.body` 抛异常（d:\ResumeAssistant\web\src\api\sse.ts:19）

## 客户端解析流程
- 读取流：`resp.body.getReader()`（d:\ResumeAssistant\web\src\api\sse.ts:20）
- 解码：`TextDecoder('utf-8')`（d:\ResumeAssistant\web\src\api\sse.ts:21）
- 缓冲拼接与按行分割：持续解码追加到 `buffer`，通过 `split("\\n")` 拆分，并保留最后的半行在 `buffer`（d:\ResumeAssistant\web\src\api\sse.ts:22-30）。
- 去除前缀：若行以 `data:` 开头则剥离（d:\ResumeAssistant\web\src\api\sse.ts:33-35）。
- 解析事件：逐行 `JSON.parse`，成功则回调 `onEvent(obj)`；无效 JSON 被忽略（d:\ResumeAssistant\web\src\api\sse.ts:35-41）。

## 事件类型约定
- `think: string`：模型思考过程文本（追加到“思考区”）
- `tool: string`：工具输出或说明（展示在“工具输出区”）
- `error: string`：错误信息（同样进入“工具输出区”）
- `data: object`：结构化简历数据（写入到顶层 `resumeData`）
- Chat 组件事件分发（d:\ResumeAssistant\web\src\components\Chat.tsx:30-44）

## 示例事件载荷
```text
data: {"type":"think","content":"正在分析你的工作经历..."}
data: {"type":"tool","content":"已抽取 3 段经历，准备生成要点"}
data: {"type":"data","content":{"basics":{"name":"张三"},"sections":[{"type":"experience","title":"工作经历","items":[{"organization":"示例公司","title":"前端工程师","date_start":"2021-01","date_end":"2023-06","location":"北京","highlights":["负责前端架构升级","主导组件库建设"]}]}]}}
data: {"type":"error","content":"后端超时，请稍后重试"}
```

## 错误处理与取消
- 非正常响应：抛异常并由 Chat 组件记录为助手消息（d:\ResumeAssistant\web\src\api\sse.ts:19；d:\ResumeAssistant\web\src\components\Chat.tsx:63-66）。
- 并发取消：若存在旧的控制器则先 `abort`，再创建新控制器（d:\ResumeAssistant\web\src\components\Chat.tsx:32-34）。
- 请求闭合：正常或异常结束时，将工具区文本合并为一条助手消息，清理“思考区”（d:\ResumeAssistant\web\src\components\Chat.tsx:50-55,62-66）。
