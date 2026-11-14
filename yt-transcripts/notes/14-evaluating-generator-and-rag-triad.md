# 14 — Evaluating the RAG Generator & the Full Pipeline (RAG Triad)

> Source: [Evaluating RAG: Testing the Generator & Full Pipeline with the RAG Triad](https://www.youtube.com/watch?v=PATGn2XhmCY) (CampusX). Notes are based only on the video transcript.

## TL;DR
- **Generator (in isolation):** **faithfulness** (reference-based: answer claims vs the golden context) and **answer relevancy** (reference-free: answer claims vs the question). Baseline F 0.91 / AR 0.73. After **prompt refinement**, F 0.96 / AR 0.92.
- **Pipeline (retriever + generator), the RAG triad:** faithfulness, answer relevancy and **contextual relevancy**, now with the **retriever's** context. Result: F ≈ 0.92, AR ≈ 0.86, **CR ≈ 0.42**.
- **The curious case:** retriever recall 0.99 and precision 0.89, yet contextual relevancy is only 0.42. The cause is **noise *inside* chunks**. Try smaller chunks.

---

## Building the generator (`src/generator.py`)
- LLM: **GPT-4o mini**, `temperature = 0`.
- Prompt: "You are a helpful teaching assistant for a course on LLM evaluations. Answer the student's question **only from the context** provided below."
  - Rules: use only the context, no outside knowledge.
  - If the context is insufficient, say *"I don't have enough information in the course material to answer that."*
  - Keep it clear and concise.
- LangChain chain: `prompt | llm | StrOutputParser()`, wrapped in `generate(query, context)`.
- Smoke test with a dummy context: "What is online eval?" gets a correct answer.

## Generator failure modes and metrics

| Failure mode | Example | Metric |
|---|---|---|
| **Unfaithful (hallucinated)**: adds information not in the context | Q: "Does the CampusX AI Engineering program include live classes?" Context: recorded lessons, assignments, projects, weekly doubt sessions (nothing about live classes). Answer: "Yes, two live classes every week…" ❌ (cf. Air Canada) | **Faithfulness** |
| **Faithful but irrelevant**: sticks to the context but doesn't answer the question | Answer: "The program includes coding assignments, projects, recorded lessons and weekly doubt sessions." This is faithful but doesn't address *live classes*. Better: "The context does not confirm live classes; it only mentions…" | **Answer relevancy** |

> **Faithful ≠ correct.** If the retrieved context is wrong, a faithful generator gives a wrong answer *from it*. Faithfulness only promises "nothing added beyond the context".

Other generator metrics (**citation accuracy, completeness, correctness**) are deferred to the **application level**.

## How the metrics are computed (DeepEval, LLM-as-a-judge)

### Faithfulness (reference-based at the component level)
- **Golden dataset:** *question → **golden context*** (all chunks that discuss the topic).
- Steps:
  1. Send the question and golden context to the **generator** (no retriever: **isolation**).
  2. The judge **splits the answer into claims**.
  3. For each claim, check whether it is **present in the golden context**.
  4. Faithfulness = supported claims / total claims (e.g. 2/3 = 0.67 for "What does it mean for a benchmark to get saturated?"). Average over questions.
- Contrast with **contextual recall**, the reverse direction: there, the *ideal answer's* claims are checked against the *retrieved* context.

### Answer relevancy (reference-free)
- Steps:
  1. The judge **splits the answer into claims**.
  2. For each claim, ask: **does it help answer the question?**
  3. Score = relevant claims / total claims.
- Example: an answer about saturation adds "Separately, contamination is test data leaking…", giving 2/3 relevant = 0.67.
- The dataset is used only to **generate answers**, **not as a reference**.

### Q&A
- **Same or different LLM for splitting and judging?** The same. Each API call is independent, so there's no benefit in using two models.
- **Judge errors (false positives/negatives)?** Yes, judges make mistakes. But a judge's bias is **consistent across runs**, so comparisons stay fair ("a bad pitch is bad for both teams"). Use the **strongest judge you can afford**; eval sample sizes are small.
- **Is the number of claims a hyperparameter?** No.
- **Relevancy ≠ correctness.** Correctness is a separate metric (next class).
- **Non-RAG apps?** DeepEval has multi-turn chatbot metrics and **custom metrics** (G-Eval, next class).

## Golden dataset for faithfulness
- `export_chroma_chunks` exports all **862 chunks** to JSON. Claude then generates **one question and golden-context pair at a time**, with **manual review** by the instructor (who taught the classes). Result: **15 rows** in `goldens/faithfulness_dataset.json`.
- Alternatives: manual authoring, or DeepEval's Synthesizer (not used yet).

## The generator eval (`evals/eval_generator.py`)
- For each row: `LLMTestCase(input=question, actual_output=generate(question, golden_context), retrieval_context=golden_context)`.
- Metrics: `FaithfulnessMetric`, `AnswerRelevancyMetric` (judge GPT-4o mini, a threshold, `include_reason=True`). Then `evaluate(...)`.
- DeepEval runs test cases **in parallel**, so it's fast.
- Run: `python -m evals.eval_generator`.

| Run | Faithfulness | Answer relevancy |
|---|---|---|
| Baseline prompt | **0.91** | **0.73** |
| Refined prompt (3–4 iterations) | **0.96** | **0.92** (14/15 pass) |

- **Why faithfulness is high from the start:** modern LLMs follow "answer only from the context" instructions well. **Answer relevancy is harder.**
- **Generator improvement levers** are limited:
  1. **A better model** (better instruction following)
  2. **The system prompt.** Analyse the failing cases and their reasons, give them to Claude, and refine. Additions in the final prompt:
     - "Do not strengthen or overstate claims."
     - "If the context says two things are different, do not upgrade that to 'separate methods' or strong wording."
     - "The context is an informal lecture transcript: synthesize and rephrase what is there; do not require the question's exact wording to appear."
- ⚠️ **Overfitting risk:** tuning the prompt too tightly to one golden set may fail on real retrieved context. The pipeline eval checks this.
- Results are **reproducible** within small ± variation.

### Experiment tracking with Confident AI
- `deepeval view` (login plus an API key) logs the run to **Confident AI** (DeepEval's parent company): pass/fail per row and details. You can also store configs (prompt, chunk size). This is MLflow-like **experiment tracking** (more of an LLMOps topic).

## Component level: complete ✅
Four metrics so far: **contextual recall and contextual precision** (retriever), **faithfulness and answer relevancy** (generator).

---

## Building the pipeline (`src/rag_pipeline.py`)
- `RAGPipeline` class: **reranking retriever**, then context joined into a string, then `generate(question, context)`, then the answer.
- Test: "What is drift and why does it matter after deployment?" gives a sensible answer from 5 retrieved chunks.

## Pipeline level: the RAG triad
```
          Question
          /      \
 Contextual       Answer
 relevancy        relevancy
        /          \
   Context ─────── Answer
        Faithfulness
```

| Pair | Metric | Type |
|---|---|---|
| Question ↔ context | **Contextual relevancy** | Reference-free |
| Context ↔ answer | **Faithfulness** | (now with the *retrieved* context) |
| Question ↔ answer | **Answer relevancy** | Reference-free |

- **What's different from component level?** The **context now comes from the retriever**, not the golden dataset. The calculation is the same, but the scores differ.

### Contextual relevancy
1. Send the question to the **retriever**, which returns k = 5 contexts.
2. The judge **splits every context into claims** (e.g. 15 claims in total).
3. For each claim, ask: **is it relevant to the question?** (yes/no)
4. Score = relevant claims / total claims (e.g. 10/15). Average over questions.
- Reference-free: the dataset is only used for questions.

## The pipeline eval (`evals/eval_rag_pipeline.py`)
- Uses `faithfulness_dataset.json` for **questions only**: `input = question`, `actual_output` and `retrieval_context` **from `RAGPipeline`**.
- Metrics: Faithfulness, AnswerRelevancy, **ContextualRelevancy**.

| RAG triad metric | Score |
|---|---|
| Faithfulness | **≈ 0.92–0.93** |
| Answer relevancy | **≈ 0.86** (the refined prompt **generalizes**, so it wasn't overfit) |
| **Contextual relevancy** | **≈ 0.42–0.43** ⚠️ |

### The curious case: a good retriever with low contextual relevancy
- Re-running the retriever eval gives **recall 0.99, precision 0.89**. So why is CR only 0.42?
- **Recall:** were all the needed contexts fetched? ✅
- **Precision:** what fraction of the **chunks** are useful? ✅ (A chunk counts as useful even if only one of its sentences helps.)
- **Contextual relevancy:** what fraction of the **claims inside the chunks** are relevant? Here many chunks contain 1–2 useful sentences plus lots of unrelated text.
- ➡️ **Noise *within* chunks.** Fix: **reduce the chunk size / overlap**. Watch for a **trade-off**: the other four metrics may drop.
- Pragmatic view: if faithfulness, answer relevancy, recall and precision are all good, a lowish CR can be **acceptable**, because the answers are still good.

## Status and next steps
- ✅ Component level and ✅ pipeline level are done.
- Next: **application level**:
  - **Quality:** correctness, completeness, CampusX **style** (custom metrics via **G-Eval**)
  - **Safety evals**
  - **Ops evals**
- Then regression testing and online evals.
