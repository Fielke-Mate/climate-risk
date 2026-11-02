# Phase 3: Heat-stress metrics

**Status:** complete (Nov 2026). The methods are in `src/climate_risk/heat.py`, and the per-year indicators in `src/climate_risk/annual.py`. They run inside `scripts/phase1_historical.py` and `scripts/phase2_future.py`. Settings are in `config/settings.yaml` → `heat`.

## Methods

| Metric | Method | Notes |
|---|---|---|
| **WBGT, outdoor in sun** | Liljegren et al. (2008), via `pywbgt` (Argonne C code) | Temperature, dew point, pressure, 10 m wind (adjusted to 2 m), global solar radiation, sun position |
| **WBGT, indoor / shade** | The same model with solar radiation = 0 | Hall at outdoor temperature (D14), with sensitivity cases at +2 and +4 °C (same moisture) |
| **Reference** | ISO 7243 Class 2 (moderate work): 28 °C acclimatised, 26 °C not acclimatised | Working hours 06:00–22:00 local |
| **Worker heat-safety days** | Days with at least one working hour above the reference | Indoor (+0/+2/+4 °C) and outdoor in sun |
| **UTCI, shade / indoor** | `pythermalcomfort` (Bröde et al. 2012), radiant temperature = air temperature | |
| **UTCI, sun** | Radiant temperature = air + ASHRAE 55 SolarCal gain for a standing person (DNI, sun position, absorptivity 0.7, ground reflectance 0.2) | The 2-inch WBGT globe was not used for this, because it overstated radiant temperature (~107 °C) |
| **Process limits** | Hours of outdoor air above placeholder thresholds | Placeholders until real specifications are supplied (D21) |
| **Hot reference year** | Ranked by indoor/shade WBGT degree-hours above 25 °C in working hours (D42) | Re-ranked with the full WBGT |

Implementation notes:
- `pywbgt` compiles pvlib's solar code with numba. All our sun-position calls therefore use `method="nrel_numba"`, and the package imports `pywbgt` first.
- `pywbgt`'s time handling fails on recent pandas, so timestamps are pre-shifted to mid-hour in `heat.py`.

## Checks

- **Plausibility:** Sevilla, 13 July 2022, 14:00 UTC (41.6 °C, 20 % RH, 927 W/m²): WBGT 32.1 °C in sun and 28.2 °C in shade; radiant temperature in sun ~77 °C; UTCI ~50 in sun and ~42 in shade.
- **Tests:** `tests/test_heat.py` checks that sun WBGT exceeds shade WBGT, that the indoor offset raises shade WBGT, that SolarCal is zero at night and plausible at noon, and the UTCI reference point.

## Results: worker heat-safety days (typical year, today → 2050 SSP5-8.5, median of 6 models)

| Site | Indoor, hall = outside | Indoor +2 °C | Indoor +4 °C | Outdoor in sun | Hours of strong UTCI heat stress in sun (>32) |
|---|---|---|---|---|---|
| Sevilla (San Pablo) | 2 → 20 | 15 → 37 | 32 → 56 | 87 → 107 | 1559 → 1796 |
| Illescas | 0 → 0 | 0 → 2 | 0 → 9 | 37 → 62 | 1181 → 1440 |
| Getafe | 0 → 0 | 0 → 2 | 0 → 10 | 37 → 62 | 1181 → 1444 |
| Marignane | 0 → 6 | 3 → 11 | 8 → 22 | 32 → 54 | 729 → 942 |
| Toulouse (Blagnac) | 1 → 6 | 3 → 12 | 10 → 22 | 33 → 50 | 617 → 780 |
| Nantes (Bouguenais) | 0 → 0 | 0 → 0 | 0 → 3 | 9 → 14 | 257 → 347 |
| Saint-Nazaire (Montoir-de-Bretagne) | 0 → 0 | 0 → 0 | 0 → 1 | 4 → 8 | 125 → 196 |
| Donauworth | 0 → 0 | 0 → 0 | 0 → 1 | 4 → 20 | 246 → 395 |
| Meaulte | 0 → 0 | 0 → 0 | 0 → 2 | 4 → 8 | 147 → 218 |
| Filton | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 3 | 55 → 80 |
| Bremen | 0 → 0 | 0 → 0 | 0 → 2 | 3 → 10 | 110 → 191 |
| Broughton | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 1 | 32 → 48 |
| Nordenham | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 4 | 53 → 118 |
| Hamburg-Finkenwerder | 0 → 0 | 0 → 0 | 0 → 2 | 2 → 8 | 102 → 182 |
| Stade | 0 → 0 | 0 → 0 | 0 → 2 | 2 → 7 | 104 → 177 |

## Findings

1. **The full WBGT reads lower in shade than the provisional estimate**, because wind cooling and night-sky radiation are now modelled. With the hall at outdoor temperature, indoor exceedances are rare: Sevilla 2 → 20 days by 2050 (SSP5-8.5); Toulouse and Marignane 6.
2. **Indoor results depend on the hall heat gain.** At +4 °C, Sevilla reaches 32 → 56 days, Toulouse and Marignane 22, and Getafe/Illescas 10. Engineering estimates of hall temperatures are the key missing input (see [methodology review](../methodology_review.md)).
3. **Outdoor work in sun is where today's risk is clearest:** Sevilla 87 → 107 days, Madrid sites 37 → 62, Marignane 32 → 54, Toulouse 33 → 50, Donauwörth 4 → 20.
4. **Indoor air speed is a minor factor** (+0.1–0.2 °C on hot hours at 0.3 m/s).
5. **ERA5 under-reads hot afternoons by about 1 °C at Sevilla and Hawarden** compared with airport stations, so results are, if anything, slightly low.
