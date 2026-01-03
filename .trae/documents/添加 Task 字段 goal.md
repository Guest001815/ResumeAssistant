# 移除 Task 类中的 goal 属性

根据您的指示，我将从 `Task` 类中移除 `goal` 属性，并相应更新 `PlanAgent` 的 Prompt，使其不再生成该字段。

## 1. 修改数据模型 (`backend/schema.py`)

* **修改** **`Task`** **类**:

  * 移除 `goal: str` 字段。

## 2. 修改 PlanAgent (`backend/plan_agent.py`)

* **更新 System Prompt**:

  * 在 JSON Schema 描述中移除 `goal` 字段。

  * 在 Few-Shot Example（少样本示例）的 Output 中移除 `goal` 字段。

  * 更新 Role/Objective 描述，如果其中有明确提到“生成 goal/修改指令”的措辞，进行微调以匹配新结构（主要是诊断为主）。

## 3. 验证

* 创建并运行一个新的验证脚本 `verify_plan_agent_no_goal.py`。

* 确认生成的 TaskList 中 `Task` 对象不再包含 `goal` 属性。

* 确认 LLM 的输出符合新的 Schema。

