import React from 'react';
import { User, Clock } from 'lucide-react';
import { motion } from 'framer-motion';
import { Resume } from '../api/workflow';

interface ResumeCardProps {
  resume: Resume;
  isSelected: boolean;
  onClick: () => void;
  showTime?: boolean;
  timeAgo?: string;
}

export function ResumeCard({ 
  resume, 
  isSelected, 
  onClick, 
  showTime = false, 
  timeAgo 
}: ResumeCardProps) {
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
        {/* 头像图标 */}
        <div className={`
          w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
          ${isSelected ? 'bg-blue-500' : 'bg-gray-200'}
        `}>
          <User className={`w-6 h-6 ${isSelected ? 'text-white' : 'text-gray-500'}`} />
        </div>
        
        {/* 简历信息 */}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-gray-900 truncate">
            {resume.basics.name || '未命名'}
          </h3>
          {resume.basics.label && (
            <p className="text-sm text-gray-500 truncate">
              {resume.basics.label}
            </p>
          )}
          
          {/* 时间标签 */}
          {showTime && timeAgo && (
            <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
              <Clock className="w-3 h-3" />
              {timeAgo}
            </div>
          )}
        </div>
        
      </div>
    </motion.div>
  );
}

