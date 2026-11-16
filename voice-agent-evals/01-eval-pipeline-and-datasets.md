# Voice Agent Evals: Pipeline + Pre-built Datasets

Researched 2026-10-28, re-checked against primary sources 2026-10-29. Verification level per source:
- **[V]** = I opened the primary page (repo / HF dataset / arXiv abstract) and confirmed the details.
- **[S]** = Confirmed from search results that point at the primary source (arXiv/ICML/GitHub), but I did not open the page.
- **[Vendor]** = Vendor blog. The numbers are opinions/rules of thumb, not standards.

---

## 0. Abbreviations
| Term | Meaning |
|---|---|
| VAD | Voice Activity Detection: detects when someone is speaking |
| STT / ASR | Speech-to-Text / Automatic Speech Recognition (same thing) |
| LLM | Large Language Model |
| TTS | Text-to-Speech |
| Barge-in | The user starts talking while the agent is speaking, and the agent should stop |
| Backchannel | Short listener sounds ("mm-hm", "yeah") that are not a request to take the turn |
| Full-duplex | The system can listen and speak at the same time (vs. half-duplex: strict turns) |
| Cascade | Separate STT -> LLM -> TTS models (vs. speech-to-speech: one audio-native model) |
| SLU-F1 | SLURP's F1 score for entity extraction from speech. F1 = 2 × precision × recall / (precision + recall) |
| EVA-A / EVA-X | EVA's composite Accuracy score / Experience score |

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

#### How the datasets in this section are laid out

Every metric below comes with three things: the table it needs, a few example rows, and how to calculate the metric from that table (SQL for Postgres, or Python where a library does the work).

- Tables join on `call_id` and `turn_id`.
- The "Filled by" column says where each value comes from:
  - **auto**: Dograh already records it (the location is noted).
  - **label**: a human fills it in. Production calls have no ground truth, so these columns are the ones that cost money.
  - **judge**: an LLM judge fills it in. Check judges against humans first (Layer 4).
  - **computed**: a script fills it in from other columns.
- No published standard covers all these metrics, so the table layout is our own design. Where a column copies a benchmark's format, the source is named. The sources for the formats:
  - [V] τ²-bench task file `data/tau2/domains/airline/tasks.json`, for `user_scenario`, `initial_state` and `evaluation_criteria.actions` / `nl_assertions`. https://github.com/sierra-research/tau2-bench
  - [V] SLURP README, for entity labels and per-recording `wer` / `ent_wer`. https://github.com/pswietojanski/slurp
  - [V] EVA `docs/data.md`, for scenario = goal with decision tree + persona + scenario database + ground-truth database. https://github.com/ServiceNow/eva
  - Not fetched, from general knowledge: the ACR 1-5 rating scale for MOS is defined in ITU-T Recommendation P.800.
  - Dograh fields were checked in the code: `workflow_runs` columns, `recordings/{id}/user.wav` and `bot.wav` (`api/services/workflow_run_artifacts.py`), per-turn speech timestamps and the `interrupted` flag (`api/services/pipecat/transcript_log_coordinator.py`), `realtime_feedback_events` (`api/services/pipecat/realtime_feedback_events.py`), and `TIME_TAKEN_*` latency logs (`api/services/pipecat/latency_observer.py`).

#### Base tables (every other table links to these)

**`calls`**: one row per call.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | auto | `workflow_runs.id` |
| workflow_version_id | text | auto | `workflow_runs.definition_id`, the graph version the call ran |
| direction | inbound / outbound | auto | `call_type` |
| started_at | timestamptz | auto | `created_at` |
| duration_s | float | auto | `usage_info.call_duration_seconds` |
| provider_combo | text | auto | e.g. `vobiz/sarvam-stt/sarvam-llm/sarvam-tts` |
| sample_rate_hz | int | auto | 8000 for phone calls |
| user_audio_uri | text | auto | `recordings/{id}/user.wav`, caller only |
| bot_audio_uri | text | auto | `recordings/{id}/bot.wav`, agent only |
| end_reason | text | auto | user_hangup, bot_end_call, transfer, error |
| language | text | label | |
| accent | text | label | |
| noise_condition | clean / light / heavy | label | |

| call_id | workflow_version_id | direction | duration_s | provider_combo | end_reason | language | accent | noise_condition |
|---|---|---|---|---|---|---|---|---|
| c1 | v12 | outbound | 94.2 | vobiz/sarvam/sarvam/sarvam | bot_end_call | hi-IN | north | clean |
| c2 | v12 | outbound | 41.0 | vobiz/sarvam/sarvam/sarvam | user_hangup | en-IN | south | heavy |

**`turns`**: one row per user utterance and the agent's reply.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id, turn_id | text, int | auto | turn number from `TurnTrackingObserver` |
| node_id | text | auto | workflow node active in this turn |
| user_speech_start_ts, user_speech_end_ts | timestamptz (ms) | auto | from VAD. The end lands about 0.2 s after the person really stopped |
| user_text_stt | text | auto | final STT transcript |
| agent_text | text | auto | `realtime_feedback_events` bot_text |
| agent_speech_start_ts, agent_speech_end_ts | timestamptz (ms) | auto | |
| interrupted | bool | auto | the caller barged in on this reply |

**`tool_calls`**: one row per tool call the agent made.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id, turn_id | text, int | auto | |
| tool_call_id | text | auto | `function_call_start` / `function_call_end` events |
| name | text | auto | |
| arguments | jsonb | auto | |
| result | jsonb | auto | |
| status | ok / error / timeout | auto | |

Dograh records the caller and the agent on separate tracks. That is what makes the clip-level tables below possible: STT clips are cut from `user.wav` and TTS clips from `bot.wav`, using the turn timestamps.

#### Noise perturbation dataset

**`perturbed_audio`**: one row per clean clip × one noise setting.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| perturbed_id | text | computed | |
| source_utterance_id | text | computed | the clean clip, a row in `stt_utterances` (Layer 1) |
| noise_corpus | MUSAN / DNS | computed | |
| noise_file | text | computed | |
| snr_db | float | computed | e.g. 20, 10, 5, 0. Lower means louder noise |
| codec_sim | text, nullable | computed | e.g. `g711_mulaw_8k` |
| audio_uri | text | computed | the mixed clip, made with `mix_at_snr()` (section 2a) |

| perturbed_id | source_utterance_id | noise_corpus | snr_db |
|---|---|---|---|
| p1 | u1 | MUSAN | 10 |
| p2 | u1 | MUSAN | 0 |

**How to calculate.** Run each mixed clip through STT and insert the result into `stt_utterances` as a new row with `perturbed_id` set and the same `reference_text` as the clean clip. Then compare WER at each noise level against clean:

```sql
SELECT COALESCE(p.snr_db::text, 'clean') AS condition,
       SUM(u.subs + u.dels + u.ins)::float / SUM(u.ref_words) AS wer
FROM stt_utterances u
LEFT JOIN perturbed_audio p ON p.perturbed_id = u.perturbed_id
GROUP BY 1
ORDER BY 1;
```

### Layer 1: Component evals (each stage alone)
| Stage | Metric | How | Source |
|---|---|---|---|
| STT | WER = (S + D + I) / N | Normalize the text, then compute with `jiwer`. Run it on your own audio. | Open ASR Leaderboard standardizes WER + RTFx across 86 systems and 12 datasets [V] https://arxiv.org/abs/2510.06961 |
| STT | RTFx (inverse real-time factor, speed) | Audio seconds / processing seconds | same |
| LLM | Task / tool-call accuracy, faithfulness | Evaluate on text transcripts first (cheap) | |
| TTS | Intelligibility WER, speaker similarity (SIM), naturalness (UTMOS / NISQA / MOS) | Seed-TTS-eval: Whisper-large-v3 (EN) / Paraformer-zh (ZH) ASR -> WER; WavLM-large speaker-verification embedding -> cosine SIM | [V] https://github.com/BytedanceSpeech/seed-tts-eval |
| Latency | STT final, LLM TTFT, TTS TTFB | Timestamp each stage | Vendor targets: STT <200ms, LLM TTFT <400ms, TTS TTFB <150ms [Vendor] https://hamming.ai/resources/how-to-evaluate-voice-agents-2026 |

#### Metrics in the table above, explained

**WER (Word Error Rate)**: `WER = (S + D + I) / N`

Align the system's transcript (hypothesis) against the correct transcript (reference) word by word, using the minimum number of edits (Levenshtein alignment). Then count:
- **S** (substitutions): a reference word replaced by a different word.
- **D** (deletions): a reference word that is missing from the hypothesis.
- **I** (insertions): an extra word in the hypothesis that is not in the reference.
- **N**: the total number of words in the reference.

