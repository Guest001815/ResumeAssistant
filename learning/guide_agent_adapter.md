# AgentAdapter 深度解析

> 本文深入剖析 `agent_adapters.py` 中的适配器模式，解释如何将不同的 Agent 统一适配到 `BaseAgent` 接口，实现 Orchestrator 的统一调度。

---

## 1. 什么是 AgentAdapter？

**AgentAdapter（Agent 适配器）** 是一种**设计模式**，用于将现有的、接口不统一的 Agent 包装成统一的 `BaseAgent` 接口，使得 Orchestrator 可以用相同的方式调度不同的 Agent。

```mermaid
flowchart LR
    subgraph 原始Agent["原始 Agent（接口各异）"]
        PA[PlanAgent<br/>generate_plan方法]
        GA[GuideAgent<br/>step/generate_opening 方法]
        EA[EditorAgent<br/>execute_doc 方法]
    end
    
    subgraph 适配器层["Adapter 适配层"]
        PAA[PlanAgentAdapter]
        GAA[GuideAgentAdapter]
        EAA[EditorAgentAdapter]
    end
    
    subgraph 统一接口["BaseAgent 统一接口"]
        BI[invoke / stream<br/>export_state / load_state]
    end
    
    PA --> PAA --> BI
    GA --> GAA --> BI
    EA --> EAA --> BI
    
    BI --> O[Orchestrator<br/>统一调度]
```

### 设计原则

项目文档定义了三大设计原则：

| 原则         | 说明                                                             |
| ------------ | ---------------------------------------------------------------- |
| **最小侵入** | 不改动原 Agent 逻辑，仅包装为统一接口                            |
| **统一协议** | 接入 `BaseAgent` / `AgentInput` / `AgentOutput` / `AgentMessage` |
| **渐进迁移** | 便于后续切换到 LangGraph 或替换 Agent 实现                       |

---

## 2. 核心组件

### 2.1 BaseAgent 抽象基类

所有适配器都继承自 `BaseAgent`，必须实现以下接口：

```mermaid
classDiagram
    class BaseAgent {
        <<abstract>>
        +name: str*
        +description: str
        +invoke(input, state) AgentOutput*
        +stream(input, state) Generator*
        +export_state() Dict*
        +load_state(state) void*
        +reset() void
    }
    
    class PlanAgentAdapter {
        -_agent: PlanAgent
        +name = "plan"
        +invoke()
        +stream()
        +export_state()
        +load_state()
    }
    
    class GuideAgentAdapter {
        -_agent: GuideAgent
        -_current_task: Task
        +name = "guide"
        +invoke()
        +stream()
        +invoke_opening()
        +export_state()
        +load_state()
        +reset()
    }
    
    class EditorAgentAdapter {
        -_agent: EditorAgent
        +name = "editor"
        +invoke()
        +stream()
        +export_state()
        +load_state()
    }
    
    BaseAgent <|-- PlanAgentAdapter
    BaseAgent <|-- GuideAgentAdapter
    BaseAgent <|-- EditorAgentAdapter
```

### 2.2 统一的数据结构

```mermaid
flowchart TB
    subgraph 输入["AgentInput"]
        I1[content: str<br/>用户输入]
        I2[context: Dict<br/>上下文信息]
    end
    
    subgraph 输出["AgentOutput"]
        O1[thought: str<br/>思考过程]
        O2[action: AgentAction<br/>下一步动作]
        O3[content: Any<br/>输出内容]
        O4[next_agent: str<br/>目标Agent]
        O5[messages: List<br/>过程消息]
    end
    
    subgraph 动作["AgentAction 枚举"]
        A1[CONTINUE - 继续当前]
        A2[HANDOFF - 切换Agent]
        A3[WAIT_INPUT - 等待输入]
        A4[REQUEST_CONFIRM - 等待确认]
        A5[FINISH - 完成任务]
        A6[SWITCH_TASK - 任务回溯]
    end
```

---

## 3. 三个适配器详解

### 3.1 PlanAgentAdapter

**职责**：简历诊断与计划生成

