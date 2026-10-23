# End-to-end UI testing guide

Use only fictional patient information and synthetic clinical scenarios. This guide tests the take-home application, not clinical diagnostic accuracy.

For one ordered pass, start with [the final rehearsal](FINAL-REHEARSAL.md); for recording, use [the timed script](FOUR-MINUTE-DEMO.md). This longer guide is a manual test catalog, not evidence that every device case has been run.

## 1. Start and identify the mode

The current development app is available at **http://127.0.0.1:8000** while its server is running. Use Chrome or Edge, keep the same hostname throughout, and allow microphone access when requested. Use headphones for speech tests to reduce speaker feedback.

To start it yourself in Windows PowerShell, from the project directory:

```powershell
.\start.ps1 -Mode live
```

For reproducible tests without model keys:

```powershell
.\start.ps1 -Mode fixture
```

Stop an existing server with Ctrl+C before starting another on the same port. Initial dependency installation/build instructions are in README.md. Live mode needs both keys in the server's `.env`; never paste keys into the browser or chat. Restart after changing configuration.

Check the upper-right badge:

- **Live providers:** real Google/Groq requests. Voice and free-form report questions are enabled.
- **Fixture mode:** a visible banner explains that sample dictations and summaries use deterministic fixtures. Microphone/TTS controls are disabled. Unknown fixture dictation is intentionally unsupported.

The screen has a patient directory on the left, report/draft workspace in the center, and assistant conversation on the right. The assistant has **Find / ask** and **Create draft** modes. **New session** starts with no selected report or conversation; it does not delete the previous stored session.

## 2. Patient-name ambiguity (mandatory retrieval behavior)

1. Click **New session**.
2. In **Find / ask**, type:

   **Open Priya's latest OPG report**

3. Press Enter or the **Send** button.

Expected: the assistant asks you to choose between **Priya Sharma / PT-001** and **Priya Shah / PT-002**. It must not silently choose a report.

4. Click **Priya Sharma** in the assistant's candidate choices.

Expected: the center shows Priya Sharma, modality **OPG**, report **RPT-001-03**, performed **19 Oct 2026**. Clinical observations include a horizontally impacted lower right third molar and no evidence of a fracture. The context version increases. A tool trace names patient search and report retrieval.

## 3. Direct retrieval and modality filtering

1. Ask: **Open Priya Sharma's latest CBCT report**.
2. Inspect the report metadata.

Expected: **RPT-001-02**, **CBCT**, **10 Sep 2026**. The application chooses the latest matching modality, not the latest report of any kind.

3. Ask: **Open Priya Sharma's latest OPG report**.

Expected: it returns to RPT-001-03. You can also click a patient in the directory to open that patient's latest report across modalities. Directory search filters the fictional patient list.

## 4. Contextual follow-up and exact evidence (mandatory)

With Priya Sharma's OPG report selected:

1. Ask: **Summarize her report**.
2. Check that the assistant does not ask for the patient again.
3. Click a source chip below the answer.

Expected: an exact cited-evidence panel opens with report ID/version and the supporting excerpt. The summary uses the selected report. The active report selection remains unchanged. Tool traces are inspectable; they show application actions, not private model reasoning.

Extra check: switch to another patient's report, then click an older answer's source chip. The evidence panel must still identify the original source; it must not relabel that excerpt as belonging to the newly selected patient.

## 5. Unresolved switch must suspend pronoun follow-ups

1. Open **Arjun Mehta's latest report**.
2. Ask **Open Priya's latest OPG report**.
3. While the two-Priya choice is pending, ask **Summarize her report**.

Expected: clarification is required. The assistant must not summarize Arjun's report as if it belonged to Priya. The old source may remain visible with a pending-selection warning, but is not used for the unresolved follow-up. Resolve the choice before continuing.

## 6. Missing patient and missing report

1. Ask **Open Kavya Rao's latest OPG report**.

Expected: a missing-patient or clarification response; no invented record and no silent reuse of the previously selected patient.

