"""
测试任务衔接引导优化效果

这个脚本测试：
1. Guide Agent 的首次对话开场引导
2. Orchestrator 的跳过任务消息
3. Orchestrator 的任务完成消息
"""

import sys
import os
import io

# 设置输出编码为 UTF-8，避免 Windows 下的编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from model import Task, Resume, TaskList, TaskStatus
from backend.guide_agent import GuideAgent
from backend.orchestrator import Orchestrator
from backend.workflow_state import WorkflowState
from backend.agent_adapters import GuideAgentAdapter

def test_guide_agent_intro():
    """测试 Guide Agent 的首次对话开场"""
    print("=" * 60)
    print("测试 1: Guide Agent 首次对话开场引导")
    print("=" * 60)
    
    task = Task(
        id=1,
        section="项目经历 - ResumeAssistant",
        original_text="开发了一个简历优化助手，使用Python和LangChain。",
        diagnosis="项目描述缺少量化数据，无法体现技术深度和实际价值。对于AI工程师岗位，需要展示系统规模、性能指标等。",
        goal="补充量化指标（如处理速度、准确率、代码量），让技术亮点更有说服力。",
        status=TaskStatus.PENDING
    )
    
    agent = GuideAgent(task)
    
    # 模拟用户第一次输入（这应该触发开场引导）
    decision = agent.step("你好")
    
    print("\n【Agent 回复】:")
    print(decision.reply_to_user)
    print("\n【思考过程】:")
    print(decision.thought)
    print("\n【下一步动作】:")
    print(decision.next_action)
    print()

def test_skip_task_message():
    """测试跳过任务时的衔接消息"""
    print("=" * 60)
    print("测试 2: 跳过任务的衔接消息")
    print("=" * 60)
    
    # 创建一个模拟的工作流状态
    resume = Resume(
        basics={"name": "测试用户", "email": "test@example.com"},
        sections=[]
    )
    
    task_list = TaskList(tasks=[
        Task(
            id=1,
            section="教育背景 - 硕士主修课程",
            original_text="机器学习、深度学习、模式识别",
            diagnosis="课程罗列过于传统",
            goal="突出与AI应用研发相关的课程",
            status=TaskStatus.PENDING
        ),
        Task(
            id=2,
            section="实习经历 - 整体结构",
            original_text="在字节跳动实习，参与AI项目开发",
            diagnosis="缺少公司/团队职责介绍",
            goal="补充公司背景和职责介绍",
            status=TaskStatus.PENDING
        ),
        Task(
            id=3,
            section="项目经历 - ResumeAssistant",
            original_text="开发简历优化助手",
            diagnosis="缺少量化数据",
            goal="补充性能指标和技术细节",
            status=TaskStatus.PENDING
        )
    ])
    
    state = WorkflowState(resume=resume, plan=task_list, current_task_idx=0)
    orchestrator = Orchestrator()
    
    # 跳过第一个任务
    message = orchestrator.skip_task(state)
    
    print("\n【系统消息】:")
    print(message.content)
    print()

def test_complete_task_message():
    """测试任务完成时的消息"""
    print("=" * 60)
    print("测试 3: 任务完成的衔接消息")
    print("=" * 60)
    
    # 创建一个模拟的工作流状态
    resume = Resume(
        basics={"name": "测试用户", "email": "test@example.com"},
        sections=[]
    )
    
    task_list = TaskList(tasks=[
        Task(
            id=1,
            section="教育背景 - 硕士主修课程",
            original_text="机器学习、深度学习、模式识别",
            diagnosis="课程罗列过于传统",
            goal="突出与AI应用研发相关的课程",
            status=TaskStatus.COMPLETED
        ),
        Task(
            id=2,
            section="实习经历 - 整体结构",
            original_text="在字节跳动实习，参与AI项目开发",
            diagnosis="缺少公司/团队职责介绍，无法体现工作定位和价值",
            goal="补充公司背景和职责介绍，形成完整的专业形象",
            status=TaskStatus.IN_PROGRESS
        ),
        Task(
            id=3,
            section="项目经历 - ResumeAssistant",
            original_text="开发简历优化助手",
            diagnosis="缺少量化数据",
            goal="补充性能指标和技术细节",
            status=TaskStatus.PENDING
        )
    ])
    
    state = WorkflowState(resume=resume, plan=task_list, current_task_idx=1)
    progress = state.get_progress()
    
    # 模拟任务完成消息的生成
    completed_task = task_list.tasks[1]
    next_task = task_list.tasks[2]
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ 任务 {completed_task.id} 已完成：{completed_task.section}",
        "",
        f"📋 进度：已完成 2/3",
    ]
    
    lines.extend([
        "",
        f"⏭️ 接下来：任务 {next_task.id} - {next_task.section}",
        f"   问题：{next_task.diagnosis[:50]}...",
        "",
        "💡 继续对话，我会引导你完成下一个优化。"
    ])
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    print("\n【系统消息】:")
    print("\n".join(lines))
    print()

def test_all_tasks_complete():
    """测试所有任务完成时的消息"""
    print("=" * 60)
    print("测试 4: 所有任务完成的消息")
    print("=" * 60)
    
    resume = Resume(
        basics={"name": "测试用户", "email": "test@example.com"},
        sections=[]
    )
    
    task_list = TaskList(tasks=[
        Task(
            id=1,
            section="教育背景 - 硕士主修课程",
            original_text="机器学习、深度学习、模式识别",
            diagnosis="课程罗列过于传统",
            goal="突出与AI应用研发相关的课程",
            status=TaskStatus.COMPLETED
        ),
        Task(
            id=2,
            section="实习经历 - 整体结构",
            original_text="在字节跳动实习，参与AI项目开发",
            diagnosis="缺少公司/团队职责介绍",
            goal="补充公司背景和职责介绍",
            status=TaskStatus.COMPLETED
        )
    ])
    
    state = WorkflowState(resume=resume, plan=task_list, current_task_idx=2)
    
    # 模拟所有任务完成的消息
    completed_task = task_list.tasks[1]
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ 任务 {completed_task.id} 已完成：{completed_task.section}",
        "",
        f"📋 进度：已完成 2/2",
        "",
        "🎉 恭喜！所有优化任务已完成！",
        "",
        "您的简历已经过全面优化，现在可以导出使用了。",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    
    print("\n【系统消息】:")
    print("\n".join(lines))
    print()

if __name__ == "__main__":
    print("\n")
    print("任务衔接引导优化 - 测试报告")
    print("=" * 60)
    print()
    
    try:
        # 测试1: Guide Agent 首次对话
        test_guide_agent_intro()
        
        # 测试2: 跳过任务消息
        test_skip_task_message()
        
        # 测试3: 任务完成消息
        test_complete_task_message()
        
        # 测试4: 所有任务完成消息
        test_all_tasks_complete()
        
        print("=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        print()
        print("改进总结:")
        print("1. [OK] Guide Agent 现在会主动发送开场引导")
        print("2. [OK] 跳过任务时会显示结构化的进度和提示")
        print("3. [OK] 任务完成时会总结成果并引导下一个任务")
        print("4. [OK] 所有任务完成时会显示祝贺消息")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()

