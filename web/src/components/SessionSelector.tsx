import React, { useState } from 'react';
import { ChevronDown, ChevronUp, History } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SessionMetadata } from '../utils/sessionManager';
import { SessionCard } from './SessionCard';

interface SessionSelectorProps {
  sessions: SessionMetadata[];
  selectedSession: SessionMetadata;
  onSelect: (session: SessionMetadata) => void;
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

export function SessionSelector({ sessions, selectedSession, onSelect }: SessionSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // 如果没有会话，返回空
  if (sessions.length === 0) {
    return null;
  }
  
  return (
    <div className="space-y-2">
      {/* 居中显示：当前选中的会话 */}
      <motion.div 
        className="relative"
        layout
        initial={false}
        animate={{
          // 展开时，第一个卡片向上移动（从居中到顶部）
          y: isExpanded ? 0 : 0
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <SessionCard
          session={selectedSession}
          isSelected={true}
          onClick={() => sessions.length > 1 && setIsExpanded(!isExpanded)}
        />
        
        {/* 展开按钮（如果有多个会话） */}
        {sessions.length > 1 && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-1.5 hover:bg-blue-100 rounded-full transition-colors z-10"
            aria-label={isExpanded ? '收起' : '展开'}
          >
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-blue-600" />
            ) : (
              <ChevronDown className="w-5 h-5 text-blue-600" />
            )}
          </button>
        )}
      </motion.div>
      
      {/* 下拉列表 - 阶梯动画 */}
      <AnimatePresence>
        {isExpanded && sessions.length > 1 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-2 overflow-hidden"
          >
            {sessions
              .filter(s => s.id !== selectedSession.id)
              .map((session, idx) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ 
                    delay: idx * 0.05, // 阶梯延迟
                    type: "spring",
                    stiffness: 300,
                    damping: 25
                  }}
                >
                  <SessionCard
                    session={session}
                    isSelected={false}
                    onClick={() => {
                      onSelect(session);
                      setIsExpanded(false);
                    }}
                    showTime={true}
                    timeAgo={calculateTimeAgo(session.updated_at)}
                  />
                </motion.div>
              ))
            }
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* 提示文字（仅在有多个会话且未展开时显示） */}
      {sessions.length > 1 && !isExpanded && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs text-center text-gray-400 flex items-center justify-center gap-1"
        >
          <History className="w-3 h-3" />
          {sessions.length - 1} 个其他会话
        </motion.p>
      )}
    </div>
  );
}


