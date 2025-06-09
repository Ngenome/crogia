# Crogia Backend API

FastAPI backend for the autonomous agent platform that provides REST API and WebSocket endpoints for managing agent sessions.

## Features

- **Session Management**: Create, list, get, and delete agent sessions
- **Task Execution**: Execute tasks in agent sessions with real-time streaming
- **Process Management**: Start, stop, and monitor processes within sessions
- **File Operations**: Read, write, and search files in session workspaces
- **WebSocket Support**: Real-time updates and progress streaming
- **Docker Integration**: Containerized agent execution environments

## API Endpoints

### Sessions

- `GET /api/sessions` - List all active sessions
- `POST /api/sessions` - Create a new session
- `GET /api/sessions/{session_id}` - Get session information
- `DELETE /api/sessions/{session_id}` - Delete a session

### Tasks

- `POST /api/sessions/{session_id}/tasks` - Execute a task in a session

### Processes

- `GET /api/sessions/{session_id}/processes` - List session processes
- `POST /api/sessions/{session_id}/processes/{pid}/stop` - Stop a process
- `GET /api/sessions/{session_id}/processes/{pid}/logs` - Get process logs

### Files

- `GET /api/sessions/{session_id}/files` - List files in directory
- `GET /api/sessions/{session_id}/files/content` - Get file content
- `POST /api/sessions/{session_id}/files/content` - Write file content

### Search

- `POST /api/sessions/{session_id}/search/files` - Search for files
- `POST /api/sessions/{session_id}/search/grep` - Search text in files

### Shell

- `POST /api/sessions/{session_id}/shell` - Execute shell commands

### WebSocket

- `WS /ws/{session_id}` - Real-time updates for a session

### Health

- `GET /api/health` - Health check endpoint

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp env.example .env
# Edit .env with your configuration
```

3. Run the server:

```bash
python run.py
```

Or directly with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

Environment variables (see `env.example`):

- `OPENAI_API_KEY`: Your OpenAI API key
- `MODEL_NAME`: AI model to use (default: o4-mini)
- `BASE_DIRECTORY`: Directory for agent workspaces
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: True)
- `ALLOWED_ORIGINS`: CORS allowed origins
- `DOCKER_BASE_IMAGE`: Docker image for agent containers
- `LOG_LEVEL`: Logging level (default: INFO)

## Docker Requirements

The backend requires Docker to be installed and running, as it creates containerized environments for each agent session.

## WebSocket Events

The WebSocket endpoint sends various event types:

- `task_started`: Task execution began
- `text_delta`: Streaming text output from agent
- `tool_call`: Agent is calling a tool
- `tool_complete`: Tool execution completed
- `task_completed`: Task execution finished
- `error`: Error occurred

## Development

The API includes automatic documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