```
Reference:  book  a  flight  to  boston          (N = 5)
Hypothesis: book     flight  to  austin  please
                 D                S       I
WER = (1 + 1 + 1) / 5 = 0.60 = 60%
```
Lower is better. 0% means a perfect match. WER can go above 100%, because insertions are not capped by N.
Normalize both texts first (lowercase, strip punctuation, treat "10" and "ten" the same way), or formatting differences get counted as errors.

```python
import jiwer
jiwer.wer("book a flight to boston", "book flight to austin please")  # 0.6
```

**Dataset `stt_utterances`**: one row per user utterance.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| utterance_id | text | computed | |
| call_id, turn_id | text, int | auto | |
| perturbed_id | text, nullable | computed | empty for the original audio, set for a noisy copy (Layer 0) |
| audio_uri | text | computed | cut from `user.wav` from `user_speech_start_ts` − 200 ms to `user_speech_end_ts` + 200 ms |
| audio_duration_s | float | computed | |
| reference_text | text | label | word-for-word human transcript, fillers included |
| hypothesis_text | text | auto | `turns.user_text_stt` |
| subs, dels, ins, ref_words | int | computed | S, D, I and N from jiwer, after normalizing both texts |

| utterance_id | reference_text | hypothesis_text | subs | dels | ins | ref_words |
|---|---|---|---|---|---|---|
| u1 | book a flight to boston | book flight to austin please | 1 | 1 | 1 | 5 |
| u2 | yes that is correct | yes that is correct | 0 | 0 | 0 | 4 |
| u3 | call me tomorrow at five | call me tomorrow at nine | 1 | 0 | 0 | 5 |

**How to calculate.** Fill the count columns per row with jiwer, then add the counts up across rows:

```python
out = jiwer.process_words(normalize(row.reference_text), normalize(row.hypothesis_text))
row.subs, row.dels, row.ins = out.substitutions, out.deletions, out.insertions
row.ref_words = out.substitutions + out.deletions + out.hits
```

```sql
SELECT SUM(subs + dels + ins)::float / SUM(ref_words) AS wer
FROM stt_utterances
WHERE perturbed_id IS NULL;
-- example rows: (3 + 0 + 1) / (5 + 4 + 5) = 4 / 14 = 0.286
```

Add the counts first and divide once. Averaging the per-utterance WERs (0.6, 0, 0.2 → 0.267) lets short utterances count as much as long ones. To split by accent or noise, join `calls` and add `GROUP BY calls.accent`.

**Dataset `stt_entities`**: one row per key entity in an utterance. This is SLURP-style entity labelling and EVA's "Key Entities" diagnostic: one wrong digit in a code breaks the task but barely moves WER.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| utterance_id | text | | links to `stt_utterances` |
| entity_type | text | label | phone, date, time, amount, id_code, name, address, city |
| reference_value | text | label | |
| hypothesis_value | text, nullable | label | what the STT wrote for this entity |
| match | bool | computed | exact match after normalizing |

| utterance_id | entity_type | reference_value | hypothesis_value | match |
|---|---|---|---|---|
| u1 | city | boston | austin | false |
| u3 | time | five | nine | false |
| u4 | id_code | DJ3LPO | DJ3LPO | true |

**How to calculate.**

```sql
SELECT entity_type, AVG(match::int) AS entity_accuracy, COUNT(*) AS n
FROM stt_entities
GROUP BY entity_type;
```

**RTFx (inverse Real-Time Factor)**: `RTFx = audio duration (s) / processing time (s)`

This measures STT speed. Higher is faster. RTFx = 100 means one hour of audio is transcribed in 36 seconds. RTFx < 1 means the system is slower than real time.

RTFx is a batch measure. Live calls use streaming STT, which runs at real time by design, so measure RTFx offline by re-running the same clips through each candidate system.

**Dataset `stt_offline_runs`**: one row per utterance × STT system.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| utterance_id | text | | links to `stt_utterances` |
| stt_system | text | computed | provider / model / version |
| hypothesis_text | text | computed | also gives you WER per system |
| processing_time_s | float | computed | wall-clock time for this clip |

| utterance_id | stt_system | audio_duration_s (from `stt_utterances`) | processing_time_s |
|---|---|---|---|
| u1 | model-A | 2.1 | 0.020 |
| u2 | model-A | 1.4 | 0.015 |
| u3 | model-A | 2.5 | 0.025 |

**How to calculate.**

```sql
SELECT r.stt_system,
       SUM(u.audio_duration_s) / SUM(r.processing_time_s) AS rtfx
FROM stt_offline_runs r
JOIN stt_utterances u USING (utterance_id)
GROUP BY r.stt_system;
-- example rows: 6.0 / 0.06 = 100
```

**Task / tool-call accuracy (LLM)**: run the LLM on text transcripts with known correct answers.
- Task accuracy = scenarios where the goal was reached / total scenarios.
- Tool-call accuracy = calls with the right tool name AND the right argument values / expected calls.

**Dataset `task_results`**: one row per call. The same table is used for Layer 3 simulated calls and for production calls.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | auto | |
| run_type | text_replay / simulated / production | computed | |
| expected_end_state | jsonb | label | what should be true after the call |
| actual_end_state | jsonb | auto | `gathered_context` plus what the tools changed, or the record in your CRM |
| end_state_match | bool | computed | every tracked key matches, and nothing else changed |
| goal_reached_human | bool | label | a human's verdict, kept to catch a bad `expected_end_state` |

| call_id | expected_end_state | actual_end_state | end_state_match |
|---|---|---|---|
| c1 | {"appointment_booked": true, "date": "2026-11-20"} | {"appointment_booked": true, "date": "2026-11-20"} | true |
| c2 | {"appointment_booked": true, "date": "2026-11-21"} | {"appointment_booked": true, "date": "2026-11-22"} | false |

Check the system the agent changed, not the transcript. τ²-bench does this with `reward_basis: ["DB", ...]`, and EVA compares a SHA-256 hash of the final database with the expected one.

**How to calculate.**

```sql
SELECT run_type, AVG(end_state_match::int) AS task_accuracy, COUNT(*) AS n
FROM task_results
GROUP BY run_type;
-- example rows: (1 + 0) / 2 = 0.5
```

**Dataset `expected_tool_calls`**: one row per tool call the agent should make. The columns copy τ²-bench's `evaluation_criteria.actions` format (`action_id`, `name`, `arguments`).

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | | |
| action_id | text | label | |
| name | text | label | |
| arguments | jsonb | label | |
| arg_match_rule | exact / normalized / judge | label | judge is for harmless variation, e.g. date formats |

The actual calls come from the `tool_calls` base table. A script pairs expected and actual calls with the same tool name, in order, and writes one row per pair, per missed call, and per extra call:

**Dataset `tool_call_matches`**

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | computed | |
| action_id | text, nullable | computed | empty = the agent made a call nobody expected (extra) |
| tool_call_id | text, nullable | computed | empty = an expected call the agent never made (missed) |
| args_match | bool, nullable | computed / judge | only for pairs, using `arg_match_rule` |

Example. Expected for c1: a1 `check_availability {date: 2026-11-20}`, a2 `book_appointment {date: 2026-11-20, slot: "10:00"}`. Actual: t1 `check_availability {date: 2026-11-20}`, t2 `book_appointment {date: 2026-11-20, slot: "11:00"}`, t3 `get_weather {}`.

| call_id | action_id | tool_call_id | args_match | meaning |
|---|---|---|---|---|
| c1 | a1 | t1 | true | right tool, right arguments |
| c1 | a2 | t2 | false | right tool, wrong slot |
| c1 | | t3 | | extra call |

**How to calculate.** Pairs count as hits. Precision is hurt by extra calls, recall by missed calls, and pass@1 needs everything right (the Full-Duplex-Bench v3 definitions).

