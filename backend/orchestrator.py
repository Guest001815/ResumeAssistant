"""
编排器：管理 Agent 间的流转和协作。

设计目标：
1. 解耦 API 层与 Agent 层
2. 集中管理工作流逻辑
3. 为 LangGraph 升级预留接口

使用示例：
```python
orchestrator = Orchestrator()
orchestrator.register_agent(PlanAgentAdapter())
orchestrator.register_agent(GuideAgentAdapter())
orchestrator.register_agent(EditorAgentAdapter())

# 执行工作流
for msg in orchestrator.run_plan(state, user_intent):
    print(msg)
```

未来升级 LangGraph：
```python
from langgraph.graph import StateGraph

graph = StateGraph(WorkflowState)
graph.add_node("plan", orchestrator.get_agent("plan").invoke)
graph.add_node("guide", orchestrator.get_agent("guide").invoke)
graph.add_edge("plan", "guide")
...
```
"""
import logging
from typing import Dict, Optional, Generator, Callable, Any

from base_agent import BaseAgent, AgentInput, AgentOutput, AgentMessage, AgentAction
from workflow_state import WorkflowState, WorkflowStage
from model import TaskStatus

logger = logging.getLogger(__name__)


# 路由函数类型
RouterFunc = Callable[[WorkflowState], Optional[str]]


