# Project working rules

These user instructions apply throughout this project, including future sessions.

- Keep comments short and useful: explain a block's purpose or a non-obvious constraint. Do not narrate obvious code.
- Record each observed failure in `docs/FAILURE-AND-FIX-LOG.md`: what failed, when observed, impact, cause, fix, verification evidence, and remaining limitations. Never record secrets or real patient information.
- Do not silently skip failed steps, checks, or requested details. Resolve failures and rerun the affected verification. If blocked, record and report the exact blocker and unfinished work.
- Call a fix complete only after verification. Distinguish automated checks, controlled test inputs, live provider tests, and actual human/device tests.
- Before continuing work, read the failure log and relevant design/status documents. Preserve these instructions across context handovers; do not claim perfect memory of other projects.
- Update the testing guide and submission package when behavior or deliverables change. Use checks appropriate to the change; avoid irrelevant test repetition.

- Preserve STT/TTS free allowance: routine verification must use local mocks or text-only requests with speech muted/blocked. Reserve real voice-provider calls for necessary targeted checks or user demo/testing; do not repeatedly rehearse cloud audio. Report any actual voice-provider usage.
