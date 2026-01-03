"""
简历持久化存储：独立于会话的简历存储管理

存储结构：
backend/storage/resumes/
  ├── {resume_id_1}.json   # 包含简历数据 + 元信息
  ├── {resume_id_2}.json
  └── ...
"""
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from model import Resume

logger = logging.getLogger(__name__)

# 默认存储路径
DEFAULT_STORAGE_PATH = Path(__file__).parent / "storage" / "resumes"


class ResumeMetadata:
    """简历元数据"""
    
    def __init__(
        self,
        id: str,
        name: str,
        label: str,
        created_at: str,
        updated_at: str,
    ):
        self.id = id
        self.name = name
        self.label = label
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeMetadata":
        return cls(**data)


class StoredResume:
    """存储的简历（包含元数据和完整数据）"""
    
    def __init__(self, metadata: ResumeMetadata, resume: Resume):
        self.metadata = metadata
        self.resume = resume
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "resume": self.resume.model_dump()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredResume":
        metadata = ResumeMetadata.from_dict(data["metadata"])
        resume = Resume.model_validate(data["resume"])
        return cls(metadata, resume)


class ResumeStorage:
    """简历持久化存储管理器"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"简历存储目录: {self.storage_path}")
    
    def _generate_resume_id(self, name: str) -> str:
        """
        根据姓名生成简历ID（MD5哈希）
        同名简历会有相同的ID，实现自动去重/更新
        """
        return hashlib.md5(name.encode('utf-8')).hexdigest()[:16]
    
    def _get_resume_file(self, resume_id: str) -> Path:
        """获取简历文件路径"""
        return self.storage_path / f"{resume_id}.json"
    
    def save_resume(self, resume: Resume) -> str:
        """
        保存简历（自动去重，同名更新）
        
        Args:
            resume: Resume对象
        
        Returns:
            简历ID
        """
        try:
            name = resume.basics.name or "未命名"
            resume_id = self._generate_resume_id(name)
            resume_file = self._get_resume_file(resume_id)
            
            now = datetime.now().isoformat()
            
            # 检查是否已存在，保留创建时间
            created_at = now
            if resume_file.exists():
                try:
                    with open(resume_file, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    created_at = existing.get("metadata", {}).get("created_at", now)
                    logger.info(f"更新已存在的简历: {name} (ID: {resume_id})")
                except Exception:
                    pass
            else:
                logger.info(f"创建新简历: {name} (ID: {resume_id})")
            
            # 创建元数据
            metadata = ResumeMetadata(
                id=resume_id,
                name=name,
                label=resume.basics.label or "",
                created_at=created_at,
                updated_at=now,
            )
            
            # 创建存储对象
            stored = StoredResume(metadata, resume)
            
            # 保存到文件
            with open(resume_file, "w", encoding="utf-8") as f:
                json.dump(stored.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"简历已保存: {resume_id}")
            return resume_id
            
        except Exception as e:
            logger.exception(f"保存简历失败: {e}")
            raise
    
    def get_resume(self, resume_id: str) -> Optional[StoredResume]:
        """
        获取单个简历
        
        Args:
            resume_id: 简历ID
        
        Returns:
            StoredResume对象，不存在则返回None
        """
        try:
            resume_file = self._get_resume_file(resume_id)
            
            if not resume_file.exists():
                logger.warning(f"简历不存在: {resume_id}")
                return None
            
            with open(resume_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return StoredResume.from_dict(data)
            
        except Exception as e:
            logger.exception(f"获取简历失败: {resume_id}, {e}")
            return None
    
    def list_resumes(self) -> List[StoredResume]:
        """
        列出所有简历
        
        Returns:
            简历列表，按更新时间倒序排列
        """
        resumes = []
        
        try:
            if not self.storage_path.exists():
                return []
            
            for resume_file in self.storage_path.glob("*.json"):
                try:
                    with open(resume_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    stored = StoredResume.from_dict(data)
                    resumes.append(stored)
                except Exception as e:
                    logger.warning(f"跳过无效简历文件 {resume_file.name}: {e}")
                    continue
            
            # 按更新时间倒序排列
            resumes.sort(key=lambda r: r.metadata.updated_at, reverse=True)
            logger.info(f"找到 {len(resumes)} 个简历")
            return resumes
            
        except Exception as e:
            logger.exception(f"列出简历失败: {e}")
            return []
    
    def delete_resume(self, resume_id: str) -> bool:
        """
        删除简历
        
        Args:
            resume_id: 简历ID
        
        Returns:
            是否删除成功
        """
        try:
            resume_file = self._get_resume_file(resume_id)
            
            if not resume_file.exists():
                logger.warning(f"简历不存在，无需删除: {resume_id}")
                return False
            
            resume_file.unlink()
            logger.info(f"简历已删除: {resume_id}")
            return True
            
        except Exception as e:
            logger.exception(f"删除简历失败: {resume_id}, {e}")
            return False
    
    def resume_exists(self, resume_id: str) -> bool:
        """检查简历是否存在"""
        return self._get_resume_file(resume_id).exists()
    
    def get_resume_by_name(self, name: str) -> Optional[StoredResume]:
        """
        根据姓名获取简历
        
        Args:
            name: 简历姓名
        
        Returns:
            StoredResume对象，不存在则返回None
        """
        resume_id = self._generate_resume_id(name)
        return self.get_resume(resume_id)


# 全局简历存储管理器实例
resume_storage = ResumeStorage()
