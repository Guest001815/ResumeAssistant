"""
手动测试 Guide Agent - 简化版本
用于验证 Prompt 修改后的基本功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from guide_agent import GuideAgent
from model import Task
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

def main():
    print("="*60)
    print("Guide Agent 手动测试")
    print("="*60)
    
    # 创建课程优化任务
    task = Task(
        id=1,
        section="教育背景 - 主修课程",
        original_text="主修课程：机器学习，深度学习，模式识别。",
        diagnosis="课程不够丰富，缺少与AI应用相关的课程。",
        goal="优化课程描述，突出相关性。"
    )
    
    agent = GuideAgent(task)
    
    print(f"\n任务信息：")
    print(f"  板块: {task.section}")
    print(f"  原文: {task.original_text}")
    print(f"  问题: {task.diagnosis}")
    print(f"  目标: {task.goal}")
    
    print(f"\n开始对话测试...")
    print("-"*60)
    
    # 测试对话
    test_inputs = [
        "开始优化",
        "没有，我主要学的是传统机器学习课程",
        "没有自学过相关课程",
        "确认"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n[第{i}轮]")
        print(f"用户: {user_input}")
        
        try:
            decision = agent.step(user_input)
            print(f"Agent: {decision.reply_to_user}")
            print(f"状态: {agent.current_state}")
            print(f"动作: {decision.next_action}")
            
            if decision.draft_content:
                print(f"\n[草稿内容]")
                print("-"*60)
                print(decision.draft_content)
                print("-"*60)
                
                # 检查格式
                draft = decision.draft_content
                has_list_separator = "、" in draft or "，" in draft
                has_description = any(word in draft for word in ["系统学习", "打下基础", "重点学习", "涵盖", "包括"])
                
                print(f"\n[格式检查]")
                print(f"  包含列表分隔符: {'YES' if has_list_separator else 'NO'}")
                print(f"  无描述性修饰: {'YES' if not has_description else 'NO'}")
                
                if has_list_separator and not has_description:
                    print("  结论: [PASS] 格式正确")
                else:
                    print("  结论: [WARN] 格式可能需要调整")
            
            if agent.is_finished():
                print("\n任务完成！")
                break
                
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n" + "="*60)
    print("测试结束")
    print("="*60)

if __name__ == "__main__":
    main()

