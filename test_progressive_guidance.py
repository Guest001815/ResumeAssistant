"""
测试循序渐进引导优化效果

测试场景：
1. 开场白简化测试 - 验证第一条消息是否只包含1个问题
2. 节奏控制测试 - 验证Agent是否根据用户回复长度调整策略
3. 话题切换测试 - 验证Agent能否自然过渡到下一个话题
4. 学生场景测试 - 模拟学生项目对话全流程
"""

import logging
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from guide_agent import GuideAgent
from model import Task, TaskStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def count_questions(text):
    """统计文本中的问题数量（粗略统计）"""
    # 统计问号数量
    question_marks = text.count('？') + text.count('?')
    # 统计列表项（1. 2. 3.）
    import re
    list_items = len(re.findall(r'\d+\.\s+', text))
    return question_marks, list_items


def test_opening_simplification():
    """测试1：开场白简化测试"""
    print("\n" + "="*60)
    print("测试1：开场白简化测试")
    print("="*60)
    
    task = Task(
        id=1,
        section="项目经历 - DeepResearch Agent",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="基于LangGraph实现的多智能体研究系统",
        diagnosis="描述过于简单，缺少技术细节和量化数据",
        goal="补充技术架构、性能指标、业务价值等细节"
    )
    
    agent = GuideAgent(task)
    decision = agent.generate_opening()
    
    print(f"\n开场白内容：\n{decision.reply_to_user}\n")
    
    # 验证：统计问题数量
    question_marks, list_items = count_questions(decision.reply_to_user)
    
    print(f"问题数量检查：")
    print(f"  - 问号数量: {question_marks}")
    print(f"  - 列表项数量: {list_items}")
    
    # 验证规则
    if question_marks <= 1:
        print("[PASS] 开场白只包含1个问题")
        return True
    else:
        print(f"[FAIL] 开场白包含{question_marks}个问题，应该只有1个")
        return False


def test_pacing_control():
    """测试2：智能节奏控制测试"""
    print("\n" + "="*60)
    print("测试2：智能节奏控制测试")
    print("="*60)
    
    task = Task(
        id=2,
        section="项目经历 - 在线考试系统",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="基于Vue3和SpringBoot实现的在线考试系统",
        diagnosis="缺少技术深度",
        goal="补充技术实现细节"
    )
    
    agent = GuideAgent(task)
    
    # 场景1：详细回答（>50字）
    print("\n场景1：用户给出详细回答（>50字）")
    print("-" * 40)
    agent.generate_opening()
    
    detailed_response = "这个项目是我跟着教程做的，主要实现了学生答题、老师出题、自动批改等功能。我自己动手改了前端的UI设计，还优化了后端的数据库查询性能。"
    decision1 = agent.step(detailed_response)
    
    print(f"用户: {detailed_response}")
    print(f"\nAgent思考: {decision1.thought}")
    print(f"\nAgent回复: {decision1.reply_to_user}\n")
    
    q1_marks, q1_list = count_questions(decision1.reply_to_user)
    if q1_marks <= 1:
        print("[PASS] 详细回答场景通过：Agent只问了1个深入问题")
        result1 = True
    else:
        print(f"[FAIL] 详细回答场景失败：Agent问了{q1_marks}个问题")
        result1 = False
    
    # 场景2：简短回答（<20字）
    print("\n场景2：用户给出简短回答（<20字）")
    print("-" * 40)
    
    task2 = Task(
        id=3,
        section="项目经历 - 博客系统",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="个人博客系统",
        diagnosis="描述过于简单",
        goal="补充细节"
    )
    
    agent2 = GuideAgent(task2)
    agent2.generate_opening()
    
    short_response = "跟着教程做的"
    decision2 = agent2.step(short_response)
    
    print(f"用户: {short_response}")
    print(f"\nAgent思考: {decision2.thought}")
    print(f"\nAgent回复: {decision2.reply_to_user}\n")
    
    # 检查是否提供了选项或更具体的引导
    has_options = ('A.' in decision2.reply_to_user or 
                   'B.' in decision2.reply_to_user or
                   '比如' in decision2.reply_to_user or
                   '例如' in decision2.reply_to_user)
    
    if has_options:
        print("[PASS] 简短回答场景通过：Agent提供了选项或具体引导")
        result2 = True
    else:
        # 也可能是换了话题
        q2_marks, _ = count_questions(decision2.reply_to_user)
        if q2_marks <= 1:
            print("[PASS] 简短回答场景通过：Agent调整了策略")
            result2 = True
        else:
            print("[FAIL] 简短回答场景失败：Agent没有调整策略")
            result2 = False
    
    return result1 and result2


