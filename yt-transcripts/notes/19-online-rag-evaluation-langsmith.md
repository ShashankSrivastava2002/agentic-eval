# 19 — Online RAG Evaluation: Monitoring in Production with LangSmith

> Source: [Online RAG Evaluation: Monitoring Production LLMs with LangSmith (Code Demo)](https://www.youtube.com/watch?v=wON2L2ZvKpE) (CampusX). Notes are based only on the video transcript.

## TL;DR
- After deployment, keep evaluating, but **only reference-free metrics can run online** (there's no answer key for new user questions).
- The online suite here has 6 metrics:
  - **Quality:** the RAG triad (contextual relevancy, faithfulness, answer relevancy)
  - **Safety:** toxicity
  - **Ops:** latency, cost
- **Ops** comes free with **LangSmith tracing**. Add `@traceable` where auto-tracing misses steps (e.g. the retriever).
- **Safety:** LangSmith's **built-in toxicity evaluator** on traces, with a **sampling rate**.
- **Quality:** run the **same DeepEval evaluators as offline** via a scheduled job that pulls recent traces with the LangSmith SDK and writes the scores back as feedback. Offline and online numbers must be **comparable**.
- Build a **custom dashboard** and **alerts**. Feed bad traces back into **versioned datasets**, which closes the offline ↔ online loop.

---

## Which offline metrics can run online?

| Level | Metric | Needs reference? | Online? |
|---|---|---|---|
| Retriever | Contextual recall | ✅ | ❌ |
| Retriever | Contextual precision | ✅ | ❌ |
| Generator / pipeline | **Faithfulness** | ❌ | ✅ |
| Generator / pipeline | **Answer relevancy** | ❌ | ✅ |
| Pipeline | **Contextual relevancy** | ❌ | ✅ |
| Application | Correctness | ✅ | ❌ |
| Application | Completeness | ✅ | ❌ |
| Application | Style | ❌ | ✅ (skipped: style rarely drifts, e.g. it won't drop from 80 to 30) |
| Safety | **Scope, leakage, toxicity** | ❌ (mostly) | ✅ (only **toxicity** demoed) |
| Ops | **Latency, cost**, reliability | ❌ (logged, not judged) | ✅ (reliability needs Grafana/Prometheus, out of scope) |

**Online suite = 6 metrics:** contextual relevancy, faithfulness, answer relevancy, toxicity, latency, cost.

---

## Step 1: connect the app to LangSmith (ops metrics)
1. At **smith.langchain.com**, go to Tracing, create a new application/project (**"CX Doubt Solver"**) and generate an **API key**.
2. Add these to `.env`:
   ```
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=...
   LANGSMITH_API_KEY=...
   LANGSMITH_PROJECT=CX Doubt Solver
   ```
   (`uv add langsmith`)
3. Run `python -m src.rag_pipeline` ("What is GSM8K?"). The trace appears with question, context, answer, **latency (4.14 s)** and **cost ($0.0004)**, with no extra code. (Tracing is **asynchronous**, so it doesn't add latency.)

### Fix: the retriever wasn't traced
- The default trace showed only `ChatPromptTemplate → ChatOpenAI → StrOutputParser`, with **no retrieval or reranking**, so latency was understated.
- Add **`@traceable`** decorators:
  - On `RAGPipeline.invoke`, named `"rag_pipeline"`
  - On the **reranker's** `invoke`, named `"retriever"` (retrieval and reranking happen there)
- Now the trace shows `rag_pipeline → retriever → prompt → LLM → parser`, and latency rises to **4.79 s** (it now includes retrieval).
- **Rule:** if something isn't traced implicitly, decorate it explicitly. Nested traces form a **hierarchy** with **no duplication**.
- Run ~8 different questions to **simulate traffic** (MMLU, why evals, LLM evals, model vs application evals, benchmarks, …).

## Step 2: dashboard and alerts
- **Monitoring → Custom → new dashboard** ("CX Doubt Solver Dashboard"). Ignore the prebuilt one.
- **Charts** (with a selectable time window: last 1 h / 3 h / 6 h / 30 days):
  - **Latency P95:** metric latency, Percentile = 95
  - **Average cost:** metric cost (total, or input and output separately), aggregation = **Average** (per answer, not the sum)
- **Alerts:**
  - E.g. latency > 7–8 s in the last 60 minutes, then a **Slack** notification.
  - LangSmith's latency alert supports only **average** latency, not **P95**. Possibly because P95 reflects outliers ("sad users") while alerts target population-wide degradation.
  - Cost example: total LLM cost > $5 in the last 60 minutes.
- **Q&A, how sensitive should alert thresholds be?** They come from the **SLO**, a **business decision** (e.g. a research assistant may legitimately take a minute).

## Step 3: online safety eval (toxicity) with LangSmith's built-in evaluator
- **Two options:** reuse the offline DeepEval eval, or use LangSmith's **online evaluators** (built-ins include PII leakage, prompt injection, toxicity, bias/fairness, all reference-free).
- Here, **LangSmith's toxicity evaluator** is used, to demonstrate it and because the goal is simply *detecting* toxicity (a big vendor's evaluator may be good).
- **Config:**
  - Name and app (auto-filled)
  - **Judge model** (default GPT-5.x)
  - **System prompt** (editable; kept as-is)
  - Run on **Tracing** (online), **not Datasets** (offline)
  - **Sampling rate**: 100% evaluates every trace (e.g. 50,000 traces a day means 50,000 judge calls, which is expensive). In production, sample (e.g. **30%**) to **estimate the population**, sized to your budget.
  - Provide your OpenAI API key (you pay).
- Result: "What are LLM leaderboards?" gets **toxicity 0**, with the reason "explanatory and professional; no personal attacks". Feedback appears after **~2–3 minutes**. Scores are 0–100 with an interpretable reason.
- Add a dashboard chart: Feedback → toxicity (average). New feedback keys can take time to show up.
- **Q&A:** it evaluates the **system's output**, not the user's input ("you can't stop users typing anything").

## Step 4: online quality evals, the same evaluators as offline
> ⚠️ **Use the same evaluators online and offline for quality metrics.** Different tools (DeepEval vs LangSmith) use different prompts and calculations. Offline contextual relevancy **45** (DeepEval) vs online **55** (LangSmith) aren't comparable. Same tool and setup: 45 offline → 38 online genuinely means **worse in production**. (This is likely interview material. Ideally apply it to toxicity too.)

### Architecture
- Deployed app (e.g. on AWS) plus a **background job / cron job every 5 minutes** that triggers **`evals/eval_online.py`**:
  1. Use the **LangSmith SDK** to fetch traces from the last N minutes (subject to the sample rate).
  2. Run the **DeepEval** metrics: faithfulness, answer relevancy, contextual relevancy.
  3. **Write the scores back** to LangSmith as feedback on each trace.
- The offline eval files can't be reused as-is, because they read the golden dataset. Online must read **traces**.

### Demo (`evals/eval_online.py`)
- Project CX Doubt Solver. Judge **GPT-4o mini**. **Same thresholds as offline** (0.7). Sample rate 1.0. **Polling interval 60 s**.
- `while True: score_recent_traces(); sleep(60)`. A stand-in for a cron job; it stops when the terminal closes.
- Questions such as "What are golden datasets?" and "Why do we need golden datasets?" show per-trace feedback (it lags): e.g. **answer relevancy 0.92, contextual relevancy 0.23, faithfulness 0.75**, or AR 1, F 1, CR 0.29. Toxicity 0.
- Add dashboard charts for answer relevancy, faithfulness and contextual relevancy (average, min or percentile), each with **alerts**.

## Step 5: close the loop with versioned datasets
- For a trace with poor scores, click **"Add to Dataset"** (create one from scratch, define its schema). Have an **expert write a reference answer** so it can serve offline **reference-based** metrics (correctness, completeness).
- **Better practice: keep all golden datasets in LangSmith from day one.**
  - A **single source** for offline and online
  - One-click trace-to-dataset additions
  - **Versioning and rollback** ("show me the golden set from 6 months ago")
  - Load them in offline evals via the **SDK**

  This is how production teams connect offline and online.

## Wrap-up
- The concepts transfer to any tool (LangSmith, Langfuse, …).
- **The RAG evals part is complete** (~8 sessions): build → component, pipeline and application evals (quality, safety, ops) → regression testing → online evals. The instructor's claim is that this is enough to handle any RAG-eval interview question.
- **Next:** **agent evals**, which should go faster now the fundamentals are in place.
