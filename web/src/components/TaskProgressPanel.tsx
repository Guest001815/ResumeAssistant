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
  collapsed: initialCollapsed = true, // 默认折叠状态
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

  // 其他任务（排除当前任务）
  const otherTasks = tasks.filter((_, idx) => idx !== currentTaskIdx);

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border-b border-gray-200 shadow-sm"
    >
      {/* Header - 进度条区域 */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          {/* Navigation Icons */}
          <div className="hidden md:flex gap-1">
            <button
              onClick={() => onMenuClick?.()}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="会话列表"
            >
              <Menu className="w-5 h-5 text-gray-700" />
            </button>
            <button
              onClick={() => onHomeClick?.()}
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
        </div>

        {isLoading && (
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
        )}
      </div>

      {/* 当前任务卡片 - 始终显示 */}
      {currentTask && (
        <div className="px-4 pb-3">
          <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all ${getTaskStatusColor(currentTask, currentTaskIdx)}`}>
            <div className="flex-shrink-0">
              {getTaskIcon(currentTask, currentTaskIdx)}
            </div>

            <div className="flex-1 min-w-0 flex items-center gap-2">
              <span className="text-sm font-semibold whitespace-nowrap">任务 {currentTask.id}</span>
              <span className="text-xs text-gray-500 flex-shrink-0">·</span>
              <span className="text-sm font-medium truncate">{currentTask.section}</span>
            </div>

            {/* 状态标签和操作按钮 */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {canSkip && (
                <button
                  onClick={() => onSkip?.()}
                  disabled={isLoading}
                  className="px-3 py-1 text-xs font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  跳过
                </button>
              )}
              {canNext && (
                <button
                  onClick={() => onNext?.()}
                  disabled={isLoading}
                  className="px-3 py-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一个
                </button>
              )}
              
              {/* Status Badge */}
              {currentTask.status === 'completed' && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                  已完成
                </span>
              )}
              {currentTask.status === 'skipped' && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                  已跳过
                </span>
              )}
              {currentTask.status !== 'completed' && currentTask.status !== 'skipped' && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium animate-pulse">
                  进行中
                </span>
              )}

              {/* 展开/折叠按钮 - 只有这个按钮可以触发展开/折叠 */}
              {otherTasks.length > 0 && (
                <button
                  onClick={() => setCollapsed(!collapsed)}
                  className="p-1.5 hover:bg-white/50 rounded-md transition-colors"
                  title={collapsed ? "展开全部任务" : "收起任务列表"}
                >
                  {collapsed ? (
                    <ChevronDown className="w-5 h-5 text-gray-500 hover:text-gray-700" />
                  ) : (
                    <ChevronUp className="w-5 h-5 text-gray-500 hover:text-gray-700" />
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 其他任务列表 - 可折叠 */}
      <AnimatePresence>
        {!collapsed && otherTasks.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3 space-y-1.5">
              {tasks.map((task, idx) => {
                // 跳过当前任务，因为已经在上面显示了
                if (idx === currentTaskIdx) return null;
                
                return (
                  <motion.div
                    key={task.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-all ${getTaskStatusColor(task, idx)}`}
                  >
                    <div className="flex-shrink-0">
                      {getTaskIcon(task, idx)}
                    </div>

                    <div className="flex-1 min-w-0 flex items-center gap-2">
                      <span className="text-xs font-semibold">任务 {task.id}</span>
                      <span className="text-xs text-gray-500">·</span>
                      <span className="text-xs font-medium truncate">{task.section}</span>
                    </div>

                    {/* Status Badge */}
                    {task.status === 'completed' && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
                        已完成
                      </span>
                    )}
                    {task.status === 'skipped' && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
                        已跳过
                      </span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
