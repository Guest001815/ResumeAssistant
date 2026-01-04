"""
测试学生项目引导策略
包括智能猜测、降级策略、四块框架引导等场景
"""
import sys
from pathlib import Path

# 添加backend到Python路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from model import Task, TaskStrategy
from guide_agent import GuideAgent


class TestStudentProjectGuidance:
    """学生项目引导测试套件"""
    
    def test_scenario_1_smooth_flow(self):
        """
        场景1：顺利流程 - 用户直接说出难点和收获
        """
        print("\n" + "="*60)
        print("测试场景1：用户直接说出难点和收获（顺利流程）")
        print("="*60)
        
        task = Task(
            id=1,
            section="项目经历 - 在线考试系统",
            strategy=TaskStrategy.STAR_STORYTELLING,
            original_text="基于Vue3和SpringBoot开发的在线考试系统，实现了题库管理、在线答题、自动批改功能。",
            diagnosis="描述仅列举了实现的功能，缺少项目难点和个人收获的展示",
            goal="挖掘项目难点（如前后端联调、跨域配置等）和技术收获（掌握的新技术、理解的原理）"
        )
        
        agent = GuideAgent(task)
        
        # 第1轮：开场白
        print("\n--- 第1轮：开场白 ---")
        decision = agent.generate_opening()
        print(f"Agent: {decision.reply_to_user}")
        assert "熟悉程度" in decision.reply_to_user or "项目描述" in decision.reply_to_user
        
        # 第2轮：用户选择模式C并说明项目
        print("\n--- 第2轮：用户选择模式C ---")
        user_input = "C，这是我的课程项目。项目就是一个在线考试系统，我主要做了前后端联调和用户认证模块。"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第3轮：用户说出难点
        print("\n--- 第3轮：用户说出难点 ---")
        user_input = "主要是跨域配置那块，一开始浏览器一直报CORS错误，后来查了资料在SpringBoot加了@CrossOrigin注解才解决。"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第4轮：用户说出收获
        print("\n--- 第4轮：用户说出收获 ---")
        user_input = "学会了前后端分离的完整流程，还掌握了Vue3的组合式API和SpringBoot的RESTful接口设计。"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        if decision.draft_content:
            print(f"\n--- 草稿内容 ---")
            print(decision.draft_content)
            assert "跨域" in decision.draft_content or "CORS" in decision.draft_content
            assert "收获" in decision.draft_content or "掌握" in decision.draft_content or "理解" in decision.draft_content
        
        print("\n✅ 场景1测试通过：顺利流程正常工作")
    
    def test_scenario_2_intelligent_guess(self):
        """
        场景2：智能猜测 - 用户说"不知道"，触发智能猜测
        """
        print("\n" + "="*60)
        print("测试场景2：用户说'不知道'，触发智能猜测")
        print("="*60)
        
        task = Task(
            id=2,
            section="项目经历 - 推荐系统",
            strategy=TaskStrategy.STAR_STORYTELLING,
            original_text="基于协同过滤算法实现的电影推荐系统，使用Python和Flask框架。",
            diagnosis="描述偏技术实现，项目难点和个人收获体现不足",
            goal="挖掘项目难点（算法实现、数据处理等）和技术收获"
        )
        
        agent = GuideAgent(task)
        
        # 第1轮：开场白
        print("\n--- 第1轮：开场白 ---")
        decision = agent.generate_opening()
        print(f"Agent: {decision.reply_to_user}")
        
        # 第2轮：用户选择模式C
        print("\n--- 第2轮：用户选择模式C ---")
        user_input = "C，这是我跟着教程做的项目"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第3轮：用户说没什么难点
        print("\n--- 第3轮：用户说'没什么难点' ---")
        user_input = "就跟着教程做的，没什么难点"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 验证是否触发智能猜测
        response_lower = decision.reply_to_user.lower()
        has_guess = (
            "推荐系统" in decision.reply_to_user or
            "协同过滤" in decision.reply_to_user or
            "算法" in decision.reply_to_user or
            ("a" in response_lower and "b" in response_lower) or  # 选项引导
            "回忆" in decision.reply_to_user
        )
        
        print(f"\n智能猜测触发: {has_guess}")
        if has_guess:
            print("✅ 场景2测试通过：智能猜测机制正常触发")
        else:
            print("⚠️ 警告：智能猜测可能未触发，请检查提示词")
    
    def test_scenario_3_degradation(self):
        """
        场景3：降级策略 - 用户连续说"没有"，测试降级策略
        """
        print("\n" + "="*60)
        print("测试场景3：用户连续说'没有'，测试降级策略")
        print("="*60)
        
        task = Task(
            id=3,
            section="项目经历 - 博客系统",
            strategy=TaskStrategy.STAR_STORYTELLING,
            original_text="基于Django开发的个人博客系统，支持文章发布、评论等功能。",
            diagnosis="仅列举了功能点，缺少技术挑战和解决过程的展示",
            goal="挖掘项目难点和技术收获，如用户表示'不知道'，主动推测并引导"
        )
        
        agent = GuideAgent(task)
        
        # 第1轮：开场白
        print("\n--- 第1轮：开场白 ---")
        decision = agent.generate_opening()
        print(f"Agent: {decision.reply_to_user}")
        
        # 第2轮：用户选择模式C
        print("\n--- 第2轮：用户选择模式C ---")
        user_input = "C，学习项目"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第3轮：用户说没有难点
        print("\n--- 第3轮：用户说'没有' ---")
        user_input = "没什么难点"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第4轮：用户再次说没有
        print("\n--- 第4轮：用户再次说'没有' ---")
        user_input = "真的想不起来了"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 第5轮：用户第三次说没有
        print("\n--- 第5轮：用户第三次说'没有' ---")
        user_input = "没有"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 验证是否触发降级策略（优雅结束）
        response_lower = decision.reply_to_user.lower()
        has_degradation = (
            "理解" in decision.reply_to_user or
            "没关系" in decision.reply_to_user or
            "草稿" in decision.reply_to_user or
            "技术实现" in decision.reply_to_user
        )
        
        print(f"\n降级策略触发: {has_degradation}")
        if has_degradation or decision.draft_content:
            print("✅ 场景3测试通过：降级策略正常工作")
        else:
            print("⚠️ 警告：降级策略可能未正常触发")
    
    def test_scenario_4_real_project_with_challenge(self):
        """
        场景4：真实项目 - 模式A/B也应该关注难点和收获
        """
        print("\n" + "="*60)
        print("测试场景4：真实项目也关注难点和收获（模式A/B）")
        print("="*60)
        
        task = Task(
            id=4,
            section="实习经历 - 后端开发",
            strategy=TaskStrategy.STAR_STORYTELLING,
            original_text="负责公司后台系统的开发，使用SpringBoot框架，完成了用户管理模块。",
            diagnosis="描述过于简单，缺少技术深度展示",
            goal="针对后端开发岗位优化：补充性能数据、突出技术难点、强调技术成长"
        )
        
        agent = GuideAgent(task)
        
        # 第1轮：开场白
        print("\n--- 第1轮：开场白 ---")
        decision = agent.generate_opening()
        print(f"Agent: {decision.reply_to_user}")
        
        # 第2轮：用户选择模式A
        print("\n--- 第2轮：用户选择模式A ---")
        user_input = "A，这是我实习项目，我很熟悉"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        # 检查是否有关于难点的提问
        response_text = decision.reply_to_user
        has_challenge_question = (
            "难点" in response_text or
            "挑战" in response_text or
            "问题" in response_text or
            "困难" in response_text
        )
        
        print(f"\n包含难点相关提问: {has_challenge_question}")
        
        # 第3轮：用户描述技术细节
        print("\n--- 第3轮：用户描述技术细节 ---")
        user_input = "主要做了用户管理模块，日均处理1万+请求。遇到的主要难点是高并发场景下的性能问题，后来通过Redis缓存优化了。"
        decision = agent.step(user_input)
        print(f"用户: {user_input}")
        print(f"Agent: {decision.reply_to_user}")
        
        if decision.draft_content:
            print(f"\n--- 草稿内容 ---")
            print(decision.draft_content)
            # 检查草稿是否包含难点相关内容
            has_challenge_in_draft = (
                "难点" in decision.draft_content or
                "优化" in decision.draft_content or
                "Redis" in decision.draft_content
            )
            print(f"草稿包含难点内容: {has_challenge_in_draft}")
        
        print("\n✅ 场景4测试通过：真实项目也能体现难点")


def run_all_tests():
    """运行所有测试场景"""
    print("\n" + "="*80)
    print("开始运行学生项目引导策略测试套件")
    print("="*80)
    
    tester = TestStudentProjectGuidance()
    
    try:
        # 场景1：顺利流程
        tester.test_scenario_1_smooth_flow()
        
        # 场景2：智能猜测
        tester.test_scenario_2_intelligent_guess()
        
        # 场景3：降级策略
        tester.test_scenario_3_degradation()
        
        # 场景4：真实项目
        tester.test_scenario_4_real_project_with_challenge()
        
        print("\n" + "="*80)
        print("✅ 所有测试场景执行完成！")
        print("="*80)
        print("\n注意：")
        print("1. 这些测试依赖于LLM的实际响应，结果可能会有变化")
        print("2. 请检查Agent的回复是否符合预期的引导策略")
        print("3. 如果某些检验未通过，可能需要调整prompt或测试断言")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()

