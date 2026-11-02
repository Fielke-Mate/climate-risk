# Concept & Framework (v0.1, draft)

> A working document. Items marked **[OPEN]** still need a decision.

## 1. Problem & vision

Companies with physical operations, manufacturing in particular, increasingly need to understand and disclose how climate change affects their sites. Most commercial physical-risk tools give one generic hazard score per location. They don't answer the operational questions a site manager or CFO actually asks:

- *How many work hours will we lose to heat at this plant in 2030 and 2050?*
- *How often will it be too hot to run this process line, and what does that cost?*
- *Which of our sites are most exposed, and what would adaptation buy us?*

**Vision:** a web app where a consultant models a client's sites, workforce and processes; runs heat (and later other hazard) projections across climate scenarios; turns hazard into operational and financial impacts; and shares a clear, read-only dashboard with the client. The outputs are structured so they can go straight into IFRS S2 / ESRS E1 disclosures.

## 2. Users

| User | Needs | Surface |
|---|---|---|
| **Consultant** (primary) | Set up client portfolios, enter site and process data, choose scenarios, adjust assumptions, review results, export report content | Consultant workspace (full edit) |
| **Client** (secondary) | See the risk across their assets, drill into a site, understand the drivers, compare scenarios | Client dashboard (read-only, shared) |

## 3. Conceptual framework

We follow the IPCC AR6 risk framing: **Risk = f(Hazard, Exposure, Vulnerability)**. That framing is then carried through to impact and financial effect.

```
 HAZARD               EXPOSURE                VULNERABILITY             IMPACT                     FINANCIAL EFFECT
 (climate data)  x    (what is there)    x    (how sensitive)     ->    (operational)         ->   (disclosure)
 ─────────────        ───────────────         ───────────────           ─────────────              ────────────────
 Tmax, humidity,      Site location,          Work intensity,           Lost work hours,           Labour cost,
 WBGT, heatwaves      workforce size,         indoor/outdoor,           productivity %,            lost output value,
 by scenario &        shifts, process         cooling/controls,         process downtime days,     cooling capex/opex,
 time horizon         lines, output value     process temp limits       H&S incidents risk         revenue at risk
```

### Scenarios & time horizons

| Dimension | Proposed default | Rationale |
|---|---|---|
| Scenarios | SSP1-2.6 (low), SSP2-4.5 (middle), SSP5-8.5 (high) | IFRS S2 needs scenario analysis across a range. ESRS E1 expects a high-emissions scenario for physical risk |
| Baseline | 1991–2020 observed/reanalysis | Current climate reference |
| Horizons | ~2030 (short), ~2050 (medium), ~2080 (long) | Map these to the client's own short/medium/long-term definitions, as both standards require |

## 4. Heat module (v1 scope)

### 4a. Use case A: worker heat stress

**Question:** How much does heat put worker health at risk and reduce work capacity at each site?

- **Core metric:** Wet Bulb Globe Temperature (WBGT), the standard occupational heat-stress index (ISO 7243). It combines temperature, humidity, radiation and air movement.
- **Thresholds:** WBGT reference values that depend on metabolic rate (light / moderate / heavy work) and acclimatisation. They drive recommended work/rest ratios.
- **Impact functions:** WBGT-to-work-capacity relationships (e.g. the curves behind the ILO *Working on a Warmer Planet* analysis). These turn hours of exceedance into **lost work hours / productivity %**.
- **Indoor vs outdoor:** Outdoor uses ambient conditions. Indoor (factory floor) applies a site-specific **indoor offset** (heat gain from processes and the building) and lets us model **controls** such as ventilation, spot cooling and HVAC.
- **Outputs per site/scenario/horizon:**
  - Hours per year above each WBGT action threshold
  - Estimated lost work hours and productivity loss (%)
  - Shift-level view (day vs night shifts)
  - Cost of lost labour productivity

### 4b. Use case B: process operating limits

**Question:** How often will conditions go past what equipment or processes can tolerate, and what does that cost in lost output?

- **Inputs per process/asset:** maximum operating ambient temperature (and optionally humidity), e.g. chiller/compressor design conditions, curing or chemical processes, electronics, cooling-tower wet-bulb limits; derating behaviour (full stop vs gradual capacity loss); production value per hour/day.
- **Metric:** hours/days per year where ambient (or modelled indoor) conditions exceed the limit.
- **Outputs:** expected downtime/derated hours, lost output units and value, and the change against baseline. These can also feed adaptation sizing, e.g. *how much extra cooling capacity keeps us below the limit to 2050?*

### 4c. Supporting heat indicators (for the dashboard and disclosure)

Days with Tmax > 35 °C / 40 °C, warm nights (Tmin > 25 °C), heatwave frequency/intensity, cooling degree days (an energy-demand proxy).

### 4d. Data approach (proposed)

