# Concept & Framework (v0.2, draft)

> A working document. Items marked **[OPEN]** still need a decision. Section 11 records the decisions taken so far.

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
 Hourly weather file   x    Site, workforce,    x    Work intensity, indoor/  ->  Days & hours above worker and
 (TMY / 2040 / 2050)        process lines            outdoor, process limits      process thresholds → house risk rating
```

### Time periods & scenarios

| Period | What it is | Climate window |
|---|---|---|
| **Historical** | Typical Meteorological Year (TMY) for the site | Source's period (PVGIS: roughly 2005–2023) |
| **2040** | TMY "morphed" to the projected 2040 climate | 2031–2050 model mean vs baseline |
| **2050** | TMY "morphed" to the projected 2050 climate | 2041–2060 model mean vs baseline |

- **Scenarios (proposed):** SSP2-4.5 (middle) and SSP5-8.5 (high). ESRS E1 expects a high-emissions scenario for physical risk. By 2040–2050 the scenarios differ less than they do later in the century, so SSP1-2.6 is optional.
- **Range:** each future year is produced once per climate model (an ensemble of roughly 5–10 CMIP6 models). Results are reported as the **median with a range** (e.g. min–max or 10th–90th percentile across models).

## 4. Weather-file workflow (core of v1)

The weather file is the central object. Every hazard metric is computed from an hourly year in one standard format, whatever the source.

```
 1. Sites            2. Historical file         3. Climate change deltas     4. Morphing             5. Analysis              6. Outputs
 ────────            ──────────────────         ────────────────────────     ──────────              ─────────                ─────────
 sites.csv      →    TMY per site:          →   CMIP6 monthly changes    →   Shift/stretch TMY   →   Thresholds, WBGT,    →   Tables, charts,
 (name, lat/lon,     • fetched (PVGIS API)      per site, per model,         hours by monthly        days/hours over          risk ratings,
 workforce,          • or loaded from file      per scenario, for            deltas → one future     limits, per file         dashboard
 processes)            (EPW / CSV)              2040 & 2050                  file per model
