import React from "react";
import { ConversationHistoryItem } from "@/types/api";
import {
  FileText,
  Terminal,
  Search,
  FolderOpen,
  Code,
  Play,
  StopCircle,
  FileSearch,
  Brain,
  Wrench,
  User,
  Bot,
} from "lucide-react";

interface ConversationWorkflowProps {
  conversationHistory: ConversationHistoryItem[];
  sessionId: string;
}

const getToolIcon = (toolName: string) => {
  const iconMap: Record<string, React.ComponentType> = {
    write_file: FileText,
    read_file: FileText,
    append_file: FileText,
    list_directory: FolderOpen,
    search_files: FileSearch,
    grep_search: Search,
    run_shell: Terminal,
    start_process: Play,
    stop_process: StopCircle,
    tail_log: FileText,
    list_processes: Terminal,
    analyze_error: Code,
    check_ports: Terminal,
  };

  return iconMap[toolName] || Wrench;
};

const formatArguments = (args: string): Record<string, any> => {
  try {
    return JSON.parse(args);
  } catch {
    return { raw: args };
  }
};

const formatOutput = (output: string): Record<string, any> => {
  try {
    return JSON.parse(output);
  } catch {
    return { raw: output };
  }
};

export const ConversationWorkflow: React.FC<ConversationWorkflowProps> = ({
  conversationHistory,
  sessionId,
}) => {
  return (
    <div className="space-y-4 p-4 max-w-4xl mx-auto">
      <div className="bg-neutral-800 rounded-lg p-4 border border-neutral-700">
        <h3 className="text-lg font-semibold text-neutral-100 mb-4 flex items-center gap-2">
          <Bot className="w-5 h-5" />
          Agent Workflow for Session: {sessionId}
        </h3>

        <div className="space-y-3">
          {conversationHistory.map((item, index) => {
            // User message
            if ("role" in item && item.role === "user") {
              return (
                <div
                  key={index}
                  className="bg-blue-900/20 rounded-lg p-3 border border-blue-700/30"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-4 h-4 text-blue-400" />
                    <span className="text-sm font-medium text-blue-400">
                      User Request
                    </span>
                  </div>
                  <div className="text-neutral-200 text-sm whitespace-pre-wrap">
                    {item.content}
                  </div>
                </div>
              );
            }

            // Assistant message (final output)
            if ("role" in item && item.role === "assistant") {
              const content = Array.isArray(item.content)
                ? item.content.map((c) => c.text || "").join("\n")
                : "";

              return (
                <div
                  key={index}
                  className="bg-green-900/20 rounded-lg p-3 border border-green-700/30"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="w-4 h-4 text-green-400" />
                    <span className="text-sm font-medium text-green-400">
                      Agent Response
                    </span>
                  </div>
                  <div className="text-neutral-200 text-sm whitespace-pre-wrap">
                    {content}
                  </div>
                </div>
              );
            }

            // Reasoning step
            if ("type" in item && item.type === "reasoning") {
              return (
                <div
                  key={index}
                  className="bg-purple-900/20 rounded-lg p-3 border border-purple-700/30"
                >
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-medium text-purple-400">
                      Thinking...
                    </span>
                    <span className="text-xs text-neutral-400">
                      #{item.id.slice(-8)}
                    </span>
                  </div>
                </div>
              );
            }

            // Function call
            if ("type" in item && item.type === "function_call") {
              const IconComponent = getToolIcon(item.name);
              const args = formatArguments(item.arguments);

              return (
                <div
                  key={index}
                  className="bg-orange-900/20 rounded-lg p-3 border border-orange-700/30"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <IconComponent className="w-4 h-4 text-orange-400" />
                    <span className="text-sm font-medium text-orange-400">
                      Tool: {item.name}
                    </span>
                    <span className="text-xs text-neutral-400">
                      #{item.call_id.slice(-8)}
                    </span>
                  </div>

                  <div className="ml-6 space-y-2">
                    <div>
                      <span className="text-xs font-medium text-neutral-400">
                        Arguments:
                      </span>
                      <div className="mt-1 bg-neutral-900 rounded p-2 text-xs font-mono text-neutral-300">
                        {Object.entries(args).map(([key, value]) => (
                          <div key={key} className="flex gap-2">
                            <span className="text-blue-400">{key}:</span>
                            <span className="text-neutral-200">
                              {typeof value === "string" && value.length > 100
                                ? `${value.substring(0, 100)}...`
                                : JSON.stringify(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            }

            // Function output
            if ("type" in item && item.type === "function_call_output") {
              const output = formatOutput(item.output);

              return (
                <div
                  key={index}
                  className="bg-green-900/20 rounded-lg p-3 border border-green-700/30 ml-6"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-green-400">
                      Tool Output
                    </span>
                    <span className="text-xs text-neutral-400">
                      #{item.call_id.slice(-8)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 rounded p-2 text-xs font-mono text-neutral-300">
                    {Object.entries(output).map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <span className="text-blue-400">{key}:</span>
                        <span className="text-neutral-200">
                          {typeof value === "string" && value.length > 200
                            ? `${value.substring(0, 200)}...`
                            : JSON.stringify(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            }

            // Unknown item type
            return (
              <div
                key={index}
                className="bg-neutral-700/20 rounded-lg p-3 border border-neutral-600/30"
              >
                <div className="text-xs text-neutral-400">
                  Unknown item type: {JSON.stringify(item).substring(0, 100)}...
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
