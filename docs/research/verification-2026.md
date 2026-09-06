# Fix-Wave Verification — 2026-09-02

Adversarial re-check of the fix wave against `audit-2026.md` (31 findings) and
`synthesis-2026.md` (P0/P1/P2). Every claim was checked against the actual code,
not the fix descriptions. Dynamic probes were run where reading was not enough
(rate-limit hammering, corrupt checkpoint, cap skip, vocab round-trip, STT error
propagation, markdown/SAY pipeline).

**Test suite: 250 passed** (`.venv/bin/python -m pytest tests/ -q`). `ruff check .`
clean, `mypy .` clean (15 files).

## Verdict per area

| Area | Verdict |
|---|---|
| web.py security (tokens, lockout, locks, caps) | verified (2 minor residuals) |
| conversation.py (cap, level, logging, windowing, quarantine) | verified (1 UX bug found: raw ---SAY--- in history) |
| progress.py (atomic writes, vocab round-trip) | verified |
| config.py (STT small, CONTEXT_MESSAGES, LEVEL_ORDER gone) | verified |
| prompts (two-strike, voce, SAY contract, coverage) | verified (1 residual wording tension) |
| audio.py STT | partial (caching + thresholds in, but 1-segment truncation + no error fallback) |
| audio.py TTS | verified for web, broken for CLI (see N1) |
| fala.py compatibility | works, but regressed at the speech layer (N1) |

## Finding-by-finding table

