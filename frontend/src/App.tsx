import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/services/api";
import { websocket } from "@/services/websocket";
import type {
  Session,
  WSEventUnion,
  ConversationHistoryItem,
} from "@/types/api";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { ConversationWorkflow } from "@/components/ConversationWorkflow";
import { TerminalManager } from "@/components/TerminalManager";

// Event types for the activity timeline
export interface ProcessedEvent {
  title: string;
  data: string;
  timestamp?: string;
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<
    ProcessedEvent[]
  >([]);
  const [historicalActivities] = useState<Record<string, ProcessedEvent[]>>({});
  const [messages, setMessages] = useState<
    Array<{ type: "human" | "ai"; content: string; id: string }>
  >([]);
  const [currentOutput, setCurrentOutput] = useState<string>("");
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [showTerminals, setShowTerminals] = useState(false);
  const [workflowData, setWorkflowData] = useState<ConversationHistoryItem[]>(
    []
  );
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Load sessions on app start
  useEffect(() => {
    loadSessions();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [messages, currentOutput]);

  const loadSessions = async () => {
    try {
      const sessionList = await api.getSessions();
      setSessions(sessionList);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  };

  const handleWebSocketEvent = useCallback(
    (event: WSEventUnion) => {
      let processedEvent: ProcessedEvent | null = null;

      switch (event.type) {
        case "connection_established":
          processedEvent = {
            title: "🔗 Connection Established",
            data: event.message,
            timestamp: event.timestamp,
          };
          console.log("WebSocket connected to session:", event.session_id);
          break;

        case "task_started":
          processedEvent = {
            title: "🚀 Task Started",
            data: `Executing: ${event.task}`,
            timestamp: event.timestamp,
          };
          setCurrentOutput(""); // Clear output for new task
          setMessages((prev) => [
            ...prev,
            {
              type: "ai",
              content: `Starting task: ${event.task}`,
              id: `task-start-${Date.now()}`,
            },
          ]);
          break;

        case "text_delta":
          // Accumulate text output from the agent
          setCurrentOutput((prev) => prev + event.content);
          break;

        case "tool_call":
          processedEvent = {
            title: `🔧 ${event.tool_name}`,
            data: `Executing tool with args: ${event.arguments}`,
            timestamp: event.timestamp,
          };
          // Also add to current output to show what the agent is doing
          setCurrentOutput(
            (prev) => prev + `\n\n**🔧 Using tool: ${event.tool_name}**\n`
          );
          break;

        case "tool_complete":
          processedEvent = {
            title: "✅ Tool Complete",
            data: "Tool execution finished successfully",
            timestamp: event.timestamp,
          };
          setCurrentOutput((prev) => prev + "\n*Tool execution completed*\n\n");
          break;

        case "task_completed":
          processedEvent = {
            title: "🎉 Task Completed",
            data: `Successfully finished: ${event.task}`,
            timestamp: event.timestamp,
          };

          // Add the final accumulated output as an AI message
          if (currentOutput.trim()) {
            setMessages((prev) => [
              ...prev,
              {
                type: "ai",
                content: currentOutput.trim(),
                id: `task-complete-${Date.now()}`,
              },
            ]);
          }

          // Add completion message
          setMessages((prev) => [
            ...prev,
            {
              type: "ai",
              content: `✅ Task completed successfully: ${event.task}`,
              id: `completion-${Date.now()}`,
            },
          ]);

          setCurrentOutput(""); // Clear for next task
          setIsLoading(false);
          break;

        case "error":
          processedEvent = {
            title: "❌ Error",
            data: event.message,
            timestamp: event.timestamp,
          };

          // Add error as AI message
          setMessages((prev) => [
            ...prev,
            {
              type: "ai",
              content: `❌ Error: ${event.message}`,
              id: `error-${Date.now()}`,
            },
          ]);

          setCurrentOutput("");
          setIsLoading(false);
          break;

        default:
          console.log("Unhandled WebSocket event:", event);
      }

      if (processedEvent) {
        setProcessedEventsTimeline((prev) => [...prev, processedEvent!]);
      }
    },
    [currentOutput]
  );

  const handleSubmit = useCallback(
    async (task: string) => {
      if (!task.trim()) return;

      setIsLoading(true);
      setProcessedEventsTimeline([]);
      setCurrentOutput("");

      try {
        let session = currentSession;

        // Create new session if none exists
        if (!session) {
          session = await api.createSession(task);
          setCurrentSession(session);
          setSessions((prev) => [...prev, session!]);

          // Connect to WebSocket for this session
          await websocket.connect(session.session_id);
          websocket.onAny(handleWebSocketEvent);
        }

        // Add user message
        const userMessage = {
          type: "human" as const,
          content: task,
          id: Date.now().toString(),
        };
        setMessages((prev) => [...prev, userMessage]);

        // Execute the task
        await api.executeTask(session.session_id, task);
      } catch (error) {
        console.error("Failed to execute task:", error);
        setIsLoading(false);

        // Add error message
        setMessages((prev) => [
          ...prev,
          {
            type: "ai",
            content: `Error: ${
              error instanceof Error ? error.message : "Unknown error occurred"
            }`,
            id: Date.now().toString(),
          },
        ]);
      }
    },
    [currentSession, handleWebSocketEvent]
  );

  const handleCancel = useCallback(() => {
    setIsLoading(false);
    websocket.disconnect();
    // Could also call an API endpoint to cancel the task if available
  }, []);

  const handleNewSession = useCallback(() => {
    setCurrentSession(null);
    setMessages([]);
    setProcessedEventsTimeline([]);
    setCurrentOutput("");
    websocket.disconnect();
  }, []);

  const loadWorkflowData = useCallback(async (sessionId: string) => {
    try {
      const fullConversation = await api.getSessionConversationFull(sessionId);
      setWorkflowData(fullConversation.conversation_history);
    } catch (error) {
      console.error("Failed to load workflow data:", error);
      setWorkflowData([]);
    }
  }, []);

  const handleSelectSession = useCallback(
    async (session: Session) => {
      setCurrentSession(session);
      setProcessedEventsTimeline([]);
      setCurrentOutput("");

      try {
        // Load conversation history for this session
        const conversationData = await api.getSessionConversation(
          session.session_id
        );
        setMessages(conversationData.messages || []);

        // Load full workflow data
        await loadWorkflowData(session.session_id);

        // Connect to WebSocket for this session
        await websocket.connect(session.session_id);
        websocket.onAny(handleWebSocketEvent);
      } catch (error) {
        console.error(
          "Failed to connect to session or load conversation:",
          error
        );
        // Still set empty messages if conversation loading fails
        setMessages([]);

        // Try to connect to WebSocket anyway
        try {
          await websocket.connect(session.session_id);
          websocket.onAny(handleWebSocketEvent);
        } catch (wsError) {
          console.error("Failed to connect to session WebSocket:", wsError);
        }
      }
    },
    [handleWebSocketEvent, loadWorkflowData]
  );

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.deleteSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));