class Orchestrator:
    """
    编排器：管理 Agent 间的流转
    
    职责：
    1. 注册和管理 Agent
    2. 定义路由规则
    3. 执行工作流
    4. 处理 Agent 间的切换
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._routers: Dict[str, RouterFunc] = {}
        
        # 默认路由规则
        self._default_routes: Dict[str, str] = {
            "plan": "guide",
            "guide": "editor",
            "editor": "guide",
        }
    
    # ==================== Agent 管理 ====================
    
    def register_agent(self, agent: BaseAgent) -> "Orchestrator":
        """
        注册 Agent
        
        支持链式调用：
        orchestrator.register_agent(a).register_agent(b)
        """
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
        return self
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(name)
    
    def list_agents(self) -> list:
        """列出所有 Agent"""
        return list(self._agents.keys())
    
    # ==================== 路由管理 ====================
    
    def set_router(self, from_agent: str, router: RouterFunc) -> "Orchestrator":
        """
        设置自定义路由规则
        
        Args:
            from_agent: 源 Agent 名称
            router: 路由函数，接收 state，返回下一个 Agent 名称
        """
        self._routers[from_agent] = router
        return self
    
    def set_default_route(self, from_agent: str, to_agent: str) -> "Orchestrator":
        """设置默认路由"""
        self._default_routes[from_agent] = to_agent
        return self
    
    def _get_next_agent(self, current_agent: str, state: WorkflowState, output: AgentOutput) -> Optional[str]:
        """
        确定下一个 Agent
        
        优先级：
        1. Agent 输出指定的 next_agent
        2. 自定义路由函数
        3. 默认路由
        """
        # 1. Agent 主动指定
        if output.action == AgentAction.HANDOFF and output.next_agent:
            return output.next_agent
        
        # 2. 自定义路由
        if current_agent in self._routers:
            return self._routers[current_agent](state)
        
        # 3. 默认路由
        return self._default_routes.get(current_agent)
    
    # ==================== 工作流执行 ====================
    
    def run_plan(self, state: WorkflowState, user_intent: str) -> Generator[AgentMessage, None, None]:
        """
        执行 Plan Agent
        
        Args:
            state: 工作流状态
            user_intent: 用户意图
            
        Yields:
            AgentMessage: 过程消息
        """
        agent = self._agents.get("plan")
        if not agent:
            yield AgentMessage(type="error", content="Plan Agent 未注册")
            return
        
        state.current_stage = WorkflowStage.PLANNING
        state.user_intent = user_intent
        
        input = AgentInput(content=user_intent, context={"resume": state.resume.model_dump()})
        
        try:
            # 流式执行，捕获最终 AgentOutput（StopIteration.value）
            output = None
            stream = agent.stream(input, state)
            try:
                for msg in stream:
                    yield msg
            except StopIteration as e:
                output = e.value
            # 若流式未返回输出（理论不应发生），回退到同步执行
            if output is None:
                output = agent.invoke(input, state)
            
            # 保存 Agent 状态
            state.save_agent_state(agent.name, agent.export_state())
            
            # 更新工作流状态
            if output.action == AgentAction.FINISH and output.content:
                state.plan = output.content
                state.current_stage = WorkflowStage.GUIDING
                yield AgentMessage(
                    type="info",
                    content=f"计划生成完成，共 {len(state.plan.tasks)} 个任务",
                    agent_name=agent.name
                )
            else:
                yield AgentMessage(type="error", content="Plan Agent 未能生成计划")
                
        except Exception as e:
            logger.exception("Plan Agent 执行失败")
            state.current_stage = WorkflowStage.ERROR
            state.error_message = str(e)
            yield AgentMessage(type="error", content=str(e))
    
    def run_guide_step(self, state: WorkflowState, user_input: str) -> Generator[AgentMessage, None, AgentOutput]:
        """
        执行 Guide Agent 单步
        
        Args:
            state: 工作流状态
            user_input: 用户输入
            
        Yields:
            AgentMessage: 过程消息
            
        Returns:
            AgentOutput: Agent 输出
        """
        agent = self._agents.get("guide")
        if not agent:
            yield AgentMessage(type="error", content="Guide Agent 未注册")
            return AgentOutput(thought="", action=AgentAction.FINISH, content=None)
        
        current_task = state.get_current_task()
        if not current_task:
            yield AgentMessage(type="info", content="所有任务已完成")
            return AgentOutput(thought="", action=AgentAction.FINISH, content=None)
        
        # 恢复 Agent 状态
        saved_state = state.get_agent_state(agent.name)
        if saved_state:
            agent.load_state(saved_state)
        
        state.current_stage = WorkflowStage.GUIDING
        state.update_task_status(current_task.id, TaskStatus.IN_PROGRESS)
        
        input = AgentInput(
            content=user_input, 
            context={
                "task": current_task.model_dump(),
                "resume": state.resume.model_dump()
            }
        )
        
        try:
            # 调用Agent的stream方法
            stream = agent.stream(input, state)
            output = None
            
            # 消费生成器并收集messages
            messages = []
            try:
                for msg in stream:
                    messages.append(msg)
                    yield msg
            except StopIteration as e:
                # 捕获生成器的返回值
                output = e.value
                logger.info(f"从生成器捕获output: {type(output)}")
            
            # 如果没有捕获到output，直接调用invoke
            if output is None:
                logger.warning("生成器未返回output，调用invoke")
                output = agent.invoke(input, state)
            
            # 保存 Agent 状态
            state.save_agent_state(agent.name, agent.export_state())
            
            # 处理输出 - 根据不同 action 更新状态
            if output.action == AgentAction.REQUEST_CONFIRM:
                # Guide Agent 请求用户确认草稿
                state.current_stage = WorkflowStage.CONFIRMING
                if hasattr(output, 'content') and output.content:
                    state.current_exec_doc = output.content
                logger.info("Guide Agent 进入确认阶段，等待用户确认")
                
            elif output.action == AgentAction.HANDOFF and output.next_agent == "editor":
                # Guide Agent 确认完成，准备移交 Editor
                state.current_stage = WorkflowStage.CONFIRMING
                if hasattr(output, 'content') and output.content:
                    state.current_exec_doc = output.content
                logger.info("Guide Agent 完成，准备移交 Editor")
            
            logger.info(f"run_guide_step返回output: action={output.action}, messages={len(output.messages)}")
            return output
            
        except Exception as e:
            logger.exception("Guide Agent 执行失败")
            state.error_message = str(e)
            yield AgentMessage(type="error", content=str(e))
            return AgentOutput(thought=str(e), action=AgentAction.FINISH, content=None)
    
    def run_editor(self, state: WorkflowState) -> Generator[AgentMessage, None, None]:
        """
        执行 Editor Agent
        
        Args:
            state: 工作流状态
            
        Yields:
            AgentMessage: 过程消息
        """
        agent = self._agents.get("editor")
        if not agent:
            yield AgentMessage(type="error", content="Editor Agent 未注册")
            return
        
        if not state.current_exec_doc:
            yield AgentMessage(type="error", content="没有待执行的文档")
            return
        
        state.current_stage = WorkflowStage.EDITING
        
        input = AgentInput(
            content="execute",
            context={
                "exec_doc": state.current_exec_doc.model_dump(),
                "resume": state.resume.model_dump()
            }
        )
        
        try:
            output = None
            stream = agent.stream(input, state)
            try:
                for msg in stream:
                    yield msg
            except StopIteration as e:
                output = e.value
            if output is None:
                output = agent.invoke(input, state)
            
            # 更新任务状态
            if output.action == AgentAction.FINISH:
                completed_task = state.get_task_by_id(state.current_exec_doc.task_id)
                state.update_task_status(state.current_exec_doc.task_id, TaskStatus.COMPLETED)
                state.current_exec_doc = None
                progress = state.get_progress()
                
                # 构建任务完成消息
                lines = [
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"✅ 任务 {completed_task.id} 已完成：{completed_task.section}",
                    "",
                    f"📋 进度：已完成 {progress['completed_tasks']}/{progress['total_tasks']}",
                ]
                
                # 检查是否所有任务完成
                if state.is_all_tasks_done():
                    state.current_stage = WorkflowStage.COMPLETED
                    lines.extend([
                        "",
                        "🎉 恭喜！所有优化任务已完成！",
                        "",
                        "您的简历已经过全面优化，现在可以导出使用了。"
                    ])
                else:
                    # 还有下一个任务，移动到下一个任务并清除 Guide Agent 状态
                    state.move_to_next_task()
                    state.current_stage = WorkflowStage.GUIDING
                    next_task = state.get_current_task()
                    if next_task:
                        lines.extend([
                            "",
                            f"⏭️ 接下来：任务 {next_task.id} - {next_task.section}",
                            f"   问题：{next_task.diagnosis[:50]}...",
                            "",
                            "💡 继续对话，我会引导你完成下一个优化。"
                        ])
                
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                yield AgentMessage(type="info", content="\n".join(lines))
                
                # 返回更新后的简历
                yield AgentMessage(
                    type="data",
                    content=state.resume.model_dump(),
                    agent_name=agent.name
                )
            
        except Exception as e:
            logger.exception("Editor Agent 执行失败")
            state.error_message = str(e)
            yield AgentMessage(type="error", content=str(e))
    
    def skip_task(self, state: WorkflowState) -> AgentMessage:
        """跳过当前任务"""
        current_task = state.get_current_task()
        if not current_task:
            return AgentMessage(type="error", content="没有可跳过的任务")
        
        next_task = state.skip_current_task()
        progress = state.get_progress()
        
        # 简化消息，由前端调用guideInit获取自然过渡话术
        if next_task:
            return AgentMessage(
                type="info", 
                content=f"已跳过任务，进度：{progress['completed_tasks']}/{progress['total_tasks']}"
            )
        elif state.is_all_tasks_done():
            state.current_stage = WorkflowStage.COMPLETED
            return AgentMessage(type="info", content="🎉 所有任务已处理完成！")
        
        return AgentMessage(type="info", content="已跳过当前任务")
    
    def next_task(self, state: WorkflowState) -> AgentMessage:
        """进入下一个任务"""
        next_task = state.move_to_next_task()
        
        if next_task:
            return AgentMessage(
                type="info",
                content=f"进入任务 {next_task.id}: {next_task.section}"
            )
        elif state.is_all_tasks_done():
            state.current_stage = WorkflowStage.COMPLETED
            return AgentMessage(type="info", content="所有任务已完成！")
        else:
            return AgentMessage(type="info", content="没有更多任务")


# ==================== Agent 适配器基类 ====================

class AgentAdapter(BaseAgent):
    """
    Agent 适配器基类
    
    用于将现有 Agent 适配到 BaseAgent 接口
    """
    
    def __init__(self, wrapped_agent):
        self._wrapped = wrapped_agent
    
    @property
    def wrapped(self):
        return self._wrapped


# 全局编排器（可选使用）
orchestrator = Orchestrator()

