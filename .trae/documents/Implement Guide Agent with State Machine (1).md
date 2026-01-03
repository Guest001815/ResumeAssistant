我将按照您的要求，开发基于状态机的 Guide Agent。

### 1. 更新模型定义 (`backend/model.py`)
我将在现有的 `model.py` 文件中补充新的状态和决策模型，保持代码库的一致性。
- **新增 `AgentState` 枚举**：定义 `DISCOVERY` (挖掘), `DRAFTING` (草稿), `FINISHED` (完成) 三种状态。
- **新增 `AgentDecision` 模型**：用于结构化 LLM 的输出（包含思考、下一步动作、回复、草稿）。
- **复用 `Task` 模型**：现有的 `Task` 定义与需求一致，直接使用。

### 2. 实现 Guide Agent 核心逻辑 (`backend/guide_agent.py`)
创建 `guide_agent.py` 文件，实现核心的 `GuideAgent` 类。
- **状态管理**：内部维护 `current_state`，默认初始化为 `DISCOVERY`。
- **Prompt 构建**：在 System Prompt 中动态注入当前状态，确保 LLM 知道自己处于“挖掘信息”还是“确认草稿”阶段。
- **状态流转逻辑 (`step` 方法)**：
  - 调用 OpenAI API 获取决策。
  - 根据 `next_action` 执行状态转换：
    - `CONTINUE_ASKING` -> 保持/返回 `DISCOVERY`
    - `PROPOSE_DRAFT` -> 进入 `DRAFTING`
    - `CONFIRM_FINISH` -> 仅在 `DRAFTING` 状态下允许进入 `FINISHED`

### 3. 创建执行入口 (`backend/main.py`)
创建 `main.py` 用于运行和测试 Agent。
- 初始化一个测试用的 `Task` 对象。
- 启动命令行交互循环，模拟用户与 Agent 的对话。
- 实时展示 Agent 的思考过程 (`thought`)、回复 (`reply_to_user`) 以及生成的草稿 (`draft_content`)。
- 当状态流转至 `FINISHED` 时结束任务。