# AgentDecision 数据层操作详解

本文档详细讲解 `AgentDecision` 如何操作数据层，包括**控制状态（AgentState）**、**对话历史（messages）**、**草稿（draft）**以及**执行文档（ExecutionDoc）**的完整机制。

---

## 📊 整体架构概览

```mermaid
graph TB
    subgraph "用户交互层"
        UI["前端 UI"]
    end
    
    subgraph "适配器层"
        Adapter["GuideAgentAdapter"]
    end
    
    subgraph "Agent 核心层"
        Agent["GuideAgent"]
        Step["step() 方法"]
    end
    
    subgraph "LLM 层"
        LLM["OpenAI API"]
    end
    
    subgraph "数据模型层"
        Decision["AgentDecision"]
        Snapshot["AgentSnapshot"]
    end
    
    subgraph "数据存储层（数据层）"
        State["AgentState<br/>状态机"]
        Messages["messages<br/>对话历史"]
        Draft["draft<br/>草稿内容"]
        ExecDoc["ExecutionDoc<br/>执行文档"]
    end
    
    subgraph "持久化层"
        WS["WorkflowState"]
        Disk["磁盘存储"]
    end
    
    UI --> Adapter
    Adapter --> Agent
    Agent --> Step
    Step --> LLM
    LLM --> Decision
    Decision --> State
    Decision --> Messages
    Decision --> Draft
    Decision --> ExecDoc
    
    State --> Snapshot
    Messages --> Snapshot
    Draft --> Snapshot
    ExecDoc --> Snapshot
    
    Snapshot --> WS
    WS --> Disk
```

---

## 🧩 核心数据模型：AgentDecision

`AgentDecision` 是 LLM 返回的**结构化决策对象**，它决定了如何更新数据层的各个组件。

### 结构定义

```python
class AgentDecision(BaseModel):
    # 推理过程
    thought: str = Field(..., description="基于诊断和用户输入的推理过程")
    
    # 下一步动作（核心状态控制字段）
    next_action: Literal[
        "CONTINUE_ASKING",   # 继续提问
        "PROPOSE_DRAFT",     # 提出草稿
        "REQUEST_CONFIRM",   # 请求确认
        "CONFIRM_FINISH"     # 确认完成
    ]
    
    # 给用户的回复
    reply_to_user: str
    
    # 草稿内容（可选）
    draft_content: Optional[str] = None
    
    # 执行文档（可选）
    execution_doc: Optional[ExecutionDoc] = None
    
    # 智能回溯字段
    intent: Optional[Literal["CONTINUE", "BACKTRACK"]] = None
    target_section: Optional[str] = None
```

### 字段与数据层的映射关系

| AgentDecision 字段          | 控制的数据层组件 | 作用说明       |
| --------------------------- | ---------------- | -------------- |
| `next_action`               | `AgentState`     | 驱动状态机流转 |
| `reply_to_user`             | `messages`       | 追加到对话历史 |
| `draft_content`             | `draft`          | 更新当前草稿   |
| `execution_doc`             | `ExecutionDoc`   | 设置执行文档   |
| `intent` + `target_section` | `AgentState`     | 触发回溯逻辑   |

---

## 🔄 状态机流转机制

### AgentState 状态定义

```python
class AgentState(str, Enum):
    DISCOVERY = "DISCOVERY"     # 正在提问挖掘信息
    DRAFTING = "DRAFTING"       # 正在展示草稿等待确认
    CONFIRMING = "CONFIRMING"   # 等待用户确认执行
    FINISHED = "FINISHED"       # 任务已完成
```

### 状态流转图

