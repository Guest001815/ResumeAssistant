"""
Agent 适配器：将现有 Agent 适配到 BaseAgent 接口。

设计原则：
1) 最小侵入：不改动原 Agent 逻辑，仅包装为统一接口
2) 统一协议：接入 BaseAgent / AgentInput / AgentOutput / AgentMessage
3) 渐进迁移：便于后续切换 LangGraph 或替换 Agent 实现

使用方式：
```python
from agent_adapters import PlanAgentAdapter, GuideAgentAdapter, EditorAgentAdapter

orchestrator = Orchestrator()
orchestrator.register_agent(PlanAgentAdapter())
orchestrator.register_agent(GuideAgentAdapter())
orchestrator.register_agent(EditorAgentAdapter())
```
"""
import logging
from typing import Dict, Any, Generator, Optional

from base_agent import BaseAgent, AgentInput, AgentOutput, AgentMessage, AgentAction
from workflow_state import WorkflowState
from model import Task, ExecutionDoc, TaskList, AgentState as GuideState

logger = logging.getLogger(__name__)


class PlanAgentAdapter(BaseAgent):
    """
    Plan Agent 适配器
    
    将 PlanAgent 适配到 BaseAgent 接口
    """
    
    def __init__(self):
        # 延迟导入避免循环依赖
        from plan_agent import PlanAgent
        self._agent = PlanAgent()
    
    @property
    def name(self) -> str:
        return "plan"
    
    @property
    def description(self) -> str:
        return "简历诊断与计划生成 Agent"
    
    def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
        """
        执行 Plan Agent
        
        输入：用户意图
        输出：TaskList（修改计划）
        """
        try:
            user_intent = input.content
            resume = state.resume
            
            # 调用原有方法
            task_list = self._agent.generate_plan(user_intent, resume)
            
            return AgentOutput(
                thought="已分析简历并生成修改计划",
                action=AgentAction.FINISH,
                content=task_list,
                messages=[
                    AgentMessage(
                        type="info",
                        content=f"生成了 {len(task_list.tasks)} 个优化任务",
                        agent_name=self.name
                    )
                ]
            )
            
        except Exception as e:
            logger.exception("PlanAgent 执行失败")
            return AgentOutput(
                thought=f"执行出错: {str(e)}",
                action=AgentAction.FINISH,
                content=None,
                messages=[AgentMessage(type="error", content=str(e), agent_name=self.name)]
            )
    
    def stream(self, input: AgentInput, state: WorkflowState) -> Generator[AgentMessage, None, AgentOutput]:
        """Plan Agent 不支持流式，直接调用 invoke"""
        yield AgentMessage(type="info", content="正在分析简历...", agent_name=self.name)
        output = self.invoke(input, state)
        for msg in output.messages:
            yield msg
        return output
    
    def export_state(self) -> Dict[str, Any]:
        """Plan Agent 是无状态的"""
        return {}
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """Plan Agent 是无状态的"""
        pass


