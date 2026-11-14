# 10 — How to Use LLM Leaderboards

> Source: [How to Use LLM Leaderboards](https://www.youtube.com/watch?v=SoZPmKb5uGc) (CampusX). Notes are based only on the video transcript.

## TL;DR
- A **leaderboard** is a public ranking of LLMs on a common set of evals: where benchmark results get published and compared.
- There are 4 types: **single-benchmark**, **multi-benchmark** (most useful), **human-preference** (e.g. LMArena) and **application-specific** (e.g. BFCL).
- Don't trust them blindly (contamination, Goodhart's Law, hidden weighting, tiny gaps, human bias, stale data).
- **Leaderboards are a filtering tool, not a decision tool.** Shortlist 3–5 models, then run **your own evals**.

---

## Definition
> "An LLM leaderboard is a **public ranking or comparison table** that shows how different LLMs perform on a **common set of evaluations**."

A benchmark is the exam; the leaderboard is the results board.

## Why leaderboards exist
1. **Cross-lab comparison** on a common reference.
2. **Trust.** They're usually **third-party**, with lower stakes than self-reporting labs.
3. **Model selection without the resources to evaluate hundreds of models yourself.** Take the top 10 and choose from them.
4. **Spotting saturation.** If the top models cluster (e.g. 92–94), the benchmark is saturating.
5. **Discovering new models.** Scroll to positions 10–20 for cheaper models that may suit you.

## Who uses them

| Stakeholder | Use |
|---|---|
| **AI engineers** | **Shortlisting** candidate models (100 down to 5), then running their own evals |
| **Frontier labs** | Know where they stand, and decide **whether to release** (e.g. don't ship a GPT-5.x that can't beat Opus 4.8). Models sometimes appear **in stealth** under code names, e.g. Google's **Nano Banana** debuted anonymously on an image leaderboard and kept the name. |
| **Researchers** | Find which benchmarks saturated and where new research directions lie |
| **Policymakers / safety institutes** | Monitor capability jumps and step in when a model looks dangerous (the speaker cites the US government stepping in over Fable 5) |
| **Open-source community** | Discovery and publicity for small labs. A small lab topping one benchmark gets famous overnight, which is how many Chinese labs came to prominence. |

## The 4 types of leaderboards

| Type | What it ranks | Example | Usefulness |
|---|---|---|---|
| **Benchmark-specific** | One benchmark (MMLU, HumanEval, GSM8K, GPQA, …), usually maintained by the benchmark's authors | **HLE leaderboard** (Gemini 3 Pro ~38%, plus calibration error) | Narrow view, **least useful** |
| **Multi-benchmark** | Cumulative score across many benchmarks and dimensions, often with **cost per token, latency, output speed, context window** | **LiveBench** ("contamination-free", 23 objective tasks across 7 categories, with per-category and overall scores). **Artificial Analysis** (separate leaderboards for intelligence, speed, cost per task, HLE, GPQA Diamond, coding agents, speech, image, audio, hardware, plus an overall one) | **Most useful.** Answers "best overall combination of capability, cost and performance?" |
| **Human-preference** | **Pairwise human votes** (A vs B) on helpfulness, clarity, writing, creativity | **LMArena** battle mode: two anonymous models answer, you vote (A better / both good / both bad / B better), then the identities are revealed. Categories include chat, code, image, video. | Popular, used for marketing. Has **human bias**, but at global scale it's still informative. |
| **Application-specific** | A domain or task (coding, agentic, SQL, medical), possibly combining several benchmarks within it | **Berkeley Function Calling Leaderboard (BFCL)**, for tool calling | Use when building in that domain |

## Why you can't trust leaderboards blindly
1. **Benchmark performance may not transfer to real applications.** Benchmarks are clean, like Kaggle ("solving Kaggle doesn't make you a good data scientist"). Real apps have ambiguous requests, missing info, company-specific data, tool failures and edge cases.
2. **Contamination** inflates scores (memorization).
3. **Over-optimization for the leaderboard.** E.g. tuning models to win LMArena votes with formatting, softer or **sycophantic** answers, without real capability gains.
   - **Goodhart's Law:** *"When a measure becomes a target, it ceases to be a good measure."* For example, a car company that optimizes only for mileage (because Indian buyers prioritize it) ends up neglecting driving dynamics and acceleration.
4. **Hidden choices in composite leaderboards.** Which benchmarks are included or excluded, how scores are **normalized** and **weighted**. Prefer transparent leaderboards.
5. **Tiny differences don't matter.** 84.3 vs 84.1 (3rd vs 5th place) is effectively the same. Avoid **rank bias** (like JEE rank 1 vs 25).
6. **Human-preference bias.** People favour longer, more confident, better-formatted, entertaining answers. The objectively best model may lose.
7. **Stale, incomplete or self-reported results.** E.g. the HLE leaderboard is missing the newest models, some list discontinued ones, and some entries are **submitted by the companies themselves**.

## How an AI engineer should read leaderboards (the playbook)
1. **Write your requirements first:**
   - Application type
   - **Latency** needs
   - **Cost** budget
   - **Context** needs
   - **Deployment constraints** (public API vs on-prem; on-prem rules out e.g. Claude Fable, so go open-source)

   This removes the bias towards whatever is ranked #1.
2. **Go to the right leaderboard for your task:**
   - **Agents:** an agent leaderboard
   - **Chatbots:** LMArena-type
   - **RAG:** **MTEB** (ranks **embedding models**)
   - **Budget-sensitive:** **Artificial Analysis** or **Vellum** (speed and cost)
3. **Read it correctly.** What is scored, how, and by whom? Inference budget? Reasoning on or off? Dataset age and update frequency? **Private test set?** Saturated benchmarks? **Confidence intervals** (small datasets make close models effectively equal)? **Weights** in composite scores? Read the footnotes, definitions and FAQ.
4. **Shortlist the top 3–5** models against your criteria.
5. **Run your own custom evals** on the shortlist and pick the winner.

> **Leaderboards are a filtering tool, not a decision tool.**

## Coming next
Practical session: running **custom model evals** on shortlisted LLMs. Then application evals (RAG and agents).