```mermaid
stateDiagram-v2
    [*] --> DISCOVERY: 任务开始
    
    DISCOVERY --> DISCOVERY: CONTINUE_ASKING
    DISCOVERY --> DRAFTING: PROPOSE_DRAFT
    
    DRAFTING --> DISCOVERY: 用户要求修改
    DRAFTING --> CONFIRMING: REQUEST_CONFIRM
    DRAFTING --> FINISHED: CONFIRM_FINISH (快速确认)
    
    CONFIRMING --> DRAFTING: 用户拒绝
    CONFIRMING --> FINISHED: CONFIRM_FINISH
    
    FINISHED --> DRAFTING: BACKTRACK (回溯)
    FINISHED --> [*]: 任务完成
    
    note right of DISCOVERY
        next_action = CONTINUE_ASKING
        继续挖掘用户信息
    end note
    
    note right of DRAFTING
        next_action = PROPOSE_DRAFT
        展示优化后的草稿
    end note
    
    note right of CONFIRMING
        next_action = REQUEST_CONFIRM
        等待用户确认执行
    end note
    
    note right of FINISHED
        next_action = CONFIRM_FINISH
        生成 ExecutionDoc
    end note
```

---

## 💾 step() 方法：数据层操作的核心

`GuideAgent.step()` 是 AgentDecision 操作数据层的**核心入口**，它实现了**原子化状态更新**。

### 执行流程图

```mermaid
flowchart TD
    subgraph "1️⃣ 接收输入"
        A["用户输入 user_input"] --> B["追加到 messages"]
    end
    
    subgraph "2️⃣ 调用 LLM"
        B --> C["构造 API 请求"]
        C --> D["调用 OpenAI API"]
        D --> E["解析 JSON 响应"]
        E --> F["创建 AgentDecision"]
    end
    
    subgraph "3️⃣ 原子化更新数据层"
        F --> G{"检查 intent"}
        G -->|BACKTRACK| H["重置状态为 DRAFTING"]
        G -->|CONTINUE| I["根据 next_action 更新状态"]
        
        H --> J["更新 messages"]
        I --> J
        
        J --> K{"有 draft_content?"}
        K -->|是| L["更新 draft"]
        K -->|否| M["跳过"]
        
        L --> N{"next_action 判断"}
        M --> N
        
        N -->|REQUEST_CONFIRM| O["构建 ExecutionDoc"]
        N -->|CONFIRM_FINISH| P["设置 FINISHED 状态"]
        N -->|其他| Q["更新对应状态"]
    end
    
    subgraph "4️⃣ 返回决策"
        O --> R["返回 AgentDecision"]
        P --> R
        Q --> R
    end
```

### 关键代码解析

```python
def step(self, user_input: str) -> AgentDecision:
    """
    执行一步对话交互：
    1. 接收用户输入
    2. 调用 LLM
    3. 原子化更新内部状态 (Messages, Draft, State)
    4. 返回决策对象供展示
    """
    # ======== 1. 更新对话历史 ========
    self.messages.append({"role": "user", "content": user_input})

    # ======== 2. 调用 LLM 获取决策 ========
    api_messages = [
        {"role": "system", "content": self._get_system_prompt()}
    ] + self.messages
    
    response = self.client.chat.completions.create(...)
    decision = AgentDecision.model_validate(json.loads(response))
    
    # ======== 3. 原子化更新数据层 ========
    
    # A. 处理回溯意图
    if decision.intent == "BACKTRACK":
        if self.current_state == AgentState.FINISHED:
            self.execution_doc = None           # 清除执行文档
            self.current_state = AgentState.DRAFTING  # 回退状态
    
    # B. 更新对话历史
    self.messages.append({"role": "assistant", "content": decision.reply_to_user})
    
    # C. 更新草稿
    if decision.draft_content:
        self.draft = decision.draft_content
    
    # D. 根据 next_action 更新状态
    if decision.next_action == "CONTINUE_ASKING":
        self.current_state = AgentState.DISCOVERY
        
    elif decision.next_action == "PROPOSE_DRAFT":
        self.current_state = AgentState.DRAFTING
        
    elif decision.next_action == "REQUEST_CONFIRM":
        self.execution_doc = self._build_execution_doc()  # 构建执行文档
        self.current_state = AgentState.CONFIRMING
        
    elif decision.next_action == "CONFIRM_FINISH":
        self.current_state = AgentState.FINISHED
    
    return decision
```

---

## 📝 对话历史（messages）管理

### 消息存储结构

