我将在 `backend` 目录下开发基于状态机驱动的 Guide Agent。

### 1. 模型定义 (`backend/models.py`)

我将创建新文件 `backend/models.py` 来定义 Agent 的内部状态和决策模型。

* **`AgentState`**: 定义枚举状态 `DISCOVERY` (挖掘), `DRAFTING` (草稿), `FINISHED` (完成)。

* **`AgentDecision`**: 定义 Pydantic 模型用于 LLM 的结构化输出，包含 `thought` (思考), `next_action` (下一步), `reply_to_user` (回复), 和 `draft_content` (草稿内容)。

* **`Task`**: 从现有的 `backend/schema.py` 导入 `Task` 模型，以保持一致性。

### 2. Guide Agent 实现 (`backend/guide_agent.py`)

我将创建 `backend/guide_agent.py` 文件并实现 `GuideAgent` 类。

* **初始化**:

  * 配置 OpenAI 客户端（参考 `PlanAgent` 的配置）。

  * 初始化 `current_state` 为 `DISCOVERY`。

  * 维护对话历史 `self.messages`。

* **`step(self, user_input)`** **方法**:

  * **预检查**: 如果状态是 `FINISHED` 则停止。

  * **上下文注入**: 将当前 `AgentState` 和 `Task` 详情动态注入到 System Prompt 中。

  * **LLM 调用**: 使用 OpenAI API (JSON 模式) 获取 `AgentDecision`。

  * **状态流转**: 根据 `next_action` 实现 `DISCOVERY` <-> `DRAFTING` -> `FINISHED` 的状态跳转逻辑。

  * **返回**: `AgentDecision` 对象。

### 3. 执行循环 (`backend/run_guide_agent.py`)

我将创建脚本 `backend/run_guide_agent.py` (即需求中的 `main.py`) 来演示和测试 Agent。

* 创建一个带有诊断信息的模拟 `Task`。

* 初始化 `GuideAgent`。

* 运行一个交互式 CLI 循环，允许用户与 Agent 对话，直到任务完成。

### 验证

* 我将运行 `backend/run_guide_agent.py` 来验证状态流转（挖掘 -> 草稿 -> 完成）是否符合预期。

