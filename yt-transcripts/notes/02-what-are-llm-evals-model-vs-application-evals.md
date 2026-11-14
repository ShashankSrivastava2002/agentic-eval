# 02 — What Are LLM Evals? Model Evals vs Application Evals

> Source: [Introduction to LLM Evaluations – Model Evals vs Application Evals](https://www.youtube.com/watch?v=cNF_MO82Qew) (CampusX). Notes are based only on the video transcript.

## TL;DR
- **LLM evals** are *systematic, repeatable tests used to judge an LLM or an LLM-powered system against clear criteria.*
- An eval is **not just a metric**. It is the **entire testing setup**.
- There are two kinds: **model evals** (judge the LLM itself, via benchmarks) and **application evals** (judge the whole product you built). As an AI engineer you'll mostly do **application evals**.

---

## Definition and its three properties
> **LLM evals are systematic, repeatable tests used to judge an LLM or LLM-powered system against clear criteria.**

| Property | Meaning | Example |
|---|---|---|
| **Systematic** | Not vibe testing. Build proper **datasets** that cover edge cases. | For the CampusX chatbot, sample ~100 real user chats and build a test dataset from them. |
| **Repeatable** | After changing the prompt, model, retriever or chunking strategy, you can evaluate **exactly the same way** again. | Run the same test set on v1 and v2 and compare. This is how you know whether the system improved. |
| **Clear criteria** | Define *what "good" means* up front. | CampusX chatbot: correct, simply explained, sourced from course content, safe (no abuse or threatening tone). |

- Without criteria you are vibe testing. With criteria you are doing a proper evaluation.

## An eval is not just a metric
- Coming from ML, it's tempting to think "eval = metric" (accuracy, precision, recall).
- In LLM land, **an eval is the complete testing setup**:
  - **What** you're testing (e.g. the retriever inside a RAG chatbot)
  - **Criteria** you test against (e.g. retriever accuracy)
  - **Dataset** you test with
  - **When** you test (offline, or in production after deployment)
  - **Tool** you test with (e.g. RAGAS for a RAG app)
- The goal is not a score. It is to **answer practical questions**:
  - Can this model be used for this task?
  - Is this system good enough to ship?
  - Did prompt v2 improve over prompt v1?
  - Is the RAG answer grounded in the retrieved context?
  - Is the agent completing the task correctly?
  - Is the chatbot safe for real users?
  - Is latency under control?

## Two types of LLM evals
> ⚠️ "Model evals" and "application evals" are the instructor's own terms, used to simplify. They aren't official terms. Industry calls both "LLM evals".

### 1. Model evals
- **Evaluate the model itself**: test and document an LLM's **capabilities**.
- This is what you see on model launches: "Model X tops benchmark/leaderboard Y."
- **The 8 capability categories** new LLMs are tested on:
  1. **Reasoning**: solving problems step by step
  2. **Knowledge**: world/general knowledge up to the cutoff date
  3. **Maths**
  4. **Coding**
  5. **Instruction following**: does it follow all 10 instructions?
  6. **Long-context handling**: finding correct answers in huge contexts
  7. **Multimodal understanding**: images, text, audio (input/output)
  8. **Tool use**
- These are tested with **benchmarks**:

| Capability | Example benchmark |
|---|---|
| General knowledge & reasoning | **MMLU** (questions across science, history, law, medicine, …) |
| Maths | **GSM8K** (grade-school maths) |
| Coding | **SWE-bench**, **HumanEval** |
| Instruction following | **IFEval** |
| Long context | **Needle in a Haystack** |
| Multimodal | **MMMU** |

- **Will you do model evals as an AI engineer? Probably not.** The **frontier labs** do this. You need **literacy**: know what benchmarks are and how to read them, so you can **choose the right LLM** for a project (OpenAI vs Anthropic vs open source).

### 2. Application evals (the focus of the course)
> Application evals assess the behaviour and performance of an LLM-powered application, **either the entire system or a specific component** within it.

- In a real app, **the LLM is just one component**. Others include:
  - UI
  - System prompt
  - Tools / APIs
  - Orchestration code (e.g. LangGraph branching and parallelism)
  - Guardrails
  - Output parsers
  - Memory and context
  - Retrieval system, embedding model, vector DB (for RAG)
  - Monitoring setup and feedback loop after deployment
- **Smartphone analogy:** chip makers publish processor benchmark scores, but a strong processor doesn't guarantee a good phone. The camera, OS, sound, graphics and battery all matter and must be tested. Frontier labs evaluate the "processor" (the LLM). **You** are responsible for evaluating the whole "phone" you built.
- Evaluate at **two levels**:
  - **System level:** final response quality, latency, cost per token
  - **Component level:** retriever, embedding model, reranker, …
- Model evals ask *"Can the model do this?"*. Application evals ask ***"Will our product work properly?"***
- Example questions for the CampusX chatbot:
  - Was the student's question answered correctly?
  - Was course material used properly?
  - Was the answer faithful?
  - Was it beginner-friendly?
  - Did it hallucinate?
  - Was it fast?
  - Is it safe?

> 💡 When a YouTube video or article says "LLM evaluation", ~99% of the time it means **application evaluation**.

## Lecture flow so far
- **Why:** evals matter (video 01)
- **What:** definition, plus model vs application evals (this video)
- **Next, How:** the evaluation workflow, from the application-eval perspective
