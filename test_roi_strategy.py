"""
测试场景2：ROI止损策略
验证用户连续说"没有"时，Agent是否快速止损
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from guide_agent import GuideAgent
from model import Task
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    print("="*60)
    print("测试场景2：ROI止损策略")
    print("="*60)
    
    task = Task(
        id=2,
        section="教育背景 - 主修课程",
        original_text="主修课程：机器学习，深度学习。",
        diagnosis="课程不够丰富，缺少与AI应用相关的课程。",
        goal="补充相关课程。"
    )
    
    agent = GuideAgent(task)
    
    print(f"\n任务: {task.section}")
    print(f"原文: {task.original_text}")
    print("\n[模拟对话 - 用户连续说'没有']")
    print("-"*60)
    
    # 测试对话 - 用户一直说没有
    test_inputs = [
        "开始",
        "没有学过这些课程",
        "真的没有，当时这些还不流行",
        "确实没有相关经历"
    ]
    
    draft_provided_at_round = None
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n[第{i}轮]")
        print(f"用户: {user_input}")
        
        try:
            decision = agent.step(user_input)
            print(f"Agent: {decision.reply_to_user[:100]}...")
            print(f"动作: {decision.next_action}")
            
            if decision.draft_content and not draft_provided_at_round:
                draft_provided_at_round = i
                print(f"\n[草稿内容]")
                print("-"*60)
                print(decision.draft_content)
                print("-"*60)
            
            if agent.is_finished():
                break
                
        except Exception as e:
            print(f"错误: {e}")
            break
    
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    if draft_provided_at_round:
        print(f"Agent 在第 {draft_provided_at_round} 轮提供了草稿")
        if draft_provided_at_round <= 3:
            print("[PASS] 止损策略生效 - Agent快速止损（<=3轮）")
        else:
            print("[WARN] 止损较慢 - 建议优化")
    else:
        print("[FAIL] 未提供草稿 - 止损策略未生效")

if __name__ == "__main__":
    main()

