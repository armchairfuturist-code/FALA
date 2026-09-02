# Pedagogy evidence review for FALA (2020–2026 research)

**Date:** 2026-09-02
**Scope:** SLA research + modern language-app practice, evaluated against FALA's current method (see `prompts/system.md`, `CONTEXT.md`): comprehension-first listen-and-translate loop at A0, no grammar explanations, "never reveal the correct answer", retrieval practice warm-ups, SM-2 spaced repetition, priority-based error correction, typed-before-voice progression.
**Method:** Web search + primary-source fetches (meta-analyses, systematic reviews, efficacy studies). Sources cited inline. Research gate: LEDGER.md checked; this run resolves the "pedagogy evidence base" item for the pt-PT tutor.

---

## 1. Comprehensible input vs output vs interaction

### The evidence

**Input (Krashen):** Input is necessary — no one disputes this. What is contested is the strong claim that comprehensible input *alone* suffices. Recurring critiques: i+1 is untestable and undefined (a learner's "i" cannot be measured), and Krashen's own formulations shifted over decades (see Wikipedia's Input Hypothesis summary and 40+ years of responses). A 2025 Frontiers in Psychology review ("Beyond comprehensible input: a neuro-ecological critique", Front. Psychol. 2025) concludes the hypothesis is "conceptually flawed, empirically outdated, and practically insufficient": language growth depends on *interaction, feedback, and multimodal engagement*, not passive processing of simplified input.

**Output (Swain 1985, 1995):** Swain's French immersion data showed students with years of input-only exposure had near-native comprehension but systematically inaccurate production. Output serves three functions: **noticing the gap** (trying to say something reveals what you don't know), hypothesis testing, and metalinguistic reflection. Follow-up experimental work (e.g., Izumi 2002; Ellis "Learner output, hypothesis testing" 2003 — Studies in Second Language Acquisition) consistently shows producing the L2 triggers noticing that input alone does not. Critique: the original hypothesis over-claimed; output is a *facilitator*, not the primary driver; pushed output without feedback can fossilize errors.

**Interaction (Long 1996):** The strongest empirical record of the three. Keck et al. (2006) meta-analysis of 14 quasi-experimental interaction studies found large effects on immediate posttests for interaction-driven treatment vs comparison conditions. Mackey & Goo (2007) synthesized 28 studies: negotiation of meaning produces large positive effects on acquisition vs no interaction. Interaction works because it bundles input + feedback + modified output — it is the delivery mechanism for the other two hypotheses.

### What a tutor app should do

The three hypotheses are complementary, not competing. The evidence-backed ordering:
1. **Input is the substrate** — FALA's listen-first A0 loop is defensible for absolute beginners (Weeks 1–2), where production demand creates anxiety with zero payoff.
2. **Interaction early** — even at A0, the learner should be doing *some* constrained production (repeating the phrase, choosing between two options) within the first sessions, because negotiation and feedback require a learner utterance to react to.
3. **Output as diagnostic** — from A1 onward, learner output is the main signal for corrective feedback and gap-noticing. A tutor that never elicits output flies blind.

**FALA verdict: MIXED.** The comprehension-first *sequence* (understand before produce) is defensible and matches graded-input practice. The *duration* is not: staying in Phase 1 (type English only) for "week 1–2+" and deferring all PT production to "mid sessions" delays the feedback loop that interaction research shows is where acquisition consolidates. Move to minimal PT production (single-word or phrase repetition) within 2–3 sessions, not weeks.

---

## 2. Corrective feedback: recasts vs prompts vs explicit correction, timing, and "never reveal the answer"

### The evidence

- **Li (2010), Language Learning 60:309–365, meta-analysis of CF in SLA:** overall medium effect for corrective feedback, **d ≈ 0.64**. CF works. The analysis also found larger effects for explicit feedback types and for classroom/lab studies vs. some naturalistic settings.
- **Lyster, Saito & Sato (2010), Studies in Second Language Acquisition 32:265–302, "Oral Feedback in Classroom SLA: A Meta-Analysis"** (15 classroom studies, N = 827): CF has significant *and durable* effects; **effects are larger for prompts (clarification requests, elicitation, metalinguistic clues) than for recasts**, and strongest on measures eliciting free constructed responses. Recasts (the tutor simply models the correct form) have the weakest classroom effect — learners frequently fail to notice them as corrections.
- **Norris & Ortega (2000), Language Learning 50:417–528, meta-analysis of L2 instruction:** focused instruction yields large gains; **explicit instruction outperforms implicit instruction** (and Spada & Tomita 2010 replicated this pattern). Note the standard caveat: explicit-instruction gains were strongest on *measured, controlled* knowledge; durability and spontaneous use are weaker — but the burden of proof is now on pure-implicit advocates.
- **Timing:** A 2023 systematic review (Front. Psychol., "Optimal timing of treatment for errors in second language learning", PMC9995700, 20 studies 2006–2021) found **no definitive answer** on immediate vs delayed — results vary by modality and explicitness. But a 2026 Frontiers in Education in-the-wild LLM-chatbot experiment (66 L2 English learners, one semester) found **no significant difference in learning gains** between immediate and post-conversation feedback, while **immediate feedback improved user experience**. A widely cited L2 classroom figure (Shrum 1985): teachers' post-response wait time is ~0.73 s — correction that arrives before the learner has finished thinking suppresses self-repair.

### Does "never reveal the correct answer" hold up?

**No — it is contradicted, and it contradicts the rest of FALA's own design.**

1. **The evidence favors *prompts* (hints, elicitation) over recasts for targeted errors — but prompts as a *second* move, not an infinite one.** Prompt-based CF works because the learner retrieves or constructs the form. However, the literature nowhere supports withholding the answer indefinitely. A learner who cannot produce the form after one or two elicitations needs the model (input again), or they exit the exchange having learned nothing except that they failed. That is the exact failure mode: "learners stuck without the answer."
2. **FALA is internally inconsistent:** Rule 2 of the A0 loop says "If correct: … that means [translation]" — the answer *is* revealed on success — and the Session Flow says "always model the correct Portuguese version." Only the wrong-answer path withholds. So the app already acknowledges modeling is essential; the rule only bites when the learner needs it most.
3. **Retrieval-practice research complicates but does not rescue the rule:** unsuccessful retrieval followed by feedback still beats no retrieval (the "pretesting effect"; Kornell et al. 2009; Yang et al. 2021 meta-analysis, Psychological Bulletin — quiz repetitions with corrective feedback g = 0.537 vs g = 0.374 without). But the feedback must arrive; the effect is not "guess forever."
4. **For a computer tutor specifically:** the learner has no peer to negotiate meaning with and no ability to look at the tutor's face to notice a recast. A recast in a chat window is nearly invisible (Lyster et al.'s core classroom finding). Text chat requires *more* explicitness, not less.

