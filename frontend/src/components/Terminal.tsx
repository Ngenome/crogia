import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { TerminalWebSocket } from "@/services/terminalWebSocket";
import type { ShellSession } from "@/types/api";
import "@xterm/xterm/css/xterm.css";

interface TerminalProps {
  shellSession: ShellSession;
  onClose?: () => void;
  onShellDead?: (deadShellId: string) => void;
}

export function Terminal({
  shellSession,
  onClose,
  onShellDead,
}: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const websocketRef = useRef<TerminalWebSocket | null>(null);
  const initializingRef = useRef<boolean>(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  console.log(
    `🖥️ TERMINAL DEBUG: Terminal component rendered for shell ${shellSession.shell_id}`
  );

  const handleShellDead = useCallback(
    (deadShellId: string) => {
      console.log(
        `💀 TERMINAL DEBUG: Shell ${deadShellId} died, notifying parent component`
      );
      if (onShellDead) {
        onShellDead(deadShellId);
      }
    },
    [onShellDead]
  );

  useEffect(() => {
    console.log(
      `🖥️ TERMINAL DEBUG: Initializing terminal for shell ${shellSession.shell_id}`
    );

    // Prevent multiple initializations
    if (initializingRef.current) {
      console.log(
        `🖥️ TERMINAL DEBUG: Already initializing terminal for shell ${shellSession.shell_id}, skipping`
      );
      return;
    }

    if (!terminalRef.current) {
      console.error(
        `🖥️ TERMINAL DEBUG: Terminal ref is null for shell ${shellSession.shell_id}`
      );
      return;
    }

    initializingRef.current = true;

    console.log(
      `🖥️ TERMINAL DEBUG: Creating XTerm instance for shell ${shellSession.shell_id}`
    );

    // Create terminal instance
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
      theme: {
        background: "#1a1a1a",
        foreground: "#ffffff",
        cursor: "#ffffff",
        black: "#000000",
        red: "#cd3131",
        green: "#0dbc79",
        yellow: "#e5e510",
        blue: "#2472c8",
        magenta: "#bc3fbc",
        cyan: "#11a8cd",
        white: "#e5e5e5",
        brightBlack: "#666666",
        brightRed: "#f14c4c",
        brightGreen: "#23d18b",
        brightYellow: "#f5f543",
        brightBlue: "#3b8eea",
        brightMagenta: "#d670d6",
        brightCyan: "#29b8db",
        brightWhite: "#e5e5e5",
      },
      cols: 80,
      rows: 24,
    });

    console.log(
      `🖥️ TERMINAL DEBUG: XTerm instance created for shell ${shellSession.shell_id}`
    );

    // Create addons
    console.log(
      `🖥️ TERMINAL DEBUG: Creating addons for shell ${shellSession.shell_id}`
    );
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    // Load addons
    console.log(
      `🖥️ TERMINAL DEBUG: Loading addons for shell ${shellSession.shell_id}`
    );
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    // Open terminal in the container
    console.log(
      `🖥️ TERMINAL DEBUG: Opening terminal in container for shell ${shellSession.shell_id}`
    );
    term.open(terminalRef.current);

    // Store refs
    xtermRef.current = term;
    fitAddonRef.current = fitAddon;
    console.log(
      `🖥️ TERMINAL DEBUG: Stored terminal refs for shell ${shellSession.shell_id}`
    );

    // Wait a moment for terminal to be fully initialized, then fit
    console.log(
      `🖥️ TERMINAL DEBUG: Scheduling terminal fit for shell ${shellSession.shell_id}`
    );
    setTimeout(() => {
      if (fitAddon && terminalRef.current) {
        try {
          console.log(
            `🖥️ TERMINAL DEBUG: Fitting terminal for shell ${shellSession.shell_id}`
          );
          fitAddon.fit();
          console.log(
            `🖥️ TERMINAL DEBUG: Terminal fitted successfully for shell ${shellSession.shell_id}`
          );
        } catch (e) {
          console.warn(
            `🖥️ TERMINAL DEBUG: Failed to fit terminal for shell ${shellSession.shell_id}:`,
            e
          );
        }
      } else {
        console.warn(
          `🖥️ TERMINAL DEBUG: Cannot fit terminal - missing refs for shell ${shellSession.shell_id}`
        );
      }
    }, 100);

    // Create WebSocket connection
    console.log(
      `🖥️ TERMINAL DEBUG: Creating WebSocket connection for shell ${shellSession.shell_id}`
    );
    const ws = new TerminalWebSocket(handleShellDead);
    websocketRef.current = ws;

    // Handle terminal input
    console.log(
      `🖥️ TERMINAL DEBUG: Setting up terminal input handler for shell ${shellSession.shell_id}`
    );
    term.onData((data) => {
      console.log(
        `🖥️ TERMINAL DEBUG: Terminal input data for shell ${shellSession.shell_id}:`,
        JSON.stringify(data)
      );
      if (ws.isConnected) {
        console.log(
          `🖥️ TERMINAL DEBUG: Sending input data to WebSocket for shell ${shellSession.shell_id}`
        );
        ws.sendInput(data);
      } else {
        console.warn(
          `🖥️ TERMINAL DEBUG: WebSocket not connected, cannot send input for shell ${shellSession.shell_id}`
        );
      }
    });

    // Handle terminal resize
    console.log(
      `🖥️ TERMINAL DEBUG: Setting up terminal resize handler for shell ${shellSession.shell_id}`
    );
    term.onResize(({ cols, rows }) => {
      console.log(
        `🖥️ TERMINAL DEBUG: Terminal resized for shell ${shellSession.shell_id}: ${cols}x${rows}`
      );
      if (ws.isConnected) {
        console.log(
          `🖥️ TERMINAL DEBUG: Sending resize to WebSocket for shell ${shellSession.shell_id}`
        );
        ws.resize(rows, cols);
      } else {
        console.warn(
          `🖥️ TERMINAL DEBUG: WebSocket not connected, cannot send resize for shell ${shellSession.shell_id}`
        );
      }
    });

    // Handle WebSocket events
    console.log(
      `🖥️ TERMINAL DEBUG: Setting up WebSocket event handlers for shell ${shellSession.shell_id}`
    );

    ws.onShellOutput((event) => {
      if (event.type === "shell_output") {
        console.log(
          `🖥️ TERMINAL DEBUG: Received shell output for ${shellSession.shell_id}:`,
          event.data.substring(0, 100)
        );
        term.write(event.data);
      }
    });

    ws.onShellConnected((event) => {
      if (event.type === "shell_connected") {
        console.log(
          `🖥️ TERMINAL DEBUG: Shell connected event for ${shellSession.shell_id}:`,
          event
        );
        setIsConnected(true);
        setError(null);
        term.write(
          `\r\n\x1b[32m✓ Connected to shell ${event.shell_id}\x1b[0m\r\n`
        );
      }
    });

    // Handle all WebSocket events for debugging
    ws.onAny((event) => {
      console.log(
        `🖥️ TERMINAL DEBUG: WebSocket event for shell ${shellSession.shell_id}:`,
        event
      );
    });

    // Connect to shell
    console.log(
      `🖥️ TERMINAL DEBUG: Initiating WebSocket connection for shell ${shellSession.shell_id}`
    );
    ws.connect(shellSession.shell_id)
      .then(() => {
        console.log(
          `🖥️ TERMINAL DEBUG: Successfully connected to shell ${shellSession.shell_id}`
        );
      })
      .catch((err) => {
        console.error(
          `🖥️ TERMINAL DEBUG: Failed to connect to shell ${shellSession.shell_id}:`,
          err
        );
        setError("Failed to connect to shell");
        term.write(
          `\r\n\x1b[31m✗ Failed to connect to shell: ${err.message}\x1b[0m\r\n`
        );
      });

    // Handle window resize
    const handleResize = () => {
      console.log(
        `🖥️ TERMINAL DEBUG: Window resize event for shell ${shellSession.shell_id}`
      );
      if (fitAddon && terminalRef.current) {
        setTimeout(() => {
          try {
            console.log(
              `🖥️ TERMINAL DEBUG: Fitting terminal on window resize for shell ${shellSession.shell_id}`
            );
            fitAddon.fit();
          } catch (e) {
            console.warn(
              `🖥️ TERMINAL DEBUG: Failed to fit terminal on resize for shell ${shellSession.shell_id}:`,
              e
            );
          }
        }, 0);
      }
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      console.log(
        `🖥️ TERMINAL DEBUG: Cleaning up terminal for shell ${shellSession.shell_id}`
      );
      initializingRef.current = false;
      window.removeEventListener("resize", handleResize);
      if (ws) {
        console.log(
          `🖥️ TERMINAL DEBUG: Disconnecting WebSocket for shell ${shellSession.shell_id}`
        );
        ws.disconnect();
      }
      if (term) {
        console.log(
          `🖥️ TERMINAL DEBUG: Disposing terminal for shell ${shellSession.shell_id}`
        );
        term.dispose();
      }
    };
  }, [shellSession.shell_id]);

  // Handle container resize
  useEffect(() => {
    console.log(
      `🖥️ TERMINAL DEBUG: Setting up resize observer for shell ${shellSession.shell_id}`
    );

    const resizeObserver = new ResizeObserver(() => {
      console.log(
        `🖥️ TERMINAL DEBUG: Container resize observed for shell ${shellSession.shell_id}`
      );
      if (fitAddonRef.current && terminalRef.current) {
        setTimeout(() => {
          try {
            console.log(
              `🖥️ TERMINAL DEBUG: Fitting terminal on container resize for shell ${shellSession.shell_id}`
            );
            fitAddonRef.current?.fit();
          } catch (e) {
            console.warn(
              `🖥️ TERMINAL DEBUG: Failed to fit terminal on container resize for shell ${shellSession.shell_id}:`,
              e
            );
          }
        }, 0);
      }
    });

    if (terminalRef.current) {
      console.log(
        `🖥️ TERMINAL DEBUG: Starting resize observation for shell ${shellSession.shell_id}`
      );
      resizeObserver.observe(terminalRef.current);
    }

    return () => {
      console.log(
        `🖥️ TERMINAL DEBUG: Disconnecting resize observer for shell ${shellSession.shell_id}`
      );
      resizeObserver.disconnect();
    };
  }, []);

  const handleClose = () => {
    console.log(
      `🖥️ TERMINAL DEBUG: Close button clicked for shell ${shellSession.shell_id}`
    );
    if (websocketRef.current) {
      console.log(
        `🖥️ TERMINAL DEBUG: Disconnecting WebSocket on close for shell ${shellSession.shell_id}`
      );
      websocketRef.current.disconnect();
    }
    if (onClose) {
      console.log(
        `🖥️ TERMINAL DEBUG: Calling onClose callback for shell ${shellSession.shell_id}`
      );
      onClose();
    }
  };

  return (
    <div className="flex flex-col h-full bg-neutral-900 border border-neutral-700 rounded-lg overflow-hidden">
      {/* Terminal Header */}
      <div className="flex items-center justify-between p-2 bg-neutral-800 border-b border-neutral-700">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-sm text-neutral-300 font-mono">
            Terminal - {shellSession.shell_id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-1">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-xs text-neutral-400">
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>

          {/* Close Button */}
          <button
            onClick={handleClose}
            className="text-neutral-400 hover:text-neutral-200 transition-colors"
            aria-label="Close terminal"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/20 border-b border-red-700 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Terminal Container */}
      <div className="flex-1 p-2">
        <div
          ref={terminalRef}
          className="w-full h-full"
          style={{ minHeight: "200px" }}
        />
      </div>
    </div>
  );
}
