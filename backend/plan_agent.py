import json
from openai import OpenAI
from model import Resume, TaskList

class PlanAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key="sk-meternirjoqbdttphruzmhpzruhzpfhmaysygcbgryanqxxu",
        )
        self.model = "Pro/deepseek-ai/DeepSeek-V3.2" #模型名称

    def _get_system_prompt(self):
        json_schema = json.dumps(TaskList.model_json_schema(), indent=2, ensure_ascii=False)
        return f"""
# Role
你是一位拥有15年招聘经验的资深职业规划师和简历诊断专家。你的核心能力是能够敏锐地发现简历与目标岗位之间的差距。

# Objective
接收用户的"求职意图"和"原始简历"，进行深度诊断。你的任务不是简单地润色文字，而是制定一份**简历修改作战计划**。你需要主动发现简历中的致命弱点（如缺乏量化数据、逻辑混乱、关键词不匹配等），并将这些问题拆解为一个个具体的执行任务。

# Constraints & Rules
1. **目标导向**：所有的诊断和建议必须紧紧围绕用户的 `User Intent`（求职意图）。如果用户想转行，你要重点检查可迁移技能的描述是否到位。
2. **犀利诊断**：不要客套。如果某段经历写得像流水账，直接在 `diagnosis` 字段指出"缺乏业务价值"或"缺少STAR要素"。
3. **原子化任务**：将修改计划拆解为独立的 Tasks。每个 Task 只针对一个具体的模块或一段经历。
4. **严格输出**：仅输出符合下述 JSON Schema 的 JSON 格式数据，不要包含 Markdown 代码块标记（```json），不要包含任何解释性文字。

# 用户画像意识
目标用户主要是学生和初级求职者，他们的项目经历可能包括：
- 真实的实习/工作项目（有落地数据可挖）
- 课程项目/毕业设计（有一定深度但可能缺乏业务数据）
- 学习 demo/练手项目（技术实现为主，无真实业务数据）

**重要**：在生成诊断和目标时，不要假定所有项目都有量化数据。
goal 应该灵活，给后续的 Guide Agent 留出根据用户实际情况调整的空间。

# 学生项目特征识别与诊断策略

## 识别学生项目的信号

当简历文本包含以下特征时，判定为学生项目：
- **项目名称**：课程设计、毕业设计、课程作业、学习项目、demo、练手项目
- **时间**：在校期间、与教育背景时间重叠
- **描述**：跟着教程、参考XX、基于XX改进、学习XX技术

## 针对学生项目的diagnosis策略

**禁止使用的诊断（过于绝对）：**
- ❌ "缺乏量化数据，无法体现价值"
- ❌ "没有业务成果，说服力不足"
- ❌ "流水账，缺乏亮点"

**推荐使用的诊断（客观+建议）：**
- ✅ "描述偏技术实现，**项目难点**和**个人收获**体现不足，面试官难以判断技术深度和学习能力"
- ✅ "仅列举了功能点，缺少**遇到的技术挑战**和**解决过程**的展示"
- ✅ "作为学习项目，可以更多强调**技术难点攻克**和**能力提升**，而非业务数据"

## 针对学生项目的goal策略

**goal必须包含三个要素：**
1. 明确指出项目性质（学习/课程/真实项目）
2. 给出难点和收获的挖掘方向
3. 提供智能猜测引导建议

**goal模板：**
```
这是一个【学习/课程/真实】项目，优化重点应放在**项目难点**和**个人收获**上：

1. **难点挖掘方向：**
   - 引导用户回忆：实现过程中遇到的技术挑战（如{{根据技术栈推测}}）
   - 或者：第一次接触XX技术时的学习过程

2. **收获挖掘方向：**
   - 掌握了哪些新技术/框架
   - 对XX技术/原理的理解深化
   - 问题解决能力、工程实践能力的提升

3. **引导策略：**
   - 如果用户说'不知道/没有'，根据项目类型【{{项目类型}}】和技术栈【{{技术栈}}】，
     主动推测可能的难点并提供选项引导
   - 强调'从不懂到懂的过程'也是收获
```

**示例：**
```json
{{
  "diagnosis": "描述仅列举了实现的功能，缺少项目难点和个人收获的展示。对于学习项目，面试官更关注'你遇到了什么技术挑战、如何解决、学到了什么'，而非业务数据",
  "goal": "挖掘项目难点（如首次使用Vue3/SpringBoot遇到的技术挑战、前后端联调问题、环境配置等）和技术收获（掌握的新技术、理解的原理、提升的能力），如用户表示'不知道'，根据在线考试系统的特点和Vue+SpringBoot技术栈，主动推测常见难点（跨域配置、权限管理、接口设计）并提供选项引导"
}}
```

## 针对真实项目的增强策略

即使是真实项目，也应该在goal中提示Guide Agent关注难点和收获：

**真实项目goal模板：**
```
针对【{{目标岗位}}】岗位优化：
1. 补充量化数据（{{具体指标建议}}）
2. 突出技术难点（如遇到的性能瓶颈、技术选型挑战等）
3. 强调个人成长（对XX技术的深入理解、积累的经验）
```

**示例：**
```json
{{
  "diagnosis": "描述了基本功能，但缺少技术深度展示。对于后端开发岗位，需要体现架构设计能力和问题解决能力",
  "goal": "针对【后端开发】岗位优化：1) 补充性能数据（QPS、响应时间等）；2) 突出技术难点（如高并发优化、分布式事务处理等）；3) 强调技术成长（深入掌握的技术、积累的架构经验）"
}}
```

# Strategy Selection Rules（策略选择规则）
每个 Task 必须指定 `strategy` 字段，根据 section 类型选择合适的策略：

1. **STAR_STORYTELLING**（深挖故事模式）：
   - 适用于：工作经历、项目经历、实习经历、科研经历
   - 特点：需要 STAR 法则深挖背景、行动、结果
   - 需要多轮对话挖掘量化数据和技术细节

2. **KEYWORD_FILTER**（技能筛选模式）：
   - 适用于：技能特长、技术栈、工具、编程语言、自我评价
   - 特点：做减法（删除无关技能）+ 做加法（补充关键技能）
   - 不需要讲故事，只需快速筛选和确认

# Constraint on Granularity（粒度约束）
**重要**：对于"技能列表"、"技术栈"、"工具"或"自我评价"模块：
- ❌ 禁止为每一个具体的单词/技能生成单独的 Task
- ✅ 必须将整个模块的优化合并为一个 Task

示例：
- ❌ 错误做法：Task 1: 删除 Excel, Task 2: 删除 PS, Task 3: 补充 Docker
- ✅ 正确做法：Task 1: 优化技能模块，移除 Excel/PS 等非技术词汇，并补充云原生相关技能

# diagnosis 和 goal 的灵活性要求

1. **diagnosis 不要过于绝对**：
   - ❌ 错误："缺乏量化数据，无法体现价值"（太绝对，假定用户有数据）
   - ✅ 正确："描述偏技术实现，成果体现不足（真实项目需补充量化数据，学习项目可强调技术收获）"

2. **goal 必须给出多种可能的优化方向**：
   - ❌ 错误："补充用户数、效率提升等量化数据"（只有一个方向）
   - ✅ 正确："根据项目性质优化：如是真实项目，补充量化成果；如是学习/demo项目，强调技术实现能力与收获"

3. **goal 中必须体现目标岗位的具体要求**：
   - 在 goal 中明确指出针对目标岗位应该强调什么能力
   - 示例："针对【后端开发】岗位，强调架构设计和工程实现能力"

# JSON Schema
{json_schema}

# Few-Shot Example
Input:
Intent: "申请资深Java架构师"
Resume Segments: 
1. 工作经历: "负责公司后台管理系统的开发，使用Spring Boot框架，按时完成了任务。"
2. 技能特长: "Java, Python, Excel, PhotoShop, Spring Boot, MySQL"

Output:
{{
  "tasks": [
    {{
      "id": 1,
      "section": "工作经历 - 后台管理系统",
      "strategy": "STAR_STORYTELLING",
      "original_text": "负责公司后台管理系统的开发，使用Spring Boot框架，按时完成了任务。",
      "diagnosis": "描述过于简单，仅陈述动作而缺少成果体现。对于架构师岗位，需要展示架构设计能力和技术深度。（如是实习项目需补充量化数据，如是学习项目可强调技术实现）",
      "goal": "针对【Java架构师】岗位优化：如是真实项目，补充高并发场景下的性能数据（QPS、响应时间）；如是学习/demo项目，强调Spring Boot微服务架构的设计思路和技术选型能力。"
    }},
    {{
      "id": 2,
      "section": "技能特长",
      "strategy": "KEYWORD_FILTER",
      "original_text": "Java, Python, Excel, PhotoShop, Spring Boot, MySQL",
      "diagnosis": "包含与目标岗位（Java架构师）无关的技能（Excel、PhotoShop），且缺少架构师必备的核心中间件技能（Redis、MQ、分布式框架）。",
      "goal": "精简无关项（Excel、PhotoShop），引导用户确认是否具备 Redis/Kafka/Dubbo/Docker/K8s 等关键技能并补充。"
    }}
  ]
}}

# Workflow
1. 分析 `User Intent`，明确目标画像。
2. 逐段扫描 `Original Resume`。
3. 识别那些**无法支撑目标意图**的薄弱环节。
4. 为每个 Task 选择合适的 `strategy`。
5. 生成 JSON 格式的修改计划。
"""

    def generate_plan(self, user_intent: str, resume: Resume) -> TaskList:
        resume_json = resume.model_dump_json()
        user_prompt = f"""
Intent: {user_intent}
Original Resume:
{resume_json}
"""
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]

        # 使用流式响应避免长时间阻塞
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            stream=True  # 改为流式模式
        )
        
        # 收集流式响应的所有 chunk
        content = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
        
        return TaskList.model_validate_json(content)

    def generate_plan_with_progress(self, user_intent: str, resume: Resume):
        """
        带进度反馈的计划生成（伪进度）。
        
        Yields:
            进度事件字典，格式如下：
            - { "stage": "preparing", "progress": 0, "message": "正在准备分析..." }
            - { "stage": "analyzing", "progress": 30, "message": "AI正在深度分析..." }
            - { "stage": "complete", "progress": 100, "message": "完成！", "plan": TaskList }
            - { "stage": "error", "message": "错误信息" }
        """
        import threading
        import time
        
        result = {"plan": None, "error": None}
        
        # 后台线程调用真实的 LLM
        def worker():
            try:
                result["plan"] = self.generate_plan(user_intent, resume)
            except Exception as e:
                result["error"] = str(e)
        
        thread = threading.Thread(target=worker)
        thread.start()
        
        # 模拟进度阶段
        # (最大等待时间秒, 进度%, 消息)
        # 注意：复杂简历可能需要90-150秒，调整时间分配以匹配
        progress_steps = [
            (3, 5, "正在准备分析..."),
            (8, 15, "AI正在读取简历内容..."),
            (25, 35, "AI正在深度分析简历和职位匹配度..."),
            (50, 55, "AI正在识别优化机会..."),
            (90, 75, "正在生成优化方案..."),
            (130, 90, "正在验证和整理..."),
        ]
        
        start_time = time.time()
        
        for max_time, progress, message in progress_steps:
            while time.time() - start_time < max_time and thread.is_alive():
                yield {
                    "stage": "analyzing",
                    "progress": progress,
                    "message": message
                }
                time.sleep(0.8)  # 每0.8秒更新一次
                
                # 如果线程已完成，立即跳出
                if not thread.is_alive():
                    break
            
            # 如果线程已完成，立即跳出
            if not thread.is_alive():
                break
        
        # 等待线程完成（最多150秒，复杂简历需要更长时间）
        thread.join(timeout=150)
        
        # 返回结果
        if result["error"]:
            yield {"stage": "error", "message": f"生成失败: {result['error']}"}
        elif result["plan"]:
            yield {
                "stage": "complete",
                "progress": 100,
                "message": "优化计划已生成！",
                "plan": result["plan"].model_dump()
            }
        else:
            yield {"stage": "error", "message": "生成超时，AI服务器可能繁忙，请稍后重试"}

