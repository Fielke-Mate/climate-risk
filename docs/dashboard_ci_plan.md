# Dashboard build in CI (D71)

**Status, Nov 2026:** steps 1–4 and 7 are implemented. Steps 5 and 6 are repository settings that the owner has to make (see the end of this page). Accepted: the dashboard gets a public Pages address.

## Recommendation

Split `scripts/build_dashboard.py` into a **data step** that stays local and a **render step** that GitHub Actions runs. Commit `dashboard/data.json` as the versioned data snapshot and stop committing `dashboard/index.html`. CI renders the page, runs the dashboard check on every PR, and publishes `main` to GitHub Pages.

This removes the main source of merge conflicts and means a template change no longer needs the full pipeline on the editor's machine.

## Why not a full build in CI

The build reads `data/weather/future/`: 15 sites × 6 models × 2 scenarios × 2 periods × 3 year types, so 1,080 parquet files. At the size of the committed TMYs (about 0.55 MB each) that is roughly 600 MB. This is an estimate, because the files aren't in this checkout. They come from `phase2_future.py`, which needs the hourly ERA5 record and so a CDS key. A CI build would need that set stored somewhere (for example as a release asset), re-uploaded after every Phase 2 run, and downloaded on every job. That's too much moving parts for what it buys.

## Why the split is worth it

Of the 36 commits that changed `index.html` up to D70, 22 changed only `template.html`, 11 changed pipeline outputs, the build script or config, and 3 were rebuilds with no source change. Under the split, the 22 template-only changes touch only `template.html`, a 142 kB text file that git can merge. Only the 11 data-driven changes touch the generated `data.json`.

## Steps

1. **Split the build.** Add `scripts/render_dashboard.py`, using the standard library only: it reads `template.html`, `data.json` and the fonts, and writes `index.html` and `page.html` (the current lines 410–422 of `build_dashboard.py`). `build_dashboard.py` writes `data.json` and then calls the render, so running it locally behaves as today.
2. **Make `data.json` deterministic.** The only time-dependent field was `meta.generated` (today's date). A rebuild now keeps the previous date when the rest of the data is unchanged. The key order follows the code, the basemap is cached in `dashboard/basemap.json`, and values are rounded. The data step could not be run twice here because the future weather files aren't in this checkout, so the first local rebuild should confirm that `git status` shows `data.json` unchanged.
3. **Swap what is committed.** Commit `data.json` and remove `index.html` from git (`git rm --cached`, add to `.gitignore`). Move the `.gitattributes` line from `index.html` to `data.json`. Record this as a new decision that amends D69 point 9.
4. **Add the workflow** `.github/workflows/dashboard.yml`, with action versions pinned. The repo has no `main` branch (the default branch is `claude/peaceful-darwin-8w6ulr`), so the workflow publishes whichever branch is the default:
   - On `pull_request`: install, run `pytest`, render, run `node tests/dashboard_check.js` with the runner's Playwright, and upload `index.html` as a workflow artefact so the reviewer can open the built page.
   - On `push` to `main`: render, check, and deploy with `actions/upload-pages-artifact` and `actions/deploy-pages`.
   - `pytest` runs on committed data. `test_ladder.py` reads `outputs/phase1/`, which is committed, and skips if it's missing.
   - Added in implementation: `tests/test_dashboard_data.py` fails when `data.json` disagrees with the sites list or config, so a new site (e.g. the Augsburg branch) can't be published on a stale snapshot.
5. **Enable Pages.** Settings → Pages → Source: GitHub Actions. This is free because the repo is public.
6. **Protect `main`.** Require a PR, one approval and the dashboard workflow passing. This is free on a public repo.
7. **Update the docs.** Change the README build section and the "Generated files" section of `CLAUDE.md`. Publishing to claude.ai stays manual: run the render locally (seconds, no pipeline inputs) and publish `page.html`.

Estimated effort is half a day to a day. Most of the uncertainty is in step 2.

## Risks and open points

- **Schema skew.** If a template change reads a new data field, it must ship in the same PR as the regenerated `data.json`. The dashboard check fails on "undefined"/"NaN" text, so CI should catch a mismatch, but only where the field reaches visible text.
- **Data conflicts remain** when both people change data in parallel. You resolve them by rebuilding the data step, which needs the full pipeline inputs. This is rarer than today but not gone.
- **Public URL.** Pages gives the dashboard a stable public address. The content is already public in the repo and the sites are from OpenStreetMap, but a client-facing URL is more discoverable. Decide before step 5 whether that's acceptable, or whether claude.ai remains the only place the dashboard is published.
- **Repository growth.** A 7 MB `data.json` per data change grows the history at about the same rate as `index.html` does now, so there's no improvement there and nothing gets worse.

## Owner actions to finish

1. **Enable Pages:** Settings → Pages → Build and deployment → Source: **GitHub Actions**. Until then the deploy job fails; the check job is unaffected.
2. **Rename the default branch to `main`** (recommended): Settings → General → Default branch → rename `claude/peaceful-darwin-8w6ulr`. GitHub retargets open PRs and redirects the old name. The workflow follows the default branch either way, but `CLAUDE.md` and PR habits read better with `main`.
3. **Protect it:** Settings → Rules → Rulesets → New branch ruleset on the default branch: require a pull request with 1 approval, and require the status check `check`. Add the check after the workflow's first run, which is when it becomes selectable.
