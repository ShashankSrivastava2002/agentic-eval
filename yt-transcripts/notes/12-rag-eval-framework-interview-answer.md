# 12 — "How Do You Evaluate Your RAG App?": The RAG Eval Framework

> Source: [How to Answer "How Do You Evaluate Your RAG App?" in GenAI Interviews](https://www.youtube.com/watch?v=4zn-gSckVTQ) (CampusX). Notes are based only on the video transcript.

## TL;DR
Don't answer with a list of metrics. Answer with a **framework**:
1. Build an **eval suite** at **3 levels**: **component** (retriever, generator), **pipeline** (RAG triad), **application** (quality, safety, ops).
2. Use it for **regression testing**, at 3 maturity levels: manual, experiment tracking, CI gating.
3. **Deploy**, then run **online evals** (capture, compute, drift, alerts) with a **self-improving loop** back into offline datasets.
4. Tooling: **DeepEval** (pytest-style).

---

## Where we are in the course
- **Done:** fundamentals (why/what, reference-based vs reference-free, offline vs online, model vs application evals), then **model evals** (benchmarks plus custom evals).
- **Now:** **application evals**.
  - LLM app types: simple chatbots, **RAG chatbots**, **agents**, multimodal apps (e.g. image generators), fixed-schema output (e.g. the Zomato email classifier).
  - The course covers **RAG** and **agents**: they're the most common production patterns, and the easier types follow from them.
- "How do you evaluate your RAG chatbot?" comes up in roughly **8 of 10 GenAI interviews**, and most candidates can't answer in a structured way.

## The case study: CampusX Doubt Solver
- A simple **RAG chatbot** over the **transcripts of every lecture** in this LLM evals course. Students ask doubts about the playlist.
- It's deliberately simple, to focus on **how to evaluate**, not on fancy RAG.
- RAG recap: query, **retriever** (embedding model + vector DB, top-k docs), then question + context go to the **generator** (LLM), which produces the answer.
- **Build and evaluate together**, like software testing at the function and feature level.

## The eval suite: 3 levels, 9 steps

### Level 1: component level

| Step | Build / evaluate | Metrics |
|---|---|---|
| 1 | **Build the retriever**: load docs, chunk, embed, store, retrieve | |
| 2 | **Evaluate the retriever in isolation** | **Recall** (how many of the correct docs were fetched), **precision** (how many fetched docs were useful) |
| 3 | **Build the generator** (LLM: question + context → answer) | |
| 4 | **Evaluate the generator in isolation**: feed it **manually provided** questions and context (golden-style), *not* the retriever's output | **Faithfulness** (only from the context, no hallucination), **answer relevance**, **citation accuracy** (e.g. cite which session and transcript link it came from) |

### Level 2: pipeline level

| Step | What | Metrics |
|---|---|---|
| 5 | **Build the RAG pipeline**: connect retriever and generator | |
| 6 | **Evaluate the pipeline** with the **RAG triad** | See below |

**The RAG triad**: three entities (**question**, **context**, **answer**) give three pairwise metrics:

| Pair | Metric | Checks |
|---|---|---|
| Question ↔ context | **Context relevance** | Is the retrieved context relevant to the question? |
| Answer ↔ context | **Faithfulness** | Is the answer grounded in the context? |
| Answer ↔ question | **Answer relevance** | Does the answer address the question? |

### Level 3: application level

| Step | Category | Metrics |
|---|---|---|
| 7 | **Quality** | **Correctness**. **Completeness** (all parts of a multi-part question answered). **Style** (matches the CampusX teachers' explanation style). |
| 8 | **Safety** | **Toxicity**, **PII leakage**, **jailbreak** resistance |
| 9 | **Operations** | **Latency**, **cost per query**, **tokens** |

> All of the above together = the **eval suite**. Some evals need **golden datasets**; some don't.

## Tooling: DeepEval
- Instead of hand-writing all the eval code (as in the custom model eval session), use **DeepEval**.
  - RAG metrics are built in: answer relevancy, faithfulness, contextual precision, contextual recall, contextual relevancy.
  - Safety metrics are built in: toxicity, PII leakage.
- **pytest-based syntax**, familiar to anyone who has done software testing.
- Why DeepEval over RAGAS (both work):
  1. RAGAS was already covered in the Advanced RAG course.
  2. DeepEval is **broader**: agents, multi-turn chatbots, non-LLM and image apps. It has higher adoption and may become the standard.

## Regression testing
> **Regression testing** = running your **whole eval suite** on a new version to check it's **not objectively worse** than the previous one. It produces a report of which metrics went up or down, which drives the deploy decision.

### Project layout
```
project/
├── src/          # retriever.py, generator.py, rag_pipeline.py, (FastAPI API, Streamlit UI)
├── evals/        # eval_retriever.py, eval_generator.py, eval_pipeline.py,
│                 # eval_application.py, eval_safety.py, eval_ops.py   ← the eval suite
└── run_evals.py  # runs every eval and generates a comparison report
```

### Three maturity levels

| Level | How | Tools |
|---|---|---|
| **1. Basic** | Run `run_evals.py`, get **baseline** numbers, re-run after changes, compare manually | — |
| **2. Experiment tracking + dashboards** | Log **config** (chunk size, overlap, temperature, embedding settings) and **metrics** per run (e.g. recall 0.82, precision 0.68), then compare runs on a dashboard | **MLflow**, Confident AI (from the makers of DeepEval), Weights & Biases |
| **3. CI gating** | On every `git push` (e.g. a chunk-size change), **CI** (GitHub Actions) re-runs the suite and compares with the **baseline** against a threshold (e.g. not more than 3 points lower). Worse means **block the deployment**. Better means **deploy and update the baseline**. | GitHub Actions (CI/CD is covered in the LLMOps course) |

> No standard LLM experiment-tracking tool exists yet (unlike MLflow for ML). **Focus on concepts, not tools.**

## After deployment: online evals
- **Capture** (via tracing/observability): latency, cost, tokens, thumbs up/down. Tools: **LangSmith**, **Langfuse**, Confident AI.
- **Compute** online: faithfulness, answer relevance, correctness (the same metrics as offline).
- **Drift detection**: e.g. faithfulness trending down over the last 8 hours triggers an **alert**, then a fix.
- **Self-improving loop**: misbehaving chats go into the **offline golden datasets**, which get richer over time.

## The interview answer (template)
> "I'd build an **eval suite** and test at **three levels**:
> **Component**: retriever (recall, precision) and generator in isolation (faithfulness, answer relevance, citation accuracy).
> **Pipeline**: the **RAG triad** (context relevance, faithfulness, answer relevance).
> **Application**: quality (correctness, completeness, style), **safety** (toxicity, PII, jailbreak) and **ops** (latency, cost, tokens).
> I'd use the suite for **regression testing** (basic, then experiment tracking, then CI/CD gating against a baseline), **deploy**, then run **online evals** (captured and computed signals, drift detection, alerts), and feed production failures back into my offline golden datasets."

Listing just 3–4 metrics (recall, precision, answer relevance) is the common weak answer. A **framework** answer shows depth.

## Roadmap for the next sessions
1. Component level: build and evaluate the retriever and generator (first use of DeepEval)
2. Pipeline level: the RAG triad
3. Application level: quality, safety, ops
4. Regression testing and online evals
