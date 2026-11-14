# 07 — Model Evals & the 8 Core LLM Capabilities

> Source: [LLM Model Evals & Capabilities](https://www.youtube.com/watch?v=FPS0rIAQwzo) (CampusX). Notes are based only on the video transcript.

## TL;DR
- AI engineers need model evals to **choose, upgrade and justify** the LLM inside their application.
- A model eval has 4 steps: **pick a capability → bring a test → run under a fixed protocol → score and interpret**.
- There are two kinds of tests: **benchmarks** (standardized, for comparison) and **custom eval sets** (your own task and data). Custom evals can reverse the conclusion benchmarks give you.
- LLMs are assessed on **8 core capabilities**.

---

## Why do AI engineers need model evals?
> "If you can't measure it, you can't improve it."

Frontier labs use model evals to steer training. For an **AI engineer** they matter because:
1. **Model selection.** "OpenAI or Claude?" must be answered in a team meeting with **concrete pointers**: the capabilities your app needs and which model scores higher on them.
2. **Tracking new models.** Your app runs on Claude Opus 4.8 and Claude Fable comes out. Is it really better? Model evals give the numbers to justify an upgrade.
3. **Safety assurance.** How much does it hallucinate? Can it be jailbroken?
4. **Build vs buy.** A proprietary API (e.g. Claude: more powerful, more expensive) or a self-hosted open-source model (e.g. DeepSeek from Hugging Face on your own servers, cheaper)?

> Without model evals, you're **blind**.

## Formal definition
> "A model eval is a systematic process of measuring an underlying model's **capabilities, behaviour, reliability, and operational characteristics** under **controlled conditions**."

### The 4 steps of every model eval
1. **Decide the capability** to test (reasoning, coding, safety, instruction following, …). There's no single "IQ" number for LLMs; each capability needs its own eval.
2. **Bring a test** for that capability.
3. **Run the model under a fixed protocol**: the same prompts and conditions, so the run is **repeatable** and every model gets the same conditions.
4. **Score and interpret / publish.**

### Two types of tests

| | **Benchmarks** | **Custom eval sets** |
|---|---|---|
| What | Standardized, shared tests (e.g. **MMLU**, **SWE-bench**) | "Data you assemble from your actual task, which measures what you specifically care about rather than what's generically useful." |
| Good for | Comparing models on **common ground**, generic capabilities | Finding the best model **for your app and data** |

### Example: benchmarks vs custom eval (Zomato email router)
Task: classify emails as billing / technical / refund, plus judge urgency.

| | **Model A** (big, top of leaderboard, Opus-like) | **Model B** (small, mid-table, MiniMax/Qwen-like) |
|---|---|---|
| Price | ~$15 / 1M tokens | ~$0.50 / 1M tokens |
| Classification accuracy (custom set) | **94%** | **91%** |
| Urgency accuracy | 88% | 87% |
| Cost per 1,000 emails | $6 | < $0.21 |
| Latency | 4.1 s | **0.9 s** |

- Custom golden set: **200–500 past emails**, labelled.
- Benchmarks alone would always pick **A**. The custom eval shows **B** is the better value: almost the same accuracy at a fraction of the cost and latency.

**Plan:** this session covers **benchmarks** ("LLM benchmarking"). The next one covers **custom model evals**.

---

## The 8 core LLM capabilities
LLMs are general-purpose (generation, sentiment, summarization, POS tagging, …). Most benchmarks target one of these eight agreed categories.

| # | Capability | What's measured | Why it matters / where it's used |
|---|---|---|---|
| 1 | **Knowledge & reasoning** | Factual recall across subjects (e.g. **MMLU covers 57 subjects**). **Multi-step logical reasoning**: connecting facts in the right order (e.g. "summarize evolution from the Big Bang and explain today's society"). | The main signal of a model's **intelligence**. Used in research assistants, analysing technical documents and papers, and professional helpers (law, teaching). |
| 2 | **Coding & software engineering** | Function-level code from English. Generating tests and fixing code from failing tests. **Bug fixing in existing codebases.** Multi-file, long-horizon tasks (refactors). **Command-line work** (install packages, configure servers, set up environments). API/function calling. | The most **economically valuable** capability (e.g. Cursor's ~$60B valuation). Powers AI coding agents. |
| 3 | **Mathematics** | Grade-school maths, **competition (Olympiad)** problems, undergraduate maths, **research-level open problems** | A form of step-by-step reasoning with many real uses: scientific computing, financial modelling, engineering simulations, data analysis |
| 4 | **Long context** | Using information from very long inputs (hundreds of thousands of tokens): finding a small fact, pulling one entity's details from huge docs, summarizing huge contexts, keeping a large codebase in context | Models claim 128K/200K/1M windows, but quality **degrades as context grows**. Tests show which models really cope. Relevant to almost every app. |
| 5 | **Vision & multimodal** | Understanding images and video beyond text | We live in a multimodal world ("what can I cook with what's in my fridge?") |
| 6 | **Agentic & tool use** | Autonomous web browsing, structured tool calling, API interaction, **desktop/computer use** | The basis of agentic AI: LLMs that *do* things. You need a reliable model for agentic apps. |
| 7 | **Safety & alignment** | No harmful content, robustness to **adversarial attacks**, **truthfulness vs sycophancy** (not praising every idea), plus newer **cybersecurity** skills (cryptography, reverse engineering, digital forensics) | Government pressure and **reputational risk** for labs. (The speaker's opinion: Claude is more truthful and less sycophantic than ChatGPT. He also notes Claude Fable was strong at finding software vulnerabilities.) |
| 8 | **Instruction following** | Obeys format and constraints (bullet list, < 200 words, friendly tone). **Asks clarifying questions** when instructions are ambiguous. | Translates directly into **user satisfaction**. Users leave products that don't listen. |

---

## Note on teaching approach
The early sessions are deliberately theory-heavy (overview mode). The instructor says, from experience with his MLOps and deep learning courses, that a strong theory base makes the later practical sessions (golden datasets, metrics) much more productive.
