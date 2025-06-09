# Crogia Backend API Documentation

## Overview

The Crogia Backend provides a REST API and WebSocket interface for managing autonomous development agent sessions.

## Base URL

```
http://localhost:8000
```

## Key Features

- Session management (create, list, delete agent sessions)
- Task execution with real-time streaming via WebSocket
- Process management within sessions
- File operations (read, write, search)
- Shell command execution
- Docker container isolation

## Quick Start

1. Start the server: `python run.py`
2. Visit API docs: http://localhost:8000/docs
3. Health check: http://localhost:8000/api/health

## Main Endpoints

### Sessions

- `GET /api/sessions` - List active sessions
- `POST /api/sessions` - Create new session
- `DELETE /api/sessions/{id}` - Delete session

### Tasks

- `POST /api/sessions/{id}/tasks` - Execute task

### WebSocket

- `WS /ws/{session_id}` - Real-time updates

### Files

- `GET /api/sessions/{id}/files` - List files
- `GET /api/sessions/{id}/files/content` - Read file
- `POST /api/sessions/{id}/files/content` - Write file

### Processes

- `GET /api/sessions/{id}/processes` - List processes
- `POST /api/sessions/{id}/processes/{pid}/stop` - Stop process

For complete documentation, see the interactive docs at `/docs` when running.

## Authentication

Currently, no authentication is required. This should be added for production use.

## API Endpoints

### Health Check

#### GET `/api/health`

