"""
测试Guide Agent 500错误修复 - 带调试信息
"""
import requests
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8001"

def test_guide_agent_debug():
    print("=" * 50)
    print("测试Guide Agent修复 (调试版)")
    print("=" * 50 + "\n")
    
    # 1. 健康检查
    print("0. 健康检查...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            print(f"   响应: {resp.json()}")
            print("   ✅ 服务正常\n")
        else:
            print(f"   ❌ 服务异常: {resp.text}\n")
            return
    except Exception as e:
        print(f"   ❌ 无法连接到服务: {e}\n")
        return
    
    # 1. 创建会话
    print("1. 创建会话...")
    resume = {
        "basics": {
            "name": "张三",
            "email": "zhangsan@example.com"
        },
        "sections": [
            {
                "id": "test-1",
                "title": "工作经历",
                "type": "text",
                "content": "2020-2023 ABC公司 - Python开发工程师"
            }
        ]
    }
    
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    print(f"   状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ❌ 创建会话失败: {resp.text}")
        return
    
    data = resp.json()
    session_id = data["session_id"]
    print(f"   会话ID: {session_id}")
    print("   ✅ 通过\n")
    
    # 1.5 验证会话存在
    print("1.5. 验证会话存在...")
    resp = requests.get(f"{API_BASE}/session/{session_id}")
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   当前阶段: {data.get('current_stage')}")
        print(f"   是否有计划: {data.get('has_plan')}")
        print("   ✅ 会话存在\n")
    else:
        print(f"   ❌ 会话不存在: {resp.text}\n")
        return
    
    # 2. 生成计划
    print("2. 生成计划...")
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "我想申请Python后端工程师"}
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ❌ 失败: {resp.text}")
        return
    
    plan = resp.json()["plan"]
    print(f"   生成任务数: {len(plan['tasks'])}")
    if len(plan['tasks']) > 0:
        print(f"   第一个任务: {plan['tasks'][0]['section']}")
        print(f"   第一个任务ID: {plan['tasks'][0]['id']}")
    print("   ✅ 通过\n")
    
    # 2.5 再次验证会话
    print("2.5. 再次验证会话...")
    resp = requests.get(f"{API_BASE}/session/{session_id}")
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   当前阶段: {data.get('current_stage')}")
        print(f"   是否有计划: {data.get('has_plan')}")
        print(f"   当前任务索引: {data.get('current_task_idx')}")
        print("   ✅ 会话正常\n")
    else:
        print(f"   ❌ 会话丢失: {resp.text}\n")
        return
    
    # 3. 获取进度
    print("2.7 获取进度...")
    resp = requests.get(f"{API_BASE}/session/{session_id}/progress")
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   总任务: {data.get('total_tasks')}")
        print(f"   当前任务索引: {data.get('current_task_idx')}")
        if data.get('current_task'):
            print(f"   当前任务: {data['current_task'].get('section')}")
        print("   ✅ 进度正常\n")
    else:
        print(f"   ⚠️ 获取进度失败: {resp.text}\n")
    
    # 3. Guide交互
    print("3. 测试Guide Agent交互...")
    print(f"   使用会话ID: {session_id}")
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "我主要负责后端API开发"}
    )
    
    print(f"   HTTP状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ 成功！")
        print(f"   思考: {data.get('thought', '')[:80]}...")
        print(f"   回复: {data.get('reply', '')[:80]}...")
        print(f"   状态: {data.get('state')}")
        print(f"   是否确认: {data.get('is_confirming')}")
        print(f"   是否完成: {data.get('is_finished')}")
    else:
        print(f"   ❌ 失败！")
        print(f"   错误: {resp.text}")
        print(f"   错误详情: {resp.json() if resp.headers.get('content-type') == 'application/json' else 'N/A'}")
    
    print("\n" + "=" * 50)
    if resp.status_code == 200:
        print("✅ Guide Agent 500错误已修复！")
    else:
        print("❌ 仍有问题需要调查")
    print("=" * 50)
    
    return resp.status_code == 200

if __name__ == "__main__":
    try:
        success = test_guide_agent_debug()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

