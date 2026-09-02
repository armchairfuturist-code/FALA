# FALA Adversarial Audit — 2026-09-02

Scope: `audio.py`, `conversation.py`, `config.py`, `progress.py`, `web.py`, `fala.py`, `prompts/`, `tests/`, `docs/deploy.md`.
Severity: **Critical** = data loss / auth bypass / breaks for real users. **Major** = wrong behavior or significant cost/UX damage. **Minor** = polish, robustness, portability.

## Summary

| # | Sev | Area | Finding | Location |
|---|-----|------|---------|----------|
| 1 | Critical | Security | No-auth mode: cookie value is used directly as `user_id` — anyone can impersonate any user (incl. `default` = the CLI user's data) by setting a cookie | `web.py:124` |
| 2 | Critical | Correctness | `GUARDRAILS["max_new_words_per_session"]` is enforced per LLM call, not per session — unlimited new words | `conversation.py:227` |
| 3 | Critical | Security | Cookie value **is** the invite code (credential in cookie, no revocation, no timing-safe compare, weak codes brute-forceable at 30/min/IP) | `web.py:118,120,437-444` |
| 4 | Major | Security/Race | Shared `SessionState.engine` mutated from threadpool threads with no lock: interleaved `/message`+`/quit`, two tabs/two devices on one code → corrupted checkpoints, double LLM calls, `AttributeError` from `state.engine = None` mid-use | `web.py:87-111,490-527` |
| 5 | Major | Correctness | `load_checkpoint` does bare `json.loads` — one torn/corrupt checkpoint file (non-atomic `write_text` + crash/FUSE stale read) permanently 500s `/start` for that user | `conversation.py:285-299`, `web.py:104-110` |
| 6 | Major | Correctness | `except Exception: pass` swallows ALL vocab-extraction failures incl. API auth/rate-limit errors — vocabulary silently stops growing; also doubles per-turn LLM latency+cost | `conversation.py:187-246` (esp. 246) |
| 7 | Major | Correctness | `_extract_level` fallback scans any "current level" line for any CEFR substring, iterating a `set` → nondeterministic level (e.g. "Current level: A1 (goal B1)" may return B1) | `conversation.py:63-76` |
| 8 | Major | Pedagogy | "Pronunciation feedback" is impossible: Whisper transcript carries zero acoustic data, but `system.md` instructs the tutor to give pronunciation feedback on `[voice]` — the model confabulates | `prompts/system.md:118-119` |
| 9 | Major | Pedagogy | `você` declared "Brazilian (never use)" — wrong: você is used in pt-PT (formal registers; safer form is `o senhor`). Tutor "corrects" valid European Portuguese and teaches over-familiarity with strangers/waiters | `prompts/system.md:11,22` |
| 10 | Major | Pedagogy | Contradiction: `warmup.md:31` "NO grammar explanations. Ever." vs `system.md:122` "Warm-up — … one grammar point" vs `system.md:29` "A1: Explain grammar in English" | see refs |
| 11 | Major | Pedagogy | "Never reveal the correct answer" (`system.md:111,131`) vs "model the correct version naturally" (`:114`) — modeling IS revealing; and a stuck learner has no escape hatch (`warmup.md:18` "Do NOT reveal") → infinite guess loop | see refs |
| 12 | Major | UX | TTS speaks the whole tutor response — English scaffolding + `**markdown**` — as Portuguese (`tts-1`/`alloy`, English-leaning voice). English read with mangled PT phonemes; Azure reads English words with PT phonetics | `web.py` JS `playTTS`, `audio.py:102-113` |
| 13 | Major | UX | `playTTS` fires on `window.onload` after `/start` — browser autoplay policy blocks audio-without-gesture; fails silently, no replay button, no TTS-off toggle | `web.py` HTML_PAGE JS |
| 14 | Major | Security | `/stt` writes upload with attacker-chosen suffix, no size cap (`await file.read()` → full-body memory+disk), no duration cap → disk-fill / Whisper CPU / LLM-cost amplification | `web.py:557-560` |
| 15 | Major | Scale | `/tts` accepts unbounded text → per-request API cost amplification; rate limit keyed by attacker-chosen `sid` cookie in no-auth mode → trivial bypass; `_rate_windows` unbounded memory growth | `web.py:46-57,572-590` |
| 16 | Major | Correctness | `speech_to_text` catches only `ImportError` — a transcription error (bad audio, CUDA) propagates and crashes the CLI main loop; local Whisper reloads the model on **every** utterance | `audio.py:224-246` |
| 17 | Major | Correctness | `record_audio`: fixed 10s block with no early stop/VAD; temp file leaked when both commands fail; timeout kills mid-recording and continues to next command, hanging the user | `audio.py:248-264` |
| 18 | Major | Scale | Every session turn re-sends the full growing `messages` list (no windowing) and checkpoints it to JSON each turn — context and cost grow quadratically over a long session; FUSE-stale reads on Cloud Run resume show old transcript | `conversation.py:267-283`, `docs/deploy.md` |
| 19 | Major | Scale | No timeout on LLM calls (`_call_llm`, vocab extractor, summary) beyond OpenAI client's 600s default → sync threadpool (40 threads) exhaustion under load | `conversation.py:178-186` |
| 20 | Major | Correctness | `end_session` summary update failure silently swallowed (`except Exception: pass`) — user sees "Session saved", but level/summary never advance | `conversation.py:350` |
| 21 | Major | Correctness | `save_vocabulary` empty-guard: a legitimately emptied (or corrupt-loaded) vocab list is never written — deletions impossible; corrupt file loops silently | `progress.py:213-216` |
| 22 | Minor | Correctness | `load_vocabulary` round-trip fragility: values containing `"` or newlines break parsing (`strip('"')` mangles); a context containing `\n- word: ` splits into bogus entries; empty word silently dropped | `progress.py:149-211` |
| 23 | Minor | Correctness | `get_status_report` session count: `int(line.split(":")[-1])` silently fails on "Sessions completed: 3 (this month)" → shows 0 | `conversation.py:85-91` |
| 24 | Minor | Correctness | `start_warmup` produces `[system, system, assistant]` (two adjacent system messages) — some OpenAI-compatible backends (vLLM, some Groq models) reject non-alternating roles | `conversation.py:137-143` |
| 25 | Minor | Correctness | First-user-message injection `[The learner is now answering your question above…]` stays in context for the entire session, misleading the model during free conversation | `conversation.py:147-156` |
| 26 | Minor | Pedagogy | `system.md:71` progression-table example is the identical string twice ("eu quero sopa instead of eu quero sopa") — intended accent example lost | `prompts/system.md:71` |
| 27 | Minor | Pedagogy | Prompt says vocabulary prompt shows 15 review words (`get_vocab_for_prompt(count=15)`) while warmup reviews 1-2 — mismatched expectations; `LEVEL_ORDER` in config is dead code | `progress.py:313`, `config.py:116` |
| 28 | Minor | Security | `secure=request.url.scheme == "https"` — behind a TLS-terminating proxy the flag is False; error responses echo `str(e)` (paths, provider errors) to the client | `web.py:133-139,525-527` |
| 29 | Minor | Robustness | All persistence (`checkpoint`, `vocabulary.md`, `summary.md`, session `.md`) uses non-atomic `write_text`; session filename collision if two sessions start in the same second | `conversation.py:270,313`, `progress.py:229` |
| 30 | Minor | Audio | `aplay` cannot play mp3 (Azure/OpenAI output) — with only `aplay` installed, TTS always "fails"; Piper voice re-`load`s model per call and `_ensure_piper_voice` downloads without a lock (concurrent corrupt downloads) | `audio.py:70-77,40-54,59` |
| 31 | Minor | UX | STT auto-sends transcript without confirmation step; no mic level indicator/timer; CLI `end_session()` at exit is unguarded (LLM outage → traceback after a good session) | `web.py` JS, `fala.py:98` |

## Detail and concrete fixes

### 1. Cookie-as-user_id impersonation (Critical)
In no-auth mode `get_session` accepts any regex-matching cookie value and uses it as the storage key (`web.py:124`). Setting `Cookie: fala_session=default` gives full access to the CLI user's profile, checkpoint, and transcript. Deploy without `FALA_INVITE_CODES` on a public host = total compromise.
**Fix**: always generate a server-side random sid and map sid→user_id in a server-side store (or sign the sid); never trust the raw cookie as a filesystem key. Also gate all routes on auth even in dev mode.

### 2. Per-call, not per-session, new-word cap (Critical)
`conversation.py:227`: `data.get("new_words", [])[:max_new]` slices each exchange's extraction. Five exchanges × 5 words = 25 "new" words in one session.
**Fix**: track `len(self.new_words)` and cap the slice at `max_new - len(self.new_words)`; skip extraction entirely at the cap (also saves an LLM call per turn).

### 3. Invite code doubles as the credential and the cookie (Critical)
`web.py:118-120,437-444`: the session cookie literally contains the invite code; `sid not in AUTH_CODES` is the whole auth check. Consequences: code exfiltration via any log/proxy that records cookies, no session revocation, `!=` comparison (no constant-time), 30/min/IP guessing against human-memorable codes.
**Fix**: derive an opaque session token from the code (HMAC + random), `hmac.compare_digest` for validation, store per-code rate limits and rotation.

### 4. Concurrency races (Major)
Sync `def` endpoints run in FastAPI's threadpool. `SessionState.engine` is created/mutated with no lock (`web.py:104-110`); `state.engine = None` in `/quit` races an in-flight `/message`. Two devices sharing one invite code → two engines, both mutating the same checkpoint JSON (`write_text`, non-atomic). Fix: per-session `threading.Lock` around engine use; atomic writes (`tmp file + os.replace`); `json.loads` in a try with backup/re-create.

### 5. TTS language handling (Major)
`system.md:96` tells the tutor to mix PT and English; `web.py` feeds the raw response (including markdown) to `/tts`. Fix: strip markdown before synthesis; have the tutor emit speech text separately from display text (structured output: `{display, speech}`), or split by language and synthesize per segment with correct `xml:lang` (Azure) / a PT-native voice.

### 6. Pronunciation feedback is fake (Major)
Whisper returns text only. Remove the `[voice]` pronunciation-feedback instruction or gate it behind a real scorer (e.g., compare transcript to expected phrase, or use an acoustic-alignment service). Otherwise the tutor invents praise/criticism.

### 7. tu/você (Major)
`você` is not Brazilian-only. Teach: `tu` with friends/family, `o senhor/a senhora` with strangers/officials; `você` exists in pt-PT (esp. spoken/northern). Rewrite the table rows so learner errors using `você` are reframed as register choice, not "Brazilian mistakes".

### 8. Prompt contradictions (Major)
Pick one policy per phase and make it level-conditional in a single place: (a) grammar: "no grammar at A0; at A1+ max one micro-explanation per session" — delete `warmup.md:31`'s "Ever"; (b) answer-reveal: keep "don't reveal" for production exercises, but allow "that means [translation]" for comprehension exercises, and add: "after 3 failed attempts, reveal and move on."

### 9. Vocab-markdown round-trip (Minor)
`progress.py` uses an ad-hoc quote-wrapped format that breaks on `"`/newlines. Switch values to single-line escapes or JSON-lines; or keep markdown but `json.dumps` each value.

### 10. Cloud Run reality (Major)
`deploy.md` mounts a FUSE GCS volume and says stale reads are "fine" — but the resume path reads the checkpoint written seconds earlier, so users can resurrect stale sessions; multi-instance Cloud Run breaks the in-memory `_sessions`/`_rate_windows` entirely. Fix: single instance (`max_instances=1`), object versioning + `gsutil rewrite`… or write checkpoints to a real store (Firestore) before inviting users.

## Test coverage notes
`tests/` is decent on happy paths (auth gates, multi-user isolation, checkpoint save/load, empty-vocab guard) but misses: corrupt checkpoint restore, concurrent requests to one session, per-session vocab cap, level-extraction fallback nondeterminism, non-UTF8/large uploads to `/stt`, and any prompt-content assertion for the pt-PT rules.
