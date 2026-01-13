import React, { useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Resume } from '../api/workflow';
import { ResumeCard } from './ResumeCard';

export interface ResumeOption {
  id: string;
  resume: Resume;
  name: string;
  label: string;
  created_at: string;
  updated_at: string;
}

interface ResumeSelectorProps {
  resumes: ResumeOption[];
  selectedResume: Resume;
  selectedResumeId?: string;  // 新增：用于精确匹配选中的简历
  onSelect: (resume: Resume, resumeId: string) => void;
  onDelete?: (resumeId: string) => void;
  showDelete?: boolean;
}

// 计算时间差
function calculateTimeAgo(lastUsed: string): string {
  const now = new Date();
  const last = new Date(lastUsed);
  const diff = now.getTime() - last.getTime();
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor(diff / (1000 * 60));
  
  if (days > 7) {
    const weeks = Math.floor(days / 7);
    return `${weeks}周前`;
  } else if (days > 0) {
    return `${days}天前`;
  } else if (hours > 0) {
    return `${hours}小时前`;
  } else if (minutes > 0) {
    return `${minutes}分钟前`;
  } else {
    return '刚刚';
  }
}

export function ResumeSelector({ 
  resumes, 
  selectedResume,
  selectedResumeId,
  onSelect, 
  onDelete,
  showDelete = false 
}: ResumeSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  // 找到当前选中的简历选项（优先使用 ID 匹配，兼容旧逻辑）
  const selectedOption = selectedResumeId 
    ? resumes.find(r => r.id === selectedResumeId)
    : resumes.find(r => r.resume.basics.name === selectedResume.basics.name);

  const handleDelete = async (e: React.MouseEvent, resumeId: string) => {
    e.stopPropagation();
    
    if (!window.confirm('确定要删除这份简历吗？此操作不可恢复。')) {
      return;
    }
    
    setDeletingId(resumeId);
    try {
      onDelete?.(resumeId);
    } finally {
      setDeletingId(null);
    }
  };
  
  return (
    <div className="space-y-2">
      {/* 当前选中的简历 */}
      <div className="relative">
        <ResumeCard
          resume={selectedResume}
          isSelected={true}
          onClick={() => resumes.length > 1 && setIsExpanded(!isExpanded)}
        />
        
        {/* 展开按钮和删除按钮 */}
        <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {/* 删除按钮 */}
          {showDelete && selectedOption && (
            <button
              onClick={(e) => handleDelete(e, selectedOption.id)}
              disabled={deletingId === selectedOption.id}
              className="p-1.5 hover:bg-red-100 rounded-full transition-colors text-gray-400 hover:text-red-500"
              aria-label="删除简历"
              title="删除简历"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          
          {/* 展开按钮（如果有多个简历） */}
          {resumes.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="p-1.5 hover:bg-blue-100 rounded-full transition-colors"
              aria-label={isExpanded ? '收起' : '展开'}
            >
              {isExpanded ? (
                <ChevronUp className="w-5 h-5 text-blue-600" />
              ) : (
                <ChevronDown className="w-5 h-5 text-blue-600" />
              )}
            </button>
          )}
        </div>
      </div>
      
      {/* 下拉列表 */}
      <AnimatePresence>
        {isExpanded && resumes.length > 1 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-2 overflow-hidden"
          >
            {resumes
              .filter(r => selectedResumeId ? r.id !== selectedResumeId : r.resume.basics.name !== selectedResume.basics.name)
              .map((option) => (
                <div key={option.id} className="relative">
                  <ResumeCard
                    resume={option.resume}
                    isSelected={false}
                    onClick={() => {
                      onSelect(option.resume, option.id);
                      setIsExpanded(false);
                    }}
                    showTime={true}
                    timeAgo={calculateTimeAgo(option.updated_at)}
                  />
                  
                  {/* 删除按钮 */}
                  {showDelete && (
                    <button
                      onClick={(e) => handleDelete(e, option.id)}
                      disabled={deletingId === option.id}
                      className="absolute right-4 top-1/2 -translate-y-1/2 p-1.5 hover:bg-red-100 rounded-full transition-colors text-gray-400 hover:text-red-500"
                      aria-label="删除简历"
                      title="删除简历"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))
            }
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* 提示文字（仅在有多个简历且未展开时显示） */}
      {resumes.length > 1 && !isExpanded && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs text-center text-gray-400 flex items-center justify-center gap-1"
        >
          <RefreshCw className="w-3 h-3" />
          {resumes.length - 1} 个其他简历
        </motion.p>
      )}
    </div>
  );
}