**FALA verdict: CONTRADICTED.** Replace with a two-strike protocol (below). Hints/prompts first — that part is well supported (prompts > recasts) — but reveal after the second failed attempt, and always model the correct form for meaning-breaking errors immediately.

**FALA's priority-based correction (meaning-breaking errors immediately, minor ones noted and batched): SUPPORTED.** This matches the consensus that errors impeding comprehension warrant immediate treatment while minor morphosyntactic slips can be noted without interrupting flow — with one caveat: batched corrections should come as explicit corrections with models, not just a list.

---

## 3. Retrieval practice and spaced repetition

### The evidence

- **Testing effect:** Roediger & Karpicke (2006, Psychological Science): one practice test + study beat re-study at a one-week delay (61% vs 40% idea-unit recall in the testing-vs-restudying comparison). Dunlosky et al. (2013, Psychological Science in the Public Interest) rated **practice testing and distributed practice the only "high utility" techniques** among ten studied.
- **Language-specific spacing:** **Kim & Webb (2022), Language Learning 72:269–319** meta-analysis: 98 effect sizes, 48 experiments, N = 3,411 — **spaced practice significantly outperforms massed for both vocabulary and grammar** in L2 learning. This is the strongest direct endorsement of FALA's SM-2 scheduler.
- **Expanding vs equal intervals:** mixed and mostly small. Karpicke & Roediger (2007): expanding retrieval helped short-term retention, but **equally spaced retrieval was at least as good for long-term retention**. Nakata (2015): small but significant expanding advantage; Kim & Webb 2022 found equal and expanding schedules **statistically equivalent overall**. The robust finding is *spacing itself*, not the expansion schedule.
- **Cepeda et al. (2006), Psychological Bulletin:** 839 assessments, 317 experiments — distributed practice improves long-term retention, with optimal gap proportional to retention interval.

### What this means for FALA

