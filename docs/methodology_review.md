# Methodology Review: a Building Services Engineering Perspective

**Scope:** the heat-risk method as built in Phases 1–3 (weather files, future morphing, WBGT/UTCI, indoor assumption, process limits) and how the dashboard presents it.
**Reviewer stance:** an experienced mechanical engineer in building services (HVAC design, thermal modelling, overheating assessment to CIBSE TM52/TM59, plant selection to ASHRAE/CIBSE design conditions). The question asked is: *are the assumptions valid for decisions about people and processes inside real factory buildings, and what would make them more defensible?*
**Status:** review of the proof of concept, Nov 2026. Two quick tests were run to put numbers on the biggest questions (section 2).

---

## 1. Verdict in brief

| Area | Verdict | Effect on results |
|---|---|---|
| Outdoor climate hazard (temperature, humidity, sun) | **Sound for screening.** ERA5 + ISO 15927-4 + quantile morphing is a defensible, standard-practice chain | Peaks understated by ~1 °C at some sites (section 2b) |
| Future climate | **Sound**, with known limits (heatwave length not changed; 6-model sample) | Probably slightly conservative on persistence |
| Outdoor worker heat stress (WBGT in sun) | **Appropriate.** Liljegren is the reference outdoor model | Slight underestimate (ERA5 peaks, no hot ground surfaces) |
| **Indoor worker heat stress** | **Not yet representative of a factory hall.** "Indoor = outdoor + fixed offset" ignores how buildings behave | **Main uncertainty.** Indoor results are very sensitive to the offset (Sevilla: 3 → 37 days a year from +0 → +4 °C) |
| UTCI indoors | **Appropriate for naturally ventilated / unconditioned halls** (warehouses, hangars), provided it gets indoor inputs. The first version used outdoor wind, which overstated cooling | Fixed: hall temperature with heat gain, still air, radiant = air (roof radiant heat still to add). PMV / adaptive only for conditioned rooms |
| Process limits | **Not meaningful as built.** Conditioned processes depend on HVAC plant capacity, not on outdoor air temperature directly | Reframe as plant design-condition exceedance |
| Degree-hours | Fine as a direction-of-travel signal; sensible-only | Understates latent (humidity) cooling load |

**Overall:** the outdoor hazard chain is good enough to stand behind. The indoor and process conclusions should be presented as **sensitivity ranges, not results**, until the building response is modelled or measured. The single most valuable improvement is to replace the fixed indoor offset with a **calibrated or simulated hall temperature**, using the weather files this tool already produces.

---

## 2. Two quick tests

### 2a. Indoor air speed vs indoor heat gain (working hours, 2015–2025, typical year)

The first indoor version used the *outdoor* wind (median 1.8–2.9 m/s at 2 m, floor ~1 m/s). A warehouse or hangar with exhaust ventilation and no active cooling runs at roughly 0.1–0.3 m/s in the occupied zone, higher near openings and fans. **Decision D52:** indoor WBGT and indoor UTCI now both use a configurable occupied-zone air speed of **0.3 m/s** (sensitivity 0.2 and 0.5 m/s). The test:

| Site | Hall | WBGT days > 28: outdoor wind (old) | 0.2 m/s | 0.3 m/s | 0.5 m/s | UTCI hours > 32: 0.2 / 0.3 / 0.5 m/s |
|---|---|---|---|---|---|---|
| Sevilla | +0 °C | 2 | 4 | 3 | 3 | 542 / 542 / 549 |
| Sevilla | +4 °C | 32 | 39 | 37 | 36 | 1,144 / 1,144 / 1,154 |
| Toulouse | +4 °C | 10 | 11 | 10 | 10 | 437 / 437 / 440 |
| Marignane | +4 °C | 8 | 10 | 9 | 9 | 610 / 610 / 617 |
| Getafe | +4 °C | 0 | 2 | 1 | 0 | 828 / 828 / 838 |

