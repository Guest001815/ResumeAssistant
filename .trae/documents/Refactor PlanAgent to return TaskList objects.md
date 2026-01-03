# 重构 PlanAgent 以输出结构化 TaskList

根据您的要求，我将设计 `Task` 和 `TaskList` 类，并将 `PlanAgent` 的输出类型从 JSON 字符串修改为 `TaskList` 对象。

## 1. 定义数据模型

在 [schema.py](file:///c%3A/Users/admin/Desktop/ResumeAssistant/backend/schema.py) 中新增以下 Pydantic 模型：

* **Task**: 用于描述单个修改任务。

  * `id`: Integer (唯一标识)

  * `section`: String (定位简历的具体模块)

  * `original_text`: String (原始文本)

  * `diagnosis`: String (诊断问题)

* **TaskList**: 用于包装任务列表。

  * `tasks`: List\[Task]

## 2. 修改 PlanAgent

更新 [plan\_agent.py](file:///c%3A/Users/admin/Desktop/ResumeAssistant/backend/plan_agent.py) 中的 `PlanAgent` 类：

* **引入新模型**: 导入 `Task` 和 `TaskList`。

* **更新** **`generate_plan`** **方法**:

  * 将返回类型注解从 `str` 改为 `TaskList`。

  * 解析 LLM 返回的 JSON 字符串，并验证转换为 `TaskList` 对象。

  * 增加错误处理，确保返回格式正确。

## 3. 验证

* 更新 `plan_agent.py` 中的 `if __name__ == "__main__":` 测试代码，以验证新的对象输出格式。

