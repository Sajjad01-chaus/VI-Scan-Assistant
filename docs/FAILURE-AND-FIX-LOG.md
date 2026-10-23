> Historical record: test counts, provider availability and open statuses below describe their observation time. The current snapshot is [implementation-status.md](implementation-status.md). F09's two reproductions now have regression-tested guards; broader clinical/human-voice evaluation remains open. Raw historical evidence is not rewritten after fixes.

# Failure and fix log

Started 23 October 2026 (Asia/Calcutta). Earlier entries below are reconstructed from this conversation's verified work; exact discovery times were not retained. Keep future entries current rather than silently dropping failures.

## F01 — Voice name mismatch and stale patient workspace

- Observed: user reported on 23 October 2026 that spoken Aisha Khan became “Ayesha Khan”, returned no match, and left Priya's workspace visible.
- Impact/cause: exact spelling lookup had no close-name recovery; the previous report stayed visually active after failed identity resolution. The original synthetic voice tests missed this case.
- Fix: propose same-surname, similar-first-name candidates without auto-selecting. Pause previous report actions and show identity resolution. Clear old evidence and remove paused patient highlighting. Allow editing recognized requests.
- Verified: `verification/name-recovery-browser.json`; backend identity tests. Exact recognized phrase reproduced through live browser commands; confirmed PT-004 and RPT-004-03, blocked previous-patient follow-ups.
- Limitation: directory similarity is a recovery heuristic; the user's actual voice/accent has not been reproduced. STT spelling is not guaranteed.

## F02 — Confirmation was only actionable by click

- Observed: 23 October 2026 follow-up highlighted that a voice workflow also needs a spoken confirmation.
- Fix: ask “Did you mean Aisha Khan, patient PT-004?”; accept explicit yes/no through the command path without another LLM call. Reject yes when zero or multiple candidates exist. Voice-originated replies are read aloud; manual microphone activation avoids listening during playback.
- Verified: `verification/spoken-confirmation-browser.json`, plus confirmation/modality/idempotency/rejection tests in `backend/tests/test_workflows.py`. Current backend suite: 37 passed.
- Limitation: that browser regression injects controlled STT transcripts and uses live TTS/LLM; it is not a human microphone test.

## F03 — Microphone cancellation race and late speech playback

- Observed: earlier browser interruption verification found asynchronous microphone setup could finish after cancellation.
- Fix: invalidate cancelled setup with capture generation tokens; cancel returned handles after stale setup. Invalidate pending playback on interruption and pause active audio.
- Verified: `verification/browser-interruption.json` covers late audio, active playback and cancellation before setup completion.

## F04 — TTS output/container and test harness issues

- Observed: initial Google instruction prefix could be spoken; Groq streaming WAV headers used unknown lengths. Playwright response-body extraction also misleadingly returned empty audio.
- Fix: send verbatim speech content; normalize WAV container lengths. Verify actual fetched bytes and decoding inside the browser instead of relying on the misleading harness result.
- Verified: provider comparison/content evidence in `verification/`; decoded speech in `verification/browser-auto-voice.json`.
- Limitation: automated content/decoding checks do not replace listening with real speakers.

## F05 — Model access and provider failures during experiments

- Observed: Groq TTS initially required account model-terms acceptance; Google file transcription attempts included unparsed output and a 503.
- Resolution: user accepted Groq terms, then successful TTS comparisons were rerun. Unparsed/failed Google file outputs were marked unscored, not counted as accuracy results. Streaming Google STT and Groq fallback were separately tested.
- Evidence: `verification/model-selection.md` and associated raw experiment files. Provider failures remain possible and must be surfaced; no unlimited-free claim is made.

## F06 — Earlier implementation audit found missing handover/workflow pieces

- Observed: user questioned whether the full application was delivered; audit found startup history race, incomplete editor/export/recovery flows and insufficient UI testing instructions.
- Fix: disable actions until history restoration completes; validate editable JSON and current form exports; restore chat/drafts; add readable preview, session reset, full UI guide and requirement coverage checklist.
- Verified: `verification/browser-smoke.json`, `docs/REQUIREMENTS-CHECKLIST.md`, `docs/UI-TESTING-GUIDE.md`.
- Remaining scope is explicitly listed in `docs/implementation-status.md`; production authentication, clinical validation and human hardware testing are not claimed complete.

## F07 — Local verification/tool execution failures

