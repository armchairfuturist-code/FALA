#!/usr/bin/env python3
"""Web app for FALA — wraps ConversationEngine in a chat UI with voice.

Design notes:
- Blocking engine/audio work runs in the threadpool (sync `def` handlers) or
  `asyncio.to_thread` so one slow LLM call cannot stall the event loop.
- In-progress sessions are checkpointed to disk per user, so they survive a
  server restart or a page refresh (`GET /history` restores the transcript).
- Voice endpoints are gated behind the same session auth as everything else.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse

from audio import extract_speech_text, is_cached_audio, speech_to_text, text_to_speech
from config import DATA_DIR
from conversation import ConversationEngine

logger = logging.getLogger("fala.web")

# Invite-code auth: when FALA_INVITE_CODES is set, only holders of valid
# codes can use the app. Each code doubles as a user_id for per-user data.
AUTH_CODES = {c.strip() for c in os.getenv("FALA_INVITE_CODES", "").split(",") if c.strip()}
AUTH_ENABLED = bool(AUTH_CODES)

SESSION_COOKIE = "fala_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 60  # 60 days

# Opaque session tokens: the cookie holds a server-generated random token,
# never a user_id or invite code. user_id is resolved via _session_tokens
# and unknown tokens are rejected — this is what blocks forged-cookie
# impersonation (audit 2026 findings 1 and 3). In-memory only, so a server
# restart invalidates sessions; on-disk data stays keyed by its stable
# user_id and users simply re-authenticate.
# Bounded: an OrderedDict capped at MAX_SESSION_TOKENS (oldest token evicted)
# so a token-flood cannot grow the map without limit.
_session_tokens: OrderedDict[str, str] = OrderedDict()  # token -> user_id
MAX_SESSION_TOKENS = 1000


def _remember_session_token(token: str, user_id: str) -> None:
    _session_tokens[token] = user_id
    _session_tokens.move_to_end(token)
    while len(_session_tokens) > MAX_SESSION_TOKENS:
        _session_tokens.popitem(last=False)


# Upload/TTS limits (audit 2026: unbounded uploads and text lengths DoS the box).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".webm", ".ogg", ".m4a"}
MAX_TTS_CHARS = 4000
MAX_STT_WAV_SECONDS = 120
# Non-wav duration is unknown before decode: bound the work instead — at most
# 2 concurrent transcriptions, 180 s each, so a long .webm cannot wedge the box.
STT_MAX_CONCURRENCY = 2
STT_TIMEOUT_SECONDS = 180
_stt_semaphore: asyncio.Semaphore | None = None


def _stt_limit() -> asyncio.Semaphore:
    global _stt_semaphore
    if _stt_semaphore is None:
        _stt_semaphore = asyncio.Semaphore(STT_MAX_CONCURRENCY)
    return _stt_semaphore


def _wav_duration_seconds(data: bytes) -> float | None:
    """Cheap RIFF header parse for a .wav payload. None = parse failed."""
    try:
        if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            return None
        pos = 12
        byte_rate = None
        while pos + 8 <= len(data):
            chunk_id = data[pos : pos + 4]
            chunk_size = int.from_bytes(data[pos + 4 : pos + 8], "little")
            if chunk_id == b"fmt ":
                byte_rate = int.from_bytes(data[pos + 16 : pos + 20], "little")
            elif chunk_id == b"data":
                if byte_rate:
                    return chunk_size / byte_rate
                return None
            pos += 8 + chunk_size + (chunk_size % 2)
    except Exception:
        return None
    return None


# Per-code brute-force lockout, on top of the per-IP rate limit.
CODE_MAX_FAILURES = int(os.getenv("FALA_CODE_MAX_FAILURES", "5"))
CODE_LOCKOUT_SECONDS = int(os.getenv("FALA_CODE_LOCKOUT_SECONDS", "300"))
# code -> (failures, last_failure, locked_until)
_code_failures: dict[str, tuple[int, float, float]] = {}

# Simple in-memory sliding-window rate limit (per session token, else per IP).
RATE_LIMIT_PER_MIN = int(os.getenv("FALA_RATE_LIMIT_PER_MIN", "30"))
_rate_windows: dict[str, list[float]] = {}
_rate_last_prune: float = 0.0


def _rate_limited(key: str) -> bool:
    """Record a hit for `key`; return True if the caller is over the limit."""
    global _rate_last_prune
    now = time.time()
    if now - _rate_last_prune > 60:
        # Bound memory: drop windows (and expired code lockouts) with no
        # activity inside the sliding window. At most once per minute.
        stale = [k for k, w in _rate_windows.items() if not w or now - w[-1] >= 60]
        for k in stale:
            del _rate_windows[k]
        stale_codes = [
            c for c, (_, _, locked_until) in _code_failures.items() if locked_until < now
        ]
        for c in stale_codes:
            del _code_failures[c]
        _rate_last_prune = now
    window = [t for t in _rate_windows.get(key, []) if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MIN:
        _rate_windows[key] = window
        return True
    window.append(now)
    _rate_windows[key] = window
    return False


def _user_id_for_code(code: str) -> str:
    """Stable per-code user_id that never exposes the code itself."""
    return "invite-" + hashlib.sha256(code.encode()).hexdigest()[:16]


def _code_matches(candidate: str) -> bool:
    cand = candidate.encode()
    return any(hmac.compare_digest(cand, c.encode()) for c in AUTH_CODES)


def _code_locked(code: str) -> bool:
    entry = _code_failures.get(code)
    return bool(entry and entry[2] > time.time())


def _record_code_failure(code: str) -> None:
    now = time.time()
    failures, _, locked_until = _code_failures.get(code, (0, 0.0, 0.0))
    failures += 1
    if failures >= CODE_MAX_FAILURES:
        locked_until = now + CODE_LOCKOUT_SECONDS
    _code_failures[code] = (failures, now, locked_until)


def _clear_code_failures(code: str) -> None:
    _code_failures.pop(code, None)


def _rate_key(request: Request) -> str:
    sid = request.cookies.get(SESSION_COOKIE, "")
    if sid:
        return f"sid:{sid}"
    addr = request.client.host if request.client else "unknown"
    return f"ip:{addr}"


def _checkpoint_exists(user_id: str) -> bool:
    """Cheap existence check for a user's session checkpoint (no dir creation)."""
    if user_id == "default":
        return (DATA_DIR / ConversationEngine.CHECKPOINT_FILENAME).exists()
    return (DATA_DIR / "users" / user_id / ConversationEngine.CHECKPOINT_FILENAME).exists()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    """Per-browser-session state. user_id binds the session to on-disk data.

    Only `engine` is kept in RAM as a cache; the durable truth for an
    in-progress session is the user's checkpoint file on disk.
    """

    user_id: str
    engine: ConversationEngine | None = None
    session_started: bool = False
    session_ended: bool = False
    last_active: float = field(default_factory=time.time)
    # RLock: serializes engine creation/use per session so concurrent requests
    # (two tabs, /message racing /quit) cannot corrupt state. Reentrant so
    # get_engine() can be called while a endpoint-level lock is held.
    lock: threading.RLock = field(default_factory=threading.RLock)


