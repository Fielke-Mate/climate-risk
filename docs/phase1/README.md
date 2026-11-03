# Phase 1: Historical weather files

**Status:** complete (Nov 2026); extended record and extreme reference year added (D61–D63). Re-run with `scripts/fetch_era5.py`, `scripts/fetch_nex.py` (for the adjustment) then `scripts/phase1_historical.py` (`--reuse-adjustment` skips the NEX step).

## What was produced

| Output | Location | In git |
|---|---|---|
| ERA5 hourly record 2015–2025, standard format, per site (the headline baseline) | `data/weather/hourly/` | No (reproducible) |
| ERA5 hourly record 2000–2025, as observed and adjusted to the 2020 climate (D61) | `data/weather/hourly/{site}_era5_2000_2025[_adj2020].parquet` | No (reproducible) |
| Typical meteorological year (ISO 15927-4), per site | `data/weather/tmy/{site}_tmy.parquet` | Yes |
| Hot reference year (unadjusted), per site | `data/weather/hot_year/{site}_{year}.parquet` | Yes |
| Extreme reference year (adjusted to the 2020 climate, D62), per site | `data/weather/extreme_year/{site}_{year}.parquet` | Yes |
| PVGIS TMY (cross-check), per site | `data/weather/pvgis/` | Yes |
| Annual indicators per site and year, 2015–2025 (incl. heatwave length, D60) | `outputs/phase1/annual_summary.csv` | Yes |
| Annual indicators, 2000–2025 adjusted to the 2020 climate | `outputs/phase1/annual_summary_extended.csv` | Yes |
| Adjustment rates per site, month and model; check against the observed trend | `outputs/phase1/baseline_adjustment.csv`, `baseline_adjustment_check.csv` | Yes |
| TMY month selection (source year per month) | `outputs/phase1/tmy_month_selection.csv` | Yes |
| Hot and extreme reference years | `outputs/phase1/hot_reference_years.csv` | Yes |
| Monthly cross-check (ERA5 mean / TMY / PVGIS) | `outputs/phase1/monthly_crosscheck.csv` | Yes |
| ERA5 grid point used per site | `outputs/phase1/era5_grid_points.csv` | Yes |
| Figures | `docs/phase1/figures/` | Yes |

All 15 sites passed the automated checks: complete hourly record, no gaps or duplicates, and values in plausible ranges (`outputs/phase1/validation.json`).

## Method summary

1. **Download:** ERA5 hourly time series from Copernicus CDS (`reanalysis-era5-single-levels-timeseries`), 1 Jan 2015 – 1 Jan 2026, 12 variables, about 30–120 s per site.
2. **Standardise:**
   - Temperature and dew point are converted to °C, and RH is calculated from them (Magnus).
   - Wind speed and direction come from the u/v wind components.
   - Hourly radiation totals are converted to W/m². DNI is derived from direct horizontal radiation and the sun position at mid-hour, and DHI = GHI − direct horizontal.
   - Timestamps are UTC and mark the end of each hour.
3. **TMY (ISO 15927-4):**
   - For each month, the Finkelstein–Schafer statistic is calculated on daily mean temperature, GHI and RH, and each year is ranked on it.
   - Of the three best-ranked years, the one whose wind speed is closest to the monthly mean is chosen.
   - Joins between months are blended over ±8 h. 29 Feb is dropped, giving 8,760 hours on a nominal year (2001).