Check if the API server and Docker are running properly.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "active_sessions": 2,
  "docker_available": true
}
```

### Session Management

#### GET `/api/sessions`

List all active agent sessions.

**Response:**

```json
[
  {
    "session_id": "a1b2c3d4",
    "container_id": "container_abc123",
    "workdir": "/home/user/agent_workspaces/session_a1b2c3d4",
    "created": "2024-01-15T10:00:00.000Z",
    "last_task": "Create a Flask web application",
    "status": "active",
    "container_status": "running"
  }
]
```

#### POST `/api/sessions`

Create a new agent session.

**Request Body:**

```json
{
  "task": "Create a Flask web application with user authentication"
}
```

**Response:**

```json
{
  "session_id": "a1b2c3d4",
  "container_id": "container_abc123",
  "workdir": "/home/user/agent_workspaces/session_a1b2c3d4",
  "created": "2024-01-15T10:00:00.000Z",
  "last_task": "Create a Flask web application with user authentication",
  "status": "active",
  "container_status": "running"
}
```

#### GET `/api/sessions/{session_id}`

Get information about a specific session.

**Response:** Same as POST `/api/sessions`

#### DELETE `/api/sessions/{session_id}`

Stop and delete a session (stops the container and cleans up).

**Response:**

```json
{
  "message": "Session a1b2c3d4 deleted successfully"
}
```

### Task Execution

#### POST `/api/sessions/{session_id}/tasks`

Execute a task in an existing session. The task runs asynchronously and progress is streamed via WebSocket.

**Request Body:**

```json
{
  "task": "Add user authentication to the Flask app"
}
```

**Response:**

```json
{
  "message": "Task started in session a1b2c3d4",
  "task": "Add user authentication to the Flask app"
}
```

### Process Management

#### GET `/api/sessions/{session_id}/processes`

List all processes running in a session.

**Response:**

```json
[
  {
    "pid": 1234,
    "cmd": "python app.py",
    "status": "running",
    "log": ".agent_logs/abc123.log",
    "started": "2024-01-15T10:15:00.000Z"
  }
]
```

#### POST `/api/sessions/{session_id}/processes/{pid}/stop`

Stop a specific process in a session.

**Response:**

```json
{
  "message": "Sent SIGTERM to process 1234"
}
```

#### GET `/api/sessions/{session_id}/processes/{pid}/logs?lines=50`

Get logs for a specific process.

**Query Parameters:**

- `lines` (optional): Number of log lines to retrieve (default: 50)

**Response:**

```json
{
  "logs": "Starting Flask app...\n * Running on http://127.0.0.1:5000\n",
  "pid": 1234
}
```

### File Operations

#### GET `/api/sessions/{session_id}/files?path=.`

List files and directories in the session workspace.

**Query Parameters:**

- `path` (optional): Directory path to list (default: ".")

**Response:**

```json
{
  "path": ".",
  "items": [
    {
      "name": "app.py",
      "type": "file",
      "size": 1024,
      "modified": "2024-01-15T10:20:00.000Z"
    },
    {
      "name": "templates",
      "type": "directory",
      "size": null,
      "modified": "2024-01-15T10:18:00.000Z"
    }
  ]
}
```

#### GET `/api/sessions/{session_id}/files/content?path=app.py`

Get the content of a specific file.

**Query Parameters:**

- `path`: File path to read

**Response:**

```json
{
  "path": "app.py",
  "content": "from flask import Flask\napp = Flask(__name__)\n..."
}
```

#### POST `/api/sessions/{session_id}/files/content`

Write content to a file.

**Request Body:**

```json
{
  "path": "app.py",
  "content": "from flask import Flask\napp = Flask(__name__)\n..."
}
```

**Response:**

```json
{
  "message": "File app.py written successfully"
}
```

### Search Operations

#### POST `/api/sessions/{session_id}/search/files`

Search for files matching a pattern.

**Request Body:**

```json
{
  "pattern": "*.py",
  "path": ".",
  "file_types": "*.py,*.js"
}
```

**Response:**

```json
{
  "pattern": "*.py",
  "path": ".",
  "matches": ["app.py", "models.py", "utils.py"]
}
```

#### POST `/api/sessions/{session_id}/search/grep`

Search for text patterns within files.

**Request Body:**

```json
{
  "pattern": "Flask",
  "path": ".",
  "file_types": "*.py,*.md"
}
```

**Response:**

```json
{
  "pattern": "Flask",
  "path": ".",
  "matches": [
    {
      "file": "app.py",
      "line": 1,
      "content": "from flask import Flask"
    }
  ]
}
```

### Shell Commands

#### POST `/api/sessions/{session_id}/shell`

Execute a shell command in the session container.

**Request Body:**

```json
{
  "cmd": "ls -la",
  "tty": true
}
```

**Response:**

```json
{
  "command": "ls -la",
  "output": "total 8\ndrwxr-xr-x 2 root root 4096 Jan 15 10:00 .\n...",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## WebSocket Interface

### Connection

Connect to: `ws://localhost:8000/ws/{session_id}`

### Event Types

The WebSocket sends JSON messages with different event types:

#### Task Started

```json
{
  "type": "task_started",
  "session_id": "a1b2c3d4",
  "task": "Create a Flask app",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### Text Delta (Streaming Output)

```json
{
  "type": "text_delta",
  "content": "Creating Flask application...",
  "timestamp": "2024-01-15T10:30:01.000Z"
}
```

#### Tool Call

```json
{
  "type": "tool_call",
  "tool_name": "write_file",
  "arguments": { "path": "app.py", "content": "..." },
  "timestamp": "2024-01-15T10:30:02.000Z"
}
```

#### Tool Complete

```json
{
  "type": "tool_complete",
  "timestamp": "2024-01-15T10:30:03.000Z"
}
```

#### Task Completed

```json
{
  "type": "task_completed",
  "session_id": "a1b2c3d4",
  "task": "Create a Flask app",
  "timestamp": "2024-01-15T10:35:00.000Z"
}
```

#### Error

```json
{
  "type": "error",
  "message": "Container not found",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `404`: Resource not found (session, file, etc.)
- `500`: Internal server error

Error response format:

```json
{
  "detail": "Session not found"
}
```

## Interactive Documentation

When the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive API documentation where you can test endpoints directly.

## Example Usage

### Python Client Example

```python
import asyncio
import aiohttp
import websockets
import json

async def create_session_and_run_task():
    async with aiohttp.ClientSession() as session:
        # Create a new session
        task_data = {"task": "Create a simple Flask app"}
        async with session.post("http://localhost:8000/api/sessions", json=task_data) as response:
            session_info = await response.json()
            session_id = session_info["session_id"]
            print(f"Created session: {session_id}")

        # Connect to WebSocket for real-time updates
        uri = f"ws://localhost:8000/ws/{session_id}"
        async with websockets.connect(uri) as websocket:
            # Execute a task
            task_data = {"task": "Add a simple route to the Flask app"}
            async with session.post(f"http://localhost:8000/api/sessions/{session_id}/tasks", json=task_data) as response:
                print("Task started")

            # Listen for updates
            async for message in websocket:
                data = json.loads(message)
                print(f"Event: {data['type']}")
                if data["type"] == "task_completed":
                    break

asyncio.run(create_session_and_run_task())
```

### JavaScript/Frontend Example

```javascript
// Create a new session
const response = await fetch("http://localhost:8000/api/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ task: "Create a React component" }),
});
const session = await response.json();

// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/${session.session_id}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Event:", data.type, data);

  if (data.type === "text_delta") {
    // Stream agent output to UI
    appendToOutput(data.content);
  }
};

// Execute a task
await fetch(`http://localhost:8000/api/sessions/${session.session_id}/tasks`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ task: "Add props to the React component" }),
});
```
