import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, 
  ChevronUp, 
  CheckCircle2, 
  Circle, 
  PlayCircle, 
  SkipForward,
  Loader2,
  Menu,
  Home
} from 'lucide-react';
import { Task } from '../api/workflow';

interface TaskProgressPanelProps {
  tasks: Task[];
  currentTaskIdx: number;
  onSkip?: () => void;
  onNext?: () => void;
  isLoading?: boolean;
  collapsed?: boolean;
  onMenuClick?: () => void;
  onHomeClick?: () => void;
}

export default function TaskProgressPanel({
  tasks,
  currentTaskIdx,
  onSkip,
  onNext,
  isLoading = false,
  collapsed: initialCollapsed = false,
  onMenuClick,
  onHomeClick
}: TaskProgressPanelProps) {
  const [collapsed, setCollapsed] = useState(initialCollapsed);

  if (tasks.length === 0) {
    return null;
  }

  const completedCount = tasks.filter(t => t.status === 'completed').length;
  const skippedCount = tasks.filter(t => t.status === 'skipped').length;
  const totalCount = tasks.length;
  const progress = ((completedCount + skippedCount) / totalCount) * 100;

  const getTaskIcon = (task: Task, idx: number) => {
    if (task.status === 'completed') {
      return <CheckCircle2 className="w-4 h-4 text-green-600" />;
    } else if (task.status === 'skipped') {
      return <SkipForward className="w-4 h-4 text-gray-400" />;
    } else if (idx === currentTaskIdx) {
      return <PlayCircle className="w-4 h-4 text-blue-600 animate-pulse" />;
    } else {
      return <Circle className="w-4 h-4 text-gray-300" />;
    }
  };

  const getTaskStatusColor = (task: Task, idx: number) => {
    if (task.status === 'completed') {
      return 'bg-green-50 border-green-200 text-green-800';
    } else if (task.status === 'skipped') {
      return 'bg-gray-50 border-gray-200 text-gray-500';
    } else if (idx === currentTaskIdx) {
      return 'bg-blue-50 border-blue-300 text-blue-900';
    } else {
      return 'bg-white border-gray-200 text-gray-600';
    }
  };

  const currentTask = tasks[currentTaskIdx];
  const canSkip = currentTask && currentTask.status !== 'completed' && currentTask.status !== 'skipped';
  const canNext = currentTask && currentTask.status === 'completed' && currentTaskIdx < tasks.length - 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border-b border-gray-200 shadow-sm"
    >
      {/* Header - Always Visible */}
      <div 
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-4 flex-1">
          {/* Navigation Icons */}
          <div className="hidden md:flex gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMenuClick?.();
              }}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="会话列表"
            >
              <Menu className="w-5 h-5 text-gray-700" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onHomeClick?.();
              }}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="返回首页"
            >
              <Home className="w-5 h-5 text-gray-700" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-700">任务进度</span>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              {completedCount + skippedCount}/{totalCount}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="flex-1 max-w-xs">
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
              />
            </div>
          </div>

          {/* Current Task Preview */}
          {!collapsed && currentTask && (
            <div className="hidden md:block text-xs text-gray-500 truncate max-w-md">
              当前: {currentTask.section}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {!collapsed && (
            <>
              {canSkip && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSkip?.();
                  }}
                  disabled={isLoading}
                  className="px-3 py-1 text-xs font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  跳过
                </button>
              )}
              {canNext && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onNext?.();
                  }}
                  disabled={isLoading}
                  className="px-3 py-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一个
                </button>
              )}
            </>
          )}

          {isLoading && (
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          )}

          {collapsed ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Task List - Collapsible */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3 space-y-2">
              {tasks.map((task, idx) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${getTaskStatusColor(task, idx)}`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getTaskIcon(task, idx)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold">任务 {task.id}</span>
                      <span className="text-xs text-gray-500">·</span>
                      <span className="text-xs font-medium truncate">{task.section}</span>
                    </div>
                    
                    {idx === currentTaskIdx && (
                      <div className="mt-1 space-y-1">
                        <p className="text-xs text-gray-600 line-clamp-2">
                          <span className="font-medium">目标:</span> {task.goal}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Status Badge */}
                  {task.status === 'completed' && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                      已完成
                    </span>
                  )}
                  {task.status === 'skipped' && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                      已跳过
                    </span>
                  )}
                  {idx === currentTaskIdx && task.status !== 'completed' && task.status !== 'skipped' && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium animate-pulse">
                      进行中
                    </span>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

