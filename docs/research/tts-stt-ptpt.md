# TTS/STT Options for European Portuguese (pt-PT)

> Research for ticket #007 — investigating voice quality alternatives for FALA.

## Summary

| Option | TTS Quality | STT Quality | Cost | Offline | Recommendation |
|--------|------------|-------------|------|---------|---------------|
| **Current: OpenAI TTS + Whisper STT** | ⚠️ English-optimised voices, no true pt-PT | ⚠️ Good but generic Portuguese (leans pt-BR) | API cost for TTS, free STT | TTS: no, STT: yes | — |
| **ElevenLabs TTS** | ✅ True multilingual, can generate pt-PT voices via Voice Design | — | $5–$22/mo | ❌ | **Best cloud TTS upgrade** |
| **Piper TTS (tugão)** | ✅ Dedicated pt-PT neural voice, ~63 MB | — | Free | ✅ | **Best local TTS** |
| **Coqui XTTSv2 + pt-PT reference** | ✅ Best quality (voice cloning) | — | Free (self-host) | ✅ (GPU) | **Best quality local TTS** |
| **Google STT (Chirp 3)** | — | ✅ Explicit pt-PT locale model | ~$64/hr Chirp, ~$0.006/15s standard | ❌ | **Most accurate STT** |
| **faster-whisper / whisper.cpp** | — | ⚠️ Same as Whisper but faster | Free | ✅ | **Best free STT** |

---

## TTS Options

### 1. Current: OpenAI TTS (tts-1 / gpt-4o-mini-tts)

**Voices**: 13 built-in (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, **marin**, **cedar**)  
**pt-PT support**: ❌ None are true pt-PT voices. All voices are English-optimised multilingual profiles.  
**Workaround**: `gpt-4o-mini-tts` has an `instructions` parameter — can prompt `"Speak in a European Portuguese accent"` to steer pronunciation.  
**Verdict**: Adequate for now, but the accent will always sound non-native.

### 2. ElevenLabs TTS (Recommended cloud upgrade)

**pt-PT support**: ✅ Portuguese (`pt`) supported by `eleven_multilingual_v2` and `eleven_flash_v2_5`.  
**Premade voices**: None verified for pt-PT, but any voice works with a multilingual model.  
**Voice Design**: Can generate a custom pt-PT voice from a text description ("a Portuguese speaker from Lisbon").  
**Voice Library**: Community voices available filtered by language.  
**Cost**: $5/mo (Starter) to $22/mo (Creator) for decent quotas.  
**Verdict**: Best cloud option — authentic pt-PT possible via Voice Design. Worth trying.

### 3. Piper TTS — tugão (Best local neural TTS)

**Voice**: `pt_PT-tugão-medium` — dedicated European Portuguese neural voice.  
**Quality**: Medium tier (22,050 Hz, ~20M params). Good for a CLI tutor.  
**Size**: ~63 MB total (model + config).  
**Usage**: `echo "Olá, como estás?" | piper --model pt_PT-tugão-medium --output_file out.wav`  
**License**: CC0 (NabuCasa dataset).  
**Verdict**: Excellent free, offline option. Runs on CPU. Should be the default for voice input sessions.

### 4. Coqui TTS — XTTSv2 (Best quality local TTS)

**pt-PT support**: Via multilingual model with `language="pt"` + a pt-PT reference audio (~6s).  
**Quality**: State-of-the-art neural, voice cloning quality.  
**Requirements**: Needs GPU for reasonable speed, ~1-2 GB model.  
**Verdict**: Overkill for a CLI tutor unless you already have a GPU pipeline.

### 5. eSpeak-NG (Fallback)

**pt-PT**: ✅ Built-in (`pt` for Portugal).  
**Quality**: Robotic formant synthesis — clearly artificial.  
**Size**: ~5 MB, works everywhere.  
**Verdict**: Good universal fallback when no other engine is available.

---

## STT Options

### 1. Current: OpenAI Whisper (local)

**pt-PT accuracy**: ~7-9% WER on Portuguese benchmarks. However, Whisper treats Portuguese as one language (leans pt-BR due to training data imbalance).  
**Variants**: `faster-whisper` (4× faster, GPU), `whisper.cpp` (CPU-optimized), `WhisperX` (word timestamps + VAD).  
**Verdict**: Adequate for a CLI tutor. The pt-BR lean is noticeable for pt-PT-specific vocabulary.

### 2. Google Cloud Speech-to-Text (Best accuracy)

**pt-PT support**: ✅ Explicit `pt-PT` locale — dedicated model for European Portuguese.  
**Models**: Chirp 3 (latest), standard, telephony.  
**Accuracy**: Likely best for pt-PT-specific phonetics (final "s" as /ʃ/, vowel reduction, etc.).  
**Cost**: Standard ~$0.006/15s ($14.40/hr); Chirp ~$0.016/15s (~$64/hr).  
**Free tier**: First 60 min/month free.  
**Verdict**: Most accurate, but ongoing cost. Worth switching to for the free tier; the pt-PT locale is a meaningful improvement.

### 3. Other STT

| Option | pt-PT quality | Cost | Offline |
|--------|--------------|------|---------|
| Azure Speech-to-Text | Very good (dedicated pt-PT) | $0.006–$1.00/hr | ❌ |
| AWS Transcribe | Good (pt-PT supported) | $0.024/min | ❌ |
| Meta MMS | Good (1,100+ languages) | Free | ✅ |

---

## Recommendation

**For a "run daily" CLI tutor, the pragmatic path:**

1. **Keep current setup** (OpenAI TTS + Whisper) as the default — it works.
2. **Add Piper TTS (tugão)** as an offline/local TTS option — no API cost, decent quality, dedicated pt-PT voice. Switchable via `FALA_TTS=piper` env var.
3. **Add Google STT as an opt-in** for users who want better pt-PT recognition — switchable via `FALA_STT_PROVIDER=google`. Free for low usage.
4. **Keep eSpeak-NG** as a universal fallback for systems without Piper.

This gives a quality progression: eSpeak (fallback) → Piper (default local) → OpenAI (cloud, current) → ElevenLabs (best cloud).

## Open questions for a follow-up ticket

- Does Piper's tugão voice sound natural enough for daily use? (Needs subjective testing.)
- How much does the `instructions` parameter on `gpt-4o-mini-tts` improve pt-PT accent? (Needs real API testing.)
- What's the latency of Piper on this machine? (Needs benchmark.)
