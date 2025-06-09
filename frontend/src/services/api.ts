import { API_ENDPOINTS } from "@/constants/urls";
import type {
  Session,
  TaskRequest,
  TaskResponse,
  ProcessInfo,
  FileContent,
  DirectoryListing,
  SearchRequest,
  SearchResponse,
  GrepRequest,
  GrepResponse,
  ShellCommand,
  ShellResponse,
  ProcessLogsResponse,
  ProcessStopResponse,
  HealthResponse,
  MessageResponse,
  APIError as APIErrorType,
  ConversationHistoryItem,
} from "@/types/api";

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

class CrogiaAPI {
  private async request<T>(url: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData: APIErrorType = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // If we can't parse the error response, use the status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new APIError(response.status, errorMessage);
    }

    return response.json();
  }

  // Health Check
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>(API_ENDPOINTS.HEALTH);
  }

  // Session Management
  async getSessions(): Promise<Session[]> {
    return this.request<Session[]>(API_ENDPOINTS.SESSIONS);
  }

  async createSession(task: string): Promise<Session> {
    const taskRequest: TaskRequest = { task };
    return this.request<Session>(API_ENDPOINTS.SESSIONS, {
      method: "POST",
      body: JSON.stringify(taskRequest),
    });
  }

  async getSession(sessionId: string): Promise<Session> {
    return this.request<Session>(API_ENDPOINTS.SESSION_BY_ID(sessionId));
  }

  async getSessionConversation(sessionId: string): Promise<{
    session_id: string;
    messages: Array<{ type: "human" | "ai"; content: string; id: string }>;
    last_task: string;
    total_messages: number;
  }> {
    return this.request(API_ENDPOINTS.SESSION_CONVERSATION(sessionId));
  }

  async getSessionConversationFull(sessionId: string): Promise<{
    session_id: string;
    conversation_history: ConversationHistoryItem[];
    last_task: string;
    total_items: number;
  }> {
    return this.request(`/api/sessions/${sessionId}/conversation/full`);
  }

  async deleteSession(sessionId: string): Promise<MessageResponse> {
    return this.request<MessageResponse>(
      API_ENDPOINTS.SESSION_BY_ID(sessionId),
      {
        method: "DELETE",
      }
    );
  }

  // Task Execution
  async executeTask(sessionId: string, task: string): Promise<TaskResponse> {
    const taskRequest: TaskRequest = { task };
    return this.request<TaskResponse>(API_ENDPOINTS.SESSION_TASKS(sessionId), {
      method: "POST",
      body: JSON.stringify(taskRequest),
    });
  }

  // File Operations
  async listFiles(
    sessionId: string,
    path: string = "."
  ): Promise<DirectoryListing> {
    const url = new URL(API_ENDPOINTS.SESSION_FILES(sessionId));
    url.searchParams.set("path", path);
    return this.request<DirectoryListing>(url.toString());
  }

  async getFileContent(sessionId: string, path: string): Promise<FileContent> {
    const url = new URL(API_ENDPOINTS.SESSION_FILE_CONTENT(sessionId));
    url.searchParams.set("path", path);
    return this.request<FileContent>(url.toString());
  }

  async writeFileContent(
    sessionId: string,
    fileContent: FileContent
  ): Promise<MessageResponse> {
    return this.request<MessageResponse>(
      API_ENDPOINTS.SESSION_FILE_CONTENT(sessionId),
      {
        method: "POST",
        body: JSON.stringify(fileContent),
      }
    );
  }

  // Search Operations
  async searchFiles(
    sessionId: string,
    searchRequest: SearchRequest
  ): Promise<SearchResponse> {
    return this.request<SearchResponse>(
      API_ENDPOINTS.SESSION_SEARCH_FILES(sessionId),
      {
        method: "POST",
        body: JSON.stringify(searchRequest),
      }
    );
  }

  async grepSearch(
    sessionId: string,
    grepRequest: GrepRequest
  ): Promise<GrepResponse> {
    return this.request<GrepResponse>(
      API_ENDPOINTS.SESSION_SEARCH_GREP(sessionId),
      {
        method: "POST",
        body: JSON.stringify(grepRequest),
      }
    );
  }

  // Process Management
  async getProcesses(sessionId: string): Promise<ProcessInfo[]> {
    return this.request<ProcessInfo[]>(
      API_ENDPOINTS.SESSION_PROCESSES(sessionId)
    );
  }

  async stopProcess(
    sessionId: string,
    pid: number
  ): Promise<ProcessStopResponse> {
    return this.request<ProcessStopResponse>(
      API_ENDPOINTS.SESSION_PROCESS_STOP(sessionId, pid),
      {
        method: "POST",
      }
    );
  }

  async getProcessLogs(
    sessionId: string,
    pid: number,
    lines: number = 50
  ): Promise<ProcessLogsResponse> {
    const url = new URL(API_ENDPOINTS.SESSION_PROCESS_LOGS(sessionId, pid));
    url.searchParams.set("lines", lines.toString());
    return this.request<ProcessLogsResponse>(url.toString());
  }

  // Shell Commands
  async executeShellCommand(
    sessionId: string,
    shellCommand: ShellCommand
  ): Promise<ShellResponse> {
    return this.request<ShellResponse>(API_ENDPOINTS.SESSION_SHELL(sessionId), {
      method: "POST",
      body: JSON.stringify(shellCommand),
    });
  }
}

// Export a singleton instance
export const api = new CrogiaAPI();
export { APIError };