| # | Sev | Finding | Verdict | Evidence |
|---|-----|---------|---------|----------|
| 1 | Crit | Cookie = user_id impersonation | **verified fixed** | web.py:157-183 — cookie is an opaque token_urlsafe token; unknown token -> 401 + cookie cleared; no-auth mints a random uuid4 user_id. Forged-cookie probes reject. |
| 2 | Crit | Word cap per-call, not per-session | **verified fixed** | conversation.py:203-205 (skip when remaining <= 0, saving the LLM call), :222 ([:remaining] slice). Probe: at cap, 0 LLM calls. No warmup bypass — start_warmup never extracts vocab. |
| 3 | Crit | Invite code = cookie credential | **verified fixed** | web.py:208 (secrets.token_urlsafe), :100 (hmac.compare_digest), :103-119 (per-code lockout: 5 fails / 300 s, env-tunable). Cookie never contains the code; user_id is a hash of it (:94-96). |
| 4 | Major | Unlocked shared engine races | **verified fixed** | web.py:157 RLock; every engine touch inside `with state.lock` (:588, 597, 601, 624, 637; get_engine locks at :239). /message re-checks session_ended after acquiring the lock (:628-631). |
| 5 | Major | Corrupt checkpoint -> permanent /start 500 | **verified fixed** | conversation.py:340-364 — JSONDecodeError/KeyError/etc -> quarantine as *.corrupt-<ts> + fresh session. Probe: torn file quarantined, load returns False. Writes atomic (progress.py:24-35). |
| 6 | Major | Silent except: pass in vocab extraction | **verified fixed** | conversation.py:283-292 logger.warning(exc_info=True); end_session summary too (:418-423) and now returns "Session saved, but summary update failed." |
| 7 | Major | Nondeterministic _extract_level | **verified fixed** | conversation.py:63-87 — strict colon parse, then fixed A0->C2 scan. Probe: "Current level: A1 (goal B1)" -> A1 across 50 iterations. |
| 8 | Major | Fake [voice] pronunciation feedback | **verified fixed** | system.md Voice input: "NEVER comment on pronunciation... you cannot hear the learner"; What NOT to do repeats. No [voice] pronunciation instruction remains. |
| 9 | Major | voce wrongly called Brazilian-only | **verified fixed** | system.md register table: "vocé — VALID pt-PT"; "Never correct 'você' as a mistake"; repeated in What NOT to do. |
| 10 | Major | Grammar contradiction (never vs A1 point) | **verified fixed** | warmup.md: "A0 weeks 1-2 are grammar-free... at most ONE grammar point per session, as a micro-explanation"; system.md A0 section + Rule 5 agree; old "Ever" gone. |
| 11 | Major | Never-reveal vs model-the-answer | **verified fixed** | Two-strike protocol (hint -> plain answer + learner repeats) in system.md Error Correction; warmup.md references it; test_no_never_reveal_language_anywhere passes. Residual wording tension: N7. |
| 12 | Major | TTS speaks English scaffolding + markdown | **verified for web** | audio.py:204-224 extract_speech_text; :230-243 markdown stripped before every provider; /message returns split response/speech (web.py:651-653); JS speaks data.speech first (:496). Broken for CLI (N1). |
| 13 | Major | Autoplay blocked, no replay/toggle | **verified fixed** | web.py:509-513 window.onload only sets label + starts warmup (no TTS); replay button per tutor message (:325-331, :363-371); TTS toggle in localStorage (:344-350). |
| 14 | Major | /stt unbounded upload | **verified (claim as scoped)** | web.py:52-53 (10 MB), :713-716 (read(MAX+1) + 413), suffix whitelist + 415. Residual: no duration cap — a 10 MB webm is minutes of Whisper CPU (N6). |
| 15 | Major | /tts unbounded, rate-limit bypass, unbounded windows | **verified (claim as scoped)** | web.py:54, 739-742 (4000 chars -> 400); rate windows pruned every 60 s (:63-83). Probe: 40 cookieless requests -> 30x200 + 10x429 (IP-key fallback holds). Residual: _session_tokens never pruned (N5). |
| 16 | Major | STT errors crash CLI; model reload per utterance | **partial** | Model caching fixed (audio.py:292, 324-333; _ow_model :358-364). Error propagation NOT fixed: speech_to_text catches only _NoLocalSTT (:373-376); probe: garbage wav -> InvalidDataError propagates (CLI crash path alive; web /stt catches it). No cloud fallback for non-ImportError backends. |
| 17 | Major | Fixed 10 s block, no VAD, temp-file leak | **partial** | sox record-until-silence is primary (audio.py:395-417). sox not installed here, so the trim-then-silence effect ordering is plausible but unverified at runtime. Temp-file leak when both commands fail remains (path created before loop, never unlinked on failure return). |
| 18 | Major | Unbounded context growth | **verified fixed** | config.py:115 CONTEXT_MESSAGES=30; conversation.py:186-207 _windowed_messages keeps system + warm-up marker + tail; used in _call_llm (:210). |
| 19 | Major | No LLM timeouts | **verified fixed** | conversation.py:213, 256, 412 — timeout=30 on main call, vocab extractor, summary. |
| 20 | Major | Silent summary failure | **verified fixed** | conversation.py:418-423, 438-441 — logged + surfaced in the return string. |
| 21 | Major | Empty vocab can't be persisted | **verified fixed** | progress.py:246-248 — empty list writes an empty file; only None rejected. Probe: save [] -> reload []. |
| 22 | Minor | Vocab round-trip fragility | **verified fixed** | progress.py:201-208 JSON-escaped values, :183-195 unescape with legacy fallback. Probe: word with ':' + quote, english with newline + quote, context containing '- word: fake' all round-trip exactly. |
| 23 | Minor | Sessions-completed parse fails on "(this month)" | **not fixed** (not claimed) | conversation.py:98-105 — int("3 (this month)") -> ValueError -> sessions 0. |
| 24 | Minor | Two adjacent system messages | **verified fixed** | conversation.py:138-168 — warmup template is a user message, replaced in-place with a user-role marker after the greeting; roles alternate system/user/assistant. |
| 25 | Minor | First-user-message injection persists | **verified fixed** | Old injected message gone; the warm-up template itself becomes the concise marker (:154-168). |
| 26 | Minor | Dup string in progression table | **verified fixed** | system.md Phase-1 row: "voce esta bem?" instead of "você está bem?" — no duplicate. |
| 27 | Minor | 15 review words vs 1-2; LEVEL_ORDER dead code | **partial** | LEVEL_ORDER removed from config.py (0 hits). But get_vocab_for_prompt(count=15) (progress.py:352) still shows 15 while warmup.md says "Pick 1-2 past sentences" — mismatch remains. |
| 28 | Minor | secure flag behind proxy; str(e) echoes | **partial** | Echoes fixed: all endpoints log + return generic messages (:608-615, 664-670, 690-697, 756-762). secure=request.url.scheme == "https" kept deliberately with a comment (:180-184) — still False behind a TLS-terminating proxy. |
| 29 | Minor | Non-atomic persistence; filename collision | **partial** | atomic_write_text (fsync + os.replace) for summary, vocabulary, records, checkpoint (progress.py:24-35, 142, 262, 341; conversation.py:308). Session .md log still plain write_text (:377); same-second filename collision remains. |
| 30 | Minor | aplay/mp3; Piper reload per call; unlocked download | **partial** | aplay now wav-only (audio.py:253-256). Piper still PiperVoice.load per call (:94); _ensure_piper_voice downloads without a lock (:41-58). |
| 31 | Minor | STT auto-send, no mic timer; unguarded CLI end_session | **partial** | Auto-send unchanged in the web UI; mic indicator absent. CLI end_session() still unguarded (fala.py:98), but the summary failure is now caught internally, so the realistic crash window is local-file I/O only. |

## Synthesis roadmap claims

