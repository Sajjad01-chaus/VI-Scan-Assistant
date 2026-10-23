# UI testing guide

Run the app using the repository README. Use synthetic data only. These are manual scenarios, not a claim that every microphone/browser combination has passed. Prefer typed requests with Spoken replies off during rehearsal to preserve provider quota.

## 1. Retrieval and conversational clarification

Start a New session in Find / ask.

1. Ask **Open Priya's latest OPG report.** Expect Priya Shah (PT-002) and Priya Sharma (PT-001), with no automatic selection.
2. Reply **It's actually Priya Sharma.** Expect PT-001, RPT-001-03, OPG, 19 October 2026.
3. Ask **Thanks for this, also can you summarize her report?** Expect a report-grounded answer and source citations. The thanks must not suppress the question.
4. Click a citation to see the original excerpt. Expand the tool trace to inspect the backend operations.
5. Say **Okay, thanks.** Expect a local acknowledgement without changing the selected report.

## 2. Dictation, validation and saving

With a patient selected, switch to Create draft.

1. Dictate or type **Possible periapical radiolucency near the upper left first molar. Further assessment is required.**
2. Inspect the source transcript, observation, anatomical site, uncertain certainty, readable preview and JSON. This is a draft of dictated observations, not an image diagnosis.
3. Change uncertain to asserted and attempt Save reviewed draft. Expect rejection because the source says possible.
4. Restore uncertain and save. Expect adjacent success feedback, a version and **Saved as draft**. The report still requires clinician review.
5. Reload. Expect the conversation, selected report and saved draft to recover. Use the session draft selector if needed. Reload re-enables Spoken replies, so mute again during rehearsal.

For negation, try **Lower right third molar is horizontally impacted. No evidence of fracture.** The fracture must remain negated. An unspecified site is valid when the transcript does not state one; do not invent details to fill fields.

JSON export validates edits and may return the draft to preview status. Export before the final save if you want to finish in saved state.

## 3. Follow-up scope and unsupported claims

Return to Find / ask.

- **Does her report confirm oral cancer?** Expect not stated/cannot infer; this is neither a diagnosis nor an exclusion of cancer.
- **Open Priya Sharma's latest CBCT report.** Expect RPT-001-02, 10 September 2026.
- **Summarize her all reports.** Expect three dated reports, newest first, with per-report evidence. Failed summaries must be labeled rather than presented as complete. The selected CBCT remains selected.
- **Summarize her report.** Expect only the selected CBCT again.
- **Open Meera Iyer's latest OPG report.** Expect no OPG available and the active report cleared, without reusing Priya evidence.

## 4. Name recovery

Use separate New sessions.

- **Open Rohit Desai's report** should suggest Rohan Desai (PT-005) and require confirmation. **Yes** completes the request.
- **Open Priya's report** must ask which Priya; **It's Priya Shah** completes the pending request.
- After an unknown name yields no matches, reply **Meera Iyer**. The corrected full name should complete the pending report request.
- With Rohan selected, **What are the findings in Rohan's report?** should answer from his selected report. Asking about a different patient must not reuse Rohan's evidence.

## 5. Voice and failure handling

In live mode with keys/network available, enable Spoken replies, click Speak a request, speak a short command and stop or pause. Check the displayed transcript and automatic response. Capture is limited to 20 seconds. Starting another voice turn should interrupt playback.

If STT misrecognizes a name, use directory confirmation, a full-name correction, or Edit request and resend. Do not portray typed input as successful speech recognition. A visible browser voice fallback must be identified as such if cloud TTS is unavailable.

Provider errors must be visible without inventing a patient action. Do not repeatedly retry quota errors. Preserve the exact request, selected patient/report, Build badge and error when reporting a failure. The automated tests use mocked providers; real-device speech accuracy and current quota require separate checks.

## 6. Reset

New session clears the active workspace. It does not delete prior stored sessions. Saving drafts never signs or finalizes a clinical report.
