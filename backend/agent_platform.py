# agent_platform.py
# -----------------------------------------------------------------------------
# An autonomous agent runner that can:
#   • explore, understand, plan, and execute complex tasks intelligently  
#   • search files, analyze errors, and make smart decisions
#   • write files, run shell commands with live streaming
#   • launch background servers / long-running commands (start_process)
#   • stop them, list them, and tail their logs
#   • persist process metadata to .processes.json inside each workspace
#   • maintain container sessions and conversation continuity
#   • iteratively improve and adapt based on feedback
#   • work autonomously like an experienced developer
# -----------------------------------------------------------------------------
# USAGE
#   python agent_platform.py              # interactive prompt for tasks
# -----------------------------------------------------------------------------

from __future__ import annotations
import asyncio, json, sys, textwrap, uuid, os, subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import docker
from rich.console import Console
from rich.table import Table
from agents import Agent, Runner, RunConfig, function_tool
from openai.types.responses import ResponseTextDeltaEvent

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
MODEL_NAME = "o4-mini"                   # swap for gpt-4o-mini etc.
BASE_DIRECTORY = Path.home() / "agent_workspaces"
BASE_DIRECTORY.mkdir(parents=True, exist_ok=True)

console = Console()
client = docker.from_env()

# Global session management
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSIONS_FILE = BASE_DIRECTORY / "active_sessions.json"

def get_active_sessions() -> Dict[str, Dict[str, Any]]:
    """Get the active sessions dictionary"""
    return ACTIVE_SESSIONS

def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a session by ID"""
    return ACTIVE_SESSIONS.get(session_id)

# -----------------------------------------------------------------------------
# SYSTEM PROMPT (autonomous, adaptive, intelligent)
# -----------------------------------------------------------------------------
UTC_NOW = datetime.utcnow()
SYSTEM_PROMPT_TEMPLATE = f"""
You are **Dev-Agent**, an autonomous software engineering assistant running inside a fresh Ubuntu 24.04 Docker container. You approach tasks like an experienced developer - exploring, understanding, planning intelligently, and adapting based on feedback.

━━━━━━━━━━━━━━━━━━━━━━━━ CONTAINER CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━
• Container ID: {{container_id}}
• Workspace   : /code   (host-mounted at "{{host_path}}")
• Network     : host-network – servers you start are accessible at http://localhost:PORT
• Base stack  : Ubuntu 24.04 (sudo available, install what you need)

━━━━━━━━━━━━━━━━━━━━━━━━ YOUR APPROACH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**EXPLORE FIRST**: Before diving in, understand what you're working with:
• Use `list_directory` to explore the workspace structure
• Use `search_files` to find relevant code, configs, or documentation
• Read existing files to understand the current state
• Check for existing processes or services

**THINK AND PLAN**: Based on your exploration:
• Understand the requirements and constraints
• Identify dependencies and prerequisites 
• Plan your approach, but stay flexible
• Document your plan in README.md for reference

**EXECUTE INTELLIGENTLY**: 
• Install dependencies as needed (apt, pip, npm, etc.)
• For development servers, use `start_process` and verify they work
• Test each step before moving to the next
• Use `run_shell` with verification commands (curl, ps, ls, etc.)
• Keep a running log of progress in task_log.txt

**ADAPT AND ITERATE**:
• If something fails, diagnose the problem thoroughly
• Use `tail_log` to check process outputs
• Try alternative approaches when needed
• Self-correct and improve as you go

**VERIFY SUCCESS**:
• Test that everything works as expected
• For web apps: verify HTTP responses
• For APIs: test endpoints with curl
• For scripts: run them and check outputs
• Document the final state

━━━━━━━━━━━━━━━━━━━━━━━━ CODING BEST PRACTICES ━━━━━━━━━━━━━━━━━━━━━
• Write clean, maintainable code with good structure
• Use appropriate error handling and logging  
• Pin versions for reproducibility
• Follow language/framework conventions
• Add helpful comments and documentation
• Make services robust and production-ready

━━━━━━━━━━━━━━━━━━━━━━━━ AVAILABLE TOOLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━
File Operations: write_file, append_file, read_file, list_directory
Code/Text Search: search_files, grep_search  
Shell Commands: run_shell (with streaming output)
Process Management: start_process, stop_process, list_processes, tail_log
Analysis: analyze_error, check_ports

