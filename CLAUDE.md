# Climate Risk: working notes for Claude

Physical climate risk (extreme heat) proof of concept for European aerospace manufacturing sites, with a client dashboard. Two people work on this repo. Start with `README.md`, then `docs/concept.md` (framework, decisions log in §12). A new contributor's setup, the pipeline timings and the coordination rules are in `docs/onboarding.md`.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python scripts/render_dashboard.py  # page from the committed data.json (seconds, no pipeline)
.venv/bin/python scripts/build_dashboard.py   # rebuilds data.json from the pipeline outputs, then renders
node tests/dashboard_check.js                 # headless check of the rendered dashboard
```

Run pytest, and after any dashboard change the render and `dashboard_check.js`, before opening a PR. CI (`.github/workflows/dashboard.yml`) runs the same on every PR and attaches the built page as a workflow artefact.

## Branches and pull requests

- "main" below means the repo's default branch, whatever it is called (as at Nov 2026 it is `claude/peaceful-darwin-8w6ulr`; renaming it to `main` is planned). Check with `git ls-remote --symref origin HEAD`.
- Never commit or push to main. Work on a branch, open a PR, and the other person reviews and merges. Every merge to main publishes the dashboard to GitHub Pages.
- Keep a PR to one change. Commit subjects follow the existing style: area, colon, what changed, decision number if any, e.g. `Process lens: one running window for both lenses (D70)`.

## Decisions log

- Every method, metric or dashboard behaviour decision gets a row in `docs/concept.md` §12 with the next D-number. Reference it in the commit subject and in code comments where the code implements it.
- Before adding a row, check `main` for the latest number: both of us may add decisions in parallel. If two branches take the same number, the later merge renumbers and says so in the row (precedent: D67).
- When a decision changes an earlier one, say which ("amends D57", "replaces D64") rather than editing the old row.

## Generated files

The dashboard is built in two steps (D71):

- `scripts/build_dashboard.py` turns the pipeline outputs and `config/settings.yaml` into the data snapshot `dashboard/data.json`, which is **committed**. It needs gitignored inputs: `data/weather/future/` (from `scripts/phase2_future.py`, which needs the hourly ERA5 files from `scripts/fetch_era5.py`; `--reuse-deltas` skips the ~3 h NEX download).
- `scripts/render_dashboard.py` puts `data.json` into `dashboard/template.html` and writes `index.html` and `page.html`. Neither is committed; CI renders and publishes.
- Edit the template for layout and behaviour, and the build script for data. Never hand-edit `data.json`, `index.html` or `page.html`.
- Any change to sites, config, pipeline outputs or the data part of the build script must ship with a rebuilt `data.json` in the same PR. `tests/test_dashboard_data.py` fails if the snapshot's sites or key config values don't match the repo. A template change that reads a new data field also needs the rebuilt snapshot in the same PR.
- `.gitattributes` marks `data.json` (and the concept pages) as binary. On a merge conflict in it, resolve the sources, rerun `build_dashboard.py`, and commit the result.
- An older branch that still edits `dashboard/index.html` conflicts with its removal: run `git rm dashboard/index.html`, then rebuild `data.json` as above.
- Pipeline outputs (`outputs/`, `data/weather/`) can't be merged by hand. When a branch that changes outputs merges in a default branch that also changed them, rerun Phase 1, Phase 2 and the build **for all sites** after the merge: a method change on either side applies to every site. Then compare the result with both parents (unchanged sites against the default branch, the branch's own sites against the branch) before committing. The Augsburg merge (D73) is the worked example.
- Phase 1 downloads PVGIS again and rewrites the committed weather files. Restore anything that changes only because of that (see `docs/onboarding.md` §4) unless the PR is about it.

## Configuration and data

- Thresholds, operating hours, shifts, hall gains, risk bands, models, scenarios and periods live in `config/settings.yaml`. Read them through `climate_risk.config`; don't hardcode them (D69 point 7).
- Sites: `data/sites/pilot_aerospace_europe.csv`.

## Secrets and visibility

- The repo is **public**. ERA5 downloads need a Copernicus CDS key in the `CDSAPI_KEY` environment variable (cloud: an environment secret). Never commit it, `.cdsapirc` or `.env`, and never put it in a log or doc.
- Each person uses their own CDS account.
- Nothing client-confidential goes in the repo. Site locations are from public sources (OpenStreetMap).

## Writing

UK English, metric units, °C. Docs are prose with tables where the content is tabular. Keep the methodology docs consistent with the code: if a change alters a method, update the relevant `docs/` page in the same PR.
