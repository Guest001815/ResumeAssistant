/**
 * Session Manager: 会话管理器
 * 
 * 负责会话的创建、加载、保存、切换、删除
 * 实现混合存储策略：LocalStorage + 服务器
 */

import { Resume, Task } from "../api/workflow";

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8001";

// ==================== 类型定义 ====================

export interface SessionMetadata {
  id: string;
  name?: string;
  resume_file_name: string;
  job_title: string;
  job_company: string;
  created_at: string;
  updated_at: string;
  progress: {
    completed: number;
    total: number;
  };
  status: 'active' | 'completed';
}

export interface Session extends SessionMetadata {
  resume: Resume;
  user_intent: string;
  plan?: {
    tasks: Task[];
  };
  current_task_idx: number;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface LocalSession extends Session {
  messages: Message[];
}

// ==================== Session Manager ====================

class SessionManager {
  private STORAGE_KEYS = {
    sessions: 'ra_sessions',
    currentId: 'ra_current_session_id',
    messages: 'ra_messages_' // 前缀，后面加session_id
  };

  /**
   * 获取当前会话ID
   */
  getCurrentSessionId(): string | null {
    return localStorage.getItem(this.STORAGE_KEYS.currentId);
  }

  /**
   * 设置当前会话ID
   */
  setCurrentSessionId(sessionId: string | null): void {
    if (sessionId) {
      localStorage.setItem(this.STORAGE_KEYS.currentId, sessionId);
    } else {
      localStorage.removeItem(this.STORAGE_KEYS.currentId);
    }
  }

  /**
   * 获取所有会话元数据
   * 优先从LocalStorage读取，降级到服务器
   */
  async getSessions(): Promise<SessionMetadata[]> {
    try {
      // 先尝试从LocalStorage读取
      const cached = localStorage.getItem(this.STORAGE_KEYS.sessions);
      if (cached) {
        const sessions = JSON.parse(cached) as SessionMetadata[];
        
        // 异步同步服务器数据（不阻塞返回）
        this.syncSessionsFromServer().catch(err => {
          console.warn('同步服务器会话失败:', err);
        });
        
        return sessions;
      }

      // LocalStorage没有，从服务器加载
      return await this.syncSessionsFromServer();
    } catch (error) {
      console.error('获取会话列表失败:', error);
      return [];
    }
  }

  /**
   * 从服务器同步会话列表
   */
  private async syncSessionsFromServer(): Promise<SessionMetadata[]> {
    const response = await fetch(`${API_BASE}/sessions`);
    if (!response.ok) {
      throw new Error(`获取会话列表失败: ${response.status}`);
    }

    const sessions = await response.json() as SessionMetadata[];
    
    // 保存到LocalStorage
    localStorage.setItem(this.STORAGE_KEYS.sessions, JSON.stringify(sessions));
    
    return sessions;
  }

  /**
   * 获取完整会话数据
   * 优先从LocalStorage，未命中则从服务器
   */
  async getSession(sessionId: string): Promise<LocalSession | null> {
    try {
      // 先尝试从LocalStorage读取完整数据
      const messagesKey = this.STORAGE_KEYS.messages + sessionId;
      const messages = localStorage.getItem(messagesKey);
      
      // 从服务器获取最新的会话数据
      const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error(`获取会话失败: ${response.status}`);
      }

      const session = await response.json() as Session;
      
      // 合并消息历史
      const localSession: LocalSession = {
        ...session,
        messages: messages ? JSON.parse(messages) : []
      };

      return localSession;
    } catch (error) {
      console.error('获取会话失败:', error);
      return null;
    }
  }

