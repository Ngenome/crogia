import { WS_BASE_URL } from "@/constants/urls";
import type {
  ShellWSEventUnion,
  ShellInputMessage,
  ShellResizeMessage,
} from "@/types/api";

type TerminalEventHandler = (event: ShellWSEventUnion) => void;

export class TerminalWebSocket {
  private ws: WebSocket | null = null;
  private shellId: string | null = null;
  private eventHandlers: Map<string, TerminalEventHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000;
  private onShellDead?: (shellId: string) => void;

  constructor(onShellDead?: (shellId: string) => void) {
    this.onShellDead = onShellDead;
  }

  connect(shellId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log(`🔌 TERMINAL DEBUG: Starting connection to shell ${shellId}`);

      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log(
          `🔌 TERMINAL DEBUG: Existing connection found, disconnecting first`
        );
        this.disconnect();
      }

      this.shellId = shellId;
      const wsUrl = `${WS_BASE_URL}/ws/shells/${shellId}`;
      console.log(`🔌 TERMINAL DEBUG: Connecting to WebSocket URL: ${wsUrl}`);

      try {
        this.ws = new WebSocket(wsUrl);
        console.log(
          `🔌 TERMINAL DEBUG: WebSocket object created for shell ${shellId}`
        );

        this.ws.onopen = () => {
          console.log(
            `🔌 TERMINAL DEBUG: WebSocket connection opened for shell ${shellId}`
          );
          console.log(
            `🔌 TERMINAL DEBUG: Connection state: ${this.connectionState}`
          );
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          console.log(
            `📨 TERMINAL DEBUG: Received message for shell ${shellId}:`,
            event.data
          );
          try {
            const data: ShellWSEventUnion = JSON.parse(event.data);
            console.log(`📨 TERMINAL DEBUG: Parsed message type: ${data.type}`);
            this.handleEvent(data);
          } catch (error) {
            console.error(
              "📨 TERMINAL DEBUG: Failed to parse terminal WebSocket message:",
              error
            );
            console.error("📨 TERMINAL DEBUG: Raw message data:", event.data);
          }
        };

        this.ws.onclose = (event) => {
          console.log(
            `🔌 TERMINAL DEBUG: WebSocket connection closed for shell ${shellId}`
          );
          console.log(`🔌 TERMINAL DEBUG: Close event details:`, {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
          });

          // Check for specific error codes that indicate shell doesn't exist
          if (event.code === 1008 || event.code === 403) {
            console.log(
              `🔌 TERMINAL DEBUG: Shell ${shellId} not found on backend (code: ${event.code})`
            );
            this.handleShellDead();
            return;
          }

          if (
            !event.wasClean &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            console.log(
              `🔌 TERMINAL DEBUG: Connection was not clean, attempting reconnect`
            );
            this.attemptReconnect();
          } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log(
              `🔌 TERMINAL DEBUG: Max reconnect attempts reached for shell ${shellId}`
            );
            this.handleShellDead();
          } else {
            console.log(
              `🔌 TERMINAL DEBUG: Not attempting reconnect (wasClean: ${event.wasClean}, attempts: ${this.reconnectAttempts})`
            );
          }
        };

