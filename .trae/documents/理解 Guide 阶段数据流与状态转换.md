# 理解 Guide 阶段数据流与状态转换

我将以用户请求 `/session/{id}/guide` 为切入点，为您详细剖析从 API 调用到 Orchestrator 调度，再到 Agent 执行和状态更新的完整数据流。

## 核心内容

1.  **数据流时序 (Sequence of Data Flow)**
    -   **API 层**: 接收请求，提取会话 ID 和用户输入。
    -   **Orchestrator**: 恢复上下文，调用 Agent，处理返回的 Action。
    -   **Guide Agent**: 执行核心业务逻辑（思考、生成回复、生成草稿），决定下一步 Action。
    -   **State Update**: 根据 Action 更新 `WorkflowState` 的 `current_stage` 和 `current_exec_doc`。

2.  **状态机转换逻辑 (State Transitions)**
    -   重点解释 `WorkflowStage` 枚举值的变化条件。
    -   **GUIDING -> GUIDING**: 普通对话（Action: `WAIT_INPUT`）。
    -   **GUIDING -> CONFIRMING**: 生成草稿并请求确认（Action: `REQUEST_CONFIRM` 或 `HANDOFF`）。
    -   **CONFIRMING -> EDITING**: 用户确认后（API: `/confirm`）。

3.  **代码映射 (Code Mapping)**
    -   我将直接引用刚才读取的代码行号，对应讲解每个步骤的代码实现。
    -   例如：`api.py` 如何调用 `orchestrator.run_guide_step`，以及 `orchestrator.py` 如何处理 `AgentAction.REQUEST_CONFIRM`。

## 交付形式
-   **文字讲解**: 结合代码片段的详细步骤说明。
-   **Mermaid 状态图**: 专门针对 Guiding 阶段的微观状态流转图。
