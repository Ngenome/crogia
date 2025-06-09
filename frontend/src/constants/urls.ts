// API Base URLs
export const API_BASE_URL = import.meta.env.DEV
  ? "http://localhost:8000"
  : "http://localhost:8000";

export const WS_BASE_URL = import.meta.env.DEV
  ? "ws://localhost:8000"
  : "ws://localhost:8000";

// API Endpoints
export const API_ENDPOINTS = {
  // Health check
  HEALTH: `${API_BASE_URL}/api/health`,

  // Session management
  SESSIONS: `${API_BASE_URL}/api/sessions`,
  SESSION_BY_ID: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}`,
  SESSION_CONVERSATION: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/conversation`,
  SESSION_TASKS: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/tasks`,

  // File operations
  SESSION_FILES: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/files`,
  SESSION_FILE_CONTENT: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/files/content`,

  // Search operations
  SESSION_SEARCH_FILES: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/search/files`,
  SESSION_SEARCH_GREP: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/search/grep`,

  // Process management
  SESSION_PROCESSES: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/processes`,
  SESSION_PROCESS_STOP: (sessionId: string, pid: number) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/processes/${pid}/stop`,
  SESSION_PROCESS_LOGS: (sessionId: string, pid: number) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/processes/${pid}/logs`,

  // Shell commands
  SESSION_SHELL: (sessionId: string) =>
    `${API_BASE_URL}/api/sessions/${sessionId}/shell`,
} as const;

// WebSocket Endpoints
export const WS_ENDPOINTS = {
  SESSION_STREAM: (sessionId: string) => `${WS_BASE_URL}/ws/${sessionId}`,
} as const;

// WebSocket Event Types (matching backend events)
export const WS_EVENT_TYPES = {
  CONNECTION_ESTABLISHED: "connection_established",
  TASK_STARTED: "task_started",
  TEXT_DELTA: "text_delta",
  TOOL_CALL: "tool_call",
  TOOL_COMPLETE: "tool_complete",
  TASK_COMPLETED: "task_completed",
  ERROR: "error",
  ECHO: "echo",
} as const;

export type WSEventType = (typeof WS_EVENT_TYPES)[keyof typeof WS_EVENT_TYPES];
