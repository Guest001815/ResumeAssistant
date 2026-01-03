"""
测试 Guide Agent Prompt 优化效果

测试场景：
1. 课程优化任务 - 验证输出格式是否符合列表格式要求
2. 用户连续说"没有" - 验证止损策略是否生效
3. 核心板块优化 - 确保仍然深入挖掘
"""

import sys
import os
import logging

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from guide_agent import GuideAgent
from model import Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s"
)

def test_course_format():
    """
    测试场景1：课程优化任务
    期望：输出格式为列表格式，不是段落描述
    """
    print("\n" + "="*60)
    print("测试场景1：课程优化任务 - 验证格式")
    print("="*60)
    
    task = Task(
        id=1,
        section="教育背景 - 主修课程",
        original_text="主修课程：机器学习，深度学习，模式识别，数据挖掘，计算机视觉。",
        diagnosis="课程罗列过于传统和宽泛，未能与目标岗位（AI应用研发）建立直接关联。",
        goal="重构课程描述，突出与目标岗位相关的课程。"
    )
    
    agent = GuideAgent(task)
    
    print("\n[模拟对话]")
    print("-" * 60)
    
    # 第一轮：Agent 提问
    decision1 = agent.step("开始优化")
    print(f"\nAgent: {decision1.reply_to_user}")
    print(f"状态: {agent.current_state}")
    
    # 第二轮：用户回答没有
    decision2 = agent.step("没有，我主要学的是传统机器学习课程")
    print(f"\nAgent: {decision2.reply_to_user}")
    print(f"状态: {agent.current_state}")
    
    if decision2.draft_content:
        print(f"\n[草稿内容]")
        print("-" * 60)
        print(decision2.draft_content)
        print("-" * 60)
        
        # 验证格式
        draft = decision2.draft_content
        is_list_format = "、" in draft or "，" in draft
        has_description = any(word in draft for word in ["系统学习", "打下基础", "重点学习", "涵盖"])
        
        print(f"\n[格式检查]")
        print(f"✓ 包含列表分隔符: {is_list_format}")
        print(f"✓ 无描述性修饰: {not has_description}")
        
        if is_list_format and not has_description:
            print("\n✅ 测试通过：格式符合要求")
        else:
            print("\n❌ 测试失败：格式不符合要求")
    
    return agent

def test_stop_loss_strategy():
    """
    测试场景2：用户连续说"没有"
    期望：Agent 快速止损，不再追问
    """
    print("\n" + "="*60)
    print("测试场景2：止损策略 - 用户连续说没有")
    print("="*60)
    
    task = Task(
        id=2,
        section="教育背景 - 主修课程",
        original_text="主修课程：机器学习，深度学习。",
        diagnosis="课程不够丰富，缺少与AI应用相关的课程。",
        goal="补充相关课程。"
    )
    
    agent = GuideAgent(task)
    
    print("\n[模拟对话]")
    print("-" * 60)
    
    # 第一轮
    decision1 = agent.step("开始")
    print(f"\nAgent: {decision1.reply_to_user}")
    
    # 第二轮：用户说没有
    decision2 = agent.step("没有学过这些课程")
    print(f"\nAgent: {decision2.reply_to_user}")
    
    # 第三轮：用户再次说没有
    decision3 = agent.step("真的没有，当时这些还不流行")
    print(f"\nAgent: {decision3.reply_to_user}")
    
    # 检查是否提供了草稿（止损）
    if decision3.draft_content:
        print(f"\n[草稿内容]")
        print("-" * 60)
        print(decision3.draft_content)
        print("-" * 60)
        print("\n✅ 测试通过：Agent 触发止损，提供了简化版草稿")
    else:
        # 第四轮：看是否继续追问
        decision4 = agent.step("没有")
        print(f"\nAgent: {decision4.reply_to_user}")
        
        if decision4.draft_content:
            print(f"\n[草稿内容]")
            print("-" * 60)
            print(decision4.draft_content)
            print("-" * 60)
            print("\n⚠️ 测试部分通过：Agent 在第4轮才止损")
        else:
            print("\n❌ 测试失败：Agent 未触发止损策略")
    
    return agent

def test_core_section_deep_dive():
    """
    测试场景3：核心板块优化
    期望：Agent 深入挖掘，不会快速止损
    """
    print("\n" + "="*60)
    print("测试场景3：核心板块 - 确保深入挖掘")
    print("="*60)
    
    task = Task(
        id=3,
        section="项目经历 - AI Agent开发",
        original_text="负责开发AI Agent系统，使用LLM技术。",
        diagnosis="描述过于简单，缺少具体成果和量化数据。",
        goal="使用STAR法则补充项目细节和成果。"
    )
    
    agent = GuideAgent(task)
    
    print("\n[模拟对话]")
    print("-" * 60)
    
    # 第一轮
    decision1 = agent.step("开始优化")
    print(f"\nAgent: {decision1.reply_to_user}")
    print(f"状态: {agent.current_state}")
    
    # 检查是否提出了深入的问题
    has_star_questions = any(word in decision1.reply_to_user for word in ["背景", "目标", "如何", "成果", "数据", "指标"])
    
    if has_star_questions:
        print("\n✅ 测试通过：Agent 对核心板块进行深入提问")
    else:
        print("\n⚠️ 测试警告：Agent 的提问可能不够深入")
    
    # 第二轮：用户提供信息
    decision2 = agent.step("这个项目服务了公司内部100多个用户，主要是帮助他们自动化处理文档")
    print(f"\nAgent: {decision2.reply_to_user}")
    
    # 检查是否继续追问细节
    continues_asking = decision2.next_action in ["CONTINUE_ASKING", "PROPOSE_DRAFT"]
    
    if continues_asking:
        print("\n✅ 测试通过：Agent 继续深入挖掘核心板块")
    else:
        print("\n❌ 测试失败：Agent 过早结束核心板块优化")
    
    return agent

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Guide Agent Prompt 优化效果测试")
    print("="*60)
    
    try:
        # 测试1：格式验证
        test_course_format()
        
        # 测试2：止损策略
        test_stop_loss_strategy()
        
        # 测试3：核心板块深入挖掘
        test_core_section_deep_dive()
        
        print("\n" + "="*60)
        print("所有测试完成")
        print("="*60)
        print("\n请检查上述输出，验证：")
        print("1. 课程格式是否为列表格式（用顿号分隔）")
        print("2. 用户说'没有'时是否快速止损")
        print("3. 核心板块是否深入挖掘")
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()

