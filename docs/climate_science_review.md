# Methodology Review: a Climate Science Perspective on Future Hot Years

**Scope:** how the future weather files (Phase 2) represent heat extremes: the delta source, quantile morphing, the typical and hot years, and how 2040/2050 results are reported.
**Reviewer stance:** an independent climate scientist who builds future weather files and models heatwaves. The question is: *research shows heat extremes are strongly amplified as the climate warms. Does the method capture that, and where could it do better?*
**Status:** review of the proof of concept, Nov 2026. Three quick tests were run to put numbers on the main questions (section 2). The building-services review ([`methodology_review.md`](methodology_review.md)) covers indoor conditions, WBGT and process limits. This review doesn't repeat it.

---

## 1. Verdict in brief

"Extremes are amplified" covers several different effects. The method handles some of them well and some not at all:

| Form of amplification | What the research says | How our method handles it | Verdict |
|---|---|---|---|
| **1. Threshold effect:** a small shift in the mean causes a much larger rise in hours above a fixed limit | Robust. It comes straight from the shape of the distribution | **Fully captured.** Every hour of 11 real years is shifted and counted against the threshold | ✅ The main driver of our results: indoor WBGT hours above 26 °C at Getafe go from 2 to ~62 a year by 2050 (SSP5-8.5), with no change in distribution shape |
| **2. Summer warms faster than the year** | Robust over southern and central Europe (soil drying, less cloud) | **Captured.** Deltas are by calendar month | ✅ Summer median-day Tmax warms 1.3–1.7× the local annual mean in Spain, southern France and the UK, ~1.1× in north Germany (2050, SSP5-8.5) |
| **3. Hot days warm faster than average summer days** | Seen in observations for western and north-western Europe. **Climate models underestimate it** (Vautard 2023, Patterson 2023, Kornhuber 2024) | **Partly captured.** Quantile morphing passes on the models' hot-day signal. But (a) the signal in our deltas is about as large as the sampling noise (2b), and (b) models are probably too conservative here | ⚠️ Main gap. Likely **underestimates** hot-day warming in France, Germany and the UK |
| **4. Longer, more frequent and more persistent heatwaves** | Projected with high confidence | **Not captured.** Morphing keeps the historical day-to-day sequence, so a 5-day heatwave stays 5 days | ❌ Underestimates multi-day events and consecutive-day stress |
| **5. Unprecedented ("record-shattering") events** | Their likelihood grows quickly with the rate of warming (Fischer et al. 2021) | **Not captured.** The hottest possible future day is the hottest 2015–2025 day plus its delta. The baseline doesn't include 2003 | ❌ No "plausible worst case" |
| **6. Humid heat on the hottest days** | Depends on the region: drier hot days inland, more humid ones on the coast | **Partly captured.** One monthly specific-humidity ratio is applied to every hour | ⚠️ Second order for WBGT. Worth a check |

**Overall:** the method captures the most important form of amplification for this tool, the non-linear growth of hours above a fixed limit, and it does that well. The quantile-morphing chain is sound and above common practice. The gaps are **(3) hot-day amplification beyond what models simulate, (4) persistence and (5) unprecedented events.** All three bias the results **low**. A +1 °C hot-day stress test (2c) changes indoor WBGT hours by **+11 % to +67 %**, about as much as the whole 6-model range. Results should be presented as **central estimates with a stated high-end storyline**, not as an upper bound.

---

## 2. Three quick tests

### 2a. What the deltas contain (summer daily maximum, SSP5-8.5, 2050, median of 6 models)

| Site | Annual mean warming | Summer median day (q50) | Summer hot day (q95) | q95 − q50 | q95 ÷ annual |
|---|---|---|---|---|---|
| Illescas | 1.55 | 2.61 | 2.44 | −0.17 | 1.6 |
| Getafe | 1.53 | 2.64 | 2.54 | −0.10 | 1.7 |
| Sevilla | 1.36 | 1.91 | 2.03 | +0.12 | 1.5 |
| Marignane | 1.32 | 1.76 | 1.91 | +0.15 | 1.4 |
| Toulouse | 1.30 | 2.12 | 2.39 | +0.27 | 1.8 |
| Donauwörth | 1.58 | 1.83 | 2.40 | +0.57 | 1.5 |
| Filton | 0.91 | 1.16 | 1.97 | +0.81 | 2.2 |
| Bremen | 1.33 | 1.51 | 2.50 | +0.99 | 1.9 |
| Hamburg-Finkenwerder | 1.36 | 1.44 | 2.62 | +1.18 | 1.9 |