**Reading:**
- Replacing outdoor wind with indoor air speed matters: indoor results rise (Sevilla +4 °C: 32 → 37 WBGT days; UTCI hours above 32 about +20 % vs outdoor wind).
- Within the plausible warehouse range (0.2–0.5 m/s), air speed is second-order (1–3 days). UTCI cannot resolve speeds below ~0.33 m/s at body height (its 10 m wind input has a 0.5 m/s floor).
- In very hot air (above skin temperature) more air movement adds heat: UTCI shows slightly *more* stress at 0.5 m/s. Fans are therefore not a reliable mitigation above roughly 35 °C, which matters for adaptation advice.
- **The hall's heat gain over outdoor remains first-order.** That is where the modelling effort should go.

### 2b. ERA5 against airport weather stations (Meteostat, 2015–2025)

| | Sevilla | Toulouse | Hamburg (Fuhlsbüttel, ~10 km) | Hawarden (Broughton) |
|---|---|---|---|---|
| Mean temperature bias (ERA5 − station) | −0.15 °C | +0.03 | +0.04 | −0.06 |
| **Summer daily maximum bias** | **−1.1 °C** | +0.1 | −0.1 | **−0.8** |
| Hottest hour (station / ERA5) | 44.5 / 43.6 | 42.3 / 42.2 | 38.4 / 37.8 | **36.6 / 33.9** |
| Days above 30 °C a year (station / ERA5) | 123 / 115 | 41 / 45 | 5.8 / 5.4 | 1.0 / 0.3 |
| Summer dew point bias | +0.5 °C | +0.2 | +0.2 | +0.5 |

**Reading:** ERA5 is excellent on averages. It under-reads afternoon peaks where the 25 km cell mixes the site with cooler surroundings (inland Andalusia; Hawarden, where the cell includes the Dee estuary), and it misses record peaks such as Hawarden's 36.6 °C in July 2022. A slightly moist bias partly offsets this in WBGT. Design work normally uses station-based data, so this matters for credibility with engineers.

---

## 3. Findings and suggestions by area

### 3.1 Climate inputs

**What's sound:** ERA5 hourly is consistent, complete and has all the variables WBGT and UTCI need. 11 years meets the ISO 15927-4 minimum (≥ 10). Recording the grid point and its distance is good practice.

**Issues**
- **Peak bias at some sites** (2b). WBGT and exceedance counts depend on peaks, so a 1 °C low bias in afternoon maxima matters.
- **Grid sharing:** Getafe and Illescas share one ERA5 cell, so their historical weather is identical.
- **Site microclimate:** most plants sit on airfields or industrial estates with large paved aprons and roofs. These are warmer than the cell average, especially in the evening.

**Suggestions**
1. **Bias-correct ERA5 to the nearest airport station** (most plants are next to one), using monthly quantile mapping of temperature and dew point. Keep ERA5 for radiation and wind. This keeps hourly completeness and gains station-level peaks. *Effort: low–medium. Data: Meteostat/NOAA ISD (licences: check commercial terms).*
2. Or use **ERA5-Land (0.1°)** for temperature and humidity to separate nearby sites. It has no direct-beam radiation, so keep ERA5 radiation.
3. **Validate against published design data:** compare the TMY and hot year with ASHRAE Handbook climatic design conditions (0.4 %/1 % dry bulb with mean coincident wet bulb; 1 % wet bulb) for each airport station. Engineers will check this first.

### 3.2 Typical and hot years

**What's sound:** ISO 15927-4 is the right standard for a reference year. Analysing all 11 years, instead of building an artificial extreme year, is a good choice.

**Issues**
- A TMY is chosen for *typicality across all months*, so its summer can be mild. It is right for energy, not for overheating.
- The hot year is ranked on shaded WBGT degree-hours, which are near zero at the UK and North Sea sites. There the choice is essentially arbitrary (the UK picks 2016, not the dry heat of 2022).
- 11 years gives a weak 90th percentile (roughly the 2nd-hottest year).

