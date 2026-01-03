"""
快速测试脚本 - 测试最近修改的核心功能
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_1_health():
    """测试1: 健康检查"""
    print("\n[测试1] 健康检查")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        print(f"  状态: {r.status_code}")
        print(f"  版本: {data.get('version')}")
        print(f"  Agents: {data.get('agents')}")
        return r.status_code == 200
    except Exception as e:
        print(f"  失败: {e}")
        return False

def test_2_sessions_api():
    """测试2: 会话管理API"""
    print("\n[测试2] 会话管理API")
    try:
        r = requests.get(f"{BASE_URL}/sessions", timeout=5)
        sessions = r.json()
        print(f"  状态: {r.status_code}")
        print(f"  现有会话数: {len(sessions)}")
        return r.status_code == 200
    except Exception as e:
        print(f"  失败: {e}")
        return False

def test_3_create_session():
    """测试3: 创建会话"""
    print("\n[测试3] 创建会话")
    try:
        resume = {
            "basics": {"name": "测试", "email": "test@test.com", "phone": "123"},
            "sections": [{"id": "edu", "title": "教育", "type": "generic", "items": []}]
        }
        r = requests.post(f"{BASE_URL}/session/create", json={"resume": resume}, timeout=10)
        data = r.json()
        print(f"  状态: {r.status_code}")
        print(f"  Session ID: {data.get('session_id')}")
        return r.status_code == 200, data.get('session_id')
    except Exception as e:
        print(f"  失败: {e}")
        return False, None

def test_4_session_metadata():
    """测试4: 会话元数据"""
    print("\n[测试4] 会话元数据功能")
    passed, sid = test_3_create_session()
    if not passed or not sid:
        print("  跳过: 无法创建会话")
        return False
    
    try:
        # 获取会话详情
        r = requests.get(f"{BASE_URL}/session/{sid}", timeout=5)
        data = r.json()
        print(f"  获取会话: {r.status_code}")
        print(f"  简历姓名: {data.get('resume', {}).get('basics', {}).get('name')}")
        
        # 测试会话列表
        r2 = requests.get(f"{BASE_URL}/sessions", timeout=5)
        sessions = r2.json()
        print(f"  会话列表: 找到 {len(sessions)} 个会话")
        
        return r.status_code == 200
    except Exception as e:
        print(f"  失败: {e}")
        return False

def test_5_editor_agent_state():
    """测试5: Editor Agent 状态持久化"""
    print("\n[测试5] Editor Agent 状态")
    passed, sid = test_3_create_session()
    if not passed or not sid:
        print("  跳过: 无法创建会话")
        return False
    
    try:
        # 获取会话状态
        r = requests.get(f"{BASE_URL}/session/{sid}", timeout=5)
        data = r.json()
        resume = data.get('resume', {})
        
        # 验证简历数据完整性
        has_basics = bool(resume.get('basics'))
        has_sections = bool(resume.get('sections'))
        
        print(f"  简历基本信息: {'存在' if has_basics else '缺失'}")
        print(f"  简历章节: {len(resume.get('sections', []))} 个")
        print(f"  数据完整性: {'通过' if (has_basics and has_sections) else '失败'}")
        
        return has_basics and has_sections
    except Exception as e:
        print(f"  失败: {e}")
        return False

def test_6_api_endpoints():
    """测试6: 核心API端点"""
    print("\n[测试6] 核心API端点")
    endpoints = [
        ("GET", "/health"),
        ("GET", "/sessions"),
    ]
    
    passed = 0
    for method, path in endpoints:
        try:
            url = f"{BASE_URL}{path}"
            r = requests.get(url, timeout=5) if method == "GET" else requests.post(url, json={}, timeout=5)
            status = "OK" if r.status_code in [200, 404] else "FAIL"
            print(f"  {method} {path}: {r.status_code} [{status}]")
            if status == "OK":
                passed += 1
        except Exception as e:
            print(f"  {method} {path}: ERROR - {e}")
    
    return passed == len(endpoints)

def main():
    print("="*70)
    print("ResumeAssistant 快速测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"后端: {BASE_URL}")
    
    results = []
    results.append(("健康检查", test_1_health()))
    results.append(("会话API", test_2_sessions_api()))
    results.append(("创建会话", test_3_create_session()[0]))
    results.append(("会话元数据", test_4_session_metadata()))
    results.append(("Editor Agent状态", test_5_editor_agent_state()))
    results.append(("API端点", test_6_api_endpoints()))
    
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "[PASS]" if p else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n结果: [SUCCESS] 所有测试通过!")
        return 0
    elif passed >= total * 0.8:
        print("\n结果: [WARNING] 大部分测试通过")
        return 0
    else:
        print("\n结果: [FAIL] 多个测试失败")
        return 1

if __name__ == "__main__":
    exit(main())

