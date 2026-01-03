"""
测试场景3：核心板块深入挖掘
验证对于项目经历等核心板块，Agent是否深入挖掘
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
    print("测试场景3：核心板块深入挖掘")
    print("="*60)
    
    task = Task(
        id=3,
        section="项目经历 - AI Agent开发",
        original_text="负责开发AI Agent系统，使用LLM技术。",
        diagnosis="描述过于简单，缺少具体成果和量化数据。",
        goal="使用STAR法则补充项目细节和成果。"
    )
    
    agent = GuideAgent(task)
    
    print(f"\n任务: {task.section}")
    print(f"原文: {task.original_text}")
    print("\n[模拟对话 - 核心板块]")
    print("-"*60)
    
    # 测试对话
    test_inputs = [
        "开始优化",
        "这个项目服务了公司内部100多个用户，主要是帮助他们自动化处理文档",
        "具体来说，我们使用了RAG技术，结合公司的知识库，让用户可以通过对话快速查询和生成文档"
    ]
    
    question_count = 0
    has_star_questions = False
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n[第{i}轮]")
        print(f"用户: {user_input}")
        
        try:
            decision = agent.step(user_input)
            print(f"Agent: {decision.reply_to_user[:150]}...")
            print(f"动作: {decision.next_action}")
            
            # 检查是否包含STAR相关问题
            star_keywords = ["背景", "目标", "如何", "怎么", "成果", "数据", "指标", "效果", "提升", "优化"]
            if any(keyword in decision.reply_to_user for keyword in star_keywords):
                has_star_questions = True
                question_count += 1
            
            if decision.draft_content:
                print(f"\n[草稿内容]")
                print("-"*60)
                print(decision.draft_content[:200])
                print("-"*60)
                break
                
        except Exception as e:
            print(f"错误: {e}")
            break
    
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    print(f"STAR相关提问次数: {question_count}")
    
    if has_star_questions and question_count >= 2:
        print("[PASS] 核心板块深入挖掘 - Agent提出了多个深入问题")
    elif has_star_questions:
        print("[WARN] 挖掘深度一般 - 可以更深入")
    else:
        print("[FAIL] 未深入挖掘 - 对核心板块的提问不够")

if __name__ == "__main__":
    main()

