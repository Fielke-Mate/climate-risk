# Concept & Framework (v0.7, draft)

> A working document. Items marked **[OPEN]** still need a decision. Section 12 records the decisions taken so far.

## 1. Problem & vision

Companies with physical operations, manufacturing in particular, need to understand and disclose how climate change affects their sites. Most physical-risk tools give one generic hazard score per location. They don't answer the operational questions a site manager asks:

- *How many days a year will it be too hot to work safely at this plant, now vs 2040 vs 2050?*
- *How often will conditions exceed what this process line can tolerate?*
- *Which of our sites are most exposed?*

**Vision:** a tool where a consultant models a client's sites, workforce and processes; builds a historical and future hourly **weather file** for each site; analyses heat (and later other hazards) against worker and process thresholds; and shares a clear, read-only dashboard with the client. The outputs are structured to support IFRS S2 and ESRS E1 disclosures.

**Current stage:** a non-commercial **proof of concept**, run and maintained by one person (the consultant). If it becomes an active tool, it will be rebuilt. So the priority is simplicity, transparency and correct methods, not scalability.

## 2. Users

| User | Needs | Surface |
|---|---|---|
| **Consultant** (primary) | Define sites, load or fetch weather files, set thresholds, run analysis, review results | Analysis workflow (scripts / notebooks / app) |
| **Client** (secondary) | See the risk across their assets, drill into a site, compare time periods | Shareable read-only dashboard |

## 3. Conceptual framework

We follow the IPCC AR6 risk framing: **Risk = f(Hazard, Exposure, Vulnerability)**.

```
 HAZARD                     EXPOSURE                 VULNERABILITY                IMPACT (v1: physical metrics, no $)
 ──────                     ────────                 ─────────────                ───────────────────────────────────
 Hourly weather files  x    Site, workforce,    x    Work intensity,          ->  Days & hours above worker and
 (typical + extreme         process lines            process limits               process thresholds → risk rating
  × hist / 2040 / 2050)                                                           (scale to be defined)
```

### Time periods & scenarios

Each site's **baseline is the actual hourly record for 2015–2025** (11 years). Every year in it is analysed hour by hour, and each one is adjusted to 2040 and 2050:

| Period | Data analysed | Reported |
|---|---|---|
| **Historical** | 11 actual years, 2015–2025 | Typical (median year) and **hot (90th percentile year)** |
| **Historical hot reference year** | One actual, **unadjusted** year per site: the site's hottest year, ranked by hours of WBGT > 28 °C | Its values, labelled with the year (may differ between sites) |
| **2040** | Each of the 11 years adjusted to 2031–2050 climate, per model & scenario | Typical and 90th percentile, with model range |
| **2050** | Each of the 11 years adjusted to 2041–2060 climate, per model & scenario | Typical and 90th percentile, with model range |

A **typical meteorological year (TMY)** is also built from 2015–2025 (and adjusted to 2040/2050). It is used only where one representative year is needed for hourly charts in the weather summary pages.

- **Scenarios (decided):** SSP2-4.5 (middle) and SSP5-8.5 (high). ESRS E1 expects a high-emissions scenario for physical risk.
- **Range:** each future year is produced once per climate model (an ensemble of roughly 5–10 CMIP6 models). Results are reported as the **median with a range** (e.g. min–max or 10th–90th percentile across models).

## 4. Weather-file workflow (core of v1)

The weather file is the central object. Every hazard metric is computed from an hourly year in one standard format, whatever the source.

```
 1. Sites            2. Historical file         3. Climate change deltas     4. Morphing             5. Analysis              6. Outputs
 ────────            ──────────────────         ────────────────────────     ──────────              ─────────                ─────────
 sites.csv      →    2015–2025 hourly +     →   CMIP6 monthly changes    →   Shift/stretch TMY   →   Thresholds, WBGT,    →   Tables, charts,
 (name, lat/lon,     TMY per site:              per site, per model,         hours by monthly        days/hours over          risk ratings,
 workforce,          • fetched (Open-Meteo)     per scenario, for            deltas → one future     limits, per file         dashboard
 processes)          • or loaded (EPW / CSV)    2040 & 2050                  year per model
```

