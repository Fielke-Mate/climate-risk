# Phase 3: Heat-stress metrics

**Status:** complete (Nov 2026). The methods are in `src/climate_risk/heat.py`, and the per-year indicators in `src/climate_risk/annual.py`. They run inside `scripts/phase1_historical.py` and `scripts/phase2_future.py`. Settings are in `config/settings.yaml` → `heat`.

## Methods

| Metric | Method | Notes |
|---|---|---|
| **WBGT, outdoor in sun** | Liljegren et al. (2008), via `pywbgt` (Argonne C code) | Temperature, dew point, pressure, 10 m wind (adjusted to 2 m), global solar radiation, sun position |
| **WBGT, indoor** | The same model with solar radiation = 0 and 0.3 m/s air speed (D52: exhaust-ventilated warehouse, no active cooling) | Hall at outdoor temperature (D14), with sensitivity cases at +2 and +4 °C (same moisture) |
| **Reference** | ISO 7243 Class 2 (moderate work): **26 °C not acclimatised (headline, D58)**; 28 °C acclimatised (sensitivity) | Working hours 06:00–22:00 local |
| **Worker heat-safety days** | Days with at least one working hour above the reference | Indoor (+0/+2/+4 °C) and outdoor in sun |
| **UTCI, indoor** | `pythermalcomfort` (Bröde et al. 2012): hall temperature incl. heat gain, radiant temperature = air, indoor air speed (10 m equivalent, floored at 0.5 m/s) | D51, D52: the right index for naturally ventilated / unconditioned halls |
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

| Site | Indoor, hall = outside | Indoor +2 °C | Indoor +4 °C | Outdoor in sun | Working hours of strong UTCI heat stress indoors (>32, hall = outside) |
|---|---|---|---|---|---|
| Sevilla (San Pablo) | 3 → 24 | 19 → 40 | 37 → 61 | 87 → 107 | 552 → 842 |
| Illescas | 0 → 0 | 0 → 4 | 1 → 14 | 37 → 62 | 395 → 662 |
| Getafe | 0 → 0 | 0 → 4 | 1 → 14 | 37 → 62 | 395 → 654 |
| Marignane | 0 → 6 | 4 → 12 | 9 → 24 | 32 → 54 | 134 → 343 |
| Toulouse (Blagnac) | 1 → 8 | 5 → 13 | 10 → 24 | 33 → 50 | 116 → 277 |
| Nantes (Bouguenais) | 0 → 0 | 0 → 1 | 1 → 4 | 9 → 14 | 26 → 62 |
| Saint-Nazaire (Montoir-de-Bretagne) | 0 → 0 | 0 → 0 | 0 → 1 | 4 → 8 | 2 → 12 |
| Donauworth | 0 → 0 | 0 → 0 | 0 → 1 | 4 → 20 | 5 → 49 |
| Meaulte | 0 → 0 | 0 → 0 | 0 → 2 | 4 → 8 | 13 → 36 |
| Filton | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 3 | 0 → 2 |
| Bremen | 0 → 0 | 0 → 0 | 0 → 2 | 3 → 10 | 6 → 36 |
| Broughton | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 1 | 0 → 0 |
| Nordenham | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 4 | 0 → 6 |
| Hamburg-Finkenwerder | 0 → 0 | 0 → 0 | 0 → 2 | 2 → 8 | 6 → 30 |
| Stade | 0 → 0 | 0 → 0 | 0 → 2 | 2 → 7 | 3 → 27 |

## Findings

1. **With the hall at outdoor temperature, indoor WBGT exceedances are rare** (exhaust-ventilated hall, 0.3 m/s): Sevilla 3 → 24 days by 2050 (SSP5-8.5); Toulouse 8, Marignane 6.
2. **Indoor results depend on the hall heat gain.** At +4 °C, Sevilla reaches 37 → 61 days, Toulouse and Marignane 24, and Getafe/Illescas 14. Engineering estimates of hall temperatures are the key missing input (see [methodology review](../methodology_review.md)).
3. **Outdoor work in sun is where today's risk is clearest:** Sevilla 87 → 107 days, Madrid sites 37 → 62, Marignane 32 → 54, Toulouse 33 → 50, Donauwörth 4 → 20.
4. **Indoor air speed:** replacing outdoor wind with 0.3 m/s raises indoor results (Sevilla +4 °C: 32 → 37 days); within 0.2–0.5 m/s it is a minor factor. Indoor UTCI strong-heat-stress working hours: Sevilla 552 → 842 a year by 2050.
5. **ERA5 under-reads hot afternoons by about 1 °C at Sevilla and Hawarden** compared with airport stations, so results are, if anything, slightly low.