4. **Hot reference year (decision D42):** each year is ranked by **WBGT degree-hours above 25 °C in working hours** (06:00–22:00 local), using the shaded / indoor WBGT (originally a provisional psychrometric WBGT; since Phase 3 the Liljegren model with no solar radiation and 0.3 m/s indoor air speed): the sum of (WBGT − 25) over the hours above 25. Ties are broken by hours above 30 °C, then annual maximum temperature.
5. **Cross-check:** the PVGIS 5.3 TMY (ERA5 meteorology + SARAH-3 satellite radiation, 2005–2023) is compared with our TMY.
6. **Extended record (D61):** ERA5 is downloaded for 2000–2025. Every year is moved to the **2020 climate** with the climate models' own warming (`src/climate_risk/adjust.py`): for each site and month, the 6-model median change in mean daily maximum and minimum temperature and in specific humidity between 2000–2010 (NEX-GDDP-CMIP6 historical run) and 2015–2025, per year, smoothed over neighbouring months. Each day is shifted by its distance in years from mid-2020 through the same hour-by-hour step as future morphing (maximum and minimum shifted, hours in between stretched; vapour pressure scaled). Radiation and wind are unchanged.
7. **Extreme reference year (D62):** the hottest year of the adjusted 2000–2025 record, ranked like the hot year (D42). Where humid heat is negligible (the site's best year has under 50 WBGT degree-hours), it is ranked on dry heat instead (hours above 30 °C, then the highest temperature).

## Results per site (south → north)

| Site | ERA5 grid point (distance) | TMY mean T (°C) | TMY − ERA5 11-yr mean | TMY − PVGIS | Hot year | WBGT degree-hours > 25 (working hrs): median → hot year | Working hours WBGT > 26 (> 28): median → hot year |
|---|---|---|---|---|---|---|---|
| Sevilla (San Pablo) | 37.50, -6.00 (14 km) | 19.1 | -0.1 | +0.0 | **2025** | 447 → 737 | 197 (12) → 321 (27) |
| Illescas | 40.25, -3.75 (12 km) | 16.3 | +0.2 | +1.1 | **2022** | 17 → 47 | 2 (0) → 11 (0) |
| Getafe | 40.25, -3.75 (6 km) | 16.3 | +0.2 | +1.6 | **2022** | 17 → 47 | 2 (0) → 11 (0) |
| Marignane | 43.50, 5.25 (8 km) | 15.9 | +0.1 | -0.0 | **2025** | 116 → 196 | 51 (0) → 92 (2) |
| Toulouse (Blagnac) | 43.75, 1.25 (14 km) | 14.9 | +0.2 | +1.0 | **2025** | 123 → 250 | 59 (3) → 107 (8) |
| Nantes (Bouguenais) | 47.25, -1.50 (12 km) | 13.2 | +0.2 | +0.1 | **2019** | 6 → 72 | 0 (0) → 28 (4) |
| Saint-Nazaire (Montoir-de-Bretagne) | 47.25, -2.25 (10 km) | 13.4 | +0.1 | -0.1 | **2024** | 1 → 23 | 0 (0) → 14 (0) |
| Donauworth | 48.75, 10.75 (5 km) | 9.9 | -0.2 | +0.0 | **2015** | 0 → 4 | 0 (0) → 0 (0) |
| Meaulte | 50.00, 2.75 (6 km) | 11.6 | +0.1 | +0.6 | **2025** | 1 → 22 | 0 (0) → 9 (0) |
| Filton | 51.50, -2.50 (6 km) | 11.2 | +0.1 | +1.0 | **2022** | 0 → 0 | 0 (0) → 0 (0) |
| Bremen | 53.00, 8.75 (7 km) | 10.5 | -0.2 | +0.3 | **2015** | 0 → 15 | 0 (0) → 7 (0) |
| Broughton | 53.25, -3.00 (8 km) | 10.4 | -0.3 | +0.6 | **2022** | 0 → 0 | 0 (0) → 0 (0) |
| Nordenham | 53.50, 8.50 (2 km) | 10.4 | -0.1 | +0.7 | **2015** | 0 → 5 | 0 (0) → 2 (0) |
| Hamburg-Finkenwerder | 53.50, 9.75 (7 km) | 10.5 | +0.0 | +0.1 | **2015** | 0 → 9 | 0 (0) → 4 (0) |
| Stade | 53.50, 9.50 (8 km) | 10.4 | -0.1 | +0.7 | **2015** | 0 → 9 | 0 (0) → 5 (0) |

![WBGT degree-hours](figures/heatmap_wbgt_degree_hours.png)

![Days above 30 °C](figures/heatmap_days_tmax30.png)

![Days with a working hour above WBGT 26 °C](figures/heatmap_wbgt_days.png)

![Monthly temperature cross-check](figures/monthly_temperature_crosscheck.png)

## Findings

1. **The TMY is representative.** At every site its annual mean temperature is within ±0.3 °C of the 2015–2025 mean, and its monthly profile follows the record closely.
2. **PVGIS agrees reasonably well.** Our TMY is 0–1.6 °C warmer. Part of this is expected, because our 2015–2025 period is more recent than PVGIS's 2005–2023. The larger gaps at the Madrid sites (+1.1 to +1.6 °C) probably also reflect PVGIS's different grid treatment. RH agrees within ±3 % points and GHI within about ±5 % at most sites.
3. **Getafe and Illescas share the same ERA5 grid point** (40.25, −3.75), so their weather files are identical. More generally, the ~25 km ERA5 grid can't separate nearby sites and smooths local peaks. **ERA5-Land** (~9 km grid, also available as a CDS time series) is an option to refine this later. It lacks the direct-radiation field, so DNI would need a separate model.
4. **Indoor WBGT above the ISO 7243 Class 2 reference is concentrated in the south.** With the hall at outdoor temperature and no solar load, the headline reference (26 °C, workforce not acclimatised, D58) is exceeded regularly only at Sevilla (median 197 working hours a year), Toulouse (59 h) and Marignane (51 h). The Madrid sites reach it on a couple of hours a year (11 h in the hot year 2022), because their heat is dry: high temperature but a low wet bulb. Northern sites exceed it only in hot years (Nantes 28 h in 2019, Saint-Nazaire 14 h in 2024, Bremen 7 h in 2015). At the acclimatised reference (28 °C) only Sevilla (12 h) and Toulouse (3 h) exceed it in a median year. Consequences:
   - The original ranking (hours > 28 °C) could not separate years at most sites, so it was replaced by **WBGT degree-hours above 25 °C** (option B, decision D42).
   - The values in this table use the Phase 3 WBGT (Liljegren). The first Phase 1 run used a provisional psychrometric WBGT, which read lower (e.g. Sevilla degree-hours 704 provisional vs 447 Liljegren indoor at 0.3 m/s, see Phase 3 for why these differ). Indoor heat gains from engineering estimates would raise all values.
5. **Hot years under option B** are the years with the most *humid* heat in working hours: 2022 for Getafe/Illescas, 2025 for Sevilla, Toulouse, Marignane and Méaulte, 2019 for Nantes, 2024 for Saint-Nazaire, and 2015 for Donauwörth and the northern German sites.
   - **UK sites (Filton, Broughton):** indoor WBGT degree-hours are zero in every year, so the ranking falls back to the tie-breakers (hours above 30 °C, then maximum temperature) and picks the record dry heat of July 2022. There is effectively no humid heat stress at these sites today. Their exposure signal will come from future warming and indoor heat gains.

## Decision: hot-year ranking metric (D42)

**Option B adopted:** WBGT degree-hours above 25 °C in working hours. Hours above the ISO 7243 reference (26 °C headline, 28 °C acclimatised) are still reported. The ranking has since been recalculated with the Phase 3 WBGT method (Liljegren); because it ranks on degree-hours above 25 °C, it does not depend on the reference value (D58 left all hot years unchanged).


## Extended record and extreme reference year (D61–D63)

**Why not use all 26 years for the headline numbers?** The adjustment uses the models' warming, and the models warm France and Germany 0.2–0.4 °C/decade less than ERA5 observed (`baseline_adjustment_check.csv`). So after adjustment the 2000–2009 summers are still 0.3–0.6 °C cooler there than 2015–2025. Sevilla is the opposite case: its ERA5 cell shows summer *cooling* since 2000, so the model warming over-adjusts it by about 1 °C. The Mediterranean coast also gained humid heat in recent years that a temperature shift can't reproduce: Marignane has had 50–90 working hours a year above WBGT 26 °C since 2018, against mostly 0–30 before, even adjusted. A 26-year typical year would have understated today's heat (Marignane 51 → 12 hours, Toulouse 59 → 36). So the typical and 1-in-10 statistics, the TMY (D63) and the hot reference year stay on 2015–2025 as observed. The adjusted record supplies the extreme reference year. With the slow model warming, that year is, if anything, slightly conservative.

**Reference years** (hot = hottest of 2015–2025 as observed; extreme = hottest of 2000–2025 adjusted to the 2020 climate):

| Site | Hot year | Extreme year | Indoor WBGT hours above 26 °C (working hours): hot / extreme | Hours above 30 °C | Longest run of days above 30 °C | Highest temperature (°C) |
|---|---|---|---|---|---|---|
| Sevilla (San Pablo) | 2025 | 2006 | 321 / 398 | 996 / 1104 | 50 / 49 | 41.6 / 42.7 |
| Illescas | 2022 | 2003 | 11 / 23 | 864 / 961 | 46 / 42 | 41.2 / 41.9 |
| Getafe | 2022 | 2003 | 11 / 23 | 864 / 970 | 46 / 42 | 41.2 / 42.0 |
| Marignane | 2025 | 2003 | 92 / 116 | 444 / 678 | 19 / 30 | 38.3 / 38.6 |
| Toulouse (Blagnac) | 2025 | 2003 | 107 / 168 | 322 / 568 | 14 / 16 | 42.2 / 41.5 |
| Nantes (Bouguenais) | 2019 | 2003 | 28 / 84 | 94 / 172 | 4 / 12 | 37.8 / 39.0 |
| Saint-Nazaire (Montoir-de-Bretagne) | 2024 | 2003 | 14 / 62 | 13 / 73 | 2 / 4 | 32.7 / 34.5 |
| Donauworth | 2015 | 2003 (dry heat) | 0 / 0 | 133 / 170 | 4 / 12 | 35.7 / 37.7 |
| Meaulte | 2025 | 2003 | 9 / 29 | 43 / 92 | 3 / 10 | 35.2 / 36.2 |
| Filton | 2022 | 2022 (dry heat) | 0 / 0 | 46 / 46 | 4 / 4 | 34.9 / 34.8 |
| Bremen | 2015 | 2018 (dry heat) | 7 / 0 | 28 / 79 | 1 / 5 | 35.6 / 35.4 |
| Broughton | 2022 | 2022 (dry heat) | 0 / 0 | 15 / 15 | 2 / 2 | 33.9 / 33.8 |
| Nordenham | 2015 | 2018 (dry heat) | 2 / 0 | 7 / 21 | 1 / 2 | 31.7 / 32.0 |
| Hamburg-Finkenwerder | 2015 | 2018 (dry heat) | 4 / 0 | 20 / 72 | 1 / 5 | 35.4 / 35.1 |
| Stade | 2015 | 2018 (dry heat) | 5 / 0 | 21 / 67 | 1 / 5 | 35.1 / 34.9 |

**Reading:**
- **2003 is the extreme year at eight sites** (all of France, the Madrid sites, Donauwörth). In today's climate it brings **more heat and longer spells** than any recent year: Nantes 172 hours above 30 °C and a 12-day spell (2019: 94 hours, 4 days), Donauwörth 12 days (2015: 4), Marignane 30 days (2025: 19), Toulouse 168 indoor WBGT hours above 26 °C (2025: 107).
- **Sevilla: 2006**, humid heat (398 WBGT hours, against 321 in 2025).
- **North Germany: 2018**, chosen on dry heat: 3–4 times the hours above 30 °C of 2015 and the longest spells. It has slightly *fewer* indoor WBGT hours than 2015 (0 vs 1–7), which had a few humid days, so on WBGT views "Extreme" can read a little lower than "Hot" there.
- **UK: 2022** is both the hot and the extreme year; no earlier year, even adjusted, beats it.