```sql
SELECT
  COUNT(*) FILTER (WHERE action_id IS NOT NULL AND tool_call_id IS NOT NULL)::float
    / NULLIF(COUNT(*) FILTER (WHERE tool_call_id IS NOT NULL), 0) AS precision,
  COUNT(*) FILTER (WHERE action_id IS NOT NULL AND tool_call_id IS NOT NULL)::float
    / NULLIF(COUNT(*) FILTER (WHERE action_id IS NOT NULL), 0) AS recall,
  AVG(args_match::int) FILTER (WHERE action_id IS NOT NULL AND tool_call_id IS NOT NULL)
    AS argument_accuracy
FROM tool_call_matches;
-- example rows: precision 2/3 = 0.67, recall 2/2 = 1.0,
-- F1 = 2 × 0.67 × 1.0 / (0.67 + 1.0) = 0.8, argument accuracy 1/2 = 0.5

-- pass@1 per call: no missed calls, no extra calls, all arguments right
SELECT call_id,
       bool_and(action_id IS NOT NULL AND tool_call_id IS NOT NULL AND args_match) AS pass_at_1
FROM tool_call_matches
GROUP BY call_id;
-- example: c1 = false
```

**Dataset `extraction_results`**: one row per call × extracted variable. In Dograh this checks variable extraction and call disposition, the same idea as SLURP's intent and entity labels.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | | |
| variable_name | text | auto | e.g. `call_disposition`, `callback_date` |
| expected_value | text, nullable | label | |
| extracted_value | text, nullable | auto | `gathered_context` |
| match | bool | computed | exact, normalized, or judge |

| call_id | variable_name | expected_value | extracted_value | match |
|---|---|---|---|---|
| c1 | call_disposition | interested | interested | true |
| c1 | callback_date | 2026-11-20 | 2026-11-21 | false |

**How to calculate.**

```sql
SELECT variable_name, AVG(match::int) AS accuracy, COUNT(*) AS n
FROM extraction_results
GROUP BY variable_name;
```

**Faithfulness (LLM)**: the share of agent responses that are supported by the tool results, knowledge base or policy, with nothing made up. This is usually scored by an LLM judge (see Layer 4).

**Dataset `faithfulness_claims`**: one row per factual claim in an agent reply. The judge splits each reply (`turns.agent_text`) into claims and checks each one against what the agent was allowed to use: the node prompt, knowledge-base chunks, `tool_calls.result`, and what the caller said earlier.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id, turn_id | text, int | | the reply being checked |
| claim_id | text | judge | |
| claim_text | text | judge | |
| verdict | supported / unsupported / contradicted | judge | |
| evidence_ref | text, nullable | judge | e.g. tool_call_id or KB chunk id |
| judged_by | text | | judge model + prompt version, or "human" |

| call_id | turn_id | claim_text | verdict | evidence_ref |
|---|---|---|---|---|
| c1 | 3 | Your appointment is on 20 November | supported | t2 |
| c1 | 3 | You will get a reminder SMS | unsupported | |
| c1 | 4 | The clinic opens at 9 am | supported | kb_17 |

**How to calculate.** A reply is faithful only if every claim in it is supported.

```sql
SELECT AVG(faithful::int) AS faithfulness
FROM (
  SELECT call_id, turn_id, bool_and(verdict = 'supported') AS faithful
  FROM faithfulness_claims
  GROUP BY call_id, turn_id
) replies;
-- example rows: turn 3 fails, turn 4 passes → 0.5
```

**Intelligibility WER (TTS)**: feed the TTS audio into a strong ASR model (e.g. Whisper-large-v3), then compute WER against the text the TTS was asked to speak. A high WER means the speech is hard to understand, or words were skipped or mispronounced.

**Dataset `tts_utterances`**: one row per agent utterance. The same table holds SIM and UTMOS / NISQA (below).

| Column | Type | Filled by | Notes |
|---|---|---|---|
| utterance_id | text | computed | |
| call_id, turn_id | text, int | auto | |
| tts_input_text | text | auto | the text TTS was told to speak |
| audio_uri | text | computed | cut from `bot.wav` between `agent_speech_start_ts` and `agent_speech_end_ts` |
| asr_model | text | computed | e.g. whisper-large-v3, as in Seed-TTS-eval |
| asr_transcript | text | computed | |
| subs, dels, ins, ref_words | int | computed | jiwer, with `tts_input_text` as the reference |
| reference_voice_uri | text, nullable | label | only for a cloned or brand voice |
| sim_cosine | float, nullable | computed | |
| utmos, nisqa | float, nullable | computed | predicted naturalness |

`bot.wav` is 8 kHz on phone calls. That is what the caller hears, which is right for production, but don't compare these numbers with benchmark results made on 24 kHz audio.

| utterance_id | tts_input_text | asr_transcript | subs | dels | ins | ref_words | sim_cosine | utmos |
|---|---|---|---|---|---|---|---|---|
| v1 | your appointment is on november twentieth | your appointment is on november twenty | 1 | 0 | 0 | 6 | 0.71 | 3.9 |
| v2 | goodbye and have a nice day | goodbye and have a nice day | 0 | 0 | 0 | 6 | 0.68 | 4.1 |

**How to calculate.** The same way as STT WER, with the TTS input text as the reference:

```sql
SELECT SUM(subs + dels + ins)::float / SUM(ref_words) AS intelligibility_wer,
       AVG(sim_cosine) AS sim,
       AVG(utmos) AS utmos
FROM tts_utterances;
-- example rows: WER 1/12 = 0.083, SIM 0.695, UTMOS 4.0
```

**SIM (speaker similarity, TTS)**: `SIM = cos(a, b) = (a · b) / (|a| × |b|)`
- **a**: speaker embedding (a vector describing the voice) of the generated TTS audio.
- **b**: speaker embedding of the reference voice clip.
- **a · b**: dot product. **|a|**, **|b|**: vector lengths.

The range is -1 to 1. Closer to 1 means the generated voice sounds more like the reference speaker. This only matters for voice cloning or a fixed brand voice.

**How to calculate.** Fill `tts_utterances.sim_cosine` per row, then average it (SQL above):

```python
import numpy as np
a = embed(row.audio_uri)               # e.g. WavLM-large speaker-verification embedding
b = embed(row.reference_voice_uri)
row.sim_cosine = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

**MOS / UTMOS / NISQA (naturalness, TTS)**
- **MOS** (Mean Opinion Score): humans rate audio quality from 1 (bad) to 5 (excellent), and you average the ratings.
- **UTMOS**, **NISQA**: neural models that predict MOS without human listeners. They are cheaper, but only approximate human ratings. They go in `tts_utterances.utmos` / `nisqa`.

**Dataset `mos_ratings`**: one row per utterance × human rater.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| utterance_id | text | | links to `tts_utterances` |
| rater_id | text | label | |
| rating | int 1-5 | label | ACR scale: 1 Bad, 2 Poor, 3 Fair, 4 Good, 5 Excellent |
| listening_device | headphones / phone_handset / speaker | label | rate on a phone handset to match what callers hear |

| utterance_id | rater_id | rating |
|---|---|---|
| v1 | r1 | 4 |
| v1 | r2 | 4 |
| v1 | r3 | 3 |
| v2 | r1 | 5 |
| v2 | r2 | 4 |
| v2 | r3 | 4 |

**How to calculate.** Average the ratings, with a 95% confidence interval:

```sql
SELECT AVG(rating) AS mos,
       1.96 * STDDEV_SAMP(rating) / SQRT(COUNT(*)) AS ci95
