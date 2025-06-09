Project “Crogia” — Working Notes for the Coding-Agent
Short-term vision (what you’ll code now) - rough draft and ideas for the MVP
A FastAPI backend + Docker containers and a React/Vite frontend that let users:

Start a session → spins up one Docker workspace and one Dev-Agent.

Send a high-level task → the agent plans, writes code, runs shell commands, starts dev servers, verifies success.

Watch in real time → chat stream, activity timeline, and soon an interactive terminal, log tails, and “open preview” links.

Your next objectives (bare-bones, no production hardening):

Area What to implement next
Interactive terminal tabs POST /sessions/{id}/shells → docker exec -it bash, WebSocket /ws/shells/{shell_id}; xterm.js tab in UI.
Process list & log tail UI Use existing /processes data; click to stream tail_log.
Port hint broadcast When start_process prints “Running on …:PORT”, backend pushes port to UI; UI shows “Open URL”.
Idle cleanup Background task stops containers idle > N minutes; updates session state.
Error & reconnect UX Toasts + auto-retry for WS/API errors.
Single-password auth .env password; FastAPI Depends guard on every route.

Everything stays inside Docker containers.

Long-term vision (what this platform eventually becomes)
Many agents, many projects, all at once.
The platform can run dozens of Docker workspaces in parallel.
Each workspace can host several cooperating agents (Backend-Agent, Frontend-Agent, QA-Agent, Docs-Agent, …).

End-to-end autonomy.
Agents handle the entire dev life-cycle: scaffold → code → tests → live preview → docs → packaging.
A workspace is “done” only when all checks pass and a deploy-ready repo / artifact is produced.

Real-time transparency & control.
Every workspace streams commands, diffs, and server ports to the dashboard.
Users can jump into a live terminal, inspect logs, or click a preview URL without leaving the browser.

Multi-tenant simplicity.
One backend schedules multiple Docker containers; users can spin up or tear down workspaces at will.

Focus on the MVP tasks first; they lay the plumbing for the long-range goal of “multiple coding agents building different projects at the same time.”

---

Project “Crogia” — Remaining MVP Work
Short vision
A single FastAPI + Docker backend and a React/Vite frontend that let users spin up multiple autonomous coding agents, watch them code, and interact with each running workspace in real time through browser-based terminals and live logs.

What already works
Create / list / delete sessions (one Docker container + workspace each).

Agents can plan, write files, run streaming shell commands, start/stop background servers, and persist process metadata.

REST + WebSocket backend streams agent progress to the UI.

Frontend shows chat, activity timeline, session sidebar, and raw agent output.

Bare-bones tasks still needed
Area Must-have for MVP
Interactive terminals Backend POST /sessions/{id}/shells → create a docker exec with tty=True and return shell_id.
WS /ws/shells/{shell_id} streams stdin ↔ stdout.
Frontend xterm.js tab pane per shell; open/close; basic send/receive.
Process list UI Surface /processes REST data in the sidebar; click to tail logs (already exposed).
Automatic port hints When an agent calls start_process, backend emits "port_hint": <int> if it sees “Running on http://0.0.0.0:PORT”. UI shows a “Open in new tab” button (localhost:PORT).
Session auto-cleanup Background task: stop containers idle > N minutes; remove workspace if user deleted session via API.
Error toast / reconnection Frontend handles WS drops and shows toast on backend errors.
Basic auth stub .env password, added as Depends on all APIs; skip multi-user complexity.

Nice-to-have (only if time allows)
Terminal resize, Ctrl-C sending, copy-paste helpers.

File-tree viewer (read-only).

Light/dark theme toggle.