```python
# 源码位置：backend/agent_adapters.py 第29-100行

class PlanAgentAdapter(BaseAgent):
    def __init__(self):
        from plan_agent import PlanAgent
        self._agent = PlanAgent()  # 延迟导入避免循环依赖
    
    @property
    def name(self) -> str:
        return "plan"
    
    def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
        user_intent = input.content
        resume = state.resume
        
        # 调用原有 PlanAgent 的方法
        task_list = self._agent.generate_plan(user_intent, resume)
        
        return AgentOutput(
            thought="已分析简历并生成修改计划",
            action=AgentAction.FINISH,
            content=task_list,
            messages=[...]
        )
```

**特点**：
- ✅ **无状态**：`export_state()` 返回空字典
- ✅ **不支持真正流式**：`stream()` 调用 `invoke()` 后包装
- ✅ **一次性执行**：调用后直接返回 `FINISH`

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant A as PlanAgentAdapter
    participant P as PlanAgent
    participant S as WorkflowState
    
    O->>A: invoke(input, state)
    A->>S: 获取 resume
    A->>P: generate_plan(intent, resume)
    P-->>A: TaskList
    A-->>O: AgentOutput(FINISH, TaskList)
```

---

### 3.2 GuideAgentAdapter

**职责**：引导用户完善简历内容，生成草稿

```python
# 源码位置：backend/agent_adapters.py 第102-374行

class GuideAgentAdapter(BaseAgent):
    def __init__(self):
        self._agent = None  # 延迟初始化
        self._current_task: Optional[Task] = None
    
    @property
    def name(self) -> str:
        return "guide"
```

**核心方法剖析**：

#### 3.2.1 `_ensure_agent()` - 确保 Agent 已初始化

```python
def _ensure_agent(self, task: Task, state: WorkflowState):
    """确保 Agent 已初始化且任务匹配"""
    from guide_agent import GuideAgent
    
    # 只有在未初始化或任务变更时才重建
    if self._agent is None or self._current_task is None or self._current_task.id != task.id:
        context = self._build_context(state)
        self._agent = GuideAgent(task, context=context)
        self._current_task = task
```

#### 3.2.2 `_build_context()` - 构建上下文信息

```python
def _build_context(self, state: WorkflowState) -> Dict[str, Any]:
    """从 WorkflowState 构建任务流转上下文"""
    return {
        "skipped_tasks": [...],      # 已跳过的任务
        "completed_tasks": [...],    # 已完成的任务
        "progress": {...},           # 进度信息
        "is_first_after_skip": bool  # 是否跳过后首次对话
    }
```

#### 3.2.3 `invoke()` - 核心执行逻辑

```mermaid
flowchart TB
    Start([invoke 开始]) --> GetTask[获取当前任务]
    GetTask --> CheckTask{任务存在?}
    CheckTask -->|否| Finish1[返回 FINISH]
    CheckTask -->|是| EnsureAgent[确保 Agent 初始化]
    EnsureAgent --> RestoreState[恢复保存的状态]
    RestoreState --> Step[调用 agent.step]
    
    Step --> BuildMsg[构建消息列表]
    BuildMsg --> CheckIntent{检查意图}
    
    CheckIntent -->|BACKTRACK| SwitchTask[返回 SWITCH_TASK]
    CheckIntent -->|正常流程| CheckFinished{is_finished?}
    
    CheckFinished -->|是| Handoff[返回 HANDOFF → editor]
    CheckFinished -->|否| CheckConfirm{is_confirming?}
    
    CheckConfirm -->|是| ReqConfirm[返回 REQUEST_CONFIRM]
    CheckConfirm -->|否| WaitInput[返回 WAIT_INPUT]
```

**状态判断逻辑**（第210-253行）：

```python
# 1. 回溯意图
if decision.intent == "BACKTRACK" and decision.target_section:
    action = AgentAction.SWITCH_TASK
    target_section = decision.target_section
    
# 2. 用户已确认，准备移交 Editor
elif self._agent.is_finished():
    action = AgentAction.HANDOFF
    next_agent = "editor"
    content = self._agent.execution_doc
    
# 3. 等待用户确认草稿
elif self._agent.is_confirming():
    action = AgentAction.REQUEST_CONFIRM
    content = decision.execution_doc
    
# 4. 普通等待用户输入
else:
    action = AgentAction.WAIT_INPUT
    content = decision.reply_to_user