2. Ask **Open Meera Iyer's latest OPG report**.

Expected: a missing-OPG response. Meera has other synthetic reports but no OPG. The active report is cleared, so a later contextual summary requires a valid report selection.

## 7. Report-aware questions (live mode bonus)

1. Open **Priya Sharma's latest OPG report**.
2. Ask **What does the report say about the lower right third molar?**

Expected: a response grounded in the impacted-molar source sentence, with a source chip. Wording and response time can vary.

3. Ask **Does this report confirm oral cancer?**

Expected: an abstention such as **That information is not stated in the selected report. I cannot infer it.** The source does not contain that diagnosis. The assistant must not invent a clinical conclusion or treatment plan.

Fixture mode does not pretend to answer arbitrary questions. It returns a clear message that free-form report questions require live mode.

## 8. Dictation with uncertainty (mandatory draft behavior)

1. Select **Priya Shah / PT-002** by opening her report.
2. Open **Draft editor**. If a prior draft is showing, you can still enter a new transcript using the assistant's **Create draft** mode.
3. Choose the displayed uncertainty sample, or paste this exact transcript in **Create draft** mode:

   **Possible periapical radiolucency near the upper left first molar. Further assessment is required.**

Expected:

- Source transcript is visible and unchanged.
- Observation: **periapical radiolucency**.
- Site: **upper left first molar**.
- Certainty: **uncertain**, rather than a confirmed diagnosis.
- A readable draft report appears below the findings.
- The draft is marked for clinician review.

The displayed sample works in both modes; arbitrary dictation requires live mode.

## 9. Negation, corrections, and incomplete speech

In **Create draft** mode, try each exact sample:

**Lower right third molar is horizontally impacted. No evidence of a fracture.**

Expected: the impacted observation is present; the fracture observation is negated. The readable draft preserves the negative sentence. It must not become a positive fracture finding.

**Upper right second molar. Correction, upper left second molar. No definite caries identified.**

Expected: the structured site is **upper left second molar**. Certainty preserves **not_definite**. The original transcript and correction metadata remain in the draft JSON; the discarded right-side phrase is not rewritten as the final site.

In live mode, try **Molar is**.

Expected: no meaningful clinical finding should be created from that incomplete phrase. The app returns clarification/validation failure. It must not complete the observation by inventing a diagnosis. In fixture mode, the unknown transcript is explicitly unsupported.

## 10. Edit and validate the JSON

Use the uncertainty draft from step 8:

1. Click **View JSON**.
2. The editable JSON contains an array of findings. Keep its structure intact.
3. Change the first observation from `periapical radiolucency` to `radiolucency`.
4. Click **Validate & apply JSON**.

Expected: validation succeeds because the shorter observation is still quoted in the source. The form reflects the change; the draft version increases.

Negative checks:

- Delete a closing JSON bracket and apply: a parse error is shown; the draft is not replaced by invalid data.
- Change the observation to `fracture` while keeping the original uncertainty evidence: the app rejects the unsupported claim.
- Change certainty from `uncertain` to `asserted` for the source beginning `Possible`: the app rejects removal of uncertainty.
- Add unexpected fields such as `requires_clinician_review: false` inside a finding: the schema rejects them. The immutable source transcript and review requirement cannot be overridden by findings JSON.

After a failed edit, restore valid JSON or use the form. Error banners can be dismissed with their X button.

## 11. Export, final save, and recover a draft

1. On a valid draft, click **Export JSON** if you want a download. Export validates current form findings and returns a preview with a new version. Unsupported edits must be rejected. Raw JSON text must first be applied with **Validate & apply JSON**.
2. Click **Save reviewed draft** after export/edits. Expect **Saved as draft · review still required**. Saving is not a clinical signature or approval. Any later edit/export can return it to preview, so perform final save last.
3. Refresh, then immediately uncheck Spoken replies if rehearsing silently. Open Draft editor if needed. Chat, selected report and persisted draft/version/status must restore; SESSION DRAFTS selects earlier previews/saves. Matching-version form edits recover locally.
4. Switch to another patient and try saving a draft assigned to Priya Shah. Expect a patient-mismatch error. Return to the assigned patient before saving; the draft must not be silently reassigned.

