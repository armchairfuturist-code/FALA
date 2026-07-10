# FALA — QA Inventory

## Feature Matrix

Each feature has:
- **AC**: Acceptance criteria (verified by automated test or manual check)
- **Edge cases**: Risk-ranked (H/M/L)
- **Test method**: auto (unit/integration) | manual (real-user simulation)

---

## 1. CLI Entrypoint (`fala.py`)

### 1.1 Banner Display
- **AC**: On `python fala.py`, banner renders with "fala — European Portuguese Tutor" and subtitle "A1→B1 | Type 'quit' to exit | /voice to toggle voice input"
- **Edges**: [L] Terminal width < 80 chars: banner wraps but stays readable. [L] Non-UTF-8 terminal: bold cyan escapes may render as garbage.
- **Test**: auto (`test_fala.py::test_cli_banner_shown`), manual

### 1.2 Status Report on Start
- **AC**: Shows "Level: X | Sessions: N | Words due for review: N | Session started: YYYY-MM-DD HH:MM"
- **Edges**: [M] First run (no data): shows "Level: A0" with no "Sessions:" field. [M] Empty vocabulary: no "Words due for review" shown. [H] Summary has "Current level: A1" but vocabulary.md is empty — **BUG**: status report shows level from summary but review words from vocabulary; they're inconsistent.
- **Test**: auto (`test_conversation.py::TestGetStatusReport`), manual

### 1.3 TTS Provider Info
- **AC**: Shows "TTS: Piper (local tugão pt-PT)" when FALA_TTS=piper, or "TTS: OpenAI (cloud, voice: X)" otherwise
- **Edges**: [M] Piper model not downloaded: shows "TTS: Piper (not downloaded)". [L] audio module unavailable: shows "Audio: install openai package for TTS support"
- **Test**: manual

### 1.4 Warm-up Phase
- **AC**: Displays "Starting warm-up...", then tutor's opening message in a blue-bordered panel
- **Edges**: [H] No API key: crashes with authentication error — user gets no helpful message. [M] API call fails: unhandled exception, no graceful fallback. [M] Prompt templates missing: FileNotFoundError with no context.
- **Test**: auto (`test_conversation.py::TestStartWarmup`), manual

### 1.5 Main Input Loop
- **AC**: Green "you" prompt accepts text; sends to engine; displays blue "tutor" panel with response
- **Edges**: [M] Empty input: skipped, no error (correct). [M] Very long input (>4000 chars): truncated by LLM context window, no warning. [L] Unicode/emoji: should pass through to LLM.
- **Test**: auto (smoke tests), manual

### 1.6 Voice Toggle (`/voice`)
- **AC**: Typing `/voice` toggles mode; shows "Voice input: ON" or "Voice input: OFF"
- **Edges**: [M] Audio unavailable: `/voice` still toggles but `voice_mode` silently has no effect on next input (input stays as text prompt). The banner says `/voice to toggle` even when audio is unavailable — **BUG**: misleading UX.
- **Test**: auto (`test_fala.py::test_cli_voice_toggle_in_banner`), manual

### 1.7 Stats Command (`/stats`)
- **AC**: Displays vocabulary count, CEFR breakdown, mature words, avg confidence, due for review in a green-bordered panel
- **Edges**: [M] No vocabulary: shows "No vocabulary yet. Start a session to build your word bank!" [L] Very large vocabulary (1000+ words): stats still render fast.
- **Test**: manual

### 1.8 Quit Commands
- **AC**: Typing "quit", "exit", or "sair" (case-insensitive) ends session; saves vocabulary, sessions log, summary; shows stats and "Adeus!"
- **Edges**: [M] API key missing: end_session LLM call for summary fails silently, but vocab save still works — user gets partial result. [H] vocabulary.md is empty but summary claims words — **BUG**: data inconsistency after quit; session saves empty vocab over pre-existing data.
- **Test**: auto (`test_fala.py::test_cli_quit_exits`), manual

### 1.9 EOF/KeyboardInterrupt
- **AC**: Ctrl+D or Ctrl+C triggers same end-session flow as quit
- **Edges**: [L] Double Ctrl+C: Python kills process immediately, no save.
- **Test**: manual

### 1.10 Audio Output (TTS)
- **AC**: When audio module available and API key set, tutor responses play audio via mpv/ffplay/aplay. Piper mode works offline with downloaded voice.
- **Edges**: [H] No audio player installed (no mpv/ffplay/aplay): `play_audio` returns False silently, no user feedback. [M] Piper model download fails: prints message, falls back to None — speak() returns False silently. [M] OpenAI TTS with invalid API key: prints error, returns None silently.
- **Test**: manual (requires hardware)

