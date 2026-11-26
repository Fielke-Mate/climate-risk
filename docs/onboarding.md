# Onboarding: working on climate-risk

For a new contributor and their Claude Code session. Written Nov 2026; the timings and the NEX outage below are as at that date.

## Paste this into your first Claude Code session

> Read `docs/onboarding.md` and `CLAUDE.md` in this repository and follow them for the rest of the session. Then do the "First session" checks in `docs/onboarding.md`, report the results, and tell me which of the pipeline inputs are present in this environment. Don't change any files yet.

## 1. Access

- You are a collaborator with write access on `Fielke-Mate/climate-risk`. The repo is **public**: anything you push is visible to anyone.
- The default branch is `claude/peaceful-darwin-8w6ulr` (a rename to `main` is planned). Every merge to it publishes the dashboard to GitHub Pages, so nothing goes to it except through a reviewed PR.

## 2. Set up Claude Code

**On the web (claude.ai/code), recommended.**

1. Sign in with your own Claude account and connect your own GitHub account when asked.
2. Create a personal environment for this repo:
   - **Environment variable:** `CDSAPI_KEY` = your own Copernicus CDS API key. Register free at the Copernicus Climate Data Store and accept the ERA5 licence. Never paste the key into a chat, file or commit.
   - **Network:** limited, with package managers allowed, plus these hosts:
     - `cds.climate.copernicus.eu` (ERA5)
     - `re.jrc.ec.europa.eu` (PVGIS cross-check)
     - `ds.nccs.nasa.gov` (NEX climate-model data; see the outage note in §4)
     - `cdn.jsdelivr.net` (only if `dashboard/basemap.json` is ever deleted)
   - **Setup script:**
     ```bash
     if [ -d climate-risk ]; then (cd climate-risk && python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]"); fi
     ```
3. Start sessions on that environment with the repository selected.

The repo owner's environment and key are not shared with you. Each person uses their own.

**Locally.** Clone the repo, run the README setup, and export `CDSAPI_KEY` in your shell. The browser check needs Node and Playwright (`npm install --no-save playwright && npx playwright install chromium`).

## 3. First session: checks that need no keys or data

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/render_dashboard.py
node tests/dashboard_check.js
```

All three should pass on a fresh clone: pytest, the render (seconds), and the headless dashboard check (a few minutes). With only this you can work on anything in `dashboard/template.html`, the docs, and code covered by tests.

## 4. Pipeline inputs, for data work

Any change to sites, config, `src/climate_risk/` metrics or the data part of `scripts/build_dashboard.py` needs the gitignored pipeline inputs, so that you can rebuild `dashboard/data.json`. Measured in a 4-core cloud session for 16 sites (Nov 2026), about 28 minutes in all:

| Step | Command | Time |
|---|---|---|
| ERA5 hourly records (needs `CDSAPI_KEY`) | `.venv/bin/python scripts/fetch_era5.py --workers 8` | ~1 min |
| Phase 1: historical files and outputs | `.venv/bin/python scripts/phase1_historical.py --reuse-adjustment --workers 4` | ~2.5 min |
| Phase 2: future files and outputs | `.venv/bin/python scripts/phase2_future.py --reuse-deltas --workers 4` | ~16 min |
| Dashboard data and page | `.venv/bin/python scripts/build_dashboard.py` | ~8 min |

`--reuse-adjustment` and `--reuse-deltas` take the climate-model results from committed files, so the NEX download (~3 h) is only needed for a new site's own model data or a change in the model method.

After running these steps on unchanged code, `git status` should show no changes except the four notes below. If anything else changed, stop and find out why before committing.

1. **PVGIS.** Phase 1 downloads the PVGIS typical year again. As at Nov 2026, PVGIS returns a different year from the committed files (different source months; annual means 0.2–0.9 °C apart). It is only a cross-check, so restore it unless the PR is deliberately updating it: `git checkout -- data/weather/pvgis outputs/phase1/monthly_crosscheck.csv docs/phase1/figures/monthly_temperature_crosscheck.png`.
2. **Weather files rewritten byte-wise.** Phase 1 rewrites `data/weather/{tmy,hot_year,extreme_year}` with identical contents but different file metadata. Restore them the same way if `git diff` lists them.
3. **`data.json`** keeps its `generated` date when the data hasn't changed (D71).
4. **NEX outage.** The NCCS THREDDS server failed every data request in Nov 2026. Augsburg borrows Donauwörth's model cell until it works again (D73; config `future.nex_proxy`).

## 5. Working together

- Before starting data work, tell the other person, so that two branches don't regenerate outputs in parallel. Template, docs and code changes can run in parallel freely.
- Branch from the latest default branch. If it moves while you work, merge it into your branch before opening the PR. If your branch changes outputs, rerun Phase 1, Phase 2 and the build **for all sites** after that merge: a method change on the default branch applies to your site too, and the output files can't be merged by hand.
- Take the next D-number when you open the PR, not when you start. If the other branch merges first with the same number, renumber yours and say so in the row (precedents: D67, D73).
- Keep PRs to one change. CI must pass, and the other person reviews and merges. The PR's CI run attaches the built page as a downloadable artefact for review.
- Everything else (decision log, generated files, secrets, writing style) is in `CLAUDE.md`.