### 4a. Historical weather files

**Baseline period:** 2015–2025 (11 years). **Full year:** all 8,760 hours are kept and analysed, both for heat metrics and for the site weather summary (section 5e).

**Humidity check (based on PVGIS documentation; to be confirmed with a live request):**
- PVGIS **TMY** output includes relative humidity (plus temperature, global/direct/diffuse radiation, infrared, wind speed/direction and pressure). ✔
- PVGIS **multi-year hourly series** includes temperature, radiation and wind, but **not humidity**. ✘

The XMY needs a multi-year hourly record **with humidity**, so PVGIS alone isn't enough.

**Approach (decided):** download the hourly ERA5 record for 2015–2025 for each site and build the TMY from the same record, so everything is consistent.
- **ERA5 hourly source (decided): Open-Meteo Historical Weather API.** ERA5-based, no API key, free for **non-commercial use only**.
  > ⚠️ **Change before any commercial use:** move to the official Copernicus Climate Data Store (CDS), which is free and allows commercial use but needs an account. See section 14.
- **TMY method:** standard ISO 15927-4 selection (most typical month per calendar month).
- **PVGIS TMY** is downloaded as an **independent cross-check**: our TMY should look similar.

**Alternative / override:** load any EPW or CSV file (e.g. climate.onebuilding.org TMYx, Meteonorm, or a client's own data) through the same parser into the same standard format. Each file is stored with metadata: source, period, coordinates, and the distance from the source grid point to the site.

### 4b. Future weather files (morphing)

- **Method:** the "morphing" approach (Belcher, Hacker & Powell, 2005), the established way to make future building-design weather files. The TMY's hourly values are **shifted** by the projected monthly mean change and **stretched** by the change in the monthly daily range. This keeps the realistic hourly and day-to-day pattern of the historical year.
  - Temperature: shift + stretch using changes in mean, max and min
  - Relative humidity, radiation, wind: shift or scale by the monthly change
- **Delta source (proposed):** NASA NEX-GDDP-CMIP6, which is open, global, daily and bias-corrected. It provides tas, tasmax, tasmin, hurs, rsds and sfcWind. The deltas are computed between the future window and a model baseline that **matches the TMY's period**, so changes aren't double-counted.
- **Result per site:** 1 historical file + (2 periods × 2 scenarios × N models) future files.

### 4c. Capturing extremes: multi-year analysis (replaces the XMY idea)

A single typical year smooths out heatwaves. Instead of building one artificial "extreme" year, we **analyse every year in the record**:

1. **Historical:** compute the hourly metrics (WBGT, UTCI, thresholds) for each of the 11 actual years 2015–2025. Report the **median year** ("typical") and the **90th percentile year** ("hot").
2. **Future:** adjust each of the 11 years to 2040 and 2050 (per model and scenario), then analyse and report them the same way.
3. **Hot reference year (per site):** each site's hottest actual year (ranked by hours of WBGT > 28 °C, Class 2), **unadjusted**, as a real-world reference that clients will remember.

**Why this works:** heatwaves that actually happened (2019, 2022, 2023…) are kept exactly as observed. No selection rule is needed, and results come straight from hour-by-hour counts.

**Caveat:** with 11 years, the 90th percentile sits roughly between the hottest and second-hottest year. That's fine as a "hot year" indicator, but it is not a statistically robust 1-in-10-year estimate. This is noted in the methodology.

**Projecting peaks (decided):** future extremes warm faster than means in much of Europe (especially Iberia and central Europe). So the adjustment uses projected changes in **upper temperatures** (e.g. the change in each month's 90th percentile daily max), not just the mean. In practice, each part of the temperature distribution is shifted by its own projected change (quantile-based morphing).

**Baseline alignment:** NEX-GDDP-CMIP6 historical runs end in 2014. So the model baseline for 2015–2025 comes from the start of the scenario runs, where SSP2-4.5 and SSP5-8.5 are still almost identical.

## 5. Heat analysis (v1 scope)

### 5a. Key metric: days (and hours) over thresholds

The headline result is **days per year above a threshold**, with hours above the threshold as supporting detail. Thresholds come in configurable **threshold sets**:

| Threshold set | Basis | Variable | Example values (to confirm) |
|---|---|---|---|
| General heat | Common climate indicators | Daily max air temperature | Tmax > 30 / 35 / 40 °C; warm nights Tmin > 20 °C |
| **Worker heat stress (v1 default)** | ISO 7243 WBGT reference value, Class 2 moderate work (section 5b) | Hourly WBGT | 28 °C (acclimatised); 26 °C not-acclimatised sensitivity |
| **Thermal stress (UTCI)** | UTCI assessment scale (section 5c) | Hourly UTCI | Moderate heat stress > 26 °C · strong > 32 °C · very strong > 38 °C · extreme > 46 °C |
| Workplace regulation (DE example) | ASR A3.5 indoor air temperature levels | Indoor air temperature | 26 / 30 / 35 °C |
| Process limits | User-defined per process | Air temp, RH, or wet-bulb | e.g. paint/sealant cure limit, chiller design ambient, composite layup room spec |

A "day over threshold" counts a day where the threshold is exceeded for at least *X* hours (default 1 hour, configurable), or where the daily max exceeds it.

### 5b. Use case A: worker heat stress

**ISO 7243 work-intensity (metabolic rate) classes.** The reference WBGT is the level up to which continuous work is generally acceptable for a fit, normally clothed worker. Values below are the widely used tabulated values. The 2017 edition expresses them as curves against metabolic rate, so check exact figures against the standard in Phase 3.

| Class | Metabolic rate (approx.) | Typical activities | WBGT ref, acclimatised | WBGT ref, not acclimatised |
|---|---|---|---|---|
| 0 Resting | < 115 W | Seated at rest | 33 °C | 32 °C |
| 1 Low | 115–235 W | Seated or standing light work: inspection, light assembly, bench work with small tools, machine operation, slow walking | 30 °C | 29 °C |
| 2 Moderate | 235–360 W | Sustained hand/arm work: riveting, drilling, fastening, sanding, pushing light carts, normal walking | 28 °C | 26 °C |
| 3 High | 360–470 W | Intense arm and trunk work: carrying heavy material, sawing, pushing heavy carts, fast walking | 25–26 °C | 22–23 °C |
| 4 Very high | > 470 W | Very intense work at fast pace: heavy shovelling, climbing stairs/ladders with loads | 23–25 °C | 18–20 °C |

**Decided default for aircraft manufacturing: Class 2 (moderate).** Background: much assembly work (riveting, drilling, sealing, fastening, wiring) is sustained arm work, often overhead, so it sits around **Class 2 (moderate)**. Inspection, quality and machine-minding are **Class 1 (low)**. Show both: **Class 2 as the headline, Class 1 as secondary**, assuming **acclimatised** workers. Show "not acclimatised" as a sensitivity for early-summer heatwaves and northern sites, where workers are less used to heat.

- Compute **hourly WBGT** from the weather file. Indoor workers use **shaded WBGT** (no direct solar load). Outdoor workers use WBGT in sun. The Liljegren method is the standard physically based approach and uses temperature, humidity, solar radiation, wind and pressure, all of which are in the file.
- **Indoor vs outdoor:** most aerospace manufacturing is indoors (hangars, assembly halls). **For v1, indoor conditions = outdoor conditions** (offset = 0 °C). The code still includes an `indoor_offset` parameter per workforce group and process, so it can later be set from **engineering estimates** without changing the method. A building model is out of scope.
- **Shifts:** count exceedances only during working hours (e.g. day shift 06:00–14:00, late shift 14:00–22:00, night shift).
- **Outputs:** days/hours above each threshold per workforce group, by period, scenario and year type (typical / extreme warm), with ranges.

### 5c. UTCI (Universal Thermal Climate Index)

UTCI is the "feels-like" temperature from a full human heat-balance model. It carries over from the earlier Power BI dashboard.

- **Inputs:** air temperature, humidity, wind speed (10 m) and **mean radiant temperature (Tmrt)**. Tmrt is calculated from direct, diffuse and longwave radiation plus sun position, all available from ERA5. Implementation: an established library (e.g. ECMWF `thermofeel` or `pythermalcomfort`).
- **Scale (decided): the Power BI scale and colour bar, extended at the top with the standard UTCI bands.**

  | Strong cold | Moderate cold | Slight cold | No thermal stress | Slight heat | Moderate heat | Strong heat | Very strong heat | Extreme heat |
  |---|---|---|---|---|---|---|---|---|
  | < −13 | −13 to 0 | 0 to 9 | 9 to 26 | 26 to 28 | 28 to 32 | 32 to 38 | 38 to 46 | > 46 |

- **Metrics (decided, from the Power BI):** % and hours of heat stress (UTCI > 28); % and hours of cold stress (UTCI < 0); % time comfortable (9–26); % time comfortable for short periods (0–28); hours in each category ("condition of person"); UTCI distribution by hour of day.
- **Sun vs shade:** UTCI in sun (outdoor work, yard operations, logistics) and in shade (Tmrt ≈ air temperature, which suits indoor-equals-outdoor in v1).
- **WBGT vs UTCI:** WBGT is the **occupational standard** (ISO 7243) and drives work/rest decisions. UTCI is a **physiological comfort/stress** index that is easier to communicate. Both are reported, and WBGT remains the headline for worker risk.
- **Mock-up:** `docs/mockups/utci_page.html` (placeholder numbers only).

### 5d. Use case B: process operating limits

- Each process has a limit (temperature, RH or wet-bulb), possibly a lower limit too, and an indoor/outdoor setting.
- **Target applications (later):** paint and coating application (temperature and humidity windows) and composite / carbon-fibre layup and curing (controlled-environment room conditions). In v1 these are placeholder thresholds the user sets.
- **Outputs:** days/hours per year above the limit, and the change from historical. No downtime cost in v1.

### 5e. Risk rating

**Left blank for v1.** The concept is shown with raw metrics (days/hours over threshold, change vs historical). The code keeps a placeholder `rating_scale.yaml` so a house scale can be dropped in later without changes elsewhere.

### 5f. Site weather summary

Alongside the risk metrics, each site gets a **full-year weather summary**, modelled on the consultant's earlier Power BI weather-analysis dashboard (temperature, humidity, wind, irradiance, UTCI comfort, natural-ventilation potential). It is reworked to **compare years** (Historical / 2040 / 2050, TMY / XMY, by scenario). See [`weather_summary_dashboard.md`](weather_summary_dashboard.md).

## 6. Pilot portfolio: European aerospace manufacturing

The pilot uses an **illustrative portfolio based on public Airbus European manufacturing locations**. It spans a strong north–south climate gradient (North Sea coast → Iberia). The sites are for method testing only. No company data, and nothing is presented as the company's own assessment. See `data/sites/pilot_aerospace_europe.csv`. **Coordinates are approximate and need checking.**

| Country | Sites |
|---|---|
| France | Toulouse, Saint-Nazaire, Nantes, Méaulte, Marignane |
| Germany | Hamburg-Finkenwerder, Bremen, Stade, Nordenham, Donauwörth |
| Spain | Getafe, Illescas, Sevilla (San Pablo), Puerto Real |
| UK | Broughton, Filton |

The Spanish sites and Marignane will probably dominate heat exposure. The northern German and UK sites act as useful low-exposure contrasts.

## 7. Later hazards (roadmap)

Following the EU Taxonomy climate hazard classification, in rough priority order: riverine & pluvial flooding → coastal flooding / sea-level rise → water stress & drought → wildfire → extreme wind. Not all of these fit the weather-file approach. Flood and sea-level rise need spatial hazard datasets. The data model stays hazard-agnostic so they can plug in later.

## 8. Disclosure alignment

| Requirement | How the tool supports it |
|---|---|
| IFRS S2: identify physical risks (acute/chronic) and time horizons | Heat metrics per site for historical / 2040 / 2050 |
| IFRS S2: climate resilience / scenario analysis | SSP2-4.5 and SSP5-8.5 results with model ranges |
| IFRS S2: amount & % of assets/activities vulnerable to physical risk | Portfolio count/% of sites above rating thresholds |
| ESRS E1: physical risk identification incl. high-emissions scenario | SSP5-8.5 included by default, plus method documentation |
| ESRS E1-9: anticipated financial effects | **Not in v1** (no $ figures). Physical metrics provide the base for later |
| Both: methodology transparency | Methodology notes generated with each run (sources, models, thresholds) |

**[OPEN]** Check the current ESRS scope and timing after the 2025 EU "Omnibus" simplification for each client.

## 9. Data model (first pass)

```
Site            id, name, country, lat, lon, notes
WorkforceGroup  site_id, name, indoor/outdoor, indoor_offset, work_intensity,
                acclimatised, shift_hours
Process         site_id, name, variable (T / RH / wet-bulb), limit, indoor/outdoor, indoor_offset
WeatherFile     site_id, period (historical/2040/2050), scenario, model, source, hourly data
ThresholdSet    name, variable, values, min_hours_per_day
RatingScale     metric → bands → rating
Result          site × group/process × threshold × period × scenario × model → days, hours
```

## 10. Tech approach (proof of concept)

Since this is a single-user proof of concept you'll run yourself, and it will be rebuilt if it becomes a product, keep it **as simple as possible**:

- **Language:** Python only.
- **Core libraries:** pandas / xarray (data), pvlib (PVGIS fetch + EPW reading), thermofeel or a WBGT implementation (Liljegren), s3fs for NEX-GDDP-CMIP6 on AWS open data.
- **Storage:** plain files (CSV/YAML for config, Parquet for weather files and results). No database.
- **Dashboard:** Streamlit, map-centred (see 10a). Runs locally. No client sharing or password protection for now.
- **Structure:**
  ```
  config/      thresholds.yaml, rating_scale.yaml, scenarios.yaml
  data/sites/  site lists
  data/weather/ cached historical + morphed files
  src/climate_risk/  weather (fetch/load), deltas, morph, heat (WBGT, thresholds), rating
  notebooks/   method checks
  app/         Streamlit dashboard
  ```

### 10a. Interactive map (target experience)

The dashboard is built **around an interactive map of the portfolio**:

- **Map:** every site as a marker, with switchable visual layers showing risk. Candidate options to work through later: markers coloured or sized by days over threshold; toggles for period, scenario and year type; change-vs-historical views; optional background climate layers.
- **Click a site** → a **side panel next to the map** shows that site's dashboard: metrics by period and scenario with ranges, threshold exceedance charts, and worker vs process results.
- **Portfolio summary** sits alongside the map, e.g. sites ranked by exposure.
- The specific visualisations will be designed in a later step. Streamlit supports this with map components (e.g. pydeck or folium) that report which site was clicked.

## 11. Roadmap

| Phase | Goal | Deliverable |
|---|---|---|
| 0 | Concept & framework | This document, agreed |
| 1 | Historical weather files | ERA5 hourly 2015–2025 + TMY + hot reference year for every pilot site; PVGIS TMY cross-check; standard format; quick plots |
| 2 | Future weather files | CMIP6 deltas + morphing → 2040/2050 ensembles; sanity checks vs published projections |
| 3 | Heat analysis | ISO 7243 WBGT, thresholds, days/hours over, ranges |
| 4 | Dashboard | Interactive portfolio map, click-through site panel, site weather summary pages, period/scenario/year-type comparison |
| 5 | Extensions | Risk rating scale, indoor offsets from engineering estimates, more hazards, financial effects, client sharing |

## 12. Decisions log

| # | Decision |
|---|---|
| D1 | Primary user is the consultant; clients get a shareable read-only dashboard |
| D2 | Physical risk first, extreme heat prioritised; worker heat stress and process limits are the two use cases |
| D3 | Align to IFRS S2 and ESRS E1 |
| D4 | Analysis is based on hourly annual weather files: historical TMY, 2040 projected, 2050 projected |
| D5 | Future years produced by morphing the TMY with climate-model deltas; results reported as a range across models |
| D6 | Pilot geography: European aerospace manufacturing sites (based on public Airbus locations) |
| D7 | No $ figures in v1; headline metric is days (and hours) over configurable worker/process thresholds |
| D8 | ~~Use the house risk rating scale~~ → superseded by D12 |
| D9 | Non-commercial proof of concept, self-maintained; simple Python stack, rebuild if productised |
| D10 | Add an Extreme Warm Year (XMY) built TMY-style with high-percentile month selection, alongside the TMY |
| D11 | Worker heat stress uses ISO 7243 WBGT as the first approach |
| D12 | Risk rating left blank for v1; show raw metrics |
| D13 | Scenarios: SSP2-4.5 and SSP5-8.5 |
| D14 | Indoor = outdoor for v1; keep an `indoor_offset` parameter to set later from engineering estimates |
| D15 | No client sharing / password for now |
| D16 | The dashboard will centre on an interactive map with risk layers and a click-through site panel; visuals to be designed later |
| D17 | Analyse the full year (8,760 h); each site also gets a weather summary comparing years, based on the earlier Power BI dashboard |
| D18 | XMY uses extreme selection across the whole year (described as a warm-case stress test) |
| D19 | The XMY is morphed with projected changes in upper temperatures, not just mean changes |
| D20 | Baseline record 2005–2023 (no need to go back to 1991). Weather source must include humidity: PVGIS multi-year series lacks it, so we use ERA5 hourly; PVGIS TMY kept as a cross-check |
| D21 | Process thresholds will eventually target paint application and composite / carbon-fibre layup and curing |
| D22 | Worker heat stress headline: ISO 7243 Class 2 (moderate), WBGT 28 °C acclimatised |
| D23 | Add UTCI (sun and shade) as an additional metric alongside WBGT |
| D24 | Replace XMY with multi-year analysis of 2015–2025 (11 years): report typical (median) and hot (90th percentile) years, historical and future |
| D25 | Keep one unadjusted historical hot reference year |
| D26 | ERA5 via Open-Meteo for the proof of concept; switch to Copernicus CDS before any commercial use |
| D27 | UTCI uses the Power BI metrics and colour-bar scale |
| D28 | Weather summary page priorities agreed (see weather_summary_dashboard.md) |
| D29 | Baseline extended to 2015–2025 (11 years) |
| D30 | Hot reference year chosen per site (hottest by WBGT > 28 °C hours) |
| D31 | UTCI scale extended with very strong (38–46) and extreme (> 46) heat bands |
| D32 | Natural ventilation and evaporative cooling removed from scope |
| D33 | Site coordinates checked against published sources (airfield reference points or addresses; see sites CSV). Precision of ~1–3 km is enough, as ERA5 grid cells are ~9–30 km |

## 13. Open questions

1. **Puerto Real:** Airbus sold the Puerto Real plant in 2024 and completed consolidation at **Airbus Cádiz, El Puerto de Santa María** (TecnoBahía park) in October 2026. Replace Puerto Real with El Puerto de Santa María? The two are ~10 km apart, so the climate is effectively the same, but the site name should reflect reality.
2. **Remaining Power BI definitions** (proposed defaults, to confirm or replace):
   - Temperature categories (pie/stacked bars): < 0, 0–10, 10–20, 20–25, 25–30, 30–35, 35–40, > 40 °C
   - Heating degree hours base 18 °C; cooling degree hours base 24 °C
   - Comfortable hours = UTCI 9–26 (no thermal stress), as on the UTCI page
3. **Coordinate refinement (optional):** Stade, Nordenham, Donauwörth and Illescas use town or helipad points. Fine for ERA5, but they could be refined with a map lookup once map services are reachable.

## 14. Notes for productisation

Things that are fine for a non-commercial proof of concept but must change if the tool develops further:
- **Weather data source:** Open-Meteo's free tier is non-commercial only. Move to the Copernicus Climate Data Store (or a paid Open-Meteo plan).
- **Licences:** re-check terms for all datasets (NEX-GDDP-CMIP6, PVGIS, ERA5) for commercial use.
- **Architecture:** rebuild beyond a single-user Streamlit app (accounts, client sharing, database), as already noted.
- **Methods:** peer-review the WBGT/UTCI implementations and the morphing; consider longer baselines or large-ensemble methods for robust return periods.
