# Implementation and verification status

Current snapshot: 23 October 2026. The local application is implemented; the latest unit/API result is **283 passed, zero failures** in `../verification/tests.xml`. This is evidence for tested cases, not a claim of universal language/clinical correctness or a completed human-recorded demo.

## Current implemented behavior

- FastAPI, React/TypeScript/Vite, SQLite/SQLAlchemy/Alembic; one backend worker and server-side provider keys. The current contract is in [system design](system-design.md) and OpenAPI `/docs`.
- Six patients and 18 seven-section revision-2 synthetic reports. Bootstrap upgrades only unchanged archived revision-1 fixtures; custom report edits are preserved.
- Deterministic latest-modality retrieval, pending name ambiguity, confirmation-only approximate suggestions, corrected full-name/ID recovery after zero matches, and retention of the original request through natural clarification.
- Unique named follow-ups may use the selected patient's report. Ambiguous/different names and different modalities require clarification; repeated questions do not reopen the report.
- Single-report evidence-backed answers with uncertainty/cause handling; explicit all-report summaries with dates, per-report citations, bounded concurrency, unchanged active report and labeled partial failures.
- Whole-message supported acknowledgements handled locally. Thanks plus a task reaches interpretation with the complete message. Eligible indirect identity replies use structured interpretation followed by Python directory/verbatim-name checks.
- Source-linked dictation, source-local site/polarity checks, negation/uncertainty/corrections, editable JSON/forms, readable previews, versioned draft saves and validated export. Export/edit returns preview; final save is explicit and always requires clinician review.
- Cookie-owned 24-hour demo sessions, persisted chat/pending state/drafts, sessionStorage recovery, bounded recent dialogue, new-session isolation, duplicate-utterance replay and stale-context/draft rejection.
- Google streaming STT, one Groq file fallback, automatic pause submission plus manual stop/cancel, separate speech requests, interruption and disclosed browser voice fallback. Spoken replies default on; long collection replies have a labeled short overview. This is not always-on full-duplex voice.
- API no-store, page/worklet revalidation and a visible startup Build fingerprint. Old chat is saved history, not regenerated answers. Backend changes require restart.

## Evidence by execution type

**Local isolated checks:** 283 unit/API tests use fixture/mocked providers and temporary SQLite databases. They include required retrieval/ambiguity/unsupported-claim tests, 36 connected patient workflows, named-question and natural-clarification matrices, collection failure handling, cache/idempotency behavior and acknowledgements with all provider methods blocked. Mixed thanks-plus-summary requests are checked through interpretation/answer handoff with the original text. One informational Starlette/AnyIO deprecation warning remains.

**Latest production UI build:** TypeScript/Vite production build passed with adjacent draft-save feedback, saved/dirty button state and local error visibility. The draft-save fixture browser check exercises real API/SQLite persistence, reload, edits, validation and forced-failure recovery. Native migration/seed/setup checks were executed earlier.

**Recent browser checks, with audio quota preserved:** name-recovery-audit uses controlled final STT transcripts with no upstream STT connection. all-reports-browser, named-followups-browser and clarification-cache-browser use live text inference with speech blocked. acknowledgements-browser uses the local acknowledgement branch. These record zero speech requests/page errors in their successful runs. See [workflow audit](WORKFLOW-AUDIT.md) for exact artifacts and limits.

**Historical provider/voice evidence:** real Google streaming STT, Groq file STT, LLM interpretation/extraction and cloud TTS succeeded on synthetic inputs. Chrome fake-microphone tests reached the pipeline and decoded audio; pause submission/interruption were checked. These are historical runs, not a current quota/health guarantee. Later Groq and Google speech quota failures remain recorded in F14. Browser speech fallback integration used controlled speech APIs; headless native voices were unavailable. Human-device speech accuracy/audibility is not established by those runs.

**Historical packaging/deployment checks:** native startup, Docker image/non-root container and Compose named-volume persistence checks ran. The Docker image was not rebuilt after every later fix. The current source ZIP is rebuilt separately with secret/exclusion/CRC checks; `output/package-check.json` describes the current archive, not production deployment.

## Deliberate scope and remaining work

Custom Python dispatch replaces an agent framework; React hooks replace a query-cache layer. Response evidence and draft findings are stored as JSON rather than separate relational evidence rows. Owner hashes are demo authorization, not login. HTTP commits commands separately from voice WebSocket transcription. Per-session locks and quota cooldowns are process-local; PostgreSQL, shared locking and multi-worker behavior are unverified.

Remaining candidate actions: one real microphone/speaker/noise rehearsal, recording the planned demo if desired, reviewing the note, uploading a repository/ZIP link and sending the submission. [The script](FOUR-MINUTE-DEMO.md) and [rehearsal](FINAL-REHEARSAL.md) are plans, not executed video evidence. Provider access/allowance is not currently guaranteed.

Production clinic authorization, real patient data, imaging/PACS diagnosis, clinical signing, regulatory certification, hosted operations, durable cancellation/queues and broader clinical/human-voice evaluation are outside this local take-home. No claim of perfect conversational coverage or medical correctness is made.

## Change history

Read [F01-F21 and later documentation audit notes](FAILURE-AND-FIX-LOG.md) for observed failures, root causes, fixes, failed verification attempts and resolution evidence. Earlier test counts and open-status statements there describe their observation time; this snapshot and each entry's later resolution give the current status. F09's two reproduced semantic defects have regression-tested guards, without a claim of universal semantic validation.


## Final user rehearsal follow-up

The candidate supplied four voice-test transcripts and screenshots, showing successful ambiguity/correction, named/contextual questions, mixed thanks and local acknowledgement, explicit cause abstention, recommendations, diagnosis abstention and a disclosed browser-speech fallback. These are user-reported device observations, not a scored STT benchmark or instrumented audibility check.

The matching reported Rohan draft was observed read-only as saved_draft version 7; the apparent save failure was missing feedback near the off-screen save controls. The UI now confirms success beside the button, disables unchanged saved drafts, re-enables for edits and shows local errors. Unspecified anatomical sites remain valid. `verification/draft-save-feedback.json` verifies this in an isolated fixture database without provider calls.

A bounded reviewed formatter now explains supported wisdom-tooth, nerve-canal, uncertainty and mock OPG sentences while preserving original quotations. Cause answers can include selected known findings/recommendations while abstaining on cause. The user's simple-language question and technique question passed through live text inference in `verification/plain-language-browser.json`, with speech blocked. Eight additional local regressions bring the complete suite to 283. No STT/TTS was used for this follow-up.