━━━━━━━━━━━━━━━━━━━━━━━━ TIME CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• UTC Date : {UTC_NOW.date()}  
• UTC Time : {UTC_NOW.time().strftime('%H:%M:%S')}

Remember: You're autonomous and intelligent. Explore, understand, plan, execute, and adapt. Don't ask for permission - make smart decisions and get the job done effectively.
"""

# -----------------------------------------------------------------------------
# CONTAINER UTILITIES
# -----------------------------------------------------------------------------
BASE_IMAGE = "frdel/agent-zero-run:latest"
def start_container(workdir: Path) -> docker.models.containers.Container:
    try:
        console.print(f"[cyan]Starting container with image: {BASE_IMAGE}")
        console.print(f"[cyan]Mounting workdir: {workdir}")
        
        # Check if Docker is available
        client.ping()
        console.print(f"[cyan]Docker connection verified")
        
        # Try to pull the image if it doesn't exist
        try:
            client.images.get(BASE_IMAGE)
            console.print(f"[cyan]Image {BASE_IMAGE} found locally")
        except docker.errors.ImageNotFound:
            console.print(f"[yellow]Image {BASE_IMAGE} not found locally, pulling...")
            client.images.pull(BASE_IMAGE)
            console.print(f"[green]Image {BASE_IMAGE} pulled successfully")
        
        container = client.containers.run(
            image=BASE_IMAGE,
            command="/bin/bash",
            tty=True,
            working_dir="/code",
            volumes={str(workdir): {"bind": "/code", "mode": "rw"}},
            network_mode="host",   # servers bind directly to host
            detach=True,
        )
        console.print(f"[green]Container started: {container.id}")
        return container
    except Exception as e:
        console.print(f"[red]Error starting container: {e}")
        raise

def stop_container(ctr):      # keep workspace for inspection
    ctr.stop()

# -----------------------------------------------------------------------------
# SESSION MANAGEMENT
# -----------------------------------------------------------------------------
def load_sessions():
    """Load active sessions from disk"""
    global ACTIVE_SESSIONS
    try:
        if SESSIONS_FILE.exists():
            ACTIVE_SESSIONS = json.loads(SESSIONS_FILE.read_text())
        # Clean up stale sessions (containers that no longer exist)
        to_remove = []
        for session_id, session in ACTIVE_SESSIONS.items():
            try:
                client.containers.get(session["container_id"])
            except docker.errors.NotFound:
                to_remove.append(session_id)
        for session_id in to_remove:
            del ACTIVE_SESSIONS[session_id]
        save_sessions()
    except Exception as e:
        console.print(f"[red]Warning: Could not load sessions: {e}")
        ACTIVE_SESSIONS = {}

def save_sessions():
    """Save active sessions to disk"""
    try:
        SESSIONS_FILE.write_text(json.dumps(ACTIVE_SESSIONS, indent=2))
    except Exception as e:
        console.print(f"[red]Warning: Could not save sessions: {e}")

def create_session(task: str) -> tuple[str, Path, docker.models.containers.Container]:
    """Create a new session with container and workspace"""
    try:
        session_id = uuid.uuid4().hex[:8]
        console.print(f"[cyan]Creating session {session_id} for task: {task}")
        
        workdir = BASE_DIRECTORY / f"session_{session_id}"
        workdir.mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan]Created workspace: {workdir}")
        
        ctr = start_container(workdir)
        console.print(f"[cyan]Started container: {ctr.id}")
        
        session = {
            "session_id": session_id,
            "container_id": ctr.id,
            "workdir": str(workdir),
            "created": datetime.utcnow().isoformat() + "Z",
            "last_task": task,
            "conversation_history": [],
            "status": "active"
        }
        
        ACTIVE_SESSIONS[session_id] = session
        console.print(f"[cyan]Added session to ACTIVE_SESSIONS: {session_id}")
        
        save_sessions()
        console.print(f"[cyan]Saved sessions to disk")
        
        console.print(f"[green]🆕 Created session {session_id}")
        return session_id, workdir, ctr
    except Exception as e:
        console.print(f"[red]Error in create_session: {e}")
        raise

def get_session(session_id: str) -> Optional[tuple[Path, docker.models.containers.Container, List]]:
    """Get an existing session"""
    if session_id not in ACTIVE_SESSIONS:
        return None
    
    session = ACTIVE_SESSIONS[session_id]
    try:
        ctr = client.containers.get(session["container_id"])
        workdir = Path(session["workdir"])
        conversation_history = session.get("conversation_history", [])
        return workdir, ctr, conversation_history
    except docker.errors.NotFound:
        # Container no longer exists, remove session
        del ACTIVE_SESSIONS[session_id]
        save_sessions()
        return None

def update_session_conversation(session_id: str, conversation_history: List, last_task: str = None):
    """Update the conversation history for a session"""
    if session_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[session_id]["conversation_history"] = conversation_history
        ACTIVE_SESSIONS[session_id]["last_activity"] = datetime.utcnow().isoformat() + "Z"
        if last_task:
            ACTIVE_SESSIONS[session_id]["last_task"] = last_task
        save_sessions()

def list_active_sessions() -> List[Dict]:
    """List all active sessions"""
    load_sessions()  # Refresh from disk
    active = []
    for session_id, session in ACTIVE_SESSIONS.items():
        try:
            ctr = client.containers.get(session["container_id"])
            session_info = session.copy()
            session_info["container_status"] = ctr.status
            active.append(session_info)
        except docker.errors.NotFound:
            continue
    return active

def cleanup_session(session_id: str):
    """Stop container and clean up session"""
    if session_id in ACTIVE_SESSIONS:
        session = ACTIVE_SESSIONS[session_id]
        try:
            ctr = client.containers.get(session["container_id"])
            ctr.stop()
            console.print(f"[yellow]🛑 Stopped container for session {session_id}")
        except docker.errors.NotFound:
            pass
        del ACTIVE_SESSIONS[session_id]
        save_sessions()
        console.print(f"[red]🗑️  Cleaned up session {session_id}")
    else:
        console.print(f"[red]Session {session_id} not found")

# -----------------------------------------------------------------------------
# STREAMING SHELL COMMANDS
# -----------------------------------------------------------------------------
def stream_exec(ctr, cmd: str, workdir="/code", tty: bool = True) -> str:
    console.rule(f"[cyan]$ {cmd}")
    exec_id = ctr.client.api.exec_create(
        container=ctr.id,
        cmd=["/bin/bash", "-lc", cmd] if tty else cmd,
        workdir=workdir,
        tty=tty,
        stdout=True,
        stderr=True,
    )["Id"]
    stream = ctr.client.api.exec_start(exec_id, stream=True, demux=not tty, tty=tty)
    captured: list[str] = []
    for chunk in stream:
        if isinstance(chunk, tuple):
            out, err = chunk
            if out:
                txt = out.decode(errors="ignore")
                sys.stdout.write(txt); captured.append(txt)
            if err:
                txt = err.decode(errors="ignore")
                sys.stdout.write("\x1b[31m"+txt+"\x1b[0m"); captured.append(txt)
        else:
            txt = chunk.decode(errors="ignore")
            sys.stdout.write(txt); captured.append(txt)
    exit_code = ctr.client.api.exec_inspect(exec_id)["ExitCode"]
    console.print(f"[bold {'green' if exit_code==0 else 'red'}]↳ exit {exit_code}\n")
    return "".join(captured)

# -----------------------------------------------------------------------------
# PROCESS REGISTRY HELPERS
# -----------------------------------------------------------------------------
def reg_path(workdir: Path) -> Path:
    return workdir / ".processes.json"

def load_registry(workdir: Path):
    try:
        return json.loads(reg_path(workdir).read_text())
    except FileNotFoundError:
        return []

def save_registry(workdir: Path, data):
    reg_path(workdir).write_text(json.dumps(data, indent=2))

def add_proc(workdir: Path, record: dict):
    data = load_registry(workdir); data.append(record); save_registry(workdir, data)

def mark_stopped(workdir: Path, pid: int):
    data = load_registry(workdir)
    for p in data:
        if p["pid"] == pid:
            p["status"] = "stopped"; p["ended"] = datetime.utcnow().isoformat()+"Z"
    save_registry(workdir, data)

# -----------------------------------------------------------------------------
# TOOL DEFINITIONS
# -----------------------------------------------------------------------------
@function_tool
def write_file(path: str, content: str) -> dict:
    fp = write_file._workdir / path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content)
    console.print(f"[yellow]📝 wrote {path}")
    return {"status": "ok"}

@function_tool
def append_file(path: str, content: str) -> dict:
    fp = append_file._workdir / path
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "a") as f: f.write(content)
    return {"status": "ok"}

@function_tool
def read_file(path: str) -> dict:
    fp = read_file._workdir / path
    return {"content": fp.read_text()} if fp.exists() else {"error": "not found"}

@function_tool
def run_shell(cmd: str, tty: bool = True) -> dict:
    return {"output": stream_exec(run_shell._container, cmd, tty=tty)}

@function_tool
def start_process(cmd: str) -> dict:
    log_dir = Path(".agent_logs"); log_dir.mkdir(exist_ok=True)
    log_file = f"{log_dir}/{uuid.uuid4().hex}.log"
    stream_exec(start_process._container, f"mkdir -p {log_dir}", tty=False)
    pid = int(
        stream_exec(
            start_process._container,
            f"bash -c 'nohup {cmd} > {log_file} 2>&1 & echo $!'",
            tty=False,
        ).strip().split("\n")[-1]
    )
    rec = {"pid": pid, "cmd": cmd, "log": log_file,
           "started": datetime.utcnow().isoformat()+"Z", "status": "running"}
    add_proc(start_process._workdir, rec)
    console.print(f"[green]🚀 started {cmd} (pid {pid})")
    return rec

@function_tool
def stop_process(pid: int) -> dict:
    stream_exec(stop_process._container, f"kill -15 {pid} || true", tty=False)
    mark_stopped(stop_process._workdir, pid)
    return {"status": f"sent SIGTERM to {pid}"}

@function_tool
def tail_log(pid: int, lines: int = 20) -> dict:
    for p in load_registry(tail_log._workdir):
        if p["pid"] == pid:
            log = stream_exec(tail_log._container,
                              f"tail -n {lines} {p['log']} || true", tty=False)
            return {"log": log}
    return {"error": "pid not tracked"}

@function_tool
def list_processes() -> dict:
    return {"processes": load_registry(list_processes._workdir)}

@function_tool
def list_directory(path: str = ".") -> dict:
    """List contents of a directory with file types and sizes"""
    try:
        fp = list_directory._workdir / path
        if not fp.exists():
            return {"error": f"Directory {path} not found"}
        
        items = []
        for item in fp.iterdir():
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
        
        return {"path": str(path), "items": sorted(items, key=lambda x: (x["type"], x["name"]))}
    except Exception as e:
        return {"error": str(e)}

@function_tool
def search_files(pattern: str, path: str = ".", file_types: str = "*") -> dict:
    """Search for files matching a pattern"""
    try:
        fp = search_files._workdir / path
        if not fp.exists():
            return {"error": f"Path {path} not found"}
        
        # Use find command for powerful file searching
        if file_types == "*":
            cmd = f"find '{fp}' -name '{pattern}' -type f 2>/dev/null | head -50"
        else:
            # Support multiple extensions like "*.py,*.js,*.json"
            extensions = file_types.replace("*.", "").split(",")
            name_parts = " -o ".join([f"-name '*.{ext.strip()}'" for ext in extensions])
            cmd = f"find '{fp}' \\( {name_parts} \\) -name '{pattern}' -type f 2>/dev/null | head -50"
        
        result = stream_exec(search_files._container, cmd, tty=False)
        files = [line.strip().replace(str(search_files._workdir), "").lstrip("/") 
                for line in result.split("\n") if line.strip()]
        
        return {"pattern": pattern, "path": path, "matches": files[:50]}
    except Exception as e:
        return {"error": str(e)}

@function_tool  
def grep_search(pattern: str, path: str = ".", file_types: str = "*.py,*.js,*.json,*.md,*.txt,*.yml,*.yaml") -> dict:
    """Search for text patterns within files"""
    try:
        fp = search_files._workdir / path
        if not fp.exists():
            return {"error": f"Path {path} not found"}
        
        # Build grep command with multiple file types
        extensions = file_types.split(",")
        include_args = " ".join([f"--include='{ext.strip()}'" for ext in extensions])
        cmd = f"grep -rn {include_args} '{pattern}' '{fp}' 2>/dev/null | head -20"
        
        result = stream_exec(grep_search._container, cmd, tty=False)
        matches = []
        for line in result.split("\n"):
            if ":" in line and line.strip():
                try:
                    file_path, line_num, content = line.split(":", 2)
                    # Clean up file path
                    clean_path = file_path.replace(str(grep_search._workdir), "").lstrip("/")
                    matches.append({
                        "file": clean_path,
                        "line": int(line_num),
                        "content": content.strip()
                    })
                except (ValueError, IndexError):
                    continue
        
        return {"pattern": pattern, "path": path, "matches": matches[:20]}
    except Exception as e:
        return {"error": str(e)}

@function_tool
def analyze_error(error_text: str, context: str = "") -> dict:
    """Analyze error messages and suggest solutions"""
    suggestions = []
    
    # Common error patterns and solutions
    error_lower = error_text.lower()
    
    if "permission denied" in error_lower:
        suggestions.append("Try using sudo or check file permissions with ls -la")
    if "command not found" in error_lower:
        suggestions.append("Install the missing package or check if it's in PATH")
    if "connection refused" in error_lower:
        suggestions.append("Check if the service is running and the port is correct")
    if "no such file or directory" in error_lower:
        suggestions.append("Verify the file path exists and check for typos")
    if "port already in use" in error_lower:
        suggestions.append("Use a different port or stop the conflicting process")
    if "module not found" in error_lower:
        suggestions.append("Install the Python package with pip install")
    if "npm err" in error_lower:
        suggestions.append("Try npm install or check package.json for issues")
    
    # Extract useful info
    info = {
        "error_type": "unknown",
        "suggestions": suggestions or ["Check logs and documentation for more details"]
    }
    
    if "error:" in error_lower:
        info["error_type"] = "runtime_error"
    elif "exception" in error_lower:
        info["error_type"] = "exception"
    elif "warning" in error_lower:
        info["error_type"] = "warning"
    
    return {"analysis": info, "original_error": error_text}

@function_tool
def check_ports(start_port: int = 3000, end_port: int = 9000) -> dict:
    """Check which ports are in use in a range"""
    try:
        cmd = f"netstat -tuln | grep -E ':{start_port}|:{end_port}' | head -20"
        result = stream_exec(check_ports._container, cmd, tty=False)
        
        used_ports = []
        for line in result.split("\n"):
            if ":" in line and "LISTEN" in line:
                try:
                    # Extract port number
                    parts = line.split()
                    for part in parts:
                        if ":" in part and part.split(":")[-1].isdigit():
                            port = int(part.split(":")[-1])
                            if start_port <= port <= end_port:
                                used_ports.append(port)
                            break
                except (ValueError, IndexError):
                    continue
        
        # Suggest available ports
        suggested_ports = []
        for port in range(start_port, end_port + 1, 100):
            if port not in used_ports:
                suggested_ports.append(port)
                if len(suggested_ports) >= 5:
                    break
        
        return {
            "used_ports": sorted(set(used_ports)),
            "suggested_ports": suggested_ports[:5],
            "range": f"{start_port}-{end_port}"
        }
    except Exception as e:
        return {"error": str(e)}

# -----------------------------------------------------------------------------
# MAIN RUNNER
# -----------------------------------------------------------------------------
async def run_task_in_session(task: str, session_id: Optional[str] = None) -> str:
    """Run a task in a session, creating new session if needed"""
    load_sessions()
    
    if session_id:
        # Continue existing session
        session_data = get_session(session_id)
        if not session_data:
            console.print(f"[red]Session {session_id} not found or expired")
            return None
        workdir, ctr, conversation_history = session_data
        console.rule(f"[bold]CONTINUING SESSION {session_id}: {task}")
    else:
        # Create new session
        session_id, workdir, ctr = create_session(task)
        conversation_history = []
        console.rule(f"[bold]NEW SESSION {session_id}: {task}")

    # Set up tools with workdir and container references
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
    
    # Create agent directly with tools
    agent = Agent(name="Dev-Agent", instructions=instructions, model=MODEL_NAME, tools=tools)

    # Prepare input - either fresh task or continue conversation
    if conversation_history:
        # Continue existing conversation
        user_input = conversation_history + [{"role": "user", "content": task}]
    else:
        # Fresh start
        user_input = f"User query: {task}"

    # Run the agent
    result = Runner.run_streamed(
        agent,
        user_input,
        max_turns=200,
        run_config=RunConfig(model=MODEL_NAME, workflow_name="autonomous-dev-session"),
    )

    # Stream events and wait for completion
    async for ev in result.stream_events():
        if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
            sys.stdout.write(ev.data.delta); sys.stdout.flush()
        elif ev.type == "run_item_stream_event":
            if ev.item.type == "tool_call_item":
                console.print(f"\n[bold blue]⇢ Tool: {ev.item.raw_item.name}"
                              f"  args={ev.item.raw_item.arguments}")
            elif ev.item.type == "tool_call_output_item":
                console.print("[green]✔ tool complete")

    # Save conversation state for continuation
    # After streaming is done, result contains the final information
    new_conversation_history = result.to_input_list()
    update_session_conversation(session_id, new_conversation_history, task)

    # Show process status
    console.rule("[green]TASK COMPLETE")
    table = Table("PID", "CMD", "STATUS", "LOG")
    for p in load_registry(workdir):
        table.add_row(str(p["pid"]), p["cmd"], p["status"], p["log"])
    if table.rows:
        console.print(table)
    
    console.print(f"\n[cyan]Session {session_id} is still active.")
    console.print(f"[cyan]Workspace: {workdir}")
    console.print(f"[cyan]Container ID: {ctr.short_id}")
    console.print(f"[yellow]Use 'continue {session_id}' to add more tasks to this session")
    console.print(f"[yellow]Use 'cleanup {session_id}' to stop and remove this session")
    
    return session_id

def show_sessions():
    """Display all active sessions"""
    sessions = list_active_sessions()
    if not sessions:
        console.print("[yellow]No active sessions")
        return
    
    table = Table("Session ID", "Created", "Last Task", "Container Status")
    for session in sessions:
        table.add_row(
            session["session_id"],
            session["created"][:19].replace("T", " "),
            session["last_task"][:50] + ("..." if len(session["last_task"]) > 50 else ""),
            session["container_status"]
        )
    console.print(table)

# -----------------------------------------------------------------------------
# CLI INTERFACE
# -----------------------------------------------------------------------------
def print_help():
    """Print available commands"""
    console.print("""
