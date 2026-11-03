"""Sensitivity of 2050 heat metrics to the tail-amplification assumption.

Used in docs/climate_science_review.md (section 2c). Needs the raw ERA5 record for each site
(scripts/fetch_era5.py) and outputs/phase2/deltas.parquet.

Usage: python scripts/review_tail_sensitivity.py SVQ,GET,TLS,XFW 4 outputs/review/tail_sensitivity_years.csv


Variants on the Tmax/Tmin quantile deltas (SSP5-8.5, 2050, each of 6 models):
  current  : as implemented (quantile deltas 5-95th pct, flat beyond 95th)
  mean     : no shape change - every quantile gets the median (q50) delta
  extrap   : above the 95th pct, extend with the 90->95 slope when it is positive (no cap)
  plus1    : stress test - hot-day Tmax delta raised by up to +1 C (ramp 0 at q50 -> +1 at q90+)
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd

from climate_risk import era5, morph
from climate_risk.annual import annual_summary
from climate_risk.config import ROOT, load_sites, settings

D = pd.read_parquet(str(ROOT / "outputs" / "phase2" / "deltas.parquet"))
METRICS = ["temp_max", "days_tmax_gt30", "days_tmax_gt35", "nights_tmin_gt20", "wbgt_shade_max",
           "op_wbgt_shade_degree_hours_gt_base", "op_hours_wbgt_shade_gt_ref", "op_days_wbgt_shade_gt_ref",
           "op_hours_wbgt_sun_gt_ref", "op_hours_wbgt_in4_gt_ref"]

def variant(d, v):
    d = d.copy()
    if v == "current":
        return d
    out = [d[~d.variable.isin(["tasmax", "tasmin"])]]
    for var in ("tasmax", "tasmin"):
        t = d[d.variable == var]
        rows = []
        for m, g in t.groupby("month"):
            g = g.sort_values("quantile").copy()
            q, val = g["quantile"].to_numpy(), g["value"].to_numpy()
            d50 = np.interp(0.5, q, val)
            if v == "mean":
                g["value"] = d50
            elif v == "plus1" and var == "tasmax":
                g["value"] = val + np.clip((q - 0.5) / 0.4, 0, 1) * 1.0
            elif v == "extrap":
                slope = max(0.0, (val[-1] - val[-2]) / (q[-1] - q[-2]))
                extra = g.iloc[[-1, -1]].copy()
                extra["quantile"] = [0.99, 0.999]
                extra["value"] = val[-1] + slope * (np.array([0.99, 0.999]) - q[-1])
                g = pd.concat([g, extra])
            rows.append(g)
        out.append(pd.concat(rows))
    return pd.concat(out, ignore_index=True)

def run(job):
    sid, model, v = job
    cfg = settings()
    site = next(s for s in load_sites() if s.site_id == sid)
    raw = era5.read_raw(era5.raw_path(site, 2015, 2025))
    hourly, _ = era5.standardise(raw)
    hourly = hourly.astype({c: "float64" for c in hourly.columns if hourly[c].dtype == "float32"})
    if model == "historical":
        fut = hourly
    else:
        d = D[(D.site_id == sid) & (D.model == model) & (D.scenario == "ssp585") & (D.period == "2050")]
        d = d.drop(columns=["site_id", "model", "scenario", "period"]).reset_index(drop=True)
        fut = morph.morph(hourly, variant(d, v), morph.baseline_daily_table(hourly))
    s = annual_summary(fut, site.lat, site.lon, site.timezone, cfg)[METRICS]
    return sid, model, v, s

if __name__ == "__main__":
    sites = sys.argv[1].split(",")
    models = sorted(D.model.unique())
    jobs = [(s, "historical", "historical") for s in sites]
    jobs += [(s, m, v) for s in sites for m in models for v in ("current", "mean", "extrap", "plus1")]
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=int(sys.argv[2])) as pool:
        for sid, model, v, s in pool.map(run, jobs):
            for y, r in s.to_dict("index").items():
                rows.append({"site_id": sid, "model": model, "variant": v, "year": y, **r})
            print(sid, model, v, f"{time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[3], index=False)