**Verdict: SUPPORTED.** Retrieval-based warm-ups ("say the Portuguese, ask for the English") and the SM-2 scheduler sit on the most robust findings in the learning sciences. Two refinements:
- Don't over-invest in interval fine-tuning; equal-ish spacing captures most of the effect. SM-2 is fine.
- The A0 warm-up reviews *sentences*, which is good (context-based retrieval beats isolated word cards), but retrieval should increasingly be **production** (EN→PT) rather than only recognition (PT→EN translation), since productive retrieval shows larger effects for later production use.

---

## 4. Krashen / Comprehensible Input community practice

### What the community actually does

**Dreaming Spanish** (the flagship CI product) measures progress purely in input hours — its method page advertises Krashen by name, "language that's meaningful, understandable, and just challenging enough", and claims ~**1,500 hours** of watch time for native-comparable ability. Learner reports (r/dreamingspanish) confirm comprehension grows dramatically by 600–1,000 hours; the same reports consistently note **speaking lags badly** ("no one is going to be able to speak much after only 600 hours of exposure… it takes thousands of hours to reach a sound conversational level"). FluentU's review headline: "The Best Resource for Comprehensible Input, **But Speaking is Undervalued**."

### Critiques relevant to a tutor app

- **Time economics:** pure-CI gets comprehension gains but defers production for hundreds of hours. Dreaming Spanish can afford this because video consumption is low-effort entertainment. A tutor app has *interactive* time — the scarcest, most feedback-rich medium — and spending it all one-way (tutor talks, learner translates to L1) wastes its structural advantage.
- **The Frontiers 2025 critique** (cited above) argues static i+1 is exactly what adaptive/AI tutors can *replace*: per-learner calibration instead of one-size input streams.
- **Krashen's zero-grammar stance** has never survived meta-analytic scrutiny: Norris & Ortega (2000) and Spada & Tomita (2010) both found explicit instruction beats implicit on targeted forms. The honest synthesis: CI advocates over-claim; explicit instruction helps most for adult learners on morphosyntax that low-frequency input won't supply (e.g., pt-PT clitics *o/a/lo/la*, personal infinitive, *estou a falar* vs *falo*).

**FALA verdict: MIXED.** The listen-first on-ramp and words-in-scenario-sentences are well supported. The **blanket "no grammar explanations, even at A1/A2"** is contradicted — FALA's own level table already promises "A1: Explain grammar in English," which conflicts with Rule 5's "Never explain verb conjugations, noun genders." Resolve the contradiction: micro-explanations (one sentence, one rule, immediately re-anchored in the example sentence) are evidence-supported; lecture-style grammar blocks are not needed.

---

## 5. CEFR adaptation, i+1, frequency-based leveling

### The evidence

- **The 98% coverage rule (Hu & Nation 2000; Nation 2006; replicated Kremmel 2023, Language Learning):** learners need ~**98% vocabulary coverage** of running text for adequate comprehension and guessing from context; 95% is the minimum for basic comprehension. Unassisted reading/listening for acquisition fails below that.
- **Graded input works because it enforces coverage:** graded readers suit learners up to ~3,000 word families (Nation); frequency-ordered syllabi put the first 1,000–2,000 families where the returns are maximal (top 1,000 word families ≈ 80–85% of casual spoken coverage in most languages).
- **CEFR levels are descriptors, not acquisition sequences** — fine as a course scaffold, but the app's real leveling tool should be *coverage*: does this session's input stay within ~95–98% known vocabulary, with 2–5 unknown items?

**FALA verdict: SUPPORTED.** The A0 target of the 1,000 most common words in scenario sentences, 2–4 new sentences/session, and level-gated vocabulary are all evidence-aligned (the `max_new_words_per_session: 5` guardrail matches functional-load thinking). One gap: FALA has no mechanism enforcing *coverage* of the listening input itself — the tutor can drift into unknown constructions. Prompt change: instruct the tutor to reuse known vocabulary ({vocabulary}) for ≥95% of its PT output and treat anything new as a deliberately taught item.

---

## 6. Speaking anxiety, wait time, and "never push voice"

### The evidence