## 12. Live microphone: automatic submission

1. Confirm **Live providers** is shown.
2. Use **Find / ask** for navigation, or **Create draft** for observations.
3. Leave **Auto-finish after a pause** checked.
4. Click **Speak a request** and allow microphone access.
5. Wait until **Stop & submit** indicates capture is ready, then speak clearly:

   **Open Priya's latest OPG report**

6. Stop speaking.

Expected: interim words appear while you speak. After roughly **1.6 seconds of silence** following detected speech, capture finalizes and submits once. The assistant then requests patient disambiguation. Model/network processing adds time after capture; 1.6 seconds is the local pause threshold, not an end-to-end latency guarantee.

Speak after capture is ready, not during connection setup. If you pause for more than the threshold mid-sentence, the app may submit early; disable auto-finish and use manual stop for longer dictation. The simple pause detector needs real microphone/noise evaluation.

## 13. Manual voice, cancellation, and silence

- Uncheck **Auto-finish after a pause**, start voice, speak a complete observation, then click **Stop & submit**. Expect one final transcript and one command.
- Start capture, then click **Cancel**, including while it still says Connecting. Wait a few seconds. Expect capture to stay stopped without a delayed command or draft.
- Start capture and remain silent, then stop. Expect a no-clear-speech message, not an invented transcript. Background noise can affect the detector.
- Deny microphone permission. Expect a visible error and working typed input.
- Keep an utterance below 20 seconds. The UI automatically finalizes around 19 seconds to stay within the server limit.

## 14. TTS and interruption

1. Complete an assistant request in live mode.
2. Click **Listen** below its response.

Expected: the saved short response is spoken; the cloud adapter limits input to 600 characters. Collection replies explicitly offer **Listen to overview**, with full per-report findings on screen. It must not add new clinical claims. The small pause control stops speech.

3. **Spoken replies** defaults on; enable it if muted to automatically speak subsequent responses.
4. While speech is playing, click **Speak a request** for a new utterance.

Expected: prior playback stops immediately. A late audio response from the previous turn must not restart itself. Starting microphone capture is the interruption action; this is not an always-listening wake-word/full-duplex agent. Use headphones to avoid speaker echo.

If a cloud voice request fails, the visible answer remains available. Groq TTS falls back to Google; if both fail, an available browser voice reads the same saved reply/overview with a disclosed fallback label. If native voices are unavailable too, the UI reports speech unavailable.

## 15. Provider failure and recovery

These are optional manual checks. Do not expose keys or intentionally spend account quota to force rate limits.

- Disable network after the app has loaded, then submit a live request. Expect a sanitized error, no fabricated live response, and no secret values. Restore the network and submit a new request.
- A provider-specific Google streaming outage can use buffered Groq STT if Groq remains reachable. Turning off all internet cannot demonstrate a successful cloud fallback because both providers need network access.
- Forced streaming/TTS outage cases are covered in the automated suite using mocks. The UI does not need a production-facing fault-injection control.
- The app must not silently switch to fixture outputs during a live outage. Fixture mode requires an explicit server mode change and shows its banner.

## 16. What has been verified versus what you should rehearse

Executed by the agent: backend regression suite; source retrieval/disambiguation; clinical validation; forced fallback/silence tests; browser source-evidence and JSON editing; saved draft/chat restoration; live tool calling and report-aware abstention; synthetic PCM WebSocket tests; Chrome fake-microphone speech capture and TTS decoding; Docker image/container smoke.

Your final rehearsal: actual microphone permission/quality, your pronunciation and accent, room noise, natural mid-sentence pauses, speaker/headphone echo, perceived voice quality, and the 3-5 minute demo narration. Synthetic voice tests cannot substitute for these device checks.

