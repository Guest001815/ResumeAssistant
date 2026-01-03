"""
A测试：集成测试 - 完整工作流测试

测试从创建会话到完成编辑的完整流程
"""
import requests
import sys
import io
import time

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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


def test_complete_workflow():
    """测试1: 完整工作流"""
    print("\n【测试1】完整工作流测试")
    print("-" * 60)
    result = TestResult()
    
    # 1. 创建会话
    resume = {
        "basics": {
            "name": "测试用户",
            "email": "test@example.com"
        },
        "sections": [
            {
                "id": "work-1",
                "title": "工作经历",
                "type": "text",
                "content": "2020-2023 测试公司 - Python开发"
            }
        ]
    }
    
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    if resp.status_code == 200:
        session_id = resp.json()["session_id"]
        result.add_pass("创建会话")
    else:
        result.add_fail("创建会话", f"状态码 {resp.status_code}")
        return result.summary()
    
    # 2. 生成计划
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "优化简历申请Python后端职位"}
    )
    if resp.status_code == 200:
        plan = resp.json()["plan"]
        result.add_pass(f"生成计划 ({len(plan['tasks'])}个任务)")
    else:
        result.add_fail("生成计划", f"状态码 {resp.status_code}")
        return result.summary()
    
    # 3. Guide交互 - 第1轮
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "我负责后端API开发，使用Python和Django"}
    )
    if resp.status_code == 200:
        data = resp.json()
        result.add_pass(f"Guide第1轮 (状态: {data['state']})")
    else:
        result.add_fail("Guide第1轮", f"状态码 {resp.status_code}: {resp.text}")
        return result.summary()
    
    # 4. Guide交互 - 第2轮
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "主要开发了用户管理和订单系统，使用MySQL和Redis"}
    )
    if resp.status_code == 200:
        data = resp.json()
        result.add_pass(f"Guide第2轮 (状态: {data['state']})")
    else:
        result.add_fail("Guide第2轮", f"状态码 {resp.status_code}: {resp.text}")
        return result.summary()
    
    # 5. Guide交互 - 第3轮
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "优化了API响应时间，从500ms降到100ms，支持10万用户"}
    )
    if resp.status_code == 200:
        data = resp.json()
        result.add_pass(f"Guide第3轮 (状态: {data['state']})")
    else:
        result.add_fail("Guide第3轮", f"状态码 {resp.status_code}: {resp.text}")
    
    return result.summary()


def test_guide_stability():
    """测试2: Guide Agent 稳定性测试"""
    print("\n【测试2】Guide Agent 稳定性测试 (10次连续调用)")
    print("-" * 60)
    result = TestResult()
    
    # 创建会话
    resume = {
        "basics": {"name": "稳定性测试", "email": "stability@test.com"},
        "sections": [{"id": "s1", "title": "工作", "type": "text", "content": "测试内容"}]
    }
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    session_id = resp.json()["session_id"]
    
    # 生成计划
    requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "优化简历"}
    )
    
    # 连续10次调用
    for i in range(10):
        resp = requests.post(
            f"{API_BASE}/session/{session_id}/guide",
            json={"user_input": f"测试输入 {i+1}"}
        )
        if resp.status_code == 200:
            result.add_pass(f"第{i+1}次调用")
        else:
            result.add_fail(f"第{i+1}次调用", f"状态码 {resp.status_code}")
        
        time.sleep(0.5)  # 避免请求过快
    
    return result.summary()


def test_multi_task_flow():
    """测试3: 多任务流程测试"""
    print("\n【测试3】多任务流程测试")
    print("-" * 60)
    result = TestResult()
    
    # 创建会话
    resume = {
        "basics": {"name": "多任务测试", "email": "multitask@test.com"},
        "sections": [
            {"id": "s1", "title": "教育", "type": "text", "content": "本科"},
            {"id": "s2", "title": "工作", "type": "text", "content": "开发"}
        ]
    }
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    session_id = resp.json()["session_id"]
    
    # 生成计划
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "全面优化简历"}
    )
    plan = resp.json()["plan"]
    task_count = len(plan["tasks"])
    
    if task_count >= 2:
        result.add_pass(f"生成多个任务 ({task_count}个)")
    else:
        result.add_fail("生成多个任务", f"只有{task_count}个任务")
        return result.summary()
    
    # 获取当前任务
    resp = requests.get(f"{API_BASE}/session/{session_id}/progress")
    if resp.status_code == 200:
        progress = resp.json()
        first_task = progress["current_task"]["section"] if progress["current_task"] else None
        result.add_pass(f"获取第1个任务: {first_task}")
    else:
        result.add_fail("获取进度", f"状态码 {resp.status_code}")
    
    # 跳过当前任务
    resp = requests.post(f"{API_BASE}/session/{session_id}/skip")
    if resp.status_code == 200:
        result.add_pass("跳过任务")
    else:
        result.add_fail("跳过任务", f"状态码 {resp.status_code}")
    
    # 验证任务索引变化
    resp = requests.get(f"{API_BASE}/session/{session_id}/progress")
    if resp.status_code == 200:
        progress = resp.json()
        if progress["current_task_idx"] == 1:
            result.add_pass("任务索引正确递增")
        else:
            result.add_fail("任务索引", f"期望1，实际{progress['current_task_idx']}")
    
    return result.summary()


def test_session_persistence():
    """测试4: 会话持久化测试"""
    print("\n【测试4】会话持久化测试")
    print("-" * 60)
    result = TestResult()
    
    # 创建会话
    resume = {
        "basics": {"name": "持久化测试", "email": "persist@test.com"},
        "sections": [{"id": "s1", "title": "工作", "type": "text", "content": "测试"}]
    }
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    session_id = resp.json()["session_id"]
    
    # 生成计划
    requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "优化"}
    )
    
    # Guide交互
    requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "测试输入"}
    )
    
    # 获取会话信息
    resp = requests.get(f"{API_BASE}/session/{session_id}")
    if resp.status_code == 200:
        data = resp.json()
        if data["has_plan"]:
            result.add_pass("会话保持计划状态")
        else:
            result.add_fail("会话状态", "计划丢失")
        
        if data["current_stage"] == "guiding":
            result.add_pass("会话保持阶段状态")
        else:
            result.add_fail("会话阶段", f"期望guiding，实际{data['current_stage']}")
    else:
        result.add_fail("获取会话", f"状态码 {resp.status_code}")
    
    return result.summary()


def main():
    print("=" * 60)
    print("A测试：集成测试 - 完整工作流")
    print("=" * 60)
    
    # 健康检查
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            print("❌ 服务器未运行，请先启动后端服务")
            return False
        print("✅ 服务器运行正常\n")
    except:
        print("❌ 无法连接到服务器，请先启动后端服务")
        return False
    
    # 运行所有测试
    all_passed = True
    all_passed &= test_complete_workflow()
    all_passed &= test_guide_stability()
    all_passed &= test_multi_task_flow()
    all_passed &= test_session_persistence()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有集成测试通过！")
    else:
        print("❌ 部分测试失败，请查看上面的详细信息")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

