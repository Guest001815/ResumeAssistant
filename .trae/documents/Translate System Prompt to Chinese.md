我将按照您的要求，将 `backend/guide_agent.py` 中的 System Prompt 全部翻译为中文。

### 1. 更新 `backend/guide_agent.py` 中的 `_get_system_prompt` 方法
我将把原本的英文提示词替换为中文，同时保留核心的逻辑变量和结构。
- **Role**: 设定为“拥有15年经验的简历专家”。
- **Context**: 将上下文信息的标签（Task ID, Section等）改为中文描述。
- **State Machine Instructions**:
  - `DISCOVERY` 状态描述：目标是“基于诊断结果追问信息”，约束是“暂不要提供草稿”。
  - `DRAFTING` 状态描述：目标是“展示草稿或根据反馈修改”，约束是“只有用户满意才可结束”。
- **Strategy**:
  - `DISCOVERY`: “提1-2个核心问题，不要让用户感到压力”。
  - `DRAFTING`: “在 `draft_content` 中提供具体的改写内容”。
  - `Finish`: “只有用户明确批准草稿后，才设置 `next_action` 为 CONFIRM_FINISH”。

这样可以确保 Agent 在中文语境下更自然地与用户交互，同时严格遵守状态机逻辑。