**Reading:**
- The hottest summer days warm **1.4–2.2× as much as the annual mean** at every site. So amplification is present everywhere, including Spain. The concept note's statement that amplification is "not borne out" in Iberia is misleading. In Spain the whole summer distribution shifts strongly (median day +2.6 °C at Getafe). In the north the hot tail stretches more than the median.
- Indicative comparison with observations: roughly 1 °C of global warming separates 2015–2025 from 2041–2060 under SSP5-8.5. So these hot-day changes are about 1.5–2.5 °C per °C of global warming. Vautard et al. (2023) found hot extremes in western Europe rose by **~3.4 °C per °C** of global warming since 1950. None of 170 model simulations reproduced the circulation-driven part of that trend. That is evidence that the deltas are on the **conservative side** for the French, German and UK sites.

### 2b. Is the hot-day signal robust? (scenario-pair test)

Up to 2040, SSP2-4.5 and SSP5-8.5 differ by only ~0.1–0.2 °C of global warming. For the same model and site, the two scenario runs should therefore give almost the same deltas. Any difference is mostly **internal variability**: the single run, the 11-year model baseline and the 20-year future window.

| Per model and site, 2040, SSP5-8.5 minus SSP2-4.5 | Spread |
|---|---|
| Summer median-day Tmax delta | SD **0.77 °C** (range −1.1 to +2.5) |
| Hot-day amplification (q95 − q50) | SD **0.68 °C** (range −1.8 to +1.4) |
| Share of the 12 model-scenario runs with q95 > q50 at 2050 | Spanish sites 25–58 %; north Germany 100 % |

**Reading:**
- The noise in the hot-day amplification (±0.7 °C) is **as large as the signal** (0 to +1.2 °C). Only the north German sites show a consistent sign. The Spanish "no amplification" result can't be told apart from noise.
- The **min–max range shown to clients is largely internal variability, not model disagreement**, especially for 2040.
- The cause is the **11-year single-run model baseline**. More models, pooled neighbouring months or pooled scenarios would cut this noise substantially (section 3.1).

### 2c. How much do the results depend on the tail? (sensitivity test)

All 11 ERA5 years were re-morphed for four sites under SSP5-8.5, 2050, for each of the 6 models, with four versions of the Tmax/Tmin deltas. The "current" case reproduces the pipeline's published values exactly. Script: [`scripts/review_tail_sensitivity.py`](../scripts/review_tail_sensitivity.py); year-level results: `outputs/review/tail_sensitivity_years.csv`.

- **mean:** no change in shape (every percentile gets the median-day delta), i.e. classic morphing
- **current:** as built (quantile deltas 5th–95th percentile, flat above the 95th)
- **no cap:** above the 95th percentile, the 90th→95th slope is extended to the 99.9th percentile (where it is positive)
- **+1 °C hot days:** stress test. The Tmax delta is raised by up to +1 °C on hot days (0 at the median, rising to +1 °C from the 90th percentile)

**Indoor WBGT working hours above 26 °C (hall = outdoor), typical year, model median**

| Site | Today | 2050: mean | **current** | no cap | +1 °C hot days | Current 6-model range |
|---|---|---|---|---|---|---|
| Sevilla | 197 | 398 | **420** | 420 | 466 (+11 %) | 335–466 |
| Getafe | 2 | 60 | **63** | 63 | 93 (+48 %) | 47–104 |
| Toulouse | 59 | 149 | **149** | 149 | 169 (+14 %) | 117–208 |
| Hamburg | 0 | 1 | **9** | 10 | 15 (+67 %) | 2–18 |

**Hot year (90th percentile year), same metric**

| Site | Today | 2050: mean | **current** | no cap | +1 °C hot days |
|---|---|---|---|---|---|
| Sevilla | 234 | 477 | **499** | 499 | 556 |
| Getafe | 12 | 123 | **121** | 121 | 183 |
| Toulouse | 75 | 195 | **228** | 236 | 265 |
| Hamburg | 2 | 8 | **18** | 18 | 27 |