FROM mos_ratings;
-- example rows: per utterance v1 = 3.67, v2 = 4.33; overall 24 / 6 = 4.0
```

**Latency**
- **STT final**: time from the end of user speech until the STT emits its final (not interim) transcript.
- **TTFT** (Time To First Token): time from sending the prompt to the LLM until it returns its first token.
- **TTFB** (Time To First Byte): time from sending text to the TTS until the first audio bytes come back.
- **P50 / P95** (used in Layer 2): percentiles. P50 (median) means half of the turns are faster than this value. P95 means 95% are faster, so it captures the slow tail that users notice.

**Dataset `turn_timings`**: one row per turn. Layer 2's turn latency uses the same table.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id, turn_id | text, int | auto | |
| stt_final_ms | int | auto | `TIME_TAKEN_STT_TTFB` log. Check that your STT measures it from the end of speech |
| llm_ttft_ms | int | auto | `TIME_TAKEN_LLM_TTFB`, or the `ttfb_metric` feedback event |
| tts_ttfb_ms | int | auto | `TIME_TAKEN_TTS_TTFB` |
| turn_latency_ms | int | computed | `turns.agent_speech_start_ts − turns.user_speech_end_ts` |
| had_tool_call | bool | auto | tool turns are slower; report them separately |

| call_id | turn_id | stt_final_ms | llm_ttft_ms | tts_ttfb_ms | turn_latency_ms | had_tool_call |
|---|---|---|---|---|---|---|
| c1 | 1 | 180 | 350 | 120 | 760 | false |
| c1 | 2 | 210 | 900 | 130 | 1420 | true |
| c1 | 3 | 170 | 380 | 140 | 790 | false |
| c2 | 1 | 250 | 420 | 160 | 930 | false |

**How to calculate.**

```sql
SELECT c.provider_combo,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY t.stt_final_ms) AS stt_p50,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY t.stt_final_ms) AS stt_p95,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY t.llm_ttft_ms)  AS ttft_p50,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY t.llm_ttft_ms)  AS ttft_p95,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY t.tts_ttfb_ms)  AS ttfb_p50,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY t.tts_ttfb_ms)  AS ttfb_p95
FROM turn_timings t
JOIN calls c USING (call_id)
GROUP BY c.provider_combo;
```

The stages don't add up to the turn latency. In row c1/1, 180 + 350 + 120 = 650 ms, but the turn took 760 ms, because the turn-end wait and sentence grouping before TTS also take time. All these timestamps are taken on Dograh's server, so the caller hears an extra delay from the carrier network.

### Layer 2: Turn-level / conversational dynamics
- **Turn latency**: end of user speech -> first agent audio. Track P50/P95, not just the mean. One vendor targets P95 < 800ms.
  [Vendor] https://hamming.ai/resources/voice-agent-evaluation-metrics-guide
  Stage latencies are not purely additive, so measure end to end.
  [Vendor] https://telnyx.com/resources/voice-ai-agents-compared-latency

  **Dataset**: `turn_timings` (Layer 1), column `turn_latency_ms`.

  **How to calculate.** Keep tool turns separate, because they are expected to be slower:

  ```sql
  SELECT c.provider_combo, t.had_tool_call,
         percentile_cont(0.5)  WITHIN GROUP (ORDER BY t.turn_latency_ms) AS p50,
         percentile_cont(0.95) WITHIN GROUP (ORDER BY t.turn_latency_ms) AS p95,
         COUNT(*) AS n
  FROM turn_timings t
  JOIN calls c USING (call_id)
  GROUP BY c.provider_combo, t.had_tool_call;
  -- example rows, non-tool turns: 760, 790, 930 → P50 = 790 ms
  ```

  Percentiles need hundreds of turns per group to be stable. Four example rows only show the shape of the query.

- **Turn-taking**: pause handling, backchannels, barge-in/interruption handling, false interruptions.
  Benchmark: Full-Duplex-Bench (below).

  **Dataset `turn_taking_events`**: one row per moment where someone could take the turn. A script finds candidate moments from silences and overlapping speech in the two tracks, and a human labels what kind of moment each one is.

  | Column | Type | Filled by | Notes |
  |---|---|---|---|
  | event_id | text | computed | |
  | call_id | text | auto | |
  | event_type | user_pause / user_backchannel / user_barge_in / smooth_turn_end | label | |
  | event_start_ts, event_end_ts | timestamptz (ms) | computed | |
  | agent_speaking | bool | auto | was the agent talking when it happened |
  | agent_took_turn | bool | computed | "TO" in Full-Duplex-Bench: the agent started a real reply |
  | agent_stopped | bool | computed | the agent stopped talking (for events while it spoke) |
  | reaction_ms | int, nullable | computed | time until the agent started or stopped |

  | event_id | event_type | agent_speaking | agent_took_turn | agent_stopped | reaction_ms | good? |
  |---|---|---|---|---|---|---|
  | e1 | user_pause | false | false | | | yes, it waited |
  | e2 | user_pause | false | true | | 600 | no, cut the caller off |
  | e3 | user_backchannel | true | false | true | 350 | no, false interruption |
  | e4 | user_barge_in | true | true | true | 320 | yes, it stopped and answered |
  | e5 | smooth_turn_end | false | true | | 780 | yes |

  **How to calculate.** TOR (takeover rate) = the mean of `agent_took_turn`, per event type (the Full-Duplex-Bench v1 definition). It should be low for pauses and high for barge-ins and turn ends:

  ```sql
  SELECT event_type,
         AVG(agent_took_turn::int) AS tor,
         AVG(agent_stopped::int)   AS stop_rate,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY reaction_ms) AS reaction_p50,
         COUNT(*) AS n
  FROM turn_taking_events
  GROUP BY event_type;
  -- example rows: user_pause TOR 0.5 (want low)
  --               user_backchannel stop_rate 1.0 (= false-interruption rate, want low)
  --               user_barge_in TOR 1.0, smooth_turn_end TOR 1.0 (want high)
  ```

  Full-Duplex-Bench's backchannel timing score (JSD) doesn't apply here, because a cascade agent like Dograh never says "mm-hm" itself.

### Layer 3: End-to-end simulated conversations
- A simulated caller (LLM + TTS with a persona and goal) talks to your agent over real audio.
- Score with: task completion (check final DB/tool state, not just the transcript), policy adherence, faithfulness, conciseness, and turn-taking.
- **Run each scenario k times**: report pass@1 AND pass^k (all k succeed). EVA-Bench found a median pass@k - pass^k gap of 0.44, so a single run is very misleading.
  [V] https://arxiv.org/abs/2605.13841

  How the scores are defined (k runs of the same scenario):
  - **pass@1**: the success rate of a single run (averaged over runs).
  - **pass@k**: the share of scenarios where *at least one* of the k runs succeeds. This is "peak" capability.
  - **pass^k**: the share of scenarios where *all* k runs succeed. This is "reliable" capability.

  Example with k = 4, where a scenario succeeds in 3 of 4 runs: pass@k counts it as a success, and pass^k counts it as a failure. A large pass@k - pass^k gap means the agent can do the task but does it inconsistently.
- Validate the simulator itself. EVA regenerates conversations where the simulated user went off-script, so the scores reflect the agent and not simulator errors.
- Reference implementation: **ServiceNow EVA** (MIT, Pipecat-based, cascade + speech-to-speech).
  [V] https://github.com/ServiceNow/eva

Production calls can't be replayed, so the scores in this layer need scenarios. Write them from real calls: a failed production call is the best seed for a new scenario.

**Dataset `scenarios`**: one row per scenario. The column names copy τ²-bench's task format, and the content follows EVA (goal with a decision tree, persona, scenario database, ground-truth database).

| Column | Type | Filled by | Notes |
|---|---|---|---|
| scenario_id | text | label | |
| source_call_id | text, nullable | label | the production call it was written from |
| persona | text | label | speaking style, patience |
| reason_for_call | text | label | τ²-bench `user_scenario.instructions.reason_for_call` |
| known_info | text | label | e.g. "You are Priya. Your booking ID is DJ3LPO." |
| task_instructions | text | label | the decision tree: "if the agent offers 11:00, refuse and ask for 10:00" |
| initial_state | jsonb | label | the scenario database before the call |
| expected_end_state | jsonb | label | the ground-truth database after a correct call |
| nl_assertions | text[] | label | τ²-bench style rules, e.g. "Agent must not promise a refund" |
| perturbation | jsonb | label | e.g. {"noise": "MUSAN", "snr_db": 10, "accent": "south"} |

Expected tool calls go in `expected_tool_calls` (Layer 1). Copy the scenario's rows to each trial's `call_id`, and copy `expected_end_state` into that trial's `task_results` row.

**Dataset `scenario_trials`**: one row per scenario × run.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| scenario_id | text | | |
| trial_index | int | computed | 1 to k |
| call_id | text | auto | the simulated call, so every Layer 1-2 table works on it |
| seed | int | computed | fixes noise and simulator randomness |
| agent_config_hash | text | computed | workflow version + models, so runs can be compared |
| simulator_valid | bool | judge | did the simulated caller stay on script (EVA). If false, rerun it |
| pass_accuracy | bool | computed | see below |
| pass_experience | bool | computed | see below |

EVA's pass rules, which you can copy:
- `pass_accuracy` = `task_results.end_state_match` AND faithfulness ≥ 0.5 AND speech fidelity ≥ 0.95 (Layer 4).
- `pass_experience` = turn-taking ≥ 0.8 AND progression ≥ 0.5 AND conciseness ≥ 0.5 (`experience_scores` below). EVA's turn-taking score is its own timestamp formula; a simple stand-in is the share of correct rows in `turn_taking_events`.

| scenario_id | trial_index | simulator_valid | pass_accuracy |
|---|---|---|---|
| s1 | 1 | true | true |
| s1 | 2 | true | true |
| s1 | 3 | true | false |
| s1 | 4 | true | true |
| s2 | 1-4 | true | true, true, true, true |
| s3 | 1-4 | true | false, false, true, false |

**How to calculate.**

```sql
WITH per_scenario AS (
  SELECT scenario_id,
         AVG(pass_accuracy::int) AS pass_rate,
         bool_or(pass_accuracy)  AS any_pass,
         bool_and(pass_accuracy) AS all_pass
  FROM scenario_trials
  WHERE simulator_valid
  GROUP BY scenario_id
)
SELECT AVG(pass_rate)      AS pass_at_1,
       AVG(any_pass::int)  AS pass_at_k,
       AVG(all_pass::int)  AS pass_hat_k
