"""
Agent 抽象基类：定义统一的 Agent 接口协议。

设计目标：
1. 为三个 Agent 提供统一接口
2. 面向 LangGraph 友好，便于未来升级
3. 支持同步/流式两种调用方式
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, List, Literal
from enum import Enum
from pydantic import BaseModel, Field


class AgentAction(str, Enum):
    """Agent 动作类型"""
    CONTINUE = "continue"           # 继续当前 Agent
    HANDOFF = "handoff"             # 切换到其他 Agent
    WAIT_INPUT = "wait_input"       # 等待用户输入
    REQUEST_CONFIRM = "request_confirm"  # 等待用户确认（显示确认按钮）
    FINISH = "finish"               # 完成任务
    SWITCH_TASK = "switch_task"     # 切换到历史任务（用于回溯修改）


class AgentMessage(BaseModel):
    """
    统一的消息格式 - 用于 Agent 间通信和前端展示
    
    设计参考 LangGraph 的消息协议，便于未来迁移
    """
    role: Literal["system", "user", "assistant", "tool"] = "assistant"
    type: Literal["think", "action", "observation", "answer", "data", "error", "info", "tool"] = "answer"
    content: Any
    agent_name: Optional[str] = None  # 消息来源的 Agent
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentInput(BaseModel):
    """
    统一的 Agent 输入
    """
    content: str = Field(..., description="用户输入或上游 Agent 的输出")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class AgentOutput(BaseModel):
    """
    统一的 Agent 输出
    """
    thought: str = Field(..., description="Agent 的思考过程")
    action: AgentAction = Field(..., description="下一步动作")
    content: Any = Field(None, description="输出内容")
    next_agent: Optional[str] = Field(None, description="切换目标 Agent（当 action=HANDOFF 时）")
    messages: List[AgentMessage] = Field(default_factory=list, description="过程中产生的消息")
    # 任务切换字段（当 action=SWITCH_TASK 时使用）
    target_task_idx: Optional[int] = Field(None, description="目标任务索引（当 action=SWITCH_TASK 时）")
    target_section: Optional[str] = Field(None, description="目标任务板块名称（当 action=SWITCH_TASK 时）")


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    所有 Agent 必须实现此接口，以便：
    1. Orchestrator 统一调度
    2. 未来迁移到 LangGraph
    
    使用示例：
    ```python
    class MyAgent(BaseAgent):
        @property
        def name(self) -> str:
            return "my_agent"
        
        def invoke(self, input: AgentInput, state: WorkflowState) -> AgentOutput:
            # 实现逻辑
            pass
    ```
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Agent 唯一名称，用于路由和日志
        
        命名规范：小写字母 + 下划线，如 "plan_agent", "guide_agent"
        """
        pass
    
    @property
    def description(self) -> str:
        """Agent 描述，用于文档和调试"""
        return f"{self.name} agent"
    
    @abstractmethod
    def invoke(self, input: AgentInput, state: "WorkflowState") -> AgentOutput:
        """
        同步执行 Agent
        
        这是核心方法，必须实现。
        
        Args:
            input: 用户输入或上游输出
            state: 工作流状态（可读可写）
            
        Returns:
            AgentOutput: 包含思考、动作、输出内容
        """
        pass
    
    def stream(self, input: AgentInput, state: "WorkflowState") -> Generator[AgentMessage, None, AgentOutput]:
        """
        流式执行 Agent
        
        默认实现：调用 invoke() 并包装为单条消息
        子类可覆盖以提供真正的流式输出
        
        Yields:
            AgentMessage: 流式消息
            
        Returns:
            AgentOutput: 最终输出
        """
        output = self.invoke(input, state)
        
        # 先 yield 过程消息
        for msg in output.messages:
            yield msg
        
        # 最后 yield 结果消息
        yield AgentMessage(
            role="assistant",
            type="answer",
            content=output.content,
            agent_name=self.name
        )
        
        return output
    
    @abstractmethod
    def export_state(self) -> Dict[str, Any]:
        """
        导出 Agent 内部状态
        
        用于：
        1. 会话持久化
        2. 断点续传
        3. 调试和监控
        
        Returns:
            可 JSON 序列化的状态字典
        """
        pass
    
    @abstractmethod
    def load_state(self, state: Dict[str, Any]) -> None:
        """
        恢复 Agent 内部状态
        
        Args:
            state: 之前 export_state() 导出的状态
        """
        pass
    
    def reset(self) -> None:
        """
        重置 Agent 状态
        
        默认实现：空操作
        子类可覆盖以清理内部状态
        """
        pass


class AgentRegistry:
    """
    Agent 注册中心
    
    用于管理和查找 Agent 实例
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent) -> None:
        """注册 Agent"""
        self._agents[agent.name] = agent
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(name)
    
    def list_agents(self) -> List[str]:
        """列出所有已注册的 Agent"""
        return list(self._agents.keys())
    
    def __contains__(self, name: str) -> bool:
        return name in self._agents


# 全局注册中心（可选使用）
agent_registry = AgentRegistry()