- **Foreign language speaking anxiety (Horwitz, Horwitz & Cope 1986; MacIntyre 2017)** reliably correlates negatively with oral performance (Woodrow 2006: moderate negative correlations; Kitano 2001) and drives avoidance. Anxiety reduces fluency, accuracy, and complexity.
- **AI conversation partners reduce that anxiety:** a 2025 mixed-methods study (Humanities & Social Sciences Communications, nature.com/articles/s41599-025-05550-z) found AI conversation bots enhanced L2 speaking **and reduced speaking anxiety** — the low-stakes, non-judging interlocutor is precisely what anxious learners need. A randomized field experiment in Language Learning & Technology found similar comfort advantages of GenAI agents over human partners.
- **Wait time (Rowe 1986; Shrum 1985):** teachers average 0.7–0.9 s of wait time after a question; **3–5 seconds is optimal** for both wait-time-1 (question → answer) and wait-time-2 (answer → teacher reaction). In L2 classrooms post-response wait time is even shorter (0.73 s). Extending wait time increases response length, voluntary responses, and reasoning.
- **Feedback timing experiment with LLM chatbots (Frontiers in Education 2026):** immediate feedback improved user experience and produced equal gains — in a *chat* context. For voice, interrupting the learner mid-attempt is the error; the corrective move is longer wait time plus feedback after the attempt completes.

### Is "never push voice" right?

