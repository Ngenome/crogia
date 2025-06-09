import { WS_ENDPOINTS, WS_EVENT_TYPES } from "@/constants/urls";
import type { WSEventUnion } from "@/types/api";

type EventHandler = (event: WSEventUnion) => void;

export class CrogiaWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private eventHandlers: Map<string, EventHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second

  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.disconnect();
      }

      this.sessionId = sessionId;
      const wsUrl = WS_ENDPOINTS.SESSION_STREAM(sessionId);

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log(`WebSocket connected to session ${sessionId}`);
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WSEventUnion = JSON.parse(event.data);
            this.handleEvent(data);
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };

        this.ws.onclose = (event) => {
          console.log(
            `WebSocket disconnected from session ${sessionId}`,
            event
          );
          if (
            !event.wasClean &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(new Error("WebSocket connection failed"));
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (!this.sessionId) return;

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`
    );

    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId).catch((error) => {
          console.error("Reconnection failed:", error);
        });
      }
    }, delay);
  }

  private handleEvent(event: WSEventUnion): void {
    // Call handlers for specific event type
    const handlers = this.eventHandlers.get(event.type) || [];
    handlers.forEach((handler) => {
      try {
        handler(event);
      } catch (error) {
        console.error(`Error in event handler for ${event.type}:`, error);
      }
    });

    // Call handlers for all events
    const allHandlers = this.eventHandlers.get("*") || [];
    allHandlers.forEach((handler) => {
      try {
        handler(event);
      } catch (error) {
        console.error("Error in global event handler:", error);
      }
    });
  }

  // Event subscription methods
  on(eventType: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);
  }

  off(eventType: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  // Convenience methods for specific event types
  onTaskStarted(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.TASK_STARTED, handler);
  }

  onTextDelta(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.TEXT_DELTA, handler);
  }

  onToolCall(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.TOOL_CALL, handler);
  }

  onToolComplete(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.TOOL_COMPLETE, handler);
  }

  onTaskCompleted(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.TASK_COMPLETED, handler);
  }

  onError(handler: EventHandler): void {
    this.on(WS_EVENT_TYPES.ERROR, handler);
  }

  // Listen to all events
  onAny(handler: EventHandler): void {
    this.on("*", handler);
  }

  // Send message to server (for future use)
  send(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn("WebSocket is not connected");
    }
  }

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
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
}

// Export a singleton instance
export const websocket = new CrogiaWebSocket();
