/**
 * 工作流API客户端
 * 封装所有新的 /session/* 端点
 */

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8001";

// ==================== 类型定义 ====================

export interface Resume {
  basics: {
    name: string;
    label?: string;
    email?: string;
    phone?: string;
    links?: string[];
  };
  sections: Array<ExperienceSection | GenericSection | TextSection>;
}

export interface ExperienceSection {
  id: string;
  title: string;
  type: "experience";
  items: ExperienceItem[];
}

export interface GenericSection {
  id: string;
  title: string;
  type: "generic";
  items: GenericItem[];
}

export interface TextSection {
  id: string;
  title: string;
  type: "text";
  content: string;
}

export interface ExperienceItem {
  id: string;
  title: string;
  organization: string;
  date_start?: string;
  date_end?: string;
  location?: string;
  highlights: string[];
}

export interface GenericItem {
  id: string;
  title: string;
  subtitle?: string;
  date?: string;
  description?: string;
}

export interface Task {
  id: number;
  status: "pending" | "in_progress" | "confirmed" | "completed" | "skipped";
  section: string;
  original_text: string;
  diagnosis: string;
  goal: string;
}

export interface TaskList {
  tasks: Task[];
}

export interface ExecutionDoc {
  task_id: number;
  section_title: string;
  item_id?: string;
  operation: "update_basics" | "update_experience" | "update_generic" | "add_item";
  changes: Record<string, any>;
  new_content_preview: string;
  reason: string;
}

export interface GuideResponse {
  thought: string;
  reply: string;
  state: string;
  draft?: string;
  execution_doc?: ExecutionDoc;
  is_confirming: boolean;
  is_finished: boolean;
}

export interface ProgressResponse {
  total_tasks: number;
  completed_tasks: number;
  skipped_tasks: number;
  current_task_idx: number;
  current_task?: Task;
  tasks_summary: Array<{
    id: number;
    section: string;
    status: string;
  }>;
}

// ==================== API函数 ====================

/**
 * 解析进度事件类型
 */
export interface ParseProgressEvent {
  stage: "reading" | "converting" | "analyzing" | "complete" | "error";
  message: string;
  current?: number;
  total?: number;
  resume?: Resume;
}

/**
 * 计划生成进度事件类型
 */
export interface PlanProgressEvent {
  stage: "preparing" | "analyzing" | "complete" | "error";
  progress: number; // 0-100
  message: string;
  plan?: TaskList;
}

/**
 * 解析PDF简历
 */
export async function parseResume(file: File): Promise<Resume> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/parse_resume`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`解析失败: ${error}`);
  }

  return await response.json();
}

/**
 * 流式解析PDF简历（带进度回调）
 */
export async function parseResumeWithProgress(
  file: File,
  onProgress: (event: ParseProgressEvent) => void,
  signal?: AbortSignal
): Promise<Resume> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/parse_resume_stream`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok || !response.body) {
    const error = await response.text();
    throw new Error(`解析失败: ${error}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalResume: Resume | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop() || "";

    for (const line of parts) {
      const s = line.trim();
      if (!s) continue;

      let content = s;
      if (content.startsWith("data:")) {
        content = content.slice(5).trim();
      }

      try {
        const event = JSON.parse(content) as ParseProgressEvent;
        onProgress(event);

        if (event.stage === "complete" && event.resume) {
          finalResume = event.resume;
        }

        if (event.stage === "error") {
          throw new Error(event.message);
        }
      } catch (e) {
        if (e instanceof Error && e.message !== "Unexpected end of JSON input") {
          throw e;
        }
      }
    }
  }

  if (!finalResume) {
    throw new Error("解析未完成");
  }

  return finalResume;
}

/**
 * 创建会话
 */
export async function createSession(resume: Resume): Promise<string> {
  const response = await fetch(`${API_BASE}/session/create`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ resume }),
  });

  if (!response.ok) {
    throw new Error(`创建会话失败: ${response.status}`);
  }

  const data = await response.json();
  return data.session_id;
}

/**
 * 生成任务计划
 */
export async function generatePlan(
  sessionId: string,
  userIntent: string
): Promise<TaskList> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_intent: userIntent }),
  });

  if (!response.ok) {
    throw new Error(`生成计划失败: ${response.status}`);
  }

  const data = await response.json();
  return data.plan;
}

/**
 * 流式生成任务计划（带伪进度反馈）
 */
export async function generatePlanWithProgress(
  sessionId: string,
  userIntent: string,
  onProgress: (event: PlanProgressEvent) => void,
  signal?: AbortSignal
): Promise<TaskList> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/plan_stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ user_intent: userIntent }),
    signal,
  });

  if (!response.ok || !response.body) {
    const error = await response.text();
    throw new Error(`生成计划失败: ${error}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalPlan: TaskList | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop() || "";

    for (const line of parts) {
      const s = line.trim();
      if (!s) continue;

      let content = s;
      if (content.startsWith("data:")) {
        content = content.slice(5).trim();
      }

      try {
        const event = JSON.parse(content) as PlanProgressEvent;
        onProgress(event);

        if (event.stage === "complete" && event.plan) {
          finalPlan = event.plan;
        }

        if (event.stage === "error") {
          throw new Error(event.message);
        }
      } catch (e) {
        if (e instanceof Error && e.message !== "Unexpected end of JSON input") {
          throw e;
        }
      }
    }
  }

  if (!finalPlan) {
    throw new Error("计划生成未完成");
  }

  return finalPlan;
}

