# FALA Deep Audit + Research Synthesis — 2026-09-02

Fan-in of four adversarial investigations. Full reports in this directory:
- `audit-2026.md` — code/pedagogy/security audit (31 findings, 3 critical)
- `pedagogy-2026.md` — SLA evidence vs FALA's method (meta-analyses cited)
- `tts-2026.md` — pt-PT TTS landscape 2025-2026
- `stt-2026.md` — pt-PT STT landscape 2025-2026 (measured WER)

Baseline: 138 tests pass; findings are gaps, not regressions.

## The one-sentence verdict

FALA's architecture (conversation-first, file-based persistence, SRS, hybrid audio)
is sound; its two biggest risks are (1) prompt rules that contradict the research
base and (2) an audio stack that is one notch too weak for a *tutor* — a tutor that
mis-hears the learner and mis-speaks the language cannot teach.

## Priority roadmap

### P0 — Prompt fixes (free, no code changes)
1. **Replace "never reveal the correct answer"** with the two-strike protocol:
   hint → hint → plain answer + learner repeats the correct form. Evidence: Li 2010
   (CF d≈0.64), Lyster/Saito/Sato 2010 (prompts > recasts), Norris & Ortega 2000
   (explicit > implicit). Current rule contradicts FALA's own "always model the
   correct version" and strands stuck learners.
2. **Fix the você table** — você is valid pt-PT (formal register). Teach
   tu/o senhor/você as register choice, not "Brazilian errors."
3. **Resolve the grammar contradiction**: "no grammar ever" vs A1 grammar point.
   Micro-explanations (1-3 sentences, example-anchored) allowed; grammar-free
   A0 weeks 1-2 only.
4. **Start minimal PT production in sessions 1-3** (repeat the phrase after a
   correct EN translation). Interaction has the strongest effects (Keck 2006;
   Mackey & Goo 2007); weeks of recognition-only wastes it.
5. **Remove the [voice] pronunciation-feedback instruction** — Whisper returns
   text only; the model confabulates. Reintroduce only with a real scorer.
6. **Add a ≥95% known-vocab coverage constraint** on tutor PT output (prevents
   level drift; Hu & Nation 2000, Kremmel 2023).
7. **Graduated voice invite** (once, after typed success) instead of "never push
   voice" — AI bots reduce speaking anxiety (Nature HSSC 2025).
8. **Clitic placement + a + infinitive** get prompt-level error priority (no
   pt-PT CF research exists; these are the highest-error pt-PT traps).

### P1 — Audio stack (biggest learner-experience wins)
1. **STT: faster-whisper, cached model, small int8 default** (large-v3-turbo int8
   if ≥6GB VRAM). Local `base` is the worst pt tier; FALA reloads the model on
   every utterance. Keep Groq whisper-large-v3-turbo ($0.04/hr) as cloud fallback.
2. **Hallucination hardening regardless of model**: record-until-silence / VAD
   instead of fixed 10s, condition_on_previous_text=False, no_speech/logprob
   thresholds, drop low-confidence results (arXiv:2501.11378).
3. **TTS: Azure pt-PT neural primary** (Fernanda/Duarte/Raquel + new pt-PT-Rui
   MAI-Voice-2, $16/1M chars, SSML rate=-20% for slow learner speech);
   gpt-4o-mini-tts with "European Portuguese, slowly" instructions secondary;
   retire tts-1; keep Piper tugão as offline fallback only (~1.5h single-speaker
   data — weak ceiling). Optional spike: Chatterbox-Multilingual-pt-pt (MIT,
   GPU-only). Kokoro/MeloTTS/Orpheus/CSM/Chirp3-HD have no pt-PT. ElevenLabs:
   10x cost, Brazilian drift — skip.
4. **Structured tutor output: {display, speech}** so TTS reads only the PT
   speech text — never English scaffolding or markdown.
5. Fix autoplay: no TTS on window.onload, add replay button + TTS toggle.
   aplay cannot play mp3 — extend player list (ffplay/mpv cover it; drop aplay
   for mp3 providers).

### P2 — Correctness & security (before real users)
1. Per-session new-word cap (currently per-call → 25 words possible).
2. Server-side opaque session tokens; never use cookie/invite code as storage key;
   hmac.compare_digest; per-code rate limits.
3. Per-session threading.Lock; atomic writes (tmp + os.replace) for checkpoints;
   tolerate corrupt checkpoints instead of permanent /start 500s.
4. Stop swallowing exceptions silently (vocab extraction, session summary) —
   log or surface; skip the vocab LLM call once the cap is reached (also halves
   per-turn cost).
5. Bound the context window (windowed messages) and add LLM call timeouts.
6. Cap /stt upload size and /tts text length; bound rate-window memory.
7. Deterministic level extraction (regex, not set iteration).

### Deliberately not recommended
- ElevenLabs, gpt-4o-transcribe as primary, SeamlessM4T-v2 (license), distil-whisper
  (English-only), Moonshine/Kyutai (no pt), Gemini TTS (no pt-PT), NeMo/Parakeet
  (only if GPU present AND faster-whisper-turbo proves insufficient — ponytail).
- Duolingo-style drills (contradicted: Jiang 2022 receptive-only outcomes) and
  pure-input "Dreaming Spanish" mode (speaking lags ~1,500h; production needed).

## Honest caveats
- No pt-PT-specific corrective-feedback research exists; effects assumed to
  transfer from ESL meta-analyses.
- No vendor publishes pt-PT TTS evals; Azure recommendation rests on voice list
  + community reports, not benchmarks. A/B the MAI voice before committing.
- LLM-chatbot CF studies are 2024-2026 vintage and thin (closest: Frontiers 2026
  immediate-vs-delayed chatbot study — no gain difference, better UX immediate).
