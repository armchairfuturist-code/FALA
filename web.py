#!/usr/bin/env python3
"""Web prototype for FALA — wraps ConversationEngine in a chat UI."""

import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse

from audio import speech_to_text, text_to_speech
from conversation import ConversationEngine

# Invite-code auth: when FALA_INVITE_CODES is set, only holders of valid
# codes can use the app. Each code doubles as a user_id for per-user data.
AUTH_CODES = {c.strip() for c in os.getenv("FALA_INVITE_CODES", "").split(",") if c.strip()}
AUTH_ENABLED = bool(AUTH_CODES)

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


def get_session(request: Request, response: Response) -> SessionState | None:
    """Return this request's SessionState, or None if not authenticated."""
    sid = request.cookies.get(SESSION_COOKIE, "")
    if AUTH_ENABLED:
        if sid not in AUTH_CODES:
            return None
        user_id = sid
    else:
        if not _SESSION_ID_RE.match(sid):
            sid = uuid.uuid4().hex
        user_id = sid
    state = _sessions.get(sid)
    if state is None:
        state = SessionState(user_id=user_id)
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

AUTH_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FALA — Enter Invite Code</title>
<style>
body { font-family: system-ui, sans-serif; background: #f5f5f5;
 display: flex; justify-content: center; min-height: 100vh; margin: 0; }
