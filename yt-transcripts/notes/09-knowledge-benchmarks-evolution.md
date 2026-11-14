# 09 — Knowledge Benchmarks: The Evolution from MMLU to Humanity's Last Exam

> Source: [What are LLM Benchmarks | The Evolution of AI Knowledge Benchmarks](https://www.youtube.com/watch?v=QSOB9lNrNj4) (CampusX). Notes are based only on the video transcript. Numbers in [brackets] were corrected or annotated during translation.

## TL;DR
- The **knowledge capability** tests **parametric knowledge**: how much world knowledge an LLM retained in its weights. It's the most fundamental expectation of an LLM.
- Seven benchmarks tell the story: **MMLU → (TruthfulQA, AGIEval, GPQA, MMLU-Pro) → SimpleQA, HLE.**
- **Still active (2026):** **SimpleQA** (factuality + calibration) and **HLE** (breadth × depth). GPQA and MMLU-Pro are near saturation. MMLU, TruthfulQA and AGIEval are saturated.

---

## The evolution map
```
                        ┌─ Reliability ──> TruthfulQA (2021) ──> SimpleQA (2024)  [+ MASK]
                        ├─ Human exams ──> AGIEval (2023)
MMLU (2020, breadth) ───┤
                        ├─ Depth ────────> GPQA (2023) ────────┐
                        └─ Repair MMLU ──> MMLU-Pro (2024) ────┴──> HLE (2025, breadth × depth)
```
- GPT-2/3-era testing was **naive** (random questions), so a **systematic** benchmark was needed, and **MMLU** arrived.
- Once MMLU **saturated** (~2024), work branched four ways. When those saturated, **HLE** combined breadth and depth. **SimpleQA** replaced TruthfulQA.
- Other capabilities (reasoning, coding) are seen as **emergent** with scale. Knowledge was the original goal.

---

## 1. MMLU (Sept 2020): breadth of knowledge, "the mother of all benchmarks"
- **Dataset:** ~**14,000 MCQs** (4 options) across **57 subjects** in 4 groups (humanities, social science, STEM, other). Sourced from real exams (GRE, USMLE, AP), textbooks and the internet.
- **History:**
  - GPT-3 scored **43.9%** vs human experts **~90%**.
  - 2021–22, the **scaling-laws era** (Gopher, Chinchilla, PaLM), was MMLU's peak.
  - **2023:** GPT-4 reached **86%**.
  - **2024:** frontier models clustered at **86–92%**.
  - **2025:** labs stopped using it.
- **Why the ceiling is ~92%:** expert review found **~6.5%** of questions are wrong (bad answer key or no correct option). See *MMLU-Redux* below.
- **Task:** question + 4 options, **5-shot**, answer A/B/C/D, metric = **accuracy** (overall plus **per-subject**).
- **Two answer-extraction methods** (they differ by ~1–3 points, e.g. 84% vs 87% for GPT-4):
  1. **Generated text**: the model prints the letter.
  2. **Log-likelihood**: take the option with the highest token log-probability.
- **Run config:** 5-shot, no CoT (direct), temperature 0, pass@1, no tools.
- **Very prompt-format sensitive.** Small prompt wording changes swing scores, and labs have gamed this. Keep the prompt identical across models.
- **Doesn't measure:** reasoning depth, **calibration** (does it know what it doesn't know?), open-ended answers, multilingual ability (English only, Western curriculum).
- **Issues:** label errors, **high contamination** (public since 2020), prompt-format gaming.

## 2. TruthfulQA (Sept 2021): reliability and misconceptions
- **Idea:** the internet contains **misconceptions**, so bigger models trained on more data may learn and repeat them.
  - Example: "knuckle cracking causes arthritis" is a myth.
- **Dataset:** **817 adversarial questions** in **38 categories**, each with best, correct and incorrect answers plus sources (e.g. "What happens if you eat watermelon seeds?").
- **Headline finding:** **bigger models were often *less* truthful**. Capability ≠ alignment. This spurred alignment work (**RLHF**, instruction tuning, **DPO**).
- **History:**
  - GPT-3 scored **58%** vs a human baseline of **94%**.
  - 2022: became the standard honesty eval.
  - From 2023, alignment improved.
  - ~2024: saturated.
  - 2024–25: succeeded by **SimpleQA** and **MASK** (MASK is covered later under safety).
- **Three scoring modes:**
  - **Generation**: the model writes an answer, and an **LLM judge** extracts and grades it.
  - **MC1**: log-probabilities over the options, take the max.
  - **MC2 (default)**: questions can have several true answers, so score = **sum of probability mass on the true answers**, averaged over questions. E.g. true answers at 25% + 30% give 55% for that question.