**Reading:**
- **The threshold effect dominates.** Most of the change from today to 2050 appears even with no change in shape ("mean").
- **Quantile morphing matters in the north.** Hamburg's hours rise ×2–9 compared with classic morphing. Keep it.
- **The 95th-percentile cap (D44) is not the problem.** Removing it changes results by 5 % or less, because the models' own 90→95 slope is small. Yet the hazardous days *are* in the capped zone: 100 % of Sevilla's days above 40 °C, 76 % of Hamburg's days above 30 °C and 54 % of Toulouse's days above 35 °C are above the monthly 95th percentile. So the **size** of the hot-day delta matters, not how it is extrapolated.
- **A +1 °C hot-day stress test adds about as much as the whole model range.** That size is set by the 2b noise and the observed-vs-modelled gap in 2a. The effect is largest where the limit sits in the tail (Getafe +48 %, Hamburg +67 %) and smallest where much of the summer is already above it (Sevilla +11 %).

---

## 3. Findings and suggestions

### 3.1 Noise in the climate-change signal

**What's sound:** NEX-GDDP-CMIP6 at 0.25° is a reasonable, open, bias-corrected source. Deriving deltas by month and by quantile is correct. A baseline window that matches ERA5 2015–2025 is sensible.

**Issues**
- Each delta compares one model run's 20-year future with **its own 11-year baseline**. Internal variability in that baseline goes straight into every delta for that model (2b).
- Quantiles for single calendar months rest on ~340 baseline days. The 95th percentile rests on ~17.

**Suggestions**
1. **Use more models.** NEX-GDDP-CMIP6 has 35. 10–15 models, chosen to span climate sensitivity, average out much more internal variability than 6 single runs.
2. **Pool ±1 month** (a 3-month moving window) when estimating quantiles, so each month uses ~3× more days.
3. Optionally **smooth the quantile-delta curve** (e.g. fit delta = a + b·z, with z the normal score of the percentile). It's more stable in the tail and makes the cap unnecessary.

*Not recommended (decided with the consultant): lengthening the model baseline window.* A 30-year window centred on 2020 would cut noise further, but it pulls in cooler early years, and it only keeps the 2020 centre if warming is close to linear. The ERA5 record shows how big that effect is: 2000–2009 summers were 0.8–1.5 °C cooler than 2015–2025 at most sites (section 3.4). Keep the model baseline at 2015–2025 to match ERA5.

*Effort: low–medium (one more NEX download; the delta code changes only slightly). This is the cheapest way to make the hot-day signal believable.*

### 3.2 Hot-day amplification likely too low in western Europe

**Issues**
- Observed hot extremes in western Europe have risen faster than models simulate (Vautard et al. 2023: ~3.4 °C per °C of global warming; ~0.8 °C of that from more frequent southerly flow, which none of 170 simulations reproduced). North-west Europe's hottest days have warmed about **twice as fast** as average summer days (Patterson 2023: England and Wales ~0.58 vs 0.26 °C per decade). Models capture the mean but not this gap. Kornhuber et al. (2024) find similar "hotspots" worldwide, also underestimated by models.
- The causes (circulation trends, aerosol reductions, soil drying) are not settled. So this is **deep uncertainty**, not a known bias to correct.
- **Bias correction may further dampen the tail signal.** NEX-GDDP-CMIP6 preserves each model's trend as a **9-year running mean per month**, then quantile-maps against a historical reference. That keeps the mean change by design. Changes in the shape of the distribution pass through the historical transfer function and are not guaranteed to be kept. (QDM, or ISIMIP3BASD [Lange 2019], preserve changes at every quantile.)

