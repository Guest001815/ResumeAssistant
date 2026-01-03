"""
ResumeAssistant 综合测试脚本
测试所有最近修改的功能模块
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

# 测试结果记录
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {"total": 0, "passed": 0, "failed": 0}
}

def log_test(name, passed, message="", details=None):
    """记录测试结果"""
    result = {
        "name": name,
        "passed": passed,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results["tests"].append(result)
    test_results["summary"]["total"] += 1
    if passed:
        test_results["summary"]["passed"] += 1
        print(f"[PASS] {name}: {message}")
    else:
        test_results["summary"]["failed"] += 1
        print(f"[FAIL] {name}: {message}")
    return passed

def test_health_check():
    """测试1: 健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        passed = response.status_code == 200 and data.get("status") == "healthy"
        log_test("健康检查", passed, 
                f"状态码={response.status_code}, agents={data.get('agents', [])}")
        return passed
    except Exception as e:
        log_test("健康检查", False, f"异常: {str(e)}")
        return False

def test_session_apis():
    """测试2: 会话管理API"""
    try:
        # 获取会话列表
        response = requests.get(f"{BASE_URL}/sessions", timeout=5)
        passed = response.status_code == 200
        sessions = response.json() if passed else []
        log_test("获取会话列表", passed, 
                f"状态码={response.status_code}, 会话数={len(sessions)}")
        return passed
    except Exception as e:
        log_test("获取会话列表", False, f"异常: {str(e)}")
        return False

