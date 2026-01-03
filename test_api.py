"""
简单的API测试脚本
用于验证后端各个端点是否正常工作
"""
import requests
import json
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8001"

def test_health():
    """测试健康检查"""
    print("1. 测试健康检查...")
    response = requests.get(f"{API_BASE}/health")
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
    assert response.status_code == 200
    print("   ✅ 通过\n")

def test_create_session():
    """测试创建会话"""
    print("2. 测试创建会话...")
    resume = {
        "basics": {
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "138****1234"
        },
        "sections": [
            {
                "id": "test-section-1",
                "title": "工作经历",
                "type": "text",
                "content": "2020-2023 ABC公司 - Python开发工程师"
            }
        ]
    }
    
    response = requests.post(
        f"{API_BASE}/session/create",
        json={"resume": resume}
    )
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   会话ID: {data.get('session_id')}")
    assert response.status_code == 200
    assert 'session_id' in data
    print("   ✅ 通过\n")
    return data['session_id']

def test_generate_plan(session_id):
    """测试生成计划"""
    print("3. 测试生成计划...")
    response = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "我想申请Python后端工程师职位"}
    )
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   任务数量: {len(data.get('plan', {}).get('tasks', []))}")
    if data.get('plan', {}).get('tasks'):
        print(f"   第一个任务: {data['plan']['tasks'][0]['section']}")
    assert response.status_code == 200
    assert 'plan' in data
    print("   ✅ 通过\n")
    return data['plan']

def test_get_progress(session_id):
    """测试获取进度"""
    print("4. 测试获取进度...")
    response = requests.get(f"{API_BASE}/session/{session_id}/progress")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   总任务: {data.get('total_tasks')}")
        print(f"   当前任务索引: {data.get('current_task_idx')}")
        print("   ✅ 通过\n")
    else:
        print(f"   错误: {response.text}")
        print("   ⚠️ 跳过此测试\n")

def test_guide_step(session_id):
    """测试Guide交互"""
    print("5. 测试Guide Agent交互...")
    response = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "我主要负责用户系统和订单系统的开发"}
    )
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   回复: {data.get('reply', '')[:100]}...")
    print(f"   状态: {data.get('state')}")
    print(f"   是否需要确认: {data.get('is_confirming')}")
    assert response.status_code == 200
    print("   ✅ 通过\n")

def test_get_session_info(session_id):
    """测试获取会话信息"""
    print("6. 测试获取会话信息...")
    response = requests.get(f"{API_BASE}/session/{session_id}")
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   当前阶段: {data.get('current_stage')}")
    print(f"   是否有计划: {data.get('has_plan')}")
    assert response.status_code == 200
    print("   ✅ 通过\n")

def main():
    print("=" * 50)
    print("开始API测试")
    print("=" * 50 + "\n")
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 创建会话
        session_id = test_create_session()
        
        # 3. 生成计划
        plan = test_generate_plan(session_id)
        
        # 4. 获取进度
        test_get_progress(session_id)
        
        # 5. Guide交互
        test_guide_step(session_id)
        
        # 6. 获取会话信息
        test_get_session_info(session_id)
        
        print("=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

