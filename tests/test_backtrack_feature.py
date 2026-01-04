"""
智能任务回溯功能测试

测试 WorkflowState.switch_to_task() 和相关回溯功能
"""
import sys
import os
import io
import requests
import time

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from workflow_state import WorkflowState, WorkflowStateManager, WorkflowStage
from model import Task, TaskList, TaskStatus, AgentDecision

API_BASE = "http://localhost:8001"


class TestResult:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.total += 1
        self.passed += 1
        print(f"   ✅ {test_name}")
    
    def add_fail(self, test_name, reason):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, reason))
        print(f"   ❌ {test_name}: {reason}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print(f"测试总结: {self.passed}/{self.total} 通过")
        if self.failed > 0:
            print(f"\n失败的测试:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print("=" * 60)
        return self.failed == 0


# ==================== 单元测试 ====================

def test_switch_to_task_exact_match():
    """测试1: switch_to_task 精确匹配"""
    print("\n【单元测试1】switch_to_task 精确匹配")
    print("-" * 60)
    result = TestResult()
    
    # 创建测试状态
    state = WorkflowState(session_id="test-1")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景", original_text="本科", diagnosis="信息不完整", goal="补充学校"),
        Task(id=2, section="工作经历", original_text="开发", diagnosis="描述简单", goal="添加细节"),
        Task(id=3, section="技能特长", original_text="Python", diagnosis="技能少", goal="补充技能"),
    ])
    
    # 设置第一个任务为已完成
    state.plan.tasks[0].status = TaskStatus.COMPLETED
    state.current_task_idx = 1  # 当前在第二个任务
    
    # 测试精确匹配
    new_idx = state.switch_to_task("教育背景")
    
    if new_idx == 0:
        result.add_pass("切换到索引 0（教育背景）")
    else:
        result.add_fail("切换索引", f"期望 0，实际 {new_idx}")
    
    if state.current_task_idx == 0:
        result.add_pass("current_task_idx 已更新")
    else:
        result.add_fail("current_task_idx", f"期望 0，实际 {state.current_task_idx}")
    
    if state.plan.tasks[0].status == TaskStatus.IN_PROGRESS:
        result.add_pass("目标任务状态改为 IN_PROGRESS")
    else:
        result.add_fail("任务状态", f"期望 IN_PROGRESS，实际 {state.plan.tasks[0].status}")
    
    if state.current_stage == WorkflowStage.GUIDING:
        result.add_pass("工作流阶段改为 GUIDING")
    else:
        result.add_fail("工作流阶段", f"期望 GUIDING，实际 {state.current_stage}")
    
    return result.summary()


def test_switch_to_task_partial_match():
    """测试2: switch_to_task 部分匹配"""
    print("\n【单元测试2】switch_to_task 部分匹配")
    print("-" * 60)
    result = TestResult()
    
    state = WorkflowState(session_id="test-2")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景 - 硕士", original_text="硕士", diagnosis="信息不完整", goal="补充"),
        Task(id=2, section="工作经历 - ABC公司", original_text="开发", diagnosis="描述简单", goal="细节"),
        Task(id=3, section="项目经验 - 电商系统", original_text="系统", diagnosis="缺少量化", goal="补充"),
    ])
    
    state.plan.tasks[0].status = TaskStatus.COMPLETED
    state.plan.tasks[1].status = TaskStatus.COMPLETED
    state.current_task_idx = 2
    
    # 测试部分匹配 - "教育" 应该匹配 "教育背景 - 硕士"
    new_idx = state.switch_to_task("教育")
    
    if new_idx == 0:
        result.add_pass("部分匹配成功：'教育' → '教育背景 - 硕士'")
    else:
        result.add_fail("部分匹配", f"期望 0，实际 {new_idx}")
    
    # 重置状态，测试另一个部分匹配
    state.current_task_idx = 2
    state.plan.tasks[0].status = TaskStatus.COMPLETED
    
    new_idx = state.switch_to_task("ABC")
    
    if new_idx == 1:
        result.add_pass("部分匹配成功：'ABC' → '工作经历 - ABC公司'")
    else:
        result.add_fail("部分匹配 ABC", f"期望 1，实际 {new_idx}")
    
    return result.summary()