```python
messages: List[dict] = [
    {"role": "user", "content": "用户的输入..."},
    {"role": "assistant", "content": "Agent的回复..."},
    {"role": "user", "content": "用户的下一轮输入..."},
    ...
]
```

### 消息流转时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as GuideAgent
    participant M as messages[]
    participant L as LLM
    
    U->>A: step("我负责开发了登录模块")
    A->>M: 追加 user 消息
    Note over M: {"role": "user", "content": "..."}
    
    A->>L: 发送 system prompt + messages
    L->>A: 返回 AgentDecision
    
    A->>M: 追加 assistant 消息
    Note over M: {"role": "assistant", "content": "..."}
    
    A->>U: 返回 decision.reply_to_user
```

---

## 📄 草稿（draft）管理

### 草稿生命周期

```mermaid
flowchart LR
    subgraph "草稿状态"
        A["None<br/>(初始)"] --> B["生成草稿<br/>(PROPOSE_DRAFT)"]
        B --> C["用户反馈修改"]
        C --> B
        B --> D["用户确认<br/>(REQUEST_CONFIRM)"]
        D --> E["构建 ExecutionDoc"]
    end
    
    style A fill:#f0f0f0
    style B fill:#ffd700
    style C fill:#87ceeb
    style D fill:#90ee90
    style E fill:#98fb98
```

### 草稿更新逻辑

```python
# step() 方法中的草稿更新逻辑
if decision.draft_content:
    self.draft = decision.draft_content  # 覆盖式更新
```

> [!IMPORTANT]
> **草稿采用覆盖式更新**：每次 LLM 返回新的 `draft_content` 时，会直接替换旧草稿，而不是追加。

---

## 📋 执行文档（ExecutionDoc）管理

### ExecutionDoc 结构

```python
class ExecutionDoc(BaseModel):
    task_id: int              # 关联的任务 ID
    section_title: str        # 目标 section 标题
    item_id: Optional[str]    # 目标 item ID
    operation: Literal[       # 操作类型
        "update_basics",
        "update_experience",
        "update_generic",
        "add_item"
    ]
    changes: Dict[str, Any]   # 具体变更内容
    new_content_preview: str  # 预览文案
    reason: str               # 修改原因
```

### ExecutionDoc 生成流程

```mermaid
flowchart TD
    A["GuideAgent.step()"] --> B{"next_action == REQUEST_CONFIRM?"}
    B -->|是| C["调用 _build_execution_doc()"]
    C --> D["从 self.task 获取元信息"]
    D --> E["从 self.draft 获取内容"]
    E --> F["构建 ExecutionDoc 对象"]
    F --> G["赋值给 self.execution_doc"]
    G --> H["同时附加到 decision.execution_doc"]
    
    B -->|否| I["跳过"]
```

### 关键代码

```python
elif decision.next_action == "REQUEST_CONFIRM":
    if self.draft:
        # 构建执行文档
        self.execution_doc = self._build_execution_doc()
        self.current_state = AgentState.CONFIRMING
        
        # 附加到决策（供 Adapter 读取）
        decision.execution_doc = self.execution_doc
```

---

## 🔗 与 WorkflowState 的集成

`GuideAgentAdapter` 负责将 `GuideAgent` 的内部状态与 `WorkflowState` 同步。

### 集成架构图

```mermaid
flowchart TB
    subgraph "GuideAgentAdapter"
        A["invoke()"]
    end
    
    subgraph "状态恢复"
        B["state.get_agent_state('guide')"]
        C["_load_from_dict()"]
    end
    
    subgraph "GuideAgent"
        D["step()"]
        E["AgentDecision 处理"]
    end
    
    subgraph "状态保存"
        F["export_state()"]
        G["state.save_agent_state('guide', ...)"]
    end
    
    subgraph "WorkflowState"
        H["agent_states: Dict"]
        I["to_dict() / from_dict()"]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

### 状态快照（AgentSnapshot）

```python
class AgentSnapshot(BaseModel):
    """Agent 运行时快照，用于中断恢复"""
    current_state: AgentState   # 当前所处的流程状态
    messages: List[dict]        # 完整的对话历史上下文
    draft: Optional[str]        # 当前持有的最新草稿
    execution_doc: Optional[ExecutionDoc]  # 当前待确认的执行文档
```