- Observed: restricted-sandbox loopback tests hung; default package cache was inaccessible. A later append command used the frontend directory with root-relative paths and failed to write CSS/tests.
- Resolution: loopback tests ran with the permitted execution profile; dependency commands used a project cache. The failed append was rerun from the correct project root, then frontend build and all affected tests passed. No failed write was treated as successful.
- Evidence: tool outputs in this conversation; `verification/tests.xml`, browser JSON files and successful production builds.


## F08 — Tool-calling and voice behavior were not clear in the handover

- Observed: 23 October 2026 user asked whether tool calling and automatic voice replies actually existed. Audit also found design text describing a voice start envelope and retry jitter that the current implementation does not use.
- Fix: README now distinguishes the actual Groq planner function from deterministic database operations/tool traces, explains Python validation boundaries and documents automatic speech for voice versus optional speech for typed requests. Corrected the inaccurate WebSocket/retry descriptions in the design document.
- Verified: inspected `providers.py` schema/tool_choice/tool_calls parsing, `service.py` dispatch and validators, `schemas.py` request constraints, `main.py` session/origin boundaries and `main.tsx` voice-origin response flag. Existing browser voice evidence confirms the spoken-response path; no runtime code changed in this documentation audit.
- Limitation: production identity/clinic permissions, billing metering and an overall utterance deadline remain future work. Browser evidence does not establish actual human microphone performance.


## F09 — Resolved reproductions: finding site and polarity validation

- Observed: reviewer-readiness audit on 23 October 2026. Direct calls to `validate_findings` accepted both cases below despite semantic mismatches.
- Case 1: transcript “Possible caries in upper left first molar. No fracture in lower right third molar.”; finding quotes the first sentence but assigns caries to “lower right third molar”. Accepted because the site check searches the entire transcript instead of establishing the finding-to-site relationship.
- Case 2: transcript/evidence “Caries in upper left first molar.”; finding polarity `negated`. Accepted because the validator checks that explicit negation is preserved but does not reject negation invented for positive evidence.
- Impact: schema and substring provenance checks alone do not ensure clinically faithful structured findings. Existing 37 passing tests do not cover these cases.
- Initial status: reproduced and left open during the earlier assessment.
- Resolution, 23 October 2026: validate anatomy against the finding’s own evidence or its immediately preceding standalone anatomical fragment, including explicit corrections. Reject invented negation when quoted evidence has no negation. Added regressions for both reproductions and the source-local fragment boundary. All 133 local tests pass, including connected extraction/save workflows. These conservative rules do not establish universal clinical semantic correctness.


## F10 — Default speech omitted directory/typed actions

- Observed: 23 October 2026 user reported silence after opening Arjun. The screenshot showed a directory-generated command and automatic speech unchecked. Earlier voice-only success did not cover that directory path.
- Cause: speech defaulted off; only voice-originated commands overrode the preference. Directory selection and typed requests therefore remained silent.
- Fix: spoken replies default on for all new interactions and the checkbox mutes all paths consistently. Unlock an AudioContext in the request gesture, show preparing/speaking/error state, and use decoded Web Audio if HTML media autoplay is blocked. Interrupt both playback mechanisms on cancellation/new capture. The report remains available when speech fails.
- Verification: `verification/default-speech-full-reports.json` checks live directory and summary playback, unmuted time advancement, mute, forced NotAllowedError fallback and forced TTS 503. `browser-auto-voice.json` now verifies automatic TTS without clicking Listen. Interruption and fixture workflow checks passed.
- Test harness failure: the first playback-progress check timed out because document listeners do not observe detached Audio-object events. Attached listeners directly to each player; rerun passed. This was not silently treated as a product success.
- Limitation: browser playback progress does not verify the user's OS output device or actual audibility. Listen remains an explicit replay/retry action. Mute is reset to the on-by-default state on page reload.

## F11 — Minimal reports were inadequate demo fixtures

- Observed: 23 October 2026 user correctly identified reports as only two or three lines. The original fixtures exercised retrieval but lacked report depth and variety.
- Fix: all 18 reports now have seven sections: indication, technique, comparison, findings, impression, clinical correlation and limitations. Revision 2 is rendered as a readable document with an emphasized impression. Original text is archived in `data/synthetic-v1.json`; bootstrap upgrades only an exact archived revision-1 fixture, preserving unrelated edits. Old turn evidence retains its recorded quote/version. Current report highlighting checks both ID and revision.
- Additional UI fix: a newly opened patient report could retain the prior report's scroll position. The report body now owns scrolling and resets at report/tab changes.
- Verification: all 18 local records are revision 2 with seven sections, minimum 1089 characters. Added an idempotent seed-upgrade test including preservation of a custom edit; 38 backend tests pass. Report-section/default-speech browser check, full draft/JSON/history browser smoke and seven-step API sequence passed. Live-provider checks are recorded separately.
- Limitations: these are authored fictional reports, not clinical image interpretations. F09 semantic-validation defects remain OPEN; richer source text does not fix those validators.