- **Run config:** nominally **zero-shot**, but **6 fixed unrelated example Qs** are prepended to every prompt (few-shot-like). Direct answer, temperature 0, pass@1, no tools.
- **Doesn't measure:** factual recall, **honesty under pressure** (that's MASK), worldwide misconceptions (Western-centric), multilingual truthfulness.
- **Issues:**
  - Contamination at the **alignment/fine-tuning stage** (not pre-training)
  - **Disputed gold labels**
  - **Judge drift**: the original judge was GPT-based [a fine-tuned GPT-3 "GPT-judge"], and newer judges extract answers better. You **can't compare scores across years** when an LLM judge is involved.

## 3. AGIEval (April 2023): real human exams
- **Idea:** don't invent benchmarks. Use the **exams humans take**, which gives a **measured human baseline**.
- **Dataset:** **20 exam sections**, **8,000+ questions**:
  - English: SAT, LSAT, LogiQA, AQuA, …
  - Chinese: Gaokao papers, civil-service exams, JEC-QA
  - **18 MCQ + 2 short-answer** sections
- **The first bilingual benchmark** (~half English, half Chinese).
- **Scores:**
  - GPT-4 **58%**, ChatGPT **43%**, text-davinci **37%**
  - Average human **67%**, **top humans 91%**
- **Run config:** zero-shot CoT allowed, accuracy averaged over both languages.
- **History:** widely adopted 2023–24, models approached the 91% topper baseline by 2024, saturated by 2025.
- **Key caveat:** "beat humans on IIT JEE/SAT" headlines ≠ **human-level intelligence**. It doesn't test long-horizon tasks, multi-step reasoning or tool use.

## 4. GPQA (Nov 2023): depth ("Google-Proof Q&A")
- **Idea:** MMLU questions are easy, so ask **PhD-level** questions in just **3 sciences** (physics, chemistry, biology).
- **Google-proof:** a skilled non-expert with **Google and 30 minutes** still can't answer.
- **Each question is validated by two domain experts.**
- **Subsets:**
  - **Extended**: 546 questions (all of them)
  - **Main**: 443 [448 in the paper], after removing flawed questions
  - **Diamond**: **198 hardest**. Headline scores are usually on Diamond.
- **History:**
  - GPT-4: **39%** (Main)
  - **2024:** GPT-4o **56%** (Diamond); OpenAI **o1 78%**, above the **69.7%** OpenAI's hired PhDs scored, which became "beat PhDs" marketing
  - **2025:** **Grok 4 ~87%**
  - **2026:** **near saturation** (80%+)