```

### 4a. Historical weather file

- **Default source: PVGIS TMY** (EU Joint Research Centre). It is free, has an API for any coordinate, and is derived from ERA5 reanalysis. It gives hourly temperature, relative humidity, solar radiation (global, direct, diffuse), wind speed and pressure, which are all the inputs WBGT needs. Coverage across Europe is good and reuse is open.
- **Alternative / override:** load any EPW or CSV file (e.g. climate.onebuilding.org TMYx, Meteonorm, or a client's own data). These go through the same parser into the same standard format.
- The tool stores each file with metadata: source, period, coordinates, and the distance from the source grid point to the site.

### 4b. Future weather files (morphing)

- **Method:** the "morphing" approach (Belcher, Hacker & Powell, 2005), the established way to make future building-design weather files. The TMY's hourly values are **shifted** by the projected monthly mean change and **stretched** by the change in the monthly daily range. This keeps the realistic hourly and day-to-day pattern of the historical year.
  - Temperature: shift + stretch using changes in mean, max and min
  - Relative humidity, radiation, wind: shift or scale by the monthly change
- **Delta source (proposed):** NASA NEX-GDDP-CMIP6, which is open, global, daily and bias-corrected. It provides tas, tasmax, tasmin, hurs, rsds and sfcWind. The deltas are computed between the future window and a model baseline that **matches the TMY's period**, so changes aren't double-counted.
- **Result per site:** 1 historical file + (2 periods × 2 scenarios × N models) future files.

### 4c. Known limitation: "typical" years under-represent extremes

A TMY is built from the most *average* months, so it smooths out heatwaves. A morphed TMY is a typical *future* year, not a bad one. For heat risk this means **results understate peak exposure**.

**Recommended addition [OPEN]:** add a **"hot year"** alongside the TMY, e.g. a recent extreme year for each site such as 2019, 2022 or 2023 from PVGIS/ERA5 hourly data. Morph it the same way. That gives "typical" vs "hot" conditions for each period, which is far more useful for worker-safety planning.

## 5. Heat analysis (v1 scope)

### 5a. Key metric: days (and hours) over thresholds

The headline result is **days per year above a threshold**, with hours above the threshold as supporting detail. Thresholds come in configurable **threshold sets**:

| Threshold set | Basis | Variable | Example values (to confirm) |
|---|---|---|---|
| General heat | Common climate indicators | Daily max air temperature | Tmax > 30 / 35 / 40 °C; warm nights Tmin > 20 °C |
| Worker heat stress | ISO 7243 WBGT reference values, by work intensity & acclimatisation | Hourly WBGT | e.g. ~28 °C (light), ~26 °C (moderate), ~25 °C (heavy), acclimatised |
| Workplace regulation (DE example) | ASR A3.5 indoor air temperature levels | Indoor air temperature | 26 / 30 / 35 °C |
| Process limits | User-defined per process | Air temp, RH, or wet-bulb | e.g. paint/sealant cure limit, chiller design ambient, composite layup room spec |

A "day over threshold" counts a day where the threshold is exceeded for at least *X* hours (default 1 hour, configurable), or where the daily max exceeds it.

### 5b. Use case A: worker heat stress

- Compute **hourly WBGT** from the weather file. The Liljegren method is the standard physically based approach and uses temperature, humidity, solar radiation, wind and pressure, all of which are in the file.
- **Indoor vs outdoor:** most aerospace manufacturing is indoors (hangars, assembly halls). For v1, indoor conditions = outdoor air temperature + a configurable **indoor offset**, with no solar load. A building model is out of scope.
- **Shifts:** count exceedances only during working hours (e.g. day shift 06:00–14:00, late shift 14:00–22:00, night shift).
- **Outputs:** days/hours above each threshold per workforce group, by period and scenario, with ranges.

### 5c. Use case B: process operating limits

- Each process has a limit (temperature, RH or wet-bulb) and an indoor/outdoor setting.
- **Outputs:** days/hours per year above the limit, and the change from historical. No downtime cost in v1.

### 5d. Risk rating

Results map to the consultant's **house risk rating scale** (to be supplied) using configurable bands, e.g. "days over threshold" → rating level. Kept as a separate, easily changed config, as the scale may be reworked later.

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
- **Dashboard:** Streamlit, with a map, site drill-down and period/scenario comparison. Run it locally. For client sharing, use a password-protected Streamlit deployment or a static HTML export. **[OPEN]**
- **Structure:**
  ```
  config/      thresholds.yaml, rating_scale.yaml, scenarios.yaml
  data/sites/  site lists
  data/weather/ cached historical + morphed files
  src/climate_risk/  weather (fetch/load), deltas, morph, heat (WBGT, thresholds), rating
  notebooks/   method checks
  app/         Streamlit dashboard
  ```

## 11. Roadmap

| Phase | Goal | Deliverable |
|---|---|---|
| 0 | Concept & framework | This document, agreed |
| 1 | Historical weather files | Fetch/load TMY for every pilot site; standard format; quick plots |
| 2 | Future weather files | CMIP6 deltas + morphing → 2040/2050 ensembles; sanity checks vs published projections |
| 3 | Heat analysis | WBGT, thresholds, days/hours over, ranges, house rating |
| 4 | Dashboard | Portfolio map, site drill-down, period/scenario comparison, shareable |
| 5 | Extensions | Hot-year files, more hazards, financial effects |

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
| D8 | Use the house risk rating scale for now; may be reworked |
| D9 | Non-commercial proof of concept, self-maintained; simple Python stack, rebuild if productised |

## 13. Open questions

1. **House rating scale:** what are its levels and definitions, so we can set bands for "days over threshold"?
2. **Thresholds:** which worker and process thresholds do you want as defaults? Are ISO 7243 WBGT plus a typical process limit (e.g. ~30 °C indoor) a sensible start?
3. **Hot year:** add a "hot year" alongside the TMY (section 4c)?
4. **Scenarios:** SSP2-4.5 + SSP5-8.5, or also SSP1-2.6?
5. **Indoor offset:** use one default (e.g. +3 °C over outdoor) for all halls, or set it per site?
6. **Client sharing:** password-protected hosted Streamlit, or a static HTML report?