```

#### 3.2.4 `invoke_opening()` - 生成开场白

专用于任务开始时主动向用户展示诊断结果：

```python
def invoke_opening(self, state: WorkflowState) -> AgentOutput:
    """生成任务开场白（无需用户输入）"""
    task = state.get_current_task()
    self._ensure_agent(task, state)
    
    # 调用 generate_opening() 而非 step()
    decision = self._agent.generate_opening()
    
    return AgentOutput(
        action=AgentAction.WAIT_INPUT,  # 开场白后等待用户输入
        content=decision.reply_to_user,
        ...
    )
```

#### 3.2.5 状态持久化

```python
def export_state(self) -> Dict[str, Any]:
    """导出 Agent 状态"""
    if self._agent is None:
        return {}
    
    snapshot = self._agent.export_state()
    return {
        "current_state": snapshot.current_state.value,  # 状态机状态
        "messages": snapshot.messages,                   # 对话历史
        "draft": snapshot.draft,                         # 草稿内容
        "execution_doc": snapshot.execution_doc.model_dump() if ... else None,
        "task_id": self._current_task.id if ... else None
    }

def load_state(self, state: Dict[str, Any]) -> None:
    """恢复 Agent 状态"""
    self._load_from_dict(state)
```

---

### 3.3 EditorAgentAdapter

**职责**：执行简历编辑操作

```python
# 源码位置：backend/agent_adapters.py 第377-489行

class EditorAgentAdapter(BaseAgent):
    def __init__(self):
        from editor_agent import EditorAgent
        self._agent = EditorAgent()
    
    @property
    def name(self) -> str:
        return "editor"
```

**核心执行逻辑**：

```python
def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
    exec_doc = state.current_exec_doc
    if not exec_doc:
        return AgentOutput(action=AgentAction.FINISH, ...)
    
    # 修复：正确捕获生成器返回值
    messages = []
    updated_resume = None
    
    gen = self._agent.execute_doc(exec_doc, state.resume)
    try:
        while True:
            msg = next(gen)
            messages.append(AgentMessage(...))
    except StopIteration as e:
        updated_resume = e.value  # 获取返回的 Resume
    
    # 更新 state 中的 resume
    if updated_resume:
        state.resume = updated_resume
    
    return AgentOutput(
        action=AgentAction.FINISH,
        content=state.resume,
        messages=messages
    )
```

> [!IMPORTANT]
> **生成器返回值捕获**：EditorAgent 的 `execute_doc()` 是一个生成器，其返回值需要通过 `StopIteration.value` 捕获，而非直接 `for` 循环遍历。

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant A as EditorAgentAdapter
    participant E as EditorAgent
    participant S as WorkflowState
    
    O->>A: invoke(input, state)
    A->>S: 获取 exec_doc, resume
    A->>E: execute_doc(exec_doc, resume)
    
    loop 生成器迭代
        E-->>A: yield 消息
        A->>A: 收集消息
    end
    
    E-->>A: StopIteration.value = 更新后的Resume
    A->>S: state.resume = updated_resume
    A-->>O: AgentOutput(FINISH, resume)
```

---

## 4. 适配器与 Orchestrator 的协作

### 4.1 注册 Agent

```python
from agent_adapters import (
    PlanAgentAdapter, 
    GuideAgentAdapter, 
    EditorAgentAdapter,
    create_default_orchestrator
)

# 方式1：手动注册
orchestrator = Orchestrator()
orchestrator.register_agent(PlanAgentAdapter())
orchestrator.register_agent(GuideAgentAdapter())
orchestrator.register_agent(EditorAgentAdapter())

# 方式2：使用工厂函数
orchestrator = create_default_orchestrator()
```

### 4.2 工作流程

```mermaid
flowchart TB
    subgraph Orchestrator
        RA[register_agent]
        RP[run_plan]
        RG[run_guide_step]
        RE[run_editor]
    end
    
    subgraph Adapters
        PA[PlanAgentAdapter]
        GA[GuideAgentAdapter]
        EA[EditorAgentAdapter]
    end
    
    RA --> PA
    RA --> GA
    RA --> EA
    
    RP -->|调用| PA
    PA -->|FINISH + TaskList| RP
    
    RG -->|调用| GA
    GA -->|WAIT_INPUT / REQUEST_CONFIRM| RG
    GA -->|HANDOFF| RE
    
    RE -->|调用| EA
    EA -->|FINISH + Resume| RE
```