# Keyed by the opaque session token. Entries are rebuilt from disk checkpoints
# after a restart, so this is only a per-process cache — it is safe to drop
# idle entries (see _reap_idle_sessions).
_sessions: dict[str, SessionState] = {}

IDLE_TIMEOUT = 3600  # seconds
_last_prune: float = 0.0


def _reap_idle_sessions():
    """Drop RAM session entries idle too long (checkpoint survives on disk)."""
    global _last_prune
    now = time.time()
    if now - _last_prune < 60:
        return
    _last_prune = now
    stale = [sid for sid, st in _sessions.items() if now - st.last_active > IDLE_TIMEOUT]
    for sid in stale:
        del _sessions[sid]


def get_session(request: Request, response: Response) -> SessionState | None:
    """Return this request's SessionState, or None if not authenticated.

    The cookie is an opaque random token; the user_id it maps to lives only
    in _session_tokens. A cookie value that is not a known token is rejected
    (401 via the None return) and cleared, so a forged cookie can never be
    used as a user_id or filesystem key.
    """
    sid = request.cookies.get(SESSION_COOKIE, "")
    if sid:
        user_id = _session_tokens.get(sid)
        if user_id is None:
            # Unknown/forged token — reject. The expired-cookie header in the
            # exception clears the stale cookie so the client can recover on
            # its next request (delete_cookie on `response` would be lost to
            # the HTTPException error response).
            clear_cookie = f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=lax"
            raise HTTPException(
                status_code=401,
                detail="Not authenticated.",
                headers={"Set-Cookie": clear_cookie},
            )
    elif AUTH_ENABLED:
        return None  # not logged in yet
    else:
        # No-auth mode: mint a fresh opaque token and an unrelated random
        # user_id. The cookie value is meaningless to the server as a key.
        sid = secrets.token_urlsafe(32)
        user_id = uuid.uuid4().hex
        _remember_session_token(sid, user_id)
    state = _sessions.get(sid)
    if state is None:
        state = SessionState(user_id=user_id)
        state.session_started = _checkpoint_exists(user_id)
        _sessions[sid] = state
    state.last_active = time.time()
    _reap_idle_sessions()
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        httponly=True,
        samesite="lax",
        # Conservative scheme check — not a substitute for token opacity
        # (the real fix): the token is random and server-side, so stealing
        # it requires an active session hijack, not cookie forgery.
        secure=_is_secure(request),
        max_age=COOKIE_MAX_AGE,
    )
    return state


