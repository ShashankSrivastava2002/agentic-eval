# 08 — LLM Benchmarking: Anatomy, Eval Harnesses, Saturation & Contamination

> Source: [What is LLM Benchmarking | Benchmark Saturation vs. Contamination](https://www.youtube.com/watch?v=qIiU3lyjrhM) (CampusX). Notes are based only on the video transcript.

## TL;DR
- A **benchmark** = a **standardized test** for a specific model capability. It has 4 parts: **dataset/task, run configuration, scoring, aggregation**, all specified in its research paper.
- Running a benchmark is a loop over the dataset, but doing it reliably at scale needs an **eval harness** (e.g. EleutherAI's **lm-evaluation-harness**, Inspect, HELM).
- Three groups run benchmarks: **frontier labs** (treat their numbers as a ceiling), **third-party evaluators** (most reliable) and **AI engineering teams** (you).
- Take benchmarks with a pinch of salt: **contamination, saturation, configuration gaming, aggregation tricks**.

---

## What is a benchmark?
> "A benchmark is a standardized test used to measure a particular model capability."

Running example: **GSM8K** (*Grade School Maths*, "8K" ≈ 8,000–8,500 Q&A pairs, ~2020–21, now saturated).

### The 4 components

**1. Dataset + task**
- Questions **plus an answer key** (like a golden dataset). Available on Hugging Face and Kaggle.
- Sample: *"Natalia sold clips to 48 friends in April, and half as many in May. How many altogether?"* → 48 + 24 = **72**.
- Task: given a grade-school maths problem, generate the answer.

**2. Run configuration**: identical settings for every model compared.

| Part | Options / GSM8K choice |
|---|---|
| **Prompt construction** | **Zero-shot** (just the question) vs **few-shot** (solved examples first). GSM8K is classically **8-shot**. Few-shot gives better performance. |
| | **Chain of thought** ("solve step by step") vs a direct answer. GSM8K allows CoT. |
| **Decoding / sampling** | **Temperature ≈ 0** (otherwise answers vary). **Max tokens**: too low and CoT gets cut off mid-thought, too high gives an advantage to strong reasoners, so keep it the same for all models. |
| **Scoring strategy** | **pass@1**: one attempt, right or wrong (strict). **pass@k**: k attempts, correct if any one is right (lenient). **majority@k**: k answers, take the **mode**. |
| **Environment / tools** | Are tools allowed (web search, code interpreter)? **GSM8K: no tools.** SWE-bench: tools required (it must fetch GitHub issues). |

> When someone says "82% on benchmark X", ask whether it was **pass@1, pass@k or majority@k**, and under what settings.

**3. Scoring**
- **Extraction** first. LLM output can be "The answer is 72", "72" or "seventy-two", so use **structured output or regex** to pull out just the answer.
- **Comparison**:
  - Closed-ended answers: **exact match** (72 == 72, giving 1 or 0).
  - Open-ended paragraph answers: **LLM-as-a-judge** (or a human).

**4. Aggregation**
- Simple: mean of the 1/0 scores (920 of 1,000 = **92%**).
- Complex: **MMLU** reports per-subject scores (57 subjects, e.g. biology 87%, physics 91%, economics 72%). Subjects have different question counts, so use a **weighted mean**.

**Where is all this specified?** In each benchmark's **research paper** (GSM8K, MMLU, SWE-bench, …). Researchers create benchmarks for their fields, the datasets become popular, and every new LLM is measured on them.

---

## How a lab evaluates a new model on a benchmark
Example: a frontier lab tests its new model "CampusX v1" on GSM8K.

```
results = []
for item in dataset:                          # 1. load item
    prompt = build_prompt(item, fewshot=8,    # 2. build prompt (few-shot, chat template, instructions)
                          chat_template=True)
    raw = model.generate(prompt, temperature=0, max_tokens=..., stop=...)  # 3. call with pinned decoding config
    pred = extract_answer(raw)                # 4. extract answer ("The answer is 72" -> 72)
    results.append(score(pred, item.answer))  # 5. score (1/0)
final = aggregate(results)                    # 6. aggregate (mean / weighted mean)
```

### Why it isn't that simple, and why eval harnesses exist
Real code also needs:
- Answer extraction
- Paper-exact scoring
- **Batching** thousands of calls
- **Retries** on failed API calls
- **Rate-limit handling**
- Standardization, so runs are reproducible

> **Eval harness** = the plumbing code that executes model evaluations. **Analogy:** the benchmark is the *exam paper*. The harness is the *exam administration* that runs everything.

Popular harnesses:
- **lm-evaluation-harness** (EleutherAI): the industry standard for running benchmarks, with many built-in benchmarks
- **Inspect**
- **HELM**

### Demo: lm-evaluation-harness
- `pip install lm-eval`, then set the OpenAI API key (Hugging Face models are also supported).
- A single command, with arguments such as:
  - model = GPT-5.6
  - `num_concurrent = 5`
  - `max_retries`
  - task = **gsm8k (cot)**
  - `num_fewshot = 8`
  - apply chat template
  - **`limit = 20`** (a smoke test)
  - output path
  - log samples
- Full GSM8K would cost ~₹2,300 per run. 20 questions cost ~₹3–4.
- Result: **~90% (18/20)**. A JSON log per question (doc ID, question, answer) is written to the output folder.
- No loop or plumbing to write. Remove `limit` and you have a publishable GSM8K result.

**DeepEval vs lm-eval-harness:** DeepEval also offers benchmarks (GSM8K included, mostly saturated ones) but needs more code. It's better suited to **application evals** and trying small fine-tuned models. lm-eval-harness is the premium, standard choice.

---

## Who runs benchmarks?

| Stakeholder | Why | How to read their numbers |
|---|---|---|
| **Frontier labs** (OpenAI, Anthropic, Google DeepMind) | Check training direction at **checkpoints** during pre-training, **release gating**, **marketing** ("smashed the coding benchmarks") | Treat them as a **ceiling**. Favourable conditions plus **cherry-picking** (good benchmarks shown first). Like car mileage: quoted 25, real 5–10. (The speaker's personal take: Claude Fable didn't live up to its hype for him.) |
| **Third-party evaluators** / leaderboards (e.g. **LMArena**) | Evaluation is their product. Same conditions for all models. | **Most reliable.** Often also report **cost and latency**, which labs omit. "Leaderboards are like IMDb ratings for models." |
| **AI engineering teams (you)** | Verify scores, latency and cost **under your own conditions** with public benchmarks and harnesses | Your own ground truth |

Leaderboards are aggregations of many benchmarks; they're covered in the next class.

---

## Why benchmarks can mislead

| Problem | What it is | Mitigation / example |
|---|---|---|
| **Contamination** | Public benchmark datasets (questions **and** answers) end up in pre-training data scraped from the internet, so the model may have **memorized** them instead of reasoning | Use **private benchmarks** or **dynamic benchmarks** (datasets refreshed regularly) instead of static ones |
| **Saturation** | Static benchmark, improving models. Scores go from ~25–36% to 50, 70, then 90–95%, and all models **cluster** (e.g. Opus 9 at 95%, GPT-5.6 at 94%, Gemini at 92%), so it can no longer **differentiate** models | Retire it and adopt a new benchmark. **GSM8K, MMLU and SWE-bench are saturated.** Life cycle: launch, hard, models improve, saturated, retired, replaced. |
| **Configuration gaming** | A lab gives its own model the most favourable settings (e.g. a Python interpreter on GSM8K) and rivals default ones. Causes ~5–10% swings. | Distrust self-reported numbers that don't disclose max tokens, reasoning level, temperature, harness changes, latency and cost |
| **Aggregation tricks** | Reporting only an average hides weak areas (e.g. strong physics, weak economics in MMLU) | Ask for **per-category scores**. Otherwise you might deploy a model for an economics chatbot and find it performs badly. |

> Don't accept a number thrown in your face. Use your own methodology to decide which model works for you (continued in the next sessions).
