# 13 — Evaluating RAG Retrievers (Hands-On with DeepEval)

> Source: [How to Test RAG Retrievers (Hands-On)](https://www.youtube.com/watch?v=9Dkz3ckRj8c) (CampusX). Notes are based only on the video transcript.

## TL;DR
- A retriever fails in two ways: it **misses** the right context (measured by **recall**) or brings it with **noise** (measured by **precision**). Increasing **k** trades one against the other.
- Both are **reference-based**. The naive method (golden **chunk IDs**) breaks every time you change the chunking, so use a golden set of **question + ideal answer** and **LLM-as-a-judge** metrics: DeepEval's **ContextualRecall** and **ContextualPrecision** (rank-aware).
- Iteration results on 15 goldens: baseline **R 0.80 / P 0.80**, best ≈ **R 0.99 / P 0.85** (bigger chunks, a reranker, a larger embedding model).

---

## Project setup (CampusX Doubt Solver)
```
rag-eval-project/
├── data/      # session transcripts (.vtt) = knowledge base (sessions 1–8)
├── src/       # retriever.py, reranker, generator, pipeline, (UI later)
├── evals/     # eval pipelines (eval_retriever.py, …)
├── goldens/   # golden datasets
└── .env       # OPENAI_API_KEY
```
- `uv init` (Python 3.11), then install **langchain, openai, deepeval, pytest, python-dotenv**.

## Building the retriever (`src/retriever.py`)
1. `load_transcripts`: read the `.vtt` files line by line and **drop the timestamp lines** (they hurt semantic quality). Store the text as LangChain `Document`s with **session metadata** (for citations later).
2. **Chunk:** `chunk_size = 750`, `chunk_overlap = 100` to start (≈800+ chunks).
3. **Embed** with OpenAI `text-embedding-3-small` and store in **Chroma** (`chroma_store/`, created only if it doesn't already exist).
4. `as_retriever` with **k = 5**.
- Smoke test: "What is regression testing?" returns 5 relevant chunks.
- **Q&A: new transcripts?** Add them to `data/`, delete `chroma_store/`, and re-run to re-embed. (In production, decouple ingestion from retrieval. The code is deliberately simple to keep the focus on evals.)

## How retrievers fail, and the metrics

| Failure mode | Example (correct = {1, 13, 15}) | Metric |
|---|---|---|
| **Misses the right context** | Retrieved {27, 28, 29} | **Recall** = correct retrieved / all correct (e.g. 3 of 5 → 3/5) |
| **Right context plus noise** | Retrieved {1, 15, 27, 28, 29}. The generator gets 2 useful and 3 noisy chunks. | **Precision** = useful retrieved / retrieved (e.g. 2 of 5 → 2/5) |

- Ideal: **both close to 1**.
- **Tension / trade-off via k:** raising k (5 → 10) raises recall but lowers precision. As recall goes towards 1, precision tends towards 0.
- Both are **reference-based** evals: you need a **golden dataset** that says what "correct context" is.

## The naive method (golden chunk IDs) and why it fails here
- Golden dataset: *question → correct chunk IDs* (e.g. "What is regression testing?" → {72, 89, 100}).
  - Per question: recall = found/correct (e.g. 3/3 = 1, or 1/2 = 0.5). Precision = useful/k (e.g. 3/5, 1/5). Average across questions.
- **Problems:**
  1. **Brutal labelling.** For each of ~50 questions, someone must read ~800 chunks.
  2. **It breaks whenever the chunking changes.** Tuning chunk size or overlap (e.g. 750/100 → 1000/150) produces **new chunks and new IDs**, so the golden set is **void** and must be rebuilt every time.
- It works only when documents are cleanly separated and chunking parameters **never change**. Here, information spans sessions (taught in session 1 *and* 5), so we must tune chunking.

## The right method: question + ideal answer, with LLM-as-a-judge
**Golden dataset:** *question → **ideal answer***, where the ideal answer is built **from the course transcripts** (what was actually taught, not Google).
- It **survives re-chunking**. The ideal answer doesn't change when chunks move.

### Contextual recall (DeepEval)
1. Retrieve the top-k chunks for the question.
2. A **judge LLM** splits the **ideal answer into atomic claims**. E.g. regression testing: (a) checks the new version vs the old, (b) runs the eval suite, (c) usable in CI.
3. The judge checks which claims are **supported by any retrieved chunk**.
4. Recall = supported claims / total claims (e.g. 3/3 = 1; RAG triad 1/2 = 0.5). Average over questions.
- Design choices that make it work:
  - Write ideal answers as **atomic claims**.
  - Use a **strong judge** with a well-written system prompt.
- (This differs from **Recall@k**, the ID-based version.)

### Contextual precision (DeepEval), rank-aware
- For **each retrieved chunk**, the judge gets: *question + ideal answer + this chunk*. "Is this chunk relevant? Does it contain information that helps produce the expected answer? Answer yes/no with a reason."
- Plain precision = relevant / k. But **rank matters**: two retrievals with the same 2/5 relevant chunks aren't equally good if one puts them at the top.
- **Rank-aware calculation** (as explained in the lecture): compute precision at each position and average.
  - **Case A** (✓ ✓ ✗ ✗ ✗): 1/1, 2/2, 2/3, 2/4, 2/5 → high average
  - **Case B** (✗ ✗ ✗ ✓ ✓): 0, 0, 0, 1/4, 2/5 → low average
  - So relevant chunks ranked higher score higher. *(Caveat added in translation: DeepEval's exact formula averages only at the positions of relevant chunks. The intuition, that higher-ranked relevant chunks score better, is the same.)*

Both metrics now use an **LLM judge**, so this is no longer a programmatic eval.

## Building the golden dataset: 4 methods

| Method | How | Pros / cons |
|---|---|---|
| **1. Hand-authored** | A domain expert (here, the teacher) writes the questions, finds the chunks and writes the ideal answers | **Best quality**, but not scalable (fatigue or cost) |
| **2. LLM-assisted drafting** ✅ *(used here)* | Give the transcripts to Claude with clear instructions and generate **one question at a time** (15 total). **A human reviews each one.** | Cheaper and faster. **Risk:** the LLM adds content that wasn't taught (e.g. internet facts), so review and remove it. |
| **3. DeepEval Synthesizer** | `goldens/generate_goldens.py`: random chunks into DeepEval's `Synthesizer` with formatting instructions, producing `retriever_dp_golden.json` | The instructor got **poor results**: unnatural questions ("Assess methodologies to validate LLMs' robustness…"), off-focus ones (UPSC example mechanics). Not used. |
| **4. Production logs** | Add positively rated interactions (thumbs up) after launch | Can't be the *first* method. You need entries before launch. |

- The final `goldens/retriever_goldens.json` has **15 questions in student-like language**: "What is an online eval and how is it different from offline?", "Faithfulness vs groundedness?", "How do I know if my eval is reference-based or reference-free?", "Why can't we test LLM apps like normal software?"

## DeepEval basics: the 3 building blocks
1. **`LLMTestCase`** = **one row** of the golden dataset. Fields: `input` (question), `actual_output`, `expected_output` (ideal answer), `retrieval_context`.
2. **Metric(s)**, e.g. `AnswerRelevancyMetric`, `ContextualRecallMetric`, `ContextualPrecisionMetric`. Params: `model` (judge LLM, e.g. GPT-4.1), `threshold` (pass/fail cut-off), `include_reason=True`.
3. **`evaluate(test_cases=[...], metrics=[...])`** runs the metrics over the test cases.

## The retriever eval (`evals/eval_retriever.py`)
- Load `retriever_goldens.json`. For each of the 15 rows: retrieve top-5 and build an `LLMTestCase(input=question, expected_output=ideal_answer, retrieval_context=[chunk texts], actual_output="Generator not evaluated in this run")`.
- Metrics: `ContextualRecallMetric` and `ContextualPrecisionMetric` (threshold 0.7, judge model set).
- **Log the config**: embedding model, chunk size and overlap, k, judge, golden file.
- Run: `python -m evals.eval_retriever`. Add `__init__.py` to `src/` and `evals/` to fix the `ModuleNotFoundError: src`.
- **Read the per-test-case reasons** to understand the failures.

## Iterating to improve the retriever

| Run | Change | Contextual recall | Contextual precision | Failing (of 15) |
|---|---|---|---|---|
| Baseline | chunk 750 / overlap 100, `text-embedding-3-small`, k = 5 | 0.80 | 0.80 | 5 |
| 2 | **chunk 1000 / overlap 150** (697 chunks; delete and rebuild Chroma) | **0.97** | 0.83 | 3 |
| 3 | + **reranker** (sentence-transformers model from Hugging Face) | 0.92 | **0.85** | 2 |
| 4 | + **`text-embedding-3-large`** (rebuild the DB) | **0.99** | 0.85 | 3 |
| 5 | k = 3 | ~ | 0.84 | — (no real gain) |

- A **reranker** moves meaningful chunks up and noisy ones down. Because contextual precision is rank-aware, it should raise precision. (A better-quality reranker would help more.)
- With only **15 rows**, there's natural **run-to-run variance**.
- Remaining ideas: a better reranker, more chunking experiments (e.g. 1500/200).
- **Outcome:** recall above 0.95 and precision around 0.85. You can move on to the generator with **measured confidence** in retrieval quality.

## Next
Component level, part 2: **build and evaluate the generator**.