### 4.3 完整工作流

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as API层
    participant O as Orchestrator
    participant Plan as PlanAgentAdapter
    participant Guide as GuideAgentAdapter
    participant Editor as EditorAgentAdapter
    
    U->>API: 上传简历 + 意图
    API->>O: run_plan(state, intent)
    O->>Plan: invoke(input, state)
    Plan-->>O: AgentOutput(FINISH, TaskList)
    O-->>API: 返回计划
    
    loop 每个任务
        API->>O: run_guide_step(state, input)
        O->>Guide: invoke_opening(state)
        Guide-->>O: AgentOutput(WAIT_INPUT)
        
        loop 对话循环
            U->>API: 用户输入
            API->>O: run_guide_step(state, input)
            O->>Guide: invoke(input, state)
            Guide-->>O: AgentOutput(action)
            
            alt action = WAIT_INPUT
                O-->>API: 等待更多输入
            else action = REQUEST_CONFIRM
                O-->>API: 显示确认按钮
            else action = HANDOFF
                O->>Editor: invoke(input, state)
                Editor-->>O: AgentOutput(FINISH, Resume)
            end
        end
    end
```

---

## 5. 三个适配器对比

| 特性           | PlanAgentAdapter | GuideAgentAdapter  | EditorAgentAdapter |
| -------------- | ---------------- | ------------------ | ------------------ |
| **状态**       | 无状态           | 有状态（复杂）     | 无状态             |
| **延迟初始化** | 构造时初始化     | 调用时初始化       | 构造时初始化       |
| **流式支持**   | 伪流式           | 伪流式             | 真流式（生成器）   |
| **返回动作**   | 仅 `FINISH`      | 多种动作           | 仅 `FINISH`        |
| **特殊方法**   | -                | `invoke_opening()` | -                  |
| **状态持久化** | 空实现           | 完整实现           | 空实现             |

---

## 6. 代码亮点与设计模式

### 6.1 延迟导入（Lazy Import）

避免循环依赖：

```python
def __init__(self):
    from plan_agent import PlanAgent  # 在需要时才导入
    self._agent = PlanAgent()
```

### 6.2 延迟初始化（Lazy Initialization）

GuideAgentAdapter 只在需要时初始化：

```python
def __init__(self):
    self._agent = None  # 不立即创建
    self._current_task = None

def _ensure_agent(self, task, state):
    if self._agent is None or self._current_task.id != task.id:
        self._agent = GuideAgent(task, context=...)
```

### 6.3 适配器模式（Adapter Pattern）

将不同接口统一：

```mermaid
flowchart LR
    subgraph 原始接口
        A1["PlanAgent.generate_plan()"]
        A2["GuideAgent.step()"]
        A3["EditorAgent.execute_doc()"]
    end
    
    subgraph 适配器
        AD["统一为 invoke()"]
    end
    
    subgraph 统一接口
        B["BaseAgent.invoke()"]
    end
    
    A1 --> AD --> B
    A2 --> AD
    A3 --> AD
```

### 6.4 工厂函数（Factory Function）

提供便捷的创建方式：

```python
def create_default_orchestrator():
    """创建默认配置的编排器"""
    from orchestrator import Orchestrator
    
    orch = Orchestrator()
    orch.register_agent(PlanAgentAdapter())
    orch.register_agent(GuideAgentAdapter())
    orch.register_agent(EditorAgentAdapter())
    
    return orch
```

---

## 7. 总结

```mermaid
mindmap
  root((AgentAdapter))
    设计目标
      最小侵入
      统一协议
      渐进迁移
    三个适配器
      PlanAgentAdapter
        无状态
        生成计划
      GuideAgentAdapter
        有状态
        对话引导
        状态持久化
      EditorAgentAdapter
        无状态
        执行编辑
        流式输出
    核心接口
      invoke
      stream
      export_state
      load_state
    与Orchestrator协作
      register_agent
      统一调度
      路由控制
```

**核心价值**：

1. **解耦**：API 层不需要了解各 Agent 的具体实现
2. **统一**：Orchestrator 用相同方式调度所有 Agent
3. **可扩展**：新增 Agent 只需实现适配器即可接入
4. **可迁移**：未来切换到 LangGraph 只需修改适配器层
