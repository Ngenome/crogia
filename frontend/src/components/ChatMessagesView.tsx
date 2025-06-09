import React, { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Copy,
  CopyCheck,
  Send,
  StopCircle,
  User,
  Bot,
  Container,
  Clock,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import {
  ActivityTimeline,
  ProcessedEvent,
} from "@/components/ActivityTimeline";
import type { Session } from "@/types/api";

// Message type for our Crogia app
interface Message {
  type: "human" | "ai";
  content: string;
  id: string;
}

interface ChatMessagesViewProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (task: string) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  currentOutput?: string;
  sessionInfo?: Session | null;
}

// Markdown components for better rendering
const mdComponents = {
  h1: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  h2: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  h3: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  p: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  code: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLElement>) => (
    <code
      className={cn(
        "bg-neutral-800 rounded px-1 py-0.5 font-mono text-xs",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre
      className={cn(
        "bg-neutral-800 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
};

// Human message bubble
const HumanMessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  return (
    <div className="flex justify-end mb-4">
      <div className="flex items-start gap-3 max-w-[80%]">
        <div className="bg-blue-600 text-white rounded-3xl rounded-br-lg px-4 py-3">
          <ReactMarkdown components={mdComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
        <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
          <User className="w-4 h-4 text-white" />
        </div>
      </div>
    </div>
  );
};

// AI message bubble
const AiMessageBubble: React.FC<{
  message: Message;
  isLastMessage: boolean;
  isLoading: boolean;
  liveActivity: ProcessedEvent[];
  currentOutput?: string;
  onCopy: (text: string) => void;
  copiedMessageId: string | null;
}> = ({
  message,
  isLastMessage,
  isLoading,
  liveActivity,
  currentOutput,
  onCopy,
  copiedMessageId,
}) => {
  const showActivity = isLastMessage && isLoading && liveActivity.length > 0;
  const hasCurrentOutput =
    isLastMessage && currentOutput && currentOutput.trim();

  // For the last message while loading, show current output if available, otherwise show message content
  // Ensure displayContent is always a string
  let displayContent = hasCurrentOutput ? currentOutput : message.content;

  // Validate that displayContent is a string, if not convert it
  if (typeof displayContent !== "string") {
    console.warn(
      "Invalid content type for ReactMarkdown:",
      typeof displayContent,
      displayContent
    );
    try {
      displayContent =
        typeof displayContent === "object"
          ? JSON.stringify(displayContent, null, 2)
          : String(displayContent);
    } catch (error) {
      console.error("Failed to convert content to string:", error);
      displayContent = "[Invalid content - could not render]";
    }
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-[80%]">
        <div className="flex-shrink-0 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          {showActivity && (
            <div className="mb-3 p-3 bg-neutral-800 rounded-lg border border-neutral-700">
              <ActivityTimeline
                processedEvents={liveActivity}
                isLoading={true}
              />
            </div>
          )}
          {displayContent && (
            <div className="bg-neutral-700 text-white rounded-3xl rounded-bl-lg px-4 py-3 relative group">
              <ReactMarkdown components={mdComponents}>
                {displayContent}
              </ReactMarkdown>
              {!isLoading && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => onCopy(message.content)}
                >
                  {copiedMessageId === message.id ? (
                    <CopyCheck className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              )}
              {isLoading && hasCurrentOutput && (
                <div className="absolute bottom-2 right-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Input form for continuing conversation
const ChatInput: React.FC<{
  onSubmit: (task: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}> = ({ onSubmit, onCancel, isLoading }) => {
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim()) return;
    onSubmit(inputValue);
    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isSubmitDisabled = !inputValue.trim() || isLoading;

  return (
    <div className="border-t border-neutral-700 p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Continue the conversation..."
          className="flex-1 min-h-[60px] max-h-[120px] bg-neutral-700 border-neutral-600 text-neutral-100 placeholder-neutral-400 resize-none"
          rows={2}
        />
        <div className="flex flex-col gap-2">
          {isLoading ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={onCancel}
            >
              <StopCircle className="w-4 h-4 mr-2" />
              Stop
            </Button>
          ) : (
            <Button type="submit" disabled={isSubmitDisabled} size="sm">
              <Send className="w-4 h-4 mr-2" />
              Send
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};

// Session info header
const SessionHeader: React.FC<{ sessionInfo: Session }> = ({ sessionInfo }) => {
  return (
    <div className="border-b border-neutral-700 p-4 bg-neutral-900">
      <div className="flex items-center gap-3">
        <Container className="w-5 h-5 text-blue-400" />
        <div className="flex-1">
          <h3 className="font-medium text-neutral-100">
            Session: {sessionInfo.session_id}
          </h3>
          <p className="text-sm text-neutral-400 truncate">
            {sessionInfo.last_task}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              sessionInfo.container_status === "running"
                ? "bg-green-500"
                : "bg-red-500"
            }`}
          />
          <span className="text-xs text-neutral-400">
            {sessionInfo.container_status || "unknown"}
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs text-neutral-500">
          <Clock className="w-3 h-3" />
          {new Date(sessionInfo.created).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export const ChatMessagesView: React.FC<ChatMessagesViewProps> = ({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  currentOutput,
  sessionInfo,
}) => {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      console.error("Failed to copy text:", error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {sessionInfo && <SessionHeader sessionInfo={sessionInfo} />}

      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className="p-4 space-y-4">
          {messages.map((message, index) => {
            const isLastMessage = index === messages.length - 1;

            if (message.type === "human") {
              return <HumanMessageBubble key={message.id} message={message} />;
            } else {
              return (
                <AiMessageBubble
                  key={message.id}
                  message={message}
                  isLastMessage={isLastMessage}
                  isLoading={isLoading}
                  liveActivity={liveActivityEvents}
                  currentOutput={currentOutput}
                  onCopy={(text) => handleCopy(text, message.id)}
                  copiedMessageId={copiedMessageId}
                />
              );
            }
          })}

          {/* Show loading state if no messages yet but loading */}
          {messages.length === 0 && isLoading && (
            <div className="flex justify-start mb-4">
              <div className="flex items-start gap-3 max-w-[80%]">
                <div className="flex-shrink-0 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1">
                  <div className="mb-3 p-3 bg-neutral-800 rounded-lg border border-neutral-700">
                    <ActivityTimeline
                      processedEvents={liveActivityEvents}
                      isLoading={true}
                    />
                  </div>
                  {currentOutput && (
                    <div className="bg-neutral-700 text-white rounded-3xl rounded-bl-lg px-4 py-3">
                      <ReactMarkdown components={mdComponents}>
                        {typeof currentOutput === "string"
                          ? currentOutput
                          : String(currentOutput)}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <ChatInput
        onSubmit={onSubmit}
        onCancel={onCancel}
        isLoading={isLoading}
      />
    </div>
  );
};
