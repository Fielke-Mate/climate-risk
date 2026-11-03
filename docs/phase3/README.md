# Phase 3: Heat-stress metrics

**Status:** complete (Nov 2026). The methods are in `src/climate_risk/heat.py`, and the per-year indicators in `src/climate_risk/annual.py`. They run inside `scripts/phase1_historical.py` and `scripts/phase2_future.py`. Settings are in `config/settings.yaml` → `heat`.

## Methods

| Metric | Method | Notes |
|---|---|---|
| **WBGT, outdoor in sun** | Liljegren et al. (2008), via `pywbgt` (Argonne C code) | Temperature, dew point, pressure, 10 m wind (adjusted to 2 m), global solar radiation, sun position |
| **WBGT, indoor** | The same model with solar radiation = 0 and 0.3 m/s air speed (D52: exhaust-ventilated warehouse, no active cooling) | Hall at outdoor temperature (D14), with sensitivity cases at +2 and +4 °C (same moisture) |
| **Reference** | ISO 7243 Class 2 (moderate work): **26 °C not acclimatised (headline, D58)**; 28 °C acclimatised (sensitivity) | Working hours 06:00–22:00 local |
| **Worker profiles (D59)** | Reference per profile, not acclimatised / acclimatised: light 29/30, moderate 26/28 (default), moderate in disposable coveralls + hood 24/26 (clothing adjustment +2), heavy 22/25 | Columns `*_gt_ref` = default profile; `*_gt_ref_<profile>` for the others; `_acc` = acclimatised; `_early/_late/_night` = shifts |
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

A heat-safety day has at least one working hour above WBGT 26 °C (ISO 7243 Class 2, workforce not acclimatised, D58): the default worker profile, moderate work in work clothes (D59). The UTCI column does not depend on the WBGT reference.

| Site | Indoor, hall = outside | Indoor +2 °C | Indoor +4 °C | Outdoor in sun | Working hours of strong UTCI heat stress indoors (>32, hall = outside) |
|---|---|---|---|---|---|
| Sevilla (San Pablo) | 36 → 59.5 | 52 → 79 | 76 → 98.5 | 124 → 143.5 | 552 → 842.5 |
| Illescas | 1 → 13 | 9 → 29.5 | 24 → 50.5 | 73 → 96.5 | 395 → 662.5 |
| Getafe | 1 → 13.5 | 9 → 30 | 24 → 51 | 73 → 95 | 395 → 654.5 |
| Marignane | 9 → 24.5 | 18 → 41.5 | 33 → 59 | 64 → 86 | 134 → 343 |
| Toulouse (Blagnac) | 10 → 23 | 18 → 33 | 28 → 47.5 | 57 → 74.5 | 116 → 277 |
| Nantes (Bouguenais) | 0 → 3.5 | 4 → 7 | 7 → 12.5 | 21 → 29 | 26 → 61.5 |
| Saint-Nazaire (Montoir-de-Bretagne) | 0 → 1 | 1 → 3 | 3 → 7 | 12 → 21.5 | 2 → 12 |
| Donauworth | 0 → 1 | 0 → 6.5 | 1 → 11 | 22 → 38.5 | 5 → 49 |
| Meaulte | 0 → 2 | 1 → 5 | 4 → 7.5 | 13 → 20 | 13 → 36.5 |
| Filton | 0 → 0 | 0 → 0 | 0 → 2.5 | 5 → 8 | 0 → 2 |
| Bremen | 0 → 2 | 0 → 6 | 3 → 10.5 | 11 → 22 | 6 → 35.5 |
| Broughton | 0 → 0 | 0 → 0 | 0 → 0.5 | 3 → 5 | 0 → 0 |
| Nordenham | 0 → 0.5 | 0 → 1.5 | 1 → 6.5 | 5 → 14 | 0 → 5.5 |
| Hamburg-Finkenwerder | 0 → 2.5 | 0 → 5.5 | 2 → 11 | 10 → 20.5 | 6 → 30.5 |
| Stade | 0 → 1.5 | 0 → 4.5 | 2 → 10.5 | 9 → 19 | 3 → 27 |

## Findings

1. **With the hall at outdoor temperature, indoor heat-safety days are already material in the south** (exhaust-ventilated hall, 0.3 m/s, 26 °C reference): Sevilla 36 → 60 days by 2050 (SSP5-8.5), Marignane 9 → 25, Toulouse 10 → 23, Getafe/Illescas 1 → 13. Northern sites stay at 0–4 days. At the acclimatised reference (28 °C) the same cases were Sevilla 3 → 24, Toulouse 1 → 8, Marignane 0 → 6, so the choice of reference (D58) matters more than the climate scenario.
2. **Indoor results depend on the hall heat gain.** At +4 °C, Sevilla reaches 76 → 99 days, Marignane 33 → 59, Getafe/Illescas 24 → 51 and Toulouse 28 → 48; northern German sites reach about 10–11 days by 2050. Engineering estimates of hall temperatures are the key missing input (see [methodology review](../methodology_review.md)).
3. **Outdoor work in sun is where today's risk is clearest:** Sevilla 124 → 144 days, Madrid sites 73 → ~96, Marignane 64 → 86, Toulouse 57 → 75, Donauwörth 22 → 39; even the UK sites have 3–8 days.
4. **Indoor air speed:** replacing outdoor wind with 0.3 m/s raises indoor results (Sevilla +4 °C at the 28 °C reference: 32 → 37 days); within 0.2–0.5 m/s it is a minor factor. Indoor UTCI strong-heat-stress working hours: Sevilla 552 → 842 a year by 2050.
5. **ERA5 under-reads hot afternoons by about 1 °C at Sevilla and Hawarden** compared with airport stations, so results are, if anything, slightly low.