| Need | Candidate source | Notes |
|---|---|---|
| Future daily climate | NASA NEX-GDDP-CMIP6 (≈25 km, daily tasmax/tasmin/humidity) | Free, global, bias-corrected, multi-model |
| Baseline | ERA5 / ERA5-Land reanalysis (hourly) | Gives the diurnal profile needed for hourly WBGT |
| Regional upgrades | National downscaled products where available | Optional higher resolution |

Known method challenges to resolve:
1. **Daily → hourly:** WBGT and exceedance hours need hourly data. Plan: use ERA5's hourly diurnal shapes, shifted by projected daily changes (delta method).
2. **WBGT from limited variables:** use a physically based calculation (e.g. the Liljegren method) where we have radiation and wind. Otherwise fall back to simpler approximations, with the uncertainty flagged.
3. **Model spread:** use a multi-model ensemble and report median plus a range, not a single number.

## 5. Later hazards (roadmap)

Following the EU Taxonomy climate hazard classification (acute/chronic × temperature/wind/water/solid mass), in rough priority order:

1. Riverine & pluvial flooding
2. Coastal flooding / sea-level rise
3. Water stress & drought (also relevant to process cooling water)
4. Wildfire / bushfire
5. Tropical cyclone / extreme wind

The data model and dashboard should be **hazard-agnostic** from day one, so new hazards plug in as modules.

## 6. Disclosure alignment

| Requirement | How the tool supports it |
|---|---|
| IFRS S2: identify climate-related physical risks (acute/chronic) and their time horizons | Hazard-by-site matrix across horizons |
| IFRS S2: climate resilience / scenario analysis | Multi-scenario results, with and without adaptation |
| IFRS S2: cross-industry metric, amount & % of assets/business activities vulnerable to physical risk | Portfolio summary: count/value of sites above risk thresholds |
| ESRS E1: physical risk identification incl. high-emissions scenario (IRO-1) | SSP5-8.5 included by default, plus method documentation |
| ESRS E1-9: anticipated financial effects from material physical risks | Financial-effect estimates (lost output, labour, capex) |
| Both: methodology & assumptions transparency | Auto-generated methodology appendix per assessment |

**[OPEN]** Check the current ESRS scope and timing after the 2025 EU "Omnibus" simplification for each client.

## 7. Data model (first pass)

```
Organisation (client)
 └── Assessment (scenario set, horizons, assumptions, status)
 └── Site (name, lat/lon, country, asset value, revenue/output value)
      ├── Workforce group (headcount, indoor/outdoor, work intensity, shifts,
      │                    acclimatisation, controls, hourly labour cost)
      └── Process / Asset (type, max operating temp/humidity, derating curve,
                           indoor offset, output value per hour, criticality)

Results: (site | group | process) × hazard × scenario × horizon → metrics + rating
```

## 8. Product shape

**Consultant workspace:** clients & portfolios → site entry (single + CSV upload) → workforce/process config → run assessment → review/adjust → export (tables, charts, methodology text).

**Client dashboard:** portfolio map with risk-coloured sites → portfolio summary (sites at risk, hours lost, output at risk) → site drill-down (heat metrics over time, scenario comparison, worker vs process impacts) → plain-language narrative and drivers.

**Architecture (proposal, [OPEN]):**
- Backend: Python (FastAPI) with xarray/pandas for the climate pipeline. Hazard indicators are precomputed per site and cached rather than computed live.
- Database: PostgreSQL + PostGIS.
- Frontend: React + MapLibre map + charting library.
- Sharing: client-scoped read-only accounts or expiring share links.

## 9. Roadmap

| Phase | Goal | Deliverable |
|---|---|---|
| 0 | Concept & framework | This document, agreed |
| 1 | Heat engine (proof of method) | Python package + notebook: one site → WBGT hours, lost work hours, process exceedance across scenarios, validated against a known location |
| 2 | Consultant MVP | Web app: enter sites/workforce/processes, run heat assessment, view results |
| 3 | Client dashboard | Shareable read-only portfolio + site views, report export |
| 4 | More hazards | Flood, water stress, wildfire, cyclone modules |
| 5 | Adaptation & finance | Adaptation options, cost-benefit, financial-effect modelling |

## 10. Open questions

1. **Geography:** Which regions do your clients mostly operate in? This decides data resolution and any national datasets.
2. **Pilot case:** Is there a real (or anonymised) manufacturing site we can use as the reference case for Phase 1?
3. **Depth vs breadth:** For v1, is a reliable, transparent heat assessment for a handful of sites enough? Or do portfolios of hundreds of sites need to work from the start?
4. **Financial outputs:** How far should v1 go into $ figures, compared with operational metrics (hours, days, %)?
5. **Risk rating:** Do you use a house risk-rating scale (e.g. 5×5 likelihood × consequence) that results should map to?
6. **Commercial intent:** Is this purely for your own practice, or a potential product? This affects hosting, multi-tenancy and data licensing (some datasets restrict commercial use).
7. **Tech comfort:** Will you be maintaining or running code yourself? This affects how simple the stack should be.
