"""
测试草稿应用到简历的修复
验证用户确认草稿后，简历确实被更新
"""
import sys
import os
import json
import logging

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from model import Resume, Task, TaskStatus, TaskStrategy, ExecutionDoc, ExperienceSection, ExperienceItem
from editor_agent import EditorAgent
from guide_agent import GuideAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_execute_doc_with_item_id():
    """测试 ExecutionDoc 中包含 item_id 时的执行"""
    logger.info("=" * 80)
    logger.info("测试 1: ExecutionDoc 包含 item_id")
    logger.info("=" * 80)
    
    # 1. 创建测试简历
    resume = Resume(
        basics={
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "13800138000",
            "links": []
        },
        sections=[
            ExperienceSection(
                title="工作经历",
                items=[
                    ExperienceItem(
                        id="exp-1",
                        title="软件工程师",
                        organization="ABC公司",
                        date_start="2020-01",
                        date_end="2022-12",
                        highlights=[
                            "负责后端开发",
                            "使用Python和Django",
                            "参与了3个项目"
                        ]
                    ),
                    ExperienceItem(
                        id="exp-2",
                        title="实习生",
                        organization="XYZ公司",
                        date_start="2019-06",
                        date_end="2019-12",
                        highlights=[
                            "学习Java",
                            "完成了一些任务"
                        ]
                    )
                ]
            )
        ]
    )
    
    logger.info(f"初始简历: 工作经历第1个item有 {len(resume.sections[0].items[0].highlights)} 条highlights")
    logger.info(f"初始简历: 工作经历第2个item有 {len(resume.sections[0].items[1].highlights)} 条highlights")
    
    # 2. 创建 ExecutionDoc，指定要修改第2个item（exp-2）
    exec_doc = ExecutionDoc(
        task_id=1,
        section_title="工作经历",
        item_id="exp-2",  # 明确指定要修改第2个item
        operation="update_experience",
        changes={
            "section": "工作经历",
            "content": """1. 深入学习Java Spring框架，掌握MVC架构和依赖注入原理
2. 独立完成用户管理模块的开发，涉及RESTful API设计与实现
3. 参与代码审查，提升代码质量和团队协作能力
4. 优化数据库查询性能，将响应时间从500ms降至150ms"""
        },
        new_content_preview="优化后的实习经历",
        reason="实习经历太简单，需要量化成果"
    )
    
    # 3. 执行 EditorAgent
    editor = EditorAgent()
    messages = []
    updated_resume = None
    
    try:
        gen = editor.execute_doc(exec_doc, resume)
        try:
            while True:
                msg = next(gen)
                messages.append(msg)
                msg_content = str(msg.get('content', ''))
                if len(msg_content) > 100:
                    msg_content = msg_content[:100] + "..."
                logger.info(f"EditorAgent消息: {msg.get('type')} - {msg_content}")
        except StopIteration as e:
            updated_resume = e.value
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        return False
    
    # 4. 验证结果
    if updated_resume:
        exp_section = updated_resume.sections[0]
        item1_highlights = len(exp_section.items[0].highlights)
        item2_highlights = len(exp_section.items[1].highlights)
        
        logger.info(f"✅ 更新后: 工作经历第1个item有 {item1_highlights} 条highlights（应该不变）")
        logger.info(f"✅ 更新后: 工作经历第2个item有 {item2_highlights} 条highlights（应该更新）")
        
        # 验证：第1个item不应该变化，第2个item应该有4条新highlights
        if item1_highlights == 3 and item2_highlights == 4:
            logger.info("✅ 测试通过！正确更新了指定的item（exp-2）")
            logger.info(f"第2个item的新highlights: {exp_section.items[1].highlights}")
            return True
        else:
            logger.error(f"❌ 测试失败！预期第1个item=3条，第2个item=4条，实际: {item1_highlights}, {item2_highlights}")
            return False
    else:
        logger.error("❌ 测试失败：未返回更新后的简历")
        return False


def test_execute_doc_without_item_id():
    """测试 ExecutionDoc 不包含 item_id 时的降级处理"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: ExecutionDoc 不包含 item_id（降级处理）")
    logger.info("=" * 80)
    
    # 1. 创建测试简历
    resume = Resume(
        basics={
            "name": "李四",
            "email": "lisi@example.com"
        },
        sections=[
            ExperienceSection(
                title="项目经历",
                items=[
                    ExperienceItem(
                        id="proj-1",
                        title="电商系统",
                        organization="个人项目",
                        highlights=["开发了一个电商系统"]
                    )
                ]
            )
        ]
    )
    
    logger.info(f"初始简历: 项目经历有 {len(resume.sections[0].items[0].highlights)} 条highlights")
    
    # 2. 创建 ExecutionDoc，不指定 item_id
    exec_doc = ExecutionDoc(
        task_id=1,
        section_title="项目经历",
        item_id=None,  # 不指定 item_id
        operation="update_experience",
        changes={
            "section": "项目经历",
            "content": """1. 使用Spring Boot + Vue.js构建前后端分离的电商平台
