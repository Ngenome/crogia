import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Loader2,
  Activity,
  Info,
  Search,
  Brain,
  Pen,
  ChevronDown,
  ChevronUp,
  Play,
  CheckCircle,
  AlertCircle,
  Settings,
  Terminal,
  FileText,
  FolderOpen,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";

export interface ProcessedEvent {
  title: string;
  data: string | object | unknown;
  timestamp?: string;
}

interface ActivityTimelineProps {
  processedEvents: ProcessedEvent[];
  isLoading: boolean;
}

export function ActivityTimeline({
  processedEvents,
  isLoading,
}: ActivityTimelineProps) {
  const [isTimelineCollapsed, setIsTimelineCollapsed] =
    useState<boolean>(false);

  const getEventIcon = (title: string, index: number) => {
    const lowerTitle = title.toLowerCase();

    // Loading states
    if (index === processedEvents.length - 1 && isLoading) {
      return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
    }

    // Task lifecycle
    if (lowerTitle.includes("🚀") || lowerTitle.includes("task started")) {
      return <Play className="h-4 w-4 text-green-400" />;
    }
    if (lowerTitle.includes("🎉") || lowerTitle.includes("task completed")) {
      return <CheckCircle className="h-4 w-4 text-green-400" />;
    }
    if (lowerTitle.includes("❌") || lowerTitle.includes("error")) {
      return <AlertCircle className="h-4 w-4 text-red-400" />;
    }

    // Tool operations
    if (lowerTitle.includes("🔧") || lowerTitle.includes("tool")) {
      // Specific tool icons
      if (
        lowerTitle.includes("write_file") ||
        lowerTitle.includes("append_file")
      ) {
        return <FileText className="h-4 w-4 text-blue-400" />;
      }
      if (lowerTitle.includes("read_file")) {
        return <FolderOpen className="h-4 w-4 text-yellow-400" />;
      }
      if (lowerTitle.includes("run_shell") || lowerTitle.includes("shell")) {
        return <Terminal className="h-4 w-4 text-purple-400" />;
      }
      if (lowerTitle.includes("search") || lowerTitle.includes("grep")) {
        return <Search className="h-4 w-4 text-cyan-400" />;
      }
      if (
        lowerTitle.includes("list_directory") ||
        lowerTitle.includes("directory")
      ) {
        return <FolderOpen className="h-4 w-4 text-orange-400" />;
      }
      if (lowerTitle.includes("process")) {
        return <Settings className="h-4 w-4 text-indigo-400" />;
      }
      // Generic tool icon
      return <Wrench className="h-4 w-4 text-blue-400" />;
    }

    // Tool completion
    if (lowerTitle.includes("✅") || lowerTitle.includes("complete")) {
      return <CheckCircle className="h-4 w-4 text-green-400" />;
    }

    // Generic activities
    if (lowerTitle.includes("thinking") || lowerTitle.includes("processing")) {
      return <Brain className="h-4 w-4 text-purple-400" />;
    }
    if (lowerTitle.includes("generating") || lowerTitle.includes("writing")) {
      return <Pen className="h-4 w-4 text-blue-400" />;
    }
    if (lowerTitle.includes("analyzing") || lowerTitle.includes("reflection")) {
      return <Brain className="h-4 w-4 text-indigo-400" />;
    }
    if (lowerTitle.includes("research") || lowerTitle.includes("searching")) {
      return <Search className="h-4 w-4 text-cyan-400" />;
    }

    // Default icon
    return <Activity className="h-4 w-4 text-neutral-400" />;
  };

  const formatEventData = (data: string | object | unknown): string => {
    if (typeof data === "string") {
      // Truncate very long strings but show useful info
      if (data.length > 200) {
        return data.substring(0, 200) + "...";
      }
      return data;
    }

    if (Array.isArray(data)) {
      return data.join(", ");
    }

    if (typeof data === "object") {
      try {
        // Pretty format JSON but keep it concise
        const jsonStr = JSON.stringify(data, null, 2);
        if (jsonStr.length > 200) {
          return JSON.stringify(data).substring(0, 200) + "...";
        }
        return jsonStr;
      } catch {
        return String(data);
      }
    }

    return String(data);
  };

  const getEventColor = (title: string): string => {
    const lowerTitle = title.toLowerCase();

    if (lowerTitle.includes("🚀") || lowerTitle.includes("task started")) {
      return "text-green-300";
    }
    if (lowerTitle.includes("🎉") || lowerTitle.includes("task completed")) {
      return "text-green-300";
    }
    if (lowerTitle.includes("❌") || lowerTitle.includes("error")) {
      return "text-red-300";
    }
    if (lowerTitle.includes("🔧") || lowerTitle.includes("tool")) {
      return "text-blue-300";
    }
    if (lowerTitle.includes("✅") || lowerTitle.includes("complete")) {
      return "text-green-300";
    }

    return "text-neutral-200";
  };

  useEffect(() => {
    if (!isLoading && processedEvents.length !== 0) {
      setIsTimelineCollapsed(true);
    }
  }, [isLoading, processedEvents]);

  return (
    <Card className="border-none rounded-lg bg-neutral-700 max-h-96">
      <CardHeader>
        <CardDescription className="flex items-center justify-between">
          <div
            className="flex items-center justify-start text-sm w-full cursor-pointer gap-2 text-neutral-100"
            onClick={() => setIsTimelineCollapsed(!isTimelineCollapsed)}
          >
            Agent Activity
            {isTimelineCollapsed ? (
              <ChevronDown className="h-4 w-4 mr-2" />
            ) : (
              <ChevronUp className="h-4 w-4 mr-2" />
            )}
            {processedEvents.length > 0 && (
              <span className="ml-auto text-xs text-neutral-400">
                {processedEvents.length} events
              </span>
            )}
          </div>
        </CardDescription>
      </CardHeader>
      {!isTimelineCollapsed && (
        <ScrollArea className="max-h-96 overflow-y-auto">
          <CardContent>
            {isLoading && processedEvents.length === 0 && (
              <div className="relative pl-8 pb-4">
                <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600" />
                <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-600 flex items-center justify-center ring-4 ring-neutral-700">
                  <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />
                </div>
                <div>
                  <p className="text-sm text-neutral-300 font-medium">
                    Initializing agent...
                  </p>
                  <p className="text-xs text-neutral-400 mt-1">
                    Setting up workspace and tools
                  </p>
                </div>
              </div>
            )}
            {processedEvents.length > 0 ? (
              <div className="space-y-0">
                {processedEvents.map((eventItem, index) => (
                  <div key={index} className="relative pl-8 pb-4">
                    {index < processedEvents.length - 1 ||
                    (isLoading && index === processedEvents.length - 1) ? (
                      <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600" />
                    ) : null}
                    <div className="absolute left-0.5 top-2 h-6 w-6 rounded-full bg-neutral-600 flex items-center justify-center ring-4 ring-neutral-700">
                      {getEventIcon(eventItem.title, index)}
                    </div>
                    <div>
                      <p
                        className={`text-sm font-medium mb-0.5 ${getEventColor(
                          eventItem.title
                        )}`}
                      >
                        {eventItem.title}
                      </p>
                      <p className="text-xs text-neutral-300 leading-relaxed">
                        {formatEventData(eventItem.data)}
                      </p>
                      {eventItem.timestamp && (
                        <p className="text-xs text-neutral-500 mt-1">
                          {new Date(eventItem.timestamp).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {isLoading && processedEvents.length > 0 && (
                  <div className="relative pl-8 pb-4">
                    <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-600 flex items-center justify-center ring-4 ring-neutral-700">
                      <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />
                    </div>
                    <div>
                      <p className="text-sm text-neutral-300 font-medium">
                        Processing...
                      </p>
                      <p className="text-xs text-neutral-400">
                        Agent is thinking and executing tools
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : !isLoading ? (
              <div className="flex flex-col items-center justify-center h-full text-neutral-500 pt-10">
                <Info className="h-6 w-6 mb-3" />
                <p className="text-sm">No activity to display.</p>
                <p className="text-xs text-neutral-600 mt-1">
                  Timeline will update during agent execution.
                </p>
              </div>
            ) : null}
          </CardContent>
        </ScrollArea>
      )}
    </Card>
  );
}