**Suggestions**
1. **Add a high-amplification storyline** alongside the model median and range, e.g. "+1 °C extra on hot days" (as in 2c) or "hot days warm twice as fast as the summer median" for the northern sites. Label it a **plausible high-end storyline** (Shepherd et al. 2018), not a projection. ESRS E1 and IFRS S2 users expect a high-end case; this gives them one that can be explained.
2. **Benchmark** the hot-day deltas for 2–3 sites against **raw CMIP6 daily tasmax** (or ISIMIP3b) for the same models. If NEX damps the q95 change, switch the delta source or apply the raw-model quantile changes.
3. **Benchmark against observations:** compare the ERA5 1979–2025 trend in each site's summer q95 Tmax with the models' historical trend. Where observations run well ahead (likely north Germany, northern France, UK), flag that site's results as possibly conservative.

### 3.3 Heatwave persistence (duration and frequency)

**Issue:** morphing changes how hot each day is, not the order of days. Future heatwaves have the same length and timing as 2015–2025 events. Duration matters for both use cases: heat strain builds up over consecutive days, and building mass heats up over a multi-day event (building-services review, 3.4).

**Suggestions**
1. **Use the NEX daily data directly for persistence metrics (low effort, data already downloaded):** for each model, count heatwave events, the longest run of days with Tmax > 30/35 °C and consecutive tropical nights in the bias-corrected 20–30-year future series, against the same metrics for the baseline. Report them as a **daily-resolution companion** to the hourly morphed results. The hourly WBGT counts stay as they are.
2. **Storyline heatwaves:** take a real event (the 2019 or 2022 heatwave, or **2003**, which is outside the baseline) and build a lengthened future version (e.g. its peak week repeated or extended by the projected increase in duration). Run it through the WBGT and hall calculations. This gives clients a concrete "what if", much like the hot reference year now.
3. Later: a **stochastic weather generator** conditioned on future statistics (as in UKCP or the CCWorldWeatherGen variants) for full persistence.

### 3.4 Unprecedented events and return periods

**Issues**
- With 11 years, the "hot year" (90th percentile) is roughly the second-hottest year, about 1-in-10 (concept 4c already notes this). Nothing in the files is more extreme than 2015–2025 plus the delta.
- **2003**, Europe's benchmark heatwave (France especially), is outside the baseline. So is 2010.
- Record-shattering events become more likely the faster the climate warms (Fischer et al. 2021). Europe is warming fast.

**Suggestions**
1. **Extend the ERA5 record back to 2000, with every year adjusted to the 2020 climate.** See the test below.
2. Fit a **non-stationary GEV** to annual maximum daily Tmax and WBGT, with global temperature as covariate. Report **1-in-20 and 1-in-50-year values** for today, 2040 and 2050. That answers the client question "how hot could it get?", which counts cannot.
3. For a true worst case, consider the **UNSEEN** method (large seasonal-forecast ensembles, e.g. SEAS5) at one or two pilot sites. *Effort: high. Research-grade.*

**Test: what would a 2000–2025 baseline change?** ERA5 2000–2025 at eight sites ([`scripts/review_baseline_2000.py`](../scripts/review_baseline_2000.py), `outputs/review/baseline_2000.csv`). "Adjusted" shifts each year by the site's summer Tmax trend to 2020 (a simple uniform shift, to show the size of the effect).

| Site (hot-day threshold) | Summer Tmax, 2000–09 vs 2015–25 | Median days above threshold: 2015–25 / 2000–25 raw / 2000–25 adjusted | 2003 rank (adjusted) | Longest hot spell 2015–25 | 2003 adjusted |
|---|---|---|---|---|---|
| Toulouse (35 °C) | −1.5 °C | 5 / 3 / 5 | 1st | 10 days (2022) | **12 days** |
| Marignane (35 °C) | −1.3 °C | 5 / 1 / 3 | 1st | 8 days (2025) | **14 days** |
| Nantes (30 °C) | −1.2 °C | 12 / 8 / 11 | 1st | 11 days (2022) | **12 days** |
| Donauwörth (30 °C) | −1.2 °C | 9 / 8 / 9 | 1st | 5 days (2025) | **13 days** |
| Getafe (35 °C) | −1.3 °C | 41 / 29 / 38 | 4th | 24 days (2022) | 19 days |
| Hamburg (30 °C) | −0.9 °C | 4 / 2 / 5 | 2nd | 8 days (2020) | 6 days |
| Filton (28 °C) | −0.8 °C | 5 / 1 / 2 | 1st | 6 days (2022) | 4 days |
| Sevilla (40 °C) | **+0.5 °C** | 5 / 4 / 3 | 6th | 7 days (2018) | 5 days |