Production authentication, real patient data, clinical signing, PACS/image diagnosis, and scan booking are not part of this submission. The chosen optional bonus is report-aware questions.

## 17. Quick 4-minute rehearsal

1. Show the synthetic/live labels. Speak Priya's OPG request and choose a patient.
2. Ask **Summarize her report** and open a source excerpt.
3. Dictate the uncertainty sample; show certainty, readable draft, editable JSON and draft save.
4. Ask an unsupported cancer question or show Meera's missing OPG.
5. Briefly show the architecture and measured provider comparison; state the remaining limitations honestly.

If something differs from the expected behavior, note the exact input, selected patient/report, UI mode, and visible error. Do not include API keys in screenshots or bug reports.


## 18. Recover a name misheard by speech recognition

1. Open Priya Shah from the directory.
2. In **Find / ask**, use **Speak a request** and say “Open Aisha Khan’s report.”
3. Inspect the recognized text in your user message. If it says “Ayesha Khan”, the app must show **Did you mean Aisha Khan, patient PT-004?**, offer **Aisha Khan / PT-004**, and pause the previous report. You can reproduce that path reliably by typing “Hello, open Ayesha Khan’s report.”
4. Before confirming, send “Summarize her report”. The app must request patient selection and must not summarize Priya’s report.
5. Click **Confirm & open** for Aisha Khan. The active patient must become **Aisha Khan**, with report **RPT-004-03**. Summarize this report and verify every citation is for that report.
6. To fix other transcript errors, click **Edit request** beneath your recognized message, correct it in the composer, and press **Send**. Editing alone does not submit a command.

Close-name matching only proposes candidates; it never selects a patient automatically. Unknown names also suspend contextual report follow-ups until a valid patient is selected. Exact-name recognition can vary with the speaker and microphone; the live browser regression reproduces the recognized text rather than claiming to reproduce your voice/accent.


### Voice confirmation follow-up

When a voice request produces one close-name candidate, the app reads “Did you mean Aisha Khan, patient PT-004? Say yes or no, or choose below.” aloud, while **Spoken replies** is enabled (on by default). Unchecking it mutes automatic replies for every input path. Click **Speak a request**, say **Yes**, and let the recording finish: Aisha’s report opens. The microphone is not reopened automatically while the assistant is speaking. Starting the microphone stops current playback.

To decline, repeat the candidate scenario and say **No**: the app removes the suggestion and asks for the name again. A later **Yes** must not open the rejected patient. If several patients are offered (for example Priya), **Yes** alone cannot select one. You can always use **Confirm & open** instead of speech.

The deterministic browser check in `verification/spoken-confirmation-browser.json` injects the two recognized transcripts through the microphone WebSocket boundary and uses live TTS. It verifies the conversation flow separately from STT name accuracy. Human microphone/accent testing remains necessary.


## 19. Default speech and complete synthetic reports

1. Refresh with Ctrl+Shift+R and confirm **Spoken replies** is checked.
2. Click **Arjun Mehta** in the directory. Expect **Preparing spoken reply…**, then **Speaking…**, and the opening acknowledgement without pressing Listen. The report itself is not automatically read in full.
3. Inspect the seven report sections: Clinical Indication, Technique, Comparison, Findings, Impression, Clinical Correlation and Limitations. These are synthetic text documents, not interpreted images. Revision 2 replaces the minimal seed text; the original fixtures remain in `data/synthetic-v1.json`.
4. Click **Summarize this report**. The summary should speak automatically and cite revision 2 of RPT-003-03.
5. Uncheck **Spoken replies**, then open Aisha. Expect a text response and no automatic speech. Re-enable it to restore spoken replies; Listen replays any saved response.
6. Starting the microphone or using Stop speech interrupts current playback. If the provider fails, the report remains open and the UI displays a speech error with retry guidance. If the browser blocks media autoplay, an AudioContext unlocked by the request click is used as a fallback; if it cannot run, the UI asks for a Listen click rather than silently succeeding.