        if (currentSession?.session_id === sessionId) {
          handleNewSession();
        }
      } catch (error) {
        console.error("Failed to delete session:", error);
      }
    },
    [currentSession, handleNewSession]
  );

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      {/* Sidebar for session management */}
      <div className="w-80 bg-neutral-900 border-r border-neutral-700 flex flex-col">
        <div className="p-4 border-b border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-100">
            Crogia Agent Sessions
          </h2>
          <button
            onClick={handleNewSession}
            className="mt-2 w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium transition-colors"
          >
            New Session
          </button>

          {currentSession && (
            <>
              <button
                onClick={() => setShowWorkflow(!showWorkflow)}
                className="mt-2 w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-md text-sm font-medium transition-colors"
              >
                {showWorkflow ? "Hide Workflow" : "Show Workflow"}
              </button>

              <button
                onClick={() => setShowTerminals(!showTerminals)}
                className="mt-2 w-full px-3 py-2 bg-green-600 hover:bg-green-700 rounded-md text-sm font-medium transition-colors"
              >
                {showTerminals ? "Hide Terminals" : "Show Terminals"}
              </button>
            </>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {sessions.length === 0 ? (
            <p className="text-neutral-400 text-sm">No active sessions</p>
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`p-3 rounded-md border cursor-pointer transition-colors ${
                    currentSession?.session_id === session.session_id
                      ? "bg-blue-600 border-blue-500"
                      : "bg-neutral-800 border-neutral-600 hover:bg-neutral-700"
                  }`}
                  onClick={() => handleSelectSession(session)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {session.session_id}
                      </p>
                      <p className="text-xs text-neutral-400 mt-1 truncate">
                        {session.last_task}
                      </p>
                      <p className="text-xs text-neutral-500 mt-1">
                        {new Date(session.created).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSession(session.session_id);
                      }}
                      className="ml-2 text-neutral-400 hover:text-red-400 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        session.container_status === "running"
                          ? "bg-green-500"
                          : "bg-red-500"
                      }`}
                    />
                    <span className="text-xs text-neutral-400">
                      {session.container_status || "unknown"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main content area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div
          className={`flex-1 overflow-y-auto ${
            !currentSession && messages.length === 0 ? "flex" : ""
          }`}
        >
          {!currentSession && messages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={isLoading}
              onCancel={handleCancel}
            />
          ) : showWorkflow && currentSession ? (
            <ConversationWorkflow
              conversationHistory={workflowData}
              sessionId={currentSession.session_id}
            />
          ) : showTerminals && currentSession ? (
            <TerminalManager
              sessionId={currentSession.session_id}
              isVisible={showTerminals}
            />
          ) : (
            <ChatMessagesView
              messages={messages}
              isLoading={isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              liveActivityEvents={processedEventsTimeline}
              historicalActivities={historicalActivities}
              currentOutput={currentOutput}
              sessionInfo={currentSession}
            />
          )}
        </div>
      </main>
    </div>
  );
}
