"""
简历助手 API v2：基于 Orchestrator 的解耦架构。

架构说明：
- API 层只负责 HTTP 处理和参数校验
- 业务逻辑委托给 Orchestrator
- Agent 通过适配器模式统一接口

端点：
- POST /session/create - 创建会话
- POST /session/{id}/plan - 生成修改计划
- POST /session/{id}/guide - Guide Agent 单步交互
- POST /session/{id}/confirm - 确认并执行 Editor
- POST /session/{id}/skip - 跳过当前任务
- GET /session/{id}/progress - 获取进度
- POST /session/{id}/next - 进入下一个任务
- GET /session/{id} - 获取会话详情
- DELETE /session/{id} - 删除会话

保留端点（兼容旧版）：
- POST /run - 原有 Editor 交互模式
- POST /parse_resume - 解析 PDF 简历
"""
import json
import logging
from typing import Dict, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from model import Resume, TaskList, Task, ExecutionDoc, TaskStatus
from workflow_state import WorkflowState, WorkflowStage, workflow_manager
from orchestrator import Orchestrator
from agent_adapters import PlanAgentAdapter, GuideAgentAdapter, EditorAgentAdapter, create_default_orchestrator
from base_agent import AgentMessage, AgentAction, AgentInput
from parse_resume import parse_resume_content, parse_resume_with_progress
from session_persistence import SessionMetadata, session_persistence
from session_utils import extract_session_metadata
from resume_storage import resume_storage
from datetime import datetime

# 保留原有 EditorAgent 用于 /run 端点
from editor_agent import EditorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== 初始化 ====================
# 修复: 添加 TaskStatus 导入 (v2.1.1)

app = FastAPI(title="简历助手 API", version="2.1.1", description="基于 Orchestrator 的解耦架构")

# 创建编排器
orchestrator = create_default_orchestrator()

# 保留原有 agent 用于兼容
legacy_agent = EditorAgent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development to avoid CORS issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """服务启动时自动迁移简历"""
    logger.info("服务启动，检查是否需要迁移简历...")
    
    # 检查独立存储是否为空
    existing_resumes = resume_storage.list_resumes()
    
    if len(existing_resumes) == 0:
        logger.info("独立简历存储为空，开始从会话迁移...")
        # 执行迁移（函数定义在文件后面，但Python在运行时可以找到）
        _do_startup_migration()
    else:
        logger.info(f"独立简历存储已有 {len(existing_resumes)} 个简历，跳过迁移")


def _do_startup_migration():
    """启动时执行的迁移逻辑（独立函数避免循环引用）"""
    migrated = 0
    skipped = 0
    errors = 0
    
    try:
        sessions = session_persistence.list_all_sessions()
        logger.info(f"找到 {len(sessions)} 个会话需要迁移")
        
        for session_meta in sessions:
            try:
                state = workflow_manager.get(session_meta.id)
                if not state or not state.resume:
                    skipped += 1
                    continue
                
                resume_storage.save_resume(state.resume)
                migrated += 1
                logger.info(f"已迁移简历: {state.resume.basics.name or '未命名'}")
                
            except Exception as e:
                logger.warning(f"迁移会话 {session_meta.id} 的简历失败: {e}")
                errors += 1
                continue
        
        logger.info(f"启动迁移完成: 成功={migrated}, 跳过={skipped}, 错误={errors}")
        
    except Exception as e:
        logger.exception(f"启动迁移过程出错: {e}")


# ==================== 请求/响应模型 ====================

class RunRequest(BaseModel):
    input: str
    resume: Optional[Resume] = None


class CreateSessionRequest(BaseModel):
    resume: Resume


class CreateSessionResponse(BaseModel):
    session_id: str
    message: str


class PlanRequest(BaseModel):
    user_intent: str


class PlanResponse(BaseModel):
    plan: TaskList
    message: str


class GuideRequest(BaseModel):
    user_input: str


