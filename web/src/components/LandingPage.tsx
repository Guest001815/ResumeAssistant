import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, ArrowRight, X, AlertCircle, Sparkles, FileSearch, Bot, CheckCircle, Target, Edit3 } from 'lucide-react';
import { parseResumeWithProgress, ParseProgressEvent, Resume } from '../api/workflow';
import { sessionManager, SessionMetadata } from '../utils/sessionManager';
import { ResumeSelector } from './ResumeSelector';
import { SessionSelector } from './SessionSelector';

interface LandingPageProps {
  onStart: (resume: Resume | null, jd: string, file: File | null) => void;
}

// 趣味提示语（简历优化小贴士）
const TIPS = [
  '用数字量化成就更有说服力，比如"提升转化率30%"',
  "针对目标职位调整关键词，提高匹配度",
  "把最亮眼的成就放在每段经历的第一条",
  '避免使用"负责"等模糊动词，改用"主导""设计""优化"',
  "保持简历在1-2页，突出重点内容",
  "用 STAR 法则描述项目：情境、任务、行动、结果",
  "技能部分要与职位要求高度匹配",
  "经历描述聚焦于成果，而非日常职责",
];

// 解析阶段配置
const STAGES = {
  reading: { label: '读取文件', progress: 10 },
  converting: { label: '转换图片', progress: 40 },
  analyzing: { label: 'AI 分析', progress: 90 },
  complete: { label: '解析完成', progress: 100 },
};

type ParseStage = keyof typeof STAGES;

