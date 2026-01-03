## 目标

* 新增 `PlanAgent`（流式输出）与 `Plan/Task` 类，将模型生成的修改计划保存到全局 `PLAN` 对象。

* 不调用工具；代码保持简洁；`think` 取自 `reasoning_content`。

## 类设计

* `Task`：表示一个任务条目

  * 字段：

    * `id: int`

    * `section: str`

    * `original_text: str`

    * `diagnosis: str`

    * `goal: str`

    * `state: str`（任务状态，枚举）

  * `state` 取值：`pending` | `in_progress` | `completed`，默认 `pending`。

  * 方法：`to_json()`（输出不包含 `state`，以满足用户给定的 JSON Schema）。

* `Plan`：任务列表容器

  * 字段：`tasks: list[Task] = []`

  * 方法：

    * `update_from_text(text: str)`：尝试 `json.loads(text)`，遍历 `tasks` 数组，构造 `Task` 对象（`state` 默认 `pending`）。

    * `model_dump()`：返回严格符合 Schema 的字典：`{"tasks": [task.to_json() ...]}`（不包含 `state`）。

    * `set_state(task_id: int, state: str)`：更新指定任务状态（仅接受上述枚举值）。

* 全局对象：`PLAN = Plan()`。

## PlanAgent

* 初始化：

  * `OpenAI` 客户端：`base_url='https://api.siliconflow.cn/v1'`，`api_key` 从环境变量读取。

  * `model='deepseek-ai/DeepSeek-V2.5'`。

  * `self.messages=[{system: _get_system_prompt()}, {user: 合成输入}]`。

* `_get_system_prompt()`：采用用户提供的系统提示词原文。

* `run(intent: str, current_resume: Resume)`：

  * 组装 `user` 消息：`Intent: ...\nOriginal Resume: ...`。

  * `response = client.chat.completions.create(..., stream=True, temperature=0)`。

  * 流式处理（完全模仿示例）：

    * `for chunk in response:`

      * 若 `chunk.choices[0].delta.content`：累计到 `buffer` 并 `yield {role:'assistant', type:'answer', content: delta.content}`。

      * 若 `chunk.choices[0].delta.reasoning_content`：`yield {role:'assistant', type:'think', content: delta.reasoning_content}`。

  * 结束后：`PLAN.update_from_text(buffer)` 保存解析结果。

## 输出与状态

* 对外展示：流式 `answer`（JSON 文本），可选一次性 `think`。

* 内部状态：`Task.state` 默认 `pending`，支持更新为 `in_progress`、`completed`。

* `PLAN.model_dump()` 返回严格符合用户给定 Schema 的 JSON 字典（不含 `state`）。

## 交付

* 创建 `backend/plan_agent.py` 实现 `Task`、`Plan`、全局 `PLAN`、`PlanAgent`（流式输出、简洁实现）。

* 使用方式：

  * `agent = PlanAgent()`；

  * `for chunk in agent.run(intent, resume): handle(chunk)`；

  * `PLAN.model_dump()` 获取最终计划。

