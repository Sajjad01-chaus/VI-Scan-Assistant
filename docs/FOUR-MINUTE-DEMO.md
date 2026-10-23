# Four-minute demo script

This is a recording script, not a claim that a video has already been recorded. Target duration: 4:00. Provider/device latency varies; the time windows include short processing/playback pauses. Speak naturally and let short assistant audio finish rather than narrating over it.

## Before pressing Record

- Complete the silent core rehearsal in `FINAL-REHEARSAL.md`.
- Open the app in Live providers mode with New session and Find / ask selected. Verify the Build badge. Make text readable at your recording resolution and hide unrelated tabs/notifications/secrets.
- Enable Spoken replies initially. Use headphones and capture microphone plus system audio in the recorder. During narration, do not leave the app microphone listening. Say only the command while app capture is active, then stop/finish capture before continuing narration.
- Pre-open `docs/diagrams/system-architecture.png` in another tab/window. Keep the project README/test evidence available if asked; do not spend the four minutes browsing files.
- The core plan uses three microphone turns: retrieval, identity correction and clinical dictation. Allow automatic spoken replies for the initial retrieval/clarification and summary; then mute while demonstrating edits. Actual quota depends on providers/input lengths. Do not promise a fixed free budget.

## 0:00–0:20 — Introduce the working product

**Screen:** whole workspace, Live providers and synthetic-data label.

**Say to the reviewer:**

“This is my VI-SCAN clinical assistant proof of concept, using only synthetic patients and reports. It supports voice-based report retrieval, source-linked follow-ups, and editable clinical dictation drafts. The clinician stays in control of patient identity and every saved draft.”

## 0:20–1:05 — Voice retrieval and conversational clarification

**Action:** click Speak a request. Speak only this command:

**“Hey, can you open Priya’s latest OPG report?”**

Wait for transcription/clarification. Show both Priyas and let the short spoken response finish. Start the microphone again and say:

**“It’s actually Priya Sharma.”**

Show PT-001, OPG, RPT-001-03, 19 October 2026. Let the opening confirmation play.

**Say to the reviewer:**

“Priya is ambiguous, so the application asks instead of guessing. My natural clarification completes the original OPG request. The report is selected by patient, modality and date through deterministic database rules.”

## 1:05–1:35 — Context, mixed intent, evidence and tool trace

**Action:** type this request so you can narrate without another STT call:

**“Thanks for this, also can you summarize her report?”**

Let the short summary play. Click one citation, then expand its tool trace. Turn Spoken replies off after playback.

**Say to the reviewer:**

“The assistant keeps the selected report as context and processes the question even though it begins with thanks. The summary preserves the recorded uncertainty. Each citation opens the original source excerpt. The trace shows which backend operation actually ran.”

**Expected:** horizontally impacted lower right third molar, a recorded assessment limitation, and RPT-001-03 citations. Do not require identical generated wording.

## 1:35–2:35 — Voice dictation, editable structure and enforced validation

**Action:** select Create draft, click Speak a request, and dictate:

**“Possible periapical radiolucency near the upper left first molar. Further assessment is required.”**

Show source transcript, finding/site, uncertain certainty and readable preview. Open View JSON briefly.

**Say to the reviewer:**

“This creates a new draft from my dictated observations; it does not diagnose an image. The original transcript remains visible, and the fields retain the site, evidence and uncertainty.”

**Action:** change Certainty from uncertain to asserted, then click Save reviewed draft. Show the uncertainty-preservation error. Restore uncertain, dismiss the error and save again.

**Say to the reviewer:**

“The LLM proposes structure, but Python validates it. Changing ‘possible’ into an asserted finding is rejected. After restoring the source-supported value, I explicitly save it as a draft. Clinician review is still required.”

**Expected:** Saved as draft status. Skip export in this recording; if rehearsing it separately, export before final save.

## 2:35–2:50 — Refresh recovery

**Action:** reload, immediately turn Spoken replies off again, and show restored chat, Priya selection and saved draft. Use the session draft selector if needed.

**Say to the reviewer:**

“The conversation, selected report and draft survive refresh in the owned demo session. Saved history remains historical; it is not regenerated on reload.”

## 2:50–3:20 — Unsupported information and missing modality

**Action:** select Find / ask and Report, then type:

**“Does her report confirm oral cancer?”**

Show the unsupported-information response. Then type:

**“Open Meera Iyer’s latest OPG report.”**

Show no OPG available and the cleared active report.

**Say to the reviewer:**

“The assistant does not invent a diagnosis when the report lacks evidence. A missing modality is also explicit: Meera has no OPG in the mock dataset, so the previous patient’s report cannot be reused.”

## 3:20–4:00 — Architecture, evidence and honest limits

**Action:** switch to the pre-opened architecture image. Keep it on screen while closing.

**Say to the reviewer:**

“The stack is React with TypeScript, FastAPI and SQLite. Google handles streaming speech recognition; Groq provides LLM inference and speech, with documented fallbacks. No reviewer GPU is needed.

“Groq calls a typed planning function. Python separately validates identity, context, evidence and draft versions before executing allowlisted operations. This is a small explicit orchestration service rather than an autonomous agent loop.

“The package includes architecture and workflow diagrams, provider experiments, failure-and-fix records, and 283 passing automated tests. This remains a local synthetic-data proof of concept. Production clinic authorization, broader clinical evaluation and robust continuous voice interaction are future work.”

Finish at approximately 4:00. Do not claim tests establish universal conversational accuracy or production readiness.

## Timing and failure contingencies

- The 4:00 target is editorial, not an application latency guarantee. If processing is slow, shorten narration first. Remove the JSON peek and refresh segment before removing retrieval, dictation, source evidence or safety behavior. Keep the final file within the assignment’s 3–5 minute allowance.
- All-report summaries, misheard-name recovery and negation/correction cases are in the longer rehearsal. They do not all need to fit in this four-minute recording.
- If STT changes the name, use the displayed directory confirmation or spoken full-name correction. If you type a correction, say you are correcting the transcript; do not portray typed input as speech.
- If a provider is unavailable, do not repeatedly retry or pretend the run succeeded. Explain the outage and use the documented API/screenshot alternative if needed. A browser voice fallback must be identified as such.
- You may trim idle waiting in an edited demo, but do not alter response content, conceal a failed action as a success or replace live provider output with undisclosed prerecorded speech.
- The current tests/build cited here should be checked again if source changes before recording. This script itself did not consume model/STT/TTS allowance.
