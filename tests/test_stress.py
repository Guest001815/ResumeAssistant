"""
压力测试：测试Guide Agent的稳定性和性能

连续多次调用，验证无500错误
"""
import requests
import sys
import io
import time
from datetime import datetime

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8001"

def stress_test_guide_agent(num_calls=20):
    """压力测试：连续调用Guide Agent"""
    print("=" * 60)
    print(f"压力测试：连续{num_calls}次调用Guide Agent")
    print("=" * 60)
    
    # 健康检查
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            print("❌ 服务器未运行")
            return False
        print("✅ 服务器运行正常\n")
    except:
        print("❌ 无法连接到服务器")
        return False
    
    # 创建会话
    print("准备测试环境...")
    resume = {
        "basics": {"name": "压力测试", "email": "stress@test.com"},
        "sections": [{"id": "s1", "title": "工作经历", "type": "text", "content": "测试"}]
    }
    resp = requests.post(f"{API_BASE}/session/create", json={"resume": resume})
    if resp.status_code != 200:
        print(f"❌ 创建会话失败: {resp.status_code}")
        return False
    
    session_id = resp.json()["session_id"]
    print(f"会话ID: {session_id}")
    
    # 生成计划
    resp = requests.post(
        f"{API_BASE}/session/{session_id}/plan",
        json={"user_intent": "优化简历"}
    )
    if resp.status_code != 200:
        print(f"❌ 生成计划失败: {resp.status_code}")
        return False
    
    print(f"计划生成成功\n")
    
    # 压力测试
    print(f"开始压力测试 ({num_calls}次调用)...")
    print("-" * 60)
    
    results = {
        "success": 0,
        "failed": 0,
        "errors": {},
        "response_times": []
    }
    
    for i in range(num_calls):
        start_time = time.time()
        
        try:
            resp = requests.post(
                f"{API_BASE}/session/{session_id}/guide",
                json={"user_input": f"测试输入 {i+1}"},
                timeout=30
            )
            
            elapsed = time.time() - start_time
            results["response_times"].append(elapsed)
            
            if resp.status_code == 200:
                results["success"] += 1
                status = "✅"
            else:
                results["failed"] += 1
                error_msg = resp.text[:50]
                results["errors"][resp.status_code] = results["errors"].get(resp.status_code, 0) + 1
                status = f"❌ ({resp.status_code})"
            
            print(f"  [{i+1:2d}/{num_calls}] {status} - {elapsed:.2f}s")
            
        except requests.exceptions.Timeout:
            results["failed"] += 1
            results["errors"]["timeout"] = results["errors"].get("timeout", 0) + 1
            print(f"  [{i+1:2d}/{num_calls}] ❌ (超时)")
        except Exception as e:
            results["failed"] += 1
            results["errors"]["exception"] = results["errors"].get("exception", 0) + 1
            print(f"  [{i+1:2d}/{num_calls}] ❌ (异常: {str(e)[:30]})")
        
        # 避免请求过快
        time.sleep(0.3)
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)
    print(f"总请求数: {num_calls}")
    print(f"成功: {results['success']} ({results['success']/num_calls*100:.1f}%)")
    print(f"失败: {results['failed']} ({results['failed']/num_calls*100:.1f}%)")
    
    if results["response_times"]:
        avg_time = sum(results["response_times"]) / len(results["response_times"])
        min_time = min(results["response_times"])
        max_time = max(results["response_times"])
        print(f"\n响应时间:")
        print(f"  平均: {avg_time:.2f}s")
        print(f"  最小: {min_time:.2f}s")
        print(f"  最大: {max_time:.2f}s")
    
    if results["errors"]:
        print(f"\n错误分布:")
        for error_type, count in results["errors"].items():
            print(f"  {error_type}: {count}次")
    
    print("=" * 60)
    
    # 成功率 >= 95% 视为通过
    success_rate = results['success'] / num_calls
    if success_rate >= 0.95:
        print(f"✅ 压力测试通过！成功率: {success_rate*100:.1f}%")
        return True
    else:
        print(f"❌ 压力测试失败！成功率: {success_rate*100:.1f}% (要求 >= 95%)")
        return False


def main():
    success = stress_test_guide_agent(num_calls=20)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

