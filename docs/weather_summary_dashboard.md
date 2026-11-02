# Site Weather Summary: dashboard design (draft)

Based on the consultant's earlier Power BI weather-analysis dashboard (Adelaide example). That dashboard analysed **one weather file**. This version keeps its structure but changes the focus to **comparing years**: Historical vs 2040 vs 2050, typical (TMY) vs extreme warm (XMY), for SSP2-4.5 and SSP5-8.5, with model ranges.

## Reference: the original Power BI dashboard

| Page | Content |
|---|---|
| Summary | Location, lat/lon, mini-map; rainfall over the year; temperature-category pie; hours at each RH; wind rose; "condition of person" bar; average temp / wind / RH; comfortable hours |
| Temperature | Hourly dry bulb over the year; % hours at each temperature; temperature-category pie; max/min; hours > 30 °C and < 10 °C (air and apparent/shaded); summer day/night temperature difference (thermal purging potential) |
| Wind Speed | Seasonal wind roses; annual wind rose; wind speed distribution with cumulative %; average wind speed |
| Relative Humidity | % hours at each RH; average RH at each temperature; hours of effective evaporative cooling |
| Irradiance | Max sun altitude by month; solstice sun angles; solar radiation distribution; monthly radiation on horizontal and N/E/S/W facades |
| UTCI Thermal Comfort | Hours by thermal-stress category; % heat stress (UTCI > 28), cold stress (UTCI < 0), comfortable; UTCI by hour |
| Natural Ventilation Potential | Hours where temperature and humidity both suit natural ventilation, by month, day vs night |
| Map | Site location |

Filters on every page: **Day / Night**, **Month**, **Season**.

A second version (**PowerBI_Template**) has the same pages and layout, with these differences:
- **Temperature page** adds **Heating Degree Hours** and **Cooling Degree Hours** cards.
- Rainfall is plotted from an hourly rainfall column, not a monthly one.
- No separate Map page (the mini-map stays on each page). The irradiance page has no "Maximum Irradiance Angle" card.

The design below combines both versions.

## Comparison version (agreed in principle)

New global filters: **Site**, **Scenario** (SSP2-4.5 / SSP5-8.5), **Year type** (typical / hot 90th percentile), plus the original Day/Night, Month and Season. Every chart compares **Historical | Hot reference year | 2040 | 2050**. Hourly profile charts that need a single year use the TMY.

Comparison patterns used throughout:
- **KPI cards in triplets:** Historical value → 2040 → 2050, each future value with its model range and the change, e.g. `412 h → 530 h (480–590) → 610 h (540–700)`.
- **Overlaid distributions:** the historical year as a grey outline, future years as coloured bars or lines.
- **Difference views:** the future minus historical by month or by hour of day, as a heatmap (month × hour).

| Page | Keep from original | Comparison additions | Priority |
|---|---|---|---|
| **Summary** | Location, KPIs, temperature categories, RH distribution, comfort bar | KPI triplets; stacked temperature-category bars per year; headline "days over threshold" | High |
| **Temperature** | Hourly profile, % hours per temperature, hours > 30 / < 10, max/min, apparent temp, day/night difference, heating & cooling degree hours | Overlaid distributions; month × hour heatmap of warming; **days over threshold** (Tmax > 30/35/40, warm nights); shift in the hottest-hours tail | High |
| **Heat stress (new, from UTCI page)** | **UTCI colour-bar scale, all UTCI metric cards, condition-of-person chart, UTCI by hour** | Comparison by year (see `mockups/utci_page.html`); **ISO 7243 WBGT** hours/days over 28 °C (Class 2) by shift | High |
| **Relative Humidity** | RH distribution, RH by temperature | Shift in humidity distribution by year | Low |
| **Process limits (new)** | – | Hours/days above process limits (e.g. paint application, composite layup/cure room conditions), by year | Medium |
| **Wind** | Wind roses, distribution | Little projected change; mainly descriptive. Comparison optional | Low |
| **Irradiance** | Monthly radiation, facades, sun altitude | Sun geometry doesn't change, and radiation change is small; mainly descriptive | Low |
| **Map** | Site location | Becomes the main interactive portfolio map (concept §10a) | High |

## Notes
- **Definitions to recover:** the Power BI calculation logic is stored in the compressed data model, so it can't be read from the file directly. Several definitions need restating: temperature category bands, "Condition of Person", comfortable hours and the degree-hour base temperatures (proposed defaults in concept §13). We'll restate them explicitly in `config/` (from the consultant's notes, or sensible defaults).
- **Rainfall:** the original used monthly rainfall. Typical weather files often don't carry reliable precipitation, so this is dropped for v1. Revisit with drought/flood hazards.
- **Apparent temperature (shaded):** keep as a secondary metric. WBGT is the primary worker metric.
- **Indoor workers:** use **shaded WBGT** (no direct solar load). Outdoor workers use WBGT in sun.
- **Out of scope (decided):** the natural ventilation and evaporative cooling pages served the original purpose of the Power BI file and are dropped.
