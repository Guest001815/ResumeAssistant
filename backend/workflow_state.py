"""
工作流状态：统一管理整个简历优化流程的状态。

设计目标：
1. 解耦 SessionManager 与具体 Agent 类型
2. 兼容 LangGraph 的 State 设计模式
3. 支持序列化和反序列化（持久化）

未来升级 LangGraph 时，可直接转换为 TypedDict：
```python
from typing import TypedDict

class GraphState(TypedDict):
    resume: Resume
    plan: TaskList
    current_stage: str
    ...
```
"""
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
import uuid

from model import Resume, TaskList, Task, TaskStatus, ExecutionDoc


class WorkflowStage(str, Enum):
    """工作流阶段"""
    INIT = "init"           # 初始化，等待上传简历
    PLANNING = "planning"   # Plan Agent 执行中
    GUIDING = "guiding"     # Guide Agent 执行中
    CONFIRMING = "confirming"  # 等待用户确认
    EDITING = "editing"     # Editor Agent 执行中
    COMPLETED = "completed" # 所有任务完成
    ERROR = "error"         # 发生错误


class WorkflowState(BaseModel):
    """
    工作流状态 - 核心状态模型
    
    设计原则：
    1. 所有状态集中管理
    2. 可序列化为 JSON（便于持久化）
    3. 兼容 LangGraph State 模式
    """
    
    # ==================== 会话标识 ====================
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # ==================== 核心数据 ====================
    resume: Resume = Field(default_factory=Resume, description="当前简历对象")
    user_intent: Optional[str] = Field(None, description="用户的求职意图")
    plan: Optional[TaskList] = Field(None, description="修改计划")
    
    # ==================== 流程控制 ====================
    current_stage: WorkflowStage = Field(
        default=WorkflowStage.INIT, 
        description="当前工作流阶段"
    )
    current_task_idx: int = Field(default=0, description="当前任务索引")
    current_exec_doc: Optional[ExecutionDoc] = Field(
        None, 
        description="当前待确认的执行文档"
    )
    
    # ==================== Agent 状态 ====================
    # 存储各 Agent 的内部状态（序列化后）
    # key: agent_name, value: agent 导出的状态字典
    agent_states: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="各 Agent 的内部状态快照"
    )
    
    # ==================== 消息历史 ====================
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="工作流消息历史，用于追溯和调试"
    )
    
    # ==================== 元数据 ====================
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据"
    )
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        use_enum_values = True

    # ==================== 任务管理方法 ====================
    
    def get_current_task(self) -> Optional[Task]:
        """获取当前任务"""
        if not self.plan or self.current_task_idx >= len(self.plan.tasks):
            return None
        return self.plan.tasks[self.current_task_idx]
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """根据 ID 获取任务"""
        if not self.plan:
            return None
        for task in self.plan.tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: int, status: TaskStatus) -> bool:
        """更新任务状态"""
        task = self.get_task_by_id(task_id)
        if task:
            task.status = status
            return True
        return False
    
    def move_to_next_task(self) -> Optional[Task]:
        """移动到下一个任务"""
        self.current_task_idx += 1
        self.current_exec_doc = None
        # 清除 Guide Agent 状态，因为要处理新任务
        self.agent_states.pop("guide", None)
        return self.get_current_task()
    
    def skip_current_task(self) -> Optional[Task]:
        """跳过当前任务"""
        current = self.get_current_task()
        if current:
            current.status = TaskStatus.SKIPPED
        return self.move_to_next_task()
    
    def get_skipped_task_names(self) -> List[str]:
        """获取所有被跳过的任务名称"""
        if not self.plan:
            return []
        return [t.section for t in self.plan.tasks if t.status == TaskStatus.SKIPPED]
    
    def get_completed_task_names(self) -> List[str]:
        """获取所有已完成的任务名称（用于回溯识别）"""
        if not self.plan:
            return []
        return [t.section for t in self.plan.tasks if t.status == TaskStatus.COMPLETED]
    
    def get_last_completed_task(self) -> Optional[Task]:
        """
        获取最后一个完成的任务（用于智能回溯默认目标）
        
        当用户表达不满意但没有指明具体任务时，默认回溯到这个任务。
        
        Returns:
            最后一个 COMPLETED 状态的任务，如果没有则返回 None
        """
        if not self.plan:
            return None
        
        # 从后往前查找最后一个已完成的任务
        for task in reversed(self.plan.tasks):
            if task.status == TaskStatus.COMPLETED:
                return task
        return None
    
    def get_last_completed_task_idx(self) -> Optional[int]:
        """
        获取最后一个完成任务的索引
        
        Returns:
            最后一个 COMPLETED 状态任务的索引，如果没有则返回 None
        """
        if not self.plan:
            return None
        
        for idx in range(len(self.plan.tasks) - 1, -1, -1):
            if self.plan.tasks[idx].status == TaskStatus.COMPLETED:
                return idx
        return None
    
    def switch_to_task(self, target_section: str) -> Optional[int]:
        """
        切换到指定任务（用于智能回溯修改）
        
        Args:
            target_section: 目标任务的板块名称（部分匹配即可）
            
        Returns:
            目标任务的索引，如果未找到返回 None
        """
        if not self.plan:
            return None
        
        # 查找匹配的任务（支持部分匹配）
        target_idx = None
        for idx, task in enumerate(self.plan.tasks):
            # 检查板块名称是否包含目标关键词
            if target_section in task.section or task.section in target_section:
                target_idx = idx
                break
        
        if target_idx is None:
            # 尝试更宽松的匹配（关键词匹配）
            target_lower = target_section.lower()
            for idx, task in enumerate(self.plan.tasks):
                section_lower = task.section.lower()
                # 检查是否有共同关键词
                if any(keyword in section_lower for keyword in target_lower.split()):
                    target_idx = idx
                    break
        
        if target_idx is not None:
            # 切换到目标任务
            self.current_task_idx = target_idx
            # 将任务状态改为进行中
            self.plan.tasks[target_idx].status = TaskStatus.IN_PROGRESS
            # 清除当前执行文档
            self.current_exec_doc = None
            # 清除 Guide Agent 状态，重新开始该任务的对话
            self.agent_states.pop("guide", None)
            # 更新工作流阶段
            self.current_stage = WorkflowStage.GUIDING
            
            return target_idx
        
        return None
    
    def find_task_by_section(self, target_section: str) -> Optional[Task]:
        """
        根据板块名称查找任务
        
        Args:
            target_section: 目标任务的板块名称
            
        Returns:
            匹配的任务，如果未找到返回 None
        """
        if not self.plan:
            return None
        
        for task in self.plan.tasks:
            if target_section in task.section or task.section in target_section:
                return task
        return None
    
    # ==================== Agent 状态管理 ====================
    
    def save_agent_state(self, agent_name: str, state: Dict[str, Any]) -> None:
        """保存 Agent 状态"""
        self.agent_states[agent_name] = state
    
    def get_agent_state(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 状态"""
        return self.agent_states.get(agent_name)
    
    def clear_agent_state(self, agent_name: str) -> None:
        """清除 Agent 状态"""
        self.agent_states.pop(agent_name, None)
    
    # ==================== 进度查询 ====================
    
    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        if not self.plan:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "skipped_tasks": 0,
                "current_task_idx": 0,
                "current_task": None,
                "tasks_summary": []
            }
        
        tasks = self.plan.tasks
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        
        return {
            "total_tasks": len(tasks),
            "completed_tasks": completed,
            "skipped_tasks": skipped,
            "current_task_idx": self.current_task_idx,
            "current_task": self.get_current_task(),
            "tasks_summary": [
                {"id": t.id, "section": t.section, "status": t.status}
                for t in tasks
            ]
        }
    
    def is_all_tasks_done(self) -> bool:
        """检查是否所有任务都已完成"""
        if not self.plan:
            return False
        for task in self.plan.tasks:
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
                return False
        return True
    
    # ==================== 消息管理 ====================
    
    def add_message(self, role: str, content: Any, msg_type: str = "info", agent: str = None) -> None:
        """添加消息到历史"""
        self.messages.append({
            "role": role,
            "type": msg_type,
            "content": content,
            "agent": agent
        })
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于持久化）"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """从字典恢复"""
        return cls.model_validate(data)


class WorkflowStateManager:
    """
    工作流状态管理器
    
    管理多个会话的 WorkflowState
    支持内存缓存 + 磁盘持久化
    """
    
    def __init__(self, enable_persistence: bool = True):
        self._states: Dict[str, WorkflowState] = {}
        self.enable_persistence = enable_persistence
        
        # 延迟导入避免循环依赖
        if enable_persistence:
            try:
                from session_persistence import session_persistence
                self._persistence = session_persistence
            except ImportError:
                import logging
                logging.warning("session_persistence 模块未找到，禁用持久化")
                self.enable_persistence = False
                self._persistence = None
        else:
            self._persistence = None
    
    def create(self, resume: Resume) -> WorkflowState:
        """创建新的工作流状态"""
        state = WorkflowState(resume=resume)
        self._states[state.session_id] = state
        return state
    
    def get(self, session_id: str) -> Optional[WorkflowState]:
        """
        获取工作流状态
        优先从内存缓存获取，如果不存在则尝试从磁盘加载
        """
        # 先检查内存缓存
        if session_id in self._states:
            return self._states[session_id]
        
        # 尝试从磁盘加载
        if self.enable_persistence and self._persistence:
            state = self._persistence.load_workflow_state(session_id)
            if state:
                # 加载后缓存到内存
                self._states[session_id] = state
                return state
        
        return None
    
    def save(self, state: WorkflowState) -> None:
        """
        保存工作流状态
        同时保存到内存和磁盘
        """
        self._states[state.session_id] = state
        
        # 如果启用持久化，同时保存到磁盘
        if self.enable_persistence and self._persistence:
            # 这里需要元数据，暂时使用默认值
            # 实际使用时应该从外部传入完整的元数据
            from session_persistence import SessionMetadata
            from datetime import datetime
            
            # 尝试加载已有元数据，如果不存在则创建默认的
            metadata = self._persistence.load_metadata(state.session_id)
            if not metadata:
                # 提取进度信息
                progress = state.get_progress()
                
                metadata = SessionMetadata(
                    id=state.session_id,
                    name=None,
                    resume_file_name=state.resume.basics.name or "未命名简历",
                    job_title="待设置",
                    job_company="待设置",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    progress={
                        "completed": progress["completed_tasks"],
                        "total": progress["total_tasks"]
                    },
                    status="active"
                )
            else:
                # 更新时间戳和进度
                metadata.updated_at = datetime.now().isoformat()
                progress = state.get_progress()
                metadata.progress = {
                    "completed": progress["completed_tasks"],
                    "total": progress["total_tasks"]
                }
            
            self._persistence.save_workflow_state(state, metadata)
    
    def delete(self, session_id: str) -> bool:
        """
        删除工作流状态
        同时从内存和磁盘删除
        """
        deleted = False
        
        # 从内存删除
        if session_id in self._states:
            del self._states[session_id]
            deleted = True
        
        # 从磁盘删除
        if self.enable_persistence and self._persistence:
            disk_deleted = self._persistence.delete_session(session_id)
            deleted = deleted or disk_deleted
        
        return deleted
    
    def list_sessions(self) -> List[str]:
        """列出所有会话ID（仅内存中的）"""
        return list(self._states.keys())
    
    def save_with_metadata(self, state: WorkflowState, metadata: "SessionMetadata") -> None:
        """
        保存工作流状态（带完整元数据）
        
        Args:
            state: WorkflowState对象
            metadata: SessionMetadata对象
        """
        self._states[state.session_id] = state
        
        if self.enable_persistence and self._persistence:
            self._persistence.save_workflow_state(state, metadata)


# 全局状态管理器
workflow_manager = WorkflowStateManager()

