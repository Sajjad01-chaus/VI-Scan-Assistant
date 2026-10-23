# Provider experiments

These optional scripts produced the historical provider comparisons in `verification/`. They are separate from the application runtime and automated test suite. They locate the project root relative to their file, read the local `.env`, and may consume real provider quota when executed.

Run them explicitly from the project root with Python or Node. Do not run all scripts as a routine check. Historical model availability, latency and quota results are not current guarantees. Generated comparison audio is kept locally; only the synthetic input clips and audio fixtures required by browser checks are committed.
