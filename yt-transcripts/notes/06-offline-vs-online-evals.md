# 06 — Offline Evals vs Online Evals

> Source: [Offline Evals Vs Online Evals](https://www.youtube.com/watch?v=SahaDGzN-Bk) (CampusX). Notes are based only on the video transcript.

## TL;DR
- **Offline evals** run **before deployment** on a **golden dataset** with an answer key. They check whether the app **works correctly**.
- **Online evals** run **after deployment** on **live traffic** with **no answer key**. They check whether the app is **running normally** in production.
- They are **complementary, not rivals**. Production failures are fed back into the offline dataset, which forms a **self-improving loop**.
- Online pipeline: **log → (sample → evaluate) → dashboard → alert**.

---

## Course recap
1. Why we need evals
2. What evals are: model evals vs application evals
3. What an eval pipeline looks like
4. Why one app needs **multiple** eval pipelines: failure points (component, workflow, application) and risk categories (quality, safety, operations)
5. Eval methods: programmatic, human, LLM-as-a-judge

## Offline evals
> Any eval pipeline you run on an LLM application **before deploying it**.

Everything studied so far (the email router, the retriever's Recall@k, the UPSC grader) is offline evaluation.

### Three benefits
1. **Pre-release testing and release gating**
   - Automate it with **CI/CD**: push code to Git, **GitHub Actions** runs the eval script, and you get a score.
   - Score ≥ threshold (e.g. 95%): deploy automatically. Below the threshold: notify and/or roll back.
2. **Version comparison**
   - Same eval and same golden dataset give a level playing field.
   - Compare models (Claude vs OpenAI), prompts, rerankers, vector DBs or whole architectures.
3. **Regression testing**
   - **Regression** = improving one thing breaks something else.
   - Example: the CampusX chatbot was cold about refunds, so the prompt was changed to "be very kind and polite". Now it softens facts and says the Insider plan is "around ₹19,000" instead of ₹19,500.
   - Fix: the golden dataset covers **all question types** (refunds, pricing, curriculum, …). Track scores **per category**. If refund accuracy was 90% it should stay ~90%; a drop to 80% means regression, so don't ship the change.

## Why offline isn't enough: three production risks
1. **Unanticipated inputs.** The golden set has 200–500 anticipated questions, but the real world sends Hindi–English mix, ambiguous half-questions, angry rants, adversarial **prompt injections** and edge cases.
2. **Emergent or systematic failures that only appear at scale**
   - Latency spikes with thousands of concurrent users (e.g. after a course launch). This can't be tested offline.
   - **Subtle bias** that is only visible across thousands of conversations (e.g. worse treatment of non-technical users).
3. **Drift.** The business changes (prices, curricula, policies), so the documents change and the data distribution shifts. The golden dataset, built for "today", becomes **obsolete**. Offline scores stay good while users give negative feedback.

> Offline evals need a golden dataset with correct answers. In production there is no golden dataset and no answer key, so offline evals can't cover these risks.

## Online evals
> "Online eval is evaluating your system on **live production traffic after deployment**, as real users interact with it."

The key property is that **it works without an answer key or golden dataset**.

### Offline vs online

| | Offline | Online |
|---|---|---|
| When | Before deployment | After deployment, continuously |
| Data | Fixed **golden dataset** | **Live production traffic** |
| Answer key | Usually yes | **No**. Quality must be estimated on the go. |
| Inputs | Only what you **anticipated** | **Anything** |
| Catches | **Regressions** | **Drift**, surprises, emergent bugs |
| Best for | **Gating**, version comparison, CI | **Drift detection**, real-world performance |
| Cost/speed | Fast, cheap, repeatable (small dataset) | Can be costly at scale, so use **sampling** (e.g. ~1,000 of 50,000 daily conversations) |

> **Offline evals tell you whether your app works *correctly*. Online evals tell you whether it's running *normally* in production.**

### Correctness vs normality (UPSC grader example)
- **Offline**, correctness = how close the grader's marks are to the **human's** marks (the human marks are in the golden set).
- **Online**, no human ever graded the new answer, so **correctness can't be measured**.
- What you *can* measure is **normality**: plot the **weekly distribution of scores** and use past weeks as the **baseline**. If one week suddenly shifts (most scores now ~800 instead of ~500), that **triggers an investigation**.
- It could be a real trend (e.g. stronger students that week), but you are alerted to look.

### How to estimate quality without an answer key
- **Metrics that don't need a correct answer**, e.g. **faithfulness**: give an LLM the retrieved context and the generated answer and ask whether the answer came from the context.
- **Workarounds / proxies** when correctness needs an answer key:
  - Baseline **distribution comparison** (UPSC)
  - **User feedback** (thumbs up/down) as a proxy for correctness. A surge of thumbs-down in the last hour means something is wrong.

---

## The online eval pipeline

### Step 1: logging
> "Capture a structured, replayable record of every conversation turn."

What to log per conversation and turn:
- **IDs:** conversation ID, turn ID, user ID, session ID, timestamp
- **Content:** user question, **retrieved context** (RAG), model output
- **Operational:** latency (ms), prompt tokens, completion tokens, total cost, errors and status codes
- **Behavioural signals:** thumbs up/down, escalations ("connect me to a human", emailing support), repeated or rephrased questions

Tool: **LangSmith** (projects contain traces with inputs, outputs and metadata).

Engineering properties of good logging:
1. **Non-blocking.** Logging must not add latency to the conversation.
2. **Durable and queryable.** Structured storage in a data warehouse or observability tool, fetchable later.
3. **Late-signal attachment.** Signals that arrive later (e.g. a support email the next day) are linked back via the **conversation ID**.
4. **PII handling.** **Mask** personal data (phone, card number, address, date of birth, Aadhaar) before storing. **PII = Personally Identifiable Information.**

### Step 2: know your signals

| Type | Meaning | Examples |
|---|---|---|
| **Captured** | Already available. Just store it. | Thumbs up/down, latency, cost per conversation, token usage |
| **Computed** | Must be calculated by an **online evaluator** | Faithfulness, answer relevance, correctness, hallucination, toxicity, bias/fairness |

### Pipeline for captured signals
**Log → dashboard → alert**
- **Dashboard:** view **aggregated** values over time windows (last 1 h, 24 h, week, 6 months). A single conversation's value doesn't matter; the trend does.
  - Example: a course launch brings 500 users at once, latency climbs, so add capacity (more EC2 instances, load balancers on AWS).
- **Alerting:** nobody watches graphs 24/7. Alert when a metric crosses a threshold (e.g. latency > 4 s) via Slack, email, PagerDuty, Dynatrace or a custom API.
- LangSmith has **Monitoring** (trace latency, error rate, LLM call count, LLM latency, cost) and **Alerts** (metric + threshold + window, e.g. last 5 minutes).

### Pipeline for computed signals
**Log → sample → evaluate → dashboard → alert**

Example: detecting **hallucination** in real time.
1. **Log** all conversations (e.g. 50,000 a day).
2. **Sample.** Running an LLM judge on everything would more than double cost.
   - Random sampling (e.g. 1,000 of 50,000) works, but **stratified sampling** is better: divide conversations into categories and **oversample risky ones**, such as thumbs-down, abrupt endings, escalations, repeated or rephrased questions, and money topics (refunds, admissions, fees). Thumbs-up conversations are low value.
   - Categorising may itself need a small model (clustering).
3. **Evaluate** with a **reference-free LLM-as-a-judge**: a stronger LLM gets the context, question, output and a detailed rubric, and decides whether the answer is a hallucination.
4. Aggregate the metric (e.g. **hallucination rate**), then **dashboard**, then **alert**.
- Run **multiple such evaluators** in parallel.

### LangSmith evaluators (templates seen in the demo)
- **Security:** PII leakage, prompt injection, code injection
- **Safety:** toxicity, bias/fairness
- **Quality:** hallucination, correctness, assertions, conciseness, code checker
- **Trajectory** (for agents), plus image- and voice-based variants
- Most are **LLM-as-a-judge**. Configure the name, application, judge model (OpenAI/Claude/…), API key, temperature, the **prompt/rubric** and the output format.
- **Run on tracing → online evaluator. Run on a dataset → offline evaluator.** LangSmith supports both, plus Datasets & Experiments for offline runs.

## Closing the loop: the self-improving cycle
- In LangSmith, a bad production trace can go **"Add to dataset"** into the offline golden set, or into an **annotation queue** to mark what went right or wrong.
- Cycle: offline eval → deploy → production failures → add to offline dataset → re-run offline evals → redeploy → …

## Q&A
- **"Dashboard shows faithfulness 0.87, latency 3 s: is the bot good?"** Compare against a **baseline**, usually from offline evaluation. A baseline of 0.85 makes 0.87 fine. A drop to 0.75 in the last 24 h is concerning, so alert and improve.
- **"Offline score went from 92 to 99: good for production?"** It depends which metric, and whether others **regressed**. Improving one metric must not lower the others.

## Coming next
Benchmarks (model-level evals) for one or two sessions, then application evals in depth: building golden datasets and running offline and online evals using **LangSmith**, **DeepEval** and **RAGAS**.
