"""
会话持久化工具：负责会话数据的磁盘存储和读取

存储结构：
backend/storage/sessions/
  ├── {session_id_1}/
  │   ├── metadata.json        # 会话元数据（快速列表查询）
  │   ├── workflow_state.json  # 完整WorkflowState
  │   └── resume.pdf           # 原始PDF（如果有）
"""
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from workflow_state import WorkflowState
from model import Resume

logger = logging.getLogger(__name__)

# 默认存储路径
DEFAULT_STORAGE_PATH = Path(__file__).parent / "storage" / "sessions"


class SessionMetadata:
    """会话元数据（用于列表展示）"""
    
    def __init__(
        self,
        id: str,
        name: Optional[str],
        resume_file_name: str,
        job_title: str,
        job_company: str,
        created_at: str,
        updated_at: str,
        progress: Dict[str, int],
        status: str
    ):
        self.id = id
        self.name = name
        self.resume_file_name = resume_file_name
        self.job_title = job_title
        self.job_company = job_company
        self.created_at = created_at
        self.updated_at = updated_at
        self.progress = progress
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "resume_file_name": self.resume_file_name,
            "job_title": self.job_title,
            "job_company": self.job_company,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        return cls(**data)


class SessionPersistence:
    """会话持久化管理器"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"会话存储目录: {self.storage_path}")
    
    def _get_session_dir(self, session_id: str) -> Path:
        """获取会话目录路径"""
        return self.storage_path / session_id
    
    def _ensure_session_dir(self, session_id: str) -> Path:
        """确保会话目录存在"""
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def save_workflow_state(
        self,
        state: WorkflowState,
        metadata: SessionMetadata
    ) -> bool:
        """
        保存会话数据到磁盘
        
        Args:
            state: WorkflowState对象
            metadata: 会话元数据
        
        Returns:
            是否保存成功
        """
        try:
            session_dir = self._ensure_session_dir(state.session_id)
            
            # 保存 workflow_state.json
            state_file = session_dir / "workflow_state.json"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 保存 metadata.json
            metadata_file = session_dir / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"会话 {state.session_id} 已保存到磁盘")
            return True
            
        except Exception as e:
            logger.exception(f"保存会话 {state.session_id} 失败: {e}")
            return False
    
    def load_workflow_state(self, session_id: str) -> Optional[WorkflowState]:
        """
        从磁盘加载会话数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            WorkflowState对象，如果不存在则返回None
        """
        try:
            session_dir = self._get_session_dir(session_id)
            state_file = session_dir / "workflow_state.json"
            
            if not state_file.exists():
                logger.warning(f"会话 {session_id} 不存在")
                return None
            
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            
            state = WorkflowState.from_dict(state_data)
            logger.info(f"会话 {session_id} 已从磁盘加载")
            return state
            
        except Exception as e:
            logger.exception(f"加载会话 {session_id} 失败: {e}")
            return None
    
    def load_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """
        从磁盘加载会话元数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            SessionMetadata对象，如果不存在则返回None
        """
        try:
            session_dir = self._get_session_dir(session_id)
            metadata_file = session_dir / "metadata.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata_data = json.load(f)
            
            return SessionMetadata.from_dict(metadata_data)
            
        except Exception as e:
            logger.exception(f"加载会话元数据 {session_id} 失败: {e}")
            return None
    
    def list_all_sessions(self) -> List[SessionMetadata]:
        """
        列出所有会话的元数据
        
        Returns:
            会话元数据列表，按更新时间倒序排列
        """
        sessions = []
        
        try:
            if not self.storage_path.exists():
                return []
            
            for session_dir in self.storage_path.iterdir():
                if not session_dir.is_dir():
                    continue
                
                metadata_file = session_dir / "metadata.json"
                if not metadata_file.exists():
                    continue
                
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata_data = json.load(f)
                    
                    metadata = SessionMetadata.from_dict(metadata_data)
                    sessions.append(metadata)
                except Exception as e:
                    logger.warning(f"跳过无效会话 {session_dir.name}: {e}")
                    continue
            
            # 按更新时间倒序排列
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            logger.info(f"找到 {len(sessions)} 个会话")
            return sessions
            
        except Exception as e:
            logger.exception(f"列出会话失败: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否删除成功
        """
        try:
            session_dir = self._get_session_dir(session_id)
            
            if not session_dir.exists():
                logger.warning(f"会话 {session_id} 不存在，无需删除")
                return False
            
            shutil.rmtree(session_dir)
            logger.info(f"会话 {session_id} 已从磁盘删除")
            return True
            
        except Exception as e:
            logger.exception(f"删除会话 {session_id} 失败: {e}")
            return False
    
    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        session_dir = self._get_session_dir(session_id)
        return session_dir.exists() and (session_dir / "workflow_state.json").exists()
    
    def save_resume_pdf(self, session_id: str, pdf_content: bytes) -> bool:
        """
        保存简历PDF文件
        
        Args:
            session_id: 会话ID
            pdf_content: PDF文件二进制内容
        
        Returns:
            是否保存成功
        """
        try:
            session_dir = self._ensure_session_dir(session_id)
            pdf_file = session_dir / "resume.pdf"
            
            with open(pdf_file, "wb") as f:
                f.write(pdf_content)
            
            logger.info(f"会话 {session_id} 的PDF已保存")
            return True
            
        except Exception as e:
            logger.exception(f"保存PDF失败: {e}")
            return False


# 全局持久化管理器实例
session_persistence = SessionPersistence()

