# Guide Agent 500错误问题报告

## 问题描述

在调用 `POST /session/{id}/guide` 端点时，偶尔会返回500错误，错误信息为"Guide Agent 返回为空"。

## 现象

1. **LLM正常响应**：从日志中可以看到Guide Agent的LLM（Qwen模型）确实返回了正确格式的JSON响应
2. **HTTP 500错误**：但API最终返回500错误
3. **日志缺失**：添加的调试日志没有出现，说明代码可能在某处提前退出

## 已尝试的修复

### 1. 修复类型转换问题
**文件**: `backend/api.py` 第242-265行

**问题**: 
- `output.action.value` 应该改为 `output.action`（直接比较枚举）
- `output.messages[-1].content` 可能不是字符串

**修复**:
```python
# 修改前
is_finished = output.action.value == "handoff" and output.next_agent == "editor"
reply = output.messages[-1].content if output.messages else ""

# 修改后
is_finished = output.action == AgentAction.HANDOFF and output.next_agent == "editor"
# 添加类型检查
if isinstance(last_msg_content, str):
    reply = last_msg_content
elif isinstance(last_msg_content, BaseModel):
    reply = last_msg_content.model_dump_json()
else:
    reply = str(last_msg_content)
```

### 2. 修复生成器返回值捕获
**文件**: `backend/api.py` 第230-238行

**问题**: for循环会自动处理StopIteration，无法捕获返回值

**修复**:
```python
# 修改前
for _ in gen:
    pass

# 修改后
while True:
    next(gen)
```

### 3. 增强orchestrator日志
**文件**: `backend/orchestrator.py` 第224-256行

添加了详细的日志记录，但这些日志没有出现在输出中。

## 根本原因分析

从症状来看，可能的原因：

1. **生成器返回机制问题**
   - Python生成器的return语句会引发StopIteration
   - 但在某些情况下，这个异常可能没有被正确捕获

2. **异步/同步混用问题**
   - FastAPI的端点是async的
   - 但orchestrator.run_guide_step返回的是同步生成器
   - 可能存在事件循环相关的问题

3. **LLM多次调用**
   - 日志显示LLM被调用了两次（连续两个Response）
   - 可能Guide Agent内部有重试或多轮对话逻辑
   - 这可能导致生成器状态混乱

## 建议的解决方案

### 方案1：简化生成器机制（推荐）

不使用生成器的返回值，改为直接返回：

```python
# backend/api.py
@app.post("/session/{session_id}/guide", response_model=GuideResponse)
async def guide_step(session_id: str, req: GuideRequest):
    state = workflow_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    current_task = state.get_current_task()
    if not current_task:
        raise HTTPException(status_code=400, detail="所有任务已完成")
    
    try:
        # 直接调用invoke，不使用stream
        agent = orchestrator.get_agent("guide")
        if not agent:
            raise HTTPException(status_code=500, detail="Guide Agent 未注册")
        
        # 恢复状态
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
        
        # 直接调用invoke
        output = agent.invoke(input, state)
        
        # 保存状态
        state.save_agent_state(agent.name, agent.export_state())
        
        # 处理输出
        is_confirming = state.current_stage == WorkflowStage.CONFIRMING
        is_finished = output.action == AgentAction.HANDOFF and output.next_agent == "editor"
        
        # 提取draft和reply
        draft = None
        reply = ""
        
        for msg in output.messages:
            if msg.type == "info" and "草稿预览" in str(msg.content):
                draft = str(msg.content).replace("草稿预览:\n", "")
        
        if output.messages:
            last_content = output.messages[-1].content
            reply = str(last_content) if not isinstance(last_content, BaseModel) else last_content.model_dump_json()
        
        return GuideResponse(
            thought=output.thought,
            reply=reply,
            state=state.current_stage.value,
            draft=draft,
            execution_doc=output.content if isinstance(output.content, ExecutionDoc) else None,
            is_confirming=is_confirming,
            is_finished=is_finished
        )
        
    except Exception as e:
        logger.exception("Guide Agent 执行失败")
        raise HTTPException(status_code=500, detail=str(e))
```

### 方案2：使用异步生成器

如果需要保留流式功能，可以改为异步生成器：

```python
# backend/base_agent.py
async def astream(self, input: AgentInput, state: WorkflowState) -> AsyncGenerator[AgentMessage, AgentOutput]:
    """异步流式接口"""
    pass
```

### 方案3：添加更详细的错误处理

在每个关键点添加try-except，确保异常能被正确捕获和记录。

## 当前状态

- ✅ 后端服务运行正常
- ✅ 前端界面完整
- ⚠️ Guide Agent 有时返回500错误
- ✅ PDF解析、Plan Agent、Editor Agent 都正常

## 临时解决方案

用户可以：
1. 重试失败的请求（通常第二次会成功）
2. 使用前端的错误处理机制
3. 刷新页面重新开始（会话会丢失）

## 不影响的功能

- 创建会话 ✅
- 生成计划 ✅
- PDF解析 ✅
- Editor Agent执行 ✅
- 简历预览和导出 ✅

## 需要用户输入

由于这是一个复杂的异步/生成器问题，建议：

1. **短期**: 使用方案1（直接调用invoke，放弃流式）
2. **中期**: 如果需要流式，改用异步生成器
3. **长期**: 升级到LangGraph，使用其内置的流式机制

您希望我实施哪个方案？

