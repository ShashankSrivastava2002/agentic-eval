# LLM Evals: Study Notes (CampusX playlist)

One file per video, built from the transcripts in `../transcripts-en/` (English translations of the original Hindi captions).

- **Notes 01, 02, 07–11** use only the transcript.
- **Notes 03–06 and 12–19** are expanded study notes: plain-language explanations, worked examples, Mermaid diagrams, self-tests, and verified outside research.
  - 🔎 **Beyond the lecture**: extra material from research or documentation
  - ✏️ **Correction / clarification**: places where the lecture was imprecise
  - Mermaid diagrams render on GitHub, in Obsidian, and in VS Code with a Mermaid extension.

## Part 1: Foundations
| # | Note | Key ideas |
|---|---|---|
| 01 | [Why evals matter + roadmap](01-why-llm-evals-matter-and-playlist-roadmap.md) | Vibe testing; Air Canada / Chevrolet / Avianca; deterministic vs probabilistic |
| 02 | [Model vs application evals](02-what-are-llm-evals-model-vs-application-evals.md) | Systematic, repeatable, clear criteria; eval = the whole setup; 8 capabilities |
| 03 | [The eval workflow](03-llm-application-eval-workflow.md) | Task → criteria → golden set → method → run → analyse → improve → deploy → monitor |
| 04 | [Multiple eval pipelines](04-why-multiple-eval-pipelines.md) | Component / workflow / application failure points; quality / safety / ops risks |
| 05 | [Eval methods](05-eval-methods-programmatic-human-llm-judge.md) | Programmatic, human, LLM-as-a-judge; Recall@k; MAE; reference-based vs reference-free |
| 06 | [Offline vs online](06-offline-vs-online-evals.md) | Gating, regression, drift; correctness vs normality; log → sample → evaluate → dashboard → alert |

## Part 2: Model evals
| # | Note | Key ideas |
|---|---|---|
| 07 | [Model evals & capabilities](07-model-evals-and-llm-capabilities.md) | Why AI engineers need model evals; benchmarks vs custom evals; 8 capabilities |
| 08 | [Benchmarking](08-llm-benchmarking-harnesses-and-pitfalls.md) | Dataset, run config, scoring, aggregation; lm-eval-harness; contamination and saturation |
| 09 | [Knowledge benchmarks](09-knowledge-benchmarks-evolution.md) | MMLU → TruthfulQA / AGIEval / GPQA / MMLU-Pro → SimpleQA / HLE |
| 10 | [Leaderboards](10-llm-leaderboards.md) | 4 types; Goodhart's Law; "a filter, not a decision tool" |
| 11 | [Custom model evals](11-custom-model-evals-text-to-sql-case-study.md) | Text-to-SQL; cost maths; prompt caching; execution-based scoring |

## Part 3: RAG evals (CampusX Doubt Solver)
| # | Note | Key ideas |
|---|---|---|
| 12 | [RAG eval framework](12-rag-eval-framework-interview-answer.md) | 3-level eval suite, regression testing, online evals; the interview answer |
| 13 | [Retriever evals](13-evaluating-rag-retrievers-hands-on.md) | Contextual recall and precision (DeepEval); golden set design |
| 14 | [Generator + RAG triad](14-evaluating-generator-and-rag-triad.md) | Faithfulness, answer relevancy, contextual relevancy; noise inside chunks |
| 15 | [G-Eval](15-g-eval-correctness-completeness-style.md) | Count-based vs judgment-based; evaluation steps + log-prob weighting |
| 16 | [Safety evals](16-rag-safety-evals-toxicity-leakage-scope.md) | Attack taxonomy; guardrails; toxicity, leakage, scope |
| 17 | [Ops evals](17-rag-operational-evals-latency-cost-reliability.md) | P50/P95/P99, TTFT, cost per query, reliability |
| 18 | [Regression testing](18-rag-regression-testing.md) | Baseline vs candidate; metric registry (direction + 2σ noise); promote/review/block |
| 19 | [Online evals](19-online-rag-evaluation-langsmith.md) | LangSmith tracing, dashboards, alerts; same evaluators offline and online |

## Key corrections made to the lecture material
1. **Contextual precision (note 13):** DeepEval averages precision **only at the positions of relevant chunks**, then divides by the number of relevant chunks. The lecture averaged over all positions. Both reward ranking relevant chunks high, but the scores differ.
2. **G-Eval `strict_mode` (note 15):** in DeepEval it forces a **binary 0/1 score** (perfect or fail). It doesn't toggle probability weighting.
3. **G-Eval paper (note 15):** GPT-4 didn't expose token probabilities, so the paper **estimated them by sampling 20 responses**. G-Eval is far more stable than naive judging but **not fully deterministic**.
4. **Toxicity score direction (note 16):** the lecture used toxic ÷ total (lower is better). Current DeepEval docs use **non-toxic ÷ total (higher is safer)**. Check your installed version.
5. **Sampling example (note 6):** the intended example is sampling ~1,000 out of **50,000** daily conversations.
6. **Noise threshold (note 18):** the demo used only 2 baseline runs. Use 5–10+ for a meaningful standard deviation.

## Main external sources
- G-Eval paper: Liu et al. 2023, [arXiv:2303.16634](https://arxiv.org/abs/2303.16634)
- LLM-as-a-judge biases: Zheng et al. 2023, [arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
- Lost in the Middle: Liu et al. 2023, [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)
- Spotlighting (indirect prompt-injection defence): Hines et al. 2024, [arXiv:2403.14720](https://arxiv.org/abs/2403.14720)
- DeepEval metric docs: [faithfulness](https://deepeval.com/docs/metrics-faithfulness), [answer relevancy](https://deepeval.com/docs/metrics-answer-relevancy), [contextual precision](https://deepeval.com/docs/metrics-contextual-precision), [contextual recall](https://deepeval.com/docs/metrics-contextual-recall), [contextual relevancy](https://deepeval.com/docs/metrics-contextual-relevancy), [G-Eval](https://deepeval.com/docs/metrics-llm-evals), [toxicity](https://deepeval.com/docs/metrics-toxicity), [PII leakage](https://deepeval.com/docs/metrics-pii-leakage), [RAG triad guide](https://deepeval.com/guides/guides-rag-triad)
- OWASP Top 10 for LLM Applications 2025: [announcement](https://genai.owasp.org/2024/11/17/owasp-reveals-2025-top-10-risks-for-llms-new-sponsorship-program/)
- LangSmith online evaluations: [LLM-as-judge](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge), [rules](https://docs.langchain.com/langsmith/rules)
- Prompt caching: [OpenAI](https://developers.openai.com/api/docs/guides/prompt-caching), [Anthropic](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