### 1.11 Voice Input (STT)
- **AC**: In voice mode, records 10s audio, transcribes via Whisper or OpenAI, displays "heard: ..."
- **Edges**: [H] No microphone: `arecord` and `rec` both fail, returns None, falls back to text input — correct but slow (10s timeout). [M] No STT model: falls back to OpenAI, needs API key. [L] Noisy environment: transcription quality degrades.
- **Test**: manual (requires hardware)

---

## 2. Web UI (`web.py`)

### 2.1 GET /
- **AC**: Returns HTML with chat interface: header, status line, chat area, stats/quit buttons, message input, send button
- **Edges**: [L] Browser without JS: page renders but non-functional. [L] Mobile viewport: basic responsiveness via max-width.
- **Test**: manual

### 2.2 POST /start
- **AC**: Initiates warm-up, returns tutor message + status report JSON
- **Edges**: [H] Called twice: creates new ConversationEngine (global engine var is None check), but first engine's data is lost. **BUG**: calling `/start` on an already-running session silently discards prior session without saving.
- **Test**: manual

### 2.3 POST /message
- **AC**: Sends user text, returns tutor response JSON. "quit"/"exit"/"sair" triggers end_session.
- **Edges**: [M] Empty message: engine receives empty string, LLM may produce junk. [M] Message before /start: returns error JSON (engine is None → get_engine creates one, so actually works but without warmup). **BUG**: no warmup context if user sends message before start.
- **Test**: manual

### 2.4 GET /stats
- **AC**: Returns vocabulary stats JSON
- **Edges**: [L] No session started: get_engine creates engine, get_stats on fresh engine returns "No vocabulary yet".
- **Test**: manual

### 2.5 POST /quit
- **AC**: Ends session, returns result string. UI disables send button.
- **Edges**: [M] Called twice: second call creates new engine, ends it immediately — "Session saved. 0 new words added." — misleading.
- **Test**: manual

### 2.6 Chat UI Behavior
- **AC**: Messages appear in chat area with tutor/user/sys styling. Enter key sends. Send button shows loading state. Auto-scroll to latest message.
- **Edges**: [M] Very long messages: overflow chat area without scrolling. [L] XSS in tutor response: textContent used (safe). [L] Rapid clicking send: loading class prevents double-submit (correct).
- **Test**: manual

---

## 3. Conversation Engine (`conversation.py`)

### 3.1 System Prompt Building
- **AC**: Reads prompts/system.md, formats with level/summary/vocabulary, sets as messages[0]
- **Edges**: [M] prompts/system.md missing: FileNotFoundError. [M] Template has {key} not provided: KeyError.
- **Test**: auto (`test_conversation.py::TestBuildSystemPrompt`)

### 3.2 Level Extraction
- **AC**: Parses "Current level: A1" from summary; defaults to "A0"
- **Edges**: [M] Summary has "Current level: B2": returns "A0" — only checks A0/A1/A2/B1. **BUG**: unknown levels silently default to A0.
- **Test**: auto (`test_conversation.py::TestExtractLevel`)

### 3.3 Warm-up Flow
- **AC**: Appends warmup.md as user message, gets LLM response, replaces warmup message with compact context marker, sets _warmup_done
- **Edges**: [H] LLM call fails: exception propagates to caller (CLI crashes). [M] Warmup called twice: second call would append another warmup prompt — no guard.
- **Test**: auto (`test_conversation.py::TestStartWarmup`)

### 3.4 User Message Flow
- **AC**: On first message after warmup, injects system message framing it as answer. Appends user msg with optional [voice] prefix. Calls LLM. Logs. Extracts vocab.
- **Edges**: [M] LLM returns empty string: `.content or ""` handles it, but tutor panel shows empty. [L] LLM returns non-string: `.content` should always be string from OpenAI client.
- **Test**: auto (`test_conversation.py::TestUserMessage`)

### 3.5 Vocabulary Extraction
- **AC**: After each exchange, sends separate LLM call to extract new words + assess review words.
- **Edges**: [H] Extraction LLM call fails: exception caught, silently ignored — words not added. [H] LLM returns hallucinated JSON keys: `data.get("new_words", [])` handles missing keys but not wrong types. [M] Duplicate word detection: `add_vocabulary` skips duplicates by word string match — but different capitalizations/accents create separate entries.
- **Test**: auto (`test_conversation.py::TestExtractVocabFromExchange`)

### 3.6 Session Logging
- **AC**: Each exchange logged as "[role] text" in session_log list
- **Edges**: [L] Very long session: log grows unbounded in memory; only last 20 lines sent to summary LLM.
- **Test**: auto

