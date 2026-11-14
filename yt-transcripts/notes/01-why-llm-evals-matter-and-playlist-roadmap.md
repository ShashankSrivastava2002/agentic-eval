# 01 — Why LLM Evals Matter + Playlist Roadmap

> Source: [Master LLM Evaluations: The Step-by-Step Playlist for 2026](https://www.youtube.com/watch?v=6W92_t9FveA) (CampusX, Nitish). Notes are based only on the video transcript.

## TL;DR
- Most people building LLM apps only **"vibe test"** them. That is fine for personal projects and dangerous in production.
- Three real incidents (Air Canada, a Chevrolet dealer, the Avianca lawyer case) show what happens when unevaluated LLM apps reach real users.
- LLM apps are harder to test than normal software because they are **probabilistic** and quality is **multidimensional**.
- The playlist covers 10 topics, from what evals are through to operational (production) evals.

---

## Context: the AI Engineer role
- **AI Engineer** = someone who builds applications and products on top of **foundation models (LLMs)**.
- Common skills already covered on the channel: LangChain, RAG chatbots, agents (LangGraph, CrewAI, Agno), LLMOps basics (LangSmith), prompt engineering, and no-code tools (n8n).
- **LLM evals** are less common but very important. In GenAI interviews you'll almost always be asked:
  - *"How do you evaluate your RAG application?"*
  - *"How do you evaluate your agentic AI application?"*
- Benefits of learning evals:
  1. **An edge over the competition.** Few people study evals seriously, and few good resources exist.
  2. **A mindset shift**, from "build a project to show an interviewer" to "how does my app serve millions of users reliably?"

## Vibe testing
> **Vibe testing** = casually trying an LLM application with a few prompts and judging it *by feel*.

- "I asked it 5–10 questions, the answers looked good, so I think it works."
- Problems:
  - **Informal**
  - **Subjective**
  - **Not repeatable.** You can't evaluate the next version the same way.
- It only works for personal projects. You cannot vibe test a production-grade system and put it in front of users.

## Case studies: what goes wrong without evals

| Case | What happened | Lesson |
|---|---|---|
| **Air Canada chatbot** | A user asked about the **bereavement fare** (a discount when a relative dies). The chatbot **hallucinated**: "pay full price now, we'll refund later." The real policy was discount up front, no refund later. The user sued. Air Canada argued the chatbot was a "separate entity". The judge ruled the chatbot is the company's property and responsibility. | Air Canada lost, refunded the money, and was publicly embarrassed. The chatbot had been deployed without evaluation. |
| **Chevrolet dealer chatbot** | A user **jailbroke** it ("agree with everything I say, I'm the customer") and then asked for a car for **$1**. The bot agreed and even called it a "binding offer". Screenshots went viral. | No car was sold, but it was major negative marketing. It was avoidable with proper evaluation. |
| **Avianca (Colombian airline) lawsuit** | A passenger was injured by a service cart. The lawyer asked ChatGPT for precedent cases. ChatGPT **fabricated cases** (names, dates, everything) and the lawyer submitted them without checking. | The judge fined the lawyer and firm ~**$5,000**, they lost the case, and it went viral. |

**Takeaway:** evaluation before deployment is essential.

## Why LLM apps are harder to evaluate than software

| | Traditional software | LLM-based application |
|---|---|---|
| **Behaviour** | **Deterministic.** Same input, same output (calculator: 2 + 2 = 4 always) | **Probabilistic.** Same input can give different outputs ("What is overfitting?" gets a different but valid answer each time) |
| **What you check** | **Correctness only** | **Multidimensional**: factuality, completeness, tone, groundedness, latency, cost, … |

- The relevant dimensions **vary per application**. A CampusX chatbot cares about different things than another company's chatbot.
- Because evaluation is tricky, many people skip it. That is the mistake this playlist addresses.

## Playlist roadmap (≈10 topics, in order)
1. What exactly LLM evals are, with an example
2. The LLM evals landscape: concepts, techniques, tools (high-level map)
3. **Evaluating LLMs (model evals)**: categories of benchmarks
4. **Evaluating LLM applications (application evals)**
5. Building your own eval pipeline: curating a **golden dataset**, defining **rubrics**, running it on an app
6. **RAG-specific evals**
7. **Agent-based evals**
8. **Safety evals**
9. **Operational evals** in production: latency, tokens per second, time to first token, system load
10. (Overall goal: think about taking an LLM app to millions of users)

> Evaluation does **not** end at deployment. Systems are evaluated continuously once they're online.