**Reading:**
- **The early years are much cooler.** Summer maxima in 2000–2009 were 0.8–1.5 °C below 2015–2025, as large as the 2050 SSP2-4.5 change. Used unadjusted, the longer record would cut typical-year hot days by 20–80 % and understate today's risk. **Adjustment to today's climate is essential.**
- **Adjusted, typical years barely change** and the 90th-percentile year changes little. The gain is in the **extremes**: 2003, adjusted to today, becomes the year with the most hot days at five of eight sites. It also has the longest hot spell on record at Marignane, Donauwörth, Toulouse and Nantes (up to 14 days against 5–11 in 2015–2025).
- So a longer, adjusted baseline also helps the **heatwave-length gap** (3.3): it brings in real long events that morphing can then carry into the future.
- **Site-by-site trends are too noisy for the adjustment.** Sevilla's ERA5 cell shows summer *cooling* since 2000, unlike every other site. In production, adjust with the climate models' own warming from each year to 2020 (the existing quantile morphing, run "backwards" in time), or scale with smoothed global mean temperature. The model-based option slightly under-adjusts in western Europe, where observations warm faster than models (3.2).
- **Decisions this needs:** whether the hot reference year (D25/D42, an actual unadjusted year) may become an adjusted 2003, and whether the TMY stays on 2015–2025. Processing time grows ×2.4.

### 3.5 Humidity on hot days

**Issue:** one monthly specific-humidity ratio (summer +2 % in Madrid to +10 % in Donauwörth) is applied to every hour. In models, the hottest inland days often get relatively **drier** (soil-moisture limitation), and coastal ones more humid. WBGT is driven ~70 % by natural wet-bulb, so humidity on the hottest days matters, though less than temperature.

**Suggestions**
1. Compute the huss ratio **conditional on Tmax percentile** (e.g. days above vs below the monthly 80th percentile) from the same NEX daily data, and apply it by day like the temperature deltas.
2. Check: compare the morphed hot-day dew point change with the models' daily dew point change on their own hot days (NEX has huss and tasmax for the same day).

### 3.6 Scenario framing: global warming levels and "hot models"

**Issues**
- Two of six models (ACCESS-CM2, EC-Earth3) have climate sensitivities above the IPCC AR6 *likely* range (2.5–4 °C). By calendar year, they warm faster than the assessed central estimate (the "hot model" problem, Hausfather et al. 2022).
- Hot extremes scale closely with global warming level, largely independent of scenario (IPCC AR6 Ch. 11).