/**
 * Guide Agent 单步交互
 */
export async function guideStep(
  sessionId: string,
  userInput: string
): Promise<GuideResponse> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/guide`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_input: userInput }),
  });

  if (!response.ok) {
    throw new Error(`Guide交互失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * Guide Agent 自动开场白
 * 
 * 在每个任务开始时调用，生成结构化的开场白，包含：
 * - 任务简介
 * - 问题诊断
 * - 优化目标
 * - 引导问题
 * 
 * 无需用户输入，由 LLM 主动生成引导消息。
 */
export async function guideInit(sessionId: string): Promise<GuideResponse> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/guide/init`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`开场白生成失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * 确认并执行 Editor Agent（SSE流式）
 */
export async function confirmAndExecute(
  sessionId: string,
  onEvent: (event: any) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/confirm`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
    },
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`执行失败: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop() || "";

    for (const line of parts) {
      const s = line.trim();
      if (!s) continue;

      let content = s;
      if (content.startsWith("data:")) {
        content = content.slice(5).trim();
      }

      try {
        const obj = JSON.parse(content);
        onEvent(obj);
      } catch {
        // ignore parse errors
      }
    }
  }
}

/**
 * 跳过当前任务
 */
export async function skipTask(sessionId: string): Promise<{
  success: boolean;
  message: string;
  next_task?: Task;
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/skip`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`跳过任务失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * 进入下一个任务
 */
export async function nextTask(sessionId: string): Promise<{
  success: boolean;
  has_next: boolean;
  task?: Task;
  message: string;
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/next`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`进入下一任务失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * 获取进度
 */
export async function getProgress(sessionId: string): Promise<ProgressResponse> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/progress`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`获取进度失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * 获取会话信息
 */
export async function getSessionInfo(sessionId: string): Promise<{
  session_id: string;
  user_intent?: string;
  current_stage: string;
  has_plan: boolean;
  current_task_idx: number;
  has_exec_doc: boolean;
  resume: Resume;
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`获取会话信息失败: ${response.status}`);
  }

  return await response.json();
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`删除会话失败: ${response.status}`);
  }
}

/**
 * 更新会话中的简历数据
 */
export async function updateResume(sessionId: string, resume: Resume): Promise<void> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/resume`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(resume),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`更新简历失败: ${errorText || response.status}`);
  }
}

/**
 * 获取最近使用的简历
 */
export async function getRecentResume(): Promise<{
  resume: Resume;
  session_id: string;
  last_used: string;
} | null> {
  try {
    const response = await fetch(`${API_BASE}/resumes/recent`, {
      method: "GET",
    });

    if (response.status === 404) {
      return null; // 没有历史记录
    }

    if (!response.ok) {
      throw new Error(`获取最近简历失败: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("获取最近简历失败:", error);
    return null;
  }
}

/**
 * 获取所有历史简历列表（去重）
 */
export async function getAllResumes(): Promise<Array<{
  resume: Resume;
  session_id: string;
  last_used: string;
  name: string;
  label: string;
}>> {
  try {
    const response = await fetch(`${API_BASE}/resumes/list`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`获取简历列表失败: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("获取简历列表失败:", error);
    return [];
  }
}