Historical playback verification checked live TTS plus unmuted audio time advancing in Chrome, and separately forces autoplay rejection and provider failure. Actual OS sound-device selection and audibility still need your device test.


## 20. Conversational clarification and session context

1. Start a new session and click **Open Priya’s latest OPG report**. Expect Priya Shah and Priya Sharma choices.
2. Refresh the page before choosing: the same chat and pending choices must return.
3. Type or speak **It’s Priya Shah.** Expect PT-002 / RPT-002-03, modality OPG. Do not repeat “open report”; the original request is retained.
4. Supported short replies also include **Priya Shah**, **Shah**, **I mean Priya Shah**, and **PT-002**. **Priya** remains ambiguous. A question or a negative statement mentioning a candidate must not silently select that patient.
5. Ask **What is described at the upper left first molar?**, then **What testing is mentioned for that tooth?** Expect source-grounded answers from the selected report; the latter can cite its clinical examination and pulp-testing statement.
6. Refresh again. The selected report and submitted conversation must remain. New session starts a separate conversation.

Conversation display and pending state persist in the database for the owned session; the browser restores its session ID from sessionStorage. Model interpretation receives at most six recent completed turns (1000 characters per message), filtered to the active patient, report and revision. Conversation may resolve references but never replaces current-report evidence. An explicit new open-report request can switch patients. This is not cross-browser identity or unlimited memory; local demo sessions expire after 24 hours.


## 21. Concise summary plus unknown cause

1. Open Priya Shah's OPG, or resolve the Priya ambiguity by replying **It's Priya Shah**.
2. Ask exactly: **Can you summarize it like what happened to her? What is her main cause?**
3. Expect a short answer describing the possible finding, explicitly saying the underlying cause is not established, and retaining a relevant source caveat/assessment. It should not recite six report sentences or infer infection, a diagnosis, symptoms, poor hygiene or a treatment.
4. Expect at most three citations with original report wording, current report ID/version and valid offsets. Limited terminology explanations in the spoken text do not replace the original evidence.
5. With Spoken replies enabled, this answer should play automatically. Listen is replay only.
6. Ask **Does her report confirm oral cancer?** Expect an explicit not-stated/cannot-infer answer, not an unrelated repeat of the radiolucency summary. Do not interpret this as a diagnosis or exclusion of cancer.

See `verification/concise-summary-cause.json` for the live browser run, and `docs/answer-quality.md` for the implementation boundaries.


## 22. Speech quota recovery and recording preparation

- Cloud generation order is Groq TTS, then Google TTS. If both fail and a browser voice is available, expect **Browser voice — cloud speech unavailable** while the exact displayed response is read. Stop speech and mute must cancel/suppress it. Browser voice is a disclosed fallback, not Groq audio.
- If no browser voice is installed/exposed, text remains and the speech-unavailable status is shown. The automated headless environment had no native voices; the fallback integration test uses a controlled speech API and does not prove the candidate's device can speak.
- A provider Retry-After estimate applies to the rejected input length, not necessarily a full daily-budget reset. The captured Groq check at 08:28 IST on 23 October indicated about 09:50 IST for the 247-character summary. A whole recording can need more allowance. Avoid repeated live speech rehearsals while waiting.
- Rehearse with **Spoken replies** unchecked. Once sufficient cloud allowance is available, enable it and record a concise successful voice sequence, followed by a source/correction/failure example. Do not describe fallback or prerecorded audio as newly generated cloud speech.
- Reproduce live answer quality without speech calls with `TEXT_ONLY=1` for `scripts/browser_answer_quality.cjs`. The normal script checks cloud playback when quotas permit. Browser fallback integration is `scripts/browser_speech_fallback.cjs`.


## 23. Meera key findings and voice-quota preservation

