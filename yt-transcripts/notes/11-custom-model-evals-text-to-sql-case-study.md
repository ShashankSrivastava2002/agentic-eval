# 11 — Selecting the Right LLM: Running Custom Model Evals (Text-to-SQL Case Study)

> Source: [Selecting the Right LLM for Your AI App: Running Custom Model Evals](https://www.youtube.com/watch?v=RG5A-W3eMHI) (CampusX). Notes are based only on the video transcript.

## TL;DR
A 3-stage, hands-on model-selection process for an **ESPNcricinfo-style "Ask Cricinfo" text-to-SQL feature**:
1. **Gather requirements**: task, cost ceiling, latency, context, deployment, correctness.
2. **Shortlist 5–10 candidates from a leaderboard**: filter by cost, then rank by a weighted score.
3. **Run a custom eval** on a golden dataset using **execution-based result-set matching**.

Result on 20 hard questions: **Grok 4.5 = 90%**, **Claude Sonnet 5 = 85%**, GPT-5.6 Terra = 80%, MiniMax M3 = 65%, Kimi K3 = 55%. The two finalists are Grok and Sonnet. The instructor leans towards **Sonnet** for API reliability and observed speed.

---

## The case study
- During live matches Cricinfo gets huge volumes of fan questions (e.g. ~500 in 5 minutes during India vs Pakistan), such as "Kohli's batting average vs Pakistan?" Analysts used to write SQL by hand. That doesn't scale.
- Feature: a user asks in English, an **LLM converts it to SQL** (it knows the schema), the SQL runs on the DB, and the result is shown to the user.
- This is **not RAG**. There are no external documents, just the fixed **schema** in the prompt.
- Goal of the session: **select the best model** to be the system's "brain". (You can't just say "use Fable, it's the top model". You need justified reasoning.)

## Stage 1: gather requirements

| Requirement | Decision | Reasoning |
|---|---|---|
| **Task** | Text-to-SQL (SQLite in the demo) | |
| **Cost ceiling** | **₹3 lakh/month** (the pre-class run used ₹5 lakh) | The feature is a **retention play**: more time on site means more ad revenue |
| **Latency** | **≤ 2–3 s** | Live-match curiosity. Avoid slow reasoning models. |
| **Context** | **Doesn't matter** | Single, independent questions. No multi-turn session. |
| **Deployment** | **Public APIs OK** (preferred) | No sensitive data. Better reliability than self-hosting. |
| **Correctness** | **Critical** | Cricket fans are finicky about records. A wrong answer becomes a viral screenshot. |

### Cost estimation (the worked example)
- **Prompt** = system prompt ("You are a text-to-SQL generator… return a single SQL query… SQLite syntax… return only the SQL") + **schema** (tables `matches` and `deliveries` for the IPL, ball-by-ball) + the user question.
  - Example question: *"Which bowler has the best economy rate among bowlers who have bowled at least 500 legal balls?"*
- Tokens: input ≈ **400** (measured 352), output ≈ **100**.
- Volume: ≈ **50,000 questions/day** (a spiky gut-feel estimate; spikes on big matches).
- **Claude Fable 5** pricing: $10 / 1M input, $50 / 1M output.
  - Per query: 400 × 10/1M + 100 × 50/1M = **$0.009**
  - Per day: × 50,000 = **$450**. Per month: × 30 = **$13,500**. × ₹95/$ ≈ **₹12.82 lakh/month**.
  - That is **~4× over budget**, so go cheaper (e.g. Claude Sonnet 5).

### Prompt caching (cost optimization)
- A large, **repeated** part of the prompt (system prompt + schema) is identical across all 50,000 queries, so cache it with the provider.
- Pricing pattern seen:
  - **Cache write** costs more than normal input ($12.50/1M for a 5-minute cache vs $10 normal).
  - **Cache hits** cost far less (~$1/1M).
- **5-minute cache** suits high traffic: at least one question every 5 minutes keeps it warm. **1-hour cache** (~$20 write) suits low traffic (e.g. ~1,000 questions/day).
- Fable's ~₹12 lakh could fall to ~₹6–7 lakh with caching.
- Less useful for **RAG**, where most of the prompt (the retrieved context) changes every query.
- Internally this relates to the **KV cache** (caching K/V vectors in attention).
- **Q&A:** domain-specific column names? Add **column descriptions** to the system prompt. It costs more tokens, which caching offsets.

## Stage 2: shortlist from a leaderboard
- Text-to-SQL leaderboards exist (**BIRD-SQL**, **Spider**, **LiveSQLBench**) but were rejected: **not updated**, and they included fine-tuned models or whole harnesses rather than base models.
- **Fallback:** use **coding capability as a proxy** for SQL generation, via **llm-stats.com** ("Best AI for coding"). It is up to date, has 146 models, and lists cost, speed and context.
- **Blended price:** a single price at a **4:1 input:output** ratio = (4 × input + 1 × output)/5. Fable: (40 + 50)/5 = **$18/1M**. Always check the ratio a leaderboard uses. Here it matches our own 400:100 = 4:1 exactly.
  - Monthly cost = 500 tokens × blended/1M × 50,000 × 30 × 95.