**Suggestions**
1. For overheating and heat stress, add **Design Summer Years following CIBSE TM49** (weighted cooling degree-hours, with *moderately warm*, *intense* and *long* variants). This is the UK building-services norm, the method transfers to other sites, and it gives engineers a familiar reference.
2. Rank the hot year on a **site-relevant** metric: outdoor WBGT or dry-bulb degree-hours where shaded WBGT is near zero.
3. Where ERA5 allows, extend the baseline for extremes statistics only (e.g. 1995–2025 for return periods) while keeping 2015–2025 as the "today" climate.

### 3.3 Future climate and morphing

**What's sound:** morphing (Belcher et al.) is the building-services standard (CIBSE, CCWorldWeatherGen). The quantile-based temperature version, the specific-humidity treatment, mid-month interpolation and the 95th-percentile cap are improvements on common practice. Six bias-corrected models spanning sensitivity is a reasonable sample.

**Issues**
- **Heatwave length is not changed.** Morphing keeps historical day-to-day sequences, so future heatwaves are as long as past ones. Projections show longer events; the effect is underestimated duration and consecutive-day stress, which matters for buildings with thermal mass and for worker fatigue.
- **Model choice and "hot models":** two of six models have high climate sensitivity. Medians are robust, but ranges are wide and partly reflect single-run variability (e.g. Hamburg 2040).
- **Communication:** clients increasingly expect global warming levels (GWL 1.5/2/3 °C), as used by UKCP and IPCC AR6.

**Suggestions**
1. Report **heatwave metrics** that morphing cannot change (consecutive days above threshold) with a caveat, or add a **stochastic weather generator** step for persistence (e.g. UKCP-style or Climate Change World Weather File variants) at a later stage.
2. Add a **GWL view** (time-independent): deltas conditioned on global warming of 1.5, 2 and 3 °C.
3. Use **more realisations** (initial-condition members) to separate model uncertainty from internal variability.

### 3.4 Indoor environment: the main issue

**Current assumption (D14):** hall air temperature = outdoor dry bulb + a uniform offset (0/2/4 °C), same moisture, no radiant gain, outdoor wind.

**Why a building services engineer would not accept this as a result**
- **Thermal mass and lag:** heavy halls damp and delay the outdoor peak. The indoor peak can be *lower* than outdoor in the afternoon and *higher* overnight. A uniform offset gets both wrong.
- **Internal gains:** process plant, lighting, people, compressed air, curing ovens and autoclaves add heat. Aerospace assembly halls are moderate (perhaps 10–30 W/m²); paint, curing and machining areas are higher.
- **Roof solar gain and stratification:** large, low-mass roofs with rooflights drive the hall's summer response. Tall hangars (15–30 m) stratify, so the occupied zone (0–2 m) can be several °C cooler than the roof void. Mezzanines and work platforms near the roof are much hotter.
- **Radiant temperature:** "no radiant gain indoors" is not right either. Poorly insulated roofs reach 40–60 °C soffit temperatures in sun, raising the mean radiant temperature at working level, as do hot process surfaces. Globe temperature indoors is often 2–5 °C above air temperature in summer.
- **HVAC:** many aerospace halls are mechanically ventilated, some with cooling (clean rooms, composite layup, paint) and some with evaporative cooling. Cooling also dehumidifies, so "same moisture" overstates indoor humidity in cooled spaces and understates it where evaporative cooling is used.
- **Night ventilation and operating schedules** change the result materially.

**Suggestions, best first**
1. **Calibrate from measurements (highest value).** Most plants have BMS trend logs of hall temperature (and sometimes RH). Regress hall temperature on outdoor temperature, solar radiation and time of day per hall type. That gives an evidence-based indoor model, and it can be done quickly with a year of data. *Data needed: BMS trends per hall.*
2. **Simulate archetypes.** Export the TMY, hot-year and morphed files as **EPW** and run dynamic thermal models (EnergyPlus, IES VE, TAS) for 3–4 hall archetypes: heavy assembly hangar, light-roof hangar, conditioned clean room, paint/cure shop. Use the resulting indoor operative temperature and humidity for WBGT. This is standard CIBSE TM52/TM59-style practice.
3. **Interim (no client data):** replace the uniform offset with a simple **hourly hall model** (ISO 52016-1 / 5R1C lumped resistance–capacitance) with archetype inputs: roof U-value and absorptance, rooflight fraction, internal gains, ventilation rate and night purge, and optional cooling with a capacity limit. This gives a time-varying indoor temperature, lag and the effect of mass. *Effort: medium.*
4. Indoor **mean radiant temperature** from roof soffit temperature (roof U-value + sol-air temperature) and internal surfaces, not equal to air.
5. Indoor air speed: **done** (D52, 0.3 m/s for an exhaust-ventilated hall, configurable). Next, link it to the ventilation design (air change rate, opening locations) once a hall model exists, and treat fans as a mitigation only below ~35 °C.

