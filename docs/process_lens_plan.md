# Process-limit lens: plan and mock-up (draft v2, Nov 2026)

A second way to read the dashboard: instead of worker heat stress (WBGT against an ISO 7243 reference), the user sets a **dry-bulb process limit** (paint application, sealant, composite layup, chiller rating, anything) and sees the same headline, map, ranking and Summary cards in terms of **hours of process downtime**: operating hours with hall air above the limit. Hours are the driver throughout, so a later version can attach a value per hour (€ of lost output) without changing the charts. Layout, controls, year colours and the nine-year structure (typical / hot / extreme × today / 2040 / 2050) stay as they are, so the two lenses can be toggled without the page moving.

Renders: `docs/mockups/process_lens/` (built on the current dashboard, D61–D65). Numbers in the renders are illustrative (see "Mock-up caveats").

| Render | Shows |
|---|---|
| `01_overview_sevilla.png` | Whole page in the process lens: header toggle, View bar, KPI tiles, map, Summary |
| `02_summary_ladder_sevilla.png` | Summary tab, downtime card drawn as a limit ladder |
| `03_summary_bridge_sevilla.png` | Summary tab, downtime card drawn as a downtime bridge (recommended) |
| `04_summary_ladder_toulouse_extreme.png` | Ladder at a temperate site, Year = Extreme |
| `06_summary_bridge_toulouse_extreme.png` | Bridge at a temperate site, Year = Extreme |
| `05_worker_lens_unchanged.png` | Worker lens after the toggle is added: unchanged apart from the toggle |

## 1. Controls

- **Header: "Heat risk to  Workers | Processes".** One toggle, remembered per viewer. Everything below follows it.
- **View bar, process lens:** Scenario, Period, Year (typical / hot / extreme) and Hall gain stay. **Exposure** and **Worker** are hidden: sun does not change air temperature, and the worker profile has no meaning here. Three controls take their place:
  - **Process**: presets with their limit (paint / coating 35 °C, sealant / adhesive 30 °C, composite layup room 32 °C, chiller rated ambient 38 °C, all placeholders until real specifications arrive) plus "Custom".
  - **Limit**: a stepper, 20–45 °C in 0.5 °C steps. Typing or stepping to a value that no preset uses switches the preset to "Custom".
  - **Runs**: 06–22 (the working hours, as now) or 24 h, for continuous processes. In 24 h mode the night shift counts in the totals.
- **Hall gain applies to the process**: the process sits in the hall, so the limit is tested against hall air (outdoor + 0 / 2 / 4 °C). For dry bulb this is exact: hours above 35 °C with a +2 °C hall = outdoor hours above 33 °C.

## 2. What each element becomes

| Element | Worker lens (now) | Process lens |
|---|---|---|
| KPI tile 1 | Sites at high risk · worker heat-safety days | Sites at high risk · **downtime hours** (placeholder bands: High 100–249 h, Very high 250+ h a year) |
| KPI tile 2 | Working time over the safe limit | **Process downtime**, hours a year summed over sites, % change vs today |
| Map "Colour by" | Worker days, days > 30 °C, WBGT degree-hours, extra days > 30 °C, warming | **Downtime hours** (default), **extra downtime hours vs today**, process-stop days, days > 30 °C, warming |
| Summary card 1 | Working hours above WBGT ref by shift, nine years | **Downtime hours by shift, nine years**. Headline in hours: typical / hot / extreme, today vs future, late-shift share. Stop days drop to the sub-line. Same chart, same footnote |
| Summary card 2 | Climate here (UTCI bands) | **Downtime card**: callout strip + downtime bridge (section 3) |
| Summary card 3 | Thermal comfort shift (UTCI) | **When the limit is exceeded, month × hour** (section 3) |
| Indicators | Dot timeline, worker / heat / heatwave / comfort groups | Process group replaces the worker group: stop days, operating hours above, longest run, degree-hours above the limit, 1 % design temperature, hottest operating hour. Heat, heatwave and energy groups unchanged |
| Temperature | Distribution, warming fingerprint, monthly Tmax | Unchanged, plus the limit as a vertical line on the temperature distribution |
| Heat stress tab | WBGT by shift, UTCI | Renamed **Process** in this lens: hours above the limit by shift (table with model ranges) and the current placeholder process table |
| About | Method | Adds the process-lens definitions below |

**Definitions.** An *operating hour above the limit* is an hour in the running window with hall air above the limit. A *process-stop day* is a day with at least one such hour, matching the worker heat-safety day (D57). Both come from the same 11-year statistics as the worker numbers (median year for typical, 90th percentile for hot, the extreme reference year), with the 6-model median and range.

## 3. Summary cards 2 and 3

The two UTCI cards answer "how comfortable is it here", which has no meaning for a process. After review (v1 → v2): the line chart's message is kept but redrawn, a downtime callout is added, and the month × hour grid stays.

**Card 2: downtime at the limit.** Three parts.

