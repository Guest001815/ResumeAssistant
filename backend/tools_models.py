from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

class UpdateBasicsArgs(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    links: Optional[List[str]] = None

class UpsertExperienceArgs(BaseModel):
    section_title: str = Field(...)
    title: str = Field(...)
    organization: str = Field(...)
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

class AddExperienceArgs(BaseModel):
    section_title: str = Field(...)
    title: str = Field(...)
    organization: str = Field(...)
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

class UpdateExperienceArgs(BaseModel):
    section_title: str = Field(...)
    title: str = Field(...)
    organization: str = Field(...)
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    highlights: Optional[List[str]] = None

class DeleteExperienceArgs(BaseModel):
    section_title: str = Field(...)
    title: str = Field(...)
    organization: str = Field(...)

class UpsertGenericArgs(BaseModel):
    section_title: str = Field(...)
    title: str = Field(...)
    subtitle: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

class AskHumanArgs(BaseModel):
    question: str = Field(...)

class StopArgs(BaseModel):
    message: Optional[str] = None

class ThinkArgs(BaseModel):
    reasoning: str = Field(..., description="详细的思考内容，包括意图分析、信息完整性检查和下一步策略。")
