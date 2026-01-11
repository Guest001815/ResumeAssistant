# 策略模式详解：GuideAgent 的双策略引导机制

本文档深入讲解 ResumeAssistant 项目中 **策略模式（Strategy Pattern）** 的应用，包括设计思想、两种策略的差异，以及动态切换机制。

---

## 📌 什么是策略模式？

**策略模式（Strategy Pattern）** 是一种行为设计模式，它允许在运行时选择算法或行为。在 GuideAgent 中，策略模式被用于实现 **不同类型简历板块的差异化处理**。

> **核心思想**：将"如何引导用户"的逻辑封装成不同的策略，根据任务类型动态选择。

```mermaid
graph TB
    subgraph "策略模式核心架构"
        GA["GuideAgent<br/>引导代理"]
        
        subgraph "策略选择"
            TS["TaskStrategy<br/>策略枚举"]
            STAR["STAR_STORYTELLING<br/>深挖故事模式"]
            KF["KEYWORD_FILTER<br/>技能筛选模式"]
        end
        
        GA --> TS
        TS --> STAR
        TS --> KF
    end
    
    style STAR fill:#e8f5e9,stroke:#2e7d32
    style KF fill:#e3f2fd,stroke:#1565c0
```

---

## 🎯 为什么需要策略模式？

### 问题场景

简历中不同板块需要**完全不同的处理方式**：

| 板块类型 | 处理需求           | 用户交互方式         |
| -------- | ------------------ | -------------------- |
| 项目经历 | 深挖细节、量化数据 | 多轮对话、STAR 法则  |
| 工作经历 | 深挖成就、业务影响 | 多轮对话、引导式提问 |
| 技能特长 | 快速筛选、匹配岗位 | 1-2轮确认即可        |
| 自我评价 | 文字优化           | 简单修改             |

### 不使用策略模式的问题

```mermaid
flowchart TB
    subgraph "❌ 没有策略模式"
        A["GuideAgent"] --> B["巨大的 if-else 分支"]
        B --> C["代码臃肿难维护"]
        B --> D["新板块类型需要改大量代码"]
        B --> E["测试困难"]
    end
```

### 使用策略模式的优势

```mermaid
flowchart TB
    subgraph "✅ 使用策略模式"
        A2["GuideAgent"] --> B2["读取 task.strategy"]
        B2 --> C2["调用对应策略方法"]
        C2 --> D2["代码清晰可维护"]
        C2 --> E2["新策略只需新增方法"]
        C2 --> F2["策略独立可测试"]
    end
```

---

## 📊 两种核心策略

项目定义了两种策略，通过枚举类型 `TaskStrategy` 表示：

```python
class TaskStrategy(str, Enum):
    """任务处理策略枚举"""
    STAR_STORYTELLING = "STAR_STORYTELLING"  # 深挖故事模式（工作/项目经历）
    KEYWORD_FILTER = "KEYWORD_FILTER"        # 技能筛选模式（技能特长/工具）
```

```mermaid
graph LR
    subgraph "策略对比"
        A["🎭 STAR_STORYTELLING<br/>深挖故事模式"]
        B["🔍 KEYWORD_FILTER<br/>技能筛选模式"]
    end
    
    A --> A1["多轮对话（5+轮）"]
    A --> A2["使用 STAR 法则"]
    A --> A3["挖掘量化数据"]
    A --> A4["循序渐进引导"]
    
    B --> B1["快速完成（1-2轮）"]
    B --> B2["直接给建议"]
    B --> B3["做减法+做加法"]
    B --> B4["高效确认"]
    
    style A fill:#e8f5e9,stroke:#2e7d32
    style B fill:#e3f2fd,stroke:#1565c0
```

---

## 🌟 策略一：STAR_STORYTELLING（深挖故事模式）

### 适用场景

- 项目经历
- 工作经历
- 实习经历
- 教育背景（课程、成就描述）

### 核心理念

使用 **STAR 法则**（Situation-Task-Action-Result）通过多轮对话挖掘用户经历中的亮点。

```mermaid
flowchart TB
    subgraph "STAR 法则结构"
        S["S - Situation<br/>情境背景"]
        T["T - Task<br/>任务目标"]
        A["A - Action<br/>采取行动"]
        R["R - Result<br/>取得结果"]
    end
    
    S --> T --> A --> R
```