1. **Headline** in hours. Sevilla, 35 °C, typical: *a typical year costs 266 hours of downtime today and 385 h by 2050: about 8,270 h in total from 2026 to 2050. 1.3 °C more process tolerance or hall cooling would hold 2050 at today's level; each extra 1 °C saves about 103 h a year by 2050.*
2. **Callout strip**: downtime a year today / 2040 / 2050 in the year colours, and a darker tile with the **2026–2050 total**. The total always uses typical years: adding up 25 extreme years is not a scenario. Years between the reference points are interpolated linearly (today = 2020, then 2040, then 2050). This is the number a revenue figure will multiply later.
3. **Visual**, replacing the exceedance curve. Two drawings of the same data:
   - **Downtime bridge (recommended).** Waterfall: today → added by climate to 2040 → added to 2050 → 2050 total → hours bought back by +1, +2, +3 °C of tolerance or cooling → 2050 with +3 °C. It reads as a ledger of hours: what climate change adds, and what each degree of engineering buys back. That is the shape a revenue or cost-benefit view takes later (hours × €/h on each step).
   - **Limit ladder (alternative).** Grouped columns of downtime for limits from 3 °C below to 3 °C above yours (today, 2040, 2050 per limit), your limit shaded, today's downtime as a dashed line and a marker where 2050 falls back to it ("36.3 °C restores today's downtime"). Closer to the engineering question "what if the spec were different", but less direct as a ledger.
   - The v1 curve stays in the mock-up behind `?v=curve` for comparison only.

**Card 3: when the limit is exceeded.** Unchanged from v1. Month × hour-of-day grid of downtime hours for a chosen year (defaults to the View bar year), in that year's colour; month totals right, hour totals beneath, non-running hours greyed, slots that are new compared with today outlined in magenta. It shows whether shift times, night running or a summer shutdown can absorb the downtime, or whether it needs capital.

**Dropped from the Summary** (v1 alternatives): stoppage run length and cooling gap. Both move to Indicators rows (longest run; 1 % design temperature; degree-hours above the limit).

## 4. Data and build

The headline numbers must come from the multi-year pipeline, so the limit cannot be applied in the browser to a single year. Instead the pipeline pre-computes a **threshold ladder**:

1. `config/settings.yaml`: `process_lens: {ladder_c: [20, 46, 0.5], presets: {...}, stop_day_min_hours: 1}`.
2. `annual.py`: per year, histogram the hall-air dry bulb at 0.5 °C bins for operating hours, all hours and each shift, plus a histogram of each day's maximum (operating and 24 h). Cumulative sums give hours and days above every rung at once (53 rungs, no 53 passes). Hall gain needs no extra data: it is a shift of the rung index. Degree-hours and the longest run per rung come from the same pass. Stored in a separate long table (`outputs/phase1/dbt_ladder.parquet`, `outputs/phase2/dbt_ladder_future.parquet`), not 53 more CSV columns.
3. Ensemble step: the same median / 90th percentile / extreme-year and model median / min / max as today, per rung. A per-rung median of monotonic curves is still monotonic, so curve A cannot zigzag.
4. `build_dashboard.py`: ladder arrays into `DATA.kpi[site].proc` (the bridge and ladder read limit + 1 / 2 / 3 °C from the same arrays, so they need no extra data), and for card B the reference-year hourly dry bulb (TMY, hot and extreme years and their futures, 6-model median per hour, uint8 at 0.25 °C) as in the mock-up.
5. Template: the lens state, the three controls, the overrides listed in section 2, and the tests (`tests/dashboard_check.js`: toggle, stepper, presets, 24 h; pytest: ladder at 30 °C equals `hours_t_gt30`, ladder at 35 and 32 °C equal the existing `proc_hours_*` all-hours values, monotonic in the limit).

**Re-run needed.** The ladder needs the hourly weather, which is not in the repository (ERA5 hourly and the future files are gitignored). Implementation therefore re-runs `fetch_era5.py` (the CDS key is set in this environment, as at 3 Nov 2026), `phase1_historical.py --reuse-adjustment` and `phase2_future.py --reuse-deltas`; NEX does not need fetching again. Existing outputs should be unchanged, which doubles as a regression check.

**Page size.** The page is about 3.9 MB now. Ladder arrays add roughly 1–1.5 MB and the card-B hourly data about 2.5 MB (the mock-up is 8.7 MB because it carries hourly data for every year and computes everything in the browser). If 7–8 MB is too heavy for sharing, card B can drop to 1 °C rungs or month × 2-hour blocks.

## 5. Mock-up caveats

The renders compute everything in the browser from single weather years: "typical" is the typical meteorological year, not the 11-year median; futures are the reference years shifted by the dashboard's median month × hour change, which ignores the extra hot-day warming of the real morph, so the mock-up likely **understates** 2040 / 2050 exceedance at hot sites. No model ranges. Treat the numbers as layout and story checks, not results. The mock-up sources (`process_lens.js`, `mock_data.py`, `build_mock.py`) are kept next to the renders; the 8.7 MB built page is not committed.

## 6. Open points

- **Risk bands in hours.** High 100–249 h and Very high 250+ h a year are placeholders; they belong per process (an hour of a paint booth costs less than an hour of an autoclave line).
- **Revenue link.** A `value_per_hour` per process (€/h, or €/h per site) would turn the strip and bridge into € directly. Expected annual loss should then use the **mean** year, not the median (typical) year, because losses are skewed by hot years; the pipeline can add a mean alongside the median at no extra cost.
- **Stop days** stay as a secondary measure (1 hour above the limit makes a stop day), shown in card 1's sub-line and on the map.
- **Humidity limits.** Several real process limits are RH or dew-point margins (paint: RH above 85 %, surface 3 °C above dew point). The ladder approach extends to RH and dew point with the same machinery; out of scope for the dry-bulb version.
- **Indoor conditions.** As for workers, hall air = outdoor + gain; a conditioned room needs its own design conditions and is not represented.
