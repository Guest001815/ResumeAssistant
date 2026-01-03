/**
 * SessionDrawer: 会话抽屉组件
 * 
 * 左侧滑出的会话列表，支持：
 * - 查看所有会话
 * - 切换会话
 * - 删除会话
 * - 重命名会话
 * - 创建新会话
 * 
 * 设计风格：Notion 简洁风 + emerald 主色调
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Plus, 
  Trash2, 
  Edit2, 
  Check, 
  FileText, 
  CheckCircle, 
  Briefcase, 
  Clock,
  Sparkles
} from 'lucide-react';
import { SessionMetadata } from '../utils/sessionManager';

// ==================== 组件Props ====================

interface SessionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: SessionMetadata[];
  currentSessionId: string | null;
  onSwitch: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onCreate: () => void;
  onRename: (sessionId: string, newName: string) => void;
}

interface SessionCardProps {
  session: SessionMetadata;
  isActive: boolean;
  onSwitch: () => void;
  onDelete: () => void;
  onRename: (newName: string) => void;
}

// ==================== 迷你进度环组件 ====================

function MiniProgressRing({ completed, total }: { completed: number; total: number }) {
  const percentage = total > 0 ? (completed / total) * 100 : 0;
  const radius = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative w-7 h-7 flex items-center justify-center">
      <svg className="w-7 h-7 -rotate-90" viewBox="0 0 24 24">
        {/* 背景圆环 */}
        <circle
          cx="12"
          cy="12"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className="text-gray-200"
        />
        {/* 进度圆环 */}
        <circle
          cx="12"
          cy="12"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="text-emerald-500 transition-all duration-300"
        />
      </svg>
      <span className="absolute text-[9px] font-medium text-gray-600">
        {completed}
      </span>
    </div>
  );
}

// ==================== SessionCard 组件 ====================