### 3.5 Worker heat stress (WBGT)

**What's sound:** Liljegren is the reference outdoor WBGT model (the basis of the US National Weather Service WBGT forecasts). ISO 7243 Class 2 (moderate, acclimatised, 28 °C) is a reasonable default for aircraft assembly. Shift-level reporting is useful.

**Issues**
- **Indoor formula:** ISO 7243 uses WBGT = 0.7·Tnw + 0.3·Tg indoors (no sun). Running the outdoor Liljegren formula (0.7·Tnw + 0.2·Tg + 0.1·Ta) with zero solar is close but not identical. It also inherits outdoor wind and a globe temperature near air temperature, which is not true for warm roofs (3.4).
- **Clothing and PPE:** ISO 7243 and ACGIH apply a **clothing adjustment value (CAV)**: about +0.5 °C (SMS coveralls), +1 °C (polyolefin coveralls) and much more for vapour-barrier suits. Paint-shop and composite workers in coveralls and respirators are a real at-risk group not yet represented.
- **Metabolic rate varies by task:** overhead drilling and riveting can be Class 2–3, inspection Class 1. A single class understates risk for heavier tasks.
- **Exceedance metric:** "a working hour above 28 °C" triggers further assessment under ISO 7243. It is not proof of harm. ISO 7933 (Predicted Heat Strain) or ACGIH work–rest regimes translate exceedance into **allowable exposure time / lost work time**, which is what operations managers act on.
- **Acclimatisation is seasonal:** early-season heatwaves hit unacclimatised workers (26 °C reference). The tool shows this but does not apply it to May–June events automatically.

**Suggestions**
1. Compute indoor WBGT with the **ISO 7243 indoor formula** and indoor Tg from the hall model (3.4), Tnw at indoor air speed.
2. Add **workforce groups** with metabolic class and CAV (assembly, paint/composite in PPE, logistics outdoors).
3. Add **work–rest / lost-time** outputs (ACGIH TLV regimes or ISO 7933), and later an ILO-style work-capacity function. This is the bridge to cost.
4. Apply the **unacclimatised reference** to the first heat episode of the season.

### 3.6 Thermal comfort (UTCI)

*Revised after discussion with the consultant.* An earlier draft of this review recommended PMV indoors. For **naturally ventilated, unconditioned spaces** such as warehouses, logistics halls and assembly hangars, **UTCI is the better index**:
- PMV (ISO 7730) assumes near-steady, moderate conditions (roughly 10–30 °C air, PMV within ±2), with clothing and activity entered as fixed values. It is designed for conditioned, mostly sedentary spaces and becomes unreliable in hot, variable, radiant-asymmetric halls.
- UTCI's multi-node physiological model handles strong heat, radiation and air-movement swings. Its reference activity (~135 W/m², walking about 4 km/h) is closer to warehouse and assembly work than office PMV.
- Adaptive comfort (EN 16798-1 / ASHRAE 55) targets occupants who can open windows and change clothing at low activity, so it also doesn't fit industrial work.

