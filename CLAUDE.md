# Climate Risk: working notes for Claude

Physical climate risk (extreme heat) proof of concept for European aerospace manufacturing sites, with a client dashboard. Two people work on this repo. Start with `README.md`, then `docs/concept.md` (framework, decisions log in §12).

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python scripts/build_dashboard.py   # rebuilds dashboard/index.html
node tests/dashboard_check.js                 # headless check of the built dashboard
```

Run pytest, and after any dashboard change the build and `dashboard_check.js`, before opening a PR.

## Branches and pull requests

- Never commit or push to `main`. Work on a branch, open a PR, and the other person reviews and merges.
- Keep a PR to one change. Commit subjects follow the existing style: area, colon, what changed, decision number if any, e.g. `Process lens: one running window for both lenses (D70)`.

## Decisions log

- Every method, metric or dashboard behaviour decision gets a row in `docs/concept.md` §12 with the next D-number. Reference it in the commit subject and in code comments where the code implements it.
- Before adding a row, check `main` for the latest number: both of us may add decisions in parallel. If two branches take the same number, the later merge renumbers and says so in the row (precedent: D67).
- When a decision changes an earlier one, say which ("amends D57", "replaces D64") rather than editing the old row.

## Generated files

- `dashboard/index.html` is built by `scripts/build_dashboard.py` from `dashboard/template.html`, the pipeline outputs and `config/settings.yaml`. Edit the template or the script, never `index.html`.
- `.gitattributes` marks `index.html` (and the concept pages) as binary. On a merge conflict, resolve the sources, rebuild, and commit the rebuilt file.
- `dashboard/data.json` and `dashboard/page.html` are build outputs and not committed (D69).
- The build reads gitignored inputs: `data/weather/future/` (from `scripts/phase2_future.py`), which in turn needs the hourly ERA5 files in `data/weather/hourly/` (from `scripts/fetch_era5.py`). Without them the build fails, even for a template-only change. `phase2_future.py --reuse-deltas` avoids the ~3 h NEX download. `docs/dashboard_ci_plan.md` plans to remove this dependency.

## Configuration and data

- Thresholds, operating hours, shifts, hall gains, risk bands, models, scenarios and periods live in `config/settings.yaml`. Read them through `climate_risk.config`; don't hardcode them (D69 point 7).
- Sites: `data/sites/pilot_aerospace_europe.csv`.

## Secrets and visibility

- The repo is **public**. ERA5 downloads need a Copernicus CDS key in the `CDSAPI_KEY` environment variable (cloud: an environment secret). Never commit it, `.cdsapirc` or `.env`, and never put it in a log or doc.
- Each person uses their own CDS account.
- Nothing client-confidential goes in the repo. Site locations are from public sources (OpenStreetMap).

## Writing

UK English, metric units, °C. Docs are prose with tables where the content is tabular. Keep the methodology docs consistent with the code: if a change alters a method, update the relevant `docs/` page in the same PR.