export default function LandingPage({ onStart }: LandingPageProps) {
  const [jd, setJd] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isParsingPDF, setIsParsingPDF] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<'history' | 'pdf'>('pdf');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 历史简历相关状态
  const [hasHistoryResume, setHasHistoryResume] = useState(false);
  const [historyResumes, setHistoryResumes] = useState<Array<{
    id: string;
    resume: Resume;
    name: string;
    label: string;
    created_at: string;
    updated_at: string;
  }>>([]);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  
  // 历史会话相关状态
  const [hasHistorySessions, setHasHistorySessions] = useState(false);
  const [historySessions, setHistorySessions] = useState<SessionMetadata[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionMetadata | null>(null);
  
  // 进度状态
  const [parseStage, setParseStage] = useState<ParseStage>('reading');
  const [parseProgress, setParseProgress] = useState(0);
  
  // 趣味提示
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 加载历史数据
  useEffect(() => {
    const loadHistoryData = async () => {
      try {
        // 并行加载会话和简历（始终加载两者）
        const [sessions, resumes] = await Promise.all([
          sessionManager.getSessions(),
          sessionManager.getStoredResumes() // 使用新的独立存储 API
        ]);
        
        // 设置历史会话
        if (sessions.length > 0) {
          setHistorySessions(sessions);
          setSelectedSession(sessions[0]);
          setHasHistorySessions(true);
        }
        
        // 始终设置历史简历（无论是否有会话）
        if (resumes.length > 0) {
          setHistoryResumes(resumes);
          setSelectedResume(resumes[0].resume);
          setSelectedResumeId(resumes[0].id); // 使用简历ID
          setHasHistoryResume(true);
        }
        
        // 决定默认模式
        if (sessions.length > 0) {
          setInputMode('history'); // 有会话，默认使用历史会话模式
        } else if (resumes.length > 0) {
          setInputMode('history'); // 无会话但有简历，也用历史模式
        } else {
          setInputMode('pdf'); // 都没有，使用PDF上传模式
        }
      } catch (error) {
        console.error('加载历史数据失败:', error);
        setInputMode('pdf');
      }
    };
    
    loadHistoryData();
  }, []);

  // 趣味提示轮播
  useEffect(() => {
    if (!isParsingPDF) return;
    
    const interval = setInterval(() => {
      setCurrentTipIndex(prev => (prev + 1) % TIPS.length);
    }, 4000);
    
    return () => clearInterval(interval);
  }, [isParsingPDF]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  // 处理进度事件
  const handleProgressEvent = useCallback((event: ParseProgressEvent) => {
    const stage = event.stage as ParseStage;
    setParseStage(stage);
    
    if (stage === 'converting' && event.current && event.total) {
      // 在 converting 阶段，根据页数计算进度 (10% ~ 40%)
      const convertProgress = 10 + (event.current / event.total) * 30;
      setParseProgress(convertProgress);
    } else if (stage in STAGES) {
      setParseProgress(STAGES[stage].progress);
    }
  }, []);

  const handleStart = async () => {
    setParseError(null);

    // 历史会话模式 - 直接恢复会话，无需JD
    if (inputMode === 'history' && selectedSession) {
      // 通过特殊标记告诉父组件恢复会话
      // @ts-ignore - 使用特殊标记传递会话ID
      onStart(null, '__RESTORE_SESSION__:' + selectedSession.id, null);
      return;
    }

    // 其他模式需要JD
    if (!jd.trim()) {
      alert('请输入职位描述');
      return;
    }

    // 历史简历模式
    if (inputMode === 'history' && selectedResume) {
      onStart(selectedResume, jd, null);
      return;
    }

    // PDF模式
    if (inputMode === 'pdf' && file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setParseError('请上传PDF格式的简历文件');
        return;
      }

      setIsParsingPDF(true);
      setParseStage('reading');
      setParseProgress(0);
      setCurrentTipIndex(Math.floor(Math.random() * TIPS.length));
      
      // 创建 AbortController 用于取消请求
      abortControllerRef.current = new AbortController();
      
      try {
        const resume = await parseResumeWithProgress(
          file,
          handleProgressEvent,
          abortControllerRef.current.signal
        );
        onStart(resume, jd, file);
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          console.log('解析已取消');
        } else {
          console.error('PDF解析失败:', error);
          setParseError(`PDF解析失败: ${error instanceof Error ? error.message : '未知错误'}`);
        }
        setIsParsingPDF(false);
      }
      return;
    }

    alert('请上传PDF文件');
  };

  // 取消解析
  const handleCancelParsing = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsParsingPDF(false);
    setParseProgress(0);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-2xl space-y-8">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center space-y-2"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 tracking-tight">
            简历助手
          </h1>
          <p className="text-lg text-gray-500">
            AI 驱动的简历优化
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="bg-white rounded-2xl shadow-xl p-8 space-y-6"
        >
          {/* 解析进度面板 */}
          <AnimatePresence mode="wait">
            {isParsingPDF ? (
              <motion.div
                key="parsing-panel"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* 动画图标 + 进度条 */}
                <div className="flex flex-col items-center py-4">
                  {/* 中心动画图标 */}
                  <div className="relative mb-6">
                    {/* 脉冲光圈 */}
                    <motion.div
                      className="absolute inset-0 bg-blue-400 rounded-full opacity-20"
                      animate={{ scale: [1, 1.8, 1.8], opacity: [0.3, 0, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                    />
                    <motion.div
                      className="absolute inset-0 bg-blue-400 rounded-full opacity-20"
                      animate={{ scale: [1, 1.8, 1.8], opacity: [0.3, 0, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "easeOut", delay: 0.6 }}
                    />
                    
                    {/* 图标容器 */}
                    <motion.div
                      className="relative w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-lg"
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    >
                      <AnimatePresence mode="wait">
                        {parseStage === 'complete' ? (
                          <motion.div
                            key="complete"
                            initial={{ scale: 0, rotate: -180 }}
                            animate={{ scale: 1, rotate: 0 }}
                            transition={{ type: "spring", stiffness: 200 }}
                          >
                            <CheckCircle className="w-10 h-10 text-white" />
                          </motion.div>
                        ) : parseStage === 'analyzing' ? (
                          <motion.div
                            key="analyzing"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                          >
                            <Bot className="w-10 h-10 text-white" />
                          </motion.div>
                        ) : (
                          <motion.div
                            key="reading"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                          >
                            <FileSearch className="w-10 h-10 text-white" />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  </div>
                  
                  {/* 进度条 */}
                  <div className="w-full max-w-xs space-y-2">
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${parseProgress}%` }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                      />
                    </div>
                    <p className="text-center text-sm text-gray-500">
                      {parseStage === 'complete' ? '解析完成' : '正在解析简历...'}
                    </p>
                  </div>
                </div>

                {/* 趣味提示 */}
                <motion.div
                  className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="flex items-start gap-3">
                    <Sparkles className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-h-[48px]">
                      <p className="text-sm font-medium text-amber-800 mb-1">简历小贴士</p>
                      <AnimatePresence mode="wait">
                        <motion.p
                          key={currentTipIndex}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ duration: 0.3 }}
                          className="text-sm text-amber-700"
                        >
                          {TIPS[currentTipIndex]}
                        </motion.p>
                      </AnimatePresence>
                    </div>
                  </div>
                </motion.div>

                {/* 取消按钮 */}
                <button
                  onClick={handleCancelParsing}
                  className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  取消解析
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="input-panel"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {/* Input Mode Toggle */}
                <div className="flex gap-2 p-1 bg-gray-100 rounded-lg">
                  {/* 历史Tab（只在有历史会话或历史简历时显示） */}
                  {(hasHistorySessions || hasHistoryResume) && (
                    <button
                      onClick={() => setInputMode('history')}
                      className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                        inputMode === 'history'
                          ? 'bg-white text-blue-600 shadow-sm'
                          : 'text-gray-600 hover:text-gray-800'
                      }`}
                    >
                      <FileText className="w-4 h-4 inline mr-1.5" />
                      历史
                    </button>
                  )}
                  
                  <button
                    onClick={() => setInputMode('pdf')}
                    className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                      inputMode === 'pdf'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-800'
                    }`}
                  >
                    <Upload className="w-4 h-4 inline mr-1.5" />
                    上传
                  </button>
                </div>

                {/* Error Message */}
                {parseError && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800"
                  >
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">解析失败</p>
                      <p className="mt-1">{parseError}</p>
                    </div>
                  </motion.div>
                )}

                {/* History Mode - 会话选择或简历选择 */}
                {inputMode === 'history' && (
                  <div className="space-y-4">
                    {/* 优先显示历史会话 */}
                    {hasHistorySessions && selectedSession ? (
                      <>
                        <SessionSelector
                          sessions={historySessions}
                          selectedSession={selectedSession}
                          onSelect={(session) => {
                            setSelectedSession(session);
                          }}
                        />
                        <p className="text-sm text-gray-500 text-center">
                          点击下方按钮继续优化简历
                        </p>
                      </>
                    ) : hasHistoryResume && selectedResume ? (
                      <>
                        <ResumeSelector
                          resumes={historyResumes}
                          selectedResume={selectedResume}
                          onSelect={(resume, resumeId) => {
                            setSelectedResume(resume);
                            setSelectedResumeId(resumeId);
                          }}
                          onDelete={async (resumeId) => {
                            const success = await sessionManager.deleteStoredResume(resumeId);
                            if (success) {
                              const newResumes = historyResumes.filter(r => r.id !== resumeId);
                              setHistoryResumes(newResumes);
                              if (newResumes.length === 0) {
                                setHasHistoryResume(false);
                                setSelectedResume(null);
                                setSelectedResumeId(null);
                                setInputMode('pdf');
                              } else if (selectedResumeId === resumeId) {
                                setSelectedResume(newResumes[0].resume);
                                setSelectedResumeId(newResumes[0].id);
                              }
                            }
                          }}
                          showDelete={true}
                        />
                        <div className="space-y-2">
                          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <Target className="w-4 h-4 text-blue-500" />
                            目标职位
                          </label>
                          <textarea
                            value={jd}
                            onChange={(e) => setJd(e.target.value)}
                            placeholder="粘贴职位要求..."
                            className="w-full min-h-[100px] p-4 text-base border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                          />
                        </div>
                      </>
                    ) : null}
                  </div>
                )}

                {/* PDF Upload Mode */}
                {inputMode === 'pdf' && (
                  <div className="space-y-4">
                    {/* 历史简历选择（如果有） */}
                    {hasHistoryResume && historyResumes.length > 0 && (
                      <div className="space-y-3">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                          <FileText className="w-4 h-4 text-blue-500" />
                          选择历史简历
                        </label>
                        <ResumeSelector
                          resumes={historyResumes}
                          selectedResume={selectedResume || historyResumes[0].resume}
                          onSelect={(resume, resumeId) => {
                            setSelectedResume(resume);
                            setSelectedResumeId(resumeId);
                            setFile(null); // 选择历史简历时清除文件
                          }}
                          onDelete={async (resumeId) => {
                            const success = await sessionManager.deleteStoredResume(resumeId);
                            if (success) {
                              // 更新本地状态
                              const newResumes = historyResumes.filter(r => r.id !== resumeId);
                              setHistoryResumes(newResumes);
                              if (newResumes.length === 0) {
                                setHasHistoryResume(false);
                                setSelectedResume(null);
                                setSelectedResumeId(null);
                              } else if (selectedResumeId === resumeId) {
                                // 如果删除的是当前选中的，选择第一个
                                setSelectedResume(newResumes[0].resume);
                                setSelectedResumeId(newResumes[0].id);
                              }
                            }
                          }}
                          showDelete={true}
                        />
                        
                        {/* 分隔线 */}
                        <div className="flex items-center gap-3 py-2">
                          <div className="flex-1 h-px bg-gray-200"></div>
                          <span className="text-sm text-gray-400">或上传新简历</span>
                          <div className="flex-1 h-px bg-gray-200"></div>
                        </div>
                      </div>
                    )}
                    
                    {/* PDF上传区 */}
                    <div 
                      className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-400 hover:bg-gray-50'
                      }`}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <input 
                        type="file" 
                        ref={fileInputRef} 
                        className="hidden" 
                        accept=".pdf" 
                        onChange={handleFileChange}
                      />
                      
                      {file ? (
                        <div className="flex items-center justify-center gap-3 text-blue-600">
                          <FileText className="w-8 h-8" />
                          <span className="text-lg font-medium">{file.name}</span>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              setFile(null);
                              setParseError(null);
                            }}
                            className="p-1 hover:bg-blue-100 rounded-full"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      ) : (
                        <div className="space-y-2 text-gray-500">
                          <div className="flex justify-center">
                            <Upload className="w-10 h-10 text-gray-400" />
                          </div>
                          <p className="text-lg font-medium">点击或拖拽上传新简历</p>
                          <p className="text-sm text-gray-400">PDF 格式</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* JD Input and Start Button */}
                <div className="space-y-4">
                  {/* 历史会话模式不需要JD输入 */}
                  {inputMode === 'history' && hasHistorySessions ? (
                    <motion.button
                      layoutId="start-button"
                      onClick={handleStart}
                      disabled={!selectedSession}
                      className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-semibold text-lg shadow-md transition-all flex items-center justify-center gap-2 group"
                    >
                      <Sparkles className="w-5 h-5" />
                      继续优化
                      <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </motion.button>
                  ) : (
                    <>
                      {/* JD输入区 */}
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                          <Target className="w-4 h-4 text-blue-500" />
                          目标职位
                        </label>
                        <motion.div 
                          layoutId="chat-input-area"
                          className="relative bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-shadow"
                        >
                          <textarea
                            value={jd}
                            onChange={(e) => setJd(e.target.value)}
                            placeholder="粘贴职位要求..."
                            className="w-full min-h-[100px] p-4 text-base resize-none border-none focus:ring-0"
                          />
                        </motion.div>
                      </div>

                      {/* 开始按钮 */}
                      <motion.button
                        layoutId="start-button"
                        onClick={handleStart}
                        disabled={
                          !jd.trim() || 
                          (inputMode === 'history' && !selectedResume) ||
                          (inputMode === 'pdf' && !file && !selectedResume)
                        }
                        className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-semibold text-lg shadow-md transition-all flex items-center justify-center gap-2 group"
                      >
                        <Sparkles className="w-5 h-5" />
                        开始优化
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </motion.button>
                    </>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}