.box { max-width: 400px; margin: auto; text-align: center; padding: 2rem; }
h1 { font-size: 1.5rem; }
input { padding: 0.5rem; font-size: 1rem; width: 200px;
 border: 1px solid #ddd; border-radius: 6px; }
button { padding: 0.5rem 1rem; font-size: 1rem; border: none;
 border-radius: 6px; background: #1976d2; color: white;
 cursor: pointer; margin-left: 0.5rem; }
#error { color: #d32f3f; margin-top: 0.5rem; }
</style>
</head>
<body>
<div class="box">
<h1>🇵🇹 FALA</h1>
<p>Enter your invite code to start learning European Portuguese:</p>
<form id="auth-form">
<input type="text" id="code" placeholder="Invite code" autofocus />
<button type="submit">Enter</button>
</form>
<p id="error"></p>
</div>
<script>
document.getElementById('auth-form').onsubmit = async (e) => {
 e.preventDefault();
 const code = document.getElementById('code').value.trim();
 const r = await fetch('/auth', {method:'POST',
 headers:{'Content-Type':'application/x-www-form-urlencoded'},
 body:'code='+encodeURIComponent(code)});
 const data = await r.json();
 if (data.ok) location.reload();
 else document.getElementById('error').textContent = data.error || 'Invalid code';
};
</script>
</body>
</html>"""

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
#mic-btn { background: #388e3c; color: white; }
#mic-btn.recording { background: #d32f3f; animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
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
 <button id="mic-btn" onclick="toggleVoice()">🎤</button>
    <button id="send" onclick="sendMessage()">Send</button>
  </div>
</div>
<script>
let started = false;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

function addMsg(text, cls) {
  const el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.textContent = text;
  document.getElementById('chat').appendChild(el);
  el.scrollIntoView({ behavior: 'smooth' });
}

function setStatus(text) {
 document.getElementById('status').textContent = text || '';
 }

 async function startWarmup() {
  document.getElementById('status').textContent = 'Starting warm-up...';
  const r = await fetch('/start', { method: 'POST' });
  const data = await r.json();
  document.getElementById('status').textContent = data.status || '';
  addMsg(data.response, 'tutor');
  started = true;
}
 playTTS(data.response);

async function toggleVoice() {
 if (isRecording) { mediaRecorder.stop(); return; }
 try {
 const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
 audioChunks = [];
 mediaRecorder = new MediaRecorder(stream);
 mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
 mediaRecorder.onstop = handleVoiceInput;
 mediaRecorder.start();
 isRecording = true;
 const btn = document.getElementById('mic-btn');
 btn.textContent = '⏹';
 btn.classList.add('recording');
 setStatus('listening...');
 } catch (e) {
 addMsg('Microphone access denied or unavailable', 'sys');
 }
 }

 async function handleVoiceInput() {
 isRecording = false;
 const btn = document.getElementById('mic-btn');
 btn.textContent = '🎤';
 btn.classList.remove('recording');
 setStatus('transcribing...');
 const blob = new Blob(audioChunks, { type: 'audio/webm' });
 const fd = new FormData();
 fd.append('file', blob, 'voice.webm');
 const r = await fetch('/stt', { method: 'POST', body: fd });
 const data = await r.json();
 if (data.transcript) {
 document.getElementById('input').value = data.transcript;
 setStatus('heard: ' + data.transcript);
 sendMessage();
 } else {
 setStatus(data.error || 'Voice input failed \u2014 type instead');
 }
 }

 async function playTTS(text) {
 setStatus('speaking...');
 try {
 const r = await fetch('/tts', {
 method: 'POST',
 headers: {'Content-Type': 'application/x-www-form-urlencoded'},
 body: 'text=' + encodeURIComponent(text),
 });
 const ct = r.headers.get('content-type') || '';
 if (ct.includes('audio')) {
 const blob = await r.blob();
 const url = URL.createObjectURL(blob);
 const audio = new Audio(url);
 audio.onended = () => { URL.revokeObjectURL(url); setStatus(''); };
 audio.play();
 } else { setStatus(''); }
 } catch (e) { setStatus(''); }
 }

 async function sendMessage() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text || !started) return;
  input.value = '';
  addMsg(text, 'user');
  document.getElementById('send').classList.add('loading');
 setStatus('thinking...');
  const r = await fetch('/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'text=' + encodeURIComponent(text),
  });
  const data = await r.json();
  document.getElementById('send').classList.remove('loading');
  addMsg(data.response, 'tutor');
 setStatus('');
 playTTS(data.response);
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
async def index(request: Request):
    if AUTH_ENABLED:
        sid = request.cookies.get(SESSION_COOKIE, "")
        if sid not in AUTH_CODES:
            return AUTH_PAGE
    return HTML_PAGE


@app.post("/auth")
async def authenticate(response: Response, code: str = Form(...)):
    """Validate an invite code and set the session cookie."""
    code = code.strip()
    if code in AUTH_CODES:
        response.set_cookie(SESSION_COOKIE, code, httponly=True, samesite="lax")
        return {"ok": True}
    return {"ok": False, "error": "Invalid invite code"}


@app.post("/start")
async def start(request: Request, response: Response):
    state = get_session(request, response)
    if state is None:
        return {"response": "Not authenticated.", "status": "auth_required"}
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
    if state is None:
        return {"response": "Not authenticated."}
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
    if state is None:
        return {"stats": "Not authenticated."}
    try:
        eng = get_engine(state)
        return {"stats": eng.get_stats()}
    except Exception as e:
        return {"stats": f"Error: {e}"}


@app.post("/quit")
async def quit_(request: Request, response: Response):
    state = get_session(request, response)
    if state is None:
        return {"response": "Not authenticated."}
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


@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    """Transcribe an audio blob to text (stateless)."""
    suffix = Path(file.filename).suffix if file.filename else ".webm"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(await file.read())
    tmp.close()
    path = Path(tmp.name)
    try:
        transcript = speech_to_text(path)
        return {"transcript": transcript or ""}
    except Exception as e:
        return {"transcript": "", "error": str(e)}
    finally:
        path.unlink(missing_ok=True)


@app.post("/tts")
async def tts(text: str = Form(...)):
    """Synthesize text to audio bytes (stateless)."""
    try:
        path = text_to_speech(text)
        if path is None:
            return {"error": "TTS synthesis failed"}
        content_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
        data = path.read_bytes()
        path.unlink(missing_ok=True)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