## F12 — Conversational patient clarification ignored pending session state

- Observed: 23 October 2026 screenshot sequence: “Open Priya’s latest OPG report” offered two choices; “It’s Priya Shah” returned generic instructions and left selection unresolved.
- Cause: only yes/no had a deterministic pending-reply handler. A named answer was routed as a fresh command, and the model had no recent dialogue. Stored chat alone did not supply conversational behavior.
- Fix: resolve short full-name, unique-surname, ID or ordinal replies against the session's pending candidates before LLM routing, retaining the requested modality. Guard ambiguous/negative/unrelated replies; an explicit new retrieval may switch requests. Supply at most six recent completed turns, capped at 1000 characters per message and filtered to the active patient/report/revision, for reference interpretation. Current-report evidence remains mandatory.
- Verification: 52 backend tests pass, including refresh-restored pending choices, original OPG retention, no model call for a clear answer, persisted reply history and session/report isolation. The live browser run passed: pending choices survived refresh, the exact reply opened the original OPG, a contextual tooth/testing follow-up was grounded in the current report, history restored again, and a controlled voice transcript resolved the same choice. Evidence: `verification/session-clarification-browser.json`.
- Intermediate regression: the new pending guard returned `candidates` instead of the existing `clarification` contract for blocked summaries, failing two tests. Restored the follow-up clarification branch and reran all tests successfully; assertions were not weakened.
- Scope: same owned demo session and browser tab, including refresh; no cross-browser account login or indefinite memory. Voice-boundary replay is controlled STT text, not a human accent test. F09 remains OPEN.


## F13 — Compound summary lost the cause question; valid quotes were not always relevant

- Observed: user supplied the live exchange on 23 October 2026. A combined summary/main-cause request returned six excerpts without addressing the cause.
- Cause: the summary provider replaced the original user question with a generic summary request, and the service concatenated all selected evidence.
- Fix: preserve the exact request with a separate summary flag. Use role-labeled, bounded excerpts and a deterministic readable formatter, preserve original evidence separately, and explicitly abstain on an unestablished cause. Model-authored narrative is not spoken.
- Additional failure during verification: a subsequent cancer-confirmation question received genuine but irrelevant report excerpts. Reproduced twice and captured in `verification/answer-quality-failure.json`. Added source-topic/relevance checks for common diagnosis-question forms plus regression cases; this was not silently ignored or relabeled as successful.
- Verification: 66 backend tests pass, covering original compound request preservation, concise output, uncertainty, no inferred cause, fabricated model prose ignored, invalid/irrelevant evidence rejected, negative evidence preserved, and exact citations despite terminology explanations. Final live text-answer browser checks passed, including the exact compound request and unsupported diagnosis follow-up. An earlier run also reached actual cloud playback (`concise-summary-cause-cloud-pass.json`). Later speech runs hit real provider quota limits; those failures and the fallback verification are recorded in F14.
- Limits: controlled phrase explanations and lexical topic/causal rules are conservative, not a semantic or clinical correctness proof. Unsupported question forms still need broader evaluation. F09 remains open and is not fixed by this answer-layer work.


## F14 — Real cloud speech quota blocked final audio verification

