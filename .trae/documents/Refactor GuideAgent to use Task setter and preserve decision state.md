您提得非常准确，`latest_decision` 确实包含了 `draft` 和 `reply`，如果分开存容易导致数据不一致。我将优化状态管理方案，确保单一数据源（Single Source of Truth）。

### 1. 优化数据结构 (`backend/model.py`)
- **新增 `AgentSnapshot`**：仅存储核心状态，避免冗余。
  - `current_state`: 当前所处阶段。
  - `messages`: 完整的对话历史（这是恢复上下文的核心）。
  - `draft`: 当前生成的草稿（这是核心交付物）。
  - *移除 `latest_decision`*：`decision` 是临时的交互结果，其产生的**副作用**（回复、草稿、状态变更）已经被分别记录在 `messages`、`draft` 和 `current_state` 中了，因此不需要单独存储它，从而消除不一致风险。

### 2. 重构 `GuideAgent` (`backend/guide_agent.py`)

#### A. 属性定义（单一真实源）
- `self.current_state`: 状态机指针。
- `self.messages`: 对话流。
- `self.draft`: 当前持有的草稿内容（初始化为 `None`）。

#### B. `step` 方法重构（原子化更新）
- **执行流程**：
  1. 调用 LLM 获取 `decision`。
  2. **同步更新（关键）**：
     - 将 `reply` 追加到 `messages`。
     - 如果 `decision` 包含 `draft_content`，**立即**更新 `self.draft`。
     - 根据 `next_action` 和 `self.draft` 的状态，更新 `current_state`。
  3. 返回 `decision` 仅供 UI 展示，不再作为内部状态依赖。

#### C. `run` 方法封装
- 循环调用 `step`。
- 每次循环开始前，根据 `self.messages` 恢复上下文。
- 最终返回 `self.draft`。

#### D. 状态导出与恢复
- **`export_state`**: 打包 `current_state`, `messages`, `draft`。
- **`load_state`**: 直接覆盖上述三个属性，确保恢复后的 Agent 与中断前完全一致。

通过这种方式，我们只存储“产生结果后的状态”（State, History, Draft），而不存储“产生过程的临时变量”（Decision），从而从根本上保证了一致性。