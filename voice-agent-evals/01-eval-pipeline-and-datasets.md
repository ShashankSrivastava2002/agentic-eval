# Voice Agent Evals: Pipeline + Pre-built Datasets

Researched 2026-10-28, re-checked against primary sources 2026-10-29. Verification level per source:
- **[V]** = I opened the primary page (repo / HF dataset / arXiv abstract) and confirmed the details.
- **[S]** = Confirmed from search results that point at the primary source (arXiv/ICML/GitHub), but I did not open the page.
- **[Vendor]** = Vendor blog. The numbers are opinions/rules of thumb, not standards.

---

## 1. The pipeline

A cascaded voice agent is `Audio in -> VAD/turn detection -> STT -> LLM (+tools) -> TTS -> Audio out`.
Speech-to-speech models (gpt-realtime, Gemini Live) collapse the middle, but the eval layers below still apply.

### Layer 0: Build the test set
- Use real recorded user audio from your domain (accents, noise, domain terms), not only TTS-generated prompts.
  Evidence: a text-to-voice tool-calling study (TTS + speaker variation + noise over Confetti / When2Call) found a 1.8-4.8 point text-to-voice gap, mostly from misheard argument values.
  The authors position TTS-converted audio as a first-stage diagnostic that complements purpose-built audio corpora, not a substitute.
  [V] https://arxiv.org/abs/2605.15104
- Add perturbations: noise (MUSAN, DNS Challenge), accents, and caller behaviours (interrupting, rambling, hesitating).

### Layer 1: Component evals (each stage alone)
| Stage | Metric | How | Source |
|---|---|---|---|
| STT | WER = (S + D + I) / N | Normalize the text, then compute with `jiwer`. Run it on your own audio. | Open ASR Leaderboard standardizes WER + RTFx across 86 systems and 12 datasets [V] https://arxiv.org/abs/2510.06961 |
| STT | RTFx (inverse real-time factor, speed) | Audio seconds / processing seconds | same |
| LLM | Task / tool-call accuracy, faithfulness | Evaluate on text transcripts first (cheap) | |
| TTS | Intelligibility WER, speaker similarity (SIM), naturalness (UTMOS / NISQA / MOS) | Seed-TTS-eval: Whisper-large-v3 (EN) / Paraformer-zh (ZH) ASR -> WER; WavLM-large speaker-verification embedding -> cosine SIM | [V] https://github.com/BytedanceSpeech/seed-tts-eval |
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
| **τ-Voice** (Ray, Dhandhania, Barres, Narasimhan; ICML 2026, PMLR 306) | Full-duplex voice agents on τ²-bench tasks (Retail, Airline, Telecom), clean vs. realistic audio (noise, accents) | 278 tasks, pass@1. Abstract: GPT-5 (reasoning, text) 85% vs. voice agents 31-51% clean, 26-38% realistic (30-45% of text capability). 79-90% of failures attributed to agent behaviour | [V] https://arxiv.org/abs/2603.13686 · https://proceedings.mlr.press/v306/ray26a.html |
| **EVA-Bench / ServiceNow EVA** (EMNLP 2026) | Bot-to-bot full conversations in enterprise domains, accent/noise/connection-degradation perturbations, pass@1 / pass@k / pass^k | 213 scenarios. Airline CSM, Healthcare HRSD, ITSM. EVA-A (task completion, faithfulness, speech fidelity) + EVA-X (turn-taking, conciseness, conversation progression). 12 systems evaluated | [V] https://arxiv.org/abs/2605.13841 · https://github.com/ServiceNow/eva |
| **Full-Duplex-Bench v3** | Tool use under real human disfluencies (chained API calls) | All real human audio, 5 disfluency types (fillers, pauses, hesitations, false starts, self-corrections), 4 domains. 6 systems incl. a cascaded baseline. Code + data released 2026-05 | [V] https://arxiv.org/abs/2604.04847 |

