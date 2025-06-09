# Crogia Frontend

A React-based frontend for the Crogia Autonomous Agent Platform. This interface allows you to interact with autonomous development agents running in isolated Docker containers.

## Features

- **Session Management**: Create, view, and manage multiple agent sessions
- **Real-time Communication**: WebSocket integration for live task execution updates
- **Interactive Chat**: Chat-like interface for communicating with agents
- **Activity Timeline**: Visual timeline showing agent activities and tool executions
- **File Operations**: Browse and manage files in agent workspaces
- **Process Monitoring**: View and manage running processes in containers

## Prerequisites

- Node.js 18+
- npm or yarn
- Crogia Backend running on `http://localhost:8000`

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Backend Integration

The frontend connects to the Crogia backend API at:

- **HTTP API**: `http://localhost:8000/api/*`
- **WebSocket**: `ws://localhost:8000/ws/{session_id}`

Make sure the backend is running before starting the frontend.

## Usage

### Creating a New Session

1. Click "New Session" in the sidebar
2. Enter your task description (e.g., "Create a Flask web app with user authentication")
3. Click "Start" to begin execution

### Managing Sessions

- **View Sessions**: All active sessions are listed in the left sidebar
- **Switch Sessions**: Click on any session to switch to it
- **Delete Sessions**: Click the "×" button on a session to delete it
- **Session Status**: Green dot = running container, Red dot = stopped container

### Interacting with Agents

- **Send Messages**: Type in the input field and press Enter or click Send
- **View Progress**: Watch the activity timeline for real-time updates
- **Copy Responses**: Hover over AI messages to see the copy button
- **Cancel Tasks**: Click the Stop button to cancel running tasks

### Real-time Updates

The interface shows live updates including:

- Task started/completed notifications
- Tool executions (file operations, shell commands, etc.)
- Streaming text output from the agent
- Error messages and status updates

## API Integration

The frontend uses these key services:

- **`/src/services/api.ts`**: HTTP API client for REST operations
- **`/src/services/websocket.ts`**: WebSocket client for real-time updates
- **`/src/constants/urls.ts`**: Centralized URL configuration
- **`/src/types/api.ts`**: TypeScript types matching the backend API

## Components

- **`WelcomeScreen`**: Initial landing page for new users
- **`ChatMessagesView`**: Main chat interface with message bubbles
- **`ActivityTimeline`**: Visual timeline of agent activities
- **Session Sidebar**: Session management and navigation

## Configuration

Update `/src/constants/urls.ts` to change backend URLs:

```typescript
export const API_BASE_URL = "http://localhost:8000";
export const WS_BASE_URL = "ws://localhost:8000";
```

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Troubleshooting

### Backend Connection Issues

- Ensure the backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify WebSocket connections in browser dev tools

### Session Issues

- Sessions are tied to Docker containers
- If a container stops, the session becomes inactive
- Delete inactive sessions and create new ones

### Development Issues

- Clear browser cache if seeing stale data
- Check browser console for JavaScript errors
- Ensure all dependencies are installed with `npm install`
