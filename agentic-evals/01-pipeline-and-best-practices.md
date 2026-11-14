# Agentic System Evals: Pipeline, Best Practices, Benchmarks

Researched 2026-11-14. Verification level per source:
- **[V]** = I read the primary page in full.
- **[S]** = Confirmed from search results pointing at the primary source (arXiv/GitHub), not opened.
- **[2nd]** = Secondary write-up only.

Main source: Anthropic Engineering, *Demystifying evals for AI agents* (Jan 9, 2026; Grace, Hadfield, Olivares, De Jonghe).
[V] https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

---

## 1. Vocabulary (from the Anthropic post) [V]
- **Task**: one test with defined inputs and success criteria.
- **Trial**: one attempt at a task. Run several, because agents are non-deterministic.
- **Grader**: scoring logic. A task can have several graders, each with several checks.
- **Transcript** (trace / trajectory): everything that happened, including messages, tool calls, reasoning and intermediate results.
- **Outcome**: the *final environment state*. The agent saying "flight booked" is not the outcome. The outcome is whether a reservation row actually exists in the DB.
- **Evaluation harness**: runs tasks concurrently, records, grades and aggregates.
- **Agent harness / scaffold**: the system that lets the model act. You always evaluate **model + harness together**.
- **Eval suite**: a group of tasks for one capability area.

---

## 2. The pipeline

```
 (0) Collect tasks ──> (1) Sandbox env ──> (2) Run k trials ──> (3) Trace everything
        ^                                                              │
        │                                                              v
 (7) Prod monitoring <── (6) CI regression gate <── (5) Error analysis <── (4) Grade
```

### Step 0: Collect tasks
- Start with **20–50 tasks drawn from real failures**. You don't need hundreds. Early effect sizes are large, so small sets are enough. [V]
- Sources for tasks: what you already check by hand before a release, common user tasks, and bug-tracker / support-queue failures, prioritized by user impact. [V]
- Every task must be **unambiguous and have a reference solution that passes all graders**. Two domain experts should reach the same pass/fail verdict. If a frontier model gets 0% at pass@100, the task is probably broken. [V]
- **Balance the set**: include cases where the behaviour *should* and *should not* happen (e.g. the search tool under-triggering vs. over-triggering). [V]

### Step 1: Stable, isolated environment
- Make it behave like production, and **start every trial from a clean state**. Leftover files, caches or resource exhaustion cause correlated failures. Shared state can also *inflate* scores: Anthropic saw Claude reading git history from previous trials. [V]

### Step 2: Run multiple trials, report reliability
- **pass@k** = at least one of k succeeds (good when one success is enough).
- **pass^k** = all k succeed (good for customer-facing agents that must be consistent).
  At 75% per-trial success, pass^3 ≈ 42%. [V]
- τ-bench introduced pass^k. GPT-4o got ~61% pass@1 on retail but ~25% at pass^8. [S] https://arxiv.org/abs/2406.12045

### Step 3: Trace everything
- Record the full transcript: tool calls with arguments, results, tokens, latency and cost.
- The **OpenTelemetry GenAI semantic conventions** define agent spans (`invoke_agent`, `execute_tool`, …) and a `gen_ai.evaluation.result` event for scores. As of Aug 2026 the spec was still marked *Development*, so pin versions. [2nd] https://www.truefoundry.com/blog/opentelemetry-genai-semantic-conventions

### Step 4: Grade, with three grader types [V]
| Type | Methods | Pros | Cons |
|---|---|---|---|
| Code-based | Exact/regex match, unit tests (fail→pass), static analysis, **outcome/state verification**, tool-call checks, turn/token counts | Fast, cheap, objective, reproducible | Brittle to valid variations |
| Model-based (LLM judge) | Rubrics, natural-language assertions, pairwise comparison, reference-based, multi-judge | Handles nuance and open-ended output | Non-deterministic, costs more, **needs human calibration** |
| Human | Expert review, spot-check sampling, A/B tests, inter-annotator agreement | Gold standard | Slow, expensive |

Rules of thumb [V]:
- Deterministic graders where possible, LLM graders where needed, humans to validate.
- **Grade the outcome, not the exact path.** Rigid tool-sequence checks penalize valid alternative solutions.
- Give partial credit. Use one isolated judge per dimension. Give the judge an "Unknown" option.
- Harden graders against reward hacking.

### Step 5: Error analysis (read transcripts!)
- Read transcripts and grades from many trials to separate **agent mistakes from grader bugs**. [V]
  Example: Opus 4.5 scored 42% on CORE-Bench until grading bugs were fixed, e.g. rejecting "96.12" when the expected value was 96.124991… It then scored 95%.
