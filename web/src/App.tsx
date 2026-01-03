import React, { useState, useMemo, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import LandingPage from "./components/LandingPage";
import WorkspaceLayout from "./components/WorkspaceLayout";
import { renderResumeHtmlFromSchema } from "./utils/renderResume";
import { Resume, Task } from "./api/workflow";
import { sessionManager, SessionMetadata } from "./utils/sessionManager";

type Msg = { role: "assistant" | "user" | "system"; content: string };

export default function App() {
  const [phase, setPhase] = useState<"landing" | "workspace">("landing");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [resumeData, setResumeData] = useState<Resume | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [taskList, setTaskList] = useState<Task[]>([]);
  const [currentTaskIdx, setCurrentTaskIdx] = useState(0);
  const [userIntent, setUserIntent] = useState<string>("");
  const [sessions, setSessions] = useState<SessionMetadata[]>([]);
  const [isLoadingSession, setIsLoadingSession] = useState(true);

  // 页面加载时尝试恢复最近会话
  useEffect(() => {
    const restoreSession = async () => {
      try {
        // 获取会话列表（已按 updated_at 倒序排列）
        const sessionList = await sessionManager.getSessions();
        setSessions(sessionList);

        // 优先恢复最近更新的会话（列表第一个）
        if (sessionList.length > 0) {
          const recentSession = await sessionManager.getSession(sessionList[0].id);
          if (recentSession) {
            // 恢复会话数据
            setResumeData(recentSession.resume);
            setMessages(recentSession.messages);
            setSessionId(recentSession.id);
            setUserIntent(recentSession.user_intent);
            setTaskList(recentSession.plan?.tasks || []);
            setCurrentTaskIdx(recentSession.current_task_idx);
            
            // 设置为当前会话
            sessionManager.setCurrentSessionId(recentSession.id);
            
            // 自动进入工作区
            setPhase("workspace");
          }
        }
      } catch (error) {
        console.error('恢复会话失败:', error);
      } finally {
        setIsLoadingSession(false);
      }
    };

    restoreSession();
  }, []);

  const handleStart = async (resume: Resume | null, jd: string, file: File | null) => {
    try {
      // 检查是否是恢复会话的特殊标记
      if (jd.startsWith('__RESTORE_SESSION__:')) {
        const sessionIdToRestore = jd.replace('__RESTORE_SESSION__:', '');
        
        // 加载指定会话
        const session = await sessionManager.getSession(sessionIdToRestore);
        if (session) {
          // 恢复会话数据
          setResumeData(session.resume);
          setMessages(session.messages);
          setSessionId(session.id);
          setUserIntent(session.user_intent);
          setTaskList(session.plan?.tasks || []);
          setCurrentTaskIdx(session.current_task_idx);
          
          // 设置为当前会话
          sessionManager.setCurrentSessionId(session.id);
          
          // 进入工作区
          setPhase("workspace");
          
          // 刷新会话列表
          const sessionList = await sessionManager.getSessions();
          setSessions(sessionList);
        } else {
          alert('会话加载失败，请重试');
        }
        return;
      }

      // 正常创建新会话流程
      if (!resume) {
        console.error('No resume provided');
        return;
      }

      // 清除旧会话状态，确保创建新会话
      setSessionId(null);
      setTaskList([]);
      setCurrentTaskIdx(0);

      // 设置新会话的初始状态
      setResumeData(resume);
      setUserIntent(jd);
      
      // 添加欢迎消息
      setMessages([
        {
          role: "assistant",
          content: "你好！我是你的简历助手。我已经收到你的简历和职位要求，正在为你生成优化计划..."
        }
      ]);

      // 进入工作区（让ChatPanel的useEffect来处理会话创建）
      setPhase("workspace");
      
      // 刷新会话列表
      const sessionList = await sessionManager.getSessions();
      setSessions(sessionList);
    } catch (error) {
      console.error('初始化失败:', error);
      alert('初始化失败，请重试');
    }
  };

  // 加载中显示
  if (isLoadingSession) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="font-sans text-gray-900 bg-gray-50 min-h-screen">
       <AnimatePresence mode="wait">
         {phase === "landing" ? (
           <motion.div
             key="landing"
             exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }}
             transition={{ duration: 0.5 }}
             className="absolute inset-0"
           >
             <LandingPage onStart={handleStart} />
           </motion.div>
         ) : (
           <motion.div
             key="workspace"
             initial={{ opacity: 0 }}
             animate={{ opacity: 1 }}
             transition={{ duration: 0.5 }}
             className="absolute inset-0"
           >
            <WorkspaceLayout 
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
              setUserIntent={setUserIntent}
              sessions={sessions}
              setSessions={setSessions}
              onReturnToLanding={() => setPhase("landing")}
            />
           </motion.div>
         )}
       </AnimatePresence>
    </div>
  );
}
