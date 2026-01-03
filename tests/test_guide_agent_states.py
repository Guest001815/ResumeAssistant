"""
B测试：单元测试 - Guide Agent 状态机测试

测试 Guide Agent 的各个状态转换逻辑
"""
import sys
import os
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from guide_agent import GuideAgent
from model import Task, AgentState
import logging

logging.basicConfig(level=logging.WARNING)  # 减少日志输出

class TestResult:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.total += 1
        self.passed += 1
        print(f"   ✅ {test_name}")
    
    def add_fail(self, test_name, reason):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, reason))
        print(f"   ❌ {test_name}: {reason}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print(f"测试总结: {self.passed}/{self.total} 通过")
        if self.failed > 0:
            print(f"\n失败的测试:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print("=" * 60)
        return self.failed == 0


def test_discovery_to_drafting():
    """测试1: DISCOVERY → DRAFTING 状态转换"""
    print("\n【测试1】DISCOVERY → DRAFTING 状态转换")
    print("-" * 60)
    result = TestResult()
    
    task = Task(
        id=1,
        section="工作经历",
        original_text="2020-2023 ABC公司 - Python开发",
        diagnosis="描述过于简单",
        goal="添加具体项目和成果"
    )
    
    agent = GuideAgent(task)
    
    # 验证初始状态
    if agent.current_state == AgentState.DISCOVERY:
        result.add_pass("初始状态为DISCOVERY")
    else:
        result.add_fail("初始状态", f"期望DISCOVERY，实际{agent.current_state}")
    
    # 模拟用户提供信息
    try:
        decision = agent.step("我负责后端API开发，主要使用Python和Django框架，开发了用户管理系统和订单系统")
        result.add_pass("接收用户输入")
        
        # 检查是否有回复
        if decision.reply_to_user:
            result.add_pass("生成回复")
        else:
            result.add_fail("生成回复", "回复为空")
        
        # 检查状态（可能还在DISCOVERY，也可能进入DRAFTING）
        if agent.current_state in [AgentState.DISCOVERY, AgentState.DRAFTING]:
            result.add_pass(f"状态合理 ({agent.current_state.value})")
        else:
            result.add_fail("状态转换", f"意外状态{agent.current_state}")
        
    except Exception as e:
        result.add_fail("执行step", str(e))
    
    return result.summary()


def test_drafting_to_confirming():
    """测试2: DRAFTING → CONFIRMING 状态转换"""
    print("\n【测试2】DRAFTING → CONFIRMING 状态转换")
    print("-" * 60)
    result = TestResult()
    
    task = Task(
        id=2,
        section="项目经验",
        original_text="开发了电商系统",
        diagnosis="缺少细节",
        goal="添加技术栈和成果"
    )
    
    agent = GuideAgent(task)
    
    # 快速进入DRAFTING状态
    agent.step("我开发了一个电商系统，使用Python+Django+MySQL+Redis，支持10万用户，日订单1000+")
    
    # 再次输入，期望生成草稿
    try:
        decision = agent.step("就按这个写吧，把技术栈和数据都写进去")
        
        # 检查是否生成草稿
        if agent.draft:
            result.add_pass(f"生成草稿 ({len(agent.draft)}字符)")
        else:
            result.add_fail("生成草稿", "草稿为空")
        
        # 检查状态
        if agent.current_state in [AgentState.DRAFTING, AgentState.CONFIRMING]:
            result.add_pass(f"状态正确 ({agent.current_state.value})")
        else:
            result.add_fail("状态", f"期望DRAFTING或CONFIRMING，实际{agent.current_state}")
        
    except Exception as e:
        result.add_fail("生成草稿", str(e))
    
    return result.summary()


def test_confirming_to_finished():
    """测试3: CONFIRMING → FINISHED 状态转换"""
    print("\n【测试3】CONFIRMING → FINISHED 状态转换")
    print("-" * 60)
    result = TestResult()
    
    task = Task(
        id=3,
        section="技能",
        original_text="Python, Django",
        diagnosis="技能列表不完整",
        goal="补充相关技能"
    )
    
    agent = GuideAgent(task)
    
    # 快速进入CONFIRMING状态
    agent.step("我会Python、Django、MySQL、Redis、Docker、Git")
    agent.step("可以了，就这样写")
    
    # 如果已经进入CONFIRMING，尝试确认
    if agent.current_state == AgentState.CONFIRMING:
        result.add_pass("成功进入CONFIRMING状态")
        
        try:
            decision = agent.step("确认")
            
            if agent.is_finished():
                result.add_pass("成功完成任务")
            else:
                result.add_fail("完成任务", f"状态为{agent.current_state}")
            
            if agent.execution_doc:
                result.add_pass("生成ExecutionDoc")
            else:
                result.add_fail("ExecutionDoc", "未生成")
                
        except Exception as e:
            result.add_fail("确认操作", str(e))
    else:
        # 如果还没进入CONFIRMING，继续尝试
        result.add_pass(f"当前状态: {agent.current_state.value}")
        try:
            decision = agent.step("确认，可以了")
            if agent.is_finished() or agent.is_confirming():
                result.add_pass("状态转换正常")
            else:
                result.add_fail("状态", f"意外状态{agent.current_state}")
        except Exception as e:
            result.add_fail("状态转换", str(e))
    
    return result.summary()


def test_drafting_loop():
    """测试4: DRAFTING → DRAFTING 循环（修改草稿）"""
    print("\n【测试4】DRAFTING → DRAFTING 循环")
    print("-" * 60)
    result = TestResult()
    
    task = Task(
        id=4,
        section="自我评价",
        original_text="热爱编程",
        diagnosis="过于简单",
        goal="具体化"
    )
    
    agent = GuideAgent(task)
    
    # 生成初始草稿
    agent.step("我有3年Python开发经验，熟悉Django和FastAPI")
    first_draft = agent.draft
    
    if first_draft:
        result.add_pass("生成初始草稿")
    else:
        result.add_fail("初始草稿", "未生成")
        return result.summary()
    
    # 请求修改
    try:
        decision = agent.step("再加上我熟悉微服务架构和Docker容器化")
        second_draft = agent.draft
        
        if second_draft and second_draft != first_draft:
            result.add_pass("草稿已更新")
        elif second_draft == first_draft:
            result.add_fail("草稿更新", "草稿未变化")
        else:
            result.add_fail("草稿更新", "草稿丢失")
        
        # 状态应该还在DRAFTING
        if agent.current_state in [AgentState.DRAFTING, AgentState.CONFIRMING]:
            result.add_pass(f"状态保持在{agent.current_state.value}")
        else:
            result.add_fail("状态", f"意外状态{agent.current_state}")
            
    except Exception as e:
        result.add_fail("修改草稿", str(e))
    
    return result.summary()


def test_state_persistence():
    """测试5: 状态恢复测试"""
    print("\n【测试5】状态恢复测试")
    print("-" * 60)
    result = TestResult()
    
    task = Task(
        id=5,
        section="教育背景",
        original_text="本科",
        diagnosis="信息不完整",
        goal="补充学校和专业"
    )
    
    agent1 = GuideAgent(task)
    
    # 进行一些交互
    agent1.step("我是计算机科学专业，某某大学毕业")
    agent1.step("GPA 3.8，获得过奖学金")
    
    # 导出状态
    snapshot = agent1.export_state()
    
    if snapshot:
        result.add_pass("导出状态快照")
    else:
        result.add_fail("导出状态", "快照为空")
        return result.summary()
    
    # 创建新agent并恢复状态
    agent2 = GuideAgent(task)
    
    try:
        agent2.load_state(snapshot)
        result.add_pass("加载状态快照")
        
        # 验证状态一致性
        if agent2.current_state == agent1.current_state:
            result.add_pass("状态一致")
        else:
            result.add_fail("状态一致性", f"{agent1.current_state} != {agent2.current_state}")
        
        if len(agent2.messages) == len(agent1.messages):
            result.add_pass(f"对话历史一致 ({len(agent2.messages)}条)")
        else:
            result.add_fail("对话历史", f"{len(agent1.messages)} != {len(agent2.messages)}")
        
        if agent2.draft == agent1.draft:
            result.add_pass("草稿一致")
        else:
            result.add_fail("草稿一致性", "草稿不匹配")
        
    except Exception as e:
        result.add_fail("加载状态", str(e))
    
    return result.summary()


def main():
    print("=" * 60)
    print("B测试：单元测试 - Guide Agent 状态机")
    print("=" * 60)
    
    # 运行所有测试
    all_passed = True
    all_passed &= test_discovery_to_drafting()
    all_passed &= test_drafting_to_confirming()
    all_passed &= test_confirming_to_finished()
    all_passed &= test_drafting_loop()
    all_passed &= test_state_persistence()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有单元测试通过！")
    else:
        print("❌ 部分测试失败，请查看上面的详细信息")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