- Method (Husain & Shankar):
  1. **Open coding**: write free-form notes on what went wrong in each trace.
  2. **Axial coding**: cluster those notes into a failure taxonomy.
  3. Write evals for the top failure categories. [S] https://hamel.dev/blog/posts/evals-faq/why-is-error-analysis-so-important-in-llm-evals-and-how-is-it-performed.html
- For multi-agent systems, use **MAST** as a starting taxonomy: 14 failure modes in 3 categories, built from 150+ traces with κ = 0.88, and an LLM annotator that matches experts with κ = 0.77. NeurIPS 2025 D&B. [S] https://arxiv.org/abs/2503.13657

### Step 6: Capability vs. regression suites [V]
- **Capability evals** start at a low pass rate and give you a hill to climb.
- **Regression evals** stay near 100% and run on every change.
- When a capability eval saturates, *graduate* it into the regression suite and write harder capability tasks.

### Step 7: Production monitoring
- Sample real traces, rescore them with the same graders, and feed new failures back into Step 0.

---

## 3. Best-practice checklist
1. Evaluate model + harness together. Changing the scaffold changes the score. [V]
2. Check the outcome state, not what the agent *says* it did. [V]
3. Report pass^k (consistency) as well as pass@1. [V][S]
4. **Report cost alongside accuracy** and compare agents on a cost–accuracy Pareto frontier. Accuracy-only leaderboards reward needlessly expensive agents. [S] Kapoor et al., *AI Agents That Matter* (TMLR 2025) https://arxiv.org/abs/2407.01502 · leaderboard: https://agents.cs.princeton.edu/
5. Audit your benchmark's validity with the **Agentic Benchmark Checklist (ABC)**. Applied to 10 popular benchmarks, it found outcome-validity flaws in 7 and reporting gaps in all 10, enough to mis-estimate performance by up to 100% relative. [S] https://arxiv.org/abs/2507.02825
6. Calibrate LLM judges against human labels before trusting them. [V]
7. Watch for saturation. Public benchmarks lose signal; the post cites SWE-bench Verified as nearing saturation at >80%. [V]
8. Treat evals like unit tests: owned, versioned, contributed to by PMs and domain experts. Use eval-driven development: write the eval before the feature. [V]

### Per agent type [V]
| Agent type | How to grade |
|---|---|
| Coding | Unit tests + LLM quality rubric (+ lint/type/security static analysis) |
| Conversational | Simulated user (LLM) + end-state DB check + interaction-quality rubric + turn limit |
| Research | Groundedness (claims supported by sources), coverage of required facts, source quality |
| Computer use | Backend/state checks (was the order actually placed), not just the screenshot |

---

## 4. Public benchmarks
| Benchmark | Tests | Grading | Link |
|---|---|---|---|
| τ-bench / τ²-bench | Tool use + simulated user, retail/airline (+telecom in τ²) | Final DB state vs. goal, pass^k | [S] https://arxiv.org/abs/2406.12045 · https://github.com/sierra-research/tau-bench (repo says use τ²-bench) |
| SWE-bench Verified | Fix real GitHub issues (500 human-validated tasks) | Repo unit tests | [2nd] https://www.honeyhive.ai/learn/agent-benchmarks |
| Terminal-Bench | End-to-end CLI tasks | Container final state | [V] mentioned in the Anthropic post · ships via Harbor |
| WebArena | Web tasks on self-hosted sites (812 tasks) | URL/page + backend state | [2nd] same as above |
| OSWorld | Desktop computer use | File system / app config / DB / UI checks | [V] mentioned in the Anthropic post |
| GAIA | 466 real-world assistant questions (browse + tools) | Answer match | [2nd] |
| BFCL | Function-calling accuracy (serial, parallel, multi-turn) | AST / execution checks | [2nd] |
| BrowseComp | Hard web research | Answer match | [V] mentioned in the Anthropic post |

Overview list: https://www.philschmid.de/benchmark-compedium [2nd]

## 5. Tooling (listed in the Anthropic post's appendix) [V]
- **Harbor**: containerized agent environments at scale. https://harborframework.com
- **Braintrust**: offline evals + observability, `autoevals` scorers. https://braintrust.dev
- **LangSmith**: tracing + evals, LangChain ecosystem.
- **Langfuse**: open-source, self-hostable. https://langfuse.com
- **Arize Phoenix**: open-source tracing + evals. https://arize.com

The post's advice is to pick one quickly and invest in the test cases instead.

## 6. Caveats
- Benchmark task counts from HoneyHive/Phil Schmid are secondary. Check each benchmark's paper before citing.
- The OTel GenAI conventions' status is disputed across articles (Development vs. stable). Check the spec repo.
