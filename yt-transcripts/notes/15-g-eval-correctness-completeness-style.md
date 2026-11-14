# 15 — G-Eval: Judgment-Based Metrics (Correctness, Completeness, Style)

> Source: [Mastering G-Eval: The Deterministic LLM-as-a-Judge Framework Explained](https://www.youtube.com/watch?v=nlyxlKD5cvU) (CampusX). Notes are based only on the video transcript.

## TL;DR
- The five metrics so far (recall, precision, faithfulness, answer relevancy, contextual relevancy) are **count-based**: split into claims, count, take a ratio.
- **Correctness, completeness, style, helpfulness and safety** need **judgment** at the **whole-answer** level.
- **Plain LLM-as-a-judge** ("score 0–10") has **high variance** for two reasons: a loose criterion, and taking the single most likely score token.
- **G-Eval** (2023 paper) fixes both:
  1. A **criterion becomes explicit evaluation steps** (via CoT) plus a rubric.
  2. A **probability-weighted score** over the score tokens' log-probabilities.
- Results on the Doubt Solver:
  - **Correctness** 0.66 → **0.84** (fixed the judge's evaluation steps and rubric)
  - **Completeness** 0.68 → **0.75** (fixed the generator prompt)
  - **Style** 0.54 → **0.74** (fixed both)

---

## Where we are
The offline eval suite is at the **application level**. Today covers **quality** (correctness, completeness, CampusX style). Safety, ops and regression testing are next.

## Count-based vs judgment-based metrics
- **Count-based:** e.g. faithfulness = claims found in the context / total claims (3/4). All five earlier metrics follow this pattern.
- **Judgment-based:** counting fails here.
  - **Style** (e.g. a CampusX *why → what → how* explanation) exists at the **answer level**, not in individual sentences.
  - **Correctness:** an **analogy**, judged in isolation as a claim, looks unrelated to the golden answer and gets wrongly penalized. Correctness must be judged on the **whole answer**.
  - Others: completeness, helpfulness, all **safety** metrics.

## Naive LLM-as-a-judge for correctness
- **Golden dataset:** question + **correct answer** (universally correct, not necessarily what was taught).
- **Judge prompt:** "You are evaluating whether an AI's answer is correct. Given a question, an expected answer and the actual answer… Compare the actual answer against the expected answer and decide how factually correct it is. Give a score from 0 to 10." Average over 15 questions.
- Differences from before: no claim splitting or ratio. **Pure judgment.**

### Why it's unreliable: high run-to-run variance
1. **A loose criterion.** One sentence leaves the judge to interpret "correctness" differently on each independent call. There's no **rule book**.
2. **Taking the argmax token.** If P(7) = 0.40, P(8) = 0.51, P(6) = 0.09, it prints **8**. Next run P(8) = 0.40, P(7) = 0.51, so it prints **7**. Scores jump, and the averages swing (60 → 70 → 75).
   - (Judge mistakes, cost and latency are real too, but they're not the main issue. 15 samples is cheap.)

> Try it yourself: run the naive judge 3–4 times and watch the scores vary a lot.

## G-Eval: how it works
1. **Input:** a metric **name** (e.g. correctness) + a high-level **criterion** ("Compare the actual answer against the expected answer and decide how factually correct it is").
2. **CoT → evaluation steps.** A judge LLM (the paper reports the best results with **GPT-4**) turns the criterion into 4–5 concrete **evaluation steps**: a constitution or rule book.
3. **Build the judge prompt** with the steps (plus an optional **scoring rubric**, e.g. 9–10 / 5–8 / 0–4), the question, expected output and actual output.
   - Example steps: "Compare only factual claims… A claim is wrong only if it contradicts the expected output or is factually false… A factually accurate answer scores high even if shorter… Don't deduct for brevity or omitted points… Additional correct information must never lower the score."
   - This leaves the judge **less room to improvise**, so behaviour is more deterministic.
4. **Probability-weighted score**, instead of reading the printed number:
   - At output time the LLM assigns probabilities over its whole vocabulary (it's autoregressive). Because the prompt asks for 0–10, the **digit tokens** get most of the mass.
   - Take the **top-k tokens' log-probabilities**, **drop non-numeric tokens**, and **renormalize**.
     - Example: 8 → 0.70, 7 → 0.20, 9 → 0.05 (sum 0.95) becomes **0.737 / 0.211 / 0.053**.
   - **Weighted score** = 8 × 0.737 + 7 × 0.211 + 9 × 0.053 ≈ **7.84** (vs argmax **8**).
   - Divide by 10 to get **0.784**, then compare with the **threshold** (e.g. 0.7) for pass/fail.
   - Scores now move slightly (7.4–7.9) instead of jumping (6 ↔ 8).

> **G-Eval = LLM-as-a-judge + (1) criterion → explicit evaluation steps and rubric + (2) a log-prob-weighted score.** That's all.

## G-Eval in DeepEval
```python
correctness = GEval(
    name="Correctness",
    criteria="...",                       # OR evaluation_steps=[...]  (then the CoT step is skipped)
    evaluation_params=[INPUT, ACTUAL_OUTPUT, EXPECTED_OUTPUT],
    rubric=[...],                         # optional: score bands
    model="gpt-4o-mini", threshold=0.7,
    strict_mode=False,                    # False = weighted log-prob scoring (keep it False)
)
evaluate(test_cases=..., metrics=[correctness])
```
- DeepEval has **no built-in correctness metric**, so you use G-Eval.
- **Criterion or your own evaluation steps?**
  - Start with a **criterion** while you're still exploring.
  - Once you understand the failures (after 2–3 runs), supply your **own evaluation steps** (and a rubric). The steps are then **identical on every call**, which means less variance.
- **`strict_mode=True`** disables the weighting and uses the raw score.

## Correctness vs faithfulness
| | Faithful | Not faithful |
|---|---|---|
| **Correct** | ✅ Ideal | Answered from training knowledge, not the context (e.g. the teacher taught it wrong and the model corrected it) |
| **Incorrect** | The teacher taught it wrong and the generator repeated it faithfully | Hallucinated **and** wrong |

The ideal answer is both **correct** (true in the eyes of the world) and **faithful** (grounded in the course).

## Hands-on: `evals/eval_application.py`
- **Golden dataset:** `goldens/correctness_goldens.json`, 15 rows (question, ideal answer, source session), written by a domain expert.
- Loop: send the question to `RAGPipeline` and build `LLMTestCase(input, actual_output, expected_output)`.

### Correctness
| Run | Change | Score | Pass/fail |
|---|---|---|---|
| 1 | Evaluation steps: compare key facts, heavily penalize contradictions, reward matching meaning, "don't penalize omissions" | **0.66** | 8 / 7 |
| 2 | Stricter steps: "**A factually accurate answer must score at least 9** even if shorter, less detailed or covers fewer points. Don't deduct for brevity, missing elaboration, fewer examples or omitted points." Plus an explicit **rubric**: clear factual error = 0–4, mostly correct with 1–2 small inaccuracies = 5–8, all claims correct = 9–10. | **0.84** | 14 / 1 |
| 3 | Re-run, no changes | **0.83** | 14 / 1 (**the same case #7 fails**, which shows determinism) |

- **Diagnosis came from reading the failure reasons:** the golden answers were very thorough, and the judge was penalizing correct but shorter answers. The fix made the judge **lenient on coverage**, because correctness ≠ completeness.

### Completeness
- Idea: if the ideal answer has points A, B, C and the generated answer covers A and B, the judge scores ~7.5/10.
- Same code, plus a **completeness G-Eval** (its own steps and rubric). Both metrics are passed to `evaluate`.

| Run | Change | Score | Pass/fail |
|---|---|---|---|
| 1 | — | **0.68** | 5 / 10 |
| 2 | **Generator prompt fix:** "Answer thoroughly. Identify every distinct part of the question and cover each one… include all relevant points the context provides… If the question has multiple parts or the concept has multiple components, address all of them rather than stopping at the first." Still context-only. | **0.75** | 14 / 1 |

- **Root cause:** the generator was told to be **concise**, which limited coverage.

### Style (CampusX voice), reference-free
- No ideal answer is needed, just a clear **rubric** of the brand style:
  - **Reward** an intuitive, explanatory tone: plain language, the idea before any formula or jargon, technical terms unpacked.
  - **Reward** a direct, conversational register that addresses the student like a CampusX lecture, not a dry or textbook tone.
  - **Reward** a concrete example, analogy or "why it matters" framing where it helps.
  - **Score bands:** 9–10 = clearly the CampusX teaching voice. 5–8 = clear but flat, formal or textbook-like. 0–4 = dry, stiff, jargon-heavy or robotic.

| Run | Change | Score | Pass/fail |
|---|---|---|---|
| 1 | Generator not told about the style | **0.54** | — |
| 2 | **Generator prompt:** "Write in flowing conversational prose, the way a teacher explains out loud, not as a bulleted list (lists only when the question needs enumeration). Explain the intuition first in plain language; briefly unpack technical terms." **Rubric de-over-correction:** "An analogy or concrete example is a **bonus** when the concept is abstract, but a clear, direct, well-explained answer is fully acceptable." | **0.74** | 9 / 6 |

- The judge had **over-weighted** "use analogies", penalizing every answer that lacked one. Fix the judge, not just the app.
- Pushing style much higher may **hurt faithfulness and other metrics**. A threshold of 0.6 may be more reasonable than 0.7.

## Lessons
- **Read the per-case failure reasons.** They tell you whether to fix the **judge** (steps/rubric) or the **app** (generator prompt, retriever, model).
- **Prompt engineering matters.** The right system prompts move eval scores substantially.
- **Supplying evaluation steps + a rubric + weighted scoring** makes judgment metrics **stable and repeatable**.
- G-Eval also covers **coherence, tonality, helpfulness** and **safety** metrics (see DeepEval's G-Eval docs).

## Status
Application-level **quality** done ✅. Next: **safety** and **operations** evals, then regression testing.
