import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Edit3, Eye, FileText, MessageSquare, Menu, Home } from 'lucide-react';
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as ToggleGroup from "@radix-ui/react-toggle-group";
import ChatPanel from './ChatPanel';
import ResumePreview from './ResumePreview';
import MarkdownPane from './MarkdownPane';
import TaskProgressPanel from './TaskProgressPanel';
import SessionDrawer from './SessionDrawer';
import { renderResumeHtmlFromSchema } from '../utils/renderResume';
import { resumeToMarkdown, markdownToResume } from '../utils/markdown';
import { exportResume } from "../utils/export";
import { Resume, Task, skipTask, nextTask, updateResume, guideInit } from '../api/workflow';
import { sessionManager, SessionMetadata } from '../utils/sessionManager';

interface WorkspaceLayoutProps {
  messages: any[];
  setMessages: React.Dispatch<React.SetStateAction<any[]>>;
  resumeData: Resume | null;
  setResumeData: (r: Resume | null) => void;
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  taskList: Task[];
  setTaskList: (tasks: Task[]) => void;
  currentTaskIdx: number;
  setCurrentTaskIdx: (idx: number) => void;
  userIntent: string;
  setUserIntent: (intent: string) => void;
  sessions: SessionMetadata[];
  setSessions: React.Dispatch<React.SetStateAction<SessionMetadata[]>>;
  onReturnToLanding: () => void;
}