### 对话流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant AI as AI Agent
    
    Note over AI: 🔄 STAR_STORYTELLING 策略
    
    AI->>U: 【第1轮】项目熟悉程度？<br/>A.非常熟悉 B.了解原理 C.学习项目
    U->>AI: 选 C，学习项目
    
    AI->>U: 【第2轮】项目是做什么的？
    U->>AI: 一个智能客服系统...
    
    AI->>U: 【第3轮】你具体做了哪些部分？
    U->>AI: 搭建环境、实现对话模块...
    
    AI->>U: 【第4轮】遇到什么困难？
    U->>AI: 响应时间太慢...优化后提升50%
    
    AI->>U: 【第5轮】有什么收获？
    U->>AI: 学会了缓存优化...
    
    AI->>U: 【生成草稿】基于收集信息生成优化内容
```

### 三种子模式

根据用户对项目的熟悉程度，STAR_STORYTELLING 内部还会动态切换子策略：

```mermaid
graph TB
    subgraph "STAR_STORYTELLING 子模式"
        Q["🎯 询问熟悉程度"]
        
        A["模式 A：深挖模式<br/>🔥 非常熟悉"]
        B["模式 B：引导模式<br/>💡 了解原理"]
        C["模式 C：包装模式<br/>📦 学习项目"]
    end
    
    Q --> A
    Q --> B
    Q --> C
    
    A --> A1["• 标准 STAR 追问<br/>• 开放式问题<br/>• 必须挖掘量化数据"]
    
    B --> B1["• 给选项让用户选<br/>• 降低数据精度要求<br/>• 每个问题都给选项"]
    
    C --> C1["• 停止追问落地效果<br/>• 主动建议模式<br/>• 强调技术学习能力"]
    
    style A fill:#ffebee,stroke:#c62828
    style B fill:#fff3e0,stroke:#e65100
    style C fill:#e8f5e9,stroke:#2e7d32
```

### 代码结构

```python
def _get_star_storytelling_strategy(self) -> str:
    """STAR_STORYTELLING 策略的详细指导"""
    return """
    # Strategy: STAR_STORYTELLING（深挖故事模式）
    
    ## 💬 对话式过渡话术（让对话更自然）
    - 话题深入：当用户提供有价值信息，继续深挖
    - 话题切换：当前话题聊透了，自然过渡
    - 给出选项：用户回答简短时，提供具体选项
    - 鼓励表达：降低用户压力
    
    ## 🎯 掌握程度探测
    - A. 非常熟悉 → 深挖模式
    - B. 了解原理 → 引导模式
    - C. 学习项目 → 包装模式
    
    ## 📊 量化数据要求（灵活处理）
    - 真实项目：必须包含 2+ 项量化数据
    - 学习项目：可用技术复杂度替代
    ...
    """
```

---

## 🔍 策略二：KEYWORD_FILTER（技能筛选模式）

### 适用场景

- 技能特长
- 工具/软件列表
- 语言能力
- 证书资质

### 核心理念

**快速高效**，直接给出分析结果，做减法（删除无关技能）+ 做加法（补充关键技能）。

```mermaid
graph TB
    subgraph "KEYWORD_FILTER 核心逻辑"
        A["分析用户技能列表"]
        
        B["✅ 建议保留<br/>与目标岗位相关"]
        C["❌ 建议删除<br/>与目标岗位无关"]
        D["🔍 可能遗漏<br/>岗位常见要求"]
    end
    
    A --> B
    A --> C
    A --> D
```

### 对话流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant AI as AI Agent
    
    Note over AI: 🔍 KEYWORD_FILTER 策略
    
    AI->>U: 【第1轮】直接展示分析结果：<br/>✅ 保留：Python、Java、MySQL<br/>❌ 删除：Excel、PhotoShop<br/>🔍 可能遗漏：Docker、Redis？
    U->>AI: Docker熟悉，Redis不会
    
    AI->>U: 【第2轮】生成草稿并请求确认
    U->>AI: 好的，就这样
    
    Note over AI: 任务完成！（仅2轮对话）
```

### 禁止行为

```mermaid
graph LR
    subgraph "❌ KEYWORD_FILTER 禁止的行为"
        X1["问'背景是什么'"]
        X2["问'解决了什么问题'"]
        X3["问'具体做了什么'"]
        X4["使用 STAR 法则追问"]
        X5["深挖每个技能的使用场景"]
    end
    
    style X1 fill:#ffcdd2
    style X2 fill:#ffcdd2
    style X3 fill:#ffcdd2
    style X4 fill:#ffcdd2
    style X5 fill:#ffcdd2
```

### 代码结构