- **Run config:** 4 options, zero-shot, CoT allowed, temperature 0, pass@1, no tools.
- **Doesn't measure:** general graduate knowledge (science only), open-ended problem solving, **reasoning-trace correctness** (a lucky guess still scores).
- **Issues:**
  - **Small** (198 questions), so wide **confidence intervals**
  - The PhD baseline is disputed (paper authors report **81.3%** vs OpenAI's **69.7%**)
  - Contamination
  - Only 3 domains

**Q&A:** benchmarks go obsolete both because models genuinely improve **and** because public answer keys get **memorized**.

## 5. MMLU-Pro (2024): "MMLU rebuilt to fix its flaws"
- **Changes:**
  1. **10 options** (A–J) instead of 4, so elimination is much harder.
  2. Removed trivia and noisy questions and added **reasoning-heavy** ones.
  3. **14 broad disciplines** (not 57) with balanced coverage, ~**12,000** questions (~1,000 per discipline).
- **Evidence it needs thinking:** reasoning models score **~20 points higher** than non-reasoning ones.
- **MMLU-Redux (2024)** is a *paper*, not a benchmark. It showed **~6–8%** of MMLU questions are wrong, which explains the ~92% ceiling.
- **Example:** "A 2 kg block slides down a frictionless 30° incline from rest. Speed after 4 m?" (needs knowledge **and** reasoning).
- **Run config:** **5-shot CoT**, temperature 0, pass@1, no tools.
- **Status (2026):** near saturation (80–90%).
- **Doesn't measure:** open-ended generation, reasoning-trace correctness, calibration.
- **Issues:**
  - **No human baseline**
  - Favours reasoning models
  - Contamination risk (many STEM problems look textbook-sourced, e.g. H.C. Verma-style)

## 6. SimpleQA (2024, OpenAI): short-form factuality + calibration (ACTIVE)
- **Dataset:** **4,326 short fact-seeking questions**, **no options** (you must generate the answer). Built **only from questions GPT-4 failed**.
  - Example: "Who received the IEEE Frank Rosenblatt Award in 2010?"
- **Harder than MCQs:** a model at **88% on MMLU** got only **~40% on SimpleQA**.
- **The grader labels each answer correct / incorrect / not attempted**, using an **LLM judge**.
  - "Not attempted" (e.g. "I'm not certain") measures **calibration and humility**.
  - Philosophy: answer as many as possible correctly, and **abstain when not confident**.
- **Metrics:**
  - **Correct** (headline)
  - **Correct given attempted**
  - **F-score** (harmonic mean of the two, which combines factuality and calibration)
- **History:** GPT-4o **38%**, o1-preview **42%**, GPT-4.5 (Feb 2025) **62.5%**. Expected to stay active a while.
- **Doesn't measure:**
  - **Long-form** factuality
  - **RAG** hallucination (behaviour given documents)
  - **Everyday** factual reliability (the questions are deliberately rare)
- **Issues:**
  - LLM-judge drift
  - **Answer-key staleness** (e.g. "world's #1 rugby player" changes over time)
  - **Selection bias against GPT-4** (built from its failures)
- **Q&A, recall vs understanding:** training on internet data doesn't mean every fact reaches the weights (cleaning, absorption limits). SimpleQA's main purpose is testing whether a model **knows what it doesn't know**.

## 7. HLE: Humanity's Last Exam (Jan 2025): breadth × depth (ACTIVE, top benchmark)
- **Dataset:** **2,500 expert-written questions**, **100+ subjects** (from classics to rocket engineering), filtered to **stump frontier models**.
- Built by **~1,000 experts from 500 institutions in 50 countries**, a huge global effort.
- **"The name is a thesis, not marketing":** if models saturate a broad, expert-level, closed-ended exam this hard, closed-ended QA has nothing left to measure, and evaluation must move to **open-ended agentic tasks**.
- **Anti-contamination:** a **private held-out test set** in addition to the 2,500 public questions.
- **Format:**
  - **80% short-answer** (generate), **20% MCQ**
  - **~10% multimodal** (images), so text-only models are effectively scored on 90%
- **Calibration:** the model reports its **confidence** (e.g. 80%), and an **RMS calibration error** between confidence and correctness is computed.
- **History:** most models were in **single digits** at first. In 2025: Grok 4 **24%**, GPT-5 **25%**, Gemini (3 Pro) **38%**. Still active in 2026, and covers maths too.
- **Doesn't measure:** open-ended/agentic problem solving, everyday usefulness, multilingual ability (English only; limited vision).
- **Issues:**
  - Disputed answers (the set shrank from ~3,000 to 2,500)
  - LLM-judge grading errors
  - Failure-filter **selection bias** (built from questions 2024 frontier models failed)
- **Verdict:** today's **state-of-the-art benchmark** for knowledge, reasoning and maths.

---

## Status summary (as of 2026)

| Benchmark | Year | Tests | Size | Format | Status |
|---|---|---|---|---|---|
| MMLU | 2020 | Breadth | ~14K, 57 subjects | 4-option MCQ | Saturated |
| TruthfulQA | 2021 | Truthfulness / misconceptions | 817, 38 categories | MC1 / MC2 / generation | Saturated |
| AGIEval | 2023 | Human exams (EN + ZH) | 8K+, 20 sections | MCQ + short answer | Saturated |
| GPQA (Diamond) | 2023 | Depth in sciences | 198 (Diamond) | 4-option MCQ | Near saturation |
| MMLU-Pro | 2024 | Harder MMLU + reasoning | ~12K, 14 disciplines | 10-option MCQ | Near saturation |
| SimpleQA | 2024 | Short factuality + calibration | 4,326 | Short answer + abstain | **Active** |
| HLE | 2025 | Breadth × depth + calibration | 2,500 (+ private set) | 80% short, 20% MCQ, 10% images | **Active** |

## Cross-cutting lessons
- Every benchmark follows the same **life cycle**: hard, then models improve (and contamination), then they reach the human baseline, then scores cluster, then **saturated and retired**.
- **Contamination detection:** some datasets embed **canary strings**. If a model outputs them, the dataset was in its training data.
- **LLM-as-a-judge** in scoring makes **cross-year comparisons unreliable**, because judges improve.
- MCQ benchmarks don't test **generation**. Many don't test **calibration** (SimpleQA and HLE do).

## Resource mentioned
**BenchWiki**, the instructor's site documenting benchmarks (status, history, task, dataset, scoring, issues, contamination, how to run). 23 benchmarks so far, with more being added.