- Observed: final full-provider smoke failed at `/speech` with HTTP 503; the audio-browser check timed out waiting for a playing event. Text-answer, retrieval, extraction and abstention steps had succeeded. Diagnosis found Groq Orpheus HTTP 429 on its daily allowance for longer replies, and Google TTS HTTP 429 too. Short Groq audio could still succeed with the small remaining allowance. No full-cloud success is claimed for those failed runs.
- Evidence: `verification/speech-availability-check.json`, `long-speech-check.json`, and `current-tts-quota.json`. At 08:28 IST on 23 October, the 247-character reply received Retry-After 4872 seconds, approximately 09:50 IST for that request, not a complete-budget reset. Account identifiers were redacted from saved diagnostics.
- Fix: respect provider 429 cooldowns without retrying early, keyed by endpoint/model so unrelated models remain available. UI falls back to browser speech when cloud audio is unavailable and a browser voice exists; the downgrade is visible. Stop/mute and generation cancellation apply to that fallback too. If no voice exists, retain text and a visible unavailable/retry status.
- Verification: 66 backend tests pass including retry-header/default cooldown and model isolation. Frontend production build passed. Controlled browser speech-API integration passed for exact displayed text, disclosed fallback, stop and mute (`browser-speech-fallback.json`). Final live text-answer check passed with speech muted to avoid consuming quota. The installed headless Chrome exposed zero native voices, so actual local voice availability/audibility is not claimed verified.
- Outstanding environmental constraint: cloud TTS remains quota-limited until the provider allows the requested input. Main demo cloud-audio recording must wait for sufficient allowance. No paid upgrade, quota evasion, silent fixture output or fake live audio was used.


## F15 — General findings question misclassified as a diagnosis target

- Observed: 23 October 2026 user opened Meera Iyer, then asked “Have you find any key findings in her report?” and received an incorrect not-stated abstention.
- Cause: F13's lexical diagnosis guard matched every have/has phrase. It treated auxiliary “Have you found...” and generic findings words as named diagnostic conditions. Genuine source-supported observations were discarded.
- Fix: restrict have/has diagnostic matching to patient-subject assertions, distinguish generic observation objects from named conditions, and explicitly instruct evidence selection to include meaningful negative/uncertain findings. Keep explicit condition checks for requests such as “Does she have findings of cancer?”.
- Verification: 81 local tests pass including multiple auxiliary/general-findings phrasings, generic patient-observation questions, explicit diagnosis requests and negative evidence. The exact live Meera browser exchange passed, returned the no-definite finding plus recorded root-overlap limitation, and cited RPT-006-03 revision 2. Evidence: `verification/meera-key-findings.json` and screenshot.
- Budget: zero STT/TTS calls for this fix. The browser muted speech before interaction and intercepted all speech endpoints; no microphone was started. Only text-model requests were live. The user's voice-quota constraint is saved in AGENTS.md.
- Limitations: the lexical topic guard is not an exhaustive conversational or clinical parser. F09 and real-device voice validation remain outstanding; this entry does not claim those resolved.


## F16 — Lost correction after an unmatched voice name

- Observed: 23 October 2026. The user’s “Meera Iyer” was transcribed as “Mira/Meera Yash”; after zero matches, “Thank you” and then the corrected full name returned generic instructions instead of completing the report request.
- Cause: pending name resolution only searched offered candidates. An empty list had no recovery path; acknowledgements and incomplete replies were routed without preserving conversational intent.
- Fix: exact corrected full directory names/IDs resolve an empty pending list deterministically, retaining the original modality. Acknowledgements preserve the request. Conservative first-name phonetic/spelling similarity offers directory candidates for explicit confirmation; approximate matches never select a patient automatically. Zero-match UI now asks for a corrected name rather than offering yes/no instructions.
- Verification: 133 local tests pass, including 36 connected workflows (six patients × three initial states × two modality scopes). Each covers pending follow-up blocking, acknowledgement, service recreation, correction, cited summary, uncertain draft/save, history, patient switch, stale save/context rejection and new-session isolation. Cloud model entry points are blocked in this matrix.
- Browser evidence: `verification/name-recovery-audit.json` and screenshot. Controlled microphone transcripts “Mira Yash” → “Thank you” → “Meera Iyer” open the right report. A separate zero-match request survives refresh and accepts the bare corrected full name; chat and selection restore again. No page errors or speech requests; STT WebSockets are intercepted without an upstream connection.
- Verification failure: the first browser run timed out waiting only for a successful command after new-session creation. The harness now awaits the session response and reports all command HTTP statuses, including errors. Rerun passed; no unobserved backend failure is asserted from the timeout.
- Limits: this fixes application recovery, not the recognizer’s human-name accuracy. Actual human microphone/noise/accent and speaker evaluation remain outstanding. No STT/TTS provider calls were used for this fix/audit. Historical F11–F15 references to F09 being open describe their earlier state; the F09 resolution above supersedes them.

## F17 — All-reports request silently summarized only the selected report

