from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel
from model import Resume, ExperienceSection, ExperienceItem, GenericSection, GenericItem, ToolMessage
from tools_models import UpdateBasicsArgs, AddExperienceArgs, UpdateExperienceArgs, DeleteExperienceArgs, UpsertGenericArgs, AskHumanArgs, StopArgs, ThinkArgs
import logging
import json

logger = logging.getLogger(__name__)

class ToolContext(BaseModel):
    resume: Optional[Resume] = None

# ==========================================
# 1. 抽象基类 (The Abstract Base)
# ==========================================
class BaseTool(ABC):
    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel] = None

    @abstractmethod
    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        pass

    def to_openai_schema(self) -> dict:
        """自动生成 OpenAI 需要的 Schema 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema()
            }
        }

# ==========================================
# 2. 具体工具实现 (The Concrete Tools)
# ==========================================

class UpdateBasicsTool(BaseTool):
    name = "update_basics"
    description = "更新简历的基本信息（姓名、电话、邮箱等）。"
    args_schema = UpdateBasicsArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        resume = context.resume if context else None
        if resume is None:
            return ToolMessage(content="未提供简历对象", tool_call_id=tool_call_id).to_dict()
        for key, value in args.items():
            if value is not None:
                setattr(resume.basics, key, value)
        logger.info("基本信息已更新: %s", args)
        return ToolMessage(
            content=f"基本信息已更新: {args}",
            tool_call_id=tool_call_id
        ).to_dict()

class AddExperienceTool(BaseTool):
    name = "add_experience_item"
    description = "新增工作/项目经历。必须包含润色后的 highlights。"
    args_schema = AddExperienceArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        resume = context.resume if context else None
        if resume is None:
            return ToolMessage(content="未提供简历对象", tool_call_id=tool_call_id).to_dict()
        target_title = args.pop("section_title")
        target_section = next((s for s in resume.sections
                               if isinstance(s, ExperienceSection) and s.title == target_title), None)
        if not target_section:
            target_section = ExperienceSection(title=target_title)
            resume.sections.append(target_section)
        new_item = ExperienceItem(**args)
        target_section.items.append(new_item)
        logger.info("经历已添加: %s at %s", new_item.title, new_item.organization)
        return ToolMessage(
            content=f"经历已添加: {new_item.title} at {new_item.organization}",
            tool_call_id=tool_call_id
        ).to_dict()

class UpdateExperienceTool(BaseTool):
    name = "update_experience_item"
    description = "更新工作/项目经历。仅更新传入字段。"
    args_schema = UpdateExperienceArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        resume = context.resume if context else None
        if resume is None:
            return ToolMessage(content="未提供简历对象", tool_call_id=tool_call_id).to_dict()
        target_title = args.get("section_title")
        target_section = next((s for s in resume.sections
                               if isinstance(s, ExperienceSection) and s.title == target_title), None)
        if not target_section:
            return ToolMessage(content="未找到经历板块", tool_call_id=tool_call_id).to_dict()
        title = args.get("title")
        organization = args.get("organization")
        existing_item = next((i for i in target_section.items
                              if i.title == title and i.organization == organization), None)
        if not existing_item:
            return ToolMessage(content="未找到经历项", tool_call_id=tool_call_id).to_dict()
        for k, v in args.items():
            if k in {"date_start", "date_end", "location", "highlights", "title", "organization"} and v is not None:
                if k == "highlights":
                    existing_item.highlights = v
                else:
                    setattr(existing_item, k, v)
        logger.info("经历已更新: %s at %s", existing_item.title, existing_item.organization)
        return ToolMessage(
            content=f"经历已更新: {existing_item.title} at {existing_item.organization}",
            tool_call_id=tool_call_id
        ).to_dict()

class DeleteExperienceTool(BaseTool):
    name = "delete_experience_item"
    description = "删除工作/项目经历。"
    args_schema = DeleteExperienceArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        resume = context.resume if context else None
        if resume is None:
            return ToolMessage(content="未提供简历对象", tool_call_id=tool_call_id).to_dict()
        target_title = args.get("section_title")
        target_section = next((s for s in resume.sections
                               if isinstance(s, ExperienceSection) and s.title == target_title), None)
        if not target_section:
            return ToolMessage(content="未找到经历板块", tool_call_id=tool_call_id).to_dict()
        title = args.get("title")
        organization = args.get("organization")
        idx = next((idx for idx, i in enumerate(target_section.items)
                    if i.title == title and i.organization == organization), None)
        if idx is None:
            return ToolMessage(content="未找到经历项", tool_call_id=tool_call_id).to_dict()
        removed = target_section.items.pop(idx)
        logger.info("经历已删除: %s at %s", removed.title, removed.organization)
        return ToolMessage(
            content=f"经历已删除: {removed.title} at {removed.organization}",
            tool_call_id=tool_call_id
        ).to_dict()

class UpsertGenericTool(BaseTool):
    name = "upsert_generic_item"
    description = "新增或更新通用经历（奖项/证书/志愿者）。"
    args_schema = UpsertGenericArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        resume = context.resume if context else None
        if resume is None:
            return ToolMessage(content="未提供简历对象", tool_call_id=tool_call_id).to_dict()
        target_title = args.pop("section_title")
        target_section = next((s for s in resume.sections 
                             if isinstance(s, GenericSection) and s.title == target_title), None)
        if not target_section:
            target_section = GenericSection(title=target_title)
            resume.sections.append(target_section)
        new_item = GenericItem(**args)
        target_section.items.append(new_item)
        logger.info("通用项已添加: %s", new_item.title)
        return ToolMessage(
            content=f"通用项已添加: {new_item.title}",
            tool_call_id=tool_call_id
        ).to_dict()

class StopTool(BaseTool):
    name = "stop"
    description = "标记任务已结束，供 Agent 调用"
    args_schema = StopArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        msg = args.get("message") if args else None
        text = "任务已结束" + (f": {msg}" if msg else "")
        logger.info("%s", text)
        return ToolMessage(
            content=text,
            tool_call_id=tool_call_id
        ).to_dict()

class AskHumanTool(BaseTool):
    name = "askHuman"
    description = "向用户提问以获取确认或补充信息"
    args_schema = AskHumanArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        question = args.get("question")
        text = f"需要用户响应: {question}" if question else "需要用户响应"
        logger.info("%s", text)
        return ToolMessage(
            content=text,
            tool_call_id=tool_call_id
        ).to_dict()

class ThinkTool(BaseTool):
    name = "think"
    description = "记录内在思考过程。在调用任何实际执行工具之前，必须先调用此工具来分析用户意图和制定策略。"
    args_schema = ThinkArgs

    def execute(self, args: dict, tool_call_id: str, context: Optional[ToolContext] = None) -> dict:
        reasoning = args.get("reasoning")
        text = f"进入思考模式\n{reasoning}" if reasoning else "进入思考模式"
        logger.info("%s", text)
        return ToolMessage(content=text, tool_call_id=tool_call_id).to_dict()

# ==========================================
# 3. 工具注册中心 (The Registry)
# ==========================================
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册一个工具"""
        self._tools[tool.name] = tool

    def get_openai_tools(self) -> List[dict]:
        """获取所有工具的 Schema 列表，给 LLM 看"""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute_tool(self, name: str, args: dict, context: ToolContext, tool_call_id: str) -> dict:
        if name not in self._tools:
            return ToolMessage(content=f"未找到工具: {name}", tool_call_id=tool_call_id).to_dict()
        tool = self._tools[name]
        try:
            if tool.args_schema is not None:
                validated = tool.args_schema.model_validate(args)
                args = validated.model_dump()
        except Exception as e:
            # 参数已是合法 JSON，但不符合工具的 Pydantic Schema。
            # 这里把校验错误、原始参数字典，以及该工具完整的 OpenAI Schema 一并反馈给大模型，
            # 其中 Schema 通过 tool.to_openai_schema() 生成，格式与最初注册给大模型的 tools 完全一致，
            # 方便大模型对照 parameters 部分重新构造 arguments 并再次调用。
            fn_schema = tool.to_openai_schema()
            # 为便于大模型直接复制使用，这里序列化为 JSON 字符串，而不是 Python dict 的 repr
            schema_json = json.dumps(fn_schema, ensure_ascii=False)
            content = (
                f"参数校验失败: {str(e)}；原始参数字典: {args}。"
                "下面是当前工具的完整 Schema（与 tools 中注册的格式相同），"
                "请你严格对照其中的 parameters 字段，重新构造一次 arguments 并再次调用该工具："
                f"{schema_json}"
            )
            return ToolMessage(
                content=content,
                tool_call_id=tool_call_id
            ).to_dict()
        return tool.execute(args, tool_call_id, context)