        this.ws.onerror = (error) => {
          console.error(
            "🔌 TERMINAL DEBUG: WebSocket error for shell",
            shellId,
            error
          );
          console.error(
            "🔌 TERMINAL DEBUG: WebSocket state:",
            this.ws?.readyState
          );
          reject(new Error("Terminal WebSocket connection failed"));
        };
      } catch (error) {
        console.error(
          "🔌 TERMINAL DEBUG: Error creating WebSocket for shell",
          shellId,
          error
        );
        reject(error);
      }
    });
  }

  disconnect(): void {
    console.log(`🔌 TERMINAL DEBUG: Disconnecting from shell ${this.shellId}`);
    if (this.ws) {
      console.log(
        `🔌 TERMINAL DEBUG: Closing WebSocket connection (state: ${this.ws.readyState})`
      );
      this.ws.close();
      this.ws = null;
    }
    this.shellId = null;
    this.reconnectAttempts = 0;
    console.log(`🔌 TERMINAL DEBUG: Disconnect complete`);
  }

  private attemptReconnect(): void {
    if (!this.shellId) {
      console.log(`🔌 TERMINAL DEBUG: No shellId for reconnection`);
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    console.log(
      `🔌 TERMINAL DEBUG: Attempting to reconnect terminal (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`
    );

    setTimeout(() => {
      if (this.shellId) {
        console.log(
          `🔌 TERMINAL DEBUG: Executing reconnection attempt for shell ${this.shellId}`
        );
        this.connect(this.shellId).catch((error) => {
          console.error(
            "🔌 TERMINAL DEBUG: Terminal reconnection failed:",
            error
          );
        });
      } else {
        console.log(`🔌 TERMINAL DEBUG: No shellId available for reconnection`);
      }
    }, delay);
  }

  private handleEvent(event: ShellWSEventUnion): void {
    console.log(
      `🎭 TERMINAL DEBUG: Handling event type: ${event.type} for shell ${this.shellId}`
    );

    // Call handlers for specific event type
    const handlers = this.eventHandlers.get(event.type) || [];
    console.log(
      `🎭 TERMINAL DEBUG: Found ${handlers.length} handlers for event type ${event.type}`
    );

    handlers.forEach((handler, index) => {
      try {
        console.log(
          `🎭 TERMINAL DEBUG: Calling handler ${index} for event ${event.type}`
        );
        handler(event);
      } catch (error) {
        console.error(
          `🎭 TERMINAL DEBUG: Error in terminal event handler ${index} for ${event.type}:`,
          error
        );
      }
    });

    // Call handlers for all events
    const allHandlers = this.eventHandlers.get("*") || [];
    console.log(
      `🎭 TERMINAL DEBUG: Found ${allHandlers.length} global handlers`
    );

    allHandlers.forEach((handler, index) => {
      try {
        console.log(`🎭 TERMINAL DEBUG: Calling global handler ${index}`);
        handler(event);
      } catch (error) {
        console.error(
          `🎭 TERMINAL DEBUG: Error in global terminal event handler ${index}:`,
          error
        );
      }
    });
  }

  // Event subscription methods
  on(eventType: string, handler: TerminalEventHandler): void {
    console.log(
      `🎭 TERMINAL DEBUG: Registering handler for event type: ${eventType}`
    );
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);
    console.log(
      `🎭 TERMINAL DEBUG: Total handlers for ${eventType}: ${
        this.eventHandlers.get(eventType)!.length
      }`
    );
  }

  off(eventType: string, handler: TerminalEventHandler): void {
    console.log(
      `🎭 TERMINAL DEBUG: Removing handler for event type: ${eventType}`
    );
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
        console.log(
          `🎭 TERMINAL DEBUG: Handler removed, remaining: ${handlers.length}`
        );
      } else {
        console.log(`🎭 TERMINAL DEBUG: Handler not found for removal`);
      }
    }
  }

  // Convenience methods
  onShellOutput(handler: TerminalEventHandler): void {
    console.log(`🎭 TERMINAL DEBUG: Registering shell output handler`);
    this.on("shell_output", handler);
  }

  onShellConnected(handler: TerminalEventHandler): void {
    console.log(`🎭 TERMINAL DEBUG: Registering shell connected handler`);
    this.on("shell_connected", handler);
  }

  onAny(handler: TerminalEventHandler): void {
    console.log(`🎭 TERMINAL DEBUG: Registering global event handler`);
    this.on("*", handler);
  }

  // Send input to the shell
  sendInput(data: string): void {
    console.log(
      `📤 TERMINAL DEBUG: Sending input to shell ${this.shellId}:`,
      JSON.stringify(data)
    );
    console.log(`📤 TERMINAL DEBUG: WebSocket state: ${this.connectionState}`);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: ShellInputMessage = {
        type: "shell_input",
        data: data,
      };
      console.log(`📤 TERMINAL DEBUG: Sending message:`, message);
      this.ws.send(JSON.stringify(message));
      console.log(`📤 TERMINAL DEBUG: Input sent successfully`);
    } else {
      console.warn(
        "📤 TERMINAL DEBUG: Terminal WebSocket is not connected, cannot send input"
      );
      console.warn("📤 TERMINAL DEBUG: Current state:", this.connectionState);
    }
  }

  // Send resize command to the shell
  resize(rows: number, cols: number): void {
    console.log(
      `📐 TERMINAL DEBUG: Resizing terminal for shell ${this.shellId} to ${cols}x${rows}`
    );

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: ShellResizeMessage = {
        type: "shell_resize",
        rows: rows,
        cols: cols,
      };
      console.log(`📐 TERMINAL DEBUG: Sending resize message:`, message);
      this.ws.send(JSON.stringify(message));
      console.log(`📐 TERMINAL DEBUG: Resize sent successfully`);
    } else {
      console.warn(
        "📐 TERMINAL DEBUG: Terminal WebSocket is not connected for resize"
      );
      console.warn("📐 TERMINAL DEBUG: Current state:", this.connectionState);
    }
  }

  get isConnected(): boolean {
    const connected = this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    console.log(
      `🔍 TERMINAL DEBUG: Connection check: ${connected} (state: ${this.connectionState})`
    );
    return connected;
  }

  get connectionState(): string {
    if (!this.ws) return "disconnected";

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return "connecting";
      case WebSocket.OPEN:
        return "connected";
      case WebSocket.CLOSING:
        return "closing";
      case WebSocket.CLOSED:
        return "closed";
      default:
        return "unknown";
    }
  }

  private handleShellDead(): void {
    console.log(
      `💀 TERMINAL DEBUG: Shell ${this.shellId} is dead, notifying parent`
    );
    if (this.onShellDead && this.shellId) {
      this.onShellDead(this.shellId);
    }
    this.disconnect();
  }
}
