# GuideAgent 状态机设计与流转详解

本文档深入讲解 GuideAgent 的状态机设计哲学、状态流转机制、以及各状态下的行为规范。

---

## 📌 为什么使用状态机？

### 传统对话 AI 的问题

```mermaid
graph LR
    subgraph "❌ 传统方式"
        A["用户消息"] --> B["LLM 推理"]
        B --> C["随机回复"]
        C --> D["无法预测的行为"]
    end
```

**问题**：
- LLM 可能在任何时候跳过步骤
- 对话流程不可控
- 用户体验不一致

### 状态机驱动的优势

```mermaid
graph LR
    subgraph "✅ 状态机方式"
        A["用户消息"] --> B["状态判断"]
        B --> C["受限的动作集"]
        C --> D["可预测的行为"]
        D --> E["规范的流程"]
    end
```

**优势**：
- 每个状态只允许特定的动作
- 流程可控、可追踪
- 用户体验一致

---

## 🔄 状态定义

GuideAgent 使用 4 个核心状态来管理对话流程：

```python
class AgentState(str, Enum):
    DISCOVERY = "DISCOVERY"     # 信息挖掘阶段
    DRAFTING = "DRAFTING"       # 草稿撰写阶段
    CONFIRMING = "CONFIRMING"   # 等待确认阶段
    FINISHED = "FINISHED"       # 任务完成阶段
```

### 状态卡片

```mermaid
graph TB
    subgraph S1["🔍 DISCOVERY"]
        D1["目标：挖掘用户信息"]
        D2["规则：禁止生成草稿"]
        D3["动作：CONTINUE_ASKING / PROPOSE_DRAFT"]
    end
    
    subgraph S2["📝 DRAFTING"]
        E1["目标：撰写和修改草稿"]
        E2["规则：必须展示草稿内容"]
        E3["动作：PROPOSE_DRAFT / REQUEST_CONFIRM"]
    end
    
    subgraph S3["✅ CONFIRMING"]
        F1["目标：等待用户最终确认"]
        F2["规则：草稿已锁定"]
        F3["动作：CONFIRM_FINISH / PROPOSE_DRAFT"]
    end
    
    subgraph S4["🏁 FINISHED"]
        G1["目标：任务已完成"]
        G2["规则：修改已应用到简历"]
        G3["动作：支持 BACKTRACK 回溯"]
    end
```

---

## 🎯 完整状态流转图

```mermaid
stateDiagram-v2
    [*] --> DISCOVERY: 任务初始化
    
    DISCOVERY --> DISCOVERY: CONTINUE_ASKING<br/>继续提问挖掘信息
    DISCOVERY --> DRAFTING: PROPOSE_DRAFT<br/>信息充足，生成草稿
    
    DRAFTING --> DRAFTING: PROPOSE_DRAFT<br/>用户反馈，修改草稿
    DRAFTING --> CONFIRMING: REQUEST_CONFIRM<br/>用户认可，请求确认
    DRAFTING --> DISCOVERY: 需要更多信息
    
    CONFIRMING --> FINISHED: CONFIRM_FINISH<br/>用户确认执行
    CONFIRMING --> DRAFTING: PROPOSE_DRAFT<br/>用户要求修改
    
    FINISHED --> DRAFTING: BACKTRACK<br/>用户要求回溯修改
    FINISHED --> [*]: 任务彻底完成
```

---

## 📊 状态详解

### 1️⃣ DISCOVERY（信息挖掘）

```mermaid
flowchart TB
    subgraph DISCOVERY["DISCOVERY 状态"]
        direction TB
        
        A["接收用户输入"] --> B{"用户回复类型?"}
        
        B -->|"详细回复 >50字"| C["深挖模式<br/>继续追问细节"]
        B -->|"简短回复 10-50字"| D["引导模式<br/>给出选项引导"]
        B -->|"极简回复 <10字"| E["猜测模式<br/>智能推测并验证"]
        
        C --> F{"信息是否充足?"}
        D --> F
        E --> F
        
        F -->|"否"| G["CONTINUE_ASKING<br/>继续停留在 DISCOVERY"]
        F -->|"是"| H["PROPOSE_DRAFT<br/>切换到 DRAFTING"]
    end
```

**System Prompt 注入的规则**：

```
当前状态: DISCOVERY (信息挖掘)
目标: 基于诊断结果，向用户提问以获取必要的信息。
约束: 暂时**不要**提供草稿。专注于理解用户的经历和细节。
可选动作: CONTINUE_ASKING, PROPOSE_DRAFT

📊 智能节奏控制（每次回复前必做判断）：
1️⃣ 用户回复质量评估：详细型/简短型/极简型
2️⃣ 下一步策略选择：深挖/引导/猜测
3️⃣ 话题切换信号：连续简短回复、用户明确结束
4️⃣ 禁止行为：不要一次问多个问题
```