def _is_secure(request: Request) -> bool:
    """True behind TLS directly or via a proxy (X-Forwarded-Proto)."""
    if request.url.scheme == "https":
        return True
    return request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"


def get_engine(state: SessionState) -> ConversationEngine:
    """Return (creating if needed) the engine for this session's user.

    If the session is already active on disk (checkpoint), the engine is
    restored from it so the conversation continues where it left off.
    Serialized on the session lock (RLock — safe to call inside one).
    """
    with state.lock:
        if state.engine is None:
            try:
                state.engine = ConversationEngine(user_id=state.user_id)
                if state.session_started:
                    state.engine.load_checkpoint()
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
  .msg { padding: 0.5rem 0.75rem; border-radius: 8px; max-width: 85%; white-space: pre-wrap; }
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
.replay-btn { background: transparent; border: none; cursor: pointer;
    font-size: 0.85rem; margin-left: 0.5rem; padding: 0 0.25rem; }
#tts-btn { background: #607d8b; color: white; }
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
    <button id="tts-btn" onclick="toggleTTS()">🔊 TTS on</button>
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
let ttsEnabled = localStorage.getItem('fala_tts') !== 'off';
const audioCache = {}; // spoken text -> object URL (cached per message)

function addMsg(text, cls, speech) {
  const el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.textContent = text;
  if (cls === 'tutor') {
    const btn = document.createElement('button');
    btn.className = 'replay-btn';
    btn.textContent = '▶';
    btn.title = 'Replay speech';
    btn.onclick = () => playTTS(speech || text);
    el.appendChild(btn);
  }
  document.getElementById('chat').appendChild(el);
  el.scrollIntoView({ behavior: 'smooth' });
}

function ttsLabel(on) {
  return on ? '🔊 TTS on' : '🔇 TTS off';
}

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  localStorage.setItem('fala_tts', ttsEnabled ? 'on' : 'off');
  document.getElementById('tts-btn').textContent = ttsLabel(ttsEnabled);
}

function setStatus(text) {
 document.getElementById('status').textContent = text || '';
 }

async function api(url, opts) {
  const r = await fetch(url, opts || {});
  let data = null;
  try { data = await r.json(); } catch (e) { /* non-JSON response */ }
  if (!r.ok) {
    addMsg((data && data.detail) || ('Request failed (' + r.status + ')'), 'sys');
    return null;
  }
  return data;
}

async function startWarmup() {
  document.getElementById('status').textContent = 'Starting warm-up...';
  const data = await api('/start', { method: 'POST' });
  if (!data) return;
  document.getElementById('status').textContent = data.status || '';
  if (data.resumed) {
    const hist = await api('/history');
    if (hist && Array.isArray(hist.messages)) {
      for (const m of hist.messages) {
        addMsg(m.content, m.role === 'user' ? 'user' : 'tutor', m.speech);
      }
    }
    setStatus('Session resumed.');
  } else {
    addMsg(data.response, 'tutor');
  }
  started = true;
}

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
 const data = await api('/stt', { method: 'POST', body: fd });
 if (!data) return;
 if (data.transcript) {
 document.getElementById('input').value = data.transcript;
 setStatus('heard: ' + data.transcript);
 sendMessage(true);
 } else {
 setStatus(data.error || 'Voice input failed \u2014 type instead');
 }
 }

 async function playTTS(text) {
 if (!ttsEnabled) return;
 // Strip markdown so the voice reads words, not symbols.
 const spoken = text.replace(/[*_#`>|]/g, '').replace(/\\[(.*?)\\]\\(.*?\\)/g, '$1');
 setStatus('speaking...');
 try {
 let url = audioCache[text];
 if (!url) {
 const r = await fetch('/tts', {
 method: 'POST',
 headers: {'Content-Type': 'application/x-www-form-urlencoded'},
 body: 'text=' + encodeURIComponent(spoken),
 });
 const ct = r.headers.get('content-type') || '';
 if (!ct.includes('audio')) { setStatus(''); return; }
 const blob = await r.blob();
 url = URL.createObjectURL(blob);
 audioCache[text] = url;
 }
 const audio = new Audio(url);
 audio.onended = () => setStatus('');
 audio.play();
 } catch (e) { setStatus(''); }
 }

 async function sendMessage(fromVoice) {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text || !started) return;
  input.value = '';
  addMsg(text, 'user');
  document.getElementById('send').classList.add('loading');
 setStatus('thinking...');
  const data = await api('/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'text=' + encodeURIComponent(text) + '&is_voice=' + (fromVoice ? 'true' : 'false'),
  });
  document.getElementById('send').classList.remove('loading');
  if (!data) return;
  addMsg(data.response, 'tutor', data.speech);
 setStatus('');
 playTTS(data.speech || data.response);
}