  /**
   * 创建新会话
   * 注意：这里只创建会话，不自动设置为当前会话
   */
  async createSession(resume: Resume, userIntent: string): Promise<string> {
    // 先创建会话
    const createResponse = await fetch(`${API_BASE}/session/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume })
    });

    if (!createResponse.ok) {
      throw new Error(`创建会话失败: ${createResponse.status}`);
    }

    const { session_id } = await createResponse.json();

    // 生成计划
    const planResponse = await fetch(`${API_BASE}/session/${session_id}/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_intent: userIntent })
    });

    if (!planResponse.ok) {
      throw new Error(`生成计划失败: ${planResponse.status}`);
    }

    // 刷新会话列表缓存
    await this.syncSessionsFromServer();

    return session_id;
  }

  /**
   * 切换到指定会话
   */
  async switchSession(sessionId: string): Promise<LocalSession | null> {
    const session = await this.getSession(sessionId);
    if (session) {
      this.setCurrentSessionId(sessionId);
    }
    return session;
  }

  /**
   * 删除会话
   */
  async deleteSession(sessionId: string): Promise<void> {
    // 删除服务器上的会话
    const response = await fetch(`${API_BASE}/session/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`删除会话失败: ${response.status}`);
    }

    // 删除LocalStorage中的数据
    const messagesKey = this.STORAGE_KEYS.messages + sessionId;
    localStorage.removeItem(messagesKey);

    // 如果删除的是当前会话，清除当前会话ID
    if (this.getCurrentSessionId() === sessionId) {
      this.setCurrentSessionId(null);
    }

    // 刷新会话列表缓存
    await this.syncSessionsFromServer();
  }

  /**
   * 更新会话名称
   */
  async updateSessionName(sessionId: string, name: string): Promise<void> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/metadata`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });

    if (!response.ok) {
      throw new Error(`更新会话名称失败: ${response.status}`);
    }

    // 刷新会话列表缓存
    await this.syncSessionsFromServer();
  }

  /**
   * 保存当前会话状态
   * 只保存消息到LocalStorage，其他数据通过API自动同步
   */
  async saveCurrentSession(sessionId: string, messages: Message[]): Promise<void> {
    try {
      // 保存消息到LocalStorage
      const messagesKey = this.STORAGE_KEYS.messages + sessionId;
      localStorage.setItem(messagesKey, JSON.stringify(messages));

      // 异步刷新会话列表（不阻塞）
      this.syncSessionsFromServer().catch(err => {
        console.warn('同步会话列表失败:', err);
      });
    } catch (error) {
      console.error('保存会话状态失败:', error);
    }
  }

  /**
   * 清除所有本地缓存
   */
  clearLocalCache(): void {
    localStorage.removeItem(this.STORAGE_KEYS.sessions);
    localStorage.removeItem(this.STORAGE_KEYS.currentId);
    
    // 清除所有消息缓存
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.STORAGE_KEYS.messages)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
  }

  /**
   * 获取最近使用的简历
   */
  async getRecentResume(): Promise<{
    resume: Resume;
    session_id: string;
    last_used: string;
  } | null> {
    try {
      const response = await fetch(`${API_BASE}/resumes/recent`);
      
      if (response.status === 404) {
        return null; // 没有历史记录
      }

      if (!response.ok) {
        throw new Error(`获取最近简历失败: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('获取最近简历失败:', error);
      return null;
    }
  }

  /**
   * 获取所有历史简历（去重）- 从会话中提取
   * @deprecated 使用 getStoredResumes 代替
   */
  async getAllResumes(): Promise<Array<{
    resume: Resume;
    session_id: string;
    last_used: string;
    name: string;
    label: string;
  }>> {
    try {
      const response = await fetch(`${API_BASE}/resumes/list`);

      if (!response.ok) {
        throw new Error(`获取简历列表失败: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('获取简历列表失败:', error);
      return [];
    }
  }

  /**
   * 获取所有独立存储的简历
   */
  async getStoredResumes(): Promise<Array<{
    id: string;
    resume: Resume;
    name: string;
    label: string;
    created_at: string;
    updated_at: string;
  }>> {
    try {
      const response = await fetch(`${API_BASE}/resumes`);

      if (!response.ok) {
        throw new Error(`获取简历列表失败: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('获取简历列表失败:', error);
      return [];
    }
  }

  /**
   * 删除独立存储的简历
   */
  async deleteStoredResume(resumeId: string): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/resumes/${resumeId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`删除简历失败: ${response.status}`);
      }

      return true;
    } catch (error) {
      console.error('删除简历失败:', error);
      return false;
    }
  }
}

// 导出单例
export const sessionManager = new SessionManager();

