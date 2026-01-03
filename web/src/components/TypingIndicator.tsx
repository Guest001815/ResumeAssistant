import React from 'react';
import { Loader2 } from 'lucide-react';

interface TypingIndicatorProps {
  className?: string;
}

/**
 * 打字指示器组件 - 旋转图标
 * 用于显示"助手正在输入"的状态
 * 与界面中其他加载状态保持一致的视觉风格
 */
export default function TypingIndicator({ className = '' }: TypingIndicatorProps) {
  return (
    <Loader2 className={`w-4 h-4 text-emerald-600 animate-spin ${className}`} />
  );
}