### Conversational dynamics
| Name | What it tests | Links |
|---|---|---|
| **Full-Duplex-Bench** (v1, v1.5, v2) | v1: pause handling, backchanneling, smooth turn-taking, user interruption (static, automatic metrics). v1.5: overlap (backchannel, side conversation, ambient speech). v2: live multi-turn with an automated LLM examiner | [V] https://arxiv.org/abs/2503.04721 · https://arxiv.org/abs/2507.23159 · https://arxiv.org/abs/2510.07838 · https://github.com/DanielLin94144/Full-Duplex-Bench |

### Spoken-input understanding / assistant quality
| Name | What it tests | Size / details | Links |
|---|---|---|---|
| **VoiceBench** (TACL 2026) | LLM voice assistants: open QA, MCQ, instruction following (IFEval), reasoning (BBH), safety (AdvBench) | 11 subsets. Mix of Google-TTS and human audio (e.g. wildvoice: 1,000 human). gpt-4o-mini judge for open-ended subsets | [V] https://arxiv.org/abs/2410.17196 · https://github.com/MatthewCYM/VoiceBench · https://huggingface.co/datasets/hlt-lab/voicebench |
| **Big Bench Audio** (Artificial Analysis) | Audio reasoning (4 BBH categories) | 1,000 questions (250 per category), English only, synthetic voices from 23 configs (OpenAI/Azure/AWS Polly), mostly US/UK accents, MIT license | [V] https://huggingface.co/datasets/ArtificialAnalysis/big_bench_audio |
| **SLURP** (EMNLP 2020) | Spoken language understanding: intent + entity from audio | ~72k recordings, 18 domains, SLU-F1 metric | [S] https://arxiv.org/abs/2011.13205 · https://github.com/pswietojanski/slurp |

### STT (ASR) component
| Name | Notes | Links |
|---|---|---|
| **Open ASR Leaderboard** (HF) | WER + RTFx across LibriSpeech, GigaSpeech, VoxPopuli, TED-LIUM, SPGISpeech, AMI, etc. 86 systems, 12 datasets; English short- + long-form and multilingual short-form tracks | [V] https://arxiv.org/abs/2510.06961 · https://huggingface.co/spaces/hf-audio/open_asr_leaderboard · https://github.com/huggingface/open_asr_leaderboard |

### TTS component
| Name | Notes | Links |
|---|---|---|
| **Seed-TTS-eval** (ByteDance) | Zero-shot TTS test lists (EN: 1,000 Common Voice; ZH: 2,000 DiDiSpeech-2; ZH-hard) plus voice-conversion lists, with `cal_wer.sh` / `cal_sim.sh`. Only WER + SIM; UTMOS is not included, so add it separately | [V] https://github.com/BytedanceSpeech/seed-tts-eval |

### Noise for robustness perturbation
| Name | Notes | Links |
|---|---|---|
| **MUSAN** | Music, speech (12 languages), noise (~6h, 929 files). CC BY 4.0 | [V] license/languages, [S] noise size · https://arxiv.org/abs/1510.08484 · https://www.openslr.org/17/ |
| **Microsoft DNS Challenge** | ~180h noise, 150 categories. Repo `main` is now DNS5 (ICASSP 2023); check which edition's noise set you download | [S] https://github.com/microsoft/DNS-Challenge |

---

## 3. Open-source tooling seen
- ServiceNow EVA: simulated caller, Pipecat, MIT. [V] https://github.com/ServiceNow/eva
- VoiceAIStackEvaluation: compares STT/TTS/LLM combos on WER, latency and NISQA. Personal project. [S] https://github.com/MahsaPaknezhad/VoiceAIStackEvaluation
- Commercial (not verified here): Hamming, Coval, Cekura, Vapi/Retell built-in testing.

## 4. Caveats
- Latency/WER thresholds from Hamming and Telnyx are vendor rules of thumb and differ between sources. Calibrate on your own traffic.
- Third-party summaries of τ-Voice quote different numbers than the paper. Cite the ICML/arXiv abstract directly (figures above are from it).
- Most "agent" benchmarks are from 2026 and are moving fast. Check the repo before relying on dataset contents.