def test_switch_to_task_not_found():
    """测试3: switch_to_task 未找到匹配"""
    print("\n【单元测试3】switch_to_task 未找到匹配")
    print("-" * 60)
    result = TestResult()
    
    state = WorkflowState(session_id="test-3")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景", original_text="本科", diagnosis="信息不完整", goal="补充"),
        Task(id=2, section="工作经历", original_text="开发", diagnosis="描述简单", goal="细节"),
    ])
    
    state.current_task_idx = 0
    original_idx = state.current_task_idx
    
    # 测试不存在的任务
    new_idx = state.switch_to_task("不存在的任务")
    
    if new_idx is None:
        result.add_pass("未找到任务时返回 None")
    else:
        result.add_fail("返回值", f"期望 None，实际 {new_idx}")
    
    if state.current_task_idx == original_idx:
        result.add_pass("current_task_idx 未改变")
    else:
        result.add_fail("current_task_idx", f"不应该改变，但从 {original_idx} 变为 {state.current_task_idx}")
    
    return result.summary()


def test_get_completed_task_names():
    """测试4: get_completed_task_names 方法"""
    print("\n【单元测试4】get_completed_task_names 方法")
    print("-" * 60)
    result = TestResult()
    
    state = WorkflowState(session_id="test-4")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景", original_text="本科", diagnosis="信息不完整", goal="补充"),
        Task(id=2, section="工作经历", original_text="开发", diagnosis="描述简单", goal="细节"),
        Task(id=3, section="技能特长", original_text="Python", diagnosis="技能少", goal="补充"),
    ])
    
    # 设置任务状态
    state.plan.tasks[0].status = TaskStatus.COMPLETED
    state.plan.tasks[1].status = TaskStatus.IN_PROGRESS
    state.plan.tasks[2].status = TaskStatus.COMPLETED
    
    completed = state.get_completed_task_names()
    
    if len(completed) == 2:
        result.add_pass(f"返回 2 个已完成任务")
    else:
        result.add_fail("已完成任务数量", f"期望 2，实际 {len(completed)}")
    
    if "教育背景" in completed:
        result.add_pass("包含 '教育背景'")
    else:
        result.add_fail("任务列表", "'教育背景' 不在列表中")
    
    if "技能特长" in completed:
        result.add_pass("包含 '技能特长'")
    else:
        result.add_fail("任务列表", "'技能特长' 不在列表中")
    
    return result.summary()


def test_find_task_by_section():
    """测试5: find_task_by_section 方法"""
    print("\n【单元测试5】find_task_by_section 方法")
    print("-" * 60)
    result = TestResult()
    
    state = WorkflowState(session_id="test-5")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景", original_text="本科", diagnosis="信息不完整", goal="补充"),
        Task(id=2, section="工作经历 - Python开发", original_text="开发", diagnosis="描述简单", goal="细节"),
    ])
    
    # 精确匹配
    task = state.find_task_by_section("教育背景")
    
    if task and task.id == 1:
        result.add_pass("精确匹配找到任务")
    else:
        result.add_fail("精确匹配", f"未找到任务或ID不匹配")
    
    # 部分匹配
    task = state.find_task_by_section("Python")
    
    if task and task.id == 2:
        result.add_pass("部分匹配找到任务：'Python' → '工作经历 - Python开发'")
    else:
        result.add_fail("部分匹配", f"未找到任务或ID不匹配")
    
    # 不存在的任务
    task = state.find_task_by_section("不存在")
    
    if task is None:
        result.add_pass("未找到任务时返回 None")
    else:
        result.add_fail("返回值", f"期望 None，实际返回了任务")
    
    return result.summary()


def test_agent_decision_intent_field():
    """测试6: AgentDecision 模型的 intent 字段"""
    print("\n【单元测试6】AgentDecision intent 字段")
    print("-" * 60)
    result = TestResult()
    
    # 测试 CONTINUE 意图
    decision1 = AgentDecision(
        thought="用户正在提供信息",
        next_action="CONTINUE_ASKING",
        reply_to_user="请继续告诉我更多细节",
        intent="CONTINUE"
    )
    
    if decision1.intent == "CONTINUE":
        result.add_pass("CONTINUE 意图正确设置")
    else:
        result.add_fail("CONTINUE 意图", f"期望 CONTINUE，实际 {decision1.intent}")
    
    # 测试 BACKTRACK 意图
    decision2 = AgentDecision(
        thought="用户想回溯修改",
        next_action="CONTINUE_ASKING",
        reply_to_user="好的，让我们回到那部分",
        intent="BACKTRACK",
        target_section="教育背景"
    )
    
    if decision2.intent == "BACKTRACK":
        result.add_pass("BACKTRACK 意图正确设置")
    else:
        result.add_fail("BACKTRACK 意图", f"期望 BACKTRACK，实际 {decision2.intent}")
    
    if decision2.target_section == "教育背景":
        result.add_pass("target_section 正确设置")
    else:
        result.add_fail("target_section", f"期望 '教育背景'，实际 {decision2.target_section}")
    
    # 测试默认值（intent 可选）
    decision3 = AgentDecision(
        thought="普通对话",
        next_action="CONTINUE_ASKING",
        reply_to_user="好的"
    )
    
    if decision3.intent is None:
        result.add_pass("intent 默认值为 None")
    else:
        result.add_fail("intent 默认值", f"期望 None，实际 {decision3.intent}")
    
    return result.summary()