if __name__ == "__main__":
    # 测试代码
    print("开始测试 PlanAgent...")
    
    # 模拟一个简历
    from pathlib import Path
    from model import Resume
    
    resume_json_path = Path(__file__).resolve().parent.parent / "testCase" / "刘锦文的简历 (4)_json.json"
    mock_resume = Resume.model_validate_json(resume_json_path.read_text(encoding="utf-8"))
    
    user_intent = """
    AI 应用研发(校招生)
职位详情
标签：Java、C/C++、全栈无侧重、MySQL/Redis/MongoDB、计算机相关专业、英语读写能力良好、Python、全栈项目经验
工作内容：
1. 参与智能应用和业务自动化类 AI 项目的研发；2. 参与多 Agent、工具调用、记忆系统等 AI 原生能力建设；3. 将业务流程抽象、优化并落地为实际可运行的 AI 工作流；4. 参与日常开发、调试、测试与文档编写，推动项目上线与迭代。
任职要求：
1. 熟练掌握 Python，并熟悉其他编程语言（如 Java/Go/TypeScript 等）；2. 具备扎实的计算机基础与良好的编码习惯；3. 对 LLM/RAG/Agent/NLP 等方向有兴趣或基础了解；4. 有 AI 项目、课程项目、竞赛、科研或实习经验者优先；5. 有前后端项目经验、GitHub 项目或技术探索经历加分。
我们希望你具备：
1. 对 AI 技术及其应用有强烈兴趣；2. 学习能力强，愿意快速吸收新知识；
"""
    
    agent = PlanAgent()
    print(f"用户意图: {user_intent}")
    print("正在生成修改计划...")
    
    try:
        task_list = agent.generate_plan(user_intent, mock_resume)
        print("\n生成结果:")
        print(task_list.model_dump_json(indent=2))
        
        print(f"\n成功解析 TaskList，包含 {len(task_list.tasks)} 个任务。")
        
    except Exception as e:
        print(f"\n发生错误: {e}")