```python
def _get_keyword_filter_strategy(self) -> str:
    """KEYWORD_FILTER 策略的详细指导"""
    return """
    # Strategy: KEYWORD_FILTER（技能筛选模式）
    
    ## 核心原则
    - 做减法：直接建议删除无关技能
    - 做加法：询问是否具备关键技能
    - 快速高效：最多 2 轮对话完成
    
    ## 禁止行为
    - ❌ 禁止问"背景是什么"
    - ❌ 禁止使用 STAR 法则追问
    
    ## 允许行为
    - ✅ 直接给出技能筛选建议
    - ✅ 询问是否具备某技能（是/否即可）
    ...
    """
```

---

## ⚙️ 策略模式的实现方式

### 1. 策略定义（枚举）

```python
# backend/model.py
class TaskStrategy(str, Enum):
    """任务处理策略枚举"""
    STAR_STORYTELLING = "STAR_STORYTELLING"
    KEYWORD_FILTER = "KEYWORD_FILTER"
```

### 2. 任务携带策略

```python
# backend/model.py
class Task(BaseModel):
    id: int
    section: str
    strategy: TaskStrategy = Field(
        default=TaskStrategy.STAR_STORYTELLING,
        description="Processing strategy for this task"
    )
    original_text: str
    diagnosis: str
    goal: str
```

### 3. 策略路由（核心！）

```mermaid
flowchart TB
    subgraph "策略路由机制"
        A["task.strategy"]
        
        B{"策略类型?"}
        
        C1["_get_star_storytelling_first_message_instruction()"]
        C2["_get_star_storytelling_strategy()"]
        
        D1["_get_keyword_filter_first_message_instruction()"]
        D2["_get_keyword_filter_strategy()"]
        
        E["动态生成 System Prompt"]
    end
    
    A --> B
    B -->|"STAR_STORYTELLING"| C1
    B -->|"STAR_STORYTELLING"| C2
    B -->|"KEYWORD_FILTER"| D1
    B -->|"KEYWORD_FILTER"| D2
    
    C1 --> E
    C2 --> E
    D1 --> E
    D2 --> E
```

```python
# backend/guide_agent.py - _get_system_prompt() 方法
def _get_system_prompt(self) -> str:
    strategy = self.task.strategy
    
    # 根据策略生成首次对话指引
    if len(self.messages) == 0:
        if strategy == TaskStrategy.KEYWORD_FILTER:
            first_message_instruction = self._get_keyword_filter_first_message_instruction()
        else:
            first_message_instruction = self._get_star_storytelling_first_message_instruction()
    
    # 根据策略生成策略指导
    if strategy == TaskStrategy.KEYWORD_FILTER:
        strategy_instruction = self._get_keyword_filter_strategy()
    else:
        strategy_instruction = self._get_star_storytelling_strategy()
    
    return f"""
    # Context
    任务策略: {strategy.value}
    ...
    {first_message_instruction}
    {strategy_instruction}
    """
```

---

## 🔄 策略分配机制

策略由 **Plan Agent** 在生成任务计划时自动分配：

```mermaid
sequenceDiagram
    participant PA as Plan Agent
    participant WS as WorkflowState
    participant GA as GuideAgent
    
    PA->>PA: 分析简历各板块
    PA->>PA: 根据板块类型分配策略
    
    Note over PA: 项目经历 → STAR_STORYTELLING
    Note over PA: 技能特长 → KEYWORD_FILTER
    
    PA->>WS: 保存 TaskList（包含策略）
    WS->>GA: 创建 GuideAgent(task)
    GA->>GA: 读取 task.strategy
    GA->>GA: 加载对应策略方法
```

### Plan Agent 的策略分配逻辑

```python
# Plan Agent Prompt 中的策略选择指导
"""
## 策略选择指南

1. **STAR_STORYTELLING**（深挖故事模式）：
   - 适用于：工作经历、项目经历、实习经历
   - 特点：多轮对话、STAR法则、挖掘量化数据

2. **KEYWORD_FILTER**（技能筛选模式）：
   - 适用于：技能特长、工具/框架列表
   - 特点：1-2轮对话、直接给建议、快速高效
"""
```

---

## 📊 两种策略的完整对比