class GuideResponse(BaseModel):
    thought: str
    reply: str
    state: str
    draft: Optional[str] = None
    execution_doc: Optional[ExecutionDoc] = None
    is_confirming: bool = False
    is_finished: bool = False


class ProgressResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    skipped_tasks: int
    current_task_idx: int
    current_task: Optional[Task] = None
    tasks_summary: list


class NextTaskResponse(BaseModel):
    success: bool
    has_next: bool
    task: Optional[Task] = None
    message: str


class SessionMetadataResponse(BaseModel):
    id: str
    name: Optional[str]
    resume_file_name: str
    job_title: str
    job_company: str
    created_at: str
    updated_at: str
    progress: Dict[str, int]
    status: str


class SessionResponse(BaseModel):
    id: str
    name: Optional[str]
    resume_file_name: str
    job_title: str
    job_company: str
    created_at: str
    updated_at: str
    progress: Dict[str, int]
    status: str
    resume: Resume
    user_intent: str
    plan: Optional[TaskList] = None
    current_task_idx: int
    
    
class UpdateSessionNameRequest(BaseModel):
    name: str


# ==================== SSE 辅助函数 ====================

def _sse(data: dict) -> str:
    """格式化 SSE 消息"""
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


def _agent_msg_to_sse(msg: AgentMessage) -> str:
    """将 AgentMessage 转换为 SSE"""
    return _sse({
        "role": msg.role,
        "type": msg.type,
        "content": msg.content if not isinstance(msg.content, BaseModel) else msg.content.model_dump(),
        "agent": msg.agent_name
    })


def _sse_guard(logger):
    """SSE 错误保护装饰器"""
    def deco(func):
        def wrapper(*args, **kwargs):
            try:
                gen = func(*args, **kwargs)
            except Exception as e:
                logger.exception("SSE 生成器创建异常")
                def _err():
                    yield _sse({"role": "assistant", "type": "error", "content": f"错误: {e}"})
                return _err()

            def _safe():
                try:
                    for m in gen:
                        yield m
                except Exception as e:
                    logger.exception("SSE 迭代发生异常")
                    yield _sse({"role": "assistant", "type": "error", "content": f"错误: {e}"})
            return _safe()
        return wrapper
    return deco


# ==================== 会话管理端点 ====================

