# Connected workflow audit

23 October 2026. Latest local suite: **283 passed**, zero failures. See `verification/tests.xml`. The production frontend build also passed.

## Coverage

`backend/tests/test_connected_workflows.py` runs 36 connected flows: six patients, three starting states (unmatched name, suggested name, different patient already selected), and two requested modality scopes (latest available or CBCT).

Each flow checks unresolved-identity follow-up blocking, acknowledgements preserving pending state, service recreation with persisted state, bare full-name correction, original modality retention, a current-report cited summary, uncertain dictation, draft saving and history. It then switches patients and verifies old-patient draft saving and stale-context commands are rejected, subsequent evidence belongs to the new report, and a new session starts empty. Cloud model entry points fail immediately if called by this matrix.

Separate regressions cover misspelled/phonetic suggestions, exact directory IDs after zero matches, negative/unrelated replies, ambiguity, source-local anatomy and invented negation. A similarity score proposes confirmation; it never authorizes selecting an approximate patient match.

## Browser evidence

`verification/name-recovery-audit.json` and `name-recovery-audit.png` record the production UI in installed headless Chrome. Three injected final transcripts exercise the microphone-to-command path: “Hey, can you open Mira Yash report?”, “Thank you.”, then “Meera Iyer”. The correct IOPA opens after the explicit correction. A separate unknown-name request survives refresh, accepts a bare corrected full name, and restores chat and selection on another refresh.

The test intercepts voice WebSockets without connecting upstream, mutes spoken replies, and blocks/counts speech requests. Three controlled captures, zero speech requests and zero page errors were recorded. Routing uses the configured live LLM. This audit consumed **no STT/TTS provider quota**.

The first browser attempt timed out around creating a new session. The harness now waits for session creation and surfaces unsuccessful command responses instead of filtering only successful responses. The rerun passed; this timeout alone did not establish a backend failure. See F16 in the failure log.

## Limits

These checks establish tested application state transitions, not universal language understanding or clinical correctness. Human-name STT recognition, real microphone noise/accent behavior and audible device playback remain unverified here. Provider quota availability is not asserted. Previous live-provider evidence is historical and separately labeled. Production authentication, clinic authorization and deployment remain outside the local take-home scope.

## Collection scope regression

The later all-reports issue is recorded as F17. The final 283-test suite adds collection scope, source span/version validation, explicit partial failures, modality filtering, patient switching and locally stubbed spoken overview checks. `verification/all-reports-browser.json` reproduces the exact Priya selection, CBCT switch, all-reports summary, older citation preview, refresh and singular follow-up sequence. It records all three report IDs and no speech requests or browser errors. Text inference was live; STT/TTS were not invoked.

## Named conversational follow-ups

F18 demonstrates why the earlier workflow audit was insufficient: pronoun-based tests did not exercise names repeated in questions, or declarative rephrasings such as I asked. The expanded matrix crosses six patients, four phrasings and two proposed planner actions. Additional guards cover ambiguous first names, different/unknown/multiple names and requested modality mismatches. The exact live Rohan browser exchange now answers both questions from RPT-005-03 without reopening, preserves history, and rejects a different-patient follow-up. See `verification/named-followups-browser.json`. No STT/TTS was used. The resulting 283-test suite still does not prove all natural conversations work.

## Natural corrections and cache/history separation

F19/F20 are verified by the final 283-test suite and `verification/clarification-cache-browser.json`. The browser completed the exact Actually it is Priya Sharma OPG correction and a less direct CBCT correction, checked matching visible/header/config build IDs, proved identical fresh submissions have distinct turn IDs, and restored history on reload. The first build-label check exposed hidden footer CSS; moving the label into the header resolved it. No speech providers were called. Historical replies deliberately remain unchanged; this does not mean new requests use an answer cache.

## Provider-independent acknowledgements

F21 covers compound polite replies rather than a single thanks phrase. Ten phrasings across four session states are checked with every provider method blocked, alongside negative/mixed-task guards. The exact Okay thanks browser check and refresh passed without speech requests or page errors. Current complete suite: 283 passed. See `verification/acknowledgements-browser.json`; this does not prove upstream availability for inference-dependent commands.

The user's mixed thanks-plus-summary example was additionally verified through the command endpoint using spied fixture interpretation and answer methods: both receive the complete original message, the response contains current-report evidence and session context remains unchanged. Three mixed-request integration cases pass; the final full suite is 283 tests. No runtime change or external provider call was necessary for this check.


## Visible save feedback and reviewed plain-language output

The user supplied four natural voice conversations and Rohan draft screenshots. A read-only database observation found the matching draft saved at version 7. The issue was feedback outside the visible scrolled area. `verification/draft-save-feedback.json` uses an isolated fixture database and real API operations to verify adjacent save success, saved-button state, refresh, edits, unsupported edits and forced-503 retry. No provider calls are made by that check. The source transcript includes a harmless fixture article difference (No evidence of a fracture); the matching user draft without the article was independently observed as saved.

`verification/plain-language-browser.json` uses live text inference for the exact simple-language question and Arjun technique query, with speech blocked. Eight source-preservation/formatter regressions bring the local suite to 283. These checks do not establish every wording or actual human audio accuracy. User screenshots visibly disclose browser speech fallback; current cloud speech allowance remains unknown.
