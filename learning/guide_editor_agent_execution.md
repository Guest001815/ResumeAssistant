# EditorAgent 执行机制详解

本文档详细讲解 `EditorAgent` 的执行流程，包括**混合执行模式**、**工具框架**、**与 Orchestrator 的交互**等核心机制。

---

## 📊 整体架构概览

```mermaid
graph TB
    subgraph "触发层"
        Guide["GuideAgent"]
        ExecDoc["ExecutionDoc"]
    end
    
    subgraph "适配器层"
        Adapter["EditorAgentAdapter"]
        Invoke["invoke()"]
    end
    
    subgraph "EditorAgent 核心"
        Agent["EditorAgent"]
        ExecuteDoc["execute_doc()"]
        Run["run() LLM推理"]
    end
    
    subgraph "执行策略"
        Simple["简单操作<br/>直接执行"]
        Complex["复杂操作<br/>LLM推理"]
    end
    
    subgraph "工具框架"
        Registry["ToolRegistry"]
        Tools["具体工具"]
    end
    
    subgraph "数据层"
        Resume["Resume 对象"]
        Sections["Sections"]
        Items["Items"]
    end
    
    Guide -->|产出| ExecDoc
    ExecDoc --> Adapter
    Adapter --> Invoke
    Invoke --> Agent
    Agent --> ExecuteDoc
    
    ExecuteDoc --> Simple
    ExecuteDoc --> Complex
    
    Simple -->|"update_basics<br/>update_experience<br/>update_generic"| Resume
    Complex --> Run
    Run --> Registry
    Registry --> Tools
    Tools --> Resume
    
    Resume --> Sections
    Sections --> Items
```

---

## 🎯 触发机制：从 GuideAgent 到 EditorAgent

### 触发条件

EditorAgent 的执行由 `ExecutionDoc` 触发。当 GuideAgent 进入 `FINISHED` 状态并产出 `ExecutionDoc` 后，Orchestrator 会自动触发 EditorAgent。

```mermaid
sequenceDiagram
    participant U as 用户
    participant Guide as GuideAgent
    participant Orch as Orchestrator
    participant Editor as EditorAgent
    participant Resume as Resume对象
    
    U->>Guide: "可以，就用这个"
    Guide->>Guide: state = FINISHED
    Guide->>Guide: 生成 ExecutionDoc
    Guide->>Orch: AgentOutput (action=HANDOFF, content=ExecutionDoc)
    
    Note over Orch: 检测到 HANDOFF 动作<br/>next_agent = "editor"
    
    Orch->>Editor: invoke(ExecutionDoc)
    Editor->>Resume: 执行变更
    Editor->>Orch: AgentOutput (更新后的 Resume)
    Orch->>U: 任务完成
```

---

## 🔧 核心方法：execute_doc()

`execute_doc()` 是 EditorAgent 的核心执行方法，采用**混合模式**设计：

### 混合执行策略

```mermaid
flowchart TD
    A["execute_doc(doc, resume)"] --> B{"判断 operation 类型"}
    
    B -->|update_basics| C["直接调用<br/>_execute_update_basics()"]
    B -->|update_experience| D["直接调用<br/>_execute_update_experience()"]
    B -->|update_generic| E["直接调用<br/>_execute_update_generic()"]
    B -->|add_item| F["LLM推理<br/>run()"]
    B -->|其他| G["错误处理"]
    
    C --> H["生成器 yield 状态消息"]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I["return 更新后的 Resume"]
    
    style C fill:#90ee90
    style D fill:#90ee90
    style E fill:#90ee90
    style F fill:#ffd700
    style G fill:#ff6b6b
```

### 代码解析

