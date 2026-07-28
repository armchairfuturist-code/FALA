#!/usr/bin/env python3
"""Web prototype for FALA — wraps ConversationEngine in a chat UI."""

import re
import time
import uuid
from dataclasses import dataclass, field

import uvicorn
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse

from conversation import ConversationEngine

SESSION_COOKIE = "fala_session"
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass
class SessionState:
    """Per-browser-session state. user_id binds the session to on-disk data."""

    user_id: str
    engine: ConversationEngine | None = None
    session_started: bool = False
    session_ended: bool = False
    last_active: float = field(default_factory=time.time)


# Keyed by the fala_session cookie.
# TODO: add an idle-session reaper — this dict grows unbounded.
_sessions: dict[str, SessionState] = {}


def get_session(request: Request, response: Response) -> SessionState:
    """Return this request's SessionState, creating it (and a cookie) if needed."""
    sid = request.cookies.get(SESSION_COOKIE, "")
    if not _SESSION_ID_RE.match(sid):
        sid = uuid.uuid4().hex
    state = _sessions.get(sid)
    if state is None:
        # user_id == session id for now; invite-code auth will bind real user ids
        state = SessionState(user_id=sid)
        _sessions[sid] = state
    state.last_active = time.time()
    response.set_cookie(SESSION_COOKIE, sid, httponly=True, samesite="lax")
    return state


def get_engine(state: SessionState) -> ConversationEngine:
    """Return (creating if needed) the engine for this session's user."""
    if state.engine is None:
        try:
            state.engine = ConversationEngine(user_id=state.user_id)
        except ValueError as e:
            raise RuntimeError(str(e)) from e
    return state.engine


app = FastAPI(title="FALA Web")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FALA — European Portuguese Tutor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f5f5f5;
    display: flex; justify-content: center; min-height: 100vh; }
  .app { max-width: 700px; width: 100%; margin: 1rem; display: flex; flex-direction: column; }
  h1 { font-size: 1.3rem; color: #333; margin-bottom: 0.5rem; text-align: center; }
  #status { font-size: 0.85rem; color: #666; text-align: center; margin-bottom: 0.5rem; }
  #chat { flex: 1; background: white; border: 1px solid #ddd;
    border-radius: 8px; padding: 1rem; overflow-y: auto; max-height: 70vh;
    margin-bottom: 0.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
  .msg { padding: 0.5rem 0.75rem; border-radius: 8px; max-width: 85%; }
  .tutor { background: #e3f2fd; align-self: flex-start; }
  .user { background: #e8f5e9; align-self: flex-end; }
  .sys  { background: #fff3e0; align-self: center; font-size: 0.85rem; }
  .input-row { display: flex; gap: 0.5rem; }
  #input { flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 6px; font-size: 1rem; }
  button { padding: 0.5rem 1rem; border: none; border-radius: 6px;
    cursor: pointer; font-size: 1rem; }
  #send { background: #1976d2; color: white; }
  #stats-btn { background: #f57c00; color: white; }
  #quit-btn { background: #d32f2f; color: white; }
  .actions { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
  .loading { opacity: 0.6; pointer-events: none; }
</style>
</head>
<body>
<div class="app">
  <h1>🇵🇹 FALA — European Portuguese Tutor</h1>
  <div id="status">Connecting...</div>
  <div id="chat"></div>
  <div class="actions">
    <button id="stats-btn" onclick="getStats()">📊 Stats</button>
    <button id="quit-btn" onclick="quitSession()">🚪 Quit</button>
  </div>
  <div class="input-row">
    <input id="input" type="text" placeholder="Type your message..." autofocus />
    <button id="send" onclick="sendMessage()">Send</button>
  </div>
</div>
<script>
let started = false;

function addMsg(text, cls) {
  const el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.textContent = text;
  document.getElementById('chat').appendChild(el);
  el.scrollIntoView({ behavior: 'smooth' });
}

async function startWarmup() {
  document.getElementById('status').textContent = 'Starting warm-up...';
  const r = await fetch('/start', { method: 'POST' });
  const data = await r.json();
  document.getElementById('status').textContent = data.status || '';
  addMsg(data.response, 'tutor');
  started = true;
}

async function sendMessage() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text || !started) return;
  input.value = '';
  addMsg(text, 'user');
  document.getElementById('send').classList.add('loading');
  const r = await fetch('/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'text=' + encodeURIComponent(text),
  });
  const data = await r.json();
  document.getElementById('send').classList.remove('loading');
  addMsg(data.response, 'tutor');
}

async function getStats() {
  const r = await fetch('/stats');
  const data = await r.json();
  addMsg(data.stats || 'No stats yet', 'sys');
}

async function quitSession() {
  if (!started) return;
  const r = await fetch('/quit', { method: 'POST' });
  const data = await r.json();
  addMsg(data.response, 'sys');
  started = false;
  document.getElementById('status').textContent = 'Session ended. Refresh to start a new one.';
  document.getElementById('send').disabled = true;
}

window.onload = startWarmup;
document.getElementById('input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/start")
async def start(request: Request, response: Response):
    state = get_session(request, response)
    if state.session_started and not state.session_ended:
        return {
            "response": "Session already started. Use /quit first to start a new one.",
            "status": "already active",
        }
    if state.session_ended:
        # Reset for new session
        state.engine = None
        state.session_ended = False
    try:
        eng = get_engine(state)
        resp = eng.start_warmup()
        state.session_started = True
        return {"response": resp, "status": eng.get_status_report()}
    except Exception as e:
        return {"response": f"Error: {e}", "status": "error"}


@app.post("/message")
async def message(request: Request, response: Response, text: str = Form(...)):
    state = get_session(request, response)
    if not state.session_started or state.session_ended or state.engine is None:
        return {"response": "No active session. Call /start first."}
    eng = state.engine
    try:
        if text.strip().lower() in ("quit", "exit", "sair"):
            result = eng.end_session()
            state.session_ended = True
            state.engine = None
            return {"response": result}
        resp = eng.user_message(text)
        return {"response": resp}
    except Exception as e:
        return {"response": f"Error: {e}"}


@app.get("/stats")
async def stats(request: Request, response: Response):
    state = get_session(request, response)
    try:
        eng = get_engine(state)
        return {"stats": eng.get_stats()}
    except Exception as e:
        return {"stats": f"Error: {e}"}


@app.post("/quit")
async def quit_(request: Request, response: Response):
    state = get_session(request, response)
    if not state.session_started or state.session_ended or state.engine is None:
        return {"response": "No active session to quit."}
    eng = state.engine
    try:
        result = eng.end_session()
        state.session_ended = True
        state.engine = None
        return {"response": result}
    except Exception as e:
        return {"response": f"Error: {e}"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