FROM per_scenario;
-- example rows: pass@1 = (0.75 + 1 + 0.25) / 3 = 0.67
--               pass@k = 3 / 3 = 1.0, pass^k = 1 / 3 = 0.33  → gap 0.67
```

Rerun invalid trials until every scenario has k valid ones, or the scenarios end up with different k.

**Dataset `policy_checks`**: one row per call × rule from `scenarios.nl_assertions`. It also works on production calls, with rules taken from the workflow's policy.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | | |
| assertion_id | text | label | |
| assertion_text | text | label | |
| verdict | pass / fail / not_applicable | judge | not_applicable = the situation never came up |
| evidence_turn_ids | int[] | judge | |
| judged_by | text | | judge model + prompt version, or "human" |

| call_id | assertion_text | verdict |
|---|---|---|
| c1 | Agent must not promise a refund | pass |
| c1 | Agent must confirm the date before booking | fail |
| c2 | Agent must not promise a refund | not_applicable |

**How to calculate.** Leave out not_applicable rows, or calls where the rule never came up make the agent look better than it is:

```sql
SELECT assertion_text,
       AVG((verdict = 'pass')::int) AS adherence,
       COUNT(*) AS n
FROM policy_checks
WHERE verdict <> 'not_applicable'
GROUP BY assertion_text;
```

**Dataset `experience_scores`**: one row per call, for conciseness and conversation progression (EVA-X).

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id | text | | |
| conciseness | float 0-1 | judge | are replies short enough for a phone call |
| progression | float 0-1 | judge | does the call keep moving towards the goal |
| issues | text[] | judge | repeated_question, lost_context, stalling, loop |
| judged_by | text | | |

| call_id | conciseness | progression | issues |
|---|---|---|---|
| c1 | 0.8 | 0.9 | {} |
| c2 | 0.4 | 0.3 | {repeated_question, stalling} |

**How to calculate.**

```sql
SELECT AVG(conciseness) AS conciseness,
       AVG(progression) AS progression,
       AVG((conciseness >= 0.5 AND progression >= 0.5)::int) AS share_passing
FROM experience_scores;
-- example rows: 0.6, 0.6, share passing 0.5
```

### Layer 4: Judges
- An LLM-as-judge on the transcript for semantics (faithfulness, policy).
- An audio-LLM judge for what was actually spoken (EVA's "Agent Speech Fidelity", in beta). This catches TTS mispronouncing numbers or entities.
- Calibrate any judge against a human-labelled sample before trusting it.

**Dataset `speech_fidelity_entities`**: one row per entity the agent said out loud.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| call_id, turn_id | text, int | | |
| entity_type | text | judge or label | phone, date, amount, id_code, name, address |
| intended_value | text | auto | taken from `turns.agent_text`, i.e. what TTS was told to say |
| spoken_correctly | bool | judge | an audio-LLM listens to the clip from `bot.wav`, or a human does |
| judged_by | text | | |

| call_id | turn_id | entity_type | intended_value | spoken_correctly |
|---|---|---|---|---|
| c1 | 3 | date | 20 November | true |
| c1 | 3 | phone | 98200 11223 | false (said "...11233") |
| c1 | 5 | amount | ₹1,500 | true |

**How to calculate.** EVA requires a fidelity of at least 0.95 per conversation:

```sql
SELECT call_id,
       AVG(spoken_correctly::int) AS speech_fidelity,
       AVG(spoken_correctly::int) >= 0.95 AS passes
FROM speech_fidelity_entities
GROUP BY call_id;
-- example rows: c1 = 2/3 = 0.67, fails
```

**Dataset `judge_calibration`**: one row per item × human annotator. The items are a random sample of rows from `faithfulness_claims`, `policy_checks`, `experience_scores` or `speech_fidelity_entities`.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| item_table | text | | which table the item came from |
| item_id | text | | |
| judge_verdict | text | judge | |
| annotator_id | text | label | |
| human_verdict | text | label | the human labels without seeing the judge's answer |

**How to calculate.** Cohen's kappa measures agreement after removing the agreement you would get by chance: `κ = (p_o − p_e) / (1 − p_e)`, where `p_o` is the share of items where judge and human agree, and `p_e` is the agreement expected by chance.

Example: 10 policy checks. Judge and human both say pass on 5 and both say fail on 3, so `p_o = 0.8`. Each of them says pass 6 times out of 10, so `p_e = 0.6 × 0.6 + 0.4 × 0.4 = 0.52`. `κ = (0.8 − 0.52) / 0.48 = 0.58`. EVA's judges reached 0.78-0.85 against humans, so a 0.58 judge needs a better prompt or a stronger model.

```python
from sklearn.metrics import cohen_kappa_score
rows = df[df.item_table == "policy_checks"]
kappa = cohen_kappa_score(rows.human_verdict, rows.judge_verdict)
```

Measure human-to-human kappa on the same items too. A judge can't be expected to agree with humans more than humans agree with each other.

### Layer 5: CI regression + production monitoring
- Run the scenario suite on every prompt/model/provider change and diff it against a stored baseline.
  [Vendor] https://hamming.ai/resources/voice-agent-testing-guide
- In production: sample real calls, rescore them with the same judges, and track latency percentiles and task-success drift.
  Feed failures back into the Layer 0 test set.

**Dataset `metric_snapshots`**: one row per metric per evaluation run. Every query above writes its result here.

| Column | Type | Filled by | Notes |
|---|---|---|---|
| snapshot_id | text | computed | |
| agent_config_hash | text | computed | same as in `scenario_trials` |
| metric_name | text | computed | e.g. wer, pass_hat_k, turn_latency_p95 |
| value | float | computed | |
| n | int | computed | rows the value is based on |
| computed_at | timestamptz | computed | |
| is_baseline | bool | | the version currently in production |

| agent_config_hash | metric_name | value | n | is_baseline |
|---|---|---|---|---|
| cfg_a | pass_hat_k | 0.62 | 40 | true |
| cfg_b | pass_hat_k | 0.55 | 40 | false |
| cfg_a | turn_latency_p95 | 1180 | 2300 | true |
| cfg_b | turn_latency_p95 | 1090 | 2250 | false |

**How to calculate.** For a CI regression check, compare the new config with the baseline and fail the build when a metric moves past its tolerance:

```sql
SELECT cur.metric_name,
       base.value AS baseline,
       cur.value  AS candidate,
       cur.value - base.value AS delta
FROM metric_snapshots cur
JOIN metric_snapshots base
  ON base.metric_name = cur.metric_name AND base.is_baseline