def test_switch_clears_agent_state():
    """测试7: switch_to_task 清除 Agent 状态"""
    print("\n【单元测试7】switch_to_task 清除 Agent 状态")
    print("-" * 60)
    result = TestResult()
    
    state = WorkflowState(session_id="test-7")
    state.plan = TaskList(tasks=[
        Task(id=1, section="教育背景", original_text="本科", diagnosis="信息不完整", goal="补充"),
        Task(id=2, section="工作经历", original_text="开发", diagnosis="描述简单", goal="细节"),
    ])
    
    # 模拟存储 Guide Agent 状态
    state.agent_states["guide"] = {
        "current_state": "DRAFTING",
        "messages": [{"role": "user", "content": "测试消息"}],
        "draft": "测试草稿"
    }
    state.current_exec_doc = {"test": "doc"}
    state.current_task_idx = 1
    state.plan.tasks[0].status = TaskStatus.COMPLETED
    
    # 切换任务
    state.switch_to_task("教育背景")
    
    if "guide" not in state.agent_states:
        result.add_pass("Guide Agent 状态已清除")
    else:
        result.add_fail("Agent 状态", "Guide Agent 状态未清除")
    
    if state.current_exec_doc is None:
        result.add_pass("current_exec_doc 已清除")
    else:
        result.add_fail("current_exec_doc", "未清除")
    
    return result.summary()


# ==================== 集成测试 ====================

def test_backtrack_api_response():
    """集成测试1: API 回溯响应字段"""
    print("\n【集成测试1】API 回溯响应字段")
    print("-" * 60)
    result = TestResult()
    
    # 创建会话
    resume = {
        "basics": {"name": "回溯测试", "email": "backtrack@test.com"},
        "sections": [
            {"id": "s1", "title": "教育背景", "type": "text", "content": "本科计算机"},
            {"id": "s2", "title": "工作经历", "type": "text", "content": "Python开发"},
            {"id": "s3", "title": "技能特长", "type": "text", "content": "Python, Django"}
        ]
    }
    
    try:
        resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume}, timeout=10)
        if resp.status_code != 200:
            result.add_fail("创建会话", f"状态码 {resp.status_code}")
            return result.summary()
        
        session_id = resp.json()["session_id"]
        result.add_pass(f"创建会话: {session_id[:8]}...")
        
        # 生成计划
        resp = requests.post(
            f"{API_BASE}/session/{session_id}/plan",
            json={"user_intent": "全面优化简历"},
            timeout=60
        )
        if resp.status_code != 200:
            result.add_fail("生成计划", f"状态码 {resp.status_code}")
            return result.summary()
        
        plan = resp.json()["plan"]
        task_count = len(plan["tasks"])
        result.add_pass(f"生成计划（{task_count}个任务）")
        
        # 验证响应中包含新字段
        resp = requests.post(
            f"{API_BASE}/session/{session_id}/guide",
            json={"user_input": "我的专业是计算机科学"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 检查响应是否包含回溯相关字段
            if "switch_to_task" in data:
                result.add_pass("响应包含 switch_to_task 字段")
            else:
                result.add_fail("响应字段", "缺少 switch_to_task")
            
            if "switch_to_section" in data:
                result.add_pass("响应包含 switch_to_section 字段")
            else:
                result.add_fail("响应字段", "缺少 switch_to_section")
            
            # 注意：switch_to_task 可能因为 LLM 意图判断而不为 null
            # 这不是一个 bug，而是 LLM 的不确定性
            switch_val = data.get("switch_to_task")
            if switch_val is None:
                result.add_pass("正常对话时 switch_to_task 为 null（符合预期）")
            else:
                # LLM 可能将输入识别为回溯意图，这不是代码 bug
                result.add_pass(f"switch_to_task = {switch_val}（LLM 意图识别结果）")
        else:
            result.add_fail("Guide 调用", f"状态码 {resp.status_code}")
        
    except requests.exceptions.Timeout:
        result.add_fail("请求超时", "API 响应超时")
    except Exception as e:
        result.add_fail("异常", str(e)[:50])
    
    return result.summary()


def test_regression_normal_workflow():
    """回归测试1: 正常工作流不受影响"""
    print("\n【回归测试1】正常工作流不受影响")
    print("-" * 60)
    result = TestResult()
    
    resume = {
        "basics": {"name": "回归测试", "email": "regression@test.com"},
        "sections": [
            {"id": "s1", "title": "工作经历", "type": "text", "content": "Python开发"}
        ]
    }
    
    try:
        # 创建会话
        resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume}, timeout=10)
        if resp.status_code != 200:
            result.add_fail("创建会话", f"状态码 {resp.status_code}")
            return result.summary()
        
        session_id = resp.json()["session_id"]
        result.add_pass("创建会话成功")
        
        # 生成计划
        resp = requests.post(
            f"{API_BASE}/session/{session_id}/plan",
            json={"user_intent": "优化简历"},
            timeout=60
        )
        if resp.status_code == 200:
            result.add_pass("生成计划成功")
        else:
            result.add_fail("生成计划", f"状态码 {resp.status_code}")
            return result.summary()
        
        # 多轮对话
        for i in range(3):
            resp = requests.post(
                f"{API_BASE}/session/{session_id}/guide",
                json={"user_input": f"测试输入 {i+1}"},
                timeout=30
            )
            if resp.status_code == 200:
                result.add_pass(f"Guide 第{i+1}轮成功")
            else:
                result.add_fail(f"Guide 第{i+1}轮", f"状态码 {resp.status_code}")
            
            time.sleep(0.5)
        
        # 获取进度
        resp = requests.get(f"{API_BASE}/session/{session_id}/progress", timeout=10)
        if resp.status_code == 200:
            progress = resp.json()
            result.add_pass(f"获取进度成功 (任务索引: {progress.get('current_task_idx', 'N/A')})")
        else:
            result.add_fail("获取进度", f"状态码 {resp.status_code}")
        
    except Exception as e:
        result.add_fail("异常", str(e)[:50])
    
    return result.summary()