2. 实现用户注册、商品管理、订单处理等核心功能
3. 引入Redis缓存，提升系统并发能力50%
4. 部署在阿里云，月活用户达到5000+"""
        },
        new_content_preview="优化后的项目经历",
        reason="项目描述太简单"
    )
    
    # 3. 执行 EditorAgent
    editor = EditorAgent()
    updated_resume = None
    
    try:
        gen = editor.execute_doc(exec_doc, resume)
        try:
            while True:
                msg = next(gen)
                msg_content = str(msg.get('content', ''))
                if len(msg_content) > 100:
                    msg_content = msg_content[:100] + "..."
                logger.info(f"EditorAgent消息: {msg.get('type')} - {msg_content}")
        except StopIteration as e:
            updated_resume = e.value
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        return False
    
    # 4. 验证结果
    if updated_resume:
        proj_section = updated_resume.sections[0]
        highlights_count = len(proj_section.items[0].highlights)
        
        logger.info(f"✅ 更新后: 项目经历有 {highlights_count} 条highlights")
        
        if highlights_count == 4:
            logger.info("✅ 测试通过！降级处理成功更新了第一个item")
            logger.info(f"新highlights: {proj_section.items[0].highlights}")
            return True
        else:
            logger.error(f"❌ 测试失败！预期4条highlights，实际: {highlights_count}")
            return False
    else:
        logger.error("❌ 测试失败：未返回更新后的简历")
        return False


def test_guide_agent_build_execution_doc():
    """测试 GuideAgent 构建 ExecutionDoc 时正确传递 item_id"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: GuideAgent 构建 ExecutionDoc")
    logger.info("=" * 80)
    
    # 创建一个带 item_id 的 Task
    task = Task(
        id=1,
        section="工作经历",
        original_text="原始文本",  # 添加必需字段
        diagnosis="描述太简单",
        goal="量化成果",
        item_id="exp-123"  # 指定 item_id
    )
    
    # 创建 GuideAgent（不实际调用LLM）
    guide = GuideAgent(task=task)
    guide.draft = "优化后的内容"
    
    # 构建 ExecutionDoc
    exec_doc = guide._build_execution_doc()
    
    # 验证
    if exec_doc.item_id == "exp-123":
        logger.info(f"✅ 测试通过！ExecutionDoc正确包含item_id: {exec_doc.item_id}")
        return True
    else:
        logger.error(f"❌ 测试失败！预期item_id='exp-123'，实际: {exec_doc.item_id}")
        return False


def test_section_not_found_error():
    """测试找不到section时是否正确抛出异常"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 4: 找不到section时的错误处理")
    logger.info("=" * 80)
    
    # 创建测试简历
    resume = Resume(
        basics={"name": "王五"},
        sections=[
            ExperienceSection(
                title="工作经历",
                items=[
                    ExperienceItem(
                        id="exp-1",
                        title="开发工程师",
                        organization="公司A",
                        highlights=["做了一些事情"]
                    )
                ]
            )
        ]
    )
    
    # 创建一个指向不存在section的ExecutionDoc
    exec_doc = ExecutionDoc(
        task_id=1,
        section_title="项目经历",  # 这个section不存在
        item_id=None,
        operation="update_experience",
        changes={"content": "新内容"},
        new_content_preview="预览",
        reason="测试"
    )
    
    # 执行
    editor = EditorAgent()
    error_raised = False
    
    try:
        gen = editor.execute_doc(exec_doc, resume)
        while True:
            try:
                msg = next(gen)
            except StopIteration:
                break
    except ValueError as e:
        error_raised = True
        logger.info(f"✅ 正确抛出了异常: {e}")
    except Exception as e:
        logger.error(f"❌ 抛出了错误的异常类型: {type(e).__name__}: {e}")
        return False
    
    if error_raised:
        logger.info("✅ 测试通过！找不到section时正确抛出ValueError")
        return True
    else:
        logger.error("❌ 测试失败！应该抛出异常但没有")
        return False


def main():
    """运行所有测试"""
    logger.info("\n" + "🚀" * 40)
    logger.info("开始测试草稿应用修复")
    logger.info("🚀" * 40 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("包含item_id的执行", test_execute_doc_with_item_id()))
    results.append(("不包含item_id的降级处理", test_execute_doc_without_item_id()))
    results.append(("GuideAgent构建ExecutionDoc", test_guide_agent_build_execution_doc()))
    results.append(("找不到section的错误处理", test_section_not_found_error()))
    
    # 输出结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("\n" + "-" * 80)
    logger.info(f"总计: {passed} 通过, {failed} 失败")
    logger.info("-" * 80)
    
    if failed == 0:
        logger.info("\n🎉 所有测试通过！草稿应用修复成功！")
        return True
    else:
        logger.error(f"\n❌ 有 {failed} 个测试失败，请检查代码")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

