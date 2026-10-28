# Voice Agent Evals: Pipeline + Pre-built Datasets

Researched 2026-10-28. Verification level per source:
- **[V]** = I opened the primary page (repo / HF dataset / arXiv abstract) and confirmed the details.
- **[S]** = Confirmed from search results that point at the primary source (arXiv/ICML/GitHub), but I did not open the page.
- **[Vendor]** = Vendor blog. The numbers are opinions/rules of thumb, not standards.

---

## 1. The pipeline

A cascaded voice agent is `Audio in -> VAD/turn detection -> STT -> LLM (+tools) -> TTS -> Audio out`.
Speech-to-speech models (gpt-realtime, Gemini Live) collapse the middle, but the eval layers below still apply.

### Layer 0: Build the test set
- Use real recorded user audio from your domain (accents, noise, domain terms), not only TTS-generated prompts.
  Proof: the tool-calling paper below found that ASR artifacts, prosody shifts and channel noise make voice runs diverge from text runs.
  It treats TTS-synthesized audio as a first-stage proxy, not a substitute.
  [S] https://arxiv.org/pdf/2605.15104
- Add perturbations: noise (MUSAN, DNS Challenge), accents, and caller behaviours (interrupting, rambling, hesitating).

### Layer 1: Component evals (each stage alone)
| Stage | Metric | How | Source |
|---|---|---|---|
| STT | WER = (S + D + I) / N | Normalize the text, then compute with `jiwer`. Run it on your own audio. | Open ASR Leaderboard paper argues no single dataset or metric is enough [S] https://arxiv.org/abs/2510.06961 |
| STT | RTFx (speed) | Audio seconds / compute seconds | same |
| LLM | Task / tool-call accuracy, faithfulness | Evaluate on text transcripts first (cheap) | |
| TTS | Intelligibility WER, speaker similarity (SIM), naturalness (UTMOS / NISQA / MOS) | Seed-TTS-eval: Whisper-large-v3 ASR -> WER; WavLM-large speaker-verification embedding -> cosine SIM | [S] https://github.com/BytedanceSpeech/seed-tts-eval |
| Latency | STT final, LLM TTFT, TTS TTFB | Timestamp each stage | Vendor targets: STT <200ms, LLM TTFT <400ms, TTS TTFB <150ms [Vendor] https://hamming.ai/resources/how-to-evaluate-voice-agents-2026 |

### Layer 2: Turn-level / conversational dynamics
- **Turn latency**: end of user speech -> first agent audio. Track P50/P95, not just the mean. One vendor targets P95 < 800ms.
  [Vendor] https://hamming.ai/resources/voice-agent-evaluation-metrics-guide
  Stage latencies are not purely additive, so measure end to end.
  [Vendor] https://telnyx.com/resources/voice-ai-agents-compared-latency
- **Turn-taking**: pause handling, backchannels, barge-in/interruption handling, false interruptions.
  Benchmark: Full-Duplex-Bench (below).

### Layer 3: End-to-end simulated conversations
- A simulated caller (LLM + TTS with a persona and goal) talks to your agent over real audio.
- Score with: task completion (check final DB/tool state, not just the transcript), policy adherence, faithfulness, conciseness, and turn-taking.
- **Run each scenario k times**: report pass@1 AND pass^k (all k succeed). EVA-Bench found a median pass@k - pass^k gap of 0.44, so a single run is very misleading.
  [V] https://arxiv.org/abs/2605.13841
- Validate the simulator itself. EVA regenerates conversations where the simulated user went off-script, so the scores reflect the agent and not simulator errors.
- Reference implementation: **ServiceNow EVA** (MIT, Pipecat-based, cascade + speech-to-speech).
  [V] https://github.com/ServiceNow/eva