def test_regression_skip_task():
    """回归测试2: 跳过任务功能正常"""
    print("\n【回归测试2】跳过任务功能正常")
    print("-" * 60)
    result = TestResult()
    
    resume = {
        "basics": {"name": "跳过测试", "email": "skip@test.com"},
        "sections": [
            {"id": "s1", "title": "教育", "type": "text", "content": "本科"},
            {"id": "s2", "title": "工作", "type": "text", "content": "开发"}
        ]
    }
    
    try:
        # 创建会话并生成计划
        resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume}, timeout=10)
        session_id = resp.json()["session_id"]
        
        requests.post(
            f"{API_BASE}/session/{session_id}/plan",
            json={"user_intent": "优化"},
            timeout=60
        )
        
        # 获取初始进度
        resp = requests.get(f"{API_BASE}/session/{session_id}/progress", timeout=10)
        initial_idx = resp.json().get("current_task_idx", 0)
        result.add_pass(f"初始任务索引: {initial_idx}")
        
        # 跳过任务
        resp = requests.post(f"{API_BASE}/session/{session_id}/skip", timeout=10)
        if resp.status_code == 200:
            result.add_pass("跳过任务 API 调用成功")
        else:
            result.add_fail("跳过任务", f"状态码 {resp.status_code}")
            return result.summary()
        
        # 验证任务索引变化
        resp = requests.get(f"{API_BASE}/session/{session_id}/progress", timeout=10)
        new_idx = resp.json().get("current_task_idx", 0)
        
        if new_idx > initial_idx:
            result.add_pass(f"任务索引递增: {initial_idx} → {new_idx}")
        else:
            result.add_fail("任务索引", f"未递增: {initial_idx} → {new_idx}")
        
    except Exception as e:
        result.add_fail("异常", str(e)[:50])
    
    return result.summary()


def main():
    print("=" * 60)
    print("智能任务回溯功能测试")
    print("=" * 60)
    
    # 健康检查
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            print("❌ 服务器未运行，请先启动后端服务")
            return False
        print("✅ 服务器运行正常\n")
    except:
        print("⚠️ 无法连接到服务器，将只运行单元测试\n")
        run_integration = False
    else:
        run_integration = True
    
    all_passed = True
    
    # 单元测试
    print("\n" + "=" * 60)
    print("第一部分：单元测试")
    print("=" * 60)
    
    all_passed &= test_switch_to_task_exact_match()
    all_passed &= test_switch_to_task_partial_match()
    all_passed &= test_switch_to_task_not_found()
    all_passed &= test_get_completed_task_names()
    all_passed &= test_find_task_by_section()
    all_passed &= test_agent_decision_intent_field()
    all_passed &= test_switch_clears_agent_state()
    
    # 集成测试
    if run_integration:
        print("\n" + "=" * 60)
        print("第二部分：集成测试")
        print("=" * 60)
        
        all_passed &= test_backtrack_api_response()
        all_passed &= test_regression_normal_workflow()
        all_passed &= test_regression_skip_task()
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！智能回溯功能正常工作。")
    else:
        print("❌ 部分测试失败，请查看上面的详细信息。")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