class GuideAgentAdapter(BaseAgent):
    """
    Guide Agent 适配器
    
    将 GuideAgent 适配到 BaseAgent 接口
    """
    
    def __init__(self):
        self._agent = None  # 延迟初始化
        self._current_task: Optional[Task] = None
    
    @property
    def name(self) -> str:
        return "guide"
    
    @property
    def description(self) -> str:
        return "简历内容引导与草稿生成 Agent"
    
    def _build_context(self, state: WorkflowState) -> Dict[str, Any]:
        """
        从 WorkflowState 构建任务流转上下文。
        
        包含：
        - skipped_tasks: 已跳过的任务名称列表
        - progress: 进度信息
        - is_first_after_skip: 是否是跳过任务后的第一次对话
        """
        from model import TaskStatus
        
        progress = state.get_progress()
        
        # 获取已跳过的任务名称
        skipped_tasks = []
        if state.plan:
            skipped_tasks = [t.section for t in state.plan.tasks if t.status == TaskStatus.SKIPPED]
        
        # 判断是否是跳过后的首次对话
        # 条件：当前任务索引 > 0，且上一个任务状态是 SKIPPED，且当前 Agent 没有对话历史
        is_first_after_skip = False
        if state.current_task_idx > 0 and state.plan:
            prev_task = state.plan.tasks[state.current_task_idx - 1]
            if prev_task.status == TaskStatus.SKIPPED:
                # 如果 Agent 还没初始化，或者已初始化但没有对话历史，则认为是跳过后的首次对话
                if self._agent is None:
                    is_first_after_skip = True
                else:
                    is_first_after_skip = len(self._agent.messages) == 0
        
        return {
            "skipped_tasks": skipped_tasks,
            "progress": progress,
            "is_first_after_skip": is_first_after_skip
        }
    
    def _ensure_agent(self, task: Task, state: WorkflowState):
        """确保 Agent 已初始化且任务匹配"""
        from guide_agent import GuideAgent
        
        if self._agent is None or self._current_task is None or self._current_task.id != task.id:
            # 构建上下文并传递给 GuideAgent
            context = self._build_context(state)
            self._agent = GuideAgent(task, context=context)
            self._current_task = task
    
    def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
        """
        执行 Guide Agent 单步
        """
        try:
            # 获取当前任务
            task = state.get_current_task()
            if not task:
                return AgentOutput(
                    thought="没有待处理的任务",
                    action=AgentAction.FINISH,
                    content=None
                )
            
            # 确保 Agent 初始化（传入 state 以构建上下文）
            self._ensure_agent(task, state)
            
            # 恢复状态
            saved_state = state.get_agent_state(self.name)
            if saved_state:
                self._load_from_dict(saved_state)
            
            # 执行单步
            decision = self._agent.step(input.content)
            
            # 构建输出
            messages = [
                AgentMessage(type="think", content=decision.thought, agent_name=self.name),
                AgentMessage(type="answer", content=decision.reply_to_user, agent_name=self.name)
            ]
            
            if decision.draft_content:
                messages.append(AgentMessage(
                    type="info", 
                    content=f"草稿预览:\n{decision.draft_content}", 
                    agent_name=self.name
                ))
            
            # 判断动作
            if self._agent.is_finished():
                # 用户已确认，准备移交 Editor
                action = AgentAction.HANDOFF
                next_agent = "editor"
                content = self._agent.execution_doc
                logger.info(f"✅ GuideAgent已完成，准备HANDOFF到Editor，ExecutionDoc: {content is not None}")
            elif self._agent.is_confirming():
                # 等待用户确认草稿（显示确认按钮）
                action = AgentAction.REQUEST_CONFIRM
                next_agent = None
                content = decision.execution_doc
                logger.info(f"✅ GuideAgent进入确认阶段，返回REQUEST_CONFIRM，ExecutionDoc: {content is not None}")
                if content:
                    logger.info(f"   ExecutionDoc详情: operation={content.operation}, section={content.section_title}")
            else:
                # 普通等待用户输入
                action = AgentAction.WAIT_INPUT
                next_agent = None
                content = decision.reply_to_user
                logger.info(f"📝 GuideAgent等待用户输入（WAIT_INPUT）")
            
            return AgentOutput(
                thought=decision.thought,
                action=action,
                content=content,
                next_agent=next_agent,
                messages=messages
            )
            
        except Exception as e:
            logger.exception("GuideAgent 执行失败")
            return AgentOutput(
                thought=f"执行出错: {str(e)}",
                action=AgentAction.FINISH,
                content=None,
                messages=[AgentMessage(type="error", content=str(e), agent_name=self.name)]
            )
    
    def stream(self, input: AgentInput, state: WorkflowState) -> Generator[AgentMessage, None, AgentOutput]:
        """Guide Agent 目前不支持真正的流式，返回完整结果"""
        output = self.invoke(input, state)
        for msg in output.messages:
            yield msg
        return output
    
    def export_state(self) -> Dict[str, Any]:
        """导出 Agent 状态"""
        if self._agent is None:
            return {}
        
        snapshot = self._agent.export_state()
        return {
            "current_state": snapshot.current_state.value,
            "messages": snapshot.messages,
            "draft": snapshot.draft,
            "execution_doc": snapshot.execution_doc.model_dump() if snapshot.execution_doc else None,
            "task_id": self._current_task.id if self._current_task else None
        }
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """恢复 Agent 状态"""
        self._load_from_dict(state)
    
    def _load_from_dict(self, state: Dict[str, Any]) -> None:
        """从字典恢复状态"""
        if not state or not self._agent:
            return
        
        from model import AgentSnapshot, ExecutionDoc
        
        exec_doc = None
        if state.get("execution_doc"):
            exec_doc = ExecutionDoc.model_validate(state["execution_doc"])
        
        snapshot = AgentSnapshot(
            current_state=GuideState(state.get("current_state", "DISCOVERY")),
            messages=state.get("messages", []),
            draft=state.get("draft"),
            execution_doc=exec_doc
        )
        self._agent.load_state(snapshot)
    
    def reset(self) -> None:
        """重置 Agent"""
        self._agent = None
        self._current_task = None

    def invoke_opening(self, state: WorkflowState) -> AgentOutput:
        """
        生成任务开场白（无需用户输入）。
        用于任务开始时主动向用户展示诊断结果和引导问题。
        
        Args:
            state: 工作流状态
            
        Returns:
            AgentOutput: 包含开场白的输出对象
        """
        try:
            # 获取当前任务
            task = state.get_current_task()
            if not task:
                return AgentOutput(
                    thought="没有待处理的任务",
                    action=AgentAction.FINISH,
                    content=None
                )
            
            # 确保 Agent 初始化（传入 state 以构建上下文）
            self._ensure_agent(task, state)
            
            # 恢复状态
            saved_state = state.get_agent_state(self.name)
            if saved_state:
                self._load_from_dict(saved_state)
            
            # 调用 generate_opening() 生成开场白
            decision = self._agent.generate_opening()
            
            # 构建输出
            messages = [
                AgentMessage(type="think", content=decision.thought, agent_name=self.name),
                AgentMessage(type="answer", content=decision.reply_to_user, agent_name=self.name)
            ]
            
            if decision.draft_content:
                messages.append(AgentMessage(
                    type="info", 
                    content=f"草稿预览:\n{decision.draft_content}", 
                    agent_name=self.name
                ))
            
            return AgentOutput(
                thought=decision.thought,
                action=AgentAction.WAIT_INPUT,  # 开场白后等待用户输入
                content=decision.reply_to_user,
                next_agent=None,
                messages=messages
            )
            
        except Exception as e:
            logger.exception("GuideAgent 开场白生成失败")
            return AgentOutput(
                thought=f"执行出错: {str(e)}",
                action=AgentAction.FINISH,
                content=None,
                messages=[AgentMessage(type="error", content=str(e), agent_name=self.name)]
            )