WHERE cur.agent_config_hash = 'cfg_b';
-- example rows: pass^k −0.07 (worse), turn latency P95 −90 ms (better)
```

For production drift, compute the same metrics every week from sampled production calls. Latency is per turn and task success is per call, so compute them separately before joining:

```sql
WITH latency AS (
  SELECT date_trunc('week', c.started_at) AS week,
         percentile_cont(0.95) WITHIN GROUP (ORDER BY t.turn_latency_ms) AS turn_latency_p95
  FROM calls c JOIN turn_timings t USING (call_id)
  GROUP BY 1
), success AS (
  SELECT date_trunc('week', c.started_at) AS week,
         AVG(r.end_state_match::int) AS task_success
  FROM calls c JOIN task_results r USING (call_id)
  WHERE r.run_type = 'production'
  GROUP BY 1
)
SELECT week, turn_latency_p95, task_success
FROM latency FULL JOIN success USING (week)
ORDER BY week;
```

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

## 2a. Benchmark deep dives (how each one works)

Each entry follows the same layout: what it does, the steps/algorithm, how it is scored, pros, cons, and when to use it.
The details come from the paper's method section or the repo README unless marked otherwise.

### τ-Voice (Sierra / Princeton, ICML 2026)
**What it does.** It takes the text customer-service tasks from τ²-bench (Retail, Airline, Telecom) and runs them as live full-duplex voice calls. This lets you compare the *same task* in text vs. voice.

**Steps / algorithm**
1. **Load a task** from τ²-bench: the user instructions, the agent's domain policy, the tools, a database, and the expected final database state.
2. **Tick-based orchestrator.** The audio stream is cut into fixed ticks (200 ms by default). In each tick, both sides exchange exactly 200 ms of audio, so both can talk at once (full-duplex). On an interruption, the agent's buffered audio is dropped.
   Voice APIs index on *audio time*, not wall-clock time. So simulation time can run slower than real time, and the user simulator can use a slow, strong LLM.
3. **Voice user simulator**, run on every tick:
   - An LLM writes the user's next words, including fillers ("um") and spoken forms of symbols ("at" instead of "@").
   - TTS speaks them with one of 7 personas (accent, style).
   - An audio environment is mixed in: background noise (chatter, traffic), bursts (phone rings, dog barks), coughs and "hold on", muffling, G.711 μ-law compression at 8 kHz, and packet loss (Gilbert-Elliott model).
   - The turn-taking policy is: wait for silence (default 1 s) before speaking. While the agent talks, an LLM periodically decides whether to interrupt. A separate LLM decides whether to backchannel ("mm-hmm"). The simulator yields after a set overlap when the agent interrupts it.
   - The simulator reads the agent's *transcript* directly, so its own ASR errors don't contaminate the score.
4. **The agent** (OpenAI Realtime, Gemini Live, or xAI Grok) streams audio back and calls tools against the database.
5. **Score.** Compare the final database state to the expected state (pass/fail), and log turn-taking events.
6. **Compare conditions.** "Clean" means clean audio and no interruptions. "Realistic" means noise, accents and turn-taking. Both are compared against a text-only baseline.

**Metrics.** Task completion pass@1 (database-state check). Voice interaction quality: latency, responsiveness (does the agent reply when it should), selectivity (does it stay quiet when it should), and interrupt rate.

**Headline result.** GPT-5 (reasoning, text) scores 85%. Voice agents score 31-51% clean and 26-38% realistic. Accents hurt most, but the effect depends heavily on the provider.

**Pros**
- Task success is verifiable (database state), not judged by an LLM.
- Direct text vs. voice comparison on identical tasks.
- Reproducible: a seed fixes all audio and environment randomness. Every factor (noise SNR, interruption timing, accent) can be switched on its own for ablations.
- Telephony-realistic audio (8 kHz μ-law, packet loss), which is close to our phone use case.
- Open code in `sierra-research/tau2-bench`.

**Cons**
- Built around speech-to-speech realtime APIs (provider adapters). A cascade/Pipecat agent like ours needs a custom adapter.
- The tick-based, slowed-down time is not real wall-clock latency. Latency numbers are not production numbers.
- The user is synthetic (LLM + TTS). EVA's authors note that τ-Voice changes accent *and* persona together, so the accent effect is confounded with persona.
- Only three domains, all customer service. English only.

**When to use.** To measure how much our agent loses going from text to voice on policy-heavy support tasks, and which audio factor hurts most.

### EVA-Bench / ServiceNow EVA (EMNLP 2026)
**What it does.** It runs full multi-turn bot-to-bot phone conversations against your voice agent, validates that the simulated caller behaved correctly, then scores both *accuracy* and *experience*.

**Steps / algorithm**
1. **Scenario design.** Each of the 213 scenarios (Airline CSM, Healthcare HRSD, ITSM) has:
   - a user goal with explicit constraints (e.g. "depart before 10pm, fare below $X");
   - a decision tree that fixes the user's choices, so runs are repeatable;
   - a persona (speaking style, patience);
   - a scenario database;
   - the ground-truth final database state.
   Scenarios deliberately include hard spoken entities: confirmation codes, names, IDs.
   They span single-intent, multi-intent (1-4 workflows) and adversarial calls (e.g. pressure to grant compensation the caller is not eligible for).
2. **Bot-to-bot call.** The user simulator (ElevenLabs Agents cascade by default; OpenAI Realtime is in beta) talks to the agent under test over a live audio WebSocket. The agent is Pipecat-based and can be a cascade or speech-to-speech.
3. **Tool Executor.** Agent tool calls run against the per-scenario database through deterministic Python functions, so the same call always gives the same result.
4. **Simulator validation (the key step).** After the call, two checks run before any scoring:
   - User Behavioral Fidelity: an LLM judge checks whether the simulator stuck to its goal.
   - User Speech Fidelity: an audio-LLM judge checks whether the simulator's audio said what it intended.
   If either check fails, the conversation is regenerated. About 12% of trials needed regeneration, almost all due to user behaviour drift.
5. **Score each conversation** (see metrics below).
6. **Repeat k = 5 times per scenario**, and compute pass@1, pass@k and pass^k.
7. **Optional perturbations**, each one independently controlled: accent, background noise, connection degradation, and caller behaviour.

**Metrics and pass rules**
- **EVA-A (Accuracy)**
  - Task Completion: the SHA-256 hash of the final database must equal the hash of the expected database. That means exactly the right changes, no extras.
  - Faithfulness: an LLM judge checks that answers are grounded in policy, tool results and user input.
  - Speech Fidelity: an audio-LLM judge checks that the agent's *spoken audio* says the right entities (codes, dates, amounts).
  - A conversation passes accuracy if Task = 1.0 AND Faithfulness ≥ 0.5 AND Speech Fidelity ≥ 0.95.
- **EVA-X (Experience)**
  - Turn-Taking: deterministic, based on timestamps. It penalizes interruptions, long silences and slow yields, and gives tool-call turns more time.
  - Conciseness: an LLM judge checks whether responses are short enough for a phone call.
  - Conversation Progression: an LLM judge checks for repeated questions, lost context and stalling.
  - A conversation passes experience if Turn-Taking ≥ 0.8 AND Progression ≥ 0.5 AND Conciseness ≥ 0.5.
- **Diagnostics** (not part of the score). For example, Transcription Accuracy (Key Entities): a confirmation code that is off by one character barely moves WER, but it breaks the task.
- **Judge quality.** Judges were checked against human annotators. Agreement (κ) was 0.78-0.85, at or above human-human agreement.

**Headline results.** No system scored above 0.5 on both EVA-A and EVA-X pass@1. The median pass@k - pass^k gap was 0.44 (EVA-A). Cascade systems lose on turn-taking (latency) and degrade more under accents. Key-entity transcription accuracy correlated r = 0.93 with task completion for cascade systems.

**Pros**
- **Pipecat-based**, the same framework Dograh uses, so it is the closest fit to our stack. MIT license.
- Works for both cascade and speech-to-speech, scored on equal footing.
- Simulator validation and regeneration mean low scores reflect the agent, not a broken simulator.
- pass^k exposes inconsistency that a single run hides.
- Measures what was *spoken* (Speech Fidelity), not just the transcript.
- Built-in Streamlit apps for config and result analysis. You can add languages and domains.

**Cons**
- Expensive: k = 5 trials × 213 scenarios, plus several commercial APIs (ElevenLabs simulator, GPT-5.2, Gemini and Claude judges).
- English only by default. The robustness tests used only one accent (French) and one noise type (coffee shop).
- The simulator does not systematically interrupt, so barge-in handling is under-tested.
- Task Completion is all-or-nothing, with no partial credit.
- Mock tools, so no real API latency or failures.
- Audio-LLM judges are new, and judges may favour their own model family.

**When to use.** As our main end-to-end regression suite. We can port our own workflows in as new domains/scenarios, and run it in CI on prompt, model or provider changes.

### Full-Duplex-Bench v3 (NTU / NVIDIA, 2026)
**What it does.** It tests whether a voice agent picks the right tools with the right arguments when the user speaks *naturally and messily*. The classic example: "Book me a flight um… to New York, actually wait… make that Boston."

**Steps / algorithm**
1. **Mock APIs** in 4 domains: Travel & Identity, Finance & Billing, Housing & Location, E-Commerce Support. They run locally, are deterministic and have zero latency, so all measured latency belongs to the model.
2. **Scenarios** in 3 difficulty tiers: Easy (1 tool call), Medium (2 calls, some ambiguity), Hard (multiple calls with conflicting constraints).
3. **Real human recordings**: 100 recordings from 12 speakers (native and non-native English, including Korean and Russian accents), recorded on everyday laptop and phone mics in real rooms. The trailing silence is the speaker's real room tone, not digital silence.
4. **Disfluency labels** on every recording: fillers, pauses, hesitations, false starts, self-corrections. 21 scenarios contain a self-correction.
5. **Stream** the audio into each model through the LiveKit realtime agent framework, and log tool calls and speech with timestamps.
6. **Score** with the metrics below.

**Metrics**
- **Tool Selection F1**: compares the expected tool calls with the actual ones. Missed calls lower recall. Invented calls lower precision.
- **Argument Accuracy**: a GPT-4o judge checks argument values, allowing harmless variations (date formats, abbreviations).
- **Pass@1**: passes only if exactly the expected tools are called AND every argument is correct.
- **Response Quality**: a GPT-4o judge checks whether the spoken reply actually tells the user the result.
- **Latency**: Δt = agent speech start - user speech end. If Δt < 0, it counts as an interruption. Latency is split into first response (including filler like "let me check"), first tool call, and the real answer.
- **Turn-take rate**: the share of turns with a timely reply.
- **Filler rate**: the share of turns where the agent says filler before the real content.

**Headline results.** GPT-Realtime had the best Pass@1 (0.600). The cascade (Whisper → GPT-4o → TTS) scored 0.450 and was slowest (10.12 s). On self-corrections, the cascade scored only 0.176, because Whisper finalizes the wrong words before the correction arrives. Pauses were the hardest category for end-of-turn detection.

Example (`travel_19`): the user corrects the destination (Rome → Milan) and the date (June 1 → June 3) in one utterance. Only GPT-Realtime booked Milan on June 3. Gemini Live 3.1 called the tool 2.27 s *before* the user finished, which locked in "Rome". The cascade also used "Rome", because the STT had already finalized it. Fast, early tool calls help on clean requests but break state rollback.

**Pros**
- 100% real human audio with real mics and rooms. Most other benchmarks use TTS.
- Directly tests self-corrections and false starts, which is the main cascade weakness (state rollback).
- Latency is split into parts (filler vs. tool call vs. answer), so you can see *where* time goes.
- Deterministic mock APIs give clean, automatic scoring.

**Cons**
- Small: only 100 recordings from 12 speakers. Per-category numbers rest on few samples.
- Single-turn per scenario (per the EVA paper), not a full multi-turn conversation.
- Argument Accuracy and Response Quality depend on a GPT-4o judge.
- The harness is LiveKit, not Pipecat, so we would need to adapt it.

**When to use.** As a focused robustness test for our STT plus end-of-turn detection on disfluent speech, especially self-corrections.

### Full-Duplex-Bench v1 / v1.5 / v2 (NTU)
**What it does.** It tests *conversational timing behaviour*: does the agent wait, backchannel, take the turn and handle interruptions like a human would? It does not test tasks or tools.

**Steps / algorithm (v1)**
1. **Prepare `input.wav`** for each test, from real dialogue data (Candor, ICC) or synthetic audio:

   | Test | Samples |
   |---|---|
   | Pause handling (Candor) | 216 |
   | Pause handling (synthetic) | 137 |
   | Smooth turn-taking (Candor) | 119 |
   | Backchannel (ICC) | 55 |
   | User interruption (synthetic) | 200 |
2. **Stream** the input to the model and record its reply as `output.wav`.
3. **Transcribe** the output with time-aligned ASR (`nvidia/parakeet-tdt-0.6b-v2`), giving word-level timestamps.
4. **Classify each model segment** as silence, backchannel (< 1 s and < 2 words) or takeover (anything else).
5. **Compute** the per-dimension metrics below.

**Metrics (v1)**
- **TO (Takeover)** = 1 if the model takes the turn, and 0 if it stays silent or only backchannels. **TOR (Takeover Rate)** = (1/N) Σ TOᵢ, the average over N samples.
- **Pause handling**: TOR should be *low*, because the user is only pausing.
- **Backchannel**:
  - TOR should be low.
  - Frequency is backchannels per second.
  - JSD (Jensen-Shannon Divergence) compares the timing of the model's backchannels (distribution P) with human timing (distribution Q):

    `JSD = ½ Σ P(i) log(P(i)/M(i)) + ½ Σ Q(i) log(Q(i)/M(i))`, where `M = ½(P + Q)` and i is a time window.

    JSD = 0 means the same timing as humans. JSD = 1 means completely different timing.
- **Smooth turn-taking**: TOR should be *high*, and latency (user end → model start) should be low.
- **User interruption**: TOR should be high (the model should respond to the interruption). A GPT-4o score (0-5) rates relevance and coherence, plus latency after the interruption.

**v1.5** adds overlap cases: the user backchannels while the agent talks, a side conversation, and ambient speech. These test whether the agent wrongly stops talking.
**v2** is live and multi-turn. An automated LLM "examiner" talks to the model over WebRTC/WebSocket across four task families (daily, correction, entity tracking, safety), and an LLM judge scores it.

**Pros**
- Precise, mostly automatic timing metrics (TOR, JSD, latency), with no human raters.
- v1 includes real human dialogue audio (Candor, ICC).
- Isolates turn-taking from task logic. Useful to tune our VAD and end-of-turn settings.
- Open code and data. Actively maintained (v1 → v3).

**Cons**
- No tools or tasks (v1, v1.5). It says nothing about whether the agent gets the job done.
- The authors say the metrics are not linked to human preference. You decide what "good" TOR or backchannel frequency is.
- English only. Small sample counts per dimension.
- Designed for full-duplex speech-to-speech models. A half-duplex cascade will score poorly on backchanneling by design.
- The interruption score relies on GPT-4o.

**When to use.** When tuning VAD, end-of-turn detection and barge-in handling. Run v1 pause handling and interruption before and after a change.



### VoiceBench (TACL 2026)
**What it does.** It tests whether a voice assistant understands and answers *spoken* questions as well as it answers typed ones, across knowledge, instruction following, reasoning and safety.

**Steps / algorithm**
1. **Load a subset** from Hugging Face (`hlt-lab/voicebench`). Each subset is a text benchmark turned into audio, either with Google TTS or with human recordings:

   | Subset | Samples | Audio | Task |
   |---|---|---|---|
   | alpacaeval_full | 636 | TTS | open-ended QA |
   | commoneval | 200 | human | open-ended QA |
   | wildvoice | 1,000 | human, diverse accents | open-ended QA |
   | sd-qa | 553 | human, per region | reference-based QA |
   | openbookqa | 455 | TTS | multiple choice |
   | mmsu | 3,074 | TTS | multiple choice |
   | mtbench | 46 | TTS | multi-turn |
   | ifeval | 345 | TTS | instruction following |
   | bbh | 1,000 | human | reasoning |
   | advbench | 520 | TTS | safety (should refuse) |
2. **Generate responses**: `python main.py --model <m> --data <subset> --split test --modality audio`. Run it again with `--modality text` to get the text baseline.
3. **Judge**:
   - Open-ended subsets (alpacaeval, commoneval, wildvoice, sd-qa) are scored by gpt-4o-mini (`api_judge.py`).
   - The other subsets are scored by rules: MCQ answer match, IFEval rule checks, refusal detection for advbench, and BBH answer match.
4. **Aggregate** with `evaluate.py --evaluator open|qa|ifeval|harm|mcq|bbh`. Compare audio vs. text scores. The gap is what speech costs you.

**Pros**
- Broad coverage in one harness. Includes human speech with accents and regional variants (sd-qa).
- Text vs. audio mode on the same items isolates the speech penalty.
- A public leaderboard to compare against.

**Cons**
- Single-turn Q&A (mtbench is only 46 items). No tools, no tasks, no turn-taking.
- Most subsets are TTS audio, which is cleaner than real calls.
- The open-ended scores depend on a gpt-4o-mini judge.
- Tests general assistant skill, not our domain.

**When to use.** A quick sanity check when choosing an STT + LLM combo or a speech-to-speech model. Not a substitute for scenario tests.

### Big Bench Audio (Artificial Analysis)
**What it does.** It tests audio *reasoning*. Do models think as well when the question is spoken?

**Steps / algorithm**
1. Take 4 Big Bench Hard categories, 250 questions each: formal fallacies, navigate, object counting, web of lies.
   They chose categories that do not depend on symbols or spelling (which can't be heard), and where humans average > 80% in text.
2. Append ". Answer the question" to each question, so TTS fully pronounces the final answer option.
3. Synthesize with a random one of 23 voices (OpenAI, Azure, AWS Polly).
4. **Quality check.** Transcribe each audio file and compute a normalized Levenshtein similarity to the source text. Manually review files below 0.85 (35 flagged, 0 actually wrong).
5. Feed the audio to the model and compare its answer with `official_answer`.

**Pros**
- Clean, objective answers (exact match), so no judge is needed.
- Good for comparing speech-to-speech vs. cascade reasoning loss. MIT license.

**Cons**
- Synthetic voices, English only, mostly US/UK accents.
- Puzzle-style reasoning, unlike real calls.
- Single-turn, no tools.

**When to use.** Only to check that an audio-native model doesn't lose reasoning ability vs. its text version.

### SLURP (EMNLP 2020)
**What it does.** It tests spoken language understanding (SLU): from a short voice command, get the *intent* (e.g. `alarm_set`) and the *entities* (e.g. `time = eight`).

**Steps / algorithm**
1. Get the text annotations from the repo (`dataset/slurp/`) and the audio with `scripts/download_audio.sh` (about 6 GB, FLAC). Audio includes close-talk (`-headset`) and distant-mic versions of the same utterance.
2. Each record contains:
   - the sentence;
   - an annotated sentence (`wake me up at [time : eight] o'clock`);
   - `scenario`, `action` and `intent`;
   - the entity spans;
   - the recordings, each with automatic `wer` / `ent_wer` fields.
   The metadata encodes the speaker's gender and whether they are a native English speaker.