---

### 2️⃣ DRAFTING（草稿撰写）

```mermaid
flowchart TB
    subgraph DRAFTING["DRAFTING 状态"]
        direction TB
        
        A["展示草稿给用户"] --> B{"用户反馈?"}
        
        B -->|"认可草稿<br/>好/可以/行"| C["REQUEST_CONFIRM<br/>切换到 CONFIRMING"]
        B -->|"修改意见<br/>好但是.../再改改"| D["PROPOSE_DRAFT<br/>修改后重新展示"]
        B -->|"指出错误<br/>这不对/搞混了"| E["PROPOSE_DRAFT<br/>修正错误后重新展示"]
        B -->|"补充信息"| F["PROPOSE_DRAFT<br/>融入新信息后更新草稿"]
        
        D --> A
        E --> A
        F --> A
    end
```

**关键判断逻辑**：

| 用户回复           | 判断结果     | 动作            |
| ------------------ | ------------ | --------------- |
| "好"、"可以"、"行" | 认可草稿     | REQUEST_CONFIRM |
| "好，但是..."      | 有修改意见   | PROPOSE_DRAFT   |
| "这不对"、"搞错了" | 指出错误     | PROPOSE_DRAFT   |
| 补充新的信息       | 需要更新草稿 | PROPOSE_DRAFT   |

**草稿展示规范**（首次展示）：
```
我帮你优化了【板块 - 具体条目】的XXX内容，草稿如下：

📝 草稿：
- ...

⚠️ 面试官可能会问：
1. "..."
   → 回答思路：...

这些问题你能hold住吗？
```

**草稿修改说明**（修改后重新展示）：
```
抱歉！我重新整理了一下：
- ❌ 之前错误：将本科课程混入了硕士背景
- ✅ 现在修正：只保留硕士阶段的核心课程

新草稿如下：
...
```

---

### 3️⃣ CONFIRMING（等待确认）

```mermaid
flowchart TB
    subgraph CONFIRMING["CONFIRMING 状态"]
        direction TB
        
        A["用户已看到预览<br/>等待最终确认"] --> B{"用户回复?"}
        
        B -->|"确认/好/没问题"| C["CONFIRM_FINISH<br/>切换到 FINISHED"]
        B -->|"再改改/还要调整"| D["PROPOSE_DRAFT<br/>回退到 DRAFTING"]
        
        C --> E["构建 ExecutionDoc<br/>准备应用修改"]
        D --> F["根据反馈修正草稿"]
    end
```

**语义理解要点**：

| 用户回复                   | 意图     | 动作           |
| -------------------------- | -------- | -------------- |
| "确认"、"没问题"、"就这样" | 同意执行 | CONFIRM_FINISH |
| "再改改"、"还要调整"       | 要求修改 | PROPOSE_DRAFT  |
| 提供具体修改建议           | 要求修改 | PROPOSE_DRAFT  |

---

### 4️⃣ FINISHED（任务完成）

```mermaid
flowchart TB
    subgraph FINISHED["FINISHED 状态"]
        direction TB
        
        A["任务已完成<br/>修改已应用"] --> B{"用户继续发消息?"}
        
        B -->|"不满意/想修改<br/>不对/再改改"| C["intent: BACKTRACK<br/>回退到 DRAFTING"]
        B -->|"想改其他任务<br/>刚才那个XX"| D["intent: BACKTRACK<br/>target_section 指定板块"]
        B -->|"满意/感谢"| E["intent: CONTINUE<br/>友好回应"]
        
        C --> F["重置 execution_doc<br/>切换状态到 DRAFTING"]
        D --> G["返回目标板块信息<br/>供 Orchestrator 处理"]
    end
```

**回溯信号词识别**：

| 信号词类型    | 示例                     | 处理方式                   |
| ------------- | ------------------------ | -------------------------- |
| 时间词        | "刚才"、"之前"、"上面"   | BACKTRACK                  |
| 否定词 + 板块 | "那个xx不对"、"xx还要改" | BACKTRACK + target_section |
| 直接指明板块  | "硕士课程"、"技能部分"   | BACKTRACK + target_section |
| 满意/感谢     | "谢谢"、"好的"、"完成了" | CONTINUE                   |

---

## ⚡ 状态转换代码实现

### step() 方法核心逻辑

