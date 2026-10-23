# Documentation index

Current implementation snapshot: 23 October 2026. Start with the repository [README](../README.md), then choose the document below. The current recorded unit/API suite has **283 passing tests**. Test counts are historical inside the failure log and raw experiment records; the latest suite is in `../verification/tests.xml`.

## Reviewer essentials

- [Implemented system design](system-design.md): actual architecture, function calling versus deterministic operations, clarification/conversation scope, drafts, voice protocol, schema, persistence, authorization and cost/latency limits.
- [One-page architecture PDF](architecture-one-page.pdf): one-page landscape architecture explanation: connected components, explicit adapter links, numbered retrieval/dictation/follow-up flows and a short validation-boundary explanation.
- [Implementation and verification status](implementation-status.md): implemented features, execution types, historical versus current evidence, and unfinished candidate/production work.
- [Requirement coverage](REQUIREMENTS-CHECKLIST.md): mandatory workflows, chosen report-chat bonus, technical expectations and deliverables.
- [Submission note](submission-note.md): candidate draft; replace link placeholders and update actual human-device/demo results before sending.

## Testing and demonstration

- [Complete ordered rehearsal](FINAL-REHEARSAL.md): one silent end-to-end pass, expected results and additional conversational/clinical cases.
- [Four-minute recording script](FOUR-MINUTE-DEMO.md): exact commands, actions, timing, narration and failure contingencies. A script is not a completed recording.
- [Detailed UI test catalog](UI-TESTING-GUIDE.md): focused checks for recovery, evidence, export/save, voice, interruptions and later fixes.
- [Demo evidence](demo.md): actual API outputs and browser/provider artifacts, separated from recording plans.
- [Connected workflow audit](WORKFLOW-AUDIT.md): stateful/natural-language regressions and execution limits.
- [Grounded-answer behavior](answer-quality.md): exact quotations, conservative formatting, diagnosis/cause limits and collection scope.
- [Failure and fix log](FAILURE-AND-FIX-LOG.md): observed defects, failed checks, resolutions and known limitations; historical evidence is preserved.
- [Initial provider experiments](../verification/model-selection.md): small historical synthetic benchmark, not current quota/access or human accuracy.
- [Name-recovery evidence overview](../verification/name-recovery-notes.md): earlier UI/name experiments and later recovery/clarification changes.

## Portable diagrams and editable sources

- System: [PNG](diagrams/system-architecture.png), [SVG](diagrams/system-architecture.svg), [Mermaid](diagrams/system-architecture.mmd).
- Retrieval/conversation: [PNG](diagrams/retrieval-workflow.png), [SVG](diagrams/retrieval-workflow.svg), [Mermaid](diagrams/retrieval.mmd).
- Dictation/review: [PNG](diagrams/dictation-workflow.png), [SVG](diagrams/dictation-workflow.svg), [Mermaid](diagrams/dictation.mmd).
- Voice lifecycle/fallback: [PNG](diagrams/voice-workflow.png), [SVG](diagrams/voice-workflow.svg), [sequence source](diagrams/voice-sequence.mmd), [state source](diagrams/voice-state.mmd).
- [Data model](diagrams/data-model.mmd) reflects the actual database entities and JSON storage boundaries.

Mermaid blocks in system-design.md are canonical for the six `.mmd` files. SVG/PNG files are simplified portable summaries, not literal renderings of each Mermaid graph. `build_design_artifacts.py` regenerates Mermaid/SVG and invokes `render_design_artifacts.cjs` for all PNG diagrams and the one-page diagram-first PDF. The renderer uses the frontend's Playwright and an installed Chrome via CHROME_PATH; PDF text and diagram paths remain selectable/vector-based. These are documentation tools, not runtime app dependencies.

## Documentation maintenance

Run `python docs/check_documentation.py` from the repository root after edits. It checks local Markdown links, canonical Mermaid synchronization and current test-count references against recorded JUnit evidence. It does not rerun clinical/voice tests, validate external sites or establish current provider health. The latest check is saved in `verification/documentation-check.json`.

Preserve old measurements and failure observations; update current summaries and add resolution notes rather than replacing historical evidence. After any package changes, rerun `python scripts/package_submission.py` to refresh the source ZIP and secret/exclusion/CRC checks. No keys or runtime database should be packaged.
