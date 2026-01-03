## 目标
- 保留生成器模式，用离散事件展示“思考—工具调用—数据更新—回答”全过程
- 移除为流式增量产出而设计的冗余逻辑（不做内容 delta 拼接、不做多段输出）

## 改动范围
- `backend/editor_agent.py:96-218`（核心运行逻辑）
- 删除未使用的流式辅助：`backend/editor_agent.py:58-70`

## 事件设计（保留生成器）
- 仅产出少量关键事件，不做增量流：
  - `think`：一次性输出模型的最终思考（若存在 `message.reasoning_content`）
  - `tool`：
    - 调用开始：`正在调用工具：{name}`
    - 调用结果：透传工具返回内容（一次性）
    - 调用结束：`工具执行完成：{name}`
  - `data`：在履历变更类工具执行后，产出一次最新 `resume.model_dump()`
  - `answer`：一次性给出最终自然语言回复
  - `error`：仅在互斥错误或参数校验失败时产出一次提示

## 具体修改
- 在 `run(user_input, current_resume)` 开始处设置 `self.resume = current_resume`
- 删除 `content_acc`，`assistant_msg["content"]` 直接取 `message.content`
- 删除所有增量/多段产出：保留一次性 `think` 与一次性 `answer`
- 保留工具互斥与执行：产出离散 `tool`/`data` 事件，不再分多段
- 参数校验失败：保留一次自纠重试（`max_circle = 2`），错误时产出一次 `error` 并内部追加 `tip` 至 `self.messages`
- 删除未使用的 `_iter_events`/`_get_final`（`backend/editor_agent.py:58-70`）

## 代码参考点
- 去除增量：`backend/editor_agent.py:104-128/132-136`
- 工具事件保留但改为一次性：`backend/editor_agent.py:163-181/192-209`
- 错误一次性提示：`backend/editor_agent.py:183-187/172-179/200-206`

## 返回行为
- 仍为生成器；调用者迭代少量事件即可了解整个过程，无需处理流式 delta

## 验证
- 运行包含三类工具（`askHuman`/`stop`/编辑工具）的用例，观察事件序列完整且无多段输出
- 参数失败时仅一次重试，最终事件序列清晰、可控