```python
def execute_doc(self, doc: ExecutionDoc, resume: Resume) -> Generator[Dict, None, Resume]:
    """
    混合模式执行：根据ExecutionDoc执行简历变更。
    
    - 简单操作（update_basics, update_experience, update_generic）：直接调用工具，不需要LLM
    - 复杂操作（add_item等）：走LLM推理
    """
    self.resume = resume
    
    yield {"role": "assistant", "type": "info", "content": f"开始执行: {doc.operation}"}
    
    # 🟢 简单操作：直接执行
    if doc.operation == "update_basics":
        result = self._execute_update_basics(doc)
        yield {"role": "assistant", "type": "tool", "content": result}
        
    elif doc.operation == "update_experience":
        result = self._execute_update_experience(doc)
        yield {"role": "assistant", "type": "tool", "content": result}
        
    elif doc.operation == "update_generic":
        result = self._execute_update_generic(doc)
        yield {"role": "assistant", "type": "tool", "content": result}
        
    # 🟡 复杂操作：LLM推理
    elif doc.operation == "add_item":
        yield {"role": "assistant", "type": "info", "content": "复杂操作，启动LLM推理..."}
        prompt = self._build_llm_prompt_from_doc(doc)
        for msg in self.run(prompt, resume):
            yield msg
    
    return self.resume  # 返回更新后的简历
```

---

## 📝 四种操作类型详解

### 操作类型对照表

| 操作类型            | 执行方式 | 使用场景               | 执行方法                       |
| ------------------- | -------- | ---------------------- | ------------------------------ |
| `update_basics`     | 直接执行 | 更新姓名、邮箱、电话等 | `_execute_update_basics()`     |
| `update_experience` | 直接执行 | 更新工作/项目经历      | `_execute_update_experience()` |
| `update_generic`    | 直接执行 | 更新技能/证书等通用项  | `_execute_update_generic()`    |
| `add_item`          | LLM推理  | 新增条目等复杂操作     | `run()`                        |

### update_experience 执行流程

```mermaid
flowchart TD
    A["_execute_update_experience(doc)"] --> B["提取 changes 和 section_title"]
    
    B --> C["精确匹配 section"]
    C -->|找到| D["定位目标 section"]
    C -->|未找到| E["模糊匹配"]
    
    E -->|找到| D
    E -->|未找到| F["❌ 抛出 ValueError"]
    
    D --> G{"有 item_id?"}
    G -->|是| H["精确定位 item"]
    G -->|否| I["降级到第一个 item"]
    
    H -->|找到| J["更新 highlights"]
    H -->|未找到| I
    
    I --> J
    
    J --> K["返回成功消息"]
    
    style F fill:#ff6b6b
    style K fill:#90ee90
```

---

## 🤖 LLM推理模式：run() 方法

复杂操作（如 `add_item`）需要 LLM 推理来决定如何执行。

### ReAct 推理循环

```mermaid
flowchart TD
    subgraph "run() 推理循环"
        A["接收用户输入"] --> B["追加到 messages"]
        B --> C["调用 LLM"]
        C --> D["解析响应"]
        
        D --> E{"有 tool_calls?"}
        E -->|是| F{"检查互斥工具"}
        E -->|否| G["继续循环"]
        
        F -->|stop/askHuman 单独出现| H["执行工具并结束"]
        F -->|stop/askHuman 与其他工具混用| I["提示修正并重试"]
        F -->|普通工具调用| J["依次执行工具"]
        
        J --> K["追加工具结果到 messages"]
        K --> G
        
        G --> C
        I --> C
    end
```

### 工具调用时序图

```mermaid
sequenceDiagram
    participant E as EditorAgent
    participant M as messages[]
    participant L as LLM
    participant R as ToolRegistry
    participant T as 具体工具
    participant Resume as Resume对象
    
    E->>M: 追加 user 消息
    E->>L: 发送 messages + tools
    L->>E: 返回 tool_calls
    
    loop 每个 tool_call
        E->>R: execute_tool(name, args)
        R->>T: 调用具体工具
        T->>Resume: 修改简历
        T->>R: 返回 ToolMessage
        R->>E: 返回结果
        E->>M: 追加工具结果
    end
    
    E->>L: 继续推理
    L->>E: stop 或 askHuman
    E->>E: 结束循环
```

---

## 🛠️ 工具框架（Tool Framework）

EditorAgent 使用工具框架来执行具体的简历修改操作。

### 工具框架架构

```mermaid
classDiagram
    class BaseTool {
        <<abstract>>
        +name: str
        +description: str
        +args_schema: Type[BaseModel]
        +execute(args, tool_call_id, context)
        +to_openai_schema()
    }
    
    class ToolRegistry {
        -_tools: Dict[str, BaseTool]
        +register(tool: BaseTool)
        +get_openai_tools()
        +execute_tool(name, args, context, tool_call_id)
    }
    
    class UpdateBasicsTool {
        +name = "update_basics"
        +execute()
    }
    
    class UpdateExperienceTool {
        +name = "update_experience_item"
        +execute()
    }
    
    class AddExperienceTool {
        +name = "add_experience_item"
        +execute()
    }
    
    class UpsertGenericTool {
        +name = "upsert_generic_item"
        +execute()
    }
    
    class StopTool {
        +name = "stop"
        +execute()
    }
    
    class ThinkTool {
        +name = "think"
        +execute()
    }
    
    BaseTool <|-- UpdateBasicsTool
    BaseTool <|-- UpdateExperienceTool
    BaseTool <|-- AddExperienceTool
    BaseTool <|-- UpsertGenericTool
    BaseTool <|-- StopTool
    BaseTool <|-- ThinkTool
    
    ToolRegistry o-- BaseTool
```

### 可用工具列表

| 工具名称                 | 描述              | 参数                                           |
| ------------------------ | ----------------- | ---------------------------------------------- |
| `update_basics`          | 更新基本信息      | name, email, phone, label, links               |
| `add_experience_item`    | 新增工作/项目经历 | section_title, title, organization, highlights |
| `update_experience_item` | 更新经历条目      | section_title, item_id, highlights             |
| `delete_experience_item` | 删除经历条目      | section_title, item_id                         |
| `upsert_generic_item`    | 新增/更新通用项   | section_title, title, subtitle, description    |
| `think`                  | 记录思考过程      | thought                                        |
| `askHuman`               | 向用户提问        | question                                       |
| `stop`                   | 标记任务结束      | reason                                         |

---

## 🔄 与 Adapter 层的集成

`EditorAgentAdapter` 负责将 `EditorAgent` 适配到统一的 `BaseAgent` 接口。

### Adapter 执行流程

```mermaid
flowchart TD
    subgraph "EditorAgentAdapter.invoke()"
        A["获取 current_exec_doc"] --> B{"有执行文档?"}
        B -->|否| C["返回 FINISH"]
        B -->|是| D["调用 execute_doc()"]
        
        D --> E["处理生成器"]
        
        subgraph "生成器处理"
            E --> F["循环 next(gen)"]
            F --> G["收集 AgentMessage"]
            G --> F
            F -->|StopIteration| H["获取返回的 Resume"]
        end
        
        H --> I["更新 state.resume"]
        I --> J["返回 AgentOutput"]
    end
    
    style C fill:#f0f0f0
    style J fill:#90ee90
```

### 关键代码

```python
def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
    exec_doc = state.current_exec_doc
    if not exec_doc:
        return AgentOutput(thought="没有待执行的文档", action=AgentAction.FINISH)
    
    # 处理生成器模式
    messages = []
    updated_resume = None
    
    gen = self._agent.execute_doc(exec_doc, state.resume)
    try:
        while True:
            msg = next(gen)
            messages.append(AgentMessage(
                role=msg.get("role", "assistant"),
                type=msg.get("type", "info"),
                content=msg.get("content"),
                agent_name=self.name
            ))
    except StopIteration as e:
        updated_resume = e.value  # 获取返回的 Resume
    
    # 更新状态
    if updated_resume:
        state.resume = updated_resume
    
    return AgentOutput(
        thought="执行完成",
        action=AgentAction.FINISH,
        content=state.resume,
        messages=messages
    )
```

---

## 🎬 完整执行场景

### 场景：更新工作经历的 highlights

```mermaid
sequenceDiagram
    participant U as 用户
    participant Guide as GuideAgent
    participant Orch as Orchestrator
    participant Adapter as EditorAgentAdapter
    participant Editor as EditorAgent
    participant Resume as Resume对象
    
    Note over Guide: 用户确认草稿<br/>state = FINISHED
    
    Guide->>Guide: 构建 ExecutionDoc
    Note over Guide: operation: "update_experience"<br/>section_title: "工作经历"<br/>item_id: "xxx"<br/>changes: {content: "..."}
    
    Guide->>Orch: HANDOFF to "editor"
    Orch->>Adapter: invoke(input, state)
    
    Adapter->>Adapter: exec_doc = state.current_exec_doc
    Adapter->>Editor: execute_doc(exec_doc, resume)
    
    Note over Editor: operation == "update_experience"<br/>走直接执行路径
    
    Editor->>Editor: _execute_update_experience(doc)
    Editor->>Resume: 查找目标 section
    Editor->>Resume: 定位目标 item
    Editor->>Resume: 更新 highlights
    
    Editor-->>Adapter: yield {"type": "info", ...}
    Editor-->>Adapter: yield {"type": "tool", ...}
    Editor-->>Adapter: return updated_resume
    
    Adapter->>Orch: AgentOutput (FINISH)
    Orch->>U: 任务完成，简历已更新
```

---

## 📊 执行模式对比

```mermaid
flowchart LR
    subgraph "简单操作（直接执行）"
        A1["ExecutionDoc"] --> B1["映射到具体方法"]
        B1 --> C1["直接修改 Resume"]
        C1 --> D1["返回结果"]
    end
    
    subgraph "复杂操作（LLM推理）"
        A2["ExecutionDoc"] --> B2["构建 LLM Prompt"]
        B2 --> C2["LLM 推理"]
        C2 --> D2["生成 tool_calls"]
        D2 --> E2["执行工具"]
        E2 --> F2["循环直到 stop"]
        F2 --> G2["返回结果"]
    end
    
    style A1 fill:#90ee90
    style D1 fill:#90ee90
    style A2 fill:#ffd700
    style G2 fill:#ffd700
```

| 特性         | 简单操作     | 复杂操作           |
| ------------ | ------------ | ------------------ |
| **执行方式** | 直接调用方法 | LLM推理 + 工具调用 |
| **延迟**     | 低（~10ms）  | 高（~1-3s）        |
| **成本**     | 无 LLM 调用  | 需要 LLM API       |
| **灵活性**   | 固定逻辑     | 可处理边缘情况     |
| **适用场景** | 结构化更新   | 新增/复杂变更      |

---

## 📚 总结

> [!TIP]
> **设计亮点**：EditorAgent 采用**混合执行模式**——简单操作直接执行，复杂操作走 LLM 推理。这种设计在保证灵活性的同时，大幅降低了延迟和成本。

### 核心组件关系

```mermaid
graph LR
    A["ExecutionDoc"] -->|输入| B["EditorAgent"]
    B -->|简单操作| C["直接执行方法"]
    B -->|复杂操作| D["run() LLM推理"]
    D -->|调用| E["ToolRegistry"]
    E -->|分发| F["具体工具"]
    C --> G["Resume"]
    F --> G
```

---

## 🔗 相关文档

- [guide_agent_decision_data_layer.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_decision_data_layer.md) - AgentDecision 数据层操作
- [guide_agent_adapter.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_adapter.md) - Agent 适配器设计
- [workflow_state.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/workflow_state.md) - 工作流状态管理
