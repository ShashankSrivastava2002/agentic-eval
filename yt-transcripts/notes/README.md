# LLM Evals: Study Notes (CampusX playlist)

Notes made **only from the video transcripts** in `../transcripts-en/` (English translations of the original Hindi captions). One file per video.

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