```python
def step(self, user_input: str) -> AgentDecision:
    # 1. 追加用户消息
    self.messages.append({"role": "user", "content": user_input})

    # 2. 调用 LLM 获取决策
    decision = self._call_llm()
    
    # 3. 处理回溯意图
    if decision.intent == "BACKTRACK":
        if self.current_state == AgentState.FINISHED:
            self.execution_doc = None
            self.current_state = AgentState.DRAFTING
    
    # 4. 根据 next_action 更新状态
    elif decision.next_action == "CONTINUE_ASKING":
        self.current_state = AgentState.DISCOVERY
        
    elif decision.next_action == "PROPOSE_DRAFT":
        self.current_state = AgentState.DRAFTING
        
    elif decision.next_action == "REQUEST_CONFIRM":
        if self.draft:
            self.execution_doc = self._build_execution_doc()
            self.current_state = AgentState.CONFIRMING
            
    elif decision.next_action == "CONFIRM_FINISH":
        if self.current_state == AgentState.CONFIRMING and self.draft:
            self.current_state = AgentState.FINISHED
    
    # 5. 更新对话历史和草稿
    self.messages.append({"role": "assistant", "content": decision.reply_to_user})
    if decision.draft_content:
        self.draft = decision.draft_content
    
    return decision
```

---

## 🛡️ 状态机保护机制

### 非法状态转换拦截

```mermaid
flowchart TB
    subgraph "状态保护逻辑"
        A["LLM 返回 CONFIRM_FINISH"] --> B{"当前状态?"}
        
        B -->|"CONFIRMING + 有草稿"| C["✅ 允许<br/>切换到 FINISHED"]
        B -->|"DRAFTING + 有草稿"| D["✅ 允许（快速确认）<br/>切换到 FINISHED"]
        B -->|"其他情况"| E["❌ 拦截<br/>强制回到正确状态"]
        
        E --> F{"有草稿?"}
        F -->|"是"| G["回退到 DRAFTING"]
        F -->|"否"| H["回退到 DISCOVERY"]
    end
```

**代码实现**：

```python
elif decision.next_action == "CONFIRM_FINISH":
    # 严格的状态流转检查
    if self.current_state == AgentState.CONFIRMING and self.draft:
        self.current_state = AgentState.FINISHED
        decision.execution_doc = self.execution_doc
    elif self.current_state == AgentState.DRAFTING and self.draft:
        # 允许从 DRAFTING 直接结束（用户快速确认）
        self.execution_doc = self._build_execution_doc()
        self.current_state = AgentState.FINISHED
        decision.execution_doc = self.execution_doc
    else:
        # 如果 LLM 试图跳过流程，强制拉回正确状态
        if self.draft:
            self.current_state = AgentState.DRAFTING
        else:
            self.current_state = AgentState.DISCOVERY
```

---

## 🔗 状态与 Prompt 的动态绑定

每个状态注入不同的 System Prompt 规则：

```mermaid
graph TB
    subgraph "状态 → Prompt 映射"
        S1["DISCOVERY"] --> P1["深挖信息指引<br/>智能节奏控制<br/>禁止生成草稿"]
        
        S2["DRAFTING"] --> P2["草稿修改判断<br/>展示规范<br/>面试可答性检验"]
        
        S3["CONFIRMING"] --> P3["确认/修改判断<br/>语义理解要点"]
        
        S4["FINISHED"] --> P4["回溯意图识别<br/>target_section 提取<br/>友好回应指导"]
    end
```

**这种设计的好处**：

1. **精确控制**：LLM 每次只看到当前状态允许的动作
2. **减少幻觉**：不会在 DISCOVERY 阶段误生成草稿
3. **节省 Token**：不加载无关规则

---

## 📐 设计总结

### 状态机设计原则

| 原则            | 实现                     | 效果               |
| --------------- | ------------------------ | ------------------ |
| **单一职责**    | 每个状态只负责一件事     | 逻辑清晰，易于维护 |
| **显式转换**    | next_action 明确指定目标 | 状态转换可追踪     |
| **防御性编程**  | 非法转换被拦截           | 流程不会失控       |
| **可回溯**      | FINISHED 支持 BACKTRACK  | 用户体验友好       |
| **动态 Prompt** | 每个状态注入专属规则     | LLM 行为受控       |

### 状态机 vs 无状态的对比

| 维度           | 无状态   | 状态机驱动 |
| -------------- | -------- | ---------- |
| 行为可预测性   | ❌ 低     | ✅ 高       |
| 流程可控性     | ❌ 差     | ✅ 强       |
| 调试难度       | ❌ 高     | ✅ 低       |
| 用户体验一致性 | ❌ 不稳定 | ✅ 一致     |
| 实现复杂度     | ✅ 低     | ⚠️ 中等     |

---

## 📚 相关文档

- [GuideAgent 上下文管理机制](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_context_management.md)
- [GuideAgent 逻辑与原理图解](file:///c:/Users/admin/Desktop/ResumeAssistant/learning/guide_agent_logic.md)
- [源码：guide_agent.py](file:///c:/Users/admin/Desktop/ResumeAssistant/backend/guide_agent.py)