```mermaid
graph TB
    subgraph "策略对比总览"
        direction TB
        
        subgraph "STAR_STORYTELLING"
            S1["🎯 目的：挖掘深度信息"]
            S2["📝 对话轮次：5+ 轮"]
            S3["💬 对话方式：循序渐进提问"]
            S4["📊 数据要求：需要量化数据"]
            S5["🎭 适用板块：项目/工作经历"]
            S6["⏱️ 用户时间：较长"]
        end
        
        subgraph "KEYWORD_FILTER"
            K1["🎯 目的：快速筛选匹配"]
            K2["📝 对话轮次：1-2 轮"]
            K3["💬 对话方式：直接给建议"]
            K4["📊 数据要求：是/否确认"]
            K5["🔍 适用板块：技能特长"]
            K6["⏱️ 用户时间：极短"]
        end
    end
    
    style S1 fill:#e8f5e9
    style S2 fill:#e8f5e9
    style S3 fill:#e8f5e9
    style S4 fill:#e8f5e9
    style S5 fill:#e8f5e9
    style S6 fill:#e8f5e9
    
    style K1 fill:#e3f2fd
    style K2 fill:#e3f2fd
    style K3 fill:#e3f2fd
    style K4 fill:#e3f2fd
    style K5 fill:#e3f2fd
    style K6 fill:#e3f2fd
```

| 维度         | STAR_STORYTELLING        | KEYWORD_FILTER      |
| ------------ | ------------------------ | ------------------- |
| **目的**     | 挖掘用户经历的深度信息   | 快速筛选和匹配技能  |
| **对话轮次** | 5+ 轮                    | 1-2 轮              |
| **开场方式** | 1句观察 + 1个问题        | 直接展示分析结果    |
| **提问风格** | 开放式 → 逐步深入        | 确认性问题（是/否） |
| **数据要求** | 量化数据（数字、百分比） | 技能具备与否        |
| **适用板块** | 项目经历、工作经历       | 技能特长、工具列表  |
| **代码行数** | ~400 行指导              | ~50 行指导          |

---

## 🧩 与传统策略模式的对比

### 传统 OOP 策略模式

```python
# 传统方式：使用接口和类
class Strategy(ABC):
    @abstractmethod
    def execute(self): pass

class StarStorytelling(Strategy):
    def execute(self): ...

class KeywordFilter(Strategy):
    def execute(self): ...

class GuideAgent:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
    
    def run(self):
        self.strategy.execute()
```

### 本项目的实现方式

```python
# 本项目方式：基于枚举 + 方法映射
class TaskStrategy(str, Enum):
    STAR_STORYTELLING = "STAR_STORYTELLING"
    KEYWORD_FILTER = "KEYWORD_FILTER"

class GuideAgent:
    def _get_system_prompt(self):
        if self.task.strategy == TaskStrategy.KEYWORD_FILTER:
            return self._get_keyword_filter_strategy()
        else:
            return self._get_star_storytelling_strategy()
```

### 为什么选择这种方式？

```mermaid
graph TB
    subgraph "本项目设计选择的原因"
        A["1. 策略是 Prompt 片段<br/>不是可执行代码"]
        B["2. LLM 的行为由 Prompt 决定<br/>不需要多态"]
        C["3. 简化序列化<br/>枚举可直接 JSON 化"]
        D["4. 便于持久化<br/>Task 对象包含策略标识"]
    end
```

---

## ✨ 设计亮点

### 1. 策略与状态机的结合

策略模式与状态机协同工作：

```mermaid
graph TB
    subgraph "状态机 × 策略"
        SM["AgentState<br/>状态机"]
        ST["TaskStrategy<br/>策略"]
        
        SM --> C["共同决定<br/>System Prompt"]
        ST --> C
        
        C --> LLM["LLM 行为"]
    end
```

- **状态机**决定"当前处于哪个阶段"
- **策略**决定"这个阶段怎么做"

### 2. 可扩展性

添加新策略只需：
1. 在 `TaskStrategy` 枚举中添加新值
2. 添加对应的 `_get_xxx_strategy()` 方法
3. 添加对应的 `_get_xxx_first_message_instruction()` 方法

### 3. 策略内的动态适应

STAR_STORYTELLING 策略内部还有**子策略切换**（模式 A/B/C），实现了更细粒度的适应性。

---

## 📐 总结

| 维度         | 说明                                      |
| ------------ | ----------------------------------------- |
| **模式**     | 策略模式（Strategy Pattern）              |
| **实现方式** | 枚举 + 方法映射（非传统 OOP 接口）        |
| **策略数量** | 2 种（STAR_STORYTELLING、KEYWORD_FILTER） |
| **分配时机** | Plan Agent 生成任务计划时                 |
| **使用时机** | GuideAgent 生成 System Prompt 时          |
| **核心价值** | 同一个 Agent 类处理不同类型任务           |

---

## 📚 相关文档

- [GuideAgent 状态机设计](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_state_machine.md)
- [GuideAgent 上下文管理](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_context_management.md)
- [工作流上下文详解](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_workflow_context.md)
- [源码：model.py](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/model.py) - TaskStrategy 定义
- [源码：guide_agent.py](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/guide_agent.py) - 策略实现
