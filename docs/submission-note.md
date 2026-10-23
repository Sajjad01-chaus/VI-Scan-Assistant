Hello VI-SCAN team,

Please find my synthetic-data clinical assistant proof of concept at: [insert repository or ZIP link]. Demo evidence: [insert video link, or point to docs/demo.md and verification/api-demo.json in the repository].

The application supports voice/text report retrieval with explicit patient disambiguation and conversational correction, source-cited report questions, single/all-report summaries, and editable structured dictation drafts. Python validates identity, source evidence, uncertainty/negation and draft/context versions separately from LLM interpretation. Every saved draft still requires clinician review.

The stack is FastAPI, React/TypeScript and SQLite, with Google streaming STT, Groq LLM/speech and documented fallbacks. A clearly labeled fixture mode supports evaluation without keys or a GPU. The package includes setup/lockfiles, a one-page architecture, editable diagrams, provider experiments, failure-and-fix records, a documented API demo and 283 passing local automated tests.

Known limits: this is a local synthetic-data proof of concept, without imaging diagnosis, clinical signing or production clinic authorization. Voice interaction is turn-based, with automatic pause submission and manual controls. Historical synthetic voice tests succeeded, but provider quota failures were also observed; the latest conversational regressions intentionally avoided speech calls. Human microphone/accent/audibility evaluation and the planned recorded demo should be described according to what I actually complete before sending this note.

With additional time I would expand real-device synthetic voice and adversarial conversational/clinical evaluation, improve endpointing and privacy/retention controls, and add production identity/clinic authorization and operational monitoring.

Thank you for reviewing my submission.

Candidate checklist before sending: replace both link placeholders, verify link access, update the human-device/demo sentence to match actual results, and attach no API keys or runtime database. This draft has not been sent automatically.
