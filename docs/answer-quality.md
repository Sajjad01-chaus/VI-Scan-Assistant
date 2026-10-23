# Concise grounded answers

The original summary route replaced the user's full request with “Summarize this report”, dropping secondary questions. It also rendered up to six excerpts as a single response. The current implementation sends the original question plus a separate summary flag, requests at most three short evidence sentences labeled finding/limitation/next_step/cause, and renders a principal finding plus one caveat for summaries.

Python, in `backend/app/answers.py`, verifies verbatim source membership and preserves original quotations/offsets for citations. Model-authored prose is never displayed or spoken. Readability uses a small controlled formatter: a radiolucency term can be explained as a darker area, caries as tooth decay, and the specific superimposition/apices limitation as overlapping structures limiting root-tip assessment. Negation and uncertainty remain in the source-based response. These substitutions are not a validated clinical language engine.

Terminology references:
- American Association of Endodontists, radiolucent appearances: https://www.aae.org/specialty/a-concise-guide-to-pathology-within-endodontics/
- NLM-hosted radiologic diagnosis discussion of periapical tissues/root apices: https://www.ncbi.nlm.nih.gov/books/NBK448020/pdf/Bookshelf_NBK448020.pdf
- American Dental Association patient terminology for tooth decay: https://www.mouthhealthy.org/all-topics-a-z/cavities/

If the user asks for a cause, a finding cannot become an etiology: Python accepts a cause excerpt only when the source uses explicit causal language and does not negate or qualify it. Otherwise the answer states that the cited findings do not establish the underlying cause. This may abstain on a supported cause phrased outside the narrow recognized patterns; that is a conservative limit, not universal causal understanding.

A live follow-up exposed another weakness: a model returned genuine but unrelated excerpts for a cancer-confirmation question. A bounded lexical target check for common diagnosis-question forms now requires source/topic support and relevant excerpts, otherwise abstaining. This is not complete semantic entailment, diagnostic interpretation or an exhaustive question parser. All source text remains synthetic. The two separate editable-finding defects in failure-log F09 now have source-local anatomy and invented-negation guards with regression tests; broader clinical semantic validation remains future work.

Verification: unit/API regressions, live browser request/response and automatic playback checks are captured in `verification/tests.xml` and `verification/concise-summary-cause.json`. The before-fix unrelated-answer case is retained in `verification/answer-quality-failure.json` for transparency.


Final verification note: live text-answer browser checks pass. An earlier actual cloud-playing run is preserved as `concise-summary-cause-cloud-pass.json`; final cloud attempts encountered real TTS quota limits. The latest answer evidence is `concise-summary-cause.json` with speech explicitly disabled, and fallback integration is checked separately with controlled speech APIs. See failure-log F14. This distinction is intentional; quota failures are not relabeled as successful live audio tests.

F15 correction: general have/has questions are not automatically diagnosis questions. Auxiliary forms such as “Have you found...” and generic finding/observation objects are excluded from diagnosis-target extraction. The exact Meera exchange passed in text-only mode with zero speech-provider calls; see `verification/meera-key-findings.json`.


## Current conversation and collection scope

Named follow-ups that uniquely identify the selected patient may answer its report; ambiguous/different names or modality mismatches require clarification. A repeated content question must not become retrieval. Whole-message pure thanks is local, while mixed thanks-plus-question text reaches interpretation intact. Pending identity blocks prior-report answers.

Explicit all-report summaries list only the resolved patient's matching reports, validate every source independently and preserve active selection. The result labels dates/modalities and failed IDs when incomplete. At most three answer calls run concurrently. There is no cross-report inference of progression. Collection audio is a disclosed short overview; original per-report evidence remains on screen.

See [current status](implementation-status.md), [workflow audit](WORKFLOW-AUDIT.md) and the full failure log for F16-F21 and their execution limits. The latest local suite has 283 passing tests; live text/controlled transcript checks are separate from historical cloud audio or actual human-device validation.


## Final plain-language pass

The formatter now handles a bounded set of exact/anchored report sentences: horizontally impacted/partly erupted lower third molars, an uncertain inferior-alveolar-canal relationship, the specific no-definite-carious-lesion caveat and the mock panoramic technique sentence. It does not paraphrase arbitrary medical text or remove qualifiers. Original quote, ID/version and offsets remain unchanged. Technique wording explicitly describes the mock report, not an actually acquired image. Cause requests can include selected finding/next-step evidence without treating a finding as an etiology.

Terminology references reviewed for these limited mappings:

- [NHS inform: wisdom teeth and third molars](https://www.nhsinform.scot/tests-and-treatments/dental-treatments/wisdom-tooth-removal/).
- [Health New Zealand: panoramic/OPG terminology](https://www.healthnz.govt.nz/hospitals-services/hospitals/wellington-hutt-and-kapiti/bee-healthy-regional-dental-service/opg-x-ray).
- [Royal College of Surgeons: third-molar guidance and inferior dental canal anatomy](https://www.rcseng.ac.uk/-/media/Files/RCS/FDS/Guidelines/3rd-molar-guidelines--April-2021-v4.pdf).

These references support terminology only; they are not patient-specific evidence or a recommendation to treat. `verification/plain-language-browser.json` records the actual text-only simple-word/technique check. Unknown sentence forms remain source wording. Universal clinical semantic correctness remains unverified.