| Item | Verdict |
|---|---|
| P0.1 two-strike protocol | verified (system.md, warmup.md, test_prompts) |
| P0.2 voce register table | verified |
| P0.3 micro-explanations | verified |
| P0.4 Phase-1 production | verified (Rule 3 Step 3, Rule 4 table, warmup) |
| P0.5 remove [voice] pronunciation feedback | verified |
| P0.6 >=95% coverage constraint | verified (system.md Vocabulary coverage + warmup rule) |
| P0.7 graduated voice invite | verified (once per session, after typed success) |
| P0.8 clitic + a+infinitive priority | verified (correction priority list, items 1-2) |
| P1.1 faster-whisper cached, small int8 | verified (config.py:98, audio.py:327-333, requirements.txt) |
| P1.2 hallucination hardening | partial — thresholds + condition_on_previous_text=False in; VAD recording unverified; 1-segment truncation bug (N2) |
| P1.3 Azure pt-PT + gpt-4o-mini-tts, retire tts-1 as primary | verified (default voice pt-PT-FernandaNeural, prosody rate=-20%, SSML html-escaped; tts-1 demoted to last resort) |
| P1.4 {display, speech} structured output | verified for web via ---SAY---; broken for CLI (N1) |
| P1.5 autoplay fix + aplay | verified |
| P2.1 per-session word cap | verified |
| P2.2 opaque tokens + compare_digest + per-code limits | verified |
| P2.3 RLock + atomic writes + corrupt tolerance | verified (except session .md, #29) |
| P2.4 no silent exceptions; skip vocab call at cap | verified |
| P2.5 context window + timeouts | verified |
| P2.6 /stt + /tts caps; bounded rate windows | verified (duration cap residual) |
| P2.7 deterministic level extraction | verified |

## New issues found

| ID | Sev | Issue | Evidence |
|---|-----|-------|----------|
| N1 | **Major (regression)** | The CLI speech path never learned the ---SAY--- contract. fala.py:107 calls audio.speak(text) with the raw response; speak -> text_to_speech (audio.py:230, 266) strips markdown but does NOT call extract_speech_text. Since system.md now tells the tutor to append ---SAY---, the CLI speaks the English display text, then the literal marker "---SAY---", then the PT speech text on any turn where the model follows the contract — and shows the marker in the CLI panel. One-line fix: speak() should use extract_speech_text (speech part, falling back to display) and print_tutor should display the display part. | audio.py:230-243, 266-272; fala.py:99-107; probe: _strip_markdown leaves ---SAY--- intact |
| N2 | **Major** | _fw_transcribe returns only the single best-scoring segment (audio.py:338-351: loop keeps best by avg_logprob, returns best.text). Any utterance faster-whisper splits into multiple segments (a pause of ~1 s — common when an A0 learner thinks mid-sentence) is silently truncated to one fragment. The hallucination research says drop low-confidence segments, not all but the best one. Fix: concatenate segments that pass the thresholds. | audio.py:338-351 |
| N3 | Major (UX, web-only) | ConversationEngine.history stores the raw response including ---SAY--- (conversation.py:173). On resume, /history -> addMsg(m.content) (web.py:407) renders the literal ---SAY--- marker plus the PT speech text as visible chat text. Replay still speaks the right part (server re-parses), but the transcript is visibly wrong after every refresh. Fix: store extract_speech_text(resp)[0] in history, or parse in /history. | conversation.py:172-173; web.py:407; probe: marker present in history[-1] |
| N4 | Minor | Lockout oracle: _code_locked returns a distinct "Too many attempts" error vs "Invalid invite code" (web.py:561-563), revealing that a candidate code is valid (it got locked) after 5 failures. Attacker can wait out the lockout and retry a known-valid code. | web.py:103-105, 559-563 |
| N5 | Minor | _session_tokens grows without bound: in no-auth mode every cookieless request mints a token+user_id (web.py:172-176) and nothing ever evicts tokens (only _sessions is reaped). A crawler hammering without cookies inflates memory. Probe: 40 cookieless requests -> 40 tokens. | web.py:157, 171-183 |
| N6 | Minor | /stt has no duration cap (only 10 MB) — a 10 MB webm is minutes of local Whisper CPU per request (cost-amplification half of audit #14). | web.py:713-716 |
| N7 | Minor | Prompt wording tension: Rule 8 "always model the correct Portuguese version" vs Error Correction step 1 "Never just model silently" on a first wrong attempt. Both survive in system.md; the model may resolve this either way. | prompts/system.md Rule 8 vs Error Correction |
| N8 | Minor | docs/deploy.md not updated by the fix wave: still says invite codes "each is a user_id" (they now map to a hash), still calls FUSE stale reads "Fine", still no --max-instances=1, and opaque in-memory tokens mean every deploy/restart logs all users out (documented only in a web.py comment). Audit #10 remains open. | docs/deploy.md:24-28, 64-66; web.py:139-147 |

## Bottom line

The three critical findings (1, 2, 3) and the majority of Major/Minor findings are
genuinely fixed — not cosmetically. Locks are held on every engine touch, tokens
are opaque server-side, the cap is per-session and skips the LLM call, the level
extract is deterministic, checkpoints quarantine, and the prompt overhaul matches
its claims (with prompt-content tests). Two real problems survived the wave:
the CLI speech path is broken by the new ---SAY--- contract (N1, regression,
one-line fix in audio.speak) and faster-whisper best-segment selection truncates
multi-segment utterances (N2). Neither is covered by the test suite.