**Conditions for using UTCI indoors** (implemented as decision D51 after this review):
- **Air movement:** UTCI's wind input is at 10 m. Indoor air speed (typically 0.1–0.3 m/s at 1.1 m) must be converted (×~1.5); 0.5 m/s at 10 m is UTCI's lower bound and is used for still halls. The first version fed the *outdoor* wind (median ~2–3 m/s), which overstated cooling. Test: still air raises UTCI by +0.2 to +1.2 °C in hot hours, and working hours above UTCI 32 rise ~20 % at Sevilla (453 → 542 a year).
- **Hall temperature:** air temperature with the hall heat gain, same moisture. At Sevilla, hours above UTCI 32 rise to 832 at +2 °C and 1,144 at +4 °C, so again the heat gain dominates.
- **Radiant temperature:** currently equal to air temperature. Roof soffits and hot process surfaces raise it in summer (section 3.4). Add this once a hall model exists.
- **Clothing:** UTCI's clothing model adapts to temperature (outdoor behaviour). Workwear and PPE do not adapt, so UTCI may understate stress for workers in coveralls. For PPE groups, rely on WBGT with clothing adjustment values (3.5).

**Where each index fits**
| Space | Thermal stress / comfort index | Occupational limit |
|---|---|---|
| Outdoor work (aprons, yards, logistics) | UTCI in sun (SolarCal + ground long-wave to add) | WBGT in sun (ISO 7243) |
| Naturally ventilated / unconditioned halls and warehouses | **UTCI with indoor inputs** | WBGT indoor (ISO 7243 indoor formula) |
| Mechanically conditioned rooms (offices, clean rooms, paint booths) | PMV/PPD (ISO 7730) or operative-temperature bands (EN 16798-1 / CIBSE Guide A) | Usually not limiting while the plant keeps up (see 3.7) |

**Outdoor in sun:** SolarCal with ground reflectance 0.2 and no long-wave from hot ground. Concrete and asphalt aprons at 45–60 °C add substantially to outdoor radiant temperature, so outdoor UTCI in sun is likely understated. *Suggestion:* include ground long-wave (surface temperature from an energy balance or a simple sol-air approach), or use a six-direction radiation model (e.g. SOLWEIG-type) for aprons.

### 3.7 Process limits and plant resilience

**Issue:** outdoor air temperature above 35 °C says little about a paint booth or clean room, which are mechanically conditioned. Their risk is the **HVAC plant running out of capacity**, which depends on design conditions, wet bulb and latent load.

**Suggestions: reframe as plant resilience**
1. **Design-condition drift:** compute ASHRAE-style **0.4 % and 1 % dry bulb (with mean coincident wet bulb) and 1 % wet bulb / dew point** for today, 2040 and 2050. Compare with each site's plant design basis. "Today's 0.4 % design day becomes a 2 % day by 2050" is the message plant engineers act on.
2. **Hours above plant design ambient:** air-cooled chillers and condensers (often 32–35 °C design, derating above), cooling towers (wet bulb design ~20–24 °C), AHU coils (outdoor dew point / enthalpy above coil design: latent capacity for humidity-controlled paint and composite rooms).
3. **Process specs:** paint and coating application windows (temperature, RH, surface above dew point +3 °C) and composite layup room specs (typically ~18–24 °C and controlled RH) apply to the **conditioned room**, so assess them via plant capacity, not outdoor air.
4. Ask the client for **plant schedules and design bases**. This turns placeholders into real thresholds.

### 3.8 Energy indicators

Cooling degree-hours above 24 °C and heating degree-hours below 19 °C are sensible-only. In humid sites (Atlantic coast, Andalusian coast), latent load is a large share of cooling. **Suggestion:** add **enthalpy-hours** (or cooling degree-hours on wet bulb) for conditioned spaces. Keep degree-hours as direction-of-travel signals, not load estimates.

### 3.9 Uncertainty and communication

- The ranges shown are **climate model spread only**. ERA5 bias (±1 °C at peaks), morphing limits and, above all, the **indoor response** are not in the range.
- **Suggestion:** add a simple confidence rating per metric (High: outdoor temperature metrics; Medium: outdoor WBGT/UTCI; Low: indoor worker and process metrics until 3.4 is addressed). Always show the hall heat-gain sensitivity next to indoor results.

---

## 4. Prioritised improvement plan