async function getStats() {
  const data = await api('/stats');
  if (data) addMsg(data.stats || 'No stats yet', 'sys');
}

async function quitSession() {
  if (!started) return;
  const data = await api('/quit', { method: 'POST' });
  if (!data) return;
  addMsg(data.response, 'sys');
  started = false;
  document.getElementById('status').textContent = 'Session ended. Refresh to start a new one.';
  document.getElementById('send').disabled = true;
}

window.onload = () => {
  document.getElementById('tts-btn').textContent = ttsLabel(ttsEnabled);
  startWarmup();
};
document.getElementById('input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});
</script>
</body>
</html>"""


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
        "media-src 'self' blob:; img-src 'self' data:"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if AUTH_ENABLED and request.cookies.get(SESSION_COOKIE, "") not in _session_tokens:
        return AUTH_PAGE
    return HTML_PAGE


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/auth")
def authenticate(request: Request, response: Response, code: str = Form(...)):
    """Validate an invite code and set an opaque session token cookie.

    The invite code never leaves the server: the cookie holds a random token
    mapped server-side to a derived user_id (audit 2026 finding 3). Code
    comparison is constant-time; repeated failures lock the code out.
    """
    if _rate_limited(_rate_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    code = code.strip()
    if _code_locked(code):
        # Same text as a wrong code: distinct errors leak valid codes.
        return {"ok": False, "error": "Invalid invite code"}
    if _code_matches(code):
        _clear_code_failures(code)
        token = secrets.token_urlsafe(32)
        _remember_session_token(token, _user_id_for_code(code))
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            samesite="lax",
            secure=_is_secure(request),
            max_age=COOKIE_MAX_AGE,
        )
        return {"ok": True}
    _record_code_failure(code)
    return {"ok": False, "error": "Invalid invite code"}


@app.post("/start")
def start(request: Request, response: Response):
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if state.session_started and not state.session_ended:
        # Idempotent resume — the engine (possibly restored from checkpoint)
        # is already warmed up; return current status instead of re-warming up.
        with state.lock:
            eng = get_engine(state)
            return {
                "response": "Session resumed.",
                "status": eng.get_status_report(),
                "resumed": True,
            }
    if state.session_ended:
        # Reset for a new session
        with state.lock:
            state.engine = None
            state.session_ended = False
    try:
        with state.lock:
            eng = get_engine(state)
            resp = eng.start_warmup()
            state.session_started = True
            status = eng.get_status_report()
        return {"response": resp, "status": status}
    except Exception:
        logger.exception("start failed")
        # Never echo internal exception text to clients.
        return {
            "response": "Something went wrong starting the session.",
            "error": {"code": "internal_error", "message": "Internal error. Check server logs."},
        }


@app.get("/history")
def history(request: Request, response: Response):
    """Return the current session's transcript (for page refresh / resume).

    Tutor entries are normalized: legacy checkpoints may store the RAW
    ---SAY--- response as content, so the display text is extracted here and
    the speech text (stored, or extracted from legacy content) rides along
    for replay.
    """
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not state.session_started or state.session_ended:
        return {"messages": []}
    with state.lock:
        eng = get_engine(state)
        messages = []
        for m in eng.get_history():
            if m.get("role") == "tutor":
                display, speech = extract_speech_text(str(m.get("content", "")))
                entry = {**m, "content": display}
                if m.get("speech") is not None:
                    entry["speech"] = m["speech"]
                elif speech is not None:
                    entry["speech"] = speech
                messages.append(entry)
            else:
                messages.append(m)
        return {"messages": messages}


@app.post("/message")
def message(
    request: Request,
    response: Response,
    text: str = Form(...),
    is_voice: bool = Form(False),
):
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if _rate_limited(_rate_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    try:
        with state.lock:
            if state.session_ended:
                # /quit (or an in-session "quit") landed while this request was
                # waiting on the lock — return a clean error, do not touch state.
                return {"response": "Session ended. Call /start to begin a new one."}
            if not state.session_started:
                return {"response": "No active session. Call /start first."}
            eng = get_engine(state)
            if text.strip().lower() in ("quit", "exit", "sair"):
                result = eng.end_session()
                state.session_ended = True
                state.engine = None
                return {"response": result}
            resp = eng.user_message(text, is_voice=is_voice)
            display, speech = extract_speech_text(resp)
            return {"response": display, "speech": speech}
    except Exception:
        logger.exception("message failed")
        # Never echo internal exception text to clients.
        return {
            "response": "Something went wrong. Please try again.",
            "error": {"code": "internal_error", "message": "Internal error. Check server logs."},
        }


@app.get("/stats")
def stats(request: Request, response: Response):
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        with state.lock:
            eng = get_engine(state)
            return {"stats": eng.get_stats()}
    except Exception:
        logger.exception("stats failed")
        return {"stats": "Error retrieving stats."}


@app.post("/quit")
def quit_(request: Request, response: Response):
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not state.session_started or state.session_ended:
        return {"response": "No active session to quit."}
    try:
        with state.lock:
            eng = get_engine(state)
            result = eng.end_session()
            state.session_ended = True
            state.engine = None
            return {"response": result}
    except Exception:
        logger.exception("quit failed")
        # Never echo internal exception text to clients.
        return {
            "response": "Something went wrong ending the session.",
            "error": {"code": "internal_error", "message": "Internal error. Check server logs."},
        }


@app.post("/stt")
async def stt(request: Request, response: Response, file: UploadFile = File(...)):
    """Transcribe an audio blob to text (stateless, auth-gated)."""
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if _rate_limited(_rate_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format. Use one of: .wav, .mp3, .webm, .ogg, .m4a",
        )
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB).")
    # ponytail: duration cap only for .wav (cheap RIFF header parse); other
    # formats rely on the 10 MB cap — upgrade path is a post-decode duration
    # check inside audio.py's STT pipeline.
    if suffix == ".wav":
        duration = _wav_duration_seconds(data)
        if duration is not None and duration > MAX_STT_WAV_SECONDS:
            raise HTTPException(
                status_code=413, detail=f"Audio too long (max {MAX_STT_WAV_SECONDS} s)."
            )
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()
    path = Path(tmp.name)
    try:
        async with _stt_limit():
            transcript = await asyncio.wait_for(
                asyncio.to_thread(speech_to_text, path), STT_TIMEOUT_SECONDS
            )
        return {"transcript": transcript or ""}
    except (TimeoutError, asyncio.TimeoutError):
        logger.warning("stt timed out after %s s", STT_TIMEOUT_SECONDS)
        return {"transcript": "", "error": "Transcription timed out."}
    except Exception:
        logger.exception("stt failed")
        # Never echo internal exception text to clients.
        return {"transcript": "", "error": "Transcription failed."}
    finally:
        path.unlink(missing_ok=True)


@app.post("/tts")
def tts(request: Request, response: Response, text: str = Form(...)):
    """Synthesize text to audio bytes (stateless, auth-gated)."""
    state = get_session(request, response)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if _rate_limited(_rate_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    if len(text) > MAX_TTS_CHARS:
        raise HTTPException(
            status_code=400, detail=f"Text too long (max {MAX_TTS_CHARS} characters)."
        )
    # Speech channel contract: honor a trailing ---SAY--- section if present.
    _display, speech = extract_speech_text(text)
    try:
        path = text_to_speech(speech if speech is not None else text)
        if path is None:
            return {"error": "TTS synthesis failed"}
        content_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
        data = path.read_bytes()
        if not is_cached_audio(path):
            path.unlink(missing_ok=True)
        return Response(content=data, media_type=content_type)
    except Exception:
        logger.exception("tts failed")
        # Never echo internal exception text to clients.
        return {"error": "Speech synthesis failed."}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