3. Run audio → your STT + NLU (or an end-to-end SLU model) → predict the intent and entities.
4. Score:
   - intent accuracy;
   - entity tagging with SLU-F1, the paper's metric. It gives partial credit when the entity text is close but not exact, so ASR spelling slips aren't counted as total misses. (Not confirmed against the paper text; check it for the exact formula.)

**Pros**
- Large, real human recordings across 18 domains. Near-field and far-field mics.
- A mature baseline. Recipes exist in SpeechBrain and ESPnet. The MASSIVE dataset extends the text to 50 languages.

**Cons**
- Home-assistant commands ("set an alarm"), not phone conversations.
- Single utterance, no dialogue.
- The audio is CC BY-NC 4.0 (non-commercial). Check the license before any commercial use.
- Dated (2020). Good for intent/entity extraction only.

**When to use.** To test intent and entity extraction from noisy speech in isolation, e.g. when tuning an extraction step.

### Open ASR Leaderboard (Hugging Face)
**What it does.** A standard, reproducible WER + speed comparison of 86 STT systems.

**Steps / algorithm**
1. Pick the datasets:
   - English short-form main sets: LibriSpeech, GigaSpeech, VoxPopuli, TED-LIUM, SPGISpeech, AMI, Earnings22.
   - English long-form: Earnings21/22, CORAAL.
   - Multilingual: FLEURS, MCV, MLS.
