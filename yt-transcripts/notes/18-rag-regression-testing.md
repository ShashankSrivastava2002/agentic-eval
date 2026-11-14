# 18 — RAG Regression Testing: Preventing Silent Failures

> Source: [RAG Regression Testing Explained: How to Prevent Silent AI Failures](https://www.youtube.com/watch?v=Aov5QczE3Vo) (CampusX). Notes are based only on the video transcript.

## TL;DR
- **Regression** = "returning to a previous, less advanced or worse state". Fixing one metric often quietly breaks others.
- **Regression testing** = on **every change**, rerun the **whole eval suite** (~14 metrics), compare with a **baseline**, and deploy only if nothing meaningfully regressed.
- The two complications are handled by a **metric registry**:
  1. **Direction**: is higher or lower better?
  2. **Noise**: LLM judges vary run to run, so set a per-metric **noise threshold = 2 × std dev** across repeated baseline runs.
- Demo: chunk 1500 → 500 to raise contextual relevancy. Instead **contextual relevancy fell (≈45 → 38)** and **PII leakage dropped ~20%**, so `promote.py` **blocks** the change.

---

## The concept
- Example: recall is low (85%), so you increase k and add a reranker. Recall rises to 90% and you ship. But **precision dropped**, **contextual relevancy fell** and **latency rose**, and nobody measured those.
- **Rule:** after *any* change (k, chunk size, model, system prompt, …) make sure the app performs **at least as well on every aspect**.
- It's an old **software engineering** concept (e.g. moving an API from Flask to FastAPI), applied to LLM apps.
- ⚠️ Disclaimer: this is a **conceptual, hand-coded** implementation. Companies use dedicated tools (e.g. MLflow, Confident AI). The concepts transfer; the execution differs.

## The process
1. **Build one script** (`run_suite.py`) that runs **all** evals in sequence: quality, safety, ops.
2. **First run, then save `baseline.json`** with all ~14 metric values.
3. **Make a change** (k, chunk size, model, system prompt, …).
4. **Re-run, then save `candidate.json`.**
5. **Compare** (`compare.py`): a per-metric **delta**. A negative delta in the bad direction means a regression.

```
run_suite.py ──(first run)──> baseline.json ──┐
             ──(after change)─> candidate.json ┼──> compare.py ──> per-metric delta ──> promote.py
metric_registry.py (direction + noise) ───────┘
```

## Two complications
1. **Direction differs by metric.**
   - Higher is better: faithfulness, recall, precision, …
   - Lower is better: **latency, cost, toxicity**
2. **Non-determinism.** Most quality and safety metrics use **LLM-as-a-judge**, so re-running the **same** setup changes the scores (precision 85.6 → 84.8 with no code change). A naive compare would report false regressions.
   - **Fix:** run the baseline **5–10 times** in the same setup, compute each metric's **standard deviation**, and set the **noise threshold = 2σ**.
   - Example: σ(recall) = 0.5, so threshold = 1. A recall of 90 → 89.5 is **noise**. 90 → 87.5 is a **regression**.
- Store both pieces of information per metric in **`metric_registry.py`** (direction = higher/lower, noise tolerance).
- *(In the demo the baseline was run only **2×** to save time and money. Use 5–10 in practice.)*
- ⚠️ **Tiny golden datasets (5–15 rows) cause large swings** (e.g. PII leakage 60% ↔ 80%). Bigger datasets mean more stable metrics.

## Code changes to the project
- **Consolidate:**
  - **Ops evals** (`eval_latency`, `eval_cost`, `eval_reliability`) merged into **`eval_ops.py`**
  - **Safety evals** (`eval_leakage`, `eval_toxicity`, `eval_scope`) merged into **`eval_safety.py`**
  - (The individual files are kept for readability. Delete them if you want a cleaner repo.)
- **Refactor the quality evals** (`eval_retriever`, `eval_generator`, `eval_rag_pipeline`, `eval_application`) to expose a **`run()` function** plus an `if __name__ == "__main__"` block, so they can be called from outside.
- **`harness.py`**: standardizes how the four quality evals receive inputs and **emit outputs in one format**.
- **`run_suite.py`**: runs all **6 eval groups** (retriever, generator, pipeline, application, safety, ops) and writes `baseline.json` on the first run and `candidate.json` afterwards. Accepts a label describing the change (e.g. "chunk 500 / overlap 100").
- **`metric_registry.py`**: direction and noise tolerance per metric.
- **`compare.py`**: reads the baseline, candidate and registry and labels each metric **improved / flat (within noise) / regressed**.
- **`promote.py`** (optional): a decision framework that sorts metrics into **tiers**:
  - Drops you **can't accept** (e.g. safety)
  - Drops that need **discussion**
  - Drops that **don't matter**

  Outputs **PROMOTE / REVIEW (human decision) / BLOCK**.

## The demo
- **Change:** `chunk_size` 1500 → **500**, `chunk_overlap` → **100** (goal: raise contextual relevancy, previously ~43–45%). Delete Chroma and re-embed.
- `run_suite.py` executes the 6 evals (retriever: recall 96 / precision 90, then generator, triad, application, safety, ops). It takes ~5+ minutes and **costs ~₹25–30 per run**, even with small datasets. That cost grows with dataset size.
- `compare.py all`:
  - **Most metrics flat** (within noise)
  - **~4–5 improved**
  - **2 regressed:** **contextual relevancy ≈ 45 → 38** (the metric the change was meant to improve) and **PII leakage dropped ~20%** (a big safety red flag)
- `promote.py` returns **BLOCK**, because a critical safety metric dropped. If only contextual relevancy had dropped, it would return **REVIEW** for human experts to weigh against the 5 improvements.

## Q&A highlights
- **Signed direction (−1/+1) × delta?** Yes, that's equivalent to what the registry does.
- **Retrieval or generation at fault?** Read the metrics together. Good recall, precision and contextual relevancy but a bad answer points to the **generator**. If a retriever metric moved, it's the **retriever**.
- **Runtime in CI?** Slowness is acceptable. Deployment can wait; only the best version should ship.
- **Is this local CI?** Yes. Move it into **GitHub Actions** and it becomes CI. In production, regression testing is part of CI.
- **One composite score?** Possible with domain-weighted formulas, but generally **not done**. The separate metrics describe different aspects, and collapsing them hides information.
- **Noise thresholds in real projects:** use 5–10+ baseline runs. Rigorous setups apply statistics such as **p-values, significance and hypothesis testing**. For something like ChatGPT, proving "no regression anywhere" is a big, expert-heavy field.

## Next
**Online evals**: running these evaluations in production after deployment. That completes the RAG story. (MLflow-based regression testing is covered in the LLMOps course.)
