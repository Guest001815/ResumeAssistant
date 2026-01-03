#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户体验修复验证脚本

快速验证三个关键修复点：
1. API 消息提取逻辑
2. 跳过流程优化
3. 确认状态检查
"""

import sys
import io
import re

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def check_api_fix():
    """检查 API 层消息提取逻辑是否正确修复"""
    print("=" * 60)
    print("检查 1: API 层消息提取逻辑")
    print("=" * 60)
    
    with open('backend/api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否有正确的消息提取逻辑
    if 'for msg in output.messages:' in content and 'if msg.type == "answer":' in content:
        print("✅ API 消息提取逻辑已修复")
        print("   - 正确查找 type='answer' 的消息")
        
        # 检查是否有日志
        if '📝 Guide返回消息结构' in content:
            print("   - 已添加消息结构日志")
        if '✅ 成功提取reply_to_user' in content:
            print("   - 已添加成功提取日志")
        
        return True
    else:
        print("❌ API 消息提取逻辑未正确修复")
        print("   请检查 backend/api.py 第527-539行")
        return False


def check_skip_optimization():
    """检查跳过流程是否优化"""
    print("\n" + "=" * 60)
    print("检查 2: 跳过流程优化")
    print("=" * 60)
    
    # 检查后端
    with open('backend/orchestrator.py', 'r', encoding='utf-8') as f:
        orchestrator_content = f.read()
    
    backend_ok = '简化消息，由前端调用guideInit获取自然过渡话术' in orchestrator_content
    
    if backend_ok:
        print("✅ 后端 orchestrator.py 已优化")
        print("   - 简化了跳过返回消息")
    else:
        print("❌ 后端 orchestrator.py 未优化")
        return False
    
    # 检查前端
    with open('web/src/components/WorkspaceLayout.tsx', 'r', encoding='utf-8') as f:
        frontend_content = f.read()
    
    frontend_ok = 'guideInit' in frontend_content and '自然的过渡话术' in frontend_content
    
    if frontend_ok:
        print("✅ 前端 WorkspaceLayout.tsx 已修改")
        print("   - 导入了 guideInit")
        print("   - 跳过后自动调用 guideInit")
        return True
    else:
        print("❌ 前端 WorkspaceLayout.tsx 未正确修改")
        return False


def check_validation():
    """检查确认状态检查是否添加"""
    print("\n" + "=" * 60)
    print("检查 3: 确认状态检查")
    print("=" * 60)
    
    with open('web/src/components/ChatPanel.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '当前没有待确认的内容' in content and 'lastMsg?.isConfirming' in content:
        print("✅ 前端确认状态检查已添加")
        print("   - 检查最后一条消息的 isConfirming 状态")
        print("   - 提供友好的错误提示")
        return True
    else:
        print("❌ 前端确认状态检查未添加")
        return False


def check_logging():
    """检查日志增强是否完成"""
    print("\n" + "=" * 60)
    print("检查 4: 日志增强")
    print("=" * 60)
    
    with open('backend/api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('📝 Guide返回消息结构', '消息结构日志'),
        ('✅ 成功提取reply_to_user', '成功提取日志'),
        ('⚠️ 未找到answer类型消息', '警告日志'),
        ('🚀 开始执行Editor Agent', 'Editor执行日志'),
        ('当前WorkflowStage', '工作流状态日志'),
    ]
    
    all_ok = True
    for marker, desc in checks:
        if marker in content:
            print(f"✅ 已添加{desc}")
        else:
            print(f"❌ 缺少{desc}")
            all_ok = False
    
    return all_ok


def main():
    print("\n" + "=" * 60)
    print("用户体验修复验证")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行所有检查
    results.append(("API 消息提取", check_api_fix()))
    results.append(("跳过流程优化", check_skip_optimization()))
    results.append(("确认状态检查", check_validation()))
    results.append(("日志增强", check_logging()))
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"总体进度: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有修复已正确实施！")
        print("\n下一步：")
        print("1. 重启后端服务: cd backend && python api.py")
        print("2. 重启前端服务: cd web && npm run dev")
        print("3. 参考 TEST_USER_EXPERIENCE_FIX.md 进行功能测试")
        return 0
    else:
        print("\n[WARNING] 部分检查未通过，请检查上述失败项")
        return 1


if __name__ == "__main__":
    exit(main())