**Filtering strategy:**
1. Compute monthly cost for all 146 models and **drop any over budget**.
2. **Min–max normalize** the coding rating and throughput (chars/sec) to 0–1.
3. **Score = 0.9 × normalized coding + 0.1 × normalized speed**.
   - Speed gets little weight because the output is only a ~100-token SQL query, so even slow models finish quickly. (A long-essay app would weight speed more. Splits like 0.8/0.2 or 0.75/0.25 are also reasonable.)
4. Sort and take the **top 10**. Muse Spark 1.1 (Meta, US-only) is unusable.
   - Observation: cheap Chinese open models (MiniMax M3 ≈ 0.76) aren't far behind GPT-5.6 Terra (≈ 0.9) at a fraction of the cost.

**5 models tested (live-class limit):**
- **GPT-5.6 Terra**: top candidate (Luna skipped; Terra should beat it)
- **Kimi K3**: hyped (2.7T params, open weights, Moonshot AI)
- **Grok 4.5**
- **Claude Sonnet 5**: the only Anthropic model in the list
- **MiniMax M3**: representing the Chinese models GLM/Qwen/MiniMax; very cheap
- (Gemini 3.6 Flash was skipped.)

## Stage 3: run the custom eval

### Design
1. **Database:** the Kaggle IPL dataset (2008–2024), **trimmed to 2020–2024**, loaded into **SQLite**.
2. **Golden dataset:** questions plus **golden SQL** written and **validated by a data analyst**.
   - Size: 30–50 typical, 50–500 fine. Bigger means more labelling cost and more LLM calls (5 models × 50 = 250 calls; × 500 = 2,500).
   - Keep it **representative of the user distribution**: e.g. 10 easy / 20 medium / 20 hard, covering joins, subqueries and window functions.
   - Keep adding production failures after launch.
   - The demo used **20 "brutal" questions** (LLM-generated, validated by execution). That's deliberately hard; a real set should include easy questions.
3. **Scoring: execution-based result matching, not string matching.**
   - Many SQL queries give the same result, so exact text comparison is wrong.
   - Run **both** the golden SQL and the generated SQL on the DB and compare the **result tables**.
4. **Accuracy** = matched / total, per model.

### Evaluator logic (`evaluator.py`)
1. **Row count** must match. If not, fail.
2. **Normalize values** (e.g. `2.0` ≡ `2`; round floats like 2.999 / 2.99).
3. Convert rows to a list of tuples.
4. If **not order-sensitive**: sort both and compare.
5. If **order-sensitive** (the golden row has `ORDER BY`, flagged in the dataset): compare **without** sorting.
6. Plus a few more checks.

### Code pipeline (12 steps, summarized)

| File | Purpose |
|---|---|
| `data/deliveries.csv`, `data/matches.csv` | Raw Kaggle data |
| `db.py` | Load 2020–24 data into SQLite (tables `deliveries`, `matches`) |
| `schema_extractor.py` → `schema.sql` | Extract tables, columns and types for the system prompt |
| `golden_dataset_generator.py` | 20 Q/SQL dicts (with difficulty). Runs each query to check it's **well-formed** (20/20 passed; this is not a correctness check). |
| `make_golden_dataset.py` → `golden_dataset.csv` | CSV with question, golden SQL, **expected row count**, **order-sensitive flag** |
| `first_test.py` | Smoke test: one question via **OpenRouter** (`ChatOpenRouter` in LangChain) with GPT-4o to verify the flow |
| `model_openrouter_slug` | List of (model name, OpenRouter slug) for the candidates |
| `evaluator.py` | Result-set comparison logic |
| `main.py` | For each model and question: generate SQL, execute generated and golden SQL, evaluate, log |

- **OpenRouter** = one API for all providers (OpenAI, Anthropic, xAI, Chinese models), with LangChain integration and some free credits. The full run cost ~$5 (~₹500).

### Results (20 hard questions)

| Model | Accuracy | Notes |
|---|---|---|
| **Grok 4.5** | **90%** | Fast, solved Q2 that others failed. ~₹2.5 lakh/month. |
| **Claude Sonnet 5** | **85%** | **Fastest observed**, ~₹2.84 lakh/month |
| GPT-5.6 Terra | 80% | Most expensive |
| MiniMax M3 | 65% | Several **SQL syntax errors** |
| Kimi K3 | 55% | Very slow (likely reasoning) plus 6 SQL errors. The hype didn't transfer to this task. |

**Decision:** Grok and Sonnet are the finalists (similar cost and score). The instructor leans to **Sonnet**: Anthropic API reliability and faster observed latency, even though the leaderboard said Grok was faster. Teams may vote.

## Lessons
- **Leaderboard hype ≠ performance on your task** (Kimi K3).
- 20 questions is **small** (1 question = 5%). Use a bigger set and/or **multiple runs** for statistical confidence.
- You can also measure **latency** in the eval (not coded in this demo).
- The stakes decide the trade-off: a medical app pays for the top accuracy; a consumer app may accept slightly lower accuracy to save cost.
- Who does this? **AI engineers** (it's technical). They report to the PM, who makes the final call.
- **Q&A on DB design:** denormalized tables suit analytics (**OLAP**), normalized tables suit transactions (**OLTP**).

## Course status
The **model evals part is complete** (benchmarks plus custom evals). Next comes **application evals** (RAG and agents).