export default function WorkspaceLayout({
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
  setUserIntent,
  sessions,
  setSessions,
  onReturnToLanding
}: WorkspaceLayoutProps) {
  const [editorMode, setEditorMode] = useState<"edit" | "preview">("preview");
  const [markdownText, setMarkdownText] = useState<string>("");
  const [resumeHtml, setResumeHtml] = useState<string>("");
  const [activeMobileTab, setActiveMobileTab] = useState<"chat" | "resume">("chat");
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isTaskActionLoading, setIsTaskActionLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const exportBtnRef = useRef<HTMLButtonElement | null>(null);

  // Sync resumeData changes to HTML and Markdown
  useEffect(() => {
    if (resumeData) {
      setResumeHtml(renderResumeHtmlFromSchema(resumeData));
      setMarkdownText(resumeToMarkdown(resumeData));
      // If data changes, switch to preview to see it (optional, but good UX)
      if (editorMode === 'edit') {
         // Maybe don't auto-switch if user is editing? 
         // But here resumeData updates usually come from AI.
         setEditorMode("preview");
      }
    }
  }, [resumeData]);

  const setEditorModeWithSync = async (m: "edit" | "preview") => {
    // 从编辑模式切换到预览模式时，保存修改
    if (m === "preview" && editorMode === "edit") {
      setIsSaving(true);
      try {
        // 解析markdown为Resume对象
        const newResume = markdownToResume(markdownText);
        
        // 如果有sessionId，更新后端数据
        if (sessionId) {
          await updateResume(sessionId, newResume);
        }
        
        // 更新前端状态
        setResumeData(newResume);
        setEditorMode("preview");
        
        // 显示成功提示
        setMessages(prev => [...prev, {
          role: "system",
          content: "✓ 简历已保存"
        }]);
      } catch (error: any) {
        // 显示错误提示
        const errorMsg = error?.message || "未知错误";
        alert(`无法保存简历：\n\n${errorMsg}\n\n请检查markdown格式是否正确。`);
        console.error("保存简历失败:", error);
        // 阻止切换，保持在编辑模式
        return;
      } finally {
        setIsSaving(false);
      }
    } 
    // 从预览模式切换到编辑模式
    else if (m === "edit" && resumeData) {
      setMarkdownText(resumeToMarkdown(resumeData));
      setEditorMode(m);
    } 
    // 其他情况直接切换
    else {
      setEditorMode(m);
    }
  };

  const handleSkipTask = async () => {
    if (!sessionId || isTaskActionLoading) return;
    
    setIsTaskActionLoading(true);
    
    // 1. 立即添加一个带 typing 标记的临时消息，让用户知道系统正在工作
    const tempMsgId = Date.now();
    setMessages(prev => [...prev, {
      role: "assistant",
      content: "好的，让我们看看下一项...",
      isTyping: true,
      tempId: tempMsgId
    }]);
    
    try {
      const result = await skipTask(sessionId);
      
      // 更新任务状态
      const updatedTasks = [...taskList];
      updatedTasks[currentTaskIdx].status = 'skipped';
      setTaskList(updatedTasks);
      
      // 移动到下一个任务
      if (result.next_task) {
        setCurrentTaskIdx(currentTaskIdx + 1);
        
        // 2. 更新临时消息文案，提示正在分析
        setMessages(prev => prev.map(m => 
          (m as any).tempId === tempMsgId 
            ? { ...m, content: "正在分析这部分内容..." }
            : m
        ));
        
        // 跳过成功后，自动调用 guideInit 获取自然的过渡话术
        try {
          const openingResponse = await guideInit(sessionId);
          // 3. 替换临时消息为真实回复
          setMessages(prev => prev.map(m => 
            (m as any).tempId === tempMsgId 
              ? { role: "assistant", content: openingResponse.reply }
              : m
          ));
        } catch (openingError) {
          console.error('获取开场白失败:', openingError);
          // 降级处理：替换临时消息为简单消息
          setMessages(prev => prev.map(m => 
            (m as any).tempId === tempMsgId 
              ? { role: "assistant", content: `已跳过当前任务。${result.message}` }
              : m
          ));
        }
      } else {
        // 没有下一个任务，替换临时消息
        setMessages(prev => prev.map(m => 
          (m as any).tempId === tempMsgId 
            ? { role: "assistant", content: result.message }
            : m
        ));
      }
    } catch (error) {
      console.error('跳过任务失败:', error);
      // 错误时替换临时消息
      setMessages(prev => prev.map(m => 
        (m as any).tempId === tempMsgId 
          ? { role: "assistant", content: `跳过失败: ${error instanceof Error ? error.message : '未知错误'}` }
          : m
      ));
    } finally {
      setIsTaskActionLoading(false);
      // 刷新会话列表以同步进度
      handleTaskComplete();
    }
  };

  const handleNextTask = async () => {
    if (!sessionId || isTaskActionLoading) return;
    
    setIsTaskActionLoading(true);
    try {
      const result = await nextTask(sessionId);
      
      if (result.has_next && result.task) {
        setCurrentTaskIdx(currentTaskIdx + 1);
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `进入下一个任务：${result.task?.section}\n\n${result.message}`
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: result.message
        }]);
      }
    } catch (error) {
      console.error('进入下一任务失败:', error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `操作失败: ${error instanceof Error ? error.message : '未知错误'}`
      }]);
    } finally {
      setIsTaskActionLoading(false);
      // 刷新会话列表以同步进度
      handleTaskComplete();
    }
  };

  // 自动保存消息到LocalStorage
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      const timer = setTimeout(() => {
        sessionManager.saveCurrentSession(sessionId, messages);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [messages, sessionId]);

  // 会话管理处理函数
  const handleSwitchSession = async (newSessionId: string) => {
    try {
      setIsDrawerOpen(false);
      
      const session = await sessionManager.switchSession(newSessionId);
      if (session) {
        setSessionId(session.id);
        setResumeData(session.resume);
        setMessages(session.messages);
        setUserIntent(session.user_intent);
        setTaskList(session.plan?.tasks || []);
        setCurrentTaskIdx(session.current_task_idx);
      }
    } catch (error) {
      console.error('切换会话失败:', error);
      alert('切换会话失败');
    }
  };

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    try {
      await sessionManager.deleteSession(sessionIdToDelete);
      
      // 刷新会话列表
      const sessionList = await sessionManager.getSessions();
      setSessions(sessionList);
      
      // 如果删除的是当前会话，返回首页
      if (sessionIdToDelete === sessionId) {
        onReturnToLanding();
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      alert('删除会话失败');
    }
  };

  const handleCreateSession = () => {
    setIsDrawerOpen(false);
    onReturnToLanding();
  };

  const handleRenameSession = async (sessionIdToRename: string, newName: string) => {
    try {
      await sessionManager.updateSessionName(sessionIdToRename, newName);
      
      // 刷新会话列表
      const sessionList = await sessionManager.getSessions();
      setSessions(sessionList);
    } catch (error) {
      console.error('重命名会话失败:', error);
      alert('重命名会话失败');
    }
  };

  // 任务完成后刷新会话列表
  const handleTaskComplete = async () => {
    try {
      const sessionList = await sessionManager.getSessions();
      setSessions(sessionList);
    } catch (error) {
      console.error('刷新会话列表失败:', error);
    }
  };

  return (
    <div className="h-[100dvh] flex flex-col md:flex-row overflow-hidden bg-gray-50">
      {/* Session Drawer */}
      <SessionDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sessions={sessions}
        currentSessionId={sessionId}
        onSwitch={handleSwitchSession}
        onDelete={handleDeleteSession}
        onCreate={handleCreateSession}
        onRename={handleRenameSession}
      />

      {/* Mobile Tab Navigation */}
      <div className="md:hidden bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between shrink-0 z-20">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="p-2 -ml-2 hover:bg-gray-100 rounded-lg"
          title="会话列表"
        >
          <Menu className="w-5 h-5 text-gray-700" />
        </button>
        <div className="flex gap-2 flex-1 justify-center">
           <button
             onClick={() => setActiveMobileTab("chat")}
             className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
               activeMobileTab === "chat" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"
             }`}
           >
             <MessageSquare className="w-4 h-4 inline mr-1" /> 对话
           </button>
           <button
             onClick={() => setActiveMobileTab("resume")}
             className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
               activeMobileTab === "resume" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"
             }`}
           >
             <FileText className="w-4 h-4 inline mr-1" /> 简历
           </button>
        </div>
        <button
          onClick={onReturnToLanding}
          className="p-2 -mr-2 hover:bg-gray-100 rounded-lg"
          title="返回首页"
        >
          <Home className="w-5 h-5 text-gray-700" />
        </button>
        {activeMobileTab === "resume" && (
           <div className="flex items-center gap-2">
             {isSaving && (
               <span className="text-xs text-blue-600">保存中...</span>
             )}
             <button 
                onClick={() => setEditorModeWithSync(editorMode === 'edit' ? 'preview' : 'edit')}
                disabled={isSaving}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
             >
               {editorMode === 'edit' ? <Eye className="w-4 h-4" /> : <Edit3 className="w-4 h-4" />}
             </button>
           </div>
        )}
      </div>

      {/* Left Column: Chat */}
      <div className={`flex-1 md:w-[45%] md:max-w-2xl flex flex-col h-full bg-white border-r border-gray-200 relative z-10 ${
        activeMobileTab === "chat" ? "block" : "hidden md:flex"
      }`}>
        {/* Task Progress Panel or Simple Navigation */}
        {taskList.length > 0 ? (
          <TaskProgressPanel
            tasks={taskList}
            currentTaskIdx={currentTaskIdx}
            onSkip={handleSkipTask}
            onNext={handleNextTask}
            isLoading={isTaskActionLoading}
            onMenuClick={() => setIsDrawerOpen(true)}
            onHomeClick={onReturnToLanding}
          />
        ) : (
          <div className="hidden md:flex bg-white border-b border-gray-200 px-4 py-3 gap-1">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="会话列表"
            >
              <Menu className="w-5 h-5 text-gray-700" />
            </button>
            <button
              onClick={onReturnToLanding}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="返回首页"
            >
              <Home className="w-5 h-5 text-gray-700" />
            </button>
          </div>
        )}
        
        {/* Chat Panel */}
        <div className="flex-1 overflow-hidden">
          <ChatPanel 
            messages={messages} 
            setMessages={setMessages} 
            resumeData={resumeData} 
            setResumeData={setResumeData}
            sessionId={sessionId}
            setSessionId={setSessionId}
            taskList={taskList}
            setTaskList={setTaskList}
            currentTaskIdx={currentTaskIdx}
            setCurrentTaskIdx={setCurrentTaskIdx}
            userIntent={userIntent}
            onSkip={handleSkipTask}
            onTaskComplete={handleTaskComplete}
          />
        </div>
      </div>

      {/* Right Column: Resume Workspace */}
      <div className={`flex-1 flex flex-col h-full bg-gray-100 relative ${
        activeMobileTab === "resume" ? "block" : "hidden md:flex"
      }`}>
        {/* Toolbar */}
        <div className="absolute top-4 right-4 z-30 flex items-center gap-2 bg-white/80 backdrop-blur-sm p-1.5 rounded-lg border border-gray-200 shadow-sm transition-opacity hover:opacity-100">
           {/* Saving indicator */}
           {isSaving && (
             <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-blue-600">
               <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
               <span>保存中...</span>
             </div>
           )}
           
           <ToggleGroup.Root
            type="single"
            value={editorMode}
            onValueChange={(val) => { if (val && !isSaving) setEditorModeWithSync(val as "edit" | "preview"); }}
            className="flex bg-gray-100 rounded-md p-0.5"
          >
            <ToggleGroup.Item 
              value="edit" 
              className="px-2 py-1 rounded text-xs font-medium text-gray-600 data-[state=on]:bg-white data-[state=on]:text-blue-600 data-[state=on]:shadow-sm transition-all disabled:opacity-50"
              disabled={isSaving}
            >
              <Edit3 className="w-3 h-3 mr-1 inline" /> 编辑
            </ToggleGroup.Item>
            <ToggleGroup.Item 
              value="preview" 
              className="px-2 py-1 rounded text-xs font-medium text-gray-600 data-[state=on]:bg-white data-[state=on]:text-blue-600 data-[state=on]:shadow-sm transition-all disabled:opacity-50"
              disabled={isSaving}
            >
              <Eye className="w-3 h-3 mr-1 inline" /> 预览
            </ToggleGroup.Item>
          </ToggleGroup.Root>

          <div className="w-px h-4 bg-gray-300 mx-1" />

          <DropdownMenu.Root open={isExportOpen} onOpenChange={setIsExportOpen}>
            <DropdownMenu.Trigger asChild>
              <button
                ref={exportBtnRef}
                className="p-1.5 rounded-md text-gray-600 hover:bg-gray-100 hover:text-blue-600 focus:outline-none transition-colors"
                title="导出"
              >
                <Download className="w-4 h-4" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content className="min-w-[120px] bg-white border border-gray-200 rounded-lg shadow-xl p-1 z-50 animate-in fade-in zoom-in-95 duration-200" align="end" sideOffset={5}>
                <DropdownMenu.Item 
                  className="flex items-center w-full px-2 py-1.5 text-sm text-gray-700 rounded hover:bg-blue-50 hover:text-blue-700 cursor-pointer outline-none"
                  onClick={() => { exportResume("pdf", { iframe: iframeRef.current, html: resumeHtml }); setIsExportOpen(false); }}
                >
                  <FileText className="w-4 h-4 mr-2" /> PDF
                </DropdownMenu.Item>
                <DropdownMenu.Item 
                  className="flex items-center w-full px-2 py-1.5 text-sm text-gray-700 rounded hover:bg-blue-50 hover:text-blue-700 cursor-pointer outline-none"
                  onClick={() => { exportResume("html", { iframe: iframeRef.current, html: resumeHtml }); setIsExportOpen(false); }}
                >
                  <FileText className="w-4 h-4 mr-2" /> HTML
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4 md:p-8">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
            className="h-full"
          >
            {editorMode === 'edit' ? (
              <MarkdownPane markdownText={markdownText} setMarkdownText={setMarkdownText} />
            ) : (
              <ResumePreview ref={iframeRef} html={resumeHtml} />
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