2. Run each model through its family's `run_eval.py` in a fixed Docker image on fixed hardware (HF Jobs, H200).
3. **Normalize** predictions and references with the repo's text normalizer, then compute WER per dataset.
4. Measure RTFx = audio seconds / processing seconds.
5. Plot WER vs. RTFx (a Pareto frontier) and model size.
6. After a submission, the maintainers also score on private sets, to detect models overfitted to the public test sets.

**Pros**
- The de facto reference for STT accuracy and speed. Same normalizer and hardware for everyone.
- Long-form and multilingual tracks. The private sets reduce benchmark gaming.

**Cons**
- Mostly read or prepared speech, not 8 kHz phone calls with noise.
- WER treats every word equally. A wrong digit in a confirmation code counts the same as a wrong "the". EVA showed key-entity accuracy predicts task success much better.
- API (cloud STT) models are evaluated separately. Real-time streaming latency is not measured; RTFx is batch speed.

**When to use.** To shortlist STT models, then re-run WER and entity accuracy on *our own* call audio before picking one.

### Seed-TTS-eval (ByteDance)
**What it does.** Objective test sets plus scripts to score zero-shot TTS and voice cloning on intelligibility and speaker similarity.

**Steps / algorithm**
1. Download the test set. Each line of a meta file is: `filename | prompt text | prompt audio | text to synthesize | ground-truth audio (if any)`.
   - EN: 1,000 samples from Common Voice (`en/meta.lst`).
   - ZH: 2,000 samples from DiDiSpeech-2 (`zh/meta.lst`).
   - ZH hard cases: tongue twisters and repetitions (`zh/hardcase.lst`).
   - Voice conversion lists (`*_non_para_reconstruct_meta.lst`).
2. For each line, synthesize "text to synthesize" in the voice of the "prompt audio".
3. **WER**: `bash cal_wer.sh <meta> <wav_dir> en|zh`. This transcribes with Whisper-large-v3 (EN) or Paraformer-zh (ZH) and computes WER against the input text.
4. **SIM**: `bash cal_sim.sh <meta> <wav_dir> <wavlm_large_finetune.pth>`. This takes WavLM-large speaker embeddings of the output and the prompt, and computes their cosine similarity.

**Pros**
- A widely used standard. Most TTS papers report these numbers, so results are comparable.
- Simple, objective, scriptable.

**Cons**
- No naturalness score. Add UTMOS or NISQA yourself.
- Intelligibility WER depends on the ASR model's own errors.
- Read-style sentences. It does not test numbers, codes, addresses or phone-style prosody, which is what breaks in our calls.
- Only EN and ZH.

**When to use.** When comparing TTS providers or a cloned voice. Add our own test lines with phone numbers, dates and IDs.

### MUSAN and Microsoft DNS Challenge (noise sources)
**What they do.** They are not benchmarks. They are libraries of noise you mix into clean test audio, to measure how much your scores drop.

**Steps / algorithm (noise augmentation)**
1. Pick clean speech `s` (your test call audio) and a noise clip `n` (MUSAN noise/music/babble, or DNS noise categories).
2. Choose a target SNR (signal-to-noise ratio), e.g. 20, 10, 5 or 0 dB. A lower SNR means louder noise.
3. Scale the noise: `n' = n × sqrt(P_s / (P_n × 10^(SNR/10)))`, where P_s and P_n are the mean powers (mean of squared samples) of the speech and the noise.
4. Mix: `x = s + n'`. Optionally add reverberation (DNS ships room impulse responses) and 8 kHz μ-law conversion to simulate phone audio.
5. Re-run your eval (WER, task completion) on `x`, and report the drop vs. clean at each SNR.

```python
import numpy as np
def mix_at_snr(speech, noise, snr_db):
    noise = np.resize(noise, speech.shape)              # loop/trim noise to speech length
    p_s, p_n = np.mean(speech**2), np.mean(noise**2)
    return speech + noise * np.sqrt(p_s / (p_n * 10 ** (snr_db / 10)))
```

| | MUSAN | DNS Challenge |
|---|---|---|
| Content | Music, speech in 12 languages, ~6 h of noise | ~180 h of noise in 150 categories, plus clean speech and room impulse responses |
| License | CC BY 4.0 | Check per-edition terms |
| Pros | Small, easy, a standard in speaker/ASR augmentation | Large and varied. Includes reverberation and a ready-made noisy-speech synthesizer script |
| Cons | Limited noise variety | Huge download. Several editions (DNS1-5) with different contents |

**When to use.** MUSAN for quick robustness checks. DNS when you need many noise types or reverberation.

### Picking a benchmark for Dograh

| Question you want answered | Use |
|---|---|
| Does our full agent finish real tasks reliably, run after run? | EVA-Bench (Pipecat, ports to our workflows) |
| How much do we lose going from text to voice? | τ-Voice |
| Does our STT + end-of-turn detection survive "um… actually, make that Boston"? | Full-Duplex-Bench v3 |
| Is our VAD / barge-in / pause handling tuned well? | Full-Duplex-Bench v1 / v1.5 |
| Which STT model should we shortlist? | Open ASR Leaderboard, then our own audio |
| Which TTS voice/provider? | Seed-TTS-eval + UTMOS + our own number/ID lines |
| Is a speech-to-speech model as smart as its text version? | VoiceBench, Big Bench Audio |
| Does intent/entity extraction survive noise? | SLURP + MUSAN/DNS mixed at several SNRs |

---

## 3. Open-source tooling seen
- ServiceNow EVA: simulated caller, Pipecat, MIT. [V] https://github.com/ServiceNow/eva
- VoiceAIStackEvaluation: compares STT/TTS/LLM combos on WER, latency and NISQA. Personal project. [S] https://github.com/MahsaPaknezhad/VoiceAIStackEvaluation
- Commercial (not verified here): Hamming, Coval, Cekura, Vapi/Retell built-in testing.

## 4. Caveats
- Latency/WER thresholds from Hamming and Telnyx are vendor rules of thumb and differ between sources. Calibrate on your own traffic.
- Third-party summaries of τ-Voice quote different numbers than the paper. Cite the ICML/arXiv abstract directly (figures above are from it).
- Most "agent" benchmarks are from 2026 and are moving fast. Check the repo before relying on dataset contents.
