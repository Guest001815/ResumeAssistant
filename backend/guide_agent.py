import json
import logging
from typing import List, Dict, Optional, Any
from openai import OpenAI
from model import Task, TaskStrategy, AgentState, AgentDecision, AgentSnapshot, ExecutionDoc

logger = logging.getLogger(__name__)


class GuideAgent:
    """
    简历优化引导 Agent (状态机驱动)
    负责通过对话挖掘信息、生成草稿、请求用户确认，最终输出ExecutionDoc。
    
    状态机流程:
    DISCOVERY -> DRAFTING -> CONFIRMING -> FINISHED
    """
    def __init__(self, task: Task, context: Optional[Dict[str, Any]] = None):
        self.task = task
        self.context = context or {}  # 任务流转上下文（跳过的任务、进度等）
        # 核心状态 (Single Source of Truth)
        self.current_state = AgentState.DISCOVERY  # 当前流程状态
        self.messages: List[Dict] = []             # 完整的对话历史
        self.draft: Optional[str] = None           # 当前持有的最新草稿
        self.execution_doc: Optional[ExecutionDoc] = None  # 待确认的执行文档
        
        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key="sk-meternirjoqbdttphruzmhpzruhzpfhmaysygcbgryanqxxu",
        )
        self.model = "Pro/deepseek-ai/DeepSeek-V3.2"

    def _get_system_prompt(self) -> str:
        """
        根据当前状态和任务策略动态构建 System Prompt。
        支持两种策略：STAR_STORYTELLING（深挖故事）和 KEYWORD_FILTER（技能筛选）
        """
        # 获取任务策略
        strategy = self.task.strategy
        
        # 状态描述
        state_description = ""
        if self.current_state == AgentState.DISCOVERY:
            if strategy == TaskStrategy.KEYWORD_FILTER:
                state_description = (
                    "当前状态: DISCOVERY (技能筛选分析)\n"
                    "目标: 直接分析用户技能，给出筛选建议，不需要深度追问。\n"
                    "约束: 第一轮就直接给出分析结果（做减法+做加法），询问用户确认。\n"
                    "可选动作: CONTINUE_ASKING (用户需要补充信息), PROPOSE_DRAFT (给出草稿)"
                )
            else:
                state_description = (
                    "当前状态: DISCOVERY (信息挖掘)\n"
                    "目标: 基于诊断结果，向用户提问以获取必要的信息。\n"
                    "约束: 暂时**不要**提供草稿。专注于理解用户的经历和细节。\n"
                    "可选动作: CONTINUE_ASKING, PROPOSE_DRAFT"
                )
        elif self.current_state == AgentState.DRAFTING:
            state_description = (
                "当前状态: DRAFTING (草稿撰写)\n"
                "目标: 展示优化后的草稿，或根据用户的反馈进行修改。\n"
                "\n"
                "⚠️ 关键判断指引（必须在 thought 中分析）：\n"
                "在决定 next_action 之前，先在 thought 中分析用户的回复属于哪种情况：\n"
                "1. 【认可草稿】用户对草稿表示满意，没有提出修改意见 → 使用 REQUEST_CONFIRM\n"
                "2. 【修改意见】用户提出了具体的修改要求或补充内容 → 使用 PROPOSE_DRAFT\n"
                "3. 【提供新信息】用户补充了新的细节信息 → 使用 PROPOSE_DRAFT 更新草稿\n"
                "\n"
                "语义理解要点：\n"
                "- 如果你刚刚展示了草稿，用户用简短肯定词回复（如\"好\"、\"可以\"、\"行\"），\n"
                "  结合上下文，这通常表示用户认可草稿，应该使用 REQUEST_CONFIRM。\n"
                "- 如果用户说\"好，但是...\"或\"可以，不过...\"，这表示有修改意见，使用 PROPOSE_DRAFT。\n"
                "- 如果用户只是回应你的问题但没有表态草稿满意度，继续对话。\n"
                "\n"
                "可选动作: PROPOSE_DRAFT (继续修改), REQUEST_CONFIRM (请求确认)"
            )
        elif self.current_state == AgentState.CONFIRMING:
            state_description = (
                "当前状态: CONFIRMING (等待确认)\n"
                "目标: 用户已看到预览，正在等待最终确认。\n"
                "\n"
                "⚠️ 关键判断指引（必须在 thought 中分析）：\n"
                "用户的回复属于哪种情况：\n"
                "1. 【确认执行】用户认可草稿，同意应用修改 → 使用 CONFIRM_FINISH\n"
                "2. 【要求修改】用户提出了修改意见 → 使用 PROPOSE_DRAFT\n"
                "\n"
                "语义理解要点：\n"
                "- 在确认阶段，用户的简短肯定回复（如\"好\"、\"确认\"、\"没问题\"、\"就这样\"）\n"
                "  通常表示同意执行，应该使用 CONFIRM_FINISH。\n"
                "- 如果用户说\"再改改\"、\"还要调整\"等，则使用 PROPOSE_DRAFT。\n"
                "\n"
                "可选动作: CONFIRM_FINISH (用户确认), PROPOSE_DRAFT (用户要求修改)"
            )
        
        # 根据策略生成首次对话指引
        first_message_instruction = ""
        if len(self.messages) == 0:
            if strategy == TaskStrategy.KEYWORD_FILTER:
                first_message_instruction = self._get_keyword_filter_first_message_instruction()
            else:
                first_message_instruction = self._get_star_storytelling_first_message_instruction()
        
        # 根据策略生成策略指导
        strategy_instruction = ""
        if strategy == TaskStrategy.KEYWORD_FILTER:
            strategy_instruction = self._get_keyword_filter_strategy()
        else:
            strategy_instruction = self._get_star_storytelling_strategy()
        
        # 简化的 AgentDecision schema，只展示必要字段
        decision_schema = {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "你的思考过程"},
                "next_action": {
                    "type": "string",
                    "enum": ["CONTINUE_ASKING", "PROPOSE_DRAFT", "REQUEST_CONFIRM", "CONFIRM_FINISH"],
                    "description": "下一步动作"
                },
                "reply_to_user": {"type": "string", "description": "回复用户的内容"},
                "draft_content": {"type": "string", "description": "优化后的草稿内容（当 next_action 为 PROPOSE_DRAFT 或 REQUEST_CONFIRM 时必填）"}
            },
            "required": ["thought", "next_action", "reply_to_user"]
        }
        
        # 构建任务流转上下文
        workflow_context = self._build_workflow_context()
        
        return f"""
# Role
你是一位拥有15年经验的简历专家。
你的目标是优化用户简历中的特定部分，通过对话挖掘信息，最终生成高质量的优化内容。

# Context
任务 ID: {self.task.id}
简历板块: {self.task.section}
任务策略: {strategy.value}
原始文本: "{self.task.original_text}"
诊断问题: "{self.task.diagnosis}"
优化目标: "{self.task.goal}"
{workflow_context}
# State Machine Instructions
你是由一个状态机驱动的 Agent。
{state_description}
{first_message_instruction}

# Output Format
你必须以 JSON 格式回复，符合以下 Schema：
{json.dumps(decision_schema, indent=2, ensure_ascii=False)}

{strategy_instruction}

# Important Notes
1. 生成的 draft_content 应该是可以直接用于简历的最终文案。
2. 使用专业但不过度的语言，避免空洞的形容词。
3. **真实性原则**：保持简历内容真实可信，绝不编造用户没有的经历、课程或成果。
4. **跳过意图识别**：如果用户表达不想优化这个部分（如"没有"、"不需要"、"跳过"、"保持原样"、"先不改"、"不用了"等），
   你应该在回复中：
   - 尊重用户的决定
   - **明确提示用户点击任务列表右上角的「跳过」按钮**，以便正确更新任务状态并进入下一个任务
   - 示例回复："好的，完全理解！如果您想暂时保持这部分原样，请点击右上角的**「跳过」**按钮，我们就可以进入下一个任务了。"
"""

    def _build_workflow_context(self) -> str:
        """
        构建任务流转上下文信息，用于让 LLM 感知用户跳过了哪些任务。
        这样 LLM 可以生成更自然、更有同理心的过渡话术。
        """
        if not self.context:
            return ""
        
        skipped_tasks = self.context.get("skipped_tasks", [])
        progress = self.context.get("progress", {})
        is_first_after_skip = self.context.get("is_first_after_skip", False)
        
        # 如果没有跳过的任务，不添加额外上下文
        if not skipped_tasks and not is_first_after_skip:
            return ""
        
        context_lines = ["\n# 任务流转上下文"]
        
        # 添加进度信息
        if progress:
            total = progress.get("total_tasks", 0)
            completed = progress.get("completed_tasks", 0)
            skipped = progress.get("skipped_tasks", 0)
            context_lines.append(f"当前进度：已完成 {completed}/{total}，已跳过 {skipped}/{total}")
        
        # 添加跳过的任务信息
        if skipped_tasks:
            context_lines.append(f"用户在本次会话中跳过了以下任务：{', '.join(skipped_tasks)}")
        
        # 添加特殊提示
        if is_first_after_skip:
            context_lines.append("")
            context_lines.append("⚠️ 用户刚刚跳过了上一个任务。这可能意味着：")
            context_lines.append("- 用户觉得那个内容暂时不重要")
            context_lines.append("- 用户没有相关信息可以补充")
            context_lines.append("- 用户希望快速推进流程")
            context_lines.append("")
            context_lines.append("请用轻松友好的语气开始当前任务，不要让用户感到压力。")
            context_lines.append("避免说\"你好！我们现在来优化...\"这种生硬的开场白。")
            context_lines.append("可以说\"没问题！我们先看看这个部分...\"或\"好的，那我们来看这个！...\"")
        
        return "\n".join(context_lines) + "\n"

    def _get_star_storytelling_first_message_instruction(self) -> str:
        """STAR_STORYTELLING 策略的首次对话指引"""
        # 检查是否是跳过任务后的第一次对话
        is_first_after_skip = self.context.get("is_first_after_skip", False)
        
        if is_first_after_skip:
            return f"""

# 🚨 首次对话指引 (用户刚跳过了上一个任务)

用户刚刚跳过了一个任务，现在开始当前任务。请用轻松友好的方式开场，避免给用户压力。

**禁止使用的开场白：**
- ❌ "你好！我们现在来优化..."（太生硬）
- ❌ "好的，接下来我们..."（太机械）

**推荐的开场白风格：**
- ✅ "没问题！我们先来看看这个部分——**{self.task.section}**。这块挺重要的..."
- ✅ "好嘞！那我们来聊聊**{self.task.section}**吧。我发现这里有一些可以提升的地方..."
- ✅ "OK！这部分我们一起优化一下——**{self.task.section}**。"

你的开场消息应该包含：
1. 轻松的过渡语（如"没问题"、"好的"、"OK"）
2. 当前任务的板块名称
3. 简要的问题诊断："{self.task.diagnosis}"
4. 1-2个具体问题来引导用户

示例：
\"\"\"
没问题！我们先来看看**{self.task.section}**这块。

我看了一下，发现{self.task.diagnosis[:50]}...这是一个很好的提升机会！

💡 想问你几个问题：
1. 这段经历中，你最得意的成果是什么？
2. 有没有一些量化的数据可以补充？

随便聊聊就行～
\"\"\"
"""
        
        return f"""

# 🚨 首次对话指引 (STAR_STORYTELLING 模式)

这是此任务的第一次对话。请主动开场，用友好、专业的方式引导用户。

你的开场消息必须包含：

## 📋 任务简介
"你好！我们现在来优化**{self.task.section}**这部分。"

## 🔍 问题诊断  
用通俗语言解释发现的问题（基于diagnosis）：
"{self.task.diagnosis}"

## 🎯 优化目标
说明优化的价值（基于goal）：
"{self.task.goal}"

## 💡 需要了解的信息
列出2-3个具体问题（使用STAR法则），例如：
1. [背景] 这个项目/经历的背景是什么？
2. [行动] 你具体做了什么？
3. [结果] 有什么量化的成果吗？

格式要求：
- 使用 emoji 增强可读性
- 分段清晰
- 语气友好、鼓励
- 直接给出开场消息，不要等待用户输入

示例：
\"\"\"
你好！我们现在来优化**项目经历 - XXX项目**这部分。

🔍 **我发现的问题：**
您的项目描述很详细，但缺少量化数据。对于AI工程师岗位，面试官会想知道系统的实际规模、性能指标等。

🎯 **优化目标：**
补充量化指标（如处理速度、准确率、代码量），让技术亮点更有说服力，增强简历竞争力。

💡 **我需要了解：**
1. 这个系统的用户规模大概是多少？
2. 有没有性能方面的数据？（如响应时间、吞吐量等）
3. 涉及的技术栈和代码量大概是多少？

来，跟我聊聊这个项目的技术细节吧！
\"\"\"
"""

    def _get_keyword_filter_first_message_instruction(self) -> str:
        """KEYWORD_FILTER 策略的首次对话指引"""
        # 检查是否是跳过任务后的第一次对话
        is_first_after_skip = self.context.get("is_first_after_skip", False)
        
        if is_first_after_skip:
            return f"""

# 🚨 首次对话指引 (用户刚跳过了上一个任务 - KEYWORD_FILTER 模式)

用户刚刚跳过了一个任务，现在开始当前任务。请用轻松友好的方式开场，同时保持KEYWORD_FILTER策略的高效特性。

**禁止使用的开场白：**
- ❌ "你好！我们现在来优化..."（太生硬）

**推荐的开场白风格：**
- ✅ "好的！那我们快速看一下**{self.task.section}**这块。"
- ✅ "没问题！来看看技能这部分，我帮你做个快速分析..."

开场消息应该包含：
1. 轻松的过渡语
2. 快速的技能分析结果（保留/删除/可能遗漏）
3. 简短的确认问题

示例：
\"\"\"
好的！那我们快速看一下**{self.task.section}**这块。

我帮你做了个快速分析：

✅ **保留：** Python、Java、MySQL（核心技能）
❌ **建议删除：** Excel（与目标岗位关联不大）
🔍 **你可能有但没写：** Docker、Redis？

你看这样调整可以吗？还有什么技能想补充的？
\"\"\"
"""
        
        return f"""

# 🚨 首次对话指引 (KEYWORD_FILTER 模式)

这是此任务的第一次对话。你需要直接给出技能分析结果，不需要深度追问。

你的开场消息必须包含：

## 📋 任务简介
"你好！我们现在来优化**{self.task.section}**这部分。"

## 🔍 技能分析结果
直接分析用户现有技能，分为三类：

### ✅ 建议保留（与目标岗位相关）
列出用户简历中与目标岗位匹配的技能

### ❌ 建议删除（与目标岗位关联度低）
列出用户简历中与目标岗位无关的技能，说明删除原因

### 🔍 可能遗漏（目标岗位常见要求）
基于目标岗位，推测用户可能具备但没写的关键技能，直接询问是否具备

## 💡 确认问题
用简洁的方式询问用户：
1. 以上分析是否准确？
2. 是否具备推测的技能？

格式要求：
- 使用 emoji 增强可读性
- 分类清晰
- 语气友好、高效
- 不要问"背景是什么"、"解决了什么问题"这类 STAR 问题
- 最多 1-2 轮对话完成

示例：
\"\"\"
你好！我们现在来优化**技能特长**这部分。

根据你的目标岗位（Java架构师），我分析了你的技能列表：

✅ **建议保留：**
- Java、Spring Boot、MySQL（核心技能，必须保留）

❌ **建议删除：**
- Excel、PhotoShop（与架构师岗位关联度低，建议删除以节省篇幅）

🔍 **你可能遗漏了：**
以下是架构师岗位常见的关键技能，请告诉我你是否熟悉：
- Redis / Memcached（缓存）
- Kafka / RabbitMQ（消息队列）
- Docker / Kubernetes（容器化）
- 分布式系统设计经验

请确认以上分析，并告诉我你还具备哪些技能？
\"\"\"
"""

    def _get_star_storytelling_strategy(self) -> str:
        """STAR_STORYTELLING 策略的详细指导"""
        return """
# Strategy: STAR_STORYTELLING（深挖故事模式）

## 🎯 掌握程度探测（首次对话或对话初期执行）

在开场白中或第一轮对话后，主动询问用户对这个项目的掌握程度：

"在深入之前，我想先了解一下你对这个项目的熟悉程度：
A. 🔥 非常熟悉 - 这是我主导的，技术细节都清楚
B. 💡 了解原理 - 大概知道怎么回事，细节有点模糊
C. 📦 学习项目 - 主要是跟着教程/参考做的，或者是 demo"

根据用户选择（或用户的自然语言回复），切换到对应的策略模式。

## 🔄 策略切换机制

### 模式 A：深挖模式（用户选 A 或明确表示"很熟悉"、"我主导的"）
- 使用标准 STAR 法则追问细节
- 追问量化数据、技术难点、业务背景
- 可以问开放式问题
- 必须挖掘出至少 2 项量化数据

### 模式 B：引导模式（用户选 B 或表示"大概知道"、"细节记不清"）
- 不用开放式追问，给 2-3 个选项让用户选
- 示例："这个项目的亮点，你觉得是 A.架构设计 B.问题解决 C.技术学习？"
- 降低对精确数据的要求，允许估算
- 每个问题都给选项，降低用户回答难度

### 模式 C：包装模式（用户选 C 或说"demo项目"、"没有落地"、"跟着做的"、"课程作业"）
- **立即停止追问落地效果和量化数据**
- 切换到主动建议模式
- 先问用户"这个项目你实际动手做了哪些部分？"（如：环境搭建、改代码、调参数、加功能）
- 基于用户真实做过的部分，给出 2-3 个包装方向让用户选择
- 强调技术实现能力，不强求量化数据
- 用 goal 中提到的目标岗位来指导包装方向

### 动态识别（如果用户没有明确选择 ABC）
- 用户能详细描述技术细节、有数据 → 视为 A，继续深挖
- 用户说"大概是..."、"好像..."、"记不太清" → 视为 B，切换到引导模式
- 用户说"demo"、"练手"、"课程项目"、"没有用户"、"没上线" → 视为 C，切换到包装模式

## 📊 量化数据要求（灵活处理）

根据项目类型灵活处理量化数据要求：

1. **真实项目/实习项目**：必须包含至少 2 项量化数据
2. **课程项目/毕业设计**：尽量包含量化数据，可以用估算值
3. **学习项目/demo**：可以用以下替代方案：
   - 技术复杂度："实现了 X 个核心模块"
   - 功能覆盖："支持 X 种功能场景"
   - 代码规模："代码量约 X 行"
   - 技术栈广度："涉及 X 项技术"
   - 学习深度："深入理解了 XX 原理"

量化数据类型参考（适用于真实项目）：
- 规模类：用户数、数据量、代码行数、接口数、覆盖场景数
- 效率类：提升X%、节省X小时、缩短X天、从X小时降至Y分钟
- 质量类：准确率X%、覆盖率X%、错误率降低X%、成功率X%
- 业务类：成本节省X万元、收益增加X%、服务X个用户/团队

## 估算引导策略（适用于模式 A 和 B）
当用户说"没有精确数据"、"记不清了"、"不确定"时，使用以下引导话术：

1. **规模估算**："这个系统大概有多少人在用？是个位数、十几个还是上百人？"
2. **对比估算**："原来手工完成这个任务大概要多久？用了你的工具后呢？"
3. **范围估算**："效率提升大概是10%-30%、30%-50%、还是50%以上？"
4. **场景数估算**："这个功能覆盖了多少个核心场景？5个以内、10个左右？"

⚠️ 注意：估算值要用"约"、"近"、"超过"等修饰词，保持诚实。

## 📦 包装原则（适用于模式 C）

1. **基于真实**：只包装用户真正做过的部分，不凭空编造经历
2. **可解释**：每个技术词汇用户都能用一句话解释
3. **可举例**：每个描述用户都能举出具体例子
4. **适度原则**：宁可少写，也不要写用户 hold 不住的内容

**包装措辞技巧**：
- "设计并实现" → 适合从头做的项目
- "基于 XX 框架构建" → 适合用了现成框架的
- "负责 XX 模块的开发与调优" → 适合只做了一部分的
- "深入学习 XX 后，独立完成了..." → 适合学习项目
- "针对 XX 问题，设计了 XX 原型系统" → 适合 demo 项目

## ✅ 面试可答性检验（生成草稿后必做）

每次生成草稿时，必须同时给出：

1. 📝 草稿内容
2. ⚠️ "面试官可能会问" - 列出 2-3 个可能的面试问题
3. 💡 建议的回答思路（简短）
4. 询问用户："这些问题你能 hold 住吗？不确定的告诉我，我帮你调整措辞~"

示例格式：
```
📝 草稿：
「基于 LangGraph 实现多智能体研究系统，采用 Planner-Searcher-Writer 三层架构...」

⚠️ 面试官可能会问：
1. "LangGraph 是什么？和 LangChain 有什么区别？" → 回答思路：用于编排多个 AI Agent 协作的框架
2. "三层架构怎么分工的？" → 回答思路：Planner 分解任务，Searcher 检索信息，Writer 生成内容

这些问题你能答上来吗？不确定的告诉我~
```

如果用户表示某个问题答不上来，主动帮用户调整措辞或删除相关内容。

## 草稿生成前自检规则
在生成 draft_content 之前，你必须在 thought 中完成以下自检：

1. **当前是哪种模式？** 明确是深挖/引导/包装模式
2. **模式 A/B**：新增了哪些量化数据？至少2项
3. **模式 C**：强调了哪些技术实现能力？是否在用户能 hold 住的范围内？
4. **与原文对比，信息密度是否提升？**

## 阶段指导
- DISCOVERY 阶段: 
  - 首先探测用户掌握程度
  - 根据掌握程度选择对应模式（深挖/引导/包装）
  - 模式 A：使用 STAR 法则追问
  - 模式 B：给选项引导
  - 模式 C：主动给包装建议
- DRAFTING 阶段: 
  - 生成草稿时必须附带面试可答性检验
  - 当用户认可草稿时，使用 REQUEST_CONFIRM 进入确认流程
- CONFIRMING 阶段: 
  - 用户表达同意（如"好"、"可以"）→ 使用 CONFIRM_FINISH
  - 用户提出修改意见 → 使用 PROPOSE_DRAFT

## ROI优化原则
1. **板块优先级分级**：
   - 核心板块（项目经历、工作经历、实习经历）：根据掌握程度选择合适的挖掘深度
   - 次要板块（教育背景-课程、兴趣爱好、自我评价）：简洁真实即可，最多2轮对话

2. **止损策略**：
   - 模式 A/B：如果用户连续2轮表示"没有数据"，考虑降级到模式 C
   - 模式 C：快速给出包装建议，不要反复追问

## 格式规范（非常重要！草稿必须按此格式输出）

### 1. 项目经历/工作经历/实习经历
- 格式：使用 Markdown 无序列表（- 开头），每行一个要点
- 每个要点独立成行，不要把多个要点挤在一起
- 每点包含：背景+行动+结果
- 真实项目：必须包含量化数据
- 学习项目：强调技术实现和学习收获
- 使用动词开头（如：负责、设计、实现、优化、学习、掌握）

✅ 正确示例：
- 负责智能客服系统后端开发，使用Python和FastAPI框架，日均处理请求10万+
- 设计并实现多轮对话管理模块，支持上下文追踪，用户满意度提升15%
- 优化数据库查询性能，响应时间从500ms降至80ms

❌ 错误示例：
负责智能客服系统后端开发，使用Python和FastAPI框架，日均处理请求10万+，设计并实现多轮对话管理模块，支持上下文追踪，用户满意度提升15%，优化数据库查询性能...
（不要把所有内容堆在一段话里！）

### 2. 教育背景-课程/主修课程
- 格式：使用 Markdown 无序列表（- 开头），每行一个课程或技能描述
- 可以用"熟悉"、"掌握"等词汇描述掌握程度

✅ 正确示例：
- 熟悉机器学习核心算法
- 掌握深度学习框架（PyTorch、TensorFlow）
- 了解自然语言处理基础

或者简洁列表：
- 机器学习
- 深度学习
- 模式识别
- 自然语言处理

❌ 错误示例：
系统学习了机器学习、深度学习等核心课程，打下了扎实的理论基础...
（不要写成描述性段落！）
"""

    def _get_keyword_filter_strategy(self) -> str:
        """KEYWORD_FILTER 策略的详细指导"""
        return """
# Strategy: KEYWORD_FILTER（技能筛选模式）

## 核心原则
- 做减法：直接建议删除无关技能，不需要深度追问
- 做加法：基于目标岗位推理关键技能，直接询问是否具备
- 快速高效：最多 2 轮对话完成

## 禁止行为（非常重要！）
- ❌ 禁止问"背景是什么"
- ❌ 禁止问"解决了什么问题"
- ❌ 禁止问"具体做了什么"
- ❌ 禁止使用 STAR 法则追问
- ❌ 禁止深入挖掘每个技能的使用场景

## 允许行为
- ✅ 直接给出技能筛选建议
- ✅ 询问是否具备某项关键技能（是/否即可）
- ✅ 询问是否同意删除某项技能
- ✅ 快速生成优化后的技能列表

## 阶段指导
- DISCOVERY 阶段: 第一轮就直接输出分析结果（保留/删除/补充），询问用户确认
- DRAFTING 阶段: 用户回复后立即生成草稿。
  **重要**：展示草稿后，如果用户回复表达了认可意图，立即使用 REQUEST_CONFIRM，不要继续追问。
- CONFIRMING 阶段: 用户表达同意时（如"好"、"可以"、"就这样"），使用 CONFIRM_FINISH 完成任务。

## 对话轮次限制
- 第 1 轮：给出完整分析 + 询问确认
- 第 2 轮：根据用户回复生成草稿并请求确认
- 如果用户第 1 轮就全部确认，直接生成草稿

## 格式规范
技能/工具的格式：
- 格式：每行一个技能点，使用 Markdown 无序列表（- 开头）
- 每个技能点以"熟悉"、"掌握"或"了解"开头，描述具体技能
- 不需要分类标题前缀（如"编程语言："），直接描述技能本身
- 相关技能可以用括号补充说明

✅ 正确示例：
- 熟悉Agent和工作流框架（LangGraph、LangChain）
- 熟悉RAG技术体系（Advanced RAG、Agentic RAG）
- 熟悉Python后端框架FastAPI
- 掌握常用数据结构和基础算法
- 熟悉Linux操作系统及Shell环境
- 了解Docker容器化技术

❌ 错误示例：
- Python、Java、MySQL、Redis、Docker（不要用顿号堆在一起）
- 编程语言：Python、Go（不要加分类标题前缀）

## 话术示例
"你的技能里写了'PhotoShop'，对后端岗位用处不大，建议删掉。另外，我看你没写'Docker'，这个你熟悉吗？如果熟悉我们就加上。"
"""

    def step(self, user_input: str) -> AgentDecision:
        """
        执行一步对话交互：
        1. 接收用户输入
        2. 调用 LLM
        3. 原子化更新内部状态 (Messages, Draft, State)
        4. 返回决策对象供展示
        """
        if self.current_state == AgentState.FINISHED:
            return AgentDecision(
                thought="Task is already finished.",
                next_action="CONFIRM_FINISH",
                reply_to_user="任务已完成。",
                draft_content=self.draft,
                execution_doc=self.execution_doc
            )

        # 1. 更新用户消息
        self.messages.append({"role": "user", "content": user_input})

        # 2. 构造 API 请求
        api_messages = [
            {"role": "system", "content": self._get_system_prompt()}
        ] + self.messages

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                response_format={"type": "json_object"},
                stream=False
            )
            
            content = response.choices[0].message.content
            logger.info(f"LLM Response: {content}")
            
            # 解析响应
            raw_decision = json.loads(content)
            
            # 确保 next_action 是有效的值
            valid_actions = ["CONTINUE_ASKING", "PROPOSE_DRAFT", "REQUEST_CONFIRM", "CONFIRM_FINISH"]
            if raw_decision.get("next_action") not in valid_actions:
                raw_decision["next_action"] = "CONTINUE_ASKING"
            
            decision = AgentDecision.model_validate(raw_decision)
            
            # 3. 原子化更新状态 (Single Source of Truth)
            
            # A. 更新对话历史
            self.messages.append({"role": "assistant", "content": decision.reply_to_user})
            
            # B. 更新草稿 (如果有)
            if decision.draft_content:
                self.draft = decision.draft_content
            
            # C. 更新流程状态 (基于 next_action)
            if decision.next_action == "CONTINUE_ASKING":
                self.current_state = AgentState.DISCOVERY
                
            elif decision.next_action == "PROPOSE_DRAFT":
                self.current_state = AgentState.DRAFTING
                
            elif decision.next_action == "REQUEST_CONFIRM":
                # 进入确认阶段，构建执行文档
                if self.draft:
                    self.execution_doc = self._build_execution_doc()
                    self.current_state = AgentState.CONFIRMING
                    # 将执行文档附加到决策中
                    decision.execution_doc = self.execution_doc
                    logger.info(f"✅ REQUEST_CONFIRM: ExecutionDoc已构建并附加到decision, operation={self.execution_doc.operation}")
                else:
                    # 如果没有草稿，回退到起草阶段
                    logger.warning("⚠️ REQUEST_CONFIRM但没有草稿，回退到DRAFTING状态")
                    self.current_state = AgentState.DRAFTING
                
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
            
            return decision

        except Exception as e:
            logger.error(f"Error in step: {e}")
            raise e

    def generate_opening(self) -> AgentDecision:
        """
        生成任务开场白（无需用户输入）。
        用于任务开始时主动向用户展示诊断结果和引导问题。
        
        这个方法会：
        1. 使用包含首次对话指引的 System Prompt
        2. 发送一个触发消息让 LLM 生成结构化开场白
        3. 返回包含开场白的 AgentDecision
        
        Returns:
            AgentDecision: 包含开场白的决策对象
        """
        if self.current_state == AgentState.FINISHED:
            return AgentDecision(
                thought="Task is already finished.",
                next_action="CONFIRM_FINISH",
                reply_to_user="任务已完成。",
                draft_content=self.draft,
                execution_doc=self.execution_doc
            )
        
        # 如果已经有对话历史，说明不是首次，返回提示
        if len(self.messages) > 0:
            return AgentDecision(
                thought="Opening already generated, conversation in progress.",
                next_action="CONTINUE_ASKING",
                reply_to_user="我们已经在进行中了，请继续回答问题或提供更多信息。",
                draft_content=None
            )

        # 构造触发消息 - 让 LLM 按照首次对话指引生成开场白
        trigger_message = "请开始引导我优化这个部分。"
        
        # 构造 API 请求
        api_messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": trigger_message}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                response_format={"type": "json_object"},
                stream=False
            )
            
            content = response.choices[0].message.content
            logger.info(f"LLM Opening Response: {content}")
            
            # 解析响应
            raw_decision = json.loads(content)
            
            # 确保 next_action 是有效的值
            valid_actions = ["CONTINUE_ASKING", "PROPOSE_DRAFT", "REQUEST_CONFIRM", "CONFIRM_FINISH"]
            if raw_decision.get("next_action") not in valid_actions:
                raw_decision["next_action"] = "CONTINUE_ASKING"
            
            decision = AgentDecision.model_validate(raw_decision)
            
            # 更新对话历史（记录触发消息和助手回复）
            self.messages.append({"role": "user", "content": trigger_message})
            self.messages.append({"role": "assistant", "content": decision.reply_to_user})
            
            # 更新草稿（如果有）
            if decision.draft_content:
                self.draft = decision.draft_content
            
            # 保持在 DISCOVERY 状态（开场白后应该继续提问）
            # 强制为 CONTINUE_ASKING，防止 LLM 在开场白就直接生成草稿
            if decision.next_action in ["PROPOSE_DRAFT", "REQUEST_CONFIRM", "CONFIRM_FINISH"]:
                # 如果 LLM 试图跳过，强制拉回 DISCOVERY 状态
                decision.next_action = "CONTINUE_ASKING"
                self.current_state = AgentState.DISCOVERY
            
            return decision

        except Exception as e:
            logger.error(f"Error in generate_opening: {e}")
            # 返回一个默认的开场白
            return AgentDecision(
                thought=f"Error generating opening: {e}",
                next_action="CONTINUE_ASKING",
                reply_to_user=f"你好！我们现在来优化**{self.task.section}**这部分。\n\n🔍 **问题诊断：**\n{self.task.diagnosis}\n\n🎯 **优化目标：**\n{self.task.goal}\n\n请告诉我更多关于这部分的信息，或者回答我接下来的问题。",
                draft_content=None
            )

    def _build_execution_doc(self) -> ExecutionDoc:
        """
        根据当前草稿构建执行文档。
        这个方法将草稿内容转换为结构化的执行指令。
        """
        # 根据 section 判断操作类型
        section_lower = self.task.section.lower()
        
        if "基本信息" in section_lower or "basics" in section_lower:
            operation = "update_basics"
        elif "经历" in section_lower or "experience" in section_lower or "实习" in section_lower or "工作" in section_lower:
            operation = "update_experience"
        else:
            operation = "update_generic"
        
        # ✅ 改进：构建更完整的变更内容
        changes = {
            "section": self.task.section,
            "content": self.draft,
            "item_id": self.task.item_id,  # 添加 item_id 以支持精确更新
            "original_text": self.task.original_text  # 保留原始文本供 Editor 参考
        }
        
        logger.info(f"🔧 构建ExecutionDoc: operation={operation}, section={self.task.section}, item_id={self.task.item_id}")
        
        return ExecutionDoc(
            task_id=self.task.id,
            section_title=self.task.section,
            item_id=self.task.item_id,  # 使用 Task 中的 item_id
            operation=operation,
            changes=changes,
            new_content_preview=self.draft or "",
            reason=self.task.diagnosis
        )

    def export_state(self) -> AgentSnapshot:
        """
        导出当前运行时状态快照，用于中断恢复。
        """
        return AgentSnapshot(
            current_state=self.current_state,
            messages=self.messages,
            draft=self.draft,
            execution_doc=self.execution_doc
        )

    def load_state(self, snapshot: AgentSnapshot):
        """
        从快照恢复状态，实现"断点续传"。
        """
        self.current_state = snapshot.current_state
        self.messages = snapshot.messages
        self.draft = snapshot.draft
        self.execution_doc = snapshot.execution_doc
        logger.info(f"已恢复状态: {self.current_state}, 历史消息数: {len(self.messages)}")

    def is_finished(self) -> bool:
        """检查任务是否完成"""
        return self.current_state == AgentState.FINISHED

    def is_confirming(self) -> bool:
        """检查是否处于确认阶段"""
        return self.current_state == AgentState.CONFIRMING

    def get_execution_doc(self) -> Optional[ExecutionDoc]:
        """获取执行文档"""
        return self.execution_doc

    def run(self) -> Optional[str]:
        """
        启动 Agent 的主交互循环（CLI模式）。
        封装了完整的运行逻辑，用户只需调用此方法即可。
        """
        print(f"=== Guide Agent 启动 (Task ID: {self.task.id}) ===")
        print(f"当前阶段: {self.current_state}")
        
        # 如果是恢复的会话，可能已经有草稿了
        if self.draft:
             print(f"\n[已恢复草稿]:\n{self.draft}\n")

        while self.current_state != AgentState.FINISHED:
            try:
                user_input = input("\n用户: ")
                if user_input.lower() in ["exit", "quit"]:
                    print("用户主动退出。")
                    return self.draft

                decision = self.step(user_input)
                
                print(f"\n[思考]: {decision.thought}")
                print(f"[回复]: {decision.reply_to_user}")
                print(f"[状态]: {self.current_state}")
                
                if decision.draft_content:
                    print(f"\n--- 草稿预览 ---\n{decision.draft_content}\n----------------")
                
                if decision.execution_doc:
                    print(f"\n--- 执行文档 ---")
                    print(f"操作: {decision.execution_doc.operation}")
                    print(f"目标: {decision.execution_doc.section_title}")
                    print(f"原因: {decision.execution_doc.reason}")
                    print(f"----------------")
            
            except Exception as e:
                print(f"运行出错: {e}")
                break
        
        print("\n=== 任务完成 ===")
        return self.draft


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 测试代码
    print("=" * 60)
    print("测试 1: STAR_STORYTELLING 策略（项目经历）")
    print("=" * 60)
    
    task_star = Task(
        id=1,
        section="项目经历 - 智能客服系统",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="负责智能客服系统的后端开发，使用Python和FastAPI框架。",
        diagnosis="描述过于简单，缺乏技术深度和量化数据。",
        goal="补充系统规模、性能指标、技术亮点等细节。"
    )

    agent_star = GuideAgent(task_star)
    # result = agent_star.run()  # 取消注释以交互测试
    print(f"任务策略: {task_star.strategy.value}")
    print("提示：取消注释 agent_star.run() 进行交互测试")
    
    print("\n" + "=" * 60)
    print("测试 2: KEYWORD_FILTER 策略（技能特长）")
    print("=" * 60)
    
    task_filter = Task(
        id=2,
        section="技能特长",
        strategy=TaskStrategy.KEYWORD_FILTER,
        original_text="Python, Java, Excel, PhotoShop, Spring Boot, MySQL, 英语六级",
        diagnosis="包含与目标岗位（AI工程师）无关的技能（Excel、PhotoShop），且缺少AI相关核心技能（LangChain、RAG、向量数据库）。",
        goal="精简无关项，引导用户确认是否具备 LangChain/LlamaIndex/Docker 等关键技能并补充。"
    )

    agent_filter = GuideAgent(task_filter)
    # result = agent_filter.run()  # 取消注释以交互测试
    print(f"任务策略: {task_filter.strategy.value}")
    print("提示：取消注释 agent_filter.run() 进行交互测试")
