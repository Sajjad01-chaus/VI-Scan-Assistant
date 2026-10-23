# Final end-to-end rehearsal

Use fictional data only. This is a manual test plan, not evidence that a human has completed it. Automated evidence and its limits are in `WORKFLOW-AUDIT.md`. The current automated suite has 283 passing tests.

## Prepare once

- Open http://127.0.0.1:8000/ in Chrome or Edge. Reload once and note the Build badge. Check Live providers. Fixture mode cannot demonstrate arbitrary speech or free-form clinical questions.
- Start a New session, select Find / ask, and uncheck Spoken replies for the silent rehearsal. Recheck mute after every reload: speech defaults on again. Do not start the microphone in this pass.
- Use one silent core rehearsal; run the extra cases only as needed. Typed live requests still use text-model allowance. No GPU is needed.
- Keep headphones, microphone permission and the recorder ready for the final recording. Close notifications, secrets, terminals with keys and unrelated patient data. Pre-open `docs/diagrams/system-architecture.png` for the closing explanation.
- Do not infer current provider allowance from a past reset estimate. If speech is unavailable, do not repeatedly probe it. Existing historical provider evidence is not a fresh success.

## Core application scenario

1. **Ambiguity.** Enter **Hey, can you open Priya’s latest OPG report?** Expect Priya Shah/PT-002 and Priya Sharma/PT-001; neither should be silently selected. Follow-up evidence is blocked until identity is resolved.
2. **Natural correction.** Enter **It’s actually Priya Sharma.** Expect PT-001, OPG, RPT-001-03, 19 October 2026. The pending choices disappear. The intended report is retained through the clarification.
3. **Mixed politeness and request.** Enter **Thanks for this, also can you summarize her report?** Expect a cited answer about the horizontally impacted lower right third molar and a recorded assessment limitation. It must not return only “You’re welcome”. Wording may differ; clinical qualifiers and source identity must remain faithful.
4. **Named follow-up.** Enter **What are the findings in Priya Sharma’s report?** Expect current-report findings and citations, without reopening the report or asking you to select Priya again. Click a citation and inspect its original quote/revision.
5. **Tool trace.** Expand the verified tool steps. Retrieval shows deterministic search/latest-report operations. A contextual answer shows answer_from_report or summarize_report. Explain that these are executed service operations; only the planner is the model-facing function schema.
6. **Standalone acknowledgement.** Enter **Okay, thanks.** Expect “You’re welcome”, no business-tool execution and no patient/context change. It does not need text inference; automatic audio would still need a speech mechanism if enabled.
7. **Voice-equivalent draft input.** Select Create draft and paste **Possible periapical radiolucency near the upper left first molar. Further assessment is required.** Expect the original transcript, a source-supported observation/site, uncertain certainty, readable draft and clinician-review status. This is typed rehearsal; use the microphone for this same input during recording.
8. **Meaning validation.** Change the finding’s Certainty from uncertain to asserted. Click Save reviewed draft. Expect an uncertainty-preservation validation error and no successful save. Restore uncertain and dismiss the error. This is a designed negative test, not a provider outage.
9. **Inspect/export before final save.** Open View JSON and confirm evidence, uncertainty and review status. If testing export, click Export JSON now and check the downloaded findings. Export validates edits and can return the server draft to preview status. Do not export after the final save if you want the screen to end in saved state.
10. **Explicit save.** Click Save reviewed draft with the valid uncertain finding. Expect a green confirmation beside the bottom button, the button changing to Saved as draft, a version increment and review still required. Unspecified sites are valid; do not invent missing details. The original source report must remain unchanged; saving is not signing.
11. **Recovery.** Reload once. Immediately mute Spoken replies again. Expect selected Priya/report, chat and draft recovery. Use the SESSION DRAFTS selector if necessary. Old messages remain their original stored results; a reload does not regenerate them.
12. **Unsupported question.** Select Find / ask and Report. Enter **Does her report confirm oral cancer?** Expect an explicit not-stated/cannot-infer response without invented diagnosis or irrelevant evidence. This is neither a diagnosis nor an exclusion of cancer.
13. **Requested modality.** Enter **Open Priya Sharma’s latest CBCT report.** Expect RPT-001-02, CBCT, 10 September 2026. Then **Summarize her all reports.** Expect RPT-001-03, RPT-001-02 and RPT-001-01, newest first, with dates/modalities and per-report citations. The selected CBCT remains selected. Incomplete source summaries must be labeled, never presented as a complete result.
14. **Scope returns to singular.** Enter **Summarize her report.** Expect only the selected RPT-001-02. A collection summary must not silently change subsequent singular scope. Collection audio is explicitly a short overview, with full details on screen.
15. **Missing modality.** Enter **Open Meera Iyer’s latest OPG report.** Expect no OPG available, Meera selected and active report cleared. Do not accept the previous Priya report as the answer. Meera has IOPA/CBCT fixtures, so this is an intentional dataset case.
16. **Session reset.** Click New session. Expect empty chat/context/draft workspace. Previous stored sessions are not deleted by this action.

## Extra conversation and clinical checks

Use separate new sessions for these so the expected state is clear. Keep speech muted.

- **Misheard name:** Open Mira Yash report → suggestion requiring Meera confirmation → Thank you → Meera Iyer. Expect PT-006/RPT-006-03 (IOPA), no approximate automatic selection.
- **Zero matches:** Open Unknown Person report → reload/mute → Meera Iyer. Expect the corrected identity to complete the pending request without repeating open report.
- **Repeated named question:** Open Rohan Desai report → What are the findings in Rohan’s report? → I asked what are the findings in Rohan Desai’s report. Expect answers from RPT-005-03, without reopening.
- **Different patient reference:** While Rohan is selected, ask about Meera Iyer’s findings without opening her. Expect clarification, not Rohan evidence used for Meera.
- **Negation:** With a patient selected, Create draft using **Lower right third molar is horizontally impacted. No evidence of a fracture.** Expect the fracture observation to remain negated. Do not treat no evidence as a positive fracture.
- **Correction:** Create draft using **Upper right second molar. Correction, upper left second molar. No definite caries identified.** Expect the corrected upper-left site, preserved no-definite qualifier, superseded source retained, and clinician review required.
- **Unsupported edit:** Change an observation to a diagnosis absent from its evidence and try saving. Expect rejection. Restore source-supported fields before continuing.

## One short device check, then record

After silent rehearsal, do one targeted real microphone/speaker check when allowance is available: speak a short open-report request and hear its automatic reply. Check that it is audible through the intended device, that the displayed transcript reflects what was recognized, and that starting another capture interrupts playback. Do not repeatedly rehearse cloud audio.

If a name is misrecognized, show the directory confirmation/correction. If cloud speech fails, the disclosed browser fallback may work depending on installed voices. Do not describe fallback as Groq audio. If the recording cannot show functional speech, state that honestly and use the permitted documented API/screenshot evidence; do not fabricate successful audio or hide a provider outage behind prerecorded speech.

Record with `FOUR-MINUTE-DEMO.md`. If any expected behavior above fails, capture the exact transcript, Build badge, selected patient/report and visible error; stop calling the failing workflow a success and record it in the failure log before another attempt.