### 3.7 End Session
- **AC**: Saves vocabulary, session log file, updates summary via LLM, saves learning records, generates stats string
- **Edges**: [H] Summary LLM call fails: exception caught, silently ignored — old summary preserved but session not counted. [H] save_vocabulary writes empty list: overwrites existing vocabulary.md with empty content. **BUG**: if vocabulary was loaded from empty file and LLM extraction also fails, save_vocabulary wipes any prior data. [M] Session file naming: format `%Y-%m-%d-%H%M` — two sessions same minute overwrite.
- **Test**: auto (`test_conversation.py::TestEndSession`)

---

## 4. Progress/Vocabulary (`progress.py`)

### 4.1 Add Vocabulary
- **AC**: Adds new word with defaults (ease=2.5, interval=1, confidence=0.3, needs_review=True). Skips duplicates by word string match.
- **Edges**: [M] Case-sensitive duplicate check: "Olá" and "olá" are different entries — **BUG**: case-variant duplicates accumulate.
- **Test**: auto (`test_progress.py::TestAddVocabulary`)

### 4.2 Update Vocab After Review
- **AC**: Correct: confidence +0.15 (capped 1.0), ease +0.1 (min 1.3), interval *= ease. At confidence >= 0.8, clears needs_review. Wrong: confidence -0.2 (min 0.0), ease -0.2 (min 1.3), interval=1, needs_review=True.
- **Edges**: [L] Floating point accumulation: 50 correct answers at +0.15 = 7.5 confidence, capped at 1.0 — fine.
- **Test**: auto (`test_progress.py::TestUpdateVocabAfterReview`)

### 4.3 Get Review Words
- **AC**: Returns words where next_review <= today OR needs_review=True. Sorted by confidence ascending. Limited to count.
- **Edges**: [M] Invalid last_reviewed date: catches ValueError, uses datetime.min → word is always due. [L] All words due: returns lowest-confidence ones first up to count limit.
- **Test**: auto (`test_progress.py::TestGetReviewWords`)

### 4.4 Vocabulary Persistence
- **AC**: Save writes markdown format to vocabulary.md. Load parses it back with all fields.
- **Edges**: [H] vocabulary.md is empty: load_vocabulary returns [] — **BUG**: save_vocabulary([]) writes empty string, and load after that returns []. But the `text.strip().split("\n- word: ")` logic for empty string returns [''], then `_parse_vocab_entry("")` returns None. Need to verify this path. [H] Malformed entry in file: `_parse_vocab_entry` returns None and entry is skipped — partial data loss. [M] File encoding issues: uses default encoding (UTF-8) which should be fine.
- **Test**: auto (`test_progress.py::TestVocabPersistence`)

### 4.5 Summary Management
- **AC**: Load returns file content or default template. Save writes to summary.md.
- **Edges**: [M] Concurrent writes: no file locking. [L] Corrupt summary: LLM update may produce malformed markdown — next load works but level extraction may fail.
- **Test**: auto (`test_progress.py::TestSummary`)

