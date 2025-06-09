# crogia/backend/main.py
# FastAPI backend for the autonomous agent platform
# Provides REST API and WebSocket endpoints for managing agent sessions

from __future__ import annotations
import asyncio
import json
import uuid
import os
import pty
import signal
import threading
import subprocess
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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ============================================================================
# TERMINAL SESSION MANAGEMENT
# ============================================================================

# Global state for shell sessions
ACTIVE_SHELLS: Dict[str, Dict[str, Any]] = {}

class ShellSession:
    def __init__(self, shell_id: str, session_id: str, ctr: docker.models.containers.Container):
        self.shell_id = shell_id
        self.session_id = session_id
        self.container = ctr
        self.exec_id = None
        self.websocket = None
        self.process = None
        self.created_at = datetime.utcnow()
        logger.info(f"🐚 DEBUG: Created ShellSession {shell_id} for session {session_id} with container {ctr.id}")
        
    async def start_shell(self):
        """Start a bash shell in the container"""
        try:
            logger.info(f"🐚 DEBUG: Starting shell {self.shell_id} for container {self.container.id}")
            
            # Check if container is running
            self.container.reload()
            logger.info(f"🐚 DEBUG: Container {self.container.id} status: {self.container.status}")
            
            if self.container.status != 'running':
                logger.error(f"🐚 DEBUG: Container {self.container.id} is not running, status: {self.container.status}")
                return False
            
            # Create exec instance with PTY
            exec_config = {
                "container": self.container.id,
                "cmd": ["/bin/bash", "-l"],
                "stdin": True,
                "stdout": True,
                "stderr": True,
                "tty": True,
                "workdir": "/code"
            }
            logger.info(f"🐚 DEBUG: Creating exec with config: {exec_config}")
            
            self.exec_id = self.container.client.api.exec_create(**exec_config)["Id"]
            
            logger.info(f"🐚 DEBUG: Successfully created exec {self.exec_id} for shell {self.shell_id}")
            return True
        except Exception as e:
            logger.error(f"🐚 DEBUG: Failed to start shell {self.shell_id}: {e}", exc_info=True)
            return False
    
    async def attach_websocket(self, websocket: WebSocket):
        """Attach WebSocket to shell for bidirectional communication"""
        logger.info(f"🔌 DEBUG: Starting WebSocket attachment for shell {self.shell_id}")
        
        if not self.exec_id:
            logger.error(f"🔌 DEBUG: Shell {self.shell_id} not started - no exec_id")
            raise ValueError("Shell not started")
        
        self.websocket = websocket
        logger.info(f"🔌 DEBUG: WebSocket assigned to shell {self.shell_id}")
        
        # Use docker exec command directly via subprocess for better PTY handling
        docker_cmd = [
            "docker", "exec", "-it", self.container.id, "/bin/bash", "-l"
        ]
        logger.info(f"🔌 DEBUG: Using docker command: {' '.join(docker_cmd)}")
        
        try:
            # Start the process with PTY
            logger.info(f"🔌 DEBUG: Creating PTY for shell {self.shell_id}")
            master, slave = pty.openpty()
            logger.info(f"🔌 DEBUG: PTY created - master: {master}, slave: {slave}")
            
            logger.info(f"🔌 DEBUG: Starting subprocess for shell {self.shell_id}")
            self.process = subprocess.Popen(
                docker_cmd,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                preexec_fn=os.setsid
            )
            os.close(slave)
            logger.info(f"🔌 DEBUG: Subprocess started with PID {self.process.pid} for shell {self.shell_id}")
            
            # Send connection confirmation
            logger.info(f"🔌 DEBUG: Sending connection confirmation for shell {self.shell_id}")
            await websocket.send_json({
                "type": "shell_connected",
                "shell_id": self.shell_id,
                "session_id": self.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Connected to shell {self.shell_id}"
            })
            logger.info(f"🔌 DEBUG: Connection confirmation sent for shell {self.shell_id}")
            
            # Start background tasks for bidirectional communication
            async def read_from_shell():
                """Read output from shell and send to WebSocket"""
                logger.info(f"📖 DEBUG: Starting read_from_shell task for shell {self.shell_id}")
                try:
                    while True:
                        # Read from PTY master
                        try:
                            logger.debug(f"📖 DEBUG: Attempting to read from PTY master {master} for shell {self.shell_id}")
                            data = os.read(master, 1024)
                            if not data:
                                logger.info(f"📖 DEBUG: No data read from shell {self.shell_id}, breaking")
                                break
                            
                            logger.debug(f"📖 DEBUG: Read {len(data)} bytes from shell {self.shell_id}: {data[:50]}...")
                            
                            # Send shell output to WebSocket
                            message = {
                                "type": "shell_output",
                                "data": data.decode('utf-8', errors='ignore'),
                                "shell_id": self.shell_id
                            }
                            logger.debug(f"📖 DEBUG: Sending WebSocket message for shell {self.shell_id}")
                            await websocket.send_json(message)
                            logger.debug(f"📖 DEBUG: Successfully sent shell output for shell {self.shell_id}")
                        except OSError as e:
                            logger.warning(f"📖 DEBUG: OSError reading from shell {self.shell_id}: {e}")
                            break
                        except Exception as e:
                            logger.error(f"📖 DEBUG: Error reading from shell {self.shell_id}: {e}")
                            break
                            
                except Exception as e:
                    logger.error(f"📖 DEBUG: Error in read_from_shell for {self.shell_id}: {e}")
                finally:
                    logger.info(f"📖 DEBUG: Closing master PTY {master} for shell {self.shell_id}")
                    try:
                        os.close(master)
                    except Exception as e:
                        logger.warning(f"📖 DEBUG: Error closing master PTY for shell {self.shell_id}: {e}")
            
            async def write_to_shell():
                """Read input from WebSocket and send to shell"""
                logger.info(f"✍️ DEBUG: Starting write_to_shell task for shell {self.shell_id}")
                try:
                    while True:
                        logger.debug(f"✍️ DEBUG: Waiting for WebSocket message for shell {self.shell_id}")
                        message = await websocket.receive_text()
                        logger.debug(f"✍️ DEBUG: Received WebSocket message for shell {self.shell_id}: {message[:100]}...")
                        data = json.loads(message)
                        
                        if data.get("type") == "shell_input":
                            input_data = data.get("data", "")
                            logger.debug(f"✍️ DEBUG: Processing shell_input for shell {self.shell_id}: {repr(input_data)}")
                            try:
                                os.write(master, input_data.encode('utf-8'))
                                logger.debug(f"✍️ DEBUG: Successfully wrote input to shell {self.shell_id}")
                            except OSError as e:
                                logger.warning(f"✍️ DEBUG: OSError writing to shell {self.shell_id}: {e}")
                                break
                            except Exception as e:
                                logger.warning(f"✍️ DEBUG: Failed to send input to shell {self.shell_id}: {e}")
                        elif data.get("type") == "shell_resize":
                            # Handle terminal resize (PTY doesn't support direct resize, 
                            # but we can send stty commands)
                            rows = data.get("rows", 24)
                            cols = data.get("cols", 80)
                            logger.info(f"✍️ DEBUG: Resizing terminal {self.shell_id} to {cols}x{rows}")
                            try:
                                resize_cmd = f"stty rows {rows} cols {cols}\n"
                                os.write(master, resize_cmd.encode('utf-8'))
                                logger.debug(f"✍️ DEBUG: Successfully resized terminal {self.shell_id}")
                            except Exception as e:
                                logger.warning(f"✍️ DEBUG: Failed to resize terminal {self.shell_id}: {e}")
                        else:
                            logger.warning(f"✍️ DEBUG: Unknown message type for shell {self.shell_id}: {data.get('type')}")
                                
                except WebSocketDisconnect:
                    logger.info(f"✍️ DEBUG: WebSocket disconnected for shell {self.shell_id}")
                except Exception as e:
                    logger.error(f"✍️ DEBUG: Error writing to shell {self.shell_id}: {e}")
            
            # Run both tasks concurrently
            await asyncio.gather(
                read_from_shell(),
                write_to_shell(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error in attach_websocket for {self.shell_id}: {e}")
            raise
    
    def cleanup(self):
        """Clean up shell resources"""
        try:
            if self.process and self.process.poll() is None:
                # Send SIGTERM to the process group
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except:
                    pass
                # Wait a bit then force kill
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Error cleaning up shell {self.shell_id}: {e}")

# Global state for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.shell_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session {session_id}")
    
    async def connect_shell(self, websocket: WebSocket, shell_id: str):
        logger.info(f"🔗 DEBUG: Accepting WebSocket connection for shell {shell_id}")
        await websocket.accept()
        self.shell_connections[shell_id] = websocket
        logger.info(f"🔗 DEBUG: Shell WebSocket connected for shell {shell_id}, total shell connections: {len(self.shell_connections)}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"🔗 DEBUG: WebSocket disconnected for session {session_id}")
    
    def disconnect_shell(self, shell_id: str):
        if shell_id in self.shell_connections:
            del self.shell_connections[shell_id]
            logger.info(f"🔗 DEBUG: Shell WebSocket disconnected for shell {shell_id}, remaining connections: {len(self.shell_connections)}")
        else:
            logger.warning(f"🔗 DEBUG: Attempted to disconnect shell {shell_id} but it was not found in connections")
    
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

class ShellSessionCreate(BaseModel):
    session_id: str

class ShellSessionResponse(BaseModel):
    shell_id: str
    session_id: str
    created: str
    status: str

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
# TERMINAL SESSION ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/shells", response_model=ShellSessionResponse)
async def create_shell_session(session_id: str):
    """Create a new shell session for a container"""
    logger.info(f"🔧 DEBUG: API call to create shell session for session {session_id}")
    try:
        # Validate session exists
        logger.info(f"🔧 DEBUG: Validating session {session_id} exists")
        session_data = get_session(session_id)
        if not session_data:
            logger.error(f"🔧 DEBUG: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        workdir, ctr, _ = session_data
        logger.info(f"🔧 DEBUG: Session {session_id} found with container {ctr.id}")
        
        # Generate shell ID
        shell_id = f"shell_{uuid.uuid4().hex[:8]}"
        logger.info(f"🔧 DEBUG: Generated shell_id: {shell_id}")
        
        # Create shell session
        logger.info(f"🔧 DEBUG: Creating ShellSession object for {shell_id}")
        shell_session = ShellSession(shell_id, session_id, ctr)
        
        logger.info(f"🔧 DEBUG: Starting shell for {shell_id}")
        success = await shell_session.start_shell()
        
        if not success:
            logger.error(f"🔧 DEBUG: Failed to start shell {shell_id}")
            raise HTTPException(status_code=500, detail="Failed to start shell")
        
        # Store in global state
        logger.info(f"🔧 DEBUG: Storing shell {shell_id} in ACTIVE_SHELLS")
        ACTIVE_SHELLS[shell_id] = {
            "shell_id": shell_id,
            "session_id": session_id,
            "created": datetime.utcnow().isoformat(),
            "status": "active",
            "shell_session": shell_session
        }
        
        logger.info(f"🔧 DEBUG: Successfully created shell session {shell_id} for session {session_id}")
        logger.info(f"🔧 DEBUG: Total active shells: {len(ACTIVE_SHELLS)}")
        
        return ShellSessionResponse(
            shell_id=shell_id,
            session_id=session_id,
            created=ACTIVE_SHELLS[shell_id]["created"],
            status="active"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔧 DEBUG: Error creating shell session for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/shells")
async def list_shell_sessions(session_id: str):
    """List all shell sessions for a session"""
    try:
        # Validate session exists
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Filter shells for this session
        session_shells = []
        for shell_id, shell_data in ACTIVE_SHELLS.items():
            if shell_data["session_id"] == session_id:
                session_shells.append({
                    "shell_id": shell_id,
                    "session_id": session_id,
                    "created": shell_data["created"],
                    "status": shell_data["status"]
                })
        
        return {"shells": session_shells}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing shells for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/shells/{shell_id}")
async def delete_shell_session(shell_id: str):
    """Delete a shell session"""
    try:
        if shell_id not in ACTIVE_SHELLS:
            raise HTTPException(status_code=404, detail="Shell session not found")
        
        shell_data = ACTIVE_SHELLS[shell_id]
        shell_session = shell_data["shell_session"]
        
        # Cleanup shell
        shell_session.cleanup()
        
        # Remove from global state
        del ACTIVE_SHELLS[shell_id]
        
        # Disconnect WebSocket if connected
        manager.disconnect_shell(shell_id)
        
        logger.info(f"Deleted shell session {shell_id}")
        return {"message": f"Shell session {shell_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shell session {shell_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TERMINAL WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/shells/{shell_id}")
async def shell_websocket_endpoint(websocket: WebSocket, shell_id: str):
    """WebSocket endpoint for interactive shell communication"""
    logger.info(f"🌐 DEBUG: WebSocket connection attempt for shell {shell_id}")
    try:
        # Validate shell exists
        logger.info(f"🌐 DEBUG: Validating shell {shell_id} exists in ACTIVE_SHELLS")
        logger.info(f"🌐 DEBUG: Current ACTIVE_SHELLS keys: {list(ACTIVE_SHELLS.keys())}")
        
        if shell_id not in ACTIVE_SHELLS:
            logger.error(f"🌐 DEBUG: Shell {shell_id} not found in ACTIVE_SHELLS")
            await websocket.close(code=1008, reason="Shell session not found")
            return
        
        shell_data = ACTIVE_SHELLS[shell_id]
        shell_session = shell_data["shell_session"]
        logger.info(f"🌐 DEBUG: Found shell {shell_id} with session {shell_session.session_id}")
        
        # Connect to shell WebSocket
        logger.info(f"🌐 DEBUG: Accepting WebSocket connection for shell {shell_id}")
        await manager.connect_shell(websocket, shell_id)
        logger.info(f"🌐 DEBUG: WebSocket connection accepted for shell {shell_id}")
        
        # Send connection confirmation
        logger.info(f"🌐 DEBUG: Sending initial connection message for shell {shell_id}")
        await websocket.send_json({
            "type": "shell_connected",
            "shell_id": shell_id,
            "session_id": shell_session.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to shell {shell_id}"
        })
        logger.info(f"🌐 DEBUG: Initial connection message sent for shell {shell_id}")
        
        # Start shell communication
        logger.info(f"🌐 DEBUG: Starting shell communication for shell {shell_id}")
        await shell_session.attach_websocket(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"🌐 DEBUG: Shell WebSocket disconnected for {shell_id}")
        manager.disconnect_shell(shell_id)
    except Exception as e:
        logger.error(f"🌐 DEBUG: Shell WebSocket error for {shell_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        except Exception as close_error:
            logger.warning(f"🌐 DEBUG: Error closing WebSocket for shell {shell_id}: {close_error}")
        manager.disconnect_shell(shell_id)

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
            "active_shells": len(ACTIVE_SHELLS),
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