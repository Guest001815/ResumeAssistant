# 创建 Plan Agent 脚本

## 1. 目标
创建一个名为 `backend/plan_agent.py` 的脚本，实现核心的 Plan Agent 功能。该 Agent 负责接收用户意图和简历，调用 LLM 生成修改计划。

## 2. 实现细节

### 类定义: `PlanAgent`
*   **初始化**:
    *   实例化 `OpenAI` 客户端，配置与 `editor_agent.py` 一致（使用相同的 `base_url` 和 `api_key`）。
    *   设置模型为 `Pro/deepseek-ai/DeepSeek-V3.2`。
*   **方法**: `generate_plan(self, user_intent: str, resume: Resume) -> str`
    *   **输入**: 用户的求职意图字符串，以及 `Resume` 对象。
    *   **处理**:
        1.  **构建 System Prompt**: 使用 `Plan Agent设计 (项目经理架构师).txt` 中定义的角色、目标、约束、JSON Schema 和示例。
        2.  **构建 User Prompt**: 将用户意图和简历内容（转换为 JSON 字符串）拼接。格式为：
            ```text
            Intent: {user_intent}
            Original Resume:
            {resume_json}
            ```
        3.  **调用 LLM**: 使用 `client.chat.completions.create` 接口，`stream=False`（根据您的要求暂不流式输出），`response_format={"type": "json_object"}` 以确保输出 JSON。
    *   **输出**: 返回 LLM 生成的 JSON 字符串（包含修改计划）。

### 依赖
*   导入 `backend/schema.py` 中的 `Resume` 类。
*   导入 `openai` 库。

### 测试代码
*   在文件末尾添加 `if __name__ == "__main__":` 代码块。
*   创建一个模拟的 `Resume` 对象和用户意图。
*   实例化 `PlanAgent` 并调用 `generate_plan`。
*   打印结果以验证效果。

## 3. 执行步骤
1.  读取 `Plan Agent设计 (项目经理架构师).txt` 获取完整的 System Prompt 内容。
2.  创建 `backend/plan_agent.py` 文件并写入代码。
