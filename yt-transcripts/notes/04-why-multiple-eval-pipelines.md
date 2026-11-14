# 04 — Why Your AI Application Needs Multiple Eval Pipelines

> Source: [Why Your AI Application Needs Multiple Eval Pipelines?](https://www.youtube.com/watch?v=DcZ-XCk-O_M) (CampusX). Notes are based only on the video transcript.

## TL;DR
An LLM app almost always needs **more than one eval pipeline**, for two reasons:
1. **Multiple failure points.** Failures happen at the **component**, **workflow** and **application** levels.
2. **Multiple risk categories.** Each failure point has several risk aspects: **quality**, **safety**, **operations**.

---

## Recap of earlier lectures
- **Why:** case studies of unevaluated apps failing in production.
- **What:** LLM evals = systematic, reliable evaluation against clear criteria. There are model evals (benchmarks, done by frontier labs) and application evals (the focus of this course).
- **How:** the step-by-step eval pipeline.
- The previous lecture ended with: *"One LLM-based application has several LLM evals."* This lecture explains why.

## Reason 1: multiple failure points

### Running example: a RAG chatbot
```
query → Retriever ⇄ Vector DB → (query + retrieved docs) → Generator (LLM) → answer
```

**Obvious failure points:**
- **Retriever** fetches the wrong documents, so the answer is wrong.
- **Generator** ignores good context and hallucinates.

So you put **one eval pipeline on each**:
- **Retriever eval:** given a query, are the **relevant documents** retrieved?
- **Generator eval:** is the answer **faithful / grounded** in the given context, with no invented facts?
  - Example: the doc says "ML course = 3 weeks". The answer should say exactly that, and nothing extra like "great course, also buy Python (4 weeks)".

### Components can pass and the pipeline still fails
Scenario with **K = 5** (retrieve the top 5 docs) and **no reranker**:
- D1–D4 are irrelevant. **D5** says "ML course duration = 8 weeks".
- **Did the retriever do its job?** Yes. With K = 5, the right answer just has to appear somewhere in the top 5 ("5 attempts, crack it once").
- The generator's prompt prioritises the **higher-ranked docs**. It picks "Python course = 6 weeks" from those and answers **"ML course is 6 weeks"**. ❌
- **Did the generator do its job?** Yes, in a sense. It didn't hallucinate; it followed instructions on the docs it was given.
- Both components "work", but **the pipeline broke**.

➡️ You need a **workflow-level eval** that checks how the retriever and generator work *together*. It would flag this error. The fix here is to **add a reranker**, which moves D5 to the top.

### Even then: application-level evals
- Retriever ✅, generator ✅, pipeline ✅, but each answer takes **10 seconds**. That isn't production-ready.
- You need an **application-level eval**, e.g. latency below a threshold.

### The three levels of failure points

| Level | What can fail | Examples |
|---|---|---|
| **Component** | Any single part | System prompt. RAG: retriever, reranker, query rewriter, embedding model, vector DB. Structured output: output parser. Agents: tool selector, memory, guardrails. |
| **Workflow** | How components interact | RAG workflow, an agent's workflow, a multi-turn chatbot flow |
| **Application** | The whole app as experienced | Total latency, token cost per query, **time to first token (TTFT)** |

## Reason 2: multiple risk categories
Each failure point has several aspects (risks). Examples:
- **Application level:** correct and helpful, **and** safe (e.g. never reveal another user's phone number or email).
- **Workflow level:** faithful and grounded, **and** not too costly (under a cost threshold).
- **Component level:** the retriever fetches the right docs, **and** with acceptable latency (not 5–10 s).

### The three risk categories

| Category | Question it answers |
|---|---|
| **Application quality** | Does the app do its actual job well: correct, relevant, complete answers? |
| **Safety** | Is the output harmful: toxic, dangerous, biased, leaking private data, jailbreakable? |
| **Operations** | Can it run **fast, cheap and reliably** once deployed? |

### Risk-category cheat sheet

**Application quality**

| App type | Risk categories |
|---|---|
| General LLM app (e.g. a summarizer) | **Correctness/accuracy**, **relevance**, **completeness**, **instruction following** (format/length) |
| RAG | **Context relevance**, **retriever recall**, **groundedness/faithfulness**, **citation accuracy** |
| Agents | **Tool selection**, **parameter correctness**, **task completion**, **error recovery** |
| Multi-turn chatbot | **Context retention** (remembers earlier turns), **clarification behaviour** (asks when ambiguous) |

**Safety**
- **Toxicity**
- **Harmful content**: self-harm, weapons, illegal acts
- **Bias**: does it treat all users the same?
- **PII leakage**: credit cards, contact details
- **Prompt injection / jailbreak resistance**

**Operations**
- **Latency**
- **Cost per request**
- **Token efficiency**
- **Error/failure rate**
- **Latency under load**

## Conclusion
- In the same app you'll have separate pipelines, e.g. one for **latency**, one for **safety**, one for **correctness**.
- ~99.99% of the time an LLM app has **more than one eval pipeline**, because of:
  1. Multiple **failure points** (component, workflow, application)
  2. Multiple **risk categories** (quality, safety, operations)