**MIXED.** The *rationale* (don't create pressure; typed input first) is supported — anxiety suppresses performance and acquisition, and an environment that never forces speech is a feature. But two problems:
1. **"Never" removes the scaffold.** Anxious learners avoid voice indefinitely without an external prompt; research on avoidance shows self-initiated escalation rarely happens. The supported design is *graduated invitation*: normalize voice early ("feel free to use /voice anytime — mistakes are fine here"), and after typed successes, offer a *zero-stakes* first speaking step (repeat one known phrase aloud, no transcription judgment).
2. **The bot is the safest possible audience.** The evidence that AI partners lower FLSA argues for *earlier* voice-onset with the bot than with humans — the exact opposite of indefinite deferral.

**FALA verdict: MIXED.** Keep "typed first" as default, but add active (gentle) invitation: after the first consistent typed successes, propose a single-phrase voice repetition; never gate progress on it.

---

## 7. Duolingo-style and pure-input critiques

### The evidence

- **Duolingo's own best-case study (Jiang, Rollinson, Plonsky, Gustafson & Pajak 2022, Foreign Language Annals, n=225):** learners finishing the beginning-level Spanish/French courses reached **Intermediate Low reading, Novice High listening** — comparable to US university students after **four semesters**. Caveats: only receptive skills tested (no speaking/writing), self-selected participants, and Duolingo-funded.
- **The earlier independent Vesselinov & Grego study (2012):** ~34 hours of Duolingo ≈ one college semester, but the median learner used it only ~154 hours in the study window and still fell below the second-semester cutoff; typical learners plateau at low-reading proficiency. Independent reviews (Loewen et al. 2019 Turkish case study; Loewen et al. 2020 Babbel) show app gains are real but modest, largely receptive, and strongly time-on-task dependent.
- **Structural critiques:** app drills build *recognition*, not retrieval-in-production; sentence-assembly is not conversation; gamification optimizes engagement, not acquisition (streaks ≠ coverage of high-frequency vocabulary in communicative contexts).
- **Pure-input critiques:** see §4 — comprehension grows, production lags for hundreds of hours; no feedback loop on learner errors.

### Where FALA already differs (correctly)

FALA's rejection of fill-in-the-blank gamification and its conversation-first framing put it on the interaction-hypothesis side of this literature. Its risk is not becoming Duolingo — it is becoming **Dreaming Spanish with a text box**: input-heavy, feedback-light, production-deferred.

**FALA verdict: SUPPORTED** (avoiding Duolingo-style drilling and streaks is consistent with the evidence that app drills alone produce receptive-only gains), with the warning above.

---

## Verdict summary per design decision

| # | FALA design decision | Verdict | Key evidence |
|---|---|---|---|
| 1 | Comprehension-first (listen → type EN) for absolute beginners | **Supported** (as an on-ramp) | Input necessity; graded-input practice |
| 2 | Deferring all PT production to "mid sessions" (weeks) | **Contradicted** | Keck et al. 2006; Mackey & Goo 2007 (interaction effects); Swain's noticing function |
| 3 | "No grammar explanations, ever" | **Contradicted** for A1+; **mixed** for A0 weeks 1–2 | Norris & Ortega 2000; Spada & Tomita 2010; Frontiers 2025 CI critique |
| 4 | "Never reveal the correct answer" | **Contradicted** | Li 2010 (CF d≈0.64); Lyster et al. 2010 (prompts work, but as bounded moves); pretesting effect requires eventual feedback (Yang 2021); classroom recasts fail when unnoticed |
| 5 | Priority-based error correction (meaning-breaking immediate, minor batched) | **Supported** | Lyster et al. 2010; CF timing review 2023 (no harm in brief delay for minor forms) |
| 6 | Retrieval practice warm-ups + SM-2 spaced repetition | **Supported** | Roediger & Karpicke 2006; Dunlosky 2013; Kim & Webb 2022; Cepeda 2006 |
| 7 | Expanding (SM-2) intervals specifically | **Mixed** (spacing robust, expanding schedule ≈ equal) | Karpicke & Roediger 2007; Kim & Webb 2022 |
| 8 | Words embedded in scenario sentences (never isolated) | **Supported** | Nation's vocabulary-in-context; 98% coverage research (Hu & Nation 2000; Kremmel 2023) |
| 9 | Frequency-based 1,000-word A0 syllabus | **Supported** | Nation 2006; graded-reader coverage data |
| 10 | "Never push voice" | **Mixed** | FLSA literature (Horwitz 1986); AI bots reduce FLSA (Nature HSSC 2025) → earlier low-stakes voice warranted |
| 11 | No Duolingo-style drills/gamification | **Supported** | Jiang 2022 (receptive-only outcomes); Vesselinov & Grego 2012 |
| 12 | No open-ended questions at A0 (phrase-first) | **Supported** | Anxiety reduction; task-supported scaffolding |

---

## Concrete prompt changes

### 1. Replace the "never reveal" rule with two-strike correction (highest priority)
In `prompts/system.md` § Error Correction, replace "CRITICAL RULE: Never reveal the correct answer directly" with:

> **Correction protocol (two strikes):**
> 1. **First attempt, wrong:** react as a prompt — clarify, elicit, or give a focused hint ("quase — think of the verb *ter*"). Never just model silently.
> 2. **Second attempt, wrong or stuck:** give the correct answer plainly, plus a one-line reason, and ask the learner to repeat it: "It's *eu tenho fome* — Portuguese uses *ter* (have), not *ser*. Your turn: say it."
> 3. **Always end a corrected exchange with the learner producing the correct form once.**
> Minor slips (article, typo, pronunciation): just model the correct version in your reply and move on — don't stop the conversation.

### 2. Start minimal production in session 1–3 (not "mid sessions")
In § A0 Method Rule 4, change the progression so that Phase 1 already includes PT *repetition*: after a correct EN translation, ask the learner to say/type the Portuguese sentence immediately ("Agora tu: repete"). Keep translation-first, but make every learned sentence get produced at least once per session. Recognition-only loops waste the interaction advantage.

### 3. Allow one-line micro-grammar
Replace Rule 5 ("Never explain…") with:

> **Rule 5: Micro-explanations only.** No grammar lectures. But when a pattern repeats across sentences (e.g., *a sopa* is feminine; *estou a falar* for ongoing actions), give a one-sentence rule in English and immediately anchor it in the next example. From A1 on, brief grammar explanations are expected — never more than 2–3 sentences, always followed by a usage example.

### 4. Add a vocabulary-coverage constraint
In the system prompt's level instructions:

> Reuse vocabulary the learner already knows for ≥95% of your Portuguese. Any unfamiliar word is either (a) one of this session's ≤5 taught items, used in a clear context, or (b) not used. Do not drift above the learner's level in free conversation.

### 5. Add graduated voice invitation
Replace "Never push voice" with:

> After the learner has produced typed Portuguese correctly several times in a session, offer once: "Se quiseres, tenta dizer a frase em voz alta (/voice) — sem pressão." Never require voice, never repeat the offer twice in a session, and treat voice attempts as success regardless of transcription accuracy on the first try.

### 6. Make warm-up retrieval production-oriented
In Rule 7, ask for PT production of reviewed sentences ("Diz em português: I'll order a soup"), not only PT→EN recognition, and let the SM-2 due-words from `{vocabulary}` drive which sentences to revisit.

### 7. Wait-time instruction (voice path)
Add one line to the voice section: after asking a question in voice mode, do not re-prompt or answer for the learner — give them time to respond.

---

## Reference list

- Li, S. (2010). The effectiveness of corrective feedback in SLA: A meta-analysis. *Language Learning*, 60, 309–365.
- Lyster, R., Saito, K., & Sato, M. (2010). Oral feedback in classroom SLA: A meta-analysis. *Studies in Second Language Acquisition*, 32, 265–302.
- Norris, J. M., & Ortega, L. (2000). Effectiveness of L2 instruction: A research synthesis and quantitative meta-analysis. *Language Learning*, 50, 417–528.
- Spada, N., & Tomita, Y. (2010). Interactions between type of instruction and type of language feature. *Language Learning*, 60, 263–308.
- Kim, S. K., & Webb, S. (2022). The effects of spaced practice on second language learning: A meta-analysis. *Language Learning*, 72, 269–319.
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks. *Psychological Bulletin*, 132, 354–380.
- Karpicke, J. D., & Roediger, H. L. (2007). Expanding retrieval practice promotes short-term retention, but equally spaced retrieval enhances long-term retention. *JEP: LMC*.
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. *Psychological Science*, 17, 249–255.
- Dunlosky, J., et al. (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest*, 14, 4–58.
- Yang, C., et al. (2021). Testing (quizzing) boosts classroom learning: A systematic and meta-analytic review. *Psychological Bulletin*, 147, 399–435.
- Nakata, T. (2015). Effects of expanding and equal spacing on second language vocabulary learning. *SSLA* (and Nakata 2017, retrieval practice).
- Hu, M., & Nation, P. (2000). Unknown vocabulary density and reading comprehension. *Reading in a Foreign Language*, 13. Replicated: Kremmel (2023), *Language Learning*.
- Nation, I. S. P. (2007). The four strands. *Innovation in Language Learning and Teaching*, 1, 2–13.
- Swain, M. (1995). Three functions of output in second language learning. In *Principles and Practice in Applied Linguistics*.
- Long, M. H. (1996). The role of the linguistic environment in SLA. In *Handbook of SLA*.
- Keck, C. M., et al. (2006). Accounting for variability in the acquisition of L2 formulas (interaction meta-analysis), in Norris & Ortega (Eds.), *Synthesizing Research on Language Learning and Teaching*.
- Mackey, A., & Goo, J. (2007). Interaction research: A meta-analysis, in Mackey (Ed.), *Conversational Interaction in SLA*.
- Rowe, M. B. (1986). Wait time: Slowing down may be a way of speeding up. *Journal of Teacher Education*, 37, 43–50.
- Shrum, J. L. (1985). Wait time in L2 classrooms (post-response wait time ≈ 0.73 s).
- Horwitz, E. K., Horwitz, M. B., & Cope, J. (1986). Foreign language classroom anxiety. *Modern Language Journal*, 70, 125–132.
- Frontiers in Psychology (2025). Beyond comprehensible input: A neuro-ecological critique of Krashen's hypothesis. doi:10.3389/fpsyg.2025.1636777
- Frontiers in Psychology (2023). Optimal timing of treatment for errors in second language learning — systematic review of CF timing. PMC9995700.
- Frontiers in Education (2026). Personalized language learning with an LLM chatbot: Effects of immediate vs. delayed corrective feedback. doi:10.3389/feduc.2026.1703664
- Jiang, X., Rollinson, J., Plonsky, L., Gustafson, E., & Pajak, B. (2022). Evaluating the reading and listening outcomes of beginning-level Duolingo courses. *Foreign Language Annals*. doi:10.1111/flan.12600
- Vesselinov, R., & Grego, J. (2012). Duolingo effectiveness study. City University of New York.
- Humanities & Social Sciences Communications (2025). Investigating the role of AI-powered conversation bots in enhancing L2 speaking skills and reducing speaking anxiety. doi:10.1057/s41599-025-05550-z
- Dreaming Spanish (dreaming.com/method): input-hours progress model, ~1,500-hour target claim.

## Open questions for FALA specifically

- No pt-PT-specific CF research exists (all CF meta-analyses are ESL/other-L2). Effects are assumed to transfer; the pt-PT-specific traps (clitic placement, *a + infinitive* vs gerund) are high-error areas that deserve prompt-level priority lists.
- LLM-specific CF studies are 2024–2026 vintage and thin; the Frontiers 2026 chatbot timing study (no gain difference, better UX with immediate) is the closest analogue to FALA's design.