1. Keep **Spoken replies** off during rehearsal.
2. Type **Hey, can you open Meera Iyer's report?** Expect RPT-006-03, IOPA.
3. Type **Have you find any key findings in her report?** Expect cited recorded observations, including the “No definite” finding and a source limitation; do not accept a generic not-stated response or reinterpret the report as proving everything normal.
4. The grammatically natural **Have you found any key findings in her report?** and **What are the key findings?** must also be interpreted as observation requests, not diagnosis confirmations.
5. Explicit unsupported condition requests, such as **Does she have findings of cancer?**, must still abstain when no corresponding source evidence exists.

The exact live text-only browser reproduction is `scripts/browser_meera_findings.cjs`. It blocks speech requests and does not start a microphone. Routine tests should preserve STT/TTS allowance for the real demo.


## 24. Recover a misheard patient name without restarting

1. Keep Spoken replies off during rehearsal to conserve quota.
2. Enter **Hey, can you open Mira Yash report?** Expect Meera Iyer as a suggestion requiring confirmation, with no automatic patient selection.
3. Enter **Thank you.** The pending report request must remain.
4. Enter **Meera Iyer** (or **It’s Meera Iyer**). Expect PT-006, RPT-006-03, IOPA without repeating “open report”.
5. In a new session enter **Open Unknown Person’s report**. Expect a request for the correct full name. Refresh, then enter **Meera Iyer**. Expect the same report and restored conversation.
6. For a request specifying CBCT, correction must retain CBCT and open RPT-006-02. A negative reply or an unrelated question must not select a patient.

The browser audit in `scripts/browser_name_recovery_audit.cjs` exercises controlled final transcripts and text recovery with speech blocked. It verifies application behavior, not real microphone transcription or audible output. See `docs/WORKFLOW-AUDIT.md` for coverage and limits.

## 25. Summarize all reports for the resolved patient

1. Keep Spoken replies off while rehearsing. Resolve **Open Priya’s latest OPG report** as Priya Sharma, then enter **Open Priya Sharma’s latest CBCT report**.
2. Enter **Summarize her all reports**. Expect a summary explicitly covering three reports: RPT-001-03 (OPG), RPT-001-02 (CBCT), RPT-001-01 (OPG), newest first. Each has its own date, finding/limitation and source citations.
3. Click an older report citation. Its quoted excerpt must appear while the active report remains RPT-001-02. Refresh; the collection answer and conversation must remain.
4. Enter **Summarize her report**. Expect only the selected CBCT. Enter **Summarize all her OPG reports**. Expect the two OPG reports.
5. A collection summary during unresolved identity must ask for selection; it must never combine the two Priyas. If a source cannot be summarized, expect an explicit incomplete result and the affected report ID.
6. Collection audio is labeled **Listen to overview**: it gives a short scope/status overview and points to the full findings and limitations on screen. This is deliberate, disclosed behavior for long answers. Single-report replies retain their usual automatic speech behavior when enabled.

Automated reproduction: `scripts/browser_all_reports.cjs`, with live text inference and speech blocked. Multi-report output is not a conclusion about disease progression or imaging changes.

## 26. Named findings questions and repeated questions

1. With speech muted for rehearsal, enter **Hey, open the Rohit Desai’s report**. Confirm the suggested Rohan Desai with **Yes**.
2. Enter **Okay, so can you tell me what are the findings in Rohan’s report?** Expect cited findings from RPT-005-03, with Rohan remaining selected. It must not ask you to open him again.
3. Enter **I asked what are the findings in Rohan Desai’s report.** Expect an answer, not another report-open action. **Show me the findings in Rohan’s report** should also answer.
4. Ask about **Meera Iyer’s report** without opening it. Expect a clarification asking for that source to be opened; it must not answer Meera’s question with Rohan’s evidence.
5. After opening Priya Sharma, a question saying only **Priya** remains ambiguous because there are two Priyas; use the full name. Requesting CBCT findings while OPG is selected must ask for the requested source rather than answer from OPG.

