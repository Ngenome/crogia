# Crogia - Autonomous Agent Platform

A full-stack platform for managing autonomous development agents with real-time web interface.

## 🏗️ Architecture

```
crogia/
├── backend/          # FastAPI backend with agent management
│   ├── main.py       # FastAPI application with REST API & WebSocket
│   ├── agent_platform.py  # Core agent platform (copied from v1.5.py)
│   ├── config.py     # Configuration management
│   ├── run.py        # Server startup script
│   ├── start.sh      # Bash startup script
│   ├── test_api.py   # API testing script
│   ├── requirements.txt  # Python dependencies
│   ├── env.example   # Environment variables template
│   ├── README.md     # Backend documentation
│   └── API_DOCS.md   # Comprehensive API documentation
└── frontend/         # React/TypeScript frontend (existing)
    ├── src/
    ├── public/
    ├── package.json
    └── ...
```

## 🚀 Features

### Backend (FastAPI)

- **Session Management**: Create, list, and manage agent sessions
- **Real-time Streaming**: WebSocket support for live task execution updates
- **Docker Integration**: Isolated containerized environments for each agent
- **Process Management**: Start, stop, and monitor processes within sessions
- **File Operations**: Read, write, and search files in agent workspaces
- **Shell Commands**: Execute commands in agent containers
- **RESTful API**: Comprehensive REST endpoints for all operations

### Frontend (React/TypeScript)

- Modern React application with TypeScript
- Vite build system for fast development
- Component library integration
- Ready for integration with the backend API

## 🛠️ Quick Start

### Backend Setup

1. **Navigate to backend directory:**

   ```bash
   cd crogia/backend
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment:**

   ```bash
   cp env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

4. **Start the server:**

   ```bash
   python run.py
   ```

   Or use the startup script:

   ```bash
   chmod +x start.sh
   ./start.sh
   ```

5. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health
   - ReDoc: http://localhost:8000/redoc

### Frontend Setup

1. **Navigate to frontend directory:**

   ```bash
   cd crogia/frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Start development server:**

   ```bash
   npm run dev
   ```

4. **Access the frontend:**
   - Development server: http://localhost:5173

## 📡 API Overview

### Core Endpoints

| Method | Endpoint                   | Description          |
| ------ | -------------------------- | -------------------- |
| GET    | `/api/health`              | Health check         |
| GET    | `/api/sessions`            | List active sessions |
| POST   | `/api/sessions`            | Create new session   |
| DELETE | `/api/sessions/{id}`       | Delete session       |
| POST   | `/api/sessions/{id}/tasks` | Execute task         |
| WS     | `/ws/{session_id}`         | Real-time updates    |

### WebSocket Events

The WebSocket connection provides real-time updates:

- `task_started` - Task execution begins
- `text_delta` - Streaming agent output
- `tool_call` - Agent tool execution
- `tool_complete` - Tool execution finished
- `task_completed` - Task finished
- `error` - Error occurred

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Agent Configuration
MODEL_NAME=o4-mini
BASE_DIRECTORY=/tmp/agent_workspaces

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 🐳 Docker Requirements

The backend requires Docker to be installed and running, as it creates containerized environments for each agent session using the `frdel/agent-zero-run:latest` image.

## 🧪 Testing

### Backend API Testing

Run the test script:

```bash
cd crogia/backend
python test_api.py
```

### Manual Testing

1. **Create a session:**

   ```bash
   curl -X POST "http://localhost:8000/api/sessions" \
        -H "Content-Type: application/json" \
        -d '{"task": "Create a simple Flask app"}'
   ```

2. **List sessions:**

   ```bash
   curl "http://localhost:8000/api/sessions"
   ```

3. **Execute a task:**
   ```bash
   curl -X POST "http://localhost:8000/api/sessions/{session_id}/tasks" \
        -H "Content-Type: application/json" \
        -d '{"task": "Add a route to the Flask app"}'
   ```

## 🔗 Integration

### Frontend Integration

The frontend can integrate with the backend using:

1. **HTTP Client** (axios, fetch) for REST API calls
2. **WebSocket Client** for real-time updates
3. **CORS** is configured for localhost:3000 and localhost:5173

Example integration:

```javascript
// Create session
const response = await fetch("http://localhost:8000/api/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ task: "Create a React component" }),
});
const session = await response.json();

// Connect WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/${session.session_id}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle real-time updates
};
```

## 📚 Documentation

- **Backend API**: See `backend/API_DOCS.md` for comprehensive API documentation
- **Interactive Docs**: Visit `/docs` when the server is running
- **Backend README**: See `backend/README.md` for backend-specific details

## 🛣️ Next Steps

1. **Frontend Integration**: Connect the React frontend to the backend API
2. **Authentication**: Add user authentication and authorization
3. **Session Persistence**: Implement session persistence across server restarts
4. **Monitoring**: Add logging, metrics, and monitoring
5. **Deployment**: Containerize and deploy to production
6. **Security**: Add rate limiting, input validation, and security headers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your license here]

---

**Built with ❤️ using FastAPI, React, and Docker**
