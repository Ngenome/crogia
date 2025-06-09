import { useState, useEffect, useCallback } from "react";
import { Terminal } from "./Terminal";
import { api } from "@/services/api";
import type { ShellSession } from "@/types/api";
import { Plus, X, Terminal as TerminalIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface TerminalManagerProps {
  sessionId: string;
  isVisible: boolean;
}

export function TerminalManager({
  sessionId,
  isVisible,
}: TerminalManagerProps) {
  const [shellSessions, setShellSessions] = useState<ShellSession[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  console.log(
    `📋 MANAGER DEBUG: TerminalManager initialized for session ${sessionId}, visible: ${isVisible}`
  );

  // Load existing shell sessions for this session
  const loadShellSessions = useCallback(async () => {
    console.log(
      `📋 MANAGER DEBUG: Loading shell sessions for session ${sessionId}`
    );
    try {
      const response = await api.listShellSessions(sessionId);
      console.log(`📋 MANAGER DEBUG: Received shell sessions:`, response);
      setShellSessions(response.shells);

      // Set active tab to first shell if none selected
      if (response.shells.length > 0 && !activeTab) {
        console.log(
          `📋 MANAGER DEBUG: Setting active tab to first shell: ${response.shells[0].shell_id}`
        );
        setActiveTab(response.shells[0].shell_id);
      } else {
        console.log(
          `📋 MANAGER DEBUG: No shells found or active tab already set (${activeTab})`
        );
      }
    } catch (err) {
      console.error(
        `📋 MANAGER DEBUG: Failed to load shell sessions for ${sessionId}:`,
        err
      );
      setError("Failed to load terminals");
    }
  }, [sessionId, activeTab]);

  // Load shell sessions when component mounts or session changes
  useEffect(() => {
    console.log(
      `📋 MANAGER DEBUG: Effect triggered - isVisible: ${isVisible}, sessionId: ${sessionId}`
    );
    if (isVisible && sessionId) {
      console.log(`📋 MANAGER DEBUG: Calling loadShellSessions`);
      loadShellSessions();
    } else {
      console.log(
        `📋 MANAGER DEBUG: Skipping loadShellSessions (not visible or no sessionId)`
      );
    }
  }, [isVisible, sessionId, loadShellSessions]);

  // Create a new terminal session
  const createTerminal = async () => {
    console.log(
      `📋 MANAGER DEBUG: Creating new terminal for session ${sessionId}`
    );
    setIsLoading(true);
    setError(null);

    try {
      console.log(`📋 MANAGER DEBUG: Calling API to create shell session`);
      const newShell = await api.createShellSession(sessionId);
      console.log(`📋 MANAGER DEBUG: New shell created:`, newShell);

      setShellSessions((prev) => {
        const updated = [...prev, newShell];
        console.log(`📋 MANAGER DEBUG: Updated shell sessions:`, updated);
        return updated;
      });

      console.log(
        `📋 MANAGER DEBUG: Setting active tab to new shell: ${newShell.shell_id}`
      );
      setActiveTab(newShell.shell_id);
    } catch (err) {
      console.error(
        `📋 MANAGER DEBUG: Failed to create terminal for ${sessionId}:`,
        err
      );
      setError("Failed to create terminal");
    } finally {
      setIsLoading(false);
      console.log(`📋 MANAGER DEBUG: Create terminal operation completed`);
    }
  };

  // Close a terminal session
  const closeTerminal = async (shellId: string) => {
    console.log(`📋 MANAGER DEBUG: Closing terminal ${shellId}`);
    try {
      await api.deleteShellSession(shellId);
      console.log(
        `📋 MANAGER DEBUG: Successfully deleted shell session ${shellId}`
      );

      setShellSessions((prev) => {
        const filtered = prev.filter((shell) => shell.shell_id !== shellId);
        console.log(
          `📋 MANAGER DEBUG: Updated shell sessions after deletion:`,
          filtered
        );
        return filtered;
      });

      // If we're closing the active tab, switch to another tab
      if (activeTab === shellId) {
        const remainingSessions = shellSessions.filter(
          (shell) => shell.shell_id !== shellId
        );
        const newActiveTab =
          remainingSessions.length > 0 ? remainingSessions[0].shell_id : null;
        console.log(
          `📋 MANAGER DEBUG: Switching active tab from ${shellId} to ${newActiveTab}`
        );
        setActiveTab(newActiveTab);
      }
    } catch (err) {
      console.error(
        `📋 MANAGER DEBUG: Failed to close terminal ${shellId}:`,
        err
      );
      setError("Failed to close terminal");
    }
  };

  // Handle tab close from Terminal component
  const handleTerminalClose = useCallback((shellId: string) => {
    console.log(
      `📋 MANAGER DEBUG: Handle terminal close called for ${shellId}`
    );
    closeTerminal(shellId);
  }, []);

  // Handle shell death - create new shell to replace the dead one
  const handleShellDead = useCallback(
    async (deadShellId: string) => {
      console.log(
        `💀 MANAGER DEBUG: Shell ${deadShellId} died, creating replacement`
      );

      // Remove the dead shell from our list
      setShellSessions((prev) => {
        const filtered = prev.filter((shell) => shell.shell_id !== deadShellId);
        console.log(
          `💀 MANAGER DEBUG: Removed dead shell ${deadShellId}, remaining:`,
          filtered.map((s) => s.shell_id)
        );
        return filtered;
      });

      // Create a new shell to replace it
      try {
        console.log(
          `💀 MANAGER DEBUG: Creating replacement shell for session ${sessionId}`
        );
        const newShell = await api.createShellSession(sessionId);
        console.log(`💀 MANAGER DEBUG: Replacement shell created:`, newShell);

        setShellSessions((prev) => {
          const updated = [...prev, newShell];
          console.log(
            `💀 MANAGER DEBUG: Added replacement shell:`,
            updated.map((s) => s.shell_id)
          );
          return updated;
        });

        // Switch to the new shell if the dead one was active
        if (activeTab === deadShellId) {
          console.log(
            `💀 MANAGER DEBUG: Setting active tab to replacement shell: ${newShell.shell_id}`
          );
          setActiveTab(newShell.shell_id);
        }
      } catch (err) {
        console.error(
          `💀 MANAGER DEBUG: Failed to create replacement shell for ${deadShellId}:`,
          err
        );
        setError("Failed to create replacement terminal");
      }
    },
    [sessionId, activeTab]
  );

  if (!isVisible) {
    console.log(
      `📋 MANAGER DEBUG: TerminalManager not visible, returning null`
    );
    return null;
  }

  console.log(
    `📋 MANAGER DEBUG: Rendering TerminalManager with ${shellSessions.length} shell sessions, active tab: ${activeTab}`
  );

  return (
    <div className="flex flex-col h-full bg-neutral-900">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-neutral-700">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-5 h-5 text-neutral-300" />
          <h3 className="text-lg font-semibold text-neutral-100">Terminals</h3>
          <span className="text-sm text-neutral-400">
            ({shellSessions.length} active)
          </span>
        </div>

        <Button
          onClick={() => {
            console.log(`📋 MANAGER DEBUG: New Terminal button clicked`);
            createTerminal();
          }}
          disabled={isLoading}
          size="sm"
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-1" />
          New Terminal
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-600 text-white text-sm">
          {error}
          <button
            onClick={() => {
              console.log(`📋 MANAGER DEBUG: Clearing error`);
              setError(null);
            }}
            className="ml-2 text-red-200 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {/* Terminal Tabs */}
      {shellSessions.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <TerminalIcon className="w-12 h-12 text-neutral-500 mx-auto mb-3" />
            <h4 className="text-lg font-medium text-neutral-300 mb-2">
              No Active Terminals
            </h4>
            <p className="text-neutral-500 mb-4">
              Create a new terminal to start interacting with the container
            </p>
            <Button
              onClick={() => {
                console.log(
                  `📋 MANAGER DEBUG: Create Terminal button clicked (empty state)`
                );
                createTerminal();
              }}
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Terminal
            </Button>
          </div>
        </div>
      ) : (
        <Tabs
          value={activeTab || undefined}
          onValueChange={(value) => {
            console.log(`📋 MANAGER DEBUG: Tab changed to ${value}`);
            setActiveTab(value);
          }}
          className="flex-1 flex flex-col"
        >
          <TabsList className="flex-shrink-0 bg-neutral-800 border-b border-neutral-700 rounded-none justify-start overflow-x-auto">
            {shellSessions.map((shell) => (
              <div key={shell.shell_id} className="flex items-center">
                <TabsTrigger
                  value={shell.shell_id}
                  className="data-[state=active]:bg-neutral-700 data-[state=active]:text-neutral-100 text-neutral-300"
                >
                  <TerminalIcon className="w-3 h-3 mr-1" />
                  {shell.shell_id.slice(-8)}
                </TabsTrigger>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    console.log(
                      `📋 MANAGER DEBUG: Close button clicked for shell ${shell.shell_id}`
                    );
                    closeTerminal(shell.shell_id);
                  }}
                  className="ml-1 p-1 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-600 rounded transition-colors"
                  title={`Close ${shell.shell_id}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </TabsList>

          <div className="flex-1">
            {shellSessions.map((shell) => {
              console.log(
                `📋 MANAGER DEBUG: Rendering terminal tab content for shell ${shell.shell_id}`
              );
              return (
                <TabsContent
                  key={shell.shell_id}
                  value={shell.shell_id}
                  className="h-full m-0 p-0"
                >
                  <Terminal
                    shellSession={shell}
                    onClose={() => {
                      console.log(
                        `📋 MANAGER DEBUG: Terminal component called onClose for ${shell.shell_id}`
                      );
                      handleTerminalClose(shell.shell_id);
                    }}
                    onShellDead={handleShellDead}
                  />
                </TabsContent>
              );
            })}
          </div>
        </Tabs>
      )}
    </div>
  );
}
