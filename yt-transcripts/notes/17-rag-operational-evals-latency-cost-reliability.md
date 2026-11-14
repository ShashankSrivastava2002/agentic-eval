# 17 — RAG Operational Evals: Latency, Cost & Reliability

> Source: [RAG Operational Evals: Building Faster & Cheaper RAG Systems](https://www.youtube.com/watch?v=kuTgQM9zhq0) (CampusX). Notes are based only on the video transcript.

## TL;DR
- **Ops evals** answer a different question: *"Even if the answers are good, can the system run **reliably, quickly and economically** in production?"*
- They are **software- and telemetry-driven**: **no golden dataset, no LLM judge**, so they're free to run apart from the app's own calls.
- Covered: **latency**, **cost**, **reliability**. **Throughput** needs load testing and is out of scope.
- Keep them in the **offline** suite too. The **absolute values** aren't dependable on a laptop, but the **differential** between versions is.
- Results:
  - **Latency:** E2E P95 5.3 s (SLO 3 s ❌), TTFT P95 2.08 s (SLO 1.2 s ❌)
  - **Cost:** ≈ ₹0.02/query ✅
  - **Reliability:** 100% success ✅

This completes the **RAG eval suite**. Next: regression testing, then online evals, then agent evals.

---

## Why ops evals belong offline as well
**Scenario.** A v2 adds a reranker, top-10 chunks and a bigger LLM.

| Metric | v1 | v2 |
|---|---|---|
| Correctness | 91% | **95%** |
| Faithfulness | 94% | **96%** |
| Answer relevance | 93% | **95%** |
| Avg latency | 2.3 s | **4.1 s** |
| P95 latency | 4.8 s | **6.2 s** |
| Avg cost/query | ₹0.72 | **₹1.08** |
| Timeout rate | 2% | 1% |
| Success rate | 99.8% | 99.9% |

Quality went up, but so did latency and cost. Without ops evals you'd only find out after users complained or the bill arrived.

> **"Do not wait until production to discover that your RAG pipeline is too slow or too expensive."**

- Laptop numbers ≠ production numbers, but the **direction of change is real**, as long as the experimental setup stays the same.
- Post-deployment, observability tools (LangSmith, Confident AI) log these metrics by default.

---

## 1. Latency
> The time a system takes to respond to a request: from the user pressing Enter to seeing the full answer.

The naive version is `start timer → rag_pipeline(q) → stop → end − start`. A good latency eval also follows these considerations:

1. **Prefer distributions over averages.** Report **P50 (median), P95, P99**, not only the mean. P95 = 95% of requests finish within this time. **Tail latencies** show how bad the worst user experiences are. (Dashboards show windows such as the last 1 h, 24 h or week, e.g. 2,000 latency values in an hour turned into a distribution.)
2. **Break end-to-end into components.** E.g. 4.5 s = retriever 1.5 s + generator 3 s. Break down further: embedding, retrieval, reranking, generation. This shows where to optimize.
3. **Measure TTFT (time to first token) separately.** Streaming improves UX: it's easier to read, and the user sees progress instead of a blank screen.
4. **Watch for cold starts.** The first requests are slow (model loading such as a Hugging Face reranker download, vector-DB connections, network handshakes, cache initialization, containers or serverless starting). **Discard warm-up runs.**
5. **Report output token count and context size**: latency scales with them.
6. **Distinguish latency from throughput.**
   - Latency is the time per request ("how long a diner waits for food").
   - Throughput is requests per unit time ("how many diners the kitchen serves per hour").
   - Exceeding throughput capacity (e.g. 20k users vs 10k capacity) creates **queues**, and latency rises. Always state the concurrency a latency number was measured at.
7. **Repeat runs**, because external APIs are noisy. E.g. send each question 5 times and average.
8. **Track failures separately.** Run B (P95 2 s, **8% timeouts**) isn't better than run A (P95 3 s, 2% timeouts). Lower latency can hide unanswered requests.
9. **Define latency budgets (SLOs)** at the **system** level (e.g. P95 ≤ 3 s) and the **component** level (e.g. retriever ≤ 1 s), based on the app, the users and industry norms.
10. **Use representative, segmented workloads**: a mix of simple, medium and complex questions.

### `evals/eval_latency.py` (generated with Claude, following these rules)
- 5 questions × 5 repeats = 25 calls, **2 warm-up runs discarded** (overall, not per question).
- SLOs: **E2E P95 ≤ 3,000 ms**, **TTFT P95 ≤ 1,200 ms**.
- The generator gained a **streaming** function to measure TTFT.
- Real evals use far more runs (500–1,000) for reliable numbers.

| Metric | Mean | P50 | P95 | P99 | Min | Max |
|---|---|---|---|---|---|---|
| **End-to-end** | 3.6 s | 3.8 s | **5.3 s** | 5.3 s | 1.3 s | 5.3 s |
| Retrieval | ~0.76 s | ~0.76 s | 0.98 s | ~1.0 s | | |
| Generation | ~2.9 s | | | | | |
| **TTFT** | 1.6 s | ~1.6 s | **2.08 s** | 2.1 s | 1.3 s | |

- Average answer length is **~1,158 chars**.
- **Generation ≈ 4× retrieval** (an LLM API call vs local retrieval).
- **Both SLOs fail**, so the pipeline needs optimizing.

### Levers to reduce latency
- **Generator:**
  - A faster model (e.g. a **Flash** variant), at some quality cost.
  - A **model router**: simple questions go to a small model, complex ones to a big model.
  - Prompt for **concise answers** or a hard length cap ("don't exceed 500 words").
- **Smaller context:** lower k (10 → 5), or **contextual compression** (compression itself costs time, so it's a trade-off).
- **Profile the retriever:** query embedding vs vector search vs reranking (e.g. 700 ms → 500 ms).
- **Caching:**
  - **Embeddings** for repeated questions
  - **Retrieval results**
  - **Reranking results**
  - **Prompt caching** for the large static system prompt
- **Infrastructure locality:** co-locate the vector DB, reranker API (e.g. Cohere) and LLM API in the region you serve (not Mumbai + US + Europe).

---

## 2. Cost
> The monetary expense to process one query, **driven primarily by the LLM tokens consumed**.

- **Where money goes:**
  - **LLM API** (dominant)
  - A paid vector DB (e.g. Pinecone)
  - A paid reranker (e.g. Cohere)
  - The embedding model (small)
  - Hosting infrastructure

  This eval assumes the other costs are 0 and measures LLM cost only.
- Formula: **input tokens × input rate + output tokens × output rate**. Rates are per 1M tokens (e.g. on OpenRouter). Output is typically ~4× input.

### Considerations
1. **Cost per query** is the key number.
2. **Split input vs output cost** to see where to optimize.
3. **Measure it as a distribution** (P95 cost). Find the tail queries that cost ₹1.5–₹3 vs the typical 2 paise.
4. **Segment by query type** (simple, medium, complex).
5. **Set a cost budget**: translate the monthly business budget into a per-query cap (e.g. ≤ ₹0.50 for complex queries).

### `evals/eval_cost.py`
- 4 questions × 3 repeats = 12 samples. Model **GPT-4o mini** ($0.15 input / $0.60 output per 1M). USD→INR fixed to ~95 (the script had 88).

| Metric | Value |
|---|---|
| Avg input tokens | ~1,753 (**1,109 auto-cached** by OpenAI) |
| Avg output tokens | ~209 |
| **Avg cost/query** | **≈ ₹0.02 (2 paise)**, very **tight min–max** range, so cost is stable |
| Input vs output spend | **More on input** (long prompt + context). Coding agents are typically the reverse. |
| Projection @ 2,000 queries/day | **≈ ₹57/day, ≈ ₹1,700/month** |
| Budget SLO | ✅ Pass |

- Cost is **stable offline** (fixed rates), unlike latency, so it's a more reliable offline metric.
- **Caching note:** the same question sent repeatedly makes provider caching **more aggressive** than in production, so real cached shares will be lower. This is **automatic provider-side caching**; no code was written for it.

### Levers to reduce cost
- **Smaller context:** smaller chunks, contextual compression
- **A leaner system prompt** (e.g. 1,000 → 800 tokens without losing its essence)
- **Concise answers / word limits**
- **Prompt caching**
- **The biggest lever is a cheaper model.** At scale, consider self-hosting open-source models. Everything else gives roughly ±5%.

---

## 3. Reliability
> The ability of a RAG system to **serve requests successfully** without errors, timeouts, crashes or broken pipeline stages. (E.g. 8 of 10 users get answers and 2 see "try again later", so 80% reliable.)

### Metrics
- **Success rate** = 1 − **error rate**
- **Timeout rate**: % of requests exceeding the allowed time (different from an error)
- **Retry rate**: % of requests needing at least one retry

### Considerations
1. Measure the overall success and failure rates.
2. **Categorize failures** instead of one generic error rate:
   - LLM API failure
   - Retriever or reranker failure
   - Timeout
   - **Rate limit**
   - Parser/formatting error
   - Internal exception

   Implement with `try/except` around each stage.
3. **Measure under load separately.** Single-user laptop tests look perfect; concurrency raises failures.
4. **Use enough samples.** 25–50 may show 100%; 1,000 may reveal failures.
5. **Representative requests**: simple, long-context, complex, long-answer and edge cases.

### `evals/eval_reliability.py`
- 4 questions × 5 = 20 calls, `max_retries = 2`.
- Result: **success 100%, error 0%, retries 0%**. That's expected for a single laptop on a reliable API. It becomes meaningful post-deployment (thousands of users, less reliable APIs, e.g. Ollama cloud models).
- **Q&A:** DeepEval runs with many metrics × many goldens, or expensive models, can hit **rate-limit errors** too.
- **Q&A, separate dev/prod budgets?** Not for **cost** (the rates are the same). **Latency** budgets may differ because production adds network distance.

---

## Throughput (not covered)
Requests served per unit time. Needs **load and stress testing** with dedicated tools that emulate many concurrent users. Standard in company production setups.

## Milestone
**The RAG eval suite is complete** (component, pipeline, application: quality, safety, ops).

Remaining:
1. **Regression testing** (run the whole suite on each change and decide whether to deploy)
2. **Online evals**
3. Then **agent evals** (faster, now that the fundamentals are in place)
