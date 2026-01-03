import React, { useMemo, useRef, useState, useEffect } from "react";
import * as ScrollArea from "@radix-ui/react-scroll-area";
import { Send, User, Bot, Loader2, CheckCircle, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import { 
  Resume, 
  Task, 
  guideStep,
  guideInit,
  confirmAndExecute,
  createSession,
  generatePlan,
  generatePlanWithProgress,
  PlanProgressEvent
} from "../api/workflow";
import MarkdownRenderer from "./MarkdownRenderer";
import TypingIndicator from "./TypingIndicator";

type Msg = { 
  role: "assistant" | "user"; 
  content: string;
  draft?: string;
  isConfirming?: boolean;
  isTyping?: boolean;  // 是否正在输入中（显示打字动画）
  tempId?: number;     // 临时消息ID，用于后续替换
};

export default function ChatPanel(props: {
  messages: Msg[];
  setMessages: React.Dispatch<React.SetStateAction<Msg[]>>;
  resumeData: Resume | null;
  setResumeData: (r: Resume | null) => void;
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  taskList: Task[];
  setTaskList: (tasks: Task[]) => void;
  currentTaskIdx: number;
  setCurrentTaskIdx: (idx: number) => void;
  userIntent: string;
  onSkip?: () => void;
  onTaskComplete?: () => void;
}) {
  const { 
    messages, 
    setMessages, 
    resumeData, 
    setResumeData,
    sessionId,
    setSessionId,
    taskList,
    setTaskList,
    currentTaskIdx,
    setCurrentTaskIdx,
    userIntent,
    onSkip,
    onTaskComplete
  } = props;

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  const hasInitializedRef = useRef(false);
  const controllerRef = useRef<AbortController | null>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, executionLogs]);

  // 自动调整 textarea 高度
  const adjustTextareaHeight = () => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  // 处理键盘事件：Enter 发送，Shift+Enter 换行
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading && !isExecuting && !needsConfirmation && sessionId) {
        onSubmit(e as unknown as React.FormEvent);
      }
    }
  };

  // 检查最后一条消息是否需要确认（提前定义，供 handleKeyDown 使用）
  const lastMessage = messages[messages.length - 1];
  const needsConfirmation = lastMessage?.role === "assistant" && lastMessage?.isConfirming;

  // 初始化工作流
  useEffect(() => {
    // 当 sessionId 被清除时，重置初始化标记
    if (sessionId === null) {
      hasInitializedRef.current = false;
    }
    
    if (resumeData && userIntent && !hasInitializedRef.current && !sessionId) {
      hasInitializedRef.current = true;
      initializeWorkflow();
    }
  }, [resumeData, userIntent, sessionId]);

  const initializeWorkflow = async () => {
    if (!resumeData || !userIntent) return;

    setIsLoading(true);
    try {
      // 1. 创建会话
      const sid = await createSession(resumeData);
      setSessionId(sid);

      setMessages(prev => [...prev, {
        role: "assistant",
        content: "会话已创建，正在分析简历和职位要求，生成优化计划..."
      }]);

      // 2. 生成计划（使用流式API带进度）
      const progressMessageIndex = messages.length; // 记录进度消息的索引
      
      // 添加初始进度消息
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⏳ 正在准备分析...\n\n[░░░░░░░░░░░░░░░░░░░░] 0%"
      }]);

      const planResponse = await generatePlanWithProgress(
        sid, 
        userIntent,
        (event: PlanProgressEvent) => {
          // 进度回调：更新进度消息
          if (event.stage === "analyzing") {
            const progressBar = "█".repeat(Math.floor(event.progress / 5)) + 
                               "░".repeat(20 - Math.floor(event.progress / 5));
            const progressText = `⏳ ${event.message}\n\n[${progressBar}] ${event.progress}%`;
            
            setMessages(prev => {
              const newMessages = [...prev];
              // 更新进度消息（progressMessageIndex + 1，因为前面有"会话已创建"消息）
              if (newMessages[progressMessageIndex + 1]) {
                newMessages[progressMessageIndex + 1] = {
                  role: "assistant",
                  content: progressText
                };
              }
              return newMessages;
            });
          }
        }
      );
      
      setTaskList(planResponse.tasks);
      setCurrentTaskIdx(0);

      // 移除进度消息，添加计划完成消息
      setMessages(prev => {
        const filtered = prev.filter((_, idx) => idx !== progressMessageIndex + 1);
        return [...filtered, {
          role: "assistant",
          content: `✅ 优化计划已生成！共有 ${planResponse.tasks.length} 个任务需要处理。`
        }];
      });

      // 调用 Guide Agent 自动开场白接口，生成结构化的引导消息
      try {
        const openingResponse = await guideInit(sid);
        setMessages(prev => [...prev, {
          role: "assistant",
          content: openingResponse.reply
        }]);
      } catch (openingError) {
        console.error('生成开场白失败:', openingError);
        // 降级到简单的开场消息
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `现在开始第一个任务：${planResponse.tasks[0].section}\n\n${planResponse.tasks[0].diagnosis}\n\n请告诉我更多相关信息。`
        }]);
      }

    } catch (error) {
      console.error('初始化工作流失败:', error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `❌ 初始化失败: ${error instanceof Error ? error.message : '未知错误'}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !sessionId) return;

    const userInput = input.trim();
    setInput("");

    // 添加用户消息
    setMessages(prev => [...prev, {
      role: "user",
      content: userInput
    }]);

    setIsLoading(true);

    try {
      // 调用 Guide Agent
      const response = await guideStep(sessionId, userInput);

      // 构建助手消息
      const assistantMsg: Msg = {
        role: "assistant",
        content: response.reply,
        draft: response.draft,
        isConfirming: response.is_confirming
      };

      setMessages(prev => [...prev, assistantMsg]);

      // 如果进入确认状态，不需要额外操作，用户可以点击确认按钮

    } catch (error) {
      console.error('Guide交互失败:', error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `处理失败: ${error instanceof Error ? error.message : '未知错误'}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!sessionId || isExecuting) return;

    // 检查最后一条消息是否处于确认状态
    const lastMsg = messages[messages.length - 1];
    if (!lastMsg?.isConfirming) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ 当前没有待确认的内容，请先完成对话。"
      }]);
      return;
    }

    setIsExecuting(true);
    setExecutionLogs([]);

    // 添加执行开始消息
    setMessages(prev => [...prev, {
      role: "assistant",
      content: "正在执行修改..."
    }]);

    if (controllerRef.current) controllerRef.current.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    let shouldLoadNextTask = false;

    try {
      await confirmAndExecute(
        sessionId,
        (event) => {
          const { type, content, role } = event;

          if (type === "think" || type === "tool") {
            setExecutionLogs(prev => [...prev, content]);
          } else if (type === "complete") {
            // 执行完成
            if (content?.resume) {
              setResumeData(content.resume);
            }
            
            // 更新任务状态为已完成（使用函数式更新避免闭包陈旧值问题）
            setTaskList(prevTasks => {
              const updatedTasks = prevTasks.map((task, idx) => 
                idx === currentTaskIdx 
                  ? { ...task, status: 'completed' as const }
                  : task
              );
              return updatedTasks;
            });
            
            setMessages(prev => [...prev, {
              role: "assistant",
              content: content?.message || "修改已完成！"
            }]);

            // 检查是否还有下一个任务
            if (currentTaskIdx < taskList.length - 1) {
              shouldLoadNextTask = true;
              const nextIdx = currentTaskIdx + 1;
              setCurrentTaskIdx(nextIdx);
            } else {
              setMessages(prev => [...prev, {
                role: "assistant",
                content: "🎉 所有任务已完成！你的简历已经优化完毕，可以导出查看了。"
              }]);
            }
          } else if (type === "error") {
            setMessages(prev => [...prev, {
              role: "assistant",
              content: `执行出错: ${content}`
            }]);
          } else if (type === "data") {
            // 更新简历数据
            if (content) {
              setResumeData(content);
            }
          }
        },
        controller.signal
      );

      // 执行完成后，如果需要加载下一个任务，调用 guideInit
      if (shouldLoadNextTask && sessionId) {
        try {
          const openingResponse = await guideInit(sessionId);
          setMessages(prev => [...prev, {
            role: "assistant",
            content: openingResponse.reply
          }]);
        } catch (openingError) {
          console.error('生成开场白失败:', openingError);
          // 降级到简单的开场消息
          const nextTask = taskList[currentTaskIdx];
          setMessages(prev => [...prev, {
            role: "assistant",
            content: `太好了！现在开始下一个任务：${nextTask.section}\n\n${nextTask.diagnosis}\n\n请提供相关信息。`
          }]);
        }
      }
      
      // 任务完成后刷新会话列表
      onTaskComplete?.();
    } catch (error) {
      if (String(error).includes('aborted')) return;
      console.error('执行失败:', error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `执行失败: ${error instanceof Error ? error.message : '未知错误'}`
      }]);
    } finally {
      setIsExecuting(false);
      setExecutionLogs([]);
    }
  };


  return (
    <div className="flex flex-col h-full bg-white relative">
      <ScrollArea.Root className="flex-1 w-full overflow-hidden">
        <ScrollArea.Viewport 
          ref={scrollAreaRef}
          className="w-full h-full p-4 pb-40"
        >
          <div className="space-y-6">
            {messages.map((m, idx) => (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={idx} 
                className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  m.role === "user" 
                    ? "bg-blue-600 text-white shadow-md" 
                    : "bg-emerald-600 text-white shadow-md"
                }`}>
                  {m.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>
                
                <div className={`flex-1 max-w-[80%] rounded-2xl p-4 shadow-sm ${
                  m.role === "user"
                    ? "bg-blue-50 text-gray-800 rounded-tr-none"
                    : "bg-white border border-gray-100 text-gray-800 rounded-tl-none"
                }`}>
                  {m.role === "assistant" ? (
                    m.isTyping ? (
                      // 显示带打字动画的临时消息
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-600">{m.content}</span>
                        <TypingIndicator />
                      </div>
                    ) : (
                      <MarkdownRenderer content={m.content} className="text-sm" />
                    )
                  ) : (
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {m.content}
                    </div>
                  )}

                  {/* 草稿预览 */}
                  {m.draft && (
                    <div className="mt-4 overflow-hidden rounded-xl shadow-lg border border-blue-100">
                      {/* 标题栏 */}
                      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-200 px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">📝</span>
                          <span className="text-sm font-semibold text-blue-900">优化草稿预览</span>
                        </div>
                      </div>
                      {/* 内容区 */}
                      <div className="bg-white p-5">
                        <MarkdownRenderer content={m.draft} className="draft-content" />
                      </div>
                    </div>
                  )}

                  {/* 确认按钮 - 只要有草稿就显示，无需等待 isConfirming */}
                  {m.draft && idx === messages.length - 1 && !isExecuting && (
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={handleConfirm}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        确认执行
                      </button>
                      <button
                        onClick={onSkip}
                        className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                        disabled={!onSkip}
                      >
                        <XCircle className="w-4 h-4" />
                        跳过
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}

            {/* 执行日志 */}
            {isExecuting && executionLogs.length > 0 && (
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-500 text-white flex items-center justify-center shadow-md">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
                <div className="flex-1 max-w-[80%] rounded-2xl p-4 bg-amber-50 border border-amber-100 rounded-tl-none shadow-sm">
                  <div className="text-xs font-semibold text-amber-800 mb-2 uppercase tracking-wide">执行中</div>
                  <div className="text-xs text-amber-900 space-y-1 font-mono">
                    {executionLogs.map((log, i) => (
                      <div key={i}>{log}</div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 加载状态 */}
            {isLoading && !isExecuting && (
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center shadow-md">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
                <div className="flex-1 max-w-[80%] rounded-2xl p-4 bg-blue-50 border border-blue-100 rounded-tl-none shadow-sm">
                  <div className="text-sm text-blue-900">正在处理...</div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea.Viewport>
        <ScrollArea.Scrollbar 
          className="flex select-none touch-none p-0.5 bg-transparent transition-colors w-2" 
          orientation="vertical"
        >
          <ScrollArea.Thumb className="flex-1 bg-gray-300 rounded-full hover:bg-gray-400" />
        </ScrollArea.Scrollbar>
      </ScrollArea.Root>
      
      {/* Input Area - Fixed at bottom with Gemini-style */}
      <div className="absolute bottom-6 left-0 right-0 px-6 bg-gradient-to-t from-white via-white to-transparent pt-8">
        <motion.form 
          onSubmit={onSubmit}
          layoutId="chat-input-area"
          className="max-w-3xl mx-auto bg-white border border-gray-200 rounded-2xl shadow-xl flex items-end gap-2 p-3 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-300 transition-all"
        >
          <textarea
            ref={inputRef}
            placeholder={needsConfirmation ? "等待确认..." : "输入你的回答或要求..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            className="flex-1 border-none focus:ring-0 focus:outline-none text-base px-4 py-3 bg-transparent resize-none min-h-[48px] max-h-[200px] overflow-y-auto leading-relaxed"
            disabled={isLoading || isExecuting || needsConfirmation}
          />
          <button 
            type="submit"
            className={`p-3 rounded-xl transition-all flex-shrink-0 ${
              input.trim() && !isLoading && !isExecuting && !needsConfirmation
                ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg" 
                : "bg-gray-100 text-gray-400 cursor-not-allowed"
            }`}
            disabled={isLoading || isExecuting || !input.trim() || needsConfirmation}
          >
            {isLoading || isExecuting ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </motion.form>
        <p className="text-center text-xs text-gray-400 mt-3 max-w-3xl mx-auto">按 Enter 发送，Shift + Enter 换行</p>
      </div>
    </div>
  );
}