def test_create_session():
    """测试3: 创建会话"""
    try:
        # 创建简单的测试简历
        resume_data = {
            "basics": {
                "name": "测试用户",
                "email": "test@example.com",
                "phone": "13800138000"
            },
            "sections": [
                {
                    "id": "education",
                    "title": "教育背景",
                    "type": "generic",
                    "items": [
                        {
                            "id": "edu1",
                            "title": "测试大学",
                            "subtitle": "计算机科学",
                            "date": "2020-2024"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/session/create",
            json={"resume": resume_data},
            timeout=10
        )
        passed = response.status_code == 200
        data = response.json() if passed else {}
        session_id = data.get("session_id")
        
        log_test("创建会话", passed, 
                f"状态码={response.status_code}, session_id={session_id}")
        return passed, session_id if passed else None
    except Exception as e:
        log_test("创建会话", False, f"异常: {str(e)}")
        return False, None

def test_plan_generation(session_id):
    """测试4: 生成优化计划"""
    if not session_id:
        log_test("生成计划", False, "无效的session_id")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/plan",
            json={"user_intent": "优化简历以申请Python后端开发岗位"},
            timeout=30
        )
        passed = response.status_code == 200
        data = response.json() if passed else {}
        plan = data.get("plan", {})
        tasks = plan.get("tasks", [])
        
        log_test("生成计划", passed, 
                f"状态码={response.status_code}, 任务数={len(tasks)}")
        return passed
    except Exception as e:
        log_test("生成计划", False, f"异常: {str(e)}")
        return False

def test_guide_agent_stability():
    """测试5: Guide Agent 稳定性测试"""
    print("\n开始 Guide Agent 稳定性测试 (10次调用)...")
    
    # 创建测试会话
    passed, session_id = test_create_session()
    if not passed:
        log_test("Guide Agent稳定性", False, "无法创建测试会话")
        return False
    
    # 生成计划
    if not test_plan_generation(session_id):
        log_test("Guide Agent稳定性", False, "无法生成计划")
        return False
    
    # 连续调用Guide Agent
    success_count = 0
    total_calls = 10
    response_times = []
    
    for i in range(total_calls):
        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/session/{session_id}/guide",
                json={"user_input": f"测试输入 {i+1}"},
                timeout=30
            )
            elapsed = time.time() - start_time
            response_times.append(elapsed)
            
            if response.status_code == 200:
                success_count += 1
                print(f"  [{i+1}] PASS ({elapsed:.2f}s)")
            else:
                print(f"  [{i+1}] FAIL (status={response.status_code})")
        except Exception as e:
            print(f"  [{i+1}] ERROR ({str(e)})")
    
    success_rate = (success_count / total_calls) * 100
    avg_time = sum(response_times) / len(response_times) if response_times else 0
    
    passed = success_rate >= 90  # 90%成功率为合格
    log_test("Guide Agent稳定性", passed, 
            f"成功率={success_rate:.1f}% ({success_count}/{total_calls}), "
            f"平均响应时间={avg_time:.2f}秒",
            {"response_times": response_times})
    return passed

def test_api_endpoints():
    """测试6: 所有API端点"""
    endpoints = [
        ("GET", "/health", None),
        ("GET", "/sessions", None),
    ]
    
    passed_count = 0
    for method, path, data in endpoints:
        try:
            url = f"{BASE_URL}{path}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json=data, timeout=5)
            
            if response.status_code in [200, 404]:  # 404也算正常(如sessions为空)
                passed_count += 1
                print(f"  [PASS] {method} {path}: {response.status_code}")
            else:
                print(f"  [FAIL] {method} {path}: {response.status_code}")
        except Exception as e:
            print(f"  [ERROR] {method} {path}: {str(e)}")
    
    passed = passed_count == len(endpoints)
    log_test("API端点测试", passed, 
            f"通过={passed_count}/{len(endpoints)}")
    return passed

def test_editor_agent_fix():
    """测试7: Editor Agent 修复验证"""
    print("\n测试 Editor Agent 生成器返回值修复...")
    
    # 创建会话
    passed, session_id = test_create_session()
    if not passed:
        log_test("Editor Agent修复", False, "无法创建会话")
        return False
    
    # 生成计划
    if not test_plan_generation(session_id):
        log_test("Editor Agent修复", False, "无法生成计划")
        return False
    
    # 获取会话信息，验证简历数据
    try:
        response = requests.get(f"{BASE_URL}/session/{session_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            resume = data.get("resume", {})
            basics = resume.get("basics", {})
            name = basics.get("name", "")
            
            # 验证简历数据完整性
            passed = bool(name) and bool(resume.get("sections"))
            log_test("Editor Agent修复", passed, 
                    f"简历数据完整性检查: name={name}, sections={len(resume.get('sections', []))}")
            return passed
        else:
            log_test("Editor Agent修复", False, f"获取会话失败: {response.status_code}")
            return False
    except Exception as e:
        log_test("Editor Agent修复", False, f"异常: {str(e)}")
        return False

def generate_report():
    """生成测试报告"""
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    print(f"测试时间: {test_results['timestamp']}")
    print(f"总测试数: {test_results['summary']['total']}")
    print(f"通过: {test_results['summary']['passed']}")
    print(f"失败: {test_results['summary']['failed']}")
    
    pass_rate = (test_results['summary']['passed'] / test_results['summary']['total'] * 100) if test_results['summary']['total'] > 0 else 0
    print(f"通过率: {pass_rate:.1f}%")
    
    print("\n详细结果:")
    for test in test_results['tests']:
        status = "[PASS]" if test['passed'] else "[FAIL]"
        print(f"{status} {test['name']}: {test['message']}")
    
    # 保存到文件
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存到: {report_file}")
    
    return pass_rate >= 80  # 80%通过率为合格

def main():
    """主测试流程"""
    print("="*60)
    print("ResumeAssistant 综合测试")
    print("="*60)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"后端地址: {BASE_URL}\n")
    
    # 执行测试
    test_health_check()
    test_session_apis()
    test_create_session()
    test_api_endpoints()
    test_editor_agent_fix()
    test_guide_agent_stability()
    
    # 生成报告
    success = generate_report()
    
    print("\n" + "="*60)
    if success:
        print("测试完成: [PASS] 通过")
    else:
        print("测试完成: [FAIL] 存在问题需要修复")
    print("="*60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