[bold cyan]Available Commands:[/bold cyan]
  • [green]<task>[/green]                    - Run a new task (creates new session)
  • [green]continue <session_id> <task>[/green] - Continue task in existing session  
  • [green]sessions[/green]                  - List all active sessions
  • [green]cleanup <session_id>[/green]      - Stop and remove a session
  • [green]cleanup all[/green]               - Stop and remove all sessions
  • [green]help[/green]                      - Show this help
  • [green]quit[/green] or [green]exit[/green]              - Exit the program

[bold yellow]Examples:[/bold yellow]
  > Create a Flask web app
  > continue a1b2c3d4 Add user authentication
  > sessions
  > cleanup a1b2c3d4
""")

async def interactive_cli():
    """Interactive command-line interface with session management"""
    load_sessions()
    
    console.print("[bold green]🤖 Autonomous Dev-Agent Platform[/bold green]")
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    
    while True:
        try:
            command = input("\n> ").strip()
            if not command:
                continue
                
            parts = command.split(maxsplit=2)
            cmd = parts[0].lower()
            
            if cmd in ["quit", "exit"]:
                console.print("[yellow]Goodbye! 👋")
                break
                
            elif cmd == "help":
                print_help()
                
            elif cmd == "sessions":
                show_sessions()
                
            elif cmd == "cleanup":
                if len(parts) < 2:
                    console.print("[red]Usage: cleanup <session_id> or cleanup all")
                    continue
                    
                if parts[1] == "all":
                    sessions = list_active_sessions()
                    for session in sessions:
                        cleanup_session(session["session_id"])
                    console.print(f"[green]Cleaned up {len(sessions)} sessions")
                else:
                    cleanup_session(parts[1])
                    
            elif cmd == "continue":
                if len(parts) < 3:
                    console.print("[red]Usage: continue <session_id> <task>")
                    continue
                    
                session_id = parts[1]
                task = parts[2]
                await run_task_in_session(task, session_id)
                
            else:
                # Treat as a new task
                task = command
                await run_task_in_session(task)
                
        except EOFError:
            console.print("\n[yellow]Goodbye! 👋")
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}")

def prompt_tasks() -> list[str]:
    """Legacy function for batch task processing"""
    console.print("[bold]Enter tasks (blank line to finish):")
    tasks: list[str] = []
    while True:
        try:
            t = input(" > ").strip()
        except EOFError:
            break
        if not t:
            break
        tasks.append(t)
    return tasks or ["Create a Flask app that says hello"]

async def batch_mode():
    """Run tasks in batch mode (legacy)"""
    for t in prompt_tasks():
        await run_task_in_session(t)

async def main():
    """Main entry point - interactive mode by default"""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        await batch_mode()
    else:
        await interactive_cli()

if __name__ == "__main__":
    asyncio.run(main())