class EditorAgentAdapter(BaseAgent):
    """
    Editor Agent 适配器
    
    将 EditorAgent 适配到 BaseAgent 接口
    """
    
    def __init__(self):
        from editor_agent import EditorAgent
        self._agent = EditorAgent()
    
    @property
    def name(self) -> str:
        return "editor"
    
    @property
    def description(self) -> str:
        return "简历编辑执行 Agent"
    
    def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
        """
        执行 Editor Agent
        """
        try:
            exec_doc = state.current_exec_doc
            if not exec_doc:
                return AgentOutput(
                    thought="没有待执行的文档",
                    action=AgentAction.FINISH,
                    content=None
                )
            
            # 修复：正确捕获生成器返回值
            messages = []
            updated_resume = None
            
            gen = self._agent.execute_doc(exec_doc, state.resume)
            try:
                while True:
                    msg = next(gen)
                    messages.append(AgentMessage(
                        role=msg.get("role", "assistant"),
                        type=msg.get("type", "info"),
                        content=msg.get("content"),
                        agent_name=self.name
                    ))
            except StopIteration as e:
                updated_resume = e.value  # 获取返回的 Resume
            
            # 更新 state 中的 resume
            if updated_resume:
                state.resume = updated_resume
            
            return AgentOutput(
                thought="执行完成",
                action=AgentAction.FINISH,
                content=state.resume,  # 返回更新后的 resume
                messages=messages
            )
            
        except Exception as e:
            logger.exception("EditorAgent 执行失败")
            return AgentOutput(
                thought=f"执行出错: {str(e)}",
                action=AgentAction.FINISH,
                content=None,
                messages=[AgentMessage(type="error", content=str(e), agent_name=self.name)]
            )
    
    def stream(self, input: AgentInput, state: WorkflowState) -> Generator[AgentMessage, None, AgentOutput]:
        """流式执行 Editor"""
        exec_doc = state.current_exec_doc
        if not exec_doc:
            yield AgentMessage(type="error", content="没有待执行的文档", agent_name=self.name)
            return AgentOutput(thought="", action=AgentAction.FINISH, content=None)
        
        messages = []
        updated_resume = None
        
        # 修复：正确捕获生成器返回值
        gen = self._agent.execute_doc(exec_doc, state.resume)
        try:
            while True:
                msg = next(gen)
                agent_msg = AgentMessage(
                    role=msg.get("role", "assistant"),
                    type=msg.get("type", "info"),
                    content=msg.get("content"),
                    agent_name=self.name
                )
                messages.append(agent_msg)
                yield agent_msg
        except StopIteration as e:
            updated_resume = e.value  # 获取返回的 Resume
        
        # 更新 state 中的 resume
        if updated_resume:
            state.resume = updated_resume
        
        return AgentOutput(
            thought="执行完成",
            action=AgentAction.FINISH,
            content=state.resume,  # 返回更新后的 resume
            messages=messages
        )
    
    def export_state(self) -> Dict[str, Any]:
        """Editor Agent 是无状态的"""
        return {}
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """Editor Agent 是无状态的"""
        pass


def create_default_orchestrator():
    """
    创建默认配置的编排器
    
    使用示例：
    ```python
    from agent_adapters import create_default_orchestrator
    orchestrator = create_default_orchestrator()
    ```
    """
    from orchestrator import Orchestrator
    
    orch = Orchestrator()
    orch.register_agent(PlanAgentAdapter())
    orch.register_agent(GuideAgentAdapter())
    orch.register_agent(EditorAgentAdapter())
    
    return orch