### Layer 4: Judges
- An LLM-as-judge on the transcript for semantics (faithfulness, policy).
- An audio-LLM judge for what was actually spoken (EVA's "Agent Speech Fidelity", in beta). This catches TTS mispronouncing numbers or entities.
- Calibrate any judge against a human-labelled sample before trusting it.

### Layer 5: CI regression + production monitoring
- Run the scenario suite on every prompt/model/provider change and diff it against a stored baseline.
  [Vendor] https://hamming.ai/resources/voice-agent-testing-guide
- In production: sample real calls, rescore them with the same judges, and track latency percentiles and task-success drift.
  Feed failures back into the Layer 0 test set.

---

## 2. Pre-built datasets / benchmarks

### End-to-end voice agents (tool use, tasks)
| Name | What it tests | Size / details | Links |
|---|---|---|---|
| **τ-Voice** (Sierra et al., ICML 2026) | Full-duplex voice agents on τ²-bench tasks (Retail, Airline, Telecom), clean vs. realistic audio (noise, accents) | 278 tasks. Abstract: GPT-5 text ~80% vs. voice agents 29-42% clean, 19-30% realistic | [S] https://arxiv.org/abs/2603.13686 · https://proceedings.mlr.press/v306/ray26a.html |
| **EVA-Bench / ServiceNow EVA** (EMNLP 2026 Findings) | Bot-to-bot full conversations in enterprise domains, accent/noise perturbations, pass^k | 213 scenarios. Airline, Healthcare HR, IT service management. Metrics EVA-A (accuracy) + EVA-X (experience) | [V] https://arxiv.org/abs/2605.13841 · https://github.com/ServiceNow/eva |
| **Full-Duplex-Bench v3** | Tool use under real human disfluencies (chained API calls) | All real human audio, 5 disfluency types, 4 domains | [S] https://arxiv.org/abs/2604.04847 |

### Conversational dynamics
| Name | What it tests | Links |
|---|---|---|
| **Full-Duplex-Bench** (v1, ASRU 2025; v1.5, v2) | Pause handling, backchanneling, turn-taking, interruption, with automatic metrics | [S] https://arxiv.org/abs/2503.04721 · https://github.com/DanielLin94144/Full-Duplex-Bench |

### Spoken-input understanding / assistant quality
| Name | What it tests | Size / details | Links |
|---|---|---|---|
| **VoiceBench** (TACL 2026) | LLM voice assistants: open QA, MCQ, instruction following (IFEval), reasoning (BBH), safety (AdvBench) | 11 subsets. Mix of Google-TTS and human audio (e.g. wildvoice: 1,000 human). gpt-4o-mini judge for open-ended subsets | [V] https://arxiv.org/abs/2410.17196 · https://github.com/MatthewCYM/VoiceBench · https://huggingface.co/datasets/hlt-lab/voicebench |
| **Big Bench Audio** (Artificial Analysis) | Audio reasoning (4 BBH categories) | 1,000 questions, synthetic voices from 23 configs (OpenAI/Azure/Polly), MIT license | [V] https://huggingface.co/datasets/ArtificialAnalysis/big_bench_audio |
| **SLURP** (EMNLP 2020) | Spoken language understanding: intent + entity from audio | ~72k recordings, 18 domains, SLU-F1 metric | [S] https://arxiv.org/abs/2011.13205 · https://github.com/pswietojanski/slurp |

### STT (ASR) component
| Name | Notes | Links |
|---|---|---|
| **Open ASR Leaderboard** (HF) | WER + RTFx across LibriSpeech, GigaSpeech, VoxPopuli, TED-LIUM, SPGISpeech, AMI, etc. Multilingual + long-form | [S] https://arxiv.org/abs/2510.06961 · https://huggingface.co/spaces/hf-audio/open_asr_leaderboard · https://github.com/huggingface/open_asr_leaderboard |

### TTS component
| Name | Notes | Links |
|---|---|---|
| **Seed-TTS-eval** (ByteDance) | Test lists (EN, ZH, ZH-hard) + `cal_wer.sh` / `cal_sim.sh`. UTMOS is not included, so add it separately | [S] https://github.com/BytedanceSpeech/seed-tts-eval |

### Noise for robustness perturbation
| Name | Notes | Links |
|---|---|---|
| **MUSAN** | Music, speech (12 languages), noise (~6h, 929 files). CC license | [S] https://arxiv.org/abs/1510.08484 · https://www.openslr.org/17/ |
| **Microsoft DNS Challenge** | ~180h noise, 150 categories | [S] https://github.com/microsoft/DNS-Challenge |

---

## 3. Open-source tooling seen
- ServiceNow EVA: simulated caller, Pipecat, MIT. [V] https://github.com/ServiceNow/eva
- VoiceAIStackEvaluation: compares STT/TTS/LLM combos on WER, latency and NISQA. Personal project. [S] https://github.com/MahsaPaknezhad/VoiceAIStackEvaluation
- Commercial (not verified here): Hamming, Coval, Cekura, Vapi/Retell built-in testing.

## 4. Caveats
- Latency/WER thresholds from Hamming and Telnyx are vendor rules of thumb and differ between sources. Calibrate on your own traffic.
- Numbers in the τ-Voice abstract differ from a third-party review of it. Cite the paper directly.
- Most "agent" benchmarks are from 2026 and are moving fast. Check the repo before relying on dataset contents.