### 4.6 Vocabulary Report (CEFR + SRS)
- **AC**: Returns dict with total_words, cefr breakdown, mature_words (>=0.7), avg_confidence, due_for_review. CEFR bands from frequency word list.
- **Edges**: [M] pt_50k.txt missing: _load_frequency_words returns {} → all words classified as "B2+". [M] Empty vocabulary: returns zeros — division by zero avoided by early return.
- **Test**: manual (no dedicated test for vocabulary_report, though it's exercised via get_stats)

### 4.7 Get Vocab for Prompt
- **AC**: Returns formatted string of review words for prompt injection. Empty returns placeholder.
- **Edges**: [L] Words with special chars: markdown in prompt is fine.
- **Test**: auto (`test_progress.py::TestGetVocabForPrompt`)

### 4.8 Learning Records
- **AC**: Saves graduated words (confidence >= 0.8, not needs_review) to records/####-slug.md
- **Edges**: [M] RECORDS_DIR has existing files: uses glob count + 1 for numbering — gaps if files deleted. [L] Title longer than 40 chars: slug truncated to 40.
- **Test**: auto (`test_conversation.py::test_graduated_words_save_learning_record`)

### 4.9 CEFR Frequency Words
- **AC**: Loads pt_50k.txt, maps word → rank, assigns CEFR band by rank thresholds (A1: <500, A2: <2000, B1: <5000, else B2+)
- **Edges**: [M] File format mismatch: splits by first space — handles "word 12345" format. [L] Very large file (50k lines): loads into memory on first call, cached after.
- **Test**: implicit via vocabulary_report

---

## 5. Audio (`audio.py`)

### 5.1 OpenAI TTS
- **AC**: Calls OpenAI speech API, writes MP3 to temp file, returns Path
- **Edges**: [H] No API key: authentication error. [M] Rate limit: exception caught, returns None. [M] Very long text (>4096 chars): OpenAI TTS has input limit.
- **Test**: manual (requires API key)

### 5.2 Piper TTS
- **AC**: Downloads pt-PT tugão model on first use. Synthesizes WAV at length_scale=1.5 (slower for learners). Returns temp file path.
- **Edges**: [H] piper-tts not installed: ImportError — not caught, crashes speak(). **BUG**: the `from piper import PiperVoice` is inside try/except but the outer code path may not handle it fully. [M] Model download fails (no network): prints message, returns None. [M] Corrupt model file: loads but synthesis fails — exception caught, returns None.
- **Test**: manual

### 5.3 Play Audio
- **AC**: Tries mpv → ffplay → aplay. Returns True on success, False if all fail.
- **Edges**: [H] No player installed: returns False silently — no user feedback. **BUG**: user has no idea audio failed. [M] Player times out (30s): returns False for that player, tries next.
- **Test**: manual

### 5.4 Speech-to-Text
- **AC**: Tries local whisper → OpenAI API fallback. Returns text string or None.
- **Edges**: [H] Neither whisper nor OpenAI available: returns None. [M] Whisper model not downloaded: loads on first call (slow).
- **Test**: manual

### 5.5 Record Audio
- **AC**: Tries arecord → rec. Records 10s WAV to temp file. Returns Path or None.
- **Edges**: [H] No microphone / no recording tool: returns None after ~15s. [M] Permission denied on /dev/snd/*: subprocess fails, returns None.
- **Test**: manual

### 5.6 Listen Pipeline
- **AC**: record_audio → speech_to_text → cleanup temp file. Returns text or None.
- **Edges**: [M] Record succeeds but STT fails: temp file cleaned up, returns None.
- **Test**: manual

---

## 6. Config (`config.py`)

### 6.1 Environment Variables
- **AC**: Reads FALA_MODEL, FALA_BASE_URL, FALA_API_KEY (fallback OPENAI_API_KEY), FALA_TTS, FALA_TTS_VOICE, FALA_STT_MODEL
- **Edges**: [H] No .env loading: Python never reads `.env` file. User must source it manually. **BUG (UX)**: running `python fala.py` without sourcing .env first has no API key, crashes on warmup.
- **Test**: auto (`test_config.py::TestEnvVarDefaults`)

### 6.2 Path Defaults
- **AC**: All paths under PROJECT_DIR. DATA_DIR/{sessions,records} auto-created.
- **Edges**: [L] PROJECT_DIR is cwd/.. if config.py imported from elsewhere: uses `Path(__file__).parent`.
- **Test**: auto (`test_config.py::TestPaths`)

### 6.3 Guardrails
- **AC**: max_new_words_per_session=5, min_review_words_per_warmup=3, present_tense_confidence_threshold=0.7
- **Edges**: [L] max_new_words_per_session is defined but not enforced in code — it's a prompt hint, not a hard limit.
- **Test**: auto (`test_config.py::TestGuardrails`)

---

## Bug Summary (discovered during inventory)

| # | Severity | Feature | Description |
|---|----------|---------|-------------|
| B1 | H | 4.4 | `vocabulary.md` is empty but `summary.md` says 20 words — data inconsistency. `save_vocabulary` may have been called with empty list, wiping prior data. |
| B2 | H | 3.7 | `end_session` writes vocabulary to file even if extraction failed — a single session with LLM errors can wipe entire vocabulary history |
| B3 | H | 6.1 | No `.env` file loading — user must manually `source .env` before every run; otherwise crashes with auth error |
| B4 | H | 1.4/1.8/3.3 | No graceful error handling for missing API key — crashes with raw exception instead of helpful message |
| B5 | H | 2.2 | Web `/start` called twice silently discards prior session without saving |
| B6 | M | 1.6 | `/voice` toggle shown in banner even when audio unavailable — misleading |
| B7 | M | 3.2 | Unknown levels (B2, C1) silently default to A0 instead of being preserved or flagged |
| B8 | M | 4.1 | Case-sensitive duplicate check: "Olá" and "olá" create separate vocabulary entries |
| B9 | M | 2.3 | Web `/message` without prior `/start` creates engine without warmup context |
| B10 | M | 5.3 | Audio playback failure is silent — user has no indication TTS didn't work |
| B11 | L | 3.7 | Session file naming: two sessions in same minute overwrite each other |
| B12 | L | 4.8 | Learning record numbering: gaps if records are deleted |
| B13 | L | 4.9 | No automated test for `vocabulary_report` function |
| L1-L6 | L | — | 13 ruff lint issues (import order, line length, unused imports) |
