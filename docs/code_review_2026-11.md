# Code Review and Functional Test (Nov 2026)

Prompted by a report that the map showed nothing for "Today".

## How it was tested

- **Browser test** (`tests/dashboard_check.js`, headless Chromium). It drives every combination of scenario, period, year type, exposure, hall heat gain and map layer, plus every tab, every site, the filters ("only", none, reset), the search box, hash navigation, stale settings stored by older page versions and phone width. That's 492 states. It fails on page errors, "undefined"/"NaN" text, uncoloured markers, missing explanations and sideways scrolling.
- **Python tests** (`pytest`, 19 tests), including a new test for the typical-year December → January join that fails on the old code and passes on the fix.
- **Code read-through** of the dashboard template and the `climate_risk` package.

## Findings and fixes

| # | Finding | Severity | Fix |
|---|---|---|---|
| 1 | **Map grey in "Today" with no explanation.** The two change layers ("Extra days above 30 °C vs today", "Warming") have no value for today, so every marker turned grey. Because the page remembers the last layer, this persisted across visits. This is the reported bug. | High (looks broken) | A message on the map explains why, with a "Show 2050" button; the ranking says the same; the layer names say "(2040 / 2050)". |
| 2 | **Overlapping markers could not be clicked.** At this scale Getafe sat under Illescas, Saint-Nazaire under Nantes, and Stade / Nordenham under Bremen / Hamburg. | Medium | Overlapping markers are nudged apart; a short leader line and dot mark each true location. |
| 3 | **Stored settings not validated.** A value saved by an older page version (e.g. an old tab or exposure name) could break the site card. | Medium | Every remembered setting is checked against the allowed values. |
| 4 | **Typical-year December → January join.** The ±8 h smoothing blended December with the January *before* it (and January with the December after it). It only affected ~16 hours a year, but it was wrong. | Low (data) | The join now uses the adjacent months; new test `test_dec_jan_join_blends_with_the_adjacent_months`. All phases re-run. |
| 5 | **Search text inserted as HTML.** Typing markup in the site search was put into the page unescaped (self-only, no data at risk). | Low | Text is escaped. |
| 6 | **Dead code** from the earlier per-tab exposure buttons. | Low | Removed. |
| 7 | **Misleading column names**: `*wbgt_shade*` now means indoor (no sun, indoor air speed). | Low (clarity) | Documented in `annual.py`. A rename can follow with the next schema change. |

## Checked and found sound

- Unit conversions, ERA5 accumulation timing, solar position (mid-hour, numba mode), operating-hours mask across midnight and DST, quantile morphing and its tests, delta ratios and limits, ensemble statistics, dashboard value lookups for every metric used.
- With all sites filtered out, the map, ranking and headline tiles show empty states without errors.

## How to re-run

```bash
.venv/bin/python -m pytest
node tests/dashboard_check.js
```
