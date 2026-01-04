from typing import List, Optional, Union, Literal, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class GenericItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(...)
    subtitle: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


class ExperienceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(...)
    organization: str = Field(...)
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class SectionBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(...)


class ExperienceSection(SectionBase):
    type: Literal["experience"] = "experience"
    items: List[ExperienceItem] = Field(default_factory=list)


class GenericSection(SectionBase):
    type: Literal["generic"] = "generic"
    items: List[GenericItem] = Field(default_factory=list)


class TextSection(SectionBase):
    type: Literal["text"] = "text"
    content: str = ""


ResumeSection = Union[ExperienceSection, GenericSection, TextSection]


class Basics(BaseModel):
    name: str = "您的姓名"
    label: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    links: List[str] = Field(default_factory=list)


class Resume(BaseModel):
    basics: Basics = Field(default_factory=Basics)
    sections: List[ResumeSection] = Field(default_factory=list)


class ToolMessage(BaseModel):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str

    def to_dict(self) -> dict:
        return self.model_dump()


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待处理
    IN_PROGRESS = "in_progress"   # Guide正在处理
    CONFIRMED = "confirmed"       # 用户已确认
    COMPLETED = "completed"       # Editor已执行
    SKIPPED = "skipped"           # 用户跳过


class TaskStrategy(str, Enum):
    """任务处理策略枚举"""
    STAR_STORYTELLING = "STAR_STORYTELLING"  # 深挖故事模式（工作/项目经历）
    KEYWORD_FILTER = "KEYWORD_FILTER"        # 技能筛选模式（技能特长/工具）


class Task(BaseModel):
    id: int = Field(..., description="Unique identifier, starting from 1")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task")
    section: str = Field(..., description="Specific section of the resume")
    strategy: TaskStrategy = Field(default=TaskStrategy.STAR_STORYTELLING, description="Processing strategy for this task")
    original_text: str = Field(..., description="Original text segment to be modified")
    diagnosis: str = Field(..., description="Diagnosis of why this content is inadequate")
    goal: str = Field(..., description="Target goal or expected effect after modification")
    item_id: Optional[str] = Field(None, description="Target item ID within the section (for precise modification)")


class TaskList(BaseModel):
    tasks: List[Task] = Field(default_factory=list)


class AgentState(str, Enum):
    DISCOVERY = "DISCOVERY"     # 正在提问挖掘信息
    DRAFTING = "DRAFTING"       # 正在展示草稿等待确认
    CONFIRMING = "CONFIRMING"   # 等待用户确认执行
    FINISHED = "FINISHED"       # 任务已完成


class ExecutionDoc(BaseModel):
    """
    执行文档：Guide Agent的输出，Editor Agent的输入。
    描述一次简历变更操作的完整信息。
    """
    task_id: int = Field(..., description="关联的Task ID")
    section_title: str = Field(..., description="目标section的标题")
    item_id: Optional[str] = Field(None, description="目标item的id（如果修改具体条目）")
    operation: Literal["update_basics", "update_experience", "update_generic", "add_item"] = Field(
        ..., description="操作类型"
    )
    changes: Dict[str, Any] = Field(..., description="具体变更内容，键值对形式")
    new_content_preview: str = Field(..., description="预览文案（给用户看的优化后内容）")
    reason: str = Field(..., description="修改原因说明")


class AgentDecision(BaseModel):
    thought: str = Field(..., description="Reasoning based on diagnosis and user input.")
    # LLM 建议的下一步动作
    next_action: Literal["CONTINUE_ASKING", "PROPOSE_DRAFT", "REQUEST_CONFIRM", "CONFIRM_FINISH"] = Field(
        ..., description="Decision for the state machine."
    )
    reply_to_user: str = Field(..., description="Response to the user.")
    draft_content: Optional[str] = Field(None, description="Optimized content. REQUIRED if next_action is PROPOSE_DRAFT.")
    execution_doc: Optional[ExecutionDoc] = Field(None, description="Execution document. Generated when entering CONFIRMING state.")
    # 智能任务回溯字段
    intent: Optional[Literal["CONTINUE", "BACKTRACK"]] = Field(None, description="User intent: CONTINUE current task or BACKTRACK to a previous task.")
    target_section: Optional[str] = Field(None, description="Target section name when intent is BACKTRACK.")


class AgentSnapshot(BaseModel):
    """
    Agent 运行时快照，用于中断恢复。
    只存储产生结果后的状态，不存储中间决策（Decision）。
    """
    current_state: AgentState = Field(..., description="当前所处的流程状态")
    messages: List[dict] = Field(default_factory=list, description="完整的对话历史上下文")
    draft: Optional[str] = Field(None, description="当前持有的最新草稿")
    execution_doc: Optional[ExecutionDoc] = Field(None, description="当前待确认的执行文档")

