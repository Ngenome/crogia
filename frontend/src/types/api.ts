// Session Types (matching SessionResponse from backend)
export interface Session {
  session_id: string;
  container_id: string;
  workdir: string;
  created: string;
  last_task: string;
  status: string;
  container_status?: string;
}

// Task Types (matching TaskRequest from backend)
export interface TaskRequest {
  task: string;
  session_id?: string;
}

export interface TaskResponse {
  message: string;
  task: string;
}

// Process Types (matching ProcessInfo from backend)
export interface ProcessInfo {
  pid: number;
  cmd: string;
  status: string;
  log: string;
  started: string;
}

// File Types (matching FileContent and DirectoryListing from backend)
export interface FileContent {
  path: string;
  content: string;
}

export interface DirectoryItem {
  name: string;
  type: string;
  size?: number;
  modified?: string;
  error?: string;
}

export interface DirectoryListing {
  path: string;
  items: DirectoryItem[];
}

// Search Types (matching SearchRequest and GrepRequest from backend)
export interface SearchRequest {
  pattern: string;
  path?: string;
  file_types?: string;
}

export interface SearchResponse {
  pattern: string;
  path: string;
  matches: string[];
}

export interface GrepRequest {
  pattern: string;
  path?: string;
  file_types?: string;
}

export interface GrepMatch {
  file: string;
  line: number;
  content: string;
}

export interface GrepResponse {
  pattern: string;
  path: string;
  matches: GrepMatch[];
}

// Shell Command Types (matching ShellCommand from backend)
export interface ShellCommand {
  cmd: string;
  tty?: boolean;
}

export interface ShellResponse {
  command: string;
  output: string;
  timestamp: string;
}

// Terminal Shell Session Types
export interface ShellSession {
  shell_id: string;
  session_id: string;
  created: string;
  status: string;
}

export interface ShellSessionCreate {
  session_id: string;
}

export interface ShellListResponse {
  shells: ShellSession[];
}

// Terminal WebSocket Events
export interface ShellOutputEvent {
  type: "shell_output";
  data: string;
  shell_id: string;
}

export interface ShellConnectedEvent {
  type: "shell_connected";
  shell_id: string;
  session_id: string;
  timestamp: string;
  message: string;
}

export interface ShellInputMessage {
  type: "shell_input";
  data: string;
}

export interface ShellResizeMessage {
  type: "shell_resize";
  rows: number;
  cols: number;
}

export type ShellWSEventUnion = ShellOutputEvent | ShellConnectedEvent;

// Process Management Types
export interface ProcessLogsResponse {
  logs: string;
  pid: number;
}

export interface ProcessStopResponse {
  message: string;
}

// WebSocket Event Types (based on actual backend send_message calls)
export interface WSEvent {
  type: string;
  timestamp?: string;
}

export interface ConnectionEstablishedEvent extends WSEvent {
  type: "connection_established";
  session_id: string;
  message: string;
}

export interface TaskStartedEvent extends WSEvent {
  type: "task_started";
  session_id: string;
  task: string;
}

export interface TextDeltaEvent extends WSEvent {
  type: "text_delta";
  content: string;
}

export interface ToolCallEvent extends WSEvent {
  type: "tool_call";
  tool_name: string;
  arguments: string;
}

export interface ToolCompleteEvent extends WSEvent {
  type: "tool_complete";
}

export interface TaskCompletedEvent extends WSEvent {
  type: "task_completed";
  session_id: string;
  task: string;
}

export interface ErrorEvent extends WSEvent {
  type: "error";
  message: string;
}

export interface EchoEvent extends WSEvent {
  type: "echo";
  data: string;
}

// Union type for all WebSocket events
export type WSEventUnion =
  | ConnectionEstablishedEvent
  | TaskStartedEvent
  | TextDeltaEvent
  | ToolCallEvent
  | ToolCompleteEvent
  | TaskCompletedEvent
  | ErrorEvent
  | EchoEvent;

// Health Check (matching backend health_check response)
export interface HealthResponse {
  status: string;
  timestamp: string;
  active_sessions?: number;
  docker_available?: boolean;
  error?: string;
}

// Generic API Response Types
export interface MessageResponse {
  message: string;
}

export interface APIError {
  detail: string;
}

// Conversation History Types (based on the agent conversation structure)
export interface ConversationUserMessage {
  role: "user";
  content: string;
}

export interface ConversationAssistantMessage {
  role: "assistant";
  content: Array<{
    type: "output_text";
    text: string;
    annotations?: unknown[];
  }>;
  id?: string;
  status?: string;
  type?: string;
}

export interface ConversationReasoningStep {
  id: string;
  summary: unknown[];
  type: "reasoning";
}

export interface ConversationFunctionCall {
  id: string;
  type: "function_call";
  name: string;
  arguments: string;
  call_id: string;
  status: "completed";
}

export interface ConversationFunctionOutput {
  type: "function_call_output";
  call_id: string;
  output: string;
}

export type ConversationHistoryItem =
  | ConversationUserMessage
  | ConversationAssistantMessage
  | ConversationReasoningStep
  | ConversationFunctionCall
  | ConversationFunctionOutput;