| Priority | Action | Why | Effort | Client data needed |
|---|---|---|---|---|
| 1 | **Indoor model**: calibrate from BMS trends, or 5R1C archetypes as an interim | Indoor results are dominated by this assumption (2a) | Medium | BMS trends; hall fabric, use, HVAC |
| 2 | **Export EPW files** (TMY, hot year, 2040/2050) for dynamic thermal simulation | Lets engineers use the tool's climate in their own models; standard practice | Low | – |
| 3 | **Bias-correct ERA5 to airport stations** (temperature, dew point) | Removes ~1 °C peak bias at some sites (2b) | Low–medium | – |
| 4 | **Plant resilience metrics**: design-condition drift, hours above plant design DB/WB/dew point | Reframes process risk in engineering terms | Low–medium | Plant design bases |
| 5 | **Workforce groups**: metabolic class, PPE clothing adjustment, indoor ISO 7243 formula | Captures the real at-risk groups (paint, composite, outdoor logistics) | Low | Task and PPE profiles |
| 6 | **Indoor comfort by space type**: UTCI with indoor inputs for naturally ventilated halls (done, D51; add roof radiant heat with the hall model); PMV / operative temperature for conditioned rooms | Right index per space | Low | Which halls are conditioned |
| 7 | **Design Summer Years (CIBSE TM49)** alongside TMY and the hot year | Recognised overheating reference | Medium | – |
| 8 | **Work–rest / lost-time** outputs | Turns exceedance into operational impact | Medium | Headcount by group (later) |
| 9 | **Heatwave persistence**, GWL view, more model members | Future-climate robustness | Medium–high | – |
| 10 | **Confidence ratings** in the dashboard | Honest communication | Low | – |

## 5. Data to request from clients

- **Per hall:** use, floor area and height, roof construction (U-value, colour), rooflights, HVAC type (none / ventilation / evaporative / cooling), set points and operating hours.
- **BMS trend logs:** hall air temperature (and RH if available), ideally 12 months, with location of sensors.
- **Plant design basis:** chiller/condenser design ambient, cooling tower design wet bulb, AHU coil design conditions.
- **Workforce:** headcount by group, indoor/outdoor split, typical tasks (metabolic class), PPE, shift patterns.
- **Process specifications:** paint and coating application windows, composite room specifications, any heat-related downtime records.

## 6. Direction of bias in today's results

| Result | Likely direction | Main reasons |
|---|---|---|
| Days above 30 °C, outdoor temperature metrics | Slightly **low** at some sites | ERA5 peak bias (2b) |
| Outdoor WBGT / UTCI in sun | Slightly **low** | ERA5 peaks; no hot-ground long-wave |
| **Indoor WBGT (hall = outside)** | **Likely low** for unconditioned halls in summer afternoons in the south; **may be high** for heavy or cooled halls | No internal gains, roof radiant or PPE; no thermal mass or cooling |
| Process exceedance hours | **Not interpretable** as risk | Outdoor air ≠ conditioned room conditions |
| Future change (deltas) | Reasonable; **low** on heatwave duration | Morphing keeps historical sequences |

## References (methods named above)

- Liljegren J.C. et al. (2008), *Modeling the wet bulb globe temperature using standard meteorological measurements*, J. Occup. Environ. Hyg. 5(10).
- ISO 7243:2017 (WBGT); ISO 7933 (Predicted Heat Strain); ISO 7730 (PMV/PPD); ISO 7726 (instruments); ISO 15927-4 (reference years); ISO 52016-1 (hourly building energy).
- ACGIH TLVs for heat stress (work–rest regimes, clothing adjustment values).
- CIBSE Guide A (environmental design); CIBSE TM49 (design summer years); TM52 / TM59 (overheating).
- ASHRAE Handbook Fundamentals, climatic design conditions; ASHRAE 55 (SolarCal); ASHRAE 169.
- EN 16798-1 (indoor environmental input parameters).
- Belcher S.E., Hacker J.N., Powell D.S. (2005), *Constructing design weather data for future climates*, BSERT 26(1).
- Bröde P. et al. (2012), *Deriving the operational procedure for the Universal Thermal Climate Index (UTCI)*.
- ILO (2019), *Working on a warmer planet*.