def test_topic_transition():
    """测试3：话题切换测试"""
    print("\n" + "="*60)
    print("测试3：话题切换测试")
    print("="*60)
    
    task = Task(
        id=4,
        section="项目经历 - 智能客服",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="基于LangChain的智能客服系统",
        diagnosis="缺少技术细节",
        goal="补充实现细节"
    )
    
    agent = GuideAgent(task)
    agent.generate_opening()
    
    # 模拟对话：用户连续简短回答
    print("\n模拟对话：用户连续简短回答")
    print("-" * 40)
    
    responses = [
        "跟着教程做的",
        "改了一些代码",
        "就这些了"
    ]
    
    for i, response in enumerate(responses, 1):
        decision = agent.step(response)
        print(f"\n轮次{i}:")
        print(f"用户: {response}")
        print(f"Agent: {decision.reply_to_user[:100]}...")
        
        # 检查第3轮是否有话题切换信号
        if i == 3:
            has_transition = any(keyword in decision.reply_to_user for keyword in [
                '了解了', '明白了', '好的', '换个角度', '那我们', '另一个'
            ])
            if has_transition or decision.next_action == "PROPOSE_DRAFT":
                print("[PASS] 话题切换测试通过：Agent识别到该切换话题或生成草稿")
                return True
            else:
                print("[WARN] 话题切换测试：Agent继续追问（可能需要优化）")
                return False


def test_student_scenario_full_flow():
    """测试4：学生场景完整流程测试"""
    print("\n" + "="*60)
    print("测试4：学生场景完整流程测试")
    print("="*60)
    
    task = Task(
        id=5,
        section="项目经历 - 电商系统",
        strategy=TaskStrategy.STAR_STORYTELLING,
        original_text="基于SpringBoot的电商系统",
        diagnosis="缺少细节",
        goal="补充技术细节"
    )
    
    agent = GuideAgent(task)
    
    # 完整对话流程
    conversation = [
        ("", "开场白"),  # 开场白
        ("跟着教程做的", "确认项目性质"),
        ("实现了商品管理和购物车功能", "主要工作"),
        ("刚开始不太理解Spring的依赖注入，花了挺长时间研究", "项目难点"),
        ("学会了SpringBoot的基本使用，理解了后端开发的流程", "个人收获"),
    ]
    
    print("\n完整对话流程：")
    print("-" * 40)
    
    all_single_question = True
    
    for i, (user_msg, phase) in enumerate(conversation):
        if i == 0:
            # 开场白
            decision = agent.generate_opening()
            print(f"\n【{phase}】")
            print(f"Agent: {decision.reply_to_user}\n")
            
            q_marks, q_list = count_questions(decision.reply_to_user)
            if q_marks > 1:
                all_single_question = False
                print(f"[WARN] 开场白包含{q_marks}个问题")
        else:
            decision = agent.step(user_msg)
            print(f"\n【{phase}】")
            print(f"用户: {user_msg}")
            print(f"Agent: {decision.reply_to_user}\n")
            
            if decision.next_action != "PROPOSE_DRAFT":
                q_marks, q_list = count_questions(decision.reply_to_user)
                if q_marks > 1:
                    all_single_question = False
                    print(f"[WARN] 第{i}轮包含{q_marks}个问题")
    
    if all_single_question:
        print("[PASS] 学生场景测试通过：每轮对话都只问1个问题")
        return True
    else:
        print("[FAIL] 学生场景测试失败：某些轮次包含多个问题")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("循序渐进引导优化 - 测试套件")
    print("="*60)
    
    results = {}
    
    try:
        results['test1'] = test_opening_simplification()
    except Exception as e:
        logger.error(f"测试1失败: {e}", exc_info=True)
        results['test1'] = False
    
    try:
        results['test2'] = test_pacing_control()
    except Exception as e:
        logger.error(f"测试2失败: {e}", exc_info=True)
        results['test2'] = False
    
    try:
        results['test3'] = test_topic_transition()
    except Exception as e:
        logger.error(f"测试3失败: {e}", exc_info=True)
        results['test3'] = False
    
    try:
        results['test4'] = test_student_scenario_full_flow()
    except Exception as e:
        logger.error(f"测试4失败: {e}", exc_info=True)
        results['test4'] = False
    
    # 输出总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！循序渐进引导优化成功！")
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，需要继续优化")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

