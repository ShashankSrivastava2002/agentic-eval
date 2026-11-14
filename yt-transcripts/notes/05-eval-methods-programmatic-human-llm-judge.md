# 05 — LLM Eval Methods: Programmatic, Human, LLM-as-a-Judge · Reference-Based vs Reference-Free

> Source: [LLM Eval Methods | LLM-as-a-Judge | Reference Based vs Reference Free Evals](https://www.youtube.com/watch?v=uQFLY8rQVYA) (CampusX). Notes are based only on the video transcript.

## TL;DR
- An **eval method** is *who/what executes the eval pipeline and produces the judgment*. There are only three options: **programmatic**, **human**, **model-graded (LLM-as-a-judge)**.
- Use code where possible, humans where nuance and trust are needed (costly), and **LLM-as-a-judge** as the scalable middle ground. It is the most used.
- **Reference-based** = the golden dataset contains the correct answer. **Reference-free** = no correct answer, only a rubric.

---

## What is an eval method?
> "An LLM eval method is the mechanism you use to decide whether an LLM's output is good or not — the actual procedure that takes an output and produces a judgment about it."

| Method | Executed by |
|---|---|
| **Programmatic / deterministic** | Code |
| **Human** | People |
| **Model-graded / LLM-graded** | An LLM (**LLM-as-a-judge**) |

- The earlier email-router example (accuracy computed in Python) was **programmatic**.
- Note: the method is about who *executes* the eval. Building the golden dataset is a separate activity, usually done by humans.

---

## Example 1: programmatic eval (retriever of a CampusX RAG chatbot)
**Component-level eval.**

1. **Task / target:** check that the **retriever** (a single component) fetches the right docs.
2. **Success criterion / metric:** **Recall@k**
   > "Out of all the correct items that exist, how many did the system retrieve in its top-k results?"
   - Example: Q = "What are the prerequisites for the ML course, and how long is it?" Correct docs = {1001, 1003}. Retrieved (k = 5) = {1001, 1002, 1004, 1005, 1006}. Recall = **1/2 = 50%**.
   - Range 0–100%. Ideal = 100%.
   - (Precision and rank-based metrics also exist. Kept simple here.)
3. **Dataset (golden):** 50–100 questions covering easy, hard, edge-case and random questions. A **human expert** marks which document(s) contain each answer.
4. **Method:** programmatic. Send every question **only to the retriever** (not the whole chatbot), compute recall **per question** (e.g. Q1 = 1.0, Q2 = 0.5), then **average** to get dataset Recall@k (e.g. **67%**).
5. **Analyse the worst questions and improve the retriever:**
   - Better **embedding model**
   - **Query expansion** (an LLM rewrites/expands the query first)
   - Increase **k** (5 → 10)
   - Add a **reranker** (e.g. a doc at position 8 moves to position 3)
- No human needed to *run* it. If a program can do it, don't pay a human.

**Q&A, "relevance" has several aspects:**
1. Of all the correct docs, how many did you fetch? (recall, used here)
2. Of the docs you fetched, how many were *not* useful?
3. Are the fetched docs ranked properly?

---

## Example 2: human eval (helpfulness of a general CampusX chatbot)
**Application-level eval, quality only** (not safety or operations).

1. **Target:** the whole app. **Task:** evaluate **helpfulness** = accurate + right tone + complete.
2. **Success criterion:** no universal metric, so define a business-specific **rubric (1–5)**:
   - **5** = correct, accurate, complete, right tone
   - **3** = partially helpful
   - **1** = not helpful / off-topic
3. **Dataset:** 50–100 questions with **only one column (the question)**, e.g. "How long is the ML course?", "Is the ML course right for me if I know Python?", "DL course fee?", "Refund if I drop out?", "Pay in instalments?"
4. **Method:** human. It is too nuanced for code.
5. **Run:** send each question to the chatbot, then a human grades question + answer against the rubric. Average the scores to get the helpfulness score.

**Why use multiple graders (A, B)?** If they keep disagreeing (one gives 2, the other gives 4), the **rubric is ambiguous**. Use agreement between graders to **refine the rubric**.

### Five ways humans evaluate LLM systems
1. **Direct grading / rating**: the example above
2. **Red teaming**: humans deliberately attack the system to find where it breaks (done before big LLM launches). Findings go back to the dev team.
3. **A/B testing**: two versions in production, users rate them, and the better one ships everywhere
4. **Golden dataset and rubric creation**: labelling correct answers is itself evaluation
5. **Human-in-the-loop**: grey-area cases that code or LLM judges can't handle (or that hit a threshold) are escalated to a human

### Human eval: pros and cons
- ✅ **Reliable judgment, high trust.** Humans handle nuance better than machines.
- ❌ **Cost.** Not feasible at scale (hundreds of thousands to tens of millions of users).

---

## Example 3: LLM-as-a-judge (CampusX UPSC mains auto-grader)
**Setup:** UPSC has Prelims (MCQ, easy to auto-grade), Mains (subjective, needs subject-matter experts) and an Interview. Grading 10,000+ students' mains papers with experts is too expensive. A vendor platform grades them with an LLM against your rubrics for a fraction of the cost. **We must evaluate that platform.**

1. **Target / task:** does the platform grade answers **like human experts**?
2. **Success criterion:** the platform's marks match a human expert's marks.
3. **Rubric (per question), defined by an expert.** Example questions:
   - "Ethical governance is impossible without administrative accountability. Discuss." (15 marks)
   - "Examine the role of the Governor in Centre–State relations." (10 marks)
   - "Federalism in India is more cooperative than competitive. Critically analyse." (15 marks)
   - Rubric for Q1: covers ethical governance and accountability, explains the **link** between them, gives **mechanisms**, cites **examples**, has a **balanced conclusion**.
   - ⚠️ A rubric is **not** the dataset.
4. **Golden dataset (50–100 answers):** columns are answer ID, question, the student's exact answer, and the **human evaluator's score**. E.g. all 5 rubric points covered = 13/15; mostly missing = 4/15.
5. **Method:** LLM (code can't do it, humans are too costly).
6. **Judge prompt** (the gist):
   - "You are grading a UPSC mains answer against an evaluation rubric." Provide the question, marks, rubric and the aspirant's answer.
   - "For each dimension, decide whether the answer genuinely addresses it, then allocate marks. **Do not reward verbosity, keyword stuffing, or confident assertions that lack substantiation.** Reward structure, relevant examples and balanced argumentation."
   - Output: dimensions addressed, total marks, a one-sentence justification.
7. **Compare LLM marks with human marks** using **MAE (mean absolute error)**:
   - MAE = (|13 − 12| + |4 − 8| + |8 − 8| + …) / 50
   - E.g. MAE = **2.3** means the LLM deviates from the human by ±2.3 marks on average. **Goal: drive MAE towards 0.**
8. **Improve:** a better LLM, a better system prompt, a refined rubric. Loop.

> Building an LLM app is the easy part. Making sure it works **every time, everywhere** is the hard part. That's the production-engineer mindset.

---

## Reference-based vs reference-free evaluation

| | Reference-based | Reference-free |
|---|---|---|
| Definition | A **known correct answer** (or the key things it must contain) is written in advance for each test case, and the output is graded by comparing against it | **No predefined correct answer.** The output is judged on its own terms against a **criterion/rubric** |
| Rubric role | (n/a) | A **scale standard**, not a per-item correct answer |
| Examples from this lecture | **Retriever eval** (correct doc IDs known), **UPSC judge** (human marks are the reference) | **Chatbot helpfulness** (dataset = questions only, human judges with a rubric) |

**Quick test:** does your golden dataset contain the correct answer? Yes means reference-based. No means reference-free.

---

## Coming next
Everything so far is **offline evaluation**. Evaluation also continues after deployment, which is **online evaluation** (next video).
