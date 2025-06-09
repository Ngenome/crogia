# crogia/backend/main.py
# FastAPI backend for the autonomous agent platform
# Provides REST API and WebSocket endpoints for managing agent sessions

from __future__ import annotations
import asyncio
import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import docker
from contextlib import asynccontextmanager

# Import our agent platform components
from agent_platform import (
    get_active_sessions, get_session_by_id, BASE_DIRECTORY, MODEL_NAME, SYSTEM_PROMPT_TEMPLATE,
    start_container, stop_container, load_sessions, save_sessions,
    create_session, get_session, update_session_conversation, cleanup_session,
    list_active_sessions, stream_exec, load_registry, BASE_IMAGE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[session_id].remove(conn)

manager = ConnectionManager()

# Pydantic models for API
class TaskRequest(BaseModel):
    task: str
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    container_id: str
    workdir: str
    created: str
    last_task: str
    status: str
    container_status: Optional[str] = None

class ProcessInfo(BaseModel):
    pid: int
    cmd: str
    status: str
    log: str
    started: str

class FileContent(BaseModel):
    path: str
    content: str

class DirectoryListing(BaseModel):
    path: str
    items: List[Dict[str, Any]]

class SearchRequest(BaseModel):
    pattern: str
    path: str = "."
    file_types: str = "*"

class GrepRequest(BaseModel):
    pattern: str
    path: str = "."
    file_types: str = "*.py,*.js,*.json,*.md,*.txt,*.yml,*.yaml"

class ShellCommand(BaseModel):
    cmd: str
    tty: bool = True

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI agent platform...")
    load_sessions()
    yield
    # Shutdown
    logger.info("Shutting down FastAPI agent platform...")

# Create FastAPI app
app = FastAPI(
    title="Autonomous Agent Platform API",
    description="REST API for managing autonomous development agents",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/sessions", response_model=List[SessionResponse])
async def get_sessions():
    """Get all active sessions"""
    try:
        sessions = list_active_sessions()
        return [SessionResponse(**session) for session in sessions]
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions", response_model=SessionResponse)
async def create_new_session(task_request: TaskRequest):
    """Create a new session"""
    try:
        logger.info(f"Creating new session for task: {task_request.task}")
        session_id, workdir, ctr = create_session(task_request.task)
        logger.info(f"Session created with ID: {session_id}")
        
        # Get session info using helper function
        session = get_session_by_id(session_id)
        if not session:
            logger.error(f"Session {session_id} not found after creation")
            # Try to reload sessions from disk
            load_sessions()
            session = get_session_by_id(session_id)
            if not session:
                raise HTTPException(status_code=500, detail=f"Session creation failed - session {session_id} not found")
        
        session = session.copy()
        logger.info(f"Session data: {session}")
        
        # Add container status
        try:
            session["container_status"] = ctr.status
            logger.info(f"Container status: {ctr.status}")
        except Exception as container_error:
            logger.warning(f"Could not get container status: {container_error}")
            session["container_status"] = "unknown"
        
        logger.info(f"Session {session_id} created successfully")
        return SessionResponse(**session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    try:
        session = get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session.copy()
        try:
            client = docker.from_env()
            ctr = client.containers.get(session["container_id"])
            session["container_status"] = ctr.status
        except docker.errors.NotFound:
            session["container_status"] = "not_found"
        
        return SessionResponse(**session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/conversation/full")
async def get_session_conversation_full(session_id: str):
    """Get full conversation history with all tool calls and reasoning steps"""
    try:
        session = get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversation_history = session.get("conversation_history", [])
        
        return {
            "session_id": session_id,
            "conversation_history": conversation_history,
            "last_task": session.get("last_task", ""),
            "total_items": len(conversation_history)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting full conversation for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/conversation")
async def get_session_conversation(session_id: str):
    """Get conversation history for a session"""
    try:
        session = get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversation_history = session.get("conversation_history", [])
        
        # Transform conversation history into a format suitable for the frontend
        messages = []
        for item in conversation_history:
            if isinstance(item, dict):
                role = item.get("role", "")
                content = item.get("content", "")
                
                # Extract text content from complex structures
                if isinstance(content, list):
                    # Handle array of content objects
                    text_parts = []
                    for content_item in content:
                        if isinstance(content_item, dict):
                            if content_item.get("type") == "output_text":
                                text_parts.append(content_item.get("text", ""))
                            elif "text" in content_item:
                                text_parts.append(content_item.get("text", ""))
                        else:
                            text_parts.append(str(content_item))
                    content = "\n".join(text_parts)
                elif isinstance(content, dict):
                    # Handle single content object
                    if content.get("type") == "output_text":
                        content = content.get("text", "")
                    elif "text" in content:
                        content = content.get("text", "")
                    else:
                        content = str(content)
                elif not isinstance(content, str):
                    content = str(content)
                
                if role == "user":
                    messages.append({
                        "type": "human",
                        "content": content,
                        "id": f"user-{len(messages)}"
                    })
                elif role == "assistant":
                    messages.append({
                        "type": "ai", 
                        "content": content,
                        "id": f"ai-{len(messages)}"
                    })
        
        return {
            "session_id": session_id,
            "messages": messages,
            "last_task": session.get("last_task", ""),
            "total_messages": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and stop its container"""
    try:
        session = get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        cleanup_session(session_id)
        return {"message": f"Session {session_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TASK EXECUTION ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/tasks")
async def execute_task(session_id: str, task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Execute a task in a session"""
    try:
        logger.info(f"Executing task in session {session_id}: {task_request.task}")
        
        # Validate session exists
        session_data = get_session(session_id)
        if not session_data:
            logger.error(f"Session {session_id} not found or expired")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")
        
        logger.info(f"Session {session_id} validated, starting task execution")
        
        # Start task execution in background
        background_tasks.add_task(run_task_with_websocket, session_id, task_request.task)
        
        return {"message": f"Task started in session {session_id}", "task": task_request.task}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing task in session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")

async def run_task_with_websocket(session_id: str, task: str):
    """Run a task and send updates via WebSocket"""
    try:
        logger.info(f"Starting WebSocket task execution for session {session_id}")
        
        # Import the agent components here to avoid circular imports
        from agents import Agent, Runner, RunConfig, function_tool
        from openai.types.responses import ResponseTextDeltaEvent
        
        # Get session data
        session_data = get_session(session_id)
        if not session_data:
            error_msg = f"Session {session_id} not found or expired"
            logger.error(error_msg)
            await manager.send_message({
                "type": "error",
                "message": error_msg
            }, session_id)
            return
        
        workdir, ctr, conversation_history = session_data
        
        # Send task start notification
        await manager.send_message({
            "type": "task_started",
            "session_id": session_id,
            "task": task,
            "timestamp": datetime.utcnow().isoformat()
        }, session_id)
        
        # Set up tools (import from agent_platform)
        from agent_platform import (
            write_file, append_file, read_file, run_shell,
            start_process, stop_process, tail_log, list_processes,
            list_directory, search_files, grep_search, analyze_error, check_ports
        )
        
        tools = [
            write_file, append_file, read_file, run_shell,
            start_process, stop_process, tail_log, list_processes,
            list_directory, search_files, grep_search, analyze_error, check_ports
        ]
        
        for t in tools:
            t._workdir = workdir
            t._container = ctr
        
        # Create system prompt
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            container_id=ctr.short_id, host_path=workdir
        )
        instructions = prompt + "\n\n# USER TASK\n" + task + "\n"
        
        # Create agent
        agent = Agent(name="Dev-Agent", instructions=instructions, model=MODEL_NAME, tools=tools)
        
        # Prepare input
        if conversation_history:
            user_input = conversation_history + [{"role": "user", "content": task}]
        else:
            user_input = f"User query: {task}"
        
        # Run the agent
        result = Runner.run_streamed(
            agent,
            user_input,
            max_turns=200,
            run_config=RunConfig(model=MODEL_NAME, workflow_name="autonomous-dev-session"),
        )
        
        # Stream events via WebSocket
        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                await manager.send_message({
                    "type": "text_delta",
                    "content": ev.data.delta,
                    "timestamp": datetime.utcnow().isoformat()
                }, session_id)
            elif ev.type == "run_item_stream_event":
                if ev.item.type == "tool_call_item":
                    await manager.send_message({
                        "type": "tool_call",
                        "tool_name": ev.item.raw_item.name,
                        "arguments": ev.item.raw_item.arguments,
                        "timestamp": datetime.utcnow().isoformat()
                    }, session_id)
                elif ev.item.type == "tool_call_output_item":
                    await manager.send_message({
                        "type": "tool_complete",
                        "timestamp": datetime.utcnow().isoformat()
                    }, session_id)
        
        # Save conversation state
        new_conversation_history = result.to_input_list()
        update_session_conversation(session_id, new_conversation_history, task)
        
        # Send completion notification
        await manager.send_message({
            "type": "task_completed",
            "session_id": session_id,
            "task": task,
            "timestamp": datetime.utcnow().isoformat()
        }, session_id)
        
    except Exception as e:
        logger.error(f"Error running task in session {session_id}: {e}", exc_info=True)
        try:
            await manager.send_message({
                "type": "error",
                "message": f"Task execution failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }, session_id)
        except Exception as ws_error:
            logger.error(f"Failed to send error message via WebSocket: {ws_error}")

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    try:
        # Validate session exists before accepting connection
        session = get_session_by_id(session_id)
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return
        
        await manager.connect(websocket, session_id)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to session {session_id}"
        })
        
        # Keep connection alive and handle any incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back for now (could be used for commands later)
            await websocket.send_json({"type": "echo", "data": data, "timestamp": datetime.utcnow().isoformat()})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        except:
            pass
        manager.disconnect(websocket, session_id)

# ============================================================================
# PROCESS MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/sessions/{session_id}/processes", response_model=List[ProcessInfo])
async def get_session_processes(session_id: str):
    """Get all processes for a session"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, _, _ = session_data
        processes = load_registry(workdir)
        return [ProcessInfo(**proc) for proc in processes]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processes for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/processes/{pid}/stop")
async def stop_session_process(session_id: str, pid: int):
    """Stop a process in a session"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        stream_exec(ctr, f"kill -15 {pid} || true", tty=False)
        
        # Update registry
        from agent_platform import mark_stopped
        mark_stopped(workdir, pid)
        
        return {"message": f"Sent SIGTERM to process {pid}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping process {pid} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/processes/{pid}/logs")
async def get_process_logs(session_id: str, pid: int, lines: int = 50):
    """Get logs for a process"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        
        # Find the process log file
        processes = load_registry(workdir)
        log_file = None
        for proc in processes:
            if proc["pid"] == pid:
                log_file = proc["log"]
                break
        
        if not log_file:
            raise HTTPException(status_code=404, detail="Process not found")
        
        logs = stream_exec(ctr, f"tail -n {lines} {log_file} || echo 'Log file not found'", tty=False)
        return {"logs": logs, "pid": pid}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs for process {pid} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FILE OPERATIONS ENDPOINTS
# ============================================================================

@app.get("/api/sessions/{session_id}/files")
async def list_files(session_id: str, path: str = "."):
    """List files in a directory"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, _, _ = session_data
        target_path = workdir / path
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        items = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except (OSError, PermissionError):
                items.append({"name": item.name, "type": "unknown", "error": "access denied"})
        
        return DirectoryListing(
            path=str(path),
            items=sorted(items, key=lambda x: (x["type"], x["name"]))
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/files/content")
async def get_file_content(session_id: str, path: str):
    """Get content of a file"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, _, _ = session_data
        file_path = workdir / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        content = file_path.read_text()
        return FileContent(path=path, content=content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/files/content")
async def write_file_content(session_id: str, file_content: FileContent):
    """Write content to a file"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, _, _ = session_data
        file_path = workdir / file_content.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_content.content)
        
        return {"message": f"File {file_content.path} written successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/search/files")
async def search_files_endpoint(session_id: str, search_req: SearchRequest):
    """Search for files matching a pattern"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        
        # Use find command for file searching
        if search_req.file_types == "*":
            cmd = f"find '{workdir / search_req.path}' -name '{search_req.pattern}' -type f 2>/dev/null | head -50"
        else:
            extensions = search_req.file_types.replace("*.", "").split(",")
            name_parts = " -o ".join([f"-name '*.{ext.strip()}'" for ext in extensions])
            cmd = f"find '{workdir / search_req.path}' \\( {name_parts} \\) -name '{search_req.pattern}' -type f 2>/dev/null | head -50"
        
        result = stream_exec(ctr, cmd, tty=False)
        files = [line.strip().replace(str(workdir), "").lstrip("/") 
                for line in result.split("\n") if line.strip()]
        
        return {
            "pattern": search_req.pattern,
            "path": search_req.path,
            "matches": files[:50]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching files in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/search/grep")
async def grep_search_endpoint(session_id: str, grep_req: GrepRequest):
    """Search for text patterns within files"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        
        # Build grep command
        extensions = grep_req.file_types.split(",")
        include_args = " ".join([f"--include='{ext.strip()}'" for ext in extensions])
        cmd = f"grep -rn {include_args} '{grep_req.pattern}' '{workdir / grep_req.path}' 2>/dev/null | head -20"
        
        result = stream_exec(ctr, cmd, tty=False)
        matches = []
        for line in result.split("\n"):
            if ":" in line and line.strip():
                try:
                    file_path, line_num, content = line.split(":", 2)
                    clean_path = file_path.replace(str(workdir), "").lstrip("/")
                    matches.append({
                        "file": clean_path,
                        "line": int(line_num),
                        "content": content.strip()
                    })
                except (ValueError, IndexError):
                    continue
        
        return {
            "pattern": grep_req.pattern,
            "path": grep_req.path,
            "matches": matches[:20]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching text in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SHELL COMMAND ENDPOINT
# ============================================================================

@app.post("/api/sessions/{session_id}/shell")
async def execute_shell_command(session_id: str, shell_cmd: ShellCommand):
    """Execute a shell command in a session"""
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        output = stream_exec(ctr, shell_cmd.cmd, tty=shell_cmd.tty)
        
        return {
            "command": shell_cmd.cmd,
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing shell command in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Docker connection
        client = docker.from_env()
        client.ping()
        
        active_sessions = get_active_sessions()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": len(active_sessions),
            "docker_available": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "docker_available": False
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 