- Observed: 23 October 2026. After selecting Priya Sharma and opening her CBCT, “Summarize her all reports” returned only RPT-001-02 evidence without acknowledging the narrower scope.
- Cause: the planner and summary executor had only a single-report summary path. Context identified a report, but the requested collection scope was discarded.
- Fix: add a `summarize_all` planner action and an explicit scope check in Python. List reports using the owned session’s resolved patient, apply any explicit modality, and sort newest first. Summarize/validate each source separately with at most three concurrent text-model calls. Return each report’s modality, timestamp, ID and exact versioned citations; keep the active report unchanged. Unresolved identity blocks retrieval. Empty collections are explicit. Generation failures, empty supported answers and invalid evidence produce a visibly incomplete result naming the failed reports, rather than pretending all succeeded.
- Voice behavior: collection summaries have a short persisted spoken overview directing the user to the report-by-report findings and limitations. The UI labels this “Listen to overview”; cloud and browser fallback use the same overview. This avoids silently cutting the long collection response at the existing speech-length limit. Single-report speech behavior is unchanged.
- Verification: `backend/tests/test_all_reports.py` covers the exact request, alternate summary phrasings, source spans/versions, modality filtering, patient switching, identity blocking, missing modality, partial outage/invalid/empty answers, persisted history, selected-report follow-ups and locally stubbed speech transport. The final full-suite count is recorded in `verification/tests.xml` and implementation status.
- Live text browser evidence: `verification/all-reports-browser.json` and screenshot reproduce the user’s ambiguity → selection → CBCT → all-reports sequence. All three PT-001 reports are cited, older-source preview leaves CBCT selected, history survives refresh and a subsequent singular summary stays on CBCT. Zero browser errors and zero speech requests. No microphone or STT/TTS provider calls were used.
- Verification failures resolved: pytest initially rejected the reserved parameter name `request`; renamed it. The new “Give a summary…” case then exposed that fixture routing recognized only the summarize verb; added the summary noun and reran the affected/full tests. Also corrected exploratory reads of a nonexistent frontend API file and an unsupported PowerShell glob by reading the actual source files; neither was treated as product evidence.
- Limits: these are separate source summaries, not inferred disease progression or a clinical comparison between images. Text-model usage scales with the number of matching reports; this local dataset has three per patient. Actual audible collection playback was not exercised against cloud providers to preserve demo quota.

## F18 — Selected patient's name rejected; repeated question reopened report

- Observed: 23 October 2026. After confirming Rohan Desai, a findings question naming “Rohan” returned “Open that patient’s report first”. Repeating the question with his full name opened the report rather than answering. The earlier readiness statement overstated conversational coverage.
- Causes: any named question was blocked, even when the name uniquely identified the active patient. The retrieval correction only recognized question marks or a few sentence beginnings, missing the declarative “I asked…” form. Existing tests mostly used pronouns and direct question forms.
- Fix: normalize proposed retrieval actions against explicit open/find/retrieve/locate intent; “show findings” remains a content question. Check named references against the directory and current selection, including names present in the text even if the planner omits them. A unique first name, surname or full name identifying the selected patient may use its selected report. Ambiguous/different/unknown names and a different modality request require clarification. Questions do not silently switch patients, choose another modality or reopen reports. The planner prompt now explains named/repeated content questions.
- Verification: 206 local tests pass. New cases include six patients × four natural phrasings × two proposed model actions, identity ambiguity/different-patient/unknown/multiple-name guards, modality mismatches and provider-boundary routing. Evidence: `verification/tests.xml` and `backend/tests/test_named_followups.py`.
- Live browser evidence: `verification/named-followups-browser.json` reproduces “Rohit Desai” → explicit Rohan confirmation → Yes → both user findings questions. Both answer from RPT-005-03 without reopening or context changes. “Show me the findings” also answers, a Meera question asks for a source switch, and history/selection survive refresh. Zero page errors or speech requests. No STT/TTS calls or microphone capture were used.
- Verification/tool issue: an initial exploratory read referenced nonexistent `test_answers.py`; inspected the actual `test_answer_quality.py`/test inventory instead. No test or product result was inferred from the failed read.
- Limits: this resolves the reproduced routing/identity rules; it is not evidence that every natural conversation will work. The planner and bounded clinical evidence selector still require broader language evaluation. Actual microphone recognition/audibility remain separate checks, and prior test counts do not establish product completeness.

## F19 — Conversational framing rejected a valid patient correction

