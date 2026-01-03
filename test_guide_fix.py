"""
测试Guide Agent 500错误修复
"""
import requests
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8001"

def test_guide_agent():
    print("=" * 50)
    print("测试Guide Agent修复")
    print("=" * 50 + "\n")
    
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
    session_id = resp.json()["session_id"]
    print(f"   会话ID: {session_id}")
    print("   ✅ 通过\n")
    
    # 2. 生成计划
    print("2. 生成计划...")
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "我想申请Python后端工程师"}
    )
    if resp.status_code != 200:
        print(f"   ❌ 失败: {resp.status_code}")
        print(f"   错误: {resp.text}")
        return
    
    plan = resp.json()["plan"]
    print(f"   生成任务数: {len(plan['tasks'])}")
    if len(plan['tasks']) > 0:
        print(f"   第一个任务: {plan['tasks'][0]['section']}")
    print("   ✅ 通过\n")
    
    # 3. Guide交互
    print("3. 测试Guide Agent交互...")
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/guide",
        json={"user_input": "我主要负责后端API开发"}
    )
    
    print(f"   HTTP状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ 成功！")
        print(f"   思考: {data.get('thought', '')[:50]}...")
        print(f"   回复: {data.get('reply', '')[:50]}...")
        print(f"   状态: {data.get('state')}")
        print(f"   是否确认: {data.get('is_confirming')}")
        print(f"   是否完成: {data.get('is_finished')}")
    else:
        print(f"   ❌ 失败！")
        print(f"   错误: {resp.text}")
    
    print("\n" + "=" * 50)
    if resp.status_code == 200:
        print("✅ Guide Agent 500错误已修复！")
    else:
        print("❌ 仍有问题需要调查")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test_guide_agent()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

