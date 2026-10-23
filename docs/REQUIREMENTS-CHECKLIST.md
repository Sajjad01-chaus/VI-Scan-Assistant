# Assignment and design completeness checklist

Audit against the supplied two-page VI-SCAN assignment, the system-design baseline, and the agreed provider choices. Updated 23 October 2026. This checklist distinguishes functional implementation, test evidence, and deliberately excluded production scope.

## Assignment: mandatory features

**A. Typed/spoken patient-report retrieval — implemented.**

Intent/name interpretation through Groq function calling; deterministic Python patient search and latest-modality report selection; explicit candidates for similar names; missing-patient and missing-report responses. Live microphone transcripts enter the same command pipeline as typed requests. Evidence: `test_workflows.py`, `browser-smoke.json`, `api-demo.json`, `app-live-smoke.json`, `browser-auto-voice.json`.

**B. Audio/transcript to editable structured draft — implemented.**

Findings include anatomical site, polarity, certainty, exact source evidence and offsets. The UI has structured form editing, direct findings-JSON editing with validation, a readable draft preview, versioned saves and validated JSON export. Negation, uncertainty, basic incomplete phrases and contradictory anatomy are checked. Explicit corrections retain original/superseded text. Every draft requires clinician review. Evidence: workflow/provider-boundary tests, browser draft screenshot and JSON-edit/recovery smoke. These checks do not prove universal clinical semantic correctness.

**C. Context-dependent follow-up and evidence — implemented.**

Explicit selected patient/report state resolves pronouns; an unresolved identity switch suspends follow-ups. Answers show report ID/version and exact excerpts. An evidence panel retains the original cited identity even when active selection later changes. Evidence: contextual tests, history tests and browser source-panel checks.

## Assignment: optional bonus

**Report-aware chatbot — implemented in live mode.**

Singular questions are scoped to the selected report, including unique matching named references. Explicit all-report summaries list the resolved patient’s matching reports with per-report citations and partial-failure labels, without changing selection. Unsupported information triggers an abstention. The selected bonus is not scan booking; booking was not part of the chosen implementation. Evidence: live smoke includes an unsupported cancer question and source-backed summary.

## Assignment: technical expectations

- **Reasonable stack:** FastAPI/Pydantic, React/TypeScript/Vite, SQLite/SQLAlchemy/Alembic, hosted provider adapters.
- **Synthetic dataset:** six fictional patients, two similar Priya names, three reports per patient. `data/synthetic.json` contains 18 reports; Meera intentionally has no OPG to exercise missing-modality behavior.
- **Tool calling and rule separation:** Groq proposes a typed action through plan_assistant_action; trace steps are deterministic service operations, not separate model-exposed tools. Local acknowledgements and strict pending-identity resolution avoid unnecessary model calls. For other interpretation, Python validates identity/context/arguments and executes allowlisted operations. Structured extraction and evidence validation are separate from interpretation.
- **Failure/input handling:** schema validation, sanitized provider errors, bounded retry/deadline behavior, source validation, idempotent turn IDs, context/draft version checks, silence rejection, audio size/duration limits, and STT/TTS fallbacks. Forced outage tests are included; the final suite has 283 passing tests.
- **Privacy/authorization/latency/cost notes:** README, system design and experiment notes. Keys remain server-side; local demo cookie ownership is explicitly not production authentication. Audio is transient; draft transcripts/history persist locally. No unlimited-free or regulatory-compliance claim is made.
- **Required automated tests:** correct retrieval, ambiguous identity, unsupported clinical claims are included, plus broader workflow/fallback/recovery tests. Actual result is recorded in `verification/tests.xml`.

## Assignment: deliverables

- **Runnable source and mock data:** source ZIP, pinned lockfiles, native launcher, Dockerfile/Compose configuration, migration and seed command. Native build and Docker image/container smoke have run. Compose startup and named-volume recovery across container recreation were executed.
- **README:** setup, providers/models, `.env.example`, demo steps, tests, and limitations are documented.
- **Demo:** documented API sequence with actual outputs, screenshots, and live/synthetic voice evidence. The assignment permits this alternative to a video; no video recording is claimed.
- **One-page architecture:** `docs/architecture-one-page.pdf`, plus full design, Mermaid sources and exported diagrams.
- **Recording preparation:** [four-minute script](FOUR-MINUTE-DEMO.md) and [complete rehearsal](FINAL-REHEARSAL.md) are prepared, not a completed human recording.
- **Submission note:** draft at `docs/submission-note.md`. Uploading/sharing a repository or ZIP link and sending HR the note remain actions for the candidate; nothing was sent automatically.

## Agreed experience: additions verified after the completeness audit

- Automatic utterance submission after a pause, with manual stop/cancel retained. This is a simple energy-based pause detector, not an always-listening full-duplex agent.
- Chat/selected-report recovery after refresh, session draft selection, local matching-version form recovery, and a new-session action.
- A distinct readable draft preview and direct JSON editor; applying/exporting edits runs backend evidence/schema validation.
- Inspectable exact source evidence, including older answers after a patient switch.
- Browser-verified interruption/capture cancellation and discarded late audio.
- A bounded structured-schema repair attempt; no unbounded agent loop.
- UI test guide: `docs/UI-TESTING-GUIDE.md`, with exact inputs, expected behavior and negative tests.

## Design choices that are equivalent implementations, not missing features

React hooks replace the proposed query-cache library. Evidence is stored in response/draft JSON instead of a separate evidence table. Owner-token hashes replace a separate actor table. Dictation uses the shared command endpoint rather than a duplicate draft-creation endpoint. These do not remove the required user workflows. The physical schema and actual API are in source/OpenAPI; the full design document now describes the current implementation rather than an unimplemented directory/tool-loop proposal.

## Remaining limits and excluded scope

Human microphone/accent/noise rehearsal and subjective voice-quality evaluation require the candidate's actual device. Automated voice evidence used synthetic PCM/Chrome fake microphone audio. Simple pause thresholds may submit early during a long clinical pause; manual stop remains available. Starting another microphone capture interrupts playback, but there is no wake-word/always-on full-duplex listening or durable cancellation of already-running cloud inference.

Production authentication/clinic authorization, regulatory certification, real patient data, PostgreSQL/multi-replica operation, production deployment, real PACS/DICOM/image diagnosis and clinical signing are excluded. These are outside the selected take-home scope. The design discusses upgrade paths; discussing an upgrade does not mean it is part of the submission.

**Completion statement:** the selected take-home application workflows and deliverables are implemented and have recorded verification. The remaining device evaluation and production exclusions above must stay visible in the submission note; this checklist does not assert perfect clinical accuracy or production readiness.


## Reviewer audit finding — 23 October 2026

The two semantic-validation defects reproduced in F09 of `FAILURE-AND-FIX-LOG.md` now have fixes and regression tests: wrong-sentence anatomy assignment and invented negation are rejected. The latest 283-test suite includes 36 connected workflows. Controlled browser name-recovery evidence is recorded separately in `verification/name-recovery-audit.json`. Human microphone evaluation and broader clinical semantic evaluation remain outstanding.
