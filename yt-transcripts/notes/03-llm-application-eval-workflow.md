# 03 — How to Evaluate LLM Applications: The Complete Workflow

> Source: [How to Evaluate LLM Applications: The Complete Workflow](https://www.youtube.com/watch?v=Pv4mkG2K_s8) (CampusX). Notes are based only on the video transcript.

## TL;DR
A repeatable loop: **define → criteria → golden dataset → eval method → run → score → analyse → improve → repeat → deploy → monitor → add prod failures back to the dataset.** The same workflow applies to simple apps, RAG and complex agents.

---

## Running example: email router (Zomato)
- Problem: a large company gets many customer emails every day. Manually reading and tagging them is hard.
- System: a single **LLM + system prompt** ("You are a customer agent; read the email and decide where to route it") that classifies each email as:
  - **Billing** → billing team
  - **Technical** → technical team
  - **General** → customer support
- It can be built in 5–10 minutes, but **don't deploy it directly. Evaluate it first.**

## The workflow, step by step

| # | Step | In the email-router example |
|---|---|---|
| 1 | **Define the task and target**: what are you evaluating? | Target: the whole workflow. Task: check it **classifies correctly**. |
| 2 | **Define success criteria + metric** | Criterion: correct classification. Metric: **accuracy** (90 of 100 routed correctly = 90%). |
| 3 | **Build a dataset** (the **golden dataset**) | Rows of *email text → correct label*: "My card was charged twice" → Billing; "The app crashes on login" → Technical; "What are your hours?" → General. Typically **50–500 rows**. Best source: **real past emails/chats**, **labelled manually**. |
| 4 | **Define the evaluation method**: who scores? | Options: **automated (code)**, **human**, or **LLM (LLM-as-a-judge)**. Here a simple **Python script** comparing predicted vs expected labels is enough. |
| 5 | **Run the system** on the dataset | Send every row through the app and collect its predictions. |
| 6 | **Evaluate the results** | The script computes accuracy, e.g. **80%** (80/100 correct). |
| 7 | **Analyse the results**: where and why does it fail? | E.g. the **system prompt** confuses billing vs technical, or the **model** is too weak (small or open-source). |
| 8 | **Improve the system** | Tweak the prompt, then 90%. Switch to a bigger LLM, then 95%. |
| 9 | **Iterate** | Re-run on the **same golden dataset** after every change. This is why evals must be **repeatable**. |
| 10 | **Deploy** when satisfied | |
| 11 | **Monitor in production** | 95% offline doesn't guarantee production quality, because new real data can fail. |
| 12 | **Feed production failures back** | A mis-routed email gets added to the **golden dataset**, and the loop restarts. |

### Choosing the evaluation method

| Method | When | Trade-off |
|---|---|---|
| **Automated (code)** | Exact or simple outputs (labels, classes) | Cheap, fast. You don't need a human or an LLM for simple label comparison. |
| **Human** | Anything | Accurate but **costly** (salaries) at scale |
| **LLM-as-a-judge** | Long free-text answers (e.g. a chatbot) where semantic meaning must be compared | The middle ground. Comparing two paragraphs by code is very hard. |

## The big loop
```
Golden dataset ──> Run system ──> Score ──> Analyse ──> Improve ─┐
      ^                                                          │ (repeat until good)
      │                                                          v
 Add prod failures <── Monitor <────────────── Deploy <──────────┘
```
- The golden dataset gets **richer over time**, and the system keeps improving against it.
- You keep doing this **for as long as the system is in deployment**. That's how you build **reliable** LLM apps.

### Q&A: who decides an output was wrong in production?
- Set up a **process**. E.g. a customer's billing email was routed to the technical team. The customer tells the technical team, the technical team **flags the case**, and it gets added to the dataset. That is the monitoring system in place.

## Key point: one app has many evals
> **One LLM-based application may have several LLM evals.**

E.g. for a RAG app, run separate evals for:
- The **retriever**
- The **embedding model**
- The **end-to-end RAG workflow**
- **System latency**
