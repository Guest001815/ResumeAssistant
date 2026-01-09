# GuideAgent：逻辑与原理图解

本文档通过图表展示 [GuideAgent](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/guide_agent.py#10-1532) 的内部逻辑，解释它是如何处理信息并管理对话状态的。

---

## 1. 大脑：数据流管道 (The Brain)

每当你发送一条消息，GuideAgent 都会通过这个管道进行处理：

```mermaid
graph TD
    classDef memory fill:#e1f5fe,stroke:#01579b
    classDef logic fill:#fff9c4,stroke:#fbc02d
    classDef output fill:#e8f5e9,stroke:#2e7d32

    subgraph INPUT ["👂 1. 上下文构建 (Context Construction)"]
        I1["用户最新消息"] -->|追加| Buffer["消息历史缓冲区"]
        History["📜 完整对话历史"] -.->|合并| Prompt
        System["🧠 System Prompt <br/>(动态策略指令)"] -.->|注入| Prompt
    end

    subgraph PROCESS ["⚙️ 2. 推理 (Reasoning)"]
        Prompt -->|发送至 API| LLM["DeepSeek / OpenAI"]
        LLM -->|返回| JSON{"结构化决策 (Decision)"} 
    end

    subgraph DECISION ["🤔 3. 执行 (Execution)"]
        JSON -->|解析| Think["思考过程 (Thought)"]
        JSON -->|解析| Action["下一步动作 (Next Action)"]
        JSON -->|解析| Reply["回复用户 (Reply)"]
        
        Action -->|CONTINUE_ASKING| Loop["更新历史 & 等待用户"]
        Action -->|PROPOSE_DRAFT| StateChange1["切换状态 -> DRAFTING"]
        Action -->|REQUEST_CONFIRM| StateChange2["切换状态 -> CONFIRMING"]
    end

    class History,System memory
    class LLM,JSON logic
    class Think,Action,Reply output
```

### 关键元素

| 元素              | 说明                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------ |
| **System Prompt** | 告诉演员如何表演的"剧本"（例如："先别写草稿，先问问题"）。它会根据当前状态动态变化。 |
| **结构化 JSON**   | Agent 不仅仅是说话，它会输出一个包含*思考*、*决策*和*回复*的 JSON 对象。             |

---

## 2. 心脏：状态机 (The Heart)

Agent 的行为完全由它的 `current_state`（当前状态）决定。

```mermaid
stateDiagram-v2
    [*] --> DISCOVERY: 任务开始
    
    state DISCOVERY {
        [*] --> 分析中
        分析中 --> 提问: 信息不完整
        分析中 --> DRAFTING: 信息足够
        
        note right of 分析中
            目标: 深挖信息
            规则: 禁止提供草稿
        end note
    }
    
    state DRAFTING {
        [*] --> 撰写草稿
        撰写草稿 --> 征求反馈: 展示给用户
        征求反馈 --> 撰写草稿: 用户想要修改
        征求反馈 --> CONFIRMING: 用户认可
        
        note right of 撰写草稿
            目标: 打磨内容
            规则: 必须展示草稿
        end note
    }

    state CONFIRMING {
        [*] --> 等待用户点击
        note right of 等待用户点击
            目标: 等待最终批准
            动作: 系统暂停
            (前端显示 [确认] 按钮)
        end note
    }
    
    CONFIRMING --> FINISHED: 用户点击按钮
    
    state FINISHED {
        [*] --> 空闲
        空闲 --> DRAFTING: 用户反悔 & 回溯任务
    }
```

### 状态说明

| 状态           | 目标         | 规则                       |
| -------------- | ------------ | -------------------------- |
| **DISCOVERY**  | 深挖信息     | 禁止提供草稿，专注于提问   |
| **DRAFTING**   | 打磨内容     | 必须展示草稿，征求反馈     |
| **CONFIRMING** | 等待最终批准 | 系统暂停，前端显示确认按钮 |
| **FINISHED**   | 任务完成     | 支持回溯到 DRAFTING        |

---

## 3. 代码映射表

| 概念              | 代码位置                                                                    | 说明                                                                                   |
| :---------------- | :-------------------------------------------------------------------------- | :------------------------------------------------------------------------------------- |
| **状态定义**      | [model.py](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/model.py) | 枚举 `AgentState` (DISCOVERY, DRAFTING 等)                                             |
| **System Prompt** | `GuideAgent._get_system_prompt()`                                           | 根据 `self.current_state` 动态返回 Prompt                                              |
| **执行循环**      | `GuideAgent.step()`                                                         | 1. 追加用户消息<br/>2. 调用 LLM<br/>3. 根据 `next_action` 更新状态<br/>4. 返回决策对象 |

---

## 4. 核心代码片段

### 状态枚举定义

```python
class AgentState(str, Enum):
    DISCOVERY = "DISCOVERY"     # 正在提问挖掘信息
    DRAFTING = "DRAFTING"       # 正在展示草稿等待确认
    CONFIRMING = "CONFIRMING"   # 等待用户确认执行
    FINISHED = "FINISHED"       # 任务已完成
```

### 决策对象结构

```python
class AgentDecision(BaseModel):
    thought: str                # 推理过程
    next_action: Literal[       # 下一步动作
        "CONTINUE_ASKING",      # 继续提问
        "PROPOSE_DRAFT",        # 提出草稿
        "REQUEST_CONFIRM",      # 请求确认
        "CONFIRM_FINISH"        # 确认完成
    ]
    reply_to_user: str          # 回复用户的内容
    draft_content: Optional[str] # 草稿内容
    intent: Optional[Literal["CONTINUE", "BACKTRACK"]]  # 用户意图
```

### 状态转换逻辑

```python
# 在 step() 方法中
if decision.next_action == "CONTINUE_ASKING":
    self.current_state = AgentState.DISCOVERY
    
elif decision.next_action == "PROPOSE_DRAFT":
    self.current_state = AgentState.DRAFTING
    
elif decision.next_action == "REQUEST_CONFIRM":
    self.current_state = AgentState.CONFIRMING
    
elif decision.next_action == "CONFIRM_FINISH":
    self.current_state = AgentState.FINISHED
```

---

## 5. 延伸阅读

- [GuideAgent 上下文管理机制](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_context_management.md) - 详细分析动态 Prompt 生成机制
- [源码：guide_agent.py](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/guide_agent.py) - 完整实现代码
