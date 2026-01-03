"""
会话工具：用于处理会话相关的元数据提取和生成

主要功能：
- 从JD中提取职位名称和公司名称
- 生成会话默认名称
"""
import re
import logging
from typing import Tuple, Dict, Any
from model import Resume

logger = logging.getLogger(__name__)


def extract_job_info(user_intent: str) -> Tuple[str, str]:
    """
    从用户意图（JD）中提取职位和公司信息
    
    使用简单的正则匹配和关键词提取
    
    Args:
        user_intent: 用户输入的职位描述文本
    
    Returns:
        (job_title, job_company) 元组
    """
    job_title = "待定职位"
    job_company = "待定公司"
    
    try:
        # 提取公司名称的常见模式
        # 1. "XX公司"、"XX集团"、"XX科技"等
        company_patterns = [
            r'([^\s，。！？,\.!?]{2,15}(?:公司|集团|科技|互联网|网络|技术|软件|信息|数据|智能))',
            r'(字节跳动|腾讯|阿里巴巴|百度|美团|京东|拼多多|快手|小米|华为|OPPO|vivo)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # 英文公司名
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, user_intent)
            if match:
                job_company = match.group(1).strip()
                break
        
        # 提取职位名称的常见模式
        # 1. "XX工程师"、"XX开发"、"XX岗"等
        title_patterns = [
            r'((?:前端|后端|全栈|算法|机器学习|深度学习|数据|测试|运维|安全|产品|设计|UI|UX)(?:研发|开发)?工程师)',
            r'((?:Java|Python|Go|C\+\+|前端|后端|全栈|算法|大数据|AI)(?:开发|工程师))',
            r'([^\s，。！？,\.!?]{2,10}(?:工程师|开发|架构师|专家|经理|总监))',
            r'(软件工程师|研发工程师|技术专家)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, user_intent)
            if match:
                job_title = match.group(1).strip()
                break
        
        # 如果没有匹配到，尝试从第一行提取
        if job_title == "待定职位" or job_company == "待定公司":
            lines = user_intent.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            if first_line:
                # 第一行通常是职位标题
                if job_title == "待定职位":
                    # 移除标点符号，取前20个字符作为职位名
                    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', first_line)
                    if cleaned:
                        job_title = cleaned[:20]
        
        logger.info(f"提取到职位信息: {job_title} @ {job_company}")
        
    except Exception as e:
        logger.warning(f"提取职位信息失败: {e}")
    
    return job_title, job_company


def generate_session_name(resume: Resume, user_intent: str) -> str:
    """
    生成会话默认名称
    
    格式：{姓名} - {职位} - {公司}
    
    Args:
        resume: Resume对象
        user_intent: 用户意图文本
    
    Returns:
        会话名称字符串
    """
    resume_name = resume.basics.name or "未命名"
    job_title, job_company = extract_job_info(user_intent)
    
    # 生成名称
    if job_title != "待定职位" and job_company != "待定公司":
        name = f"{resume_name} - {job_title} - {job_company}"
    elif job_title != "待定职位":
        name = f"{resume_name} - {job_title}"
    elif job_company != "待定公司":
        name = f"{resume_name} - {job_company}"
    else:
        name = f"{resume_name} - 简历优化"
    
    return name


def extract_session_metadata(resume: Resume, user_intent: str) -> Dict[str, Any]:
    """
    从简历和JD中提取会话元数据
    
    Args:
        resume: Resume对象
        user_intent: 用户意图文本
    
    Returns:
        包含元数据的字典
    """
    job_title, job_company = extract_job_info(user_intent)
    resume_name = resume.basics.name or "未命名"
    
    return {
        "name": generate_session_name(resume, user_intent),
        "job_title": job_title,
        "job_company": job_company,
        "resume_file_name": f"{resume_name}.pdf"
    }