- Observed: 23 October 2026. “Actually it’s Priya Sharma” failed to resolve the pending two-Priya OPG request, although the full intended identity was explicit.
- Cause: deterministic identity parsing matched narrowly framed replies and did not remove ordinary conversational fillers. Pending-state handling prevented general interpretation of less direct identity replies.
- Fix: normalize conversational framing for direct name replies. For eligible less direct replies, a separate structured LLM interpreter proposes choose/unresolved and a verbatim name; Python requires that name to be explicitly present in the current reply and resolve uniquely within pending choices. It cannot invent/expand names or select an unspoken ID. Questions/negative/clinical/retrieval phrases are excluded from this fallback; ambiguous replies remain unresolved. Fixture mode does not silently invoke cloud inference.
- Verification: 223 local tests pass, including natural framing variants, model-proposed invented/different names, unresolved decisions and exclusion of negative/questions. Browser evidence `verification/clarification-cache-browser.json` verifies the exact correction completing OPG and “The person I was referring to was Priya Sharma” completing the original CBCT through live text interpretation. No STT/TTS calls.
- Limits: language interpretation can still fail; this fallback is conservative and not a universal conversational guarantee. It adds text-model latency/cost only on eligible unresolved replies. No real microphone recognition claim is made.

## F20 — Unclear running build versus restored chat history

- Observed: 23 October 2026 user suspected port 8000 returned cached results. Inspected the listening process, served HTML/assets, current backend behavior, API fetch code and persisted history.
- Findings: the expected current process/build was running; no service worker or general answer cache was found. APIs already sent Cache-Control no-store. History deliberately restores stored old answers, and same-utterance-ID replay is intentional duplicate-request protection. New UI submissions generate new UUIDs. The HTML/worklet lacked explicit revalidation headers and the UI did not expose its running build.
- Fix: retain API no-store; add no-cache/must-revalidate for the HTML entry/worklet and explicit no-store on frontend API fetches. Expose a source/build fingerprint in API config, response headers and a visible header badge. No stored answers were rewritten or deleted.
- Verification: local cache-policy and fresh-versus-replayed-turn tests; live browser check confirms matching visible/header/config build IDs, two identical new submissions with distinct turn IDs, saved conversation after refresh and new-session isolation. Evidence: `verification/clarification-cache-browser.json`. The checked build ID is recorded there; fingerprints change with relevant source/frontend builds.
- Verification issue resolved: the first browser run could find the build label but it was hidden by existing footer CSS. Moved the badge into the visible header, rebuilt/restarted, and reran successfully. An initial sandbox CIM query could not inspect the listening process; repeated the read-only inspection with the permitted execution profile. No product failure was inferred from that tool restriction.
- Limits: a previously open page needs one reload to load the new frontend. Old saved chat is historical evidence, not a rerun against the new code. The current process fingerprint identifies code loaded at startup; backend source edits require restart. No STT/TTS calls were used.

## F21 — Compound polite acknowledgement unnecessarily called a failing provider

- Observed: 23 October 2026. After a successful Priya selection and summary, “Okay, thanks” returned a provider configuration/quota/access error.
- Cause: the local acknowledgement branch accepted only individual exact phrases. A compound acknowledgement fell through to LLM routing; an upstream failure then surfaced for a message requiring no inference. The generic error does not establish the precise upstream cause, and no new live quota probe was performed.
- Fix: recognize complete sequences of supported polite phrases with punctuation normalization. Compound thanks/acknowledgements respond locally and preserve session state. Require a full-message match so thanks followed by a task, question, clinical statement, correction or negative reply is not swallowed. “No thanks” remains a pending-identity decline. The acknowledgement path also skips identity-interpretation fallback.
- Verification: 272 local tests passed. A 40-case matrix crosses ten polite phrasings with empty, selected, pending and draft states; plan/answer/extract/identity/speech provider methods raise immediately if invoked. Further cases protect mixed commands, clinical text, questions and declines. `verification/acknowledgements-browser.json` confirms the exact text and compound variants return “You’re welcome”, use no tool calls, and survive refresh without browser errors. Speech was muted and blocked; no STT/TTS or text inference was needed by the browser acknowledgement checks.
- Limits: supported social phrases are deliberately bounded; this is not a general social-chat model. This fix avoids unnecessary provider dependence for the reproduced acknowledgements; it does not establish that the provider itself is currently healthy for model-dependent commands. Actual audio playback was not exercised.

