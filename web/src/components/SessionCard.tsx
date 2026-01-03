import React from 'react';
import { Briefcase, CheckCircle, Clock, Target } from 'lucide-react';
import { motion } from 'framer-motion';
import { SessionMetadata } from '../utils/sessionManager';

interface SessionCardProps {
  session: SessionMetadata;
  isSelected: boolean;
  onClick: () => void;
  showTime?: boolean;
  timeAgo?: string;
}

export function SessionCard({ 
  session, 
  isSelected, 
  onClick, 
  showTime = false, 
  timeAgo 
}: SessionCardProps) {
  const progressPercentage = session.progress.total > 0 
    ? Math.round((session.progress.completed / session.progress.total) * 100)
    : 0;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`
        relative p-4 rounded-xl border-2 cursor-pointer transition-all
        ${isSelected 
          ? 'border-blue-500 bg-blue-50 shadow-md' 
          : 'border-gray-200 hover:border-blue-300 bg-white hover:shadow-sm'
        }
      `}
    >
      <div className="flex items-center gap-3">
        {/* 图标 */}
        <div className={`
          w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
          ${isSelected ? 'bg-blue-500' : 'bg-gray-200'}
        `}>
          <Briefcase className={`w-6 h-6 ${isSelected ? 'text-white' : 'text-gray-500'}`} />
        </div>
        
        {/* 会话信息 */}
        <div className="flex-1 min-w-0">
          {/* 公司·职位 */}
          <h3 className="text-base font-semibold text-gray-900 truncate">
            {session.job_company && session.job_title 
              ? `${session.job_company} · ${session.job_title}`
              : session.name || '未命名会话'
            }
          </h3>
          
          {/* 进度条 */}
          <div className="mt-1.5 space-y-1">
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all ${
                  isSelected ? 'bg-blue-600' : 'bg-gray-400'
                }`}
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            
            {/* 任务数和时间 */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <Target className="w-3 h-3" />
                {session.progress.completed}/{session.progress.total} 个任务
              </span>
              
              {showTime && timeAgo && (
                <span className="flex items-center gap-1 text-gray-400">
                  <Clock className="w-3 h-3" />
                  {timeAgo}
                </span>
              )}
            </div>
          </div>
        </div>
        
        {/* 选中标记 */}
        {isSelected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
            className="flex-shrink-0"
          >
            <CheckCircle className="w-6 h-6 text-blue-500" />
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}


