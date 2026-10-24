# Completed research report

- PDF: `../../output/pdf/option_pricing_hedging_research_report.pdf` (12 pages).
- Editable content: `research_report.md`, generated from `build_report.py`.
- Worked application: `../../docs/USE_CASE_TH.md`.
- Five-minute demonstration: `../../docs/DEMO_SCRIPT_TH.md`.
- Evidence QA: `../verification/final-report-evidence.json`.
- New pricing/hedge archived-source replay: `../verification/contract-review-replay.json`.
- Document input/output hashes: `report_manifest.json`.

Run `verify_evidence.py` with the project Python and `PYTHONPATH=src` before building.
Build with a Python containing ReportLab and Pillow. This is document generation,
not a replacement pricing engine. On this host those libraries are in the Codex
bundled runtime; they are not added to the financial package's runtime dependencies.

The report summarizes saved experiments; it does not overwrite or regenerate them.
Older runs keep their original manifests and limitations. The hypothetical contract
review uses existing pricing/MC/hedge APIs and three predeclared configs under
`configs/contract_review_*.toml`; its outputs are in `../examples/contract-review/`.

Milestone 6 completes the original model-study/report scope. Market quote ingestion,
implied-volatility inversion, American exercise, dividends and production execution
are not implemented. See the practical guide for what is usable within the present
model and what a subsequent contract-aware extension must validate.
