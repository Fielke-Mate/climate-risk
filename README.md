# Climate Risk

A physical climate risk assessment tool for sustainability consultants, with a shareable client dashboard.

The first focus is **extreme heat**: risk to **worker health and productivity** and to **production processes** that can't run above certain operating conditions. Outputs are built to support disclosures under **IFRS S2 (ISSB)** and **ESRS E1 (CSRD)**.

- Concept & framework: [`docs/concept.md`](docs/concept.md)
- Weather summary dashboard design: [`docs/weather_summary_dashboard.md`](docs/weather_summary_dashboard.md)
- Phase 1 (historical weather files): [`docs/phase1/README.md`](docs/phase1/README.md)
- Phase 2 (future weather files): [`docs/phase2/README.md`](docs/phase2/README.md)
- Phase 3 (heat-stress metrics): [`docs/phase3/README.md`](docs/phase3/README.md)
- Code review and functional test (Nov 2026): [`docs/code_review_2026-11.md`](docs/code_review_2026-11.md)
- Methodology review (building services): [`docs/methodology_review.md`](docs/methodology_review.md)
- Methodology review (climate science: future hot years and amplified extremes): [`docs/climate_science_review.md`](docs/climate_science_review.md)
- Dashboard prototype: `dashboard/index.html` (self-contained; open in a browser or host on GitHub Pages). Rebuild with `scripts/build_dashboard.py`, which also writes `dashboard/data.json` (the data, for inspection) and `dashboard/page.html` (for publishing as a claude.ai page); those two are build outputs and not committed (D69).
- Process-limit lens (D66, dashboard "Heat risk to: Processes"): [`docs/process_lens_plan.md`](docs/process_lens_plan.md)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

ERA5 downloads need a free Copernicus CDS account. Put the API key in the `CDSAPI_KEY` environment variable (cloud: an environment secret). Never commit it.

## Workflow

```bash
.venv/bin/python scripts/fetch_era5.py       # ERA5 2000-2025
.venv/bin/python scripts/fetch_nex.py        # climate model data, resumable (~3 h); Phase 1 needs it for the 2000-2025 adjustment
.venv/bin/python scripts/phase1_historical.py   # --reuse-adjustment skips the model data
.venv/bin/python scripts/phase2_future.py       # --reuse-deltas skips the model data
.venv/bin/python -m pytest
node tests/dashboard_check.js   # browser test of dashboard/index.html (needs Playwright)
```

Settings (baseline years, operating hours, thresholds, heatwave definitions) live in `config/settings.yaml`.

Behind a proxy that re-signs TLS (as in the cloud environment), point Python at its CA bundle for the NEX download, e.g. `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt`. Sites live in `data/sites/pilot_aerospace_europe.csv`.