- F21 follow-up verification: the user's concern about thanks plus a real question did not reproduce a failure. Three additional command-level local regressions confirm the complete mixed request reaches interpretation and the answer provider, returns selected-report citations and preserves context. The full suite now has 275 passing tests. No runtime change or live provider calls were needed for this additional verification; it does not assert arbitrary live wording accuracy.


## F22 - Documentation drift after iterative conversation fixes

- Observed: documentation audit on 23 October 2026 after the user requested all docs reflect accumulated changes. The earlier system design still described a bounded tool loop, WebSocket execution/events and proposed schema/layout that differed from the code; the one-page PDF said 29 tests. Current notes were spread across appended updates. The UI guide placed export after final save without explaining its preview-status effect, and an older fallback paragraph omitted browser speech.
- Fix: rewrite the system design as the implemented contract, consolidate status, refresh README/requirement/demo/submission/answer/name-recovery documentation, correct export/fallback instructions, and preserve historical evidence/counts with explicit labels. Rebuild the one-page PDF, four SVG/PNG diagrams and six canonical Mermaid sources. Include new natural clarification, named follow-up, collection scope, local acknowledgement and cache/build/history behavior. Recording/rehearsal docs remain plans, not completed videos. The note's human-device sentence must be updated by the candidate to actual results before sending.
- Verification: local Markdown links, six Mermaid/source synchronization checks and current test-count references are checked by docs/check_documentation.py against the preserved 275-test JUnit result. The PDF is exactly one page; PDF and all four portable diagrams were rendered and visually reviewed. Final verification artifacts are documentation-check.json and design-artifact-check.json; final source ZIP has independent secret/exclusion/CRC checks. No runtime source or provider configuration changed, so runtime tests were not rerun solely for prose/artifact maintenance.
- Tool/render issues resolved: bundled Python did not include fitz; available reportlab, pypdf, Poppler and PDFium were used without installing dependencies. Poppler emitted display-font warnings despite a readable render; final PDFium rendering was inspected. The initial voice diagram's HTTP-command label crowded its box, so it was shortened and rendered again. No unavailable dependency or render warning was counted as a successful check without an alternative verification.
- Limits: external websites, current model catalog/access/quota, human-device speech and Docker images were not revalidated. Historical test/provider/failure observations remain intact. Documentation verification is not an additional clinical/conversational correctness claim. No model, STT or TTS calls were made for this audit.


## F23 - One-page summary did not communicate the architecture visually

- Observed: 23 October 2026 user opened the generated architecture PDF and reasonably questioned whether it was the assignment brief. Although its prose described components, the stacked boxes and long explanation did not make the system's actual connections clear.
- Fix: replace that PDF with a diagram-first landscape page generated from the same system-architecture SVG as the PNG preview. Browser input/workspace/playback, FastAPI boundary/orchestration/rules/evidence/adapters, SQLite and hosted STT/LLM/TTS are connected by labeled protocol/data arrows. Model interpretation is visibly separated from business validation. The full explanatory prose stays in system-design.md. Rendering now exports native SVG text/paths through Chromium to PDF rather than rebuilding a separate prose handout.
- Verification: exactly one landscape page; readable component labels and plan_assistant_action text remain extractable. Regenerated PNG/PDF previews were visually inspected for clipping and alignment; documentation links/sources and package checks rerun. No application/runtime/model behavior changed and no provider calls were made.
- Limit: this is a logical component/data-flow view, not a production deployment topology or a claim of new voice validation. Detailed sequence/state/data-model Mermaid diagrams remain separate in the documentation index.


## F24 - Saved draft appeared unsaved because feedback was outside the visible editor

- Observed: candidate supplied Rohan dictation screenshots and reported Save reviewed draft was not working. Read-only inspection found the matching transcript already persisted as saved_draft version 7, with the fracture negated and site unspecified. This is a feedback defect, not evidence that fields were missing or the save failed.
- Cause: saved status was near the top of the scrolled editor. The bottom button retained its save label, and success had no adjacent confirmation. Errors also appeared only in the global area.
- Fix: show saving/success/error beside the bottom controls; on success show the version and change/disable the unchanged button as Saved as draft. Edits clear stale feedback, show unsaved state and re-enable saving. Restored saved drafts show the confirmation after reload. Explain that unspecified details need not be invented. Existing schema/evidence/patient/version checks remain enforced.
- Verification: `verification/reported-draft-save-observation.json` preserves the read-only observation. `verification/draft-save-feedback.json` uses an isolated fixture SQLite database and actual API save/read operations: unspecified/negated finding, adjacent success, duplicate-save prevention, reload, editing, invalid claim rejection and a deliberately intercepted 503 followed by a successful fresh-version retry. Screenshot inspected. No provider calls were used by this test; the existing user draft was not edited by it.
- Limits: this establishes tested feedback/persistence behavior. It does not mean every future network failure is impossible, or that saving signs a report. Fixture speech is disabled; no human/audio claim is made.