**Suggestions**
1. Compute deltas by **global warming level** (e.g. +0.5, +1.0 and +1.5 °C above 2015–2025) by pooling both scenarios at the same warming. This doubles the sample and also reduces the noise in 3.1.
2. Map warming levels to years using the **IPCC AR6 assessed warming** for each SSP. That handles hot models without throwing them away.
3. Keep "2040 / 2050 under SSP2-4.5 / SSP5-8.5" as the client-facing labels (that's what disclosures ask for). Derive the numbers from warming levels underneath.

### 3.7 Smaller points

- **The baseline isn't stationary.** 2015–2025 includes a few tenths of a degree of warming in itself. Every year is treated as "2020 climate", so 2015 is slightly cool and 2025 slightly warm for that label. Detrending the years to 2020 before morphing is cleaner. The effect is small compared with the above.
- **ERA5's low bias at peaks** (−1.1 °C summer Tmax at Sevilla, −0.8 °C at Broughton; building-services review 2b) is about half the 2050 signal at those sites. Station bias correction (that review, priority 3) also matters for extremes.
- **Tmin is morphed by its own quantile**, which is good: warm nights matter for recovery. Report warm nights alongside daytime metrics in the heat-stress story.

### 3.8 Communication

- Describe the range as **"model and natural variability range (6 models)"**, not just model uncertainty (2b).
- Call the hot year **"about a 1-in-10 year"** and say it does not include events more extreme than 2015–2025.
- Show the **high-end storyline** (3.2) as a third marker next to the median and range, for at least the headline metric.
- Update concept 4c and Phase 2 finding 3: amplification is present at every site (2a). In Spain it shows up as strong warming of the whole summer distribution, not as tail stretching, and the hot-day signal there is within the noise.
- Add a per-metric **direction of bias** note: future hot-day and heatwave metrics are more likely **low** than high.

---

## 4. Prioritised improvement plan

| Priority | Action | Why | Effort |
|---|---|---|---|
| 1 | **Less noisy deltas:** 10–15 models, ±1-month pooling (model window stays 2015–2025) | Hot-day signal is currently within noise (2b); ranges are mostly internal variability | Low–medium |
| 2 | **High-end hot-day storyline** (+1 °C hot days, or 2× median-day warming in the north) shown next to the range | Models likely underestimate western European hot-day trends; matches 2c's sensitivity; useful for disclosure | Low |
| 3 | **Heatwave persistence metrics** straight from the NEX daily series (events, longest run, consecutive warm nights) | Morphing can't change duration | Low–medium |
| 4 | **Global warming level deltas** (pooled scenarios, AR6-assessed timing) | Handles hot models; halves noise further | Medium |
| 5 | **Benchmark NEX hot-day deltas** against raw CMIP6 / ISIMIP3b and against ERA5 observed trends | Checks whether bias correction or models damp the tail | Medium |
| 6 | **Hot-day-conditional humidity deltas** | WBGT on the hottest days | Low–medium |
| 7 | **Extended detrended baseline + non-stationary GEV** return levels (1-in-20, 1-in-50) | Unprecedented events; "how hot could it get?"; brings in 2003 | Medium–high |
| 8 | **Storyline heatwave** (lengthened 2003/2019/2022 event) through WBGT and the hall model | Concrete worst-case narrative for clients | Medium |
| 9 | Stochastic weather generator / UNSEEN | Full treatment of persistence and tail | High (later) |

Priorities 1–3 address the user question directly: they make the amplification signal robust, give a defensible high-end case, and cover the duration gap. They can be done with data the pipeline already downloads, apart from extra NEX years and models.

---

## References

- Belcher S.E., Hacker J.N., Powell D.S. (2005), *Constructing design weather data for future climates*, BSERT 26(1).
- Cannon A.J., Sobie S.R., Murdock T.Q. (2015), *Bias correction of GCM precipitation by quantile mapping: how well do methods preserve changes in quantiles and extremes?*, J. Climate 28.
- Fischer E.M., Sippel S., Knutti R. (2021), *Increasing probability of record-shattering climate extremes*, Nature Climate Change 11.
- Hausfather Z. et al. (2022), *Climate simulations: recognize the 'hot model' problem*, Nature 605.
- IPCC (2021), AR6 WG1 Chapter 11, *Weather and climate extreme events in a changing climate* (incl. Fig. 11.3, regional TXx vs global warming).
- Kornhuber K. et al. (2024), [*Global emergence of regional heatwave hotspots outpaces climate model simulations*](https://pure.iiasa.ac.at/20150), PNAS 121(49).
- Lange S. (2019), *Trend-preserving bias adjustment and statistical downscaling with ISIMIP3BASD (v1.0)*, GMD 12.
- Patterson M. (2023), [*North-West Europe hottest days are warming twice as fast as mean summer days*](https://www.ox.ac.uk/news/2023-05-17-extremely-hot-days-are-warming-twice-fast-average-summer-days-north-west-europe), GRL 50, e2023GL102757.
- Shepherd T.G. et al. (2018), *Storylines: an alternative approach to representing uncertainty in physical aspects of climate change*, Climatic Change 151.
- Thompson V. et al. (2017), *High risk of unprecedented UK rainfall in the current climate*, Nature Communications 8 (UNSEEN method).
- Thrasher B. et al. (2022), [*NASA Global Daily Downscaled Projections, CMIP6*](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9163132/), Scientific Data 9; [NEX-GDDP-CMIP6 tech note](https://www.nccs.nasa.gov/sites/default/files/NEX-GDDP-CMIP6-Tech_Note_4.pdf).
- Vautard R. et al. (2023), [*Heat extremes in Western Europe increasing faster than simulated due to atmospheric circulation trends*](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10603106/), Nature Communications 14, 6803.