### 导出与恢复代码

```python
# 导出状态
def export_state(self) -> AgentSnapshot:
    return AgentSnapshot(
        current_state=self.current_state,
        messages=self.messages,
        draft=self.draft,
        execution_doc=self.execution_doc
    )

# 恢复状态
def load_state(self, snapshot: AgentSnapshot):
    self.current_state = snapshot.current_state
    self.messages = snapshot.messages
    self.draft = snapshot.draft
    self.execution_doc = snapshot.execution_doc
```

---

## 🎯 完整数据流示例

以下是一个完整的用户交互场景，展示 AgentDecision 如何操作数据层：

### 场景：用户优化工作经历

```mermaid
sequenceDiagram
    participant U as 用户
    participant Adapter as GuideAgentAdapter
    participant Agent as GuideAgent
    participant LLM as OpenAI
    participant Data as 数据层
    
    Note over Data: 初始状态<br/>state=DISCOVERY<br/>messages=[]<br/>draft=None
    
    U->>Adapter: "我负责过登录模块的开发"
    Adapter->>Agent: step(user_input)
    
    Agent->>Data: messages.append(user_input)
    Agent->>LLM: API 调用
    
    LLM->>Agent: AgentDecision<br/>next_action=CONTINUE_ASKING<br/>reply="能详细说说吗？"
    
    Agent->>Data: messages.append(reply)
    Agent->>Data: state = DISCOVERY
    
    Note over Data: state=DISCOVERY<br/>messages=[user, assistant]
    
    Agent->>Adapter: return decision
    Adapter->>U: "能详细说说您具体做了什么吗？"
    
    U->>Adapter: "实现了 OAuth2.0 登录..."
    Adapter->>Agent: step(user_input)
    Agent->>LLM: API 调用
    
    LLM->>Agent: AgentDecision<br/>next_action=PROPOSE_DRAFT<br/>draft_content="优化后的内容..."
    
    Agent->>Data: messages.append(...)
    Agent->>Data: draft = "优化后的内容..."
    Agent->>Data: state = DRAFTING
    
    Note over Data: state=DRAFTING<br/>draft="优化后的内容..."
    
    U->>Adapter: "可以，就用这个"
    Adapter->>Agent: step(user_input)
    Agent->>LLM: API 调用
    
    LLM->>Agent: AgentDecision<br/>next_action=CONFIRM_FINISH
    
    Agent->>Data: execution_doc = _build_execution_doc()
    Agent->>Data: state = FINISHED
    
    Note over Data: state=FINISHED<br/>execution_doc={...}
    
    Agent->>Adapter: return decision (含 execution_doc)
    Adapter->>U: 任务完成，交接给 EditorAgent
```

---

## 📚 总结

| 数据层组件     | 更新时机             | 更新来源                   | 持久化方式    |
| -------------- | -------------------- | -------------------------- | ------------- |
| `AgentState`   | 每次 step()          | `next_action` + `intent`   | AgentSnapshot |
| `messages`     | 每次 step()          | user_input + reply_to_user | AgentSnapshot |
| `draft`        | `PROPOSE_DRAFT` 时   | `draft_content`            | AgentSnapshot |
| `ExecutionDoc` | `REQUEST_CONFIRM` 时 | `_build_execution_doc()`   | AgentSnapshot |

> [!TIP]
> **设计亮点**：AgentDecision 采用**声明式**设计——LLM 只需声明"下一步做什么"（next_action），具体的状态更新逻辑由 `step()` 方法统一处理，实现了 **LLM 决策** 与 **状态管理** 的解耦。

---

## 🔗 相关文档

- [guide_agent_state_machine.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_state_machine.md) - GuideAgent 状态机详解
- [guide_state_persistence.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_state_persistence.md) - 状态持久化机制
- [guide_agent_adapter.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_adapter.md) - Agent 适配器设计
- [workflow_state.md](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/workflow_state.md) - 工作流状态管理