@app.post("/session/create", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    """创建新会话"""
    logger.info("收到请求 /session/create")
    
    state = workflow_manager.create(req.resume)
    
    # 创建默认的元数据（暂时没有user_intent）
    metadata = SessionMetadata(
        id=state.session_id,
        name=None,
        resume_file_name=state.resume.basics.name or "未命名简历",
        job_title="待设置",
        job_company="待设置",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        progress={"completed": 0, "total": 0},
        status="active"
    )
    
    # 保存到磁盘
    workflow_manager.save_with_metadata(state, metadata)
    
    return CreateSessionResponse(
        session_id=state.session_id,
        message="会话创建成功"
    )


@app.post("/session/{session_id}/plan", response_model=PlanResponse)
async def generate_plan(session_id: str, req: PlanRequest):
    """执行 Plan Agent，生成修改计划"""
    logger.info(f"收到请求 /session/{session_id}/plan")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    try:
        # 保存user_intent到state
        state.user_intent = req.user_intent
        
        # 通过编排器执行 Plan Agent
        messages = []
        for msg in orchestrator.run_plan(state, req.user_intent):
            messages.append(msg)
        
        if not state.plan:
            raise HTTPException(status_code=500, detail="计划生成失败")
        
        # 提取会话元数据并更新
        metadata_info = extract_session_metadata(state.resume, req.user_intent)
        
        # 加载或创建metadata
        metadata = session_persistence.load_metadata(session_id)
        if not metadata:
            metadata = SessionMetadata(
                id=session_id,
                name=metadata_info["name"],
                resume_file_name=metadata_info["resume_file_name"],
                job_title=metadata_info["job_title"],
                job_company=metadata_info["job_company"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                progress={"completed": 0, "total": len(state.plan.tasks)},
                status="active"
            )
        else:
            # 更新元数据
            metadata.name = metadata_info["name"]
            metadata.job_title = metadata_info["job_title"]
            metadata.job_company = metadata_info["job_company"]
            metadata.updated_at = datetime.now().isoformat()
            metadata.progress["total"] = len(state.plan.tasks)
        
        # 保存
        workflow_manager.save_with_metadata(state, metadata)
        
        return PlanResponse(
            plan=state.plan,
            message=f"修改计划生成成功，共 {len(state.plan.tasks)} 个任务"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Plan Agent 执行失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/plan_stream")
async def generate_plan_stream(session_id: str, req: PlanRequest):
    """
    流式生成修改计划（带伪进度反馈）
    
    实时推送计划生成进度：
    - { "stage": "analyzing", "progress": 30, "message": "AI正在分析..." }
    - { "stage": "complete", "progress": 100, "message": "完成！", "plan": {...} }
    - { "stage": "error", "message": "错误信息" }
    """
    logger.info(f"收到请求 /session/{session_id}/plan_stream")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 保存user_intent到state
    state.user_intent = req.user_intent
    
    def _iter():
        try:
            # 获取 Plan Agent
            from plan_agent import PlanAgent
            agent = PlanAgent()
            
            # 使用带进度的生成方法
            for progress_event in agent.generate_plan_with_progress(req.user_intent, state.resume):
                yield _sse(progress_event)
                
                # 如果完成，保存到state和metadata
                if progress_event.get("stage") == "complete" and progress_event.get("plan"):
                    try:
                        # 将plan转换为TaskList对象
                        state.plan = TaskList.model_validate(progress_event["plan"])
                        
                        # 提取会话元数据并更新
                        metadata_info = extract_session_metadata(state.resume, req.user_intent)
                        
                        # 加载或创建metadata
                        metadata = session_persistence.load_metadata(session_id)
                        if not metadata:
                            metadata = SessionMetadata(
                                id=session_id,
                                name=metadata_info["name"],
                                resume_file_name=metadata_info["resume_file_name"],
                                job_title=metadata_info["job_title"],
                                job_company=metadata_info["job_company"],
                                created_at=datetime.now().isoformat(),
                                updated_at=datetime.now().isoformat(),
                                progress={"completed": 0, "total": len(state.plan.tasks)},
                                status="active"
                            )
                        else:
                            # 更新元数据
                            metadata.name = metadata_info["name"]
                            metadata.job_title = metadata_info["job_title"]
                            metadata.job_company = metadata_info["job_company"]
                            metadata.updated_at = datetime.now().isoformat()
                            metadata.progress["total"] = len(state.plan.tasks)
                        
                        # 保存
                        workflow_manager.save_with_metadata(state, metadata)
                        logger.info(f"计划生成成功，共 {len(state.plan.tasks)} 个任务")
                    except Exception as e:
                        logger.exception("保存计划失败")
                        yield _sse({"stage": "error", "message": f"保存失败: {e}"})
                        
        except Exception as e:
            logger.exception("流式生成计划失败")
            yield _sse({"stage": "error", "message": f"生成失败: {e}"})
    
    return StreamingResponse(
        _iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/session/{session_id}/guide/init", response_model=GuideResponse)
async def guide_init(session_id: str):
    """
    Guide Agent 自动开场白接口
    
    在每个任务开始时调用，生成结构化的开场白，包含：
    - 任务简介
    - 问题诊断
    - 优化目标
    - 引导问题
    
    无需用户输入，由 LLM 主动生成引导消息。
    """
    logger.info(f"收到请求 /session/{session_id}/guide/init")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if not state.plan:
        raise HTTPException(status_code=400, detail="请先生成修改计划")
    
    current_task = state.get_current_task()
    if not current_task:
        raise HTTPException(status_code=400, detail="所有任务已完成")
    
    try:
        # 获取 Guide Agent（使用适配器）
        agent = orchestrator.get_agent("guide")
        if not agent:
            raise HTTPException(status_code=500, detail="Guide Agent 未注册")
        
        # 设置工作流状态
        state.current_stage = WorkflowStage.GUIDING
        state.update_task_status(current_task.id, TaskStatus.IN_PROGRESS)
        
        # 调用 invoke_opening() 生成开场白
        logger.info("调用 Guide Agent invoke_opening 方法")
        output = agent.invoke_opening(state)
        logger.info(f"Guide Agent 开场白生成完成: messages数量={len(output.messages)}")
        
        # 保存 Agent 状态
        state.save_agent_state(agent.name, agent.export_state())
        
        # 保存到磁盘
        workflow_manager.save(state)
        
        # 安全地获取reply内容
        reply = ""
        if output.messages:
            # 找到 answer 类型的消息
            for msg in output.messages:
                if msg.type == "answer":
                    if isinstance(msg.content, str):
                        reply = msg.content
                    elif isinstance(msg.content, BaseModel):
                        reply = msg.content.model_dump_json()
                    else:
                        reply = str(msg.content)
                    break
        
        return GuideResponse(
            thought=output.thought,
            reply=reply,
            state=state.current_stage.value,
            draft=None,  # 开场白不包含草稿
            execution_doc=None,
            is_confirming=False,
            is_finished=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Guide Agent 开场白生成失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/guide", response_model=GuideResponse)
async def guide_step(session_id: str, req: GuideRequest):
    """Guide Agent 单步交互"""
    logger.info(f"收到请求 /session/{session_id}/guide")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if not state.plan:
        raise HTTPException(status_code=400, detail="请先生成修改计划")
    
    current_task = state.get_current_task()
    if not current_task:
        raise HTTPException(status_code=400, detail="所有任务已完成")
    
    try:
        # 方案1：直接调用 invoke，不使用生成器返回值
        agent = orchestrator.get_agent("guide")
        if not agent:
            raise HTTPException(status_code=500, detail="Guide Agent 未注册")
        
        # 恢复 Agent 状态
        saved_state = state.get_agent_state(agent.name)
        if saved_state:
            agent.load_state(saved_state)
        
        state.current_stage = WorkflowStage.GUIDING
        state.update_task_status(current_task.id, TaskStatus.IN_PROGRESS)
        
        input = AgentInput(
            content=req.user_input,
            context={
                "task": current_task.model_dump(),
                "resume": state.resume.model_dump()
            }
        )
        
        # 直接调用 invoke
        logger.info("调用 Guide Agent invoke 方法")
        output = agent.invoke(input, state)
        logger.info(f"Guide Agent 返回: action={output.action}, messages数量={len(output.messages)}")
        
        # 保存 Agent 状态
        state.save_agent_state(agent.name, agent.export_state())
        
        # ✅ 关键修复：同步状态到 WorkflowState（与 orchestrator 保持一致）
        if output.action == AgentAction.REQUEST_CONFIRM:
            state.current_stage = WorkflowStage.CONFIRMING
            if isinstance(output.content, ExecutionDoc):
                state.current_exec_doc = output.content
                logger.info(f"✅ ExecutionDoc已保存到state: operation={output.content.operation}, section={output.content.section_title}")
            else:
                logger.warning(f"⚠️ REQUEST_CONFIRM但output.content不是ExecutionDoc，类型: {type(output.content)}")
        elif output.action == AgentAction.HANDOFF and output.next_agent == "editor":
            state.current_stage = WorkflowStage.CONFIRMING
            if isinstance(output.content, ExecutionDoc):
                state.current_exec_doc = output.content
                logger.info(f"✅ ExecutionDoc已保存到state（HANDOFF）: operation={output.content.operation}, section={output.content.section_title}")
        
        # ✅ 保存状态到磁盘（包含新的 current_exec_doc）
        workflow_manager.save(state)
        logger.info(f"✅ WorkflowState已保存，current_exec_doc: {state.current_exec_doc is not None}")
        
        # 处理输出
        # 使用双重检查：优先使用 state.current_stage（由 orchestrator 同步），同时检查 output.action
        is_confirming = (
            state.current_stage == WorkflowStage.CONFIRMING or 
            output.action == AgentAction.REQUEST_CONFIRM
        )
        is_finished = output.action == AgentAction.HANDOFF and output.next_agent == "editor"
        
        # 从 messages 中提取 draft
        draft = None
        for msg in output.messages:
            if msg.type == "info" and "草稿预览" in str(msg.content):
                draft = str(msg.content).replace("草稿预览:\n", "")
        
        # 安全地获取reply内容（查找type="answer"的消息）
        reply = ""
        if output.messages:
            # 记录消息结构以便调试
            logger.info(f"📝 Guide返回消息结构: {[(msg.type, len(str(msg.content)) if msg.content else 0) for msg in output.messages]}")
            # 找到 answer 类型的消息
            for msg in output.messages:
                if msg.type == "answer":
                    if isinstance(msg.content, str):
                        reply = msg.content
                    elif isinstance(msg.content, BaseModel):
                        reply = msg.content.model_dump_json()
                    else:
                        reply = str(msg.content)
                    logger.info(f"✅ 成功提取reply_to_user，长度: {len(reply)}")
                    break
            if not reply:
                logger.warning(f"⚠️ 未找到answer类型消息，messages类型: {[msg.type for msg in output.messages]}")
        
        return GuideResponse(
            thought=output.thought,
            reply=reply,
            state=state.current_stage.value,
            draft=draft,
            execution_doc=output.content if isinstance(output.content, ExecutionDoc) else None,
            is_confirming=is_confirming,
            is_finished=is_finished
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Guide Agent 执行失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/confirm")
async def confirm_and_execute(session_id: str):
    """用户确认后执行 Editor Agent"""
    logger.info(f"收到请求 /session/{session_id}/confirm")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    logger.info(f"🔍 检查ExecutionDoc: current_exec_doc存在={state.current_exec_doc is not None}")
    logger.info(f"   当前WorkflowStage: {state.current_stage.value}")
    if state.current_exec_doc:
        logger.info(f"   ExecutionDoc详情: operation={state.current_exec_doc.operation}, section={state.current_exec_doc.section_title}, item_id={state.current_exec_doc.item_id}")
    
    if not state.current_exec_doc:
        logger.error(f"❌ 没有待确认的执行文档！current_stage={state.current_stage}")
        raise HTTPException(status_code=400, detail="没有待确认的执行文档")
    
    @_sse_guard(logger)
    def _iter():
        try:
            logger.info(f"🚀 开始执行Editor Agent，操作类型: {state.current_exec_doc.operation}")
            # 通过编排器执行 Editor
            for msg in orchestrator.run_editor(state):
                yield _agent_msg_to_sse(msg)
            
            # 保存状态到磁盘（包括更新后的任务进度）
            workflow_manager.save(state)
            logger.info(f"✅ 状态已保存，进度: {state.get_progress()}")
            
            # 返回完成信息
            yield _sse({
                "role": "assistant",
                "type": "complete",
                "content": {
                    "success": True,
                    "message": "执行完成",
                    "resume": state.resume.model_dump()
                }
            })
            
        except Exception as e:
            logger.exception("Editor Agent 执行失败")
            yield _sse({"role": "assistant", "type": "error", "content": str(e)})
    
    return StreamingResponse(
        _iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/session/{session_id}/skip")
async def skip_task(session_id: str):
    """跳过当前任务"""
    logger.info(f"收到请求 /session/{session_id}/skip")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    result = orchestrator.skip_task(state)
    next_task = state.get_current_task()
    
    return {
        "success": True,
        "message": result.content,
        "next_task": next_task.model_dump() if next_task else None
    }


@app.get("/session/{session_id}/progress", response_model=ProgressResponse)
async def get_progress(session_id: str):
    """获取任务进度"""
    logger.info(f"收到请求 /session/{session_id}/progress")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    progress = state.get_progress()
    
    return ProgressResponse(**progress)


@app.post("/session/{session_id}/next", response_model=NextTaskResponse)
async def next_task(session_id: str):
    """进入下一个任务"""
    logger.info(f"收到请求 /session/{session_id}/next")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    result = orchestrator.next_task(state)
    next_task = state.get_current_task()
    
    return NextTaskResponse(
        success=True,
        has_next=next_task is not None,
        task=next_task,
        message=result.content
    )


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话详细信息"""
    logger.info(f"收到请求 /session/{session_id}")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {
        "session_id": state.session_id,
        "user_intent": state.user_intent,
        "current_stage": state.current_stage,
        "has_plan": state.plan is not None,
        "current_task_idx": state.current_task_idx,
        "has_exec_doc": state.current_exec_doc is not None,
        "resume": state.resume.model_dump()
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    logger.info(f"收到请求 DELETE /session/{session_id}")
    
    success = workflow_manager.delete(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"success": True, "message": "会话已删除"}


# ==================== 会话管理端点（新增）====================

@app.get("/sessions", response_model=list)
async def list_sessions():
    """获取所有会话列表"""
    logger.info("收到请求 GET /sessions")
    
    try:
        sessions = session_persistence.list_all_sessions()
        return [s.to_dict() for s in sessions]
    except Exception as e:
        logger.exception("获取会话列表失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_full_session(session_id: str):
    """获取完整会话数据"""
    logger.info(f"收到请求 GET /sessions/{session_id}")
    
    # 加载workflow state
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 加载metadata
    metadata = session_persistence.load_metadata(session_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="会话元数据不存在")
    
    # 构建响应
    progress = state.get_progress()
    
    return SessionResponse(
        id=state.session_id,
        name=metadata.name,
        resume_file_name=metadata.resume_file_name,
        job_title=metadata.job_title,
        job_company=metadata.job_company,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
        progress=metadata.progress,
        status=metadata.status,
        resume=state.resume,
        user_intent=state.user_intent or "",
        plan=state.plan,
        current_task_idx=state.current_task_idx
    )


@app.patch("/sessions/{session_id}/metadata")
async def update_session_metadata(session_id: str, req: UpdateSessionNameRequest):
    """更新会话元数据（名称）"""
    logger.info(f"收到请求 PATCH /sessions/{session_id}/metadata")
    
    # 加载metadata
    metadata = session_persistence.load_metadata(session_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 更新名称和时间戳
    metadata.name = req.name
    metadata.updated_at = datetime.now().isoformat()
    
    # 加载state并重新保存（触发metadata更新）
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话状态不存在")
    
    # 保存
    workflow_manager.save_with_metadata(state, metadata)
    
    return metadata.to_dict()


@app.put("/session/{session_id}/resume")
async def update_resume(session_id: str, resume: Resume):
    """更新会话中的简历数据"""
    logger.info(f"收到请求 PUT /session/{session_id}/resume")
    
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    try:
        # 更新简历数据
        state.resume = resume
        workflow_manager.save(state)
        
        logger.info(f"成功更新会话 {session_id} 的简历数据")
        return {
            "success": True,
            "message": "简历数据已更新",
            "resume": resume.model_dump()
        }
    except Exception as e:
        logger.exception(f"更新简历数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resumes/recent")
async def get_recent_resume():
    """获取最近使用的简历（从最近的会话中提取）"""
    logger.info("收到请求 GET /resumes/recent")
    
    try:
        # 获取所有会话，按更新时间排序
        sessions = session_persistence.list_all_sessions()
        
        if not sessions:
            raise HTTPException(status_code=404, detail="没有找到历史会话")
        
        # 获取最近的会话
        recent_session = sessions[0]
        
        # 加载完整的会话数据
        state = workflow_manager.get(recent_session.id)
        if not state:
            raise HTTPException(status_code=404, detail="无法加载会话数据")
        
        logger.info(f"成功获取最近简历，来自会话 {recent_session.id}")
        return {
            "resume": state.resume.model_dump(),
            "session_id": recent_session.id,
            "last_used": recent_session.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("获取最近简历失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resumes/list")
async def list_all_resumes():
    """获取所有历史简历的唯一列表（按姓名去重）"""
    logger.info("收到请求 GET /resumes/list")
    
    try:
        sessions = session_persistence.list_all_sessions()
        
        if not sessions:
            return []
        
        # 用字典按姓名去重，保留最新的
        resume_map = {}
        
        for session_meta in sessions:
            state = workflow_manager.get(session_meta.id)
            if not state:
                continue
            
            resume = state.resume
            name = resume.basics.name or "未命名"
            
            # 如果这个姓名的简历不存在，或者当前会话更新时间更晚，则更新
            if name not in resume_map or session_meta.updated_at > resume_map[name]["last_used"]:
                resume_map[name] = {
                    "resume": resume.model_dump(),
                    "session_id": session_meta.id,
                    "last_used": session_meta.updated_at,
                    "name": name,
                    "label": resume.basics.label or ""
                }
        
        # 转换为列表并按最后使用时间排序
        resumes = list(resume_map.values())
        resumes.sort(key=lambda x: x["last_used"], reverse=True)
        
        logger.info(f"成功获取 {len(resumes)} 个唯一简历")
        return resumes
        
    except Exception as e:
        logger.exception("获取简历列表失败")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 独立简历存储 API ====================

@app.get("/resumes")
async def get_stored_resumes():
    """获取所有独立存储的简历列表"""
    logger.info("收到请求 GET /resumes")
    
    try:
        stored_resumes = resume_storage.list_resumes()
        
        # 转换为前端需要的格式
        result = []
        for stored in stored_resumes:
            result.append({
                "id": stored.metadata.id,
                "name": stored.metadata.name,
                "label": stored.metadata.label,
                "created_at": stored.metadata.created_at,
                "updated_at": stored.metadata.updated_at,
                "resume": stored.resume.model_dump()
            })
        
        logger.info(f"成功获取 {len(result)} 个独立存储的简历")
        return result
        
    except Exception as e:
        logger.exception("获取简历列表失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resumes/{resume_id}")
async def get_stored_resume(resume_id: str):
    """获取单个独立存储的简历"""
    logger.info(f"收到请求 GET /resumes/{resume_id}")
    
    try:
        stored = resume_storage.get_resume(resume_id)
        
        if not stored:
            raise HTTPException(status_code=404, detail="简历不存在")
        
        return {
            "id": stored.metadata.id,
            "name": stored.metadata.name,
            "label": stored.metadata.label,
            "created_at": stored.metadata.created_at,
            "updated_at": stored.metadata.updated_at,
            "resume": stored.resume.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取简历失败: {resume_id}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/resumes/{resume_id}")
async def delete_stored_resume(resume_id: str):
    """删除独立存储的简历"""
    logger.info(f"收到请求 DELETE /resumes/{resume_id}")
    
    try:
        success = resume_storage.delete_resume(resume_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="简历不存在")
        
        return {"message": "简历已删除", "id": resume_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除简历失败: {resume_id}")
        raise HTTPException(status_code=500, detail=str(e))


class SaveResumeRequest(BaseModel):
    resume: Resume


@app.post("/resumes")
async def save_resume(req: SaveResumeRequest):
    """保存简历到独立存储（同名自动更新）"""
    logger.info("收到请求 POST /resumes")
    
    try:
        resume_id = resume_storage.save_resume(req.resume)
        
        return {
            "message": "简历已保存",
            "id": resume_id,
            "name": req.resume.basics.name or "未命名"
        }
        
    except Exception as e:
        logger.exception("保存简历失败")
        raise HTTPException(status_code=500, detail=str(e))


def migrate_resumes_from_sessions() -> dict:
    """
    从会话中迁移简历到独立存储
    
    遍历所有会话的 workflow_state.json，提取 resume 字段，
    保存到独立简历存储（自动按姓名去重）
    
    Returns:
        迁移结果统计
    """
    logger.info("开始从会话迁移简历到独立存储...")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    try:
        sessions = session_persistence.list_all_sessions()
        logger.info(f"找到 {len(sessions)} 个会话")
        
        for session_meta in sessions:
            try:
                state = workflow_manager.get(session_meta.id)
                if not state or not state.resume:
                    skipped += 1
                    continue
                
                # 保存到独立存储（同名自动更新）
                resume_storage.save_resume(state.resume)
                migrated += 1
                logger.info(f"已迁移简历: {state.resume.basics.name or '未命名'}")
                
            except Exception as e:
                logger.warning(f"迁移会话 {session_meta.id} 的简历失败: {e}")
                errors += 1
                continue
        
        logger.info(f"迁移完成: 成功={migrated}, 跳过={skipped}, 错误={errors}")
        
    except Exception as e:
        logger.exception(f"迁移过程出错: {e}")
    
    return {
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors
    }


@app.post("/resumes/migrate")
async def migrate_resumes_endpoint():
    """从会话中迁移简历到独立存储（手动触发）"""
    logger.info("收到请求 POST /resumes/migrate")
    
    try:
        result = migrate_resumes_from_sessions()
        return {
            "message": "迁移完成",
            **result
        }
    except Exception as e:
        logger.exception("迁移简历失败")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 保留原有端点（兼容） ====================

@app.post("/run")
def run(req: RunRequest):
    """原有的 Editor Agent 交互模式（保留兼容）"""
    logger.info("收到请求 /run")

    @_sse_guard(logger)
    def _iter():
        for m in legacy_agent.run(req.input, req.resume):
            yield _sse(m)

    return StreamingResponse(
        _iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/parse_resume", response_model=Resume)
async def parse_resume_endpoint(file: UploadFile = File(...)):
    """解析 PDF 简历"""
    logger.info(f"收到请求 /parse_resume: {file.filename}")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        content = await file.read()
        resume = await run_in_threadpool(parse_resume_content, content)
        
        # 自动存储到独立简历库
        try:
            resume_id = resume_storage.save_resume(resume)
            logger.info(f"简历已自动存储: {resume_id}")
        except Exception as save_error:
            logger.warning(f"自动存储简历失败（不影响返回）: {save_error}")
        
        return resume
    except ValueError as e:
        logger.error(f"解析错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("简历解析发生未知错误")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/parse_resume_stream")
async def parse_resume_stream_endpoint(file: UploadFile = File(...)):
    """
    流式解析 PDF 简历（SSE）
    
    实时推送解析进度：
    - { "stage": "reading", "message": "正在读取PDF文件..." }
    - { "stage": "converting", "current": 1, "total": 3, "message": "正在转换第1/3页..." }
    - { "stage": "analyzing", "message": "AI正在分析简历内容..." }
    - { "stage": "complete", "resume": {...} }
    - { "stage": "error", "message": "错误信息" }
    """
    logger.info(f"收到请求 /parse_resume_stream: {file.filename}")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    content = await file.read()
    
    def _iter():
        try:
            for progress_event in parse_resume_with_progress(content):
                # 在 complete 阶段自动存储简历
                if progress_event.get("stage") == "complete" and "resume" in progress_event:
                    try:
                        resume = Resume.model_validate(progress_event["resume"])
                        resume_id = resume_storage.save_resume(resume)
                        logger.info(f"简历已自动存储: {resume_id}")
                        # 在返回事件中添加 resume_id
                        progress_event["resume_id"] = resume_id
                    except Exception as save_error:
                        logger.warning(f"自动存储简历失败（不影响返回）: {save_error}")
                
                yield _sse(progress_event)
        except Exception as e:
            logger.exception("流式解析发生未知错误")
            yield _sse({"stage": "error", "message": f"解析失败: {e}"})
    
    return StreamingResponse(
        _iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "agents": orchestrator.list_agents()
    }


@app.get("/")
async def root():
    """API 文档入口"""
    return {
        "message": "简历助手 API",
        "version": "2.1.0",
        "docs": "/docs",
        "architecture": "Orchestrator-based decoupled design"
    }
