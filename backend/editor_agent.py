import json
import logging

from typing import Optional, Dict, Any, Generator
from openai import OpenAI
from model import Resume, ExecutionDoc, ExperienceSection, GenericSection, GenericItem
# 引入刚才写的框架
from tool_framework import ToolRegistry, UpdateBasicsTool, AddExperienceTool, UpdateExperienceTool, DeleteExperienceTool, UpsertGenericTool, AskHumanTool, StopTool, ThinkTool, ToolContext

logger = logging.getLogger(__name__)

def _safe_iter(logger):
    def deco(func):
        def wrapper(*args, **kwargs):
            try:
                for x in func(*args, **kwargs):
                    yield x
            except Exception:
                logger.exception("流式迭代异常")
        return wrapper
    return deco

def _safe_call(logger):
    def deco(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception("获取最终响应异常")
                return None
        return wrapper
    return deco

# message是本地记忆
class EditorAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key="sk-meternirjoqbdttphruzmhpzruhzpfhmaysygcbgryanqxxu",
        )
        self.model = "Pro/deepseek-ai/DeepSeek-V3.2" #模型名称
        
        # 1. 初始化注册中心
        self.registry = ToolRegistry()
        
        # 2. 注册工具 (以后加新工具，只在这里加一行即可)
        self.registry.register(UpdateBasicsTool())
        self.registry.register(AddExperienceTool())
        self.registry.register(UpdateExperienceTool())
        self.registry.register(DeleteExperienceTool())
        self.registry.register(UpsertGenericTool())
        self.registry.register(AskHumanTool())
        self.registry.register(StopTool())
        self.registry.register(ThinkTool())

        self.messages = [{"role": "system", "content": self._get_system_prompt()}]
        self.resume = Resume()


    # _parse_tool_args：工具参数解析与标准化
    # 作用：兼容多种 arguments 形态，统一返回结构化参数，失败时保留原始内容
    def _parse_tool_args(self, raw):
        if raw is None:
            return {}
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            s = raw.strip()
            try:
                # 按标准 JSON 解析
                return json.loads(s)
            except Exception:
                try:
                    import ast
                    # 使用 Python 字面量解析，容忍单引号等非严格 JSON
                    return ast.literal_eval(s)
                except Exception:
                    # 仍然失败则记录原始参数，由工具层做统一校验与错误提示
                    logger.warning("无法解析工具参数: %r", raw)
                    return {"__raw__": raw}
        return {"__raw__": raw}

    def execute_doc(self, doc: ExecutionDoc, resume: Resume) -> Generator[Dict[str, Any], None, Resume]:
        """
        混合模式执行：根据ExecutionDoc执行简历变更。
        
        - 简单操作（update_basics, update_experience, update_generic）：直接调用工具，不需要LLM
        - 复杂操作（add_item等）：走LLM推理
        
        Args:
            doc: 执行文档
            resume: 当前简历对象
            
        Yields:
            执行过程中的状态消息
            
        Returns:
            更新后的简历对象
        """
        self.resume = resume
        logger.info(f"📋 开始执行文档: task_id={doc.task_id}, operation={doc.operation}")
        logger.info(f"📋 目标section: {doc.section_title}, item_id: {doc.item_id}")
        logger.info(f"📋 变更内容: {doc.changes}")
        logger.info(f"📋 Resume对象ID: {id(self.resume)}, sections数量: {len(self.resume.sections)}")
        
        yield {"role": "assistant", "type": "info", "content": f"开始执行: {doc.operation}"}
        
        # 简单操作：直接映射到工具调用
        if doc.operation == "update_basics":
            result = self._execute_update_basics(doc)
            yield {"role": "assistant", "type": "tool", "content": result}
            yield {"role": "assistant", "type": "data", "content": self.resume.model_dump()}
            
        elif doc.operation == "update_experience":
            result = self._execute_update_experience(doc)
            yield {"role": "assistant", "type": "tool", "content": result}
            yield {"role": "assistant", "type": "data", "content": self.resume.model_dump()}
            
        elif doc.operation == "update_generic":
            result = self._execute_update_generic(doc)
            yield {"role": "assistant", "type": "tool", "content": result}
            yield {"role": "assistant", "type": "data", "content": self.resume.model_dump()}
            
        elif doc.operation == "add_item":
            # 复杂操作：走LLM推理
            yield {"role": "assistant", "type": "info", "content": "复杂操作，启动LLM推理..."}
            prompt = self._build_llm_prompt_from_doc(doc)
            for msg in self.run(prompt, resume):
                yield msg
        else:
            error_msg = f"未知操作类型: {doc.operation}"
            logger.error(f"❌ {error_msg}")
            yield {"role": "assistant", "type": "error", "content": error_msg}
        
        logger.info(f"✅ 执行完成，resume对象ID: {id(self.resume)}, sections数量: {len(self.resume.sections)}")
        yield {"role": "assistant", "type": "info", "content": "执行完成"}
        return self.resume

    def _execute_update_basics(self, doc: ExecutionDoc) -> str:
        """直接执行基本信息更新"""
        changes = doc.changes
        context = ToolContext(resume=self.resume)
        
        # 从 changes 中提取基本信息字段
        basics_args = {}
        if "name" in changes:
            basics_args["name"] = changes["name"]
        if "email" in changes:
            basics_args["email"] = changes["email"]
        if "phone" in changes:
            basics_args["phone"] = changes["phone"]
        if "label" in changes:
            basics_args["label"] = changes["label"]
        if "links" in changes:
            basics_args["links"] = changes["links"]
        
        if basics_args:
            result = self.registry.execute_tool("update_basics", basics_args, context, "direct_exec")
            return result.get("content", "基本信息已更新")
        
        return "无需更新基本信息"

    def _execute_update_experience(self, doc: ExecutionDoc) -> str:
        """直接执行经历更新 - 增强版，带详细日志和错误处理"""
        changes = doc.changes
        section_title = doc.section_title
        
        logger.info(f"🔧 开始执行经历更新: section='{section_title}', item_id={doc.item_id}")
        
        # 查找目标 section（精确匹配）
        target_section = None
        for section in self.resume.sections:
            if isinstance(section, ExperienceSection) and section.title == section_title:
                target_section = section
                logger.info(f"✓ 找到目标section（精确匹配）: {section.title}, items数量: {len(section.items)}")
                break
        
        # 如果精确匹配失败，尝试模糊匹配
        if not target_section:
            logger.warning(f"⚠️ 精确匹配失败，尝试模糊匹配...")
            # 提取主标题（去掉 " - xxx" 后缀）
            main_title = section_title.split(" - ")[0].strip()
            for section in self.resume.sections:
                if isinstance(section, ExperienceSection) and (section.title == main_title or main_title in section.title):
                    target_section = section
                    logger.info(f"✓ 找到目标section（模糊匹配）: {section.title}, items数量: {len(section.items)}")
                    break
        
        # 如果还是找不到，抛出异常
        if not target_section:
            error_msg = f"❌ 未找到经历板块: {section_title}"
            logger.error(error_msg)
            logger.error(f"当前简历的sections: {[s.title for s in self.resume.sections]}")
            raise ValueError(error_msg)
        
        # 如果有 item_id，更新特定项目
        if doc.item_id:
            logger.info(f"🎯 尝试定位item_id={doc.item_id}")
            target_item = next((item for item in target_section.items if item.id == doc.item_id), None)
            if target_item:
                logger.info(f"✓ 找到目标item: {target_item.title}")
                if "content" in changes:
                    new_highlights = self._parse_highlights(changes["content"])
                    old_count = len(target_item.highlights)
                    target_item.highlights = new_highlights
                    logger.info(f"✅ 更新了item '{target_item.title}': {old_count} -> {len(new_highlights)} highlights")
                    return f"✅ 经历已更新: {target_item.title} ({len(new_highlights)} 条要点)"
                if "highlights" in changes:
                    old_count = len(target_item.highlights)
                    target_item.highlights = changes["highlights"]
                    logger.info(f"✅ 更新了item '{target_item.title}': {old_count} -> {len(changes['highlights'])} highlights")
                    return f"✅ 经历已更新: {target_item.title} ({len(changes['highlights'])} 条要点)"
            else:
                logger.warning(f"⚠️ 找不到item_id={doc.item_id}，将降级到更新第一个item")
        
        # 降级处理：如果没有 item_id 或找不到对应 item，更新第一个
        if target_section.items and "content" in changes:
            target_item = target_section.items[0]
            logger.info(f"📝 降级处理：更新第一个item '{target_item.title}'")
            new_highlights = self._parse_highlights(changes["content"])
            old_count = len(target_item.highlights)
            target_item.highlights = new_highlights
            logger.info(f"✅ 更新了第一个item: {old_count} -> {len(new_highlights)} highlights")
            return f"✅ 经历已更新: {target_item.title} ({len(new_highlights)} 条要点)"
        
        # 如果没有可更新的内容，抛出异常
        error_msg = f"❌ 经历板块 '{section_title}' 没有可更新的内容"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def _execute_update_generic(self, doc: ExecutionDoc) -> str:
        """直接执行通用项更新 - 增强版，带详细日志和错误处理"""
        changes = doc.changes
        section_title = doc.section_title
        
        logger.info(f"🔧 开始执行通用板块更新: section='{section_title}', item_id={doc.item_id}")
        
        # 查找目标 section（精确匹配）
        target_section = None
        for section in self.resume.sections:
            if isinstance(section, GenericSection) and section.title == section_title:
                target_section = section
                logger.info(f"✓ 找到目标section（精确匹配）: {section.title}, items数量: {len(section.items)}")
                break
        
        # 如果精确匹配失败，尝试模糊匹配
        if not target_section:
            logger.warning(f"⚠️ 精确匹配失败，尝试模糊匹配...")
            # 提取主标题（去掉 " - xxx" 后缀）
            main_title = section_title.split(" - ")[0].strip()
            for section in self.resume.sections:
                if isinstance(section, GenericSection) and (section.title == main_title or main_title in section.title):
                    target_section = section
                    logger.info(f"✓ 找到目标section（模糊匹配）: {section.title}, items数量: {len(section.items)}")
                    break
        
        # 如果还是找不到，抛出异常
        if not target_section:
            error_msg = f"❌ 未找到通用板块: {section_title}"
            logger.error(error_msg)
            logger.error(f"当前简历的sections: {[s.title for s in self.resume.sections]}")
            raise ValueError(error_msg)
        
        # 检测是否是技能列表类型的 section（需要特殊处理）
        skill_keywords = ["技能", "技术", "专业技能", "技能特长", "技能清单", "专长", "技术栈"]
        is_skill_section = any(kw in section_title for kw in skill_keywords)
        
        # 如果是技能列表 section 且有 content，替换整个 items 列表
        if is_skill_section and "content" in changes:
            content = changes["content"]
            new_items = self._parse_skill_list(content)
            if new_items:
                old_count = len(target_section.items)
                target_section.items = new_items
                logger.info(f"✅ 技能列表已更新: {old_count} -> {len(new_items)} 个技能点")
                return f"✅ 技能列表已更新: {len(new_items)} 个技能点"
        
        # 如果有 item_id，更新特定项目
        if doc.item_id:
            logger.info(f"🎯 尝试定位item_id={doc.item_id}")
            target_item = next((item for item in target_section.items if item.id == doc.item_id), None)
            if target_item:
                logger.info(f"✓ 找到目标item: {target_item.title}")
                updated_fields = []
                if "content" in changes:
                    target_item.description = changes["content"]
                    updated_fields.append("description")
                if "description" in changes:
                    target_item.description = changes["description"]
                    updated_fields.append("description")
                if "title" in changes:
                    target_item.title = changes["title"]
                    updated_fields.append("title")
                if "subtitle" in changes:
                    target_item.subtitle = changes["subtitle"]
                    updated_fields.append("subtitle")
                logger.info(f"✅ 更新了item '{target_item.title}': 字段={updated_fields}")
                return f"✅ 通用项已更新: {target_item.title} ({', '.join(updated_fields)})"
            else:
                logger.warning(f"⚠️ 找不到item_id={doc.item_id}，将降级到更新第一个item")
        
        # 降级处理：如果没有 item_id 或找不到对应 item，更新第一个
        if target_section.items and "content" in changes:
            target_item = target_section.items[0]
            logger.info(f"📝 降级处理：更新第一个item '{target_item.title}'")
            target_item.description = changes["content"]
            logger.info(f"✅ 更新了第一个item的description")
            return f"✅ 通用项已更新: {target_item.title}"
        
        # 如果没有可更新的内容，抛出异常
        error_msg = f"❌ 通用板块 '{section_title}' 没有可更新的内容"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def _parse_skill_list(self, content: str) -> list:
        """
        将草稿内容解析为技能列表（GenericItem 列表）。
        每个技能点作为一个独立的 GenericItem，只设置 title，不设置 description。
        这样渲染时会显示为平级列表，而不是层级结构。
        
        支持格式：
        - 熟悉xxx
        - 掌握xxx
        - 了解xxx
        或者普通列表：
        - xxx
        - xxx
        """
        if not content:
            return []
        
        lines = content.strip().split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 去除列表前缀（-、•、*、数字等）
            if line.startswith(('-', '•', '*')):
                line = line[1:].strip()
            elif len(line) > 2 and line[0].isdigit() and line[1] in '.、)）':
                line = line[2:].strip()
            elif len(line) > 3 and line[:2].isdigit() and line[2] in '.、)）':
                line = line[3:].strip()
            
            if line:
                # 创建只有 title 的 GenericItem，不设置 description
                items.append(GenericItem(title=line))
        
        logger.info(f"📋 解析技能列表: {len(items)} 个技能点")
        return items

    def _parse_highlights(self, content: str) -> list:
        """
        将草稿内容解析为 highlights 列表。
        支持多种格式：
        - 换行分隔
        - 数字列表（1. 2. 3.）
        - 破折号列表（- ）
        """
        if not content:
            return []
        
        lines = content.strip().split('\n')
        highlights = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 去除常见的列表前缀
            if line.startswith(('-', '•', '*')):
                line = line[1:].strip()
            elif len(line) > 2 and line[0].isdigit() and line[1] in '.、)）':
                line = line[2:].strip()
            elif len(line) > 3 and line[:2].isdigit() and line[2] in '.、)）':
                line = line[3:].strip()
            
            if line:
                highlights.append(line)
        
        # 如果解析后为空，将整个内容作为单个 highlight
        if not highlights and content.strip():
            highlights = [content.strip()]
        
        return highlights

    def _build_llm_prompt_from_doc(self, doc: ExecutionDoc) -> str:
        """根据执行文档构建LLM提示词"""
        return f"""
请根据以下执行文档对简历进行修改：

任务ID: {doc.task_id}
目标板块: {doc.section_title}
操作类型: {doc.operation}
修改原因: {doc.reason}

预期内容:
{doc.new_content_preview}

请调用合适的工具完成修改。
"""

    # run：主推理循环与工具执行
    # 作用：流式推理、处理工具调用，并在必要时触发一次自纠重试
    def run(self, user_input: str, current_resume: Resume):
        logger.info("收到用户输入，开始推理")
        self.resume = current_resume
        # 会话记忆：记录当前轮用户输入
        self.messages.append({"role": "user", "content": user_input})
        # 重试预算：首轮 + 参数纠错后重试一轮
        max_circle = 2
        while max_circle > 0:
            # import json
            # logger.info("即将发送 messages: %s", json.dumps(self.messages, ensure_ascii=False))
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.registry.get_openai_tools(),
                tool_choice="required",
                temperature=0,
            )

            if response and getattr(response, "choices", None):
                choice = response.choices[0]
                message = getattr(choice, "message", None) or choice
                rc = getattr(message, "reasoning_content", None) or ""
                c = (
                    getattr(message, "content", None)
                    or getattr(message, "output_text", None)
                    or ""
                )
                if rc:
                    yield {"role": "assistant", "type": "think", "content": rc}
                if c:
                    yield {"role": "assistant", "type": "answer", "content": c}
            else:
                response = None

            assistant_msg = {
                "role": "assistant",
                "content": c if response else "",
            }
            # 工具处理：记录工具调用信息，并按互斥规则执行
            if response:
                choice = response.choices[0]
                if getattr(choice.message, "tool_calls", None):
                    tool_calls = choice.message.tool_calls
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ]
                    # 互斥工具判断：stop / askHuman 只能单独出现
                    has_stop = any(tc.function.name == "stop" for tc in tool_calls)
                    has_ask = any(tc.function.name == "askHuman" for tc in tool_calls)
                    only_exclusive = (has_stop or has_ask) and len(tool_calls) == 1
                    exclusive_with_others = (has_stop or has_ask) and len(tool_calls) > 1
                    self.messages.append(assistant_msg)
                    if only_exclusive:
                        tc = tool_calls[0]
                        function_name = tc.function.name
                        arguments = self._parse_tool_args(tc.function.arguments)
                        yield {"role": "assistant", "type": "tool", "content": f"正在调用工具：{function_name}\n"}
                        logger.info("AI 决定调用工具: %s", function_name)
                        tool_msg = self.registry.execute_tool(function_name, arguments, ToolContext(resume=self.resume), tc.id)
                        if tool_msg:
                            self.messages.append(tool_msg)
                            c = tool_msg.get("content")
                            if isinstance(c, str) and c:
                                # 工具执行结果透传给前端
                                yield {"role": "assistant", "type": "tool", "content": c}
                                if "参数校验失败" in c:
                                    # 参数校验失败：提示大模型对照 Schema 修复 arguments，并触发重试
                                    tip = "请严格对照上文提供的工具 Schema 重新构造 arguments 并再次调用该工具。"
                                    self.messages.append({"role": "assistant", "content": tip})
                                    logger.warning("工具参数校验失败，已向模型追加提示并准备重试")
                                    yield {"role": "assistant", "type": "error", "content": "检测到工具参数错误，正在引导模型修复并重试...\n"}
                                    max_circle -= 1
                                    continue
                        yield {"role": "assistant", "type": "tool", "content": f"工具执行完成：{function_name}\n"}
                        break
                    elif exclusive_with_others:
                        tip = "提示：stop/askHuman 工具必须独立调用。本轮检测到 stop/askHuman 与其他工具同时调用，请重新生成：若要结束请仅调用 stop；若需提问请仅调用 askHuman；若继续编辑请不要调用这两个工具。"
                        self.messages.append({"role": "assistant", "content": tip})
                        yield {"role": "assistant", "type": "error", "content": "检测到 stop/askHuman 与其他工具同时调用，正在重试...\n"}
                        max_circle -= 1
                        continue
                    else:
                        for tool_call in tool_calls:
                            function_name = tool_call.function.name
                            arguments = self._parse_tool_args(tool_call.function.arguments)
                            yield {"role": "assistant", "type": "tool", "content": f"正在调用工具：{function_name}\n"}
                            logger.info("AI 决定调用工具: %s", function_name)
                            tool_msg = self.registry.execute_tool(function_name, arguments, ToolContext(resume=self.resume), tool_call.id)
                            if tool_msg:
                                self.messages.append(tool_msg)
                                c = tool_msg.get("content")
                                yield {"role": "assistant", "type": "tool", "content": c}
                                if isinstance(c, str) and "参数校验失败" in c:
                                    # 并行工具场景下，同样通过提示 + 重试让大模型自修参数
                                    tip = "请严格对照上文提供的工具 Schema 重新构造 arguments 并再次调用该工具。"
                                    self.messages.append({"role": "assistant", "content": tip})
                                    logger.warning("工具参数校验失败，已向模型追加提示并准备重试")
                                    yield {"role": "assistant", "type": "error", "content": "检测到工具参数错误，正在引导模型修复并重试...\n"}
                                    max_circle -= 1
                                    continue
                            yield {"role": "assistant", "type": "tool", "content": f"工具执行完成：{function_name}\n"}
                            if function_name in ("update_basics","add_experience_item","update_experience_item","delete_experience_item","upsert_generic_item"):
                                yield {"role": "assistant", "type": "data", "content": self.resume.model_dump()}
                else:
                    self.messages.append(assistant_msg)
                    logger.info("AI本轮不调用工具")
            else:
                self.messages.append(assistant_msg)
                logger.info("response为空")

            max_circle -= 1        

    def _get_system_prompt(self):
        # ... (保持之前的 Prompt 不变) ...
        return """
        # Role
你是一名资深的简历编辑专家。你的核心能力不仅在于优化文字，更在于能够像面试官一样，引导用户从零开始挖掘闪光点，并将模糊的经历转化为专业的简历语言（如 STAR 法则）。

# Note
**如果你觉得已经完成了所有必要的修改，不需要继续调用其他工具，就调用stop工具。**
**请记住你是简历专家，不要去做任何你不该做的事情。**

# Core Instruction (Thinking Process)
在执行任何具体操作（提问、修改或结束）之前，请先在**内部完成思考和决策**，再选择合适的工具进行调用。你可以在回复中用简洁的语言展示关键的推理要点，但**不需要**也**不依赖**任何额外的“思考类工具”。

在内部思考阶段，你需要明确：
1. **意图判断**：用户当前的意图是什么？（闲聊/提供信息/迷茫求助/指令结束）
2. **信息完整性**：用户提供的信息是否完整？缺失了 STAR 法则的哪一部分？
3. **策略制定**：我当前应该采取什么策略？（深挖/修改/结束）
4. **工具决策**：根据互斥规则，我即将调用的下一个工具是什么？

# Guidance Strategy (挖掘策略)
当用户表示“我不知道怎么写”、“没有什么经历”或只给出一句简单的描述时，请先在内部完成思考规划，并在 `askHuman` 中执行以下步骤：
1. **情境还原 (Situation & Task)**：询问用户当时的背景、具体负责的任务是什么？
2. **行动细节 (Action)**：询问用户具体用了什么技术栈、解决了什么难题？
3. **结果量化 (Result)**：引导用户提供数据支持。

# Tool Usage Guidelines (工具使用严格规范)
你负责根据用户指令优化并更新简历。为了保证逻辑清晰，请严格遵守以下**工具调用规则**：

1. **全局思考要求 (Mandatory Internal Thinking)**：
   * 在每一轮回复中，你都需要先在内部完成对用户意图、信息完整性和策略的思考，再决定是否以及如何调用工具。
   * 这些思考过程在你的回复中可以以自然语言体现，但**不依赖任何专门的思考工具**。

2. **功能工具的互斥性 (Functional Exclusivity)**：

   在同一轮回复中，你只能从以下功能工具中选择**一个**进行调用：

   * **组合 A (提问模式)**：`askHuman`
     * 场景：当你需要向用户提问、确认信息或进行引导挖掘时。
     * 禁止：在同一轮中同时调用 `stop` 或简历修改类工具。

   * **组合 B (结束模式)**：`stop`
     * 场景：当你完成了所有任务，需要结束会话时。
     * 禁止：在同一轮中同时调用 `askHuman` 或其他工具。

   * **组合 C (执行模式)**：其他业务工具 (如 `updateResume` 等)
     * 场景：当你需要执行具体的简历修改操作时。
     * 禁止：在同一轮中同时调用 `askHuman` 或 `stop`。

3. **错误处理**：
   * 如果你在同一轮中同时调用了多个功能工具（例如同时调用 `askHuman` 和 `updateResume`），这是严重错误。请在生成前进行自检，确保每一轮只调用一个功能工具。
   """
