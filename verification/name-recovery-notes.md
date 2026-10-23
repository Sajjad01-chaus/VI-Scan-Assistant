# Patient-name recovery: evidence and current scope

Updated 23 October 2026. The first reported failure was Aisha Khan transcribed as Ayesha Khan while an older Priya report remained visible. Later cases exposed lost corrections after zero matches and natural named replies. This overview points to preserved evidence; it does not claim the user's actual accent/microphone was reproduced.

## Current behavior

Approximate surname/first-name and consonant-key matches offer candidates for confirmation; they never authorize automatic selection. Pending identity pauses previous report follow-ups, clears stale evidence on a new response and gives the center an explicit identity state. No-match pending requests accept corrected exact directory full names/IDs without repeating open report. The requested modality is retained.

Direct names, IDs and supported conversational framing resolve locally. Eligible indirect named replies can use a structured text interpreter, then Python requires a verbatim name present in the reply and a unique pending-directory match. Questions, negative statements and ambiguous references cannot silently confirm. Yes resolves only one candidate; no declines without discarding the original request. Supported pure thanks preserves pending state; mixed thanks plus a task is not treated as a closing.

Unique matching named questions use the selected patient's report; repeating the question is not an open-report action. Different patients or modalities require explicit source resolution. Two Priyas remain ambiguous when only Priya is spoken.

## Execution evidence

- Earlier Ayesha/Aisha UI/layout checks: `name-recovery-browser.json`, `spoken-confirmation-browser.json`, `browser-smoke.json`. The older spoken-confirmation artifact used live TTS with controlled STT text.
- Controlled Mira Yash -> thanks -> Meera Iyer capture path, zero-match correction, refresh and history: `name-recovery-audit.json`. Voice WebSockets were intercepted with no upstream STT and speech was blocked.
- Named Rohan findings questions and repeated wording: `named-followups-browser.json`, using live text inference only.
- Actually it is Priya Sharma and indirect corrections retaining OPG/CBCT: `clarification-cache-browser.json`, using live text interpretation and blocked speech.
- Pure/compound acknowledgements: `acknowledgements-browser.json`, using local replies and no speech calls.

The current suite has 283 passing local tests in `tests.xml`; earlier evidence counts belong to their original runs. Read [the workflow audit](../docs/WORKFLOW-AUDIT.md), [failure history](../docs/FAILURE-AND-FIX-LOG.md) and [manual rehearsal](../docs/FINAL-REHEARSAL.md) for details. Human recognition/audibility, general accent robustness and universal conversational accuracy remain unverified. No provider call was made for this documentation refresh.