## F25 - Source-grounded answers remained technical or described a synthetic fixture too literally

- Observed: the candidate's four voice-test conversations successfully resolved identities/acknowledgements and abstained on unsupported diagnoses/causes. However, simple-word findings retained third-molar/nerve-canal terminology and Arjun's technique answer recited Synthetic panoramic dental radiograph text scenario.
- Fix: add bounded exact/anchored sentence formatting for the recorded wisdom-tooth observations, selected uncertainty/canal caveats and the mock OPG technique sentence. Keep original evidence text, offsets and versions unchanged. Unknown wording remains unchanged. Cause prompts may select the known principal finding and a recommended next step, while Python still explicitly abstains on an unestablished cause. Primary terminology references and limits are recorded in answer-quality.md; no new patient diagnosis/treatment is inferred from them.
- Verification: eight additional local formatter/source/cause regressions bring the full suite to 283 passed. Frontend TypeScript/Vite build passed. `verification/plain-language-browser.json` replays the user's mixed thanks/simple-words request and Arjun technique query through live text inference with speech muted/blocked; both returned clearer wording with original quotes and zero browser errors/speech calls.
- Limits: the glossary is deliberately small and is not a universal medical paraphraser or clinical validation engine. New terminology still needs review. The four supplied conversations are user-reported device observations, not an instrumented STT accuracy/audibility study. No STT/TTS calls were made for either fix.


## F26 - Component diagram omitted numbered report-generation paths and obscured adapters

- Observed: candidate shared an external review noting the one-page diagram still did not show ordered retrieval, dictation-to-draft and follow-up paths or enough explanation. The bottom-positioned adapters box made STT/LLM appear to bypass adapters.
- Fix: compact the component view; put distinct STT/LLM/TTS adapter boxes on each cloud connection; retain separate SQLAlchemy database access. Add three numbered flow strips, including extraction → validate_findings (quote/site/negation/uncertainty) → editable JSON → clinician review → versioned save, and a short explanation of the interpretation/validation boundary. Typed input explicitly bypasses STT. Mirror the flows in README, and add the candidate-requested what-works/limitations/additional-time summary there rather than relying on scattered sections or only the separate note.
- Verification: regenerated the PDF/SVG/PNG; checked exactly one landscape page, text extraction of all three flows and adapter labels, and visually inspected readability/alignment. Local documentation links/canonical source checks and source-package secret/exclusion/CRC checks were rerun. The recorded runtime suite remains 283 passed; no runtime source changed and no provider calls were made.
- Limit: this is a logical execution explanation, not a physical production topology, a new runtime test or a completed candidate video/submission. Existing formal human-voice and production limits remain explicit.

## F27 - Submission tree included local scratch files and root-level experiments

- Observed: pre-publication audit on 23 October 2026 found no Git repository yet, incomplete scratch/audio ignore rules, and optional provider experiment scripts mixed into the project root. An initial Windows ripgrep wildcard argument was invalid; corrected glob-based searches completed the audit.
- Fix: initialize main against the candidate-provided empty GitHub repository; move historical experiments into scripts/experiments and adjust their root resolution. Ignore editor state, test scratch folders, temporary databases, archives, credentials and generated audio; retain the synthetic input/browser audio fixtures needed by existing checks. Add consistent text line endings and a staged-snapshot credential/path check. Align ZIP audio exclusions and document the layout. Local environment, credentials and running demo data remain intact.
- Verification: relocated Python/JavaScript syntax checked without executing provider experiments. Documentation link/source checks passed with 283 recorded runtime tests. The staged snapshot passed scans for actual local credential values, recognizable credential patterns and forbidden paths. ZIP secret/exclusion/CRC checks passed. This is repository/package verification, not another live-provider or runtime test.
- Final formatting check found two whitespace-only lines in the existing browser speech check; trimmed them and reran the staged whitespace check.
- Limits: automatic scanning is bounded and not a guarantee against every possible secret format. Final recording and candidate submission remain pending. No STT, TTS or LLM calls were made for this cleanup.