function SessionCard({ session, isActive, onSwitch, onDelete, onRename }: SessionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [editValue, setEditValue] = useState(session.name || '');

  const handleRename = () => {
    if (editValue.trim() && editValue !== session.name) {
      onRename(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`确定要删除会话"${session.name || session.job_company}"吗？`)) {
      onDelete();
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      
      if (days === 0) {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        if (hours === 0) {
          const mins = Math.floor(diff / (1000 * 60));
          return `${mins}分钟前`;
        }
        return `${hours}小时前`;
      } else if (days === 1) {
        return '昨天';
      } else if (days < 7) {
        return `${days}天前`;
      } else {
        return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
      }
    } catch {
      return '';
    }
  };

  const displayName = session.name || `${session.job_company} - ${session.job_title}`;
  const isCompleted = session.status === 'completed';

  return (
    <motion.div
      className={`
        mx-3 mb-2 rounded-xl cursor-pointer transition-all duration-200
        ${isActive 
          ? 'bg-emerald-50 border-l-[3px] border-l-emerald-500 shadow-sm' 
          : 'hover:bg-gray-50 border-l-[3px] border-l-transparent hover:shadow-sm'
        }
      `}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={() => !isEditing && onSwitch()}
      initial={false}
      animate={{ 
        y: hovering && !isActive ? -1 : 0,
      }}
      transition={{ duration: 0.15 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="p-3">
        {/* 紧凑模式 */}
        <AnimatePresence mode="wait">
          {!hovering ? (
            <motion.div 
              key="compact"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              className="flex items-center gap-3"
            >
              {/* 状态图标 */}
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                ${isActive 
                  ? 'bg-emerald-500 text-white' 
                  : isCompleted 
                    ? 'bg-emerald-100 text-emerald-600' 
                    : 'bg-gray-100 text-gray-500'
                }
              `}>
                {isActive ? (
                  <Sparkles className="w-4 h-4" />
                ) : isCompleted ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
              </div>
              
              {/* 会话信息 */}
              <div className="flex-1 min-w-0">
                <div className={`font-medium truncate text-sm ${isActive ? 'text-emerald-900' : 'text-gray-800'}`}>
                  {session.job_company}
                </div>
                <div className={`text-xs truncate ${isActive ? 'text-emerald-600' : 'text-gray-500'}`}>
                  {session.job_title}
                </div>
              </div>
              
              {/* 进度环 */}
              <MiniProgressRing 
                completed={session.progress.completed} 
                total={session.progress.total} 
              />
            </motion.div>
          ) : (
            <motion.div 
              key="expanded"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              className="space-y-3"
            >
              {/* 标题编辑区 */}
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={handleRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleRename();
                      if (e.key === 'Escape') setIsEditing(false);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="flex-1 px-2 py-1 text-sm border border-emerald-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                    autoFocus
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRename();
                    }}
                    className="p-1.5 text-emerald-600 hover:bg-emerald-100 rounded-lg transition-colors"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <span className={`font-medium text-sm flex-1 min-w-0 truncate ${isActive ? 'text-emerald-900' : 'text-gray-800'}`}>
                    {displayName}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsEditing(true);
                    }}
                    className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="重命名"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* 详细信息 */}
              <div className="text-xs text-gray-500 space-y-1.5">
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-gray-400" />
                  <span className="truncate">{session.resume_file_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Briefcase className="w-3.5 h-3.5 text-gray-400" />
                  <span className="truncate">{session.job_title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3.5 h-3.5 flex items-center justify-center">
                    <div className="w-full h-1 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${session.progress.total > 0 ? (session.progress.completed / session.progress.total) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                  <span>
                    {session.progress.completed}/{session.progress.total} 任务
                    {isCompleted && (
                      <span className="ml-1 text-emerald-600 font-medium">已完成</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span>{formatDate(session.updated_at)}</span>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2 pt-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSwitch();
                  }}
                  className={`
                    flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
                    ${isActive 
                      ? 'text-emerald-700 bg-emerald-100 cursor-default' 
                      : 'text-emerald-600 bg-emerald-50 hover:bg-emerald-100'
                    }
                  `}
                >
                  {isActive ? '当前会话' : '切换到此会话'}
                </button>
                <button
                  onClick={handleDelete}
                  className="px-2 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title="删除"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ==================== SessionDrawer 主组件 ====================

export default function SessionDrawer({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  onSwitch,
  onDelete,
  onCreate,
  onRename
}: SessionDrawerProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* 遮罩层 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-40"
            onClick={onClose}
          />

          {/* 抽屉 */}
          <motion.div
            initial={{ x: -320 }}
            animate={{ x: 0 }}
            exit={{ x: -320 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 h-full w-[300px] bg-white shadow-2xl z-50 flex flex-col rounded-r-2xl overflow-hidden"
          >
            {/* 头部 */}
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-gray-800">会话列表</h2>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={onCreate}
                  className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-xl transition-colors"
                  title="新建会话"
                >
                  <Plus className="w-5 h-5" />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                  title="关闭"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 会话列表 */}
            <div className="flex-1 overflow-y-auto py-3">
              {sessions.length === 0 ? (
                <div className="p-8 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-gray-400" />
                  </div>
                  <p className="text-sm text-gray-500 mb-1">暂无会话</p>
                  <p className="text-xs text-gray-400">点击上方 + 创建新会话</p>
                </div>
              ) : (
                sessions.map((session) => (
                  <SessionCard
                    key={session.id}
                    session={session}
                    isActive={session.id === currentSessionId}
                    onSwitch={() => onSwitch(session.id)}
                    onDelete={() => onDelete(session.id)}
                    onRename={(name) => onRename(session.id, name)}
                  />
                ))
              )}
            </div>

            {/* 底部统计 */}
            <div className="px-5 py-3 border-t border-gray-100 shrink-0">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>共 {sessions.length} 个会话</span>
                <button
                  onClick={onCreate}
                  className="flex items-center gap-1 text-emerald-600 hover:text-emerald-700 font-medium transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  新建
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