The exact browser sequence is `scripts/browser_named_followups.cjs`. It uses live text inference with speech blocked and no microphone. This validates the recorded examples, not all possible conversations.

## 27. Natural clarification and current-build checks

1. Reload once after an update. The small **Build** label beneath the app name identifies the running backend/frontend fingerprint; it is also returned by `/api/config` and the `X-App-Build` response header.
2. Enter **Hey, open Priya’s latest OPG report**. Reply **Actually it’s Priya Sharma**. Expect RPT-001-03 without another identity question. **Sorry, it’s Priya Sharma** also resolves the pending identity.
3. In a new session, ask for Priya’s CBCT, then reply **The person I was referring to was Priya Sharma**. Expect RPT-001-02. This less direct reply uses structured text interpretation followed by strict directory validation.
4. Refresh restores old submitted messages, including any failures produced before a code fix. Those historical messages are not regenerated. Submit a new request to exercise current behavior; New session starts a clean conversation without deleting old stored sessions.
5. New submissions always get fresh utterance IDs. Repeating a question is a new turn; retrying the exact same network utterance ID deliberately replays its original result to prevent duplicate execution.

`scripts/browser_clarification_cache.cjs` verifies these checks with speech muted/blocked and no microphone. APIs use no-store; the HTML/worklet revalidate. No service worker is used.

## 28. Polite closings do not require model inference

After selecting a patient or reading a summary, enter **Okay, thanks**. Expect **You’re welcome** with the selected report unchanged. **Thanks, got it** and **Perfect, thank you so much** also work locally. During pending clarification, the acknowledgement additionally reminds you that the report request is still waiting.

**Thanks, summarize her report** must still process the summary request. **No thanks** while a suggested identity is pending must decline that suggestion. These are not ordinary acknowledgements. Local replies do not establish provider availability for subsequent model-dependent requests. Spoken replies still use the configured speech path when enabled; keep them muted during rehearsal.

`scripts/browser_acknowledgements.cjs` checks the exact closing, compound variants and refresh history with speech blocked. The local regression matrix blocks all provider entry points across empty, selected, pending and draft states.

Mixed politeness is matched against the whole message, never a thanks keyword. **Thanks for this, also can you help me with the report's summary?** must reach interpretation and summarization with the complete original request. Three local integration regressions verify this handoff, current-report evidence and unchanged session context; they use fixture interpretation/answers, not a live model accuracy check.


## Final rehearsal and recording

For one ordered end-to-end pass, use [FINAL-REHEARSAL.md](FINAL-REHEARSAL.md). The [four-minute recording script](FOUR-MINUTE-DEMO.md) includes exact commands, timing, narration, expected output and quota/failure contingencies. These are manual plans, not additional executed verification. Export before the final save if you want to finish with saved-draft status.


## 29. Visible draft-save result and plain-language follow-up

You do not need to fill every field. A generated unspecified site is valid when the transcript gives no location for that finding. For No evidence of fracture, keep polarity negated; asserted certainty means the negative observation is stated directly.

After Save reviewed draft, expect a green confirmation beside the bottom button with the saved version, and the button changes to Saved as draft. The saved unchanged button is disabled; editing a field re-enables saving. Invalid edits and temporary save errors appear beside that button as well as in the global error area. Refresh restores the saved confirmation. The new check in `scripts/browser_draft_save_feedback.cjs` uses an isolated fixture server/database on port 8001 and makes no cloud calls; it must not be pointed at the live server for its fixture-only run.

The user's supplied draft was already stored as saved_draft v7 when investigated. The old top-of-editor badge was out of view, so visible feedback was the issue; no missing clinical fields were required.

Ask for Priya Sharma findings in simple words, then ask which imaging technique Arjun's report describes. Expect the supported plain-language wording with unchanged original citations, and mock OPG description rather than a claim that the app acquired an image. See `verification/plain-language-browser.json` for the live text-only check. This is bounded terminology formatting, not universal medical paraphrasing.
