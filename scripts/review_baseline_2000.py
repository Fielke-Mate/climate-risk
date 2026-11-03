"""Would a 2000-2025 ERA5 baseline help? Trend, the rank of 2003 and heatwave lengths (review, section 3.4).

Needs ERA5 2000-2025 for the listed sites (era5.fetch(site, 2000, 2025)). Each year is also shown
adjusted to the 2020 climate with a simple uniform shift from the site's linear summer-Tmax trend
(enough to show the size of the effect; not the method proposed for production).

Usage: python scripts/review_baseline_2000.py   -> outputs/review/baseline_2000.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from climate_risk import era5
from climate_risk.config import ROOT, load_sites
from climate_risk.heatwave import run_lengths as runs

pd.set_option("display.width", 250)

def yearly(daily, thr):
    out = {}
    for y, g in daily.groupby(daily.index.year):
        tx = g["tmax"].to_numpy()
        r = runs(tx > thr); hw = r[r >= 3]
        jja = g[g.index.month.isin([6, 7, 8])]["tmax"]
        out[y] = {"jja_tmax": jja.mean(), "days": int((tx > thr).sum()), "hw_events": len(hw),
                  "hw_days": int(hw.sum()), "longest": int(r.max()) if len(r) else 0}
    return pd.DataFrame(out).T

THR = {"SVQ": 40, "GET": 35, "MRS": 35, "TLS": 35, "NTE": 30, "DON": 30, "XFW": 30, "FIL": 28}
summary = []
for s in load_sites():
    if s.site_id not in THR: continue
    h, _ = era5.standardise(era5.read_raw(era5.raw_path(s, 2000, 2025)))
    t = h["temp_air"]; loc = (t.index - pd.Timedelta(hours=1)).tz_convert(s.timezone)
    daily = t.groupby(loc.normalize().tz_localize(None)).agg(["max", "min", "size"])
    daily = daily[daily["size"] >= 23].rename(columns={"max": "tmax", "min": "tmin"})
    yrs = np.arange(2000, 2026)
    jja = daily[daily.index.month.isin([6, 7, 8])]["tmax"].groupby(daily[daily.index.month.isin([6, 7, 8])].index.year).mean()
    slope = np.polyfit(jja.index, jja.values, 1)[0]          # C per year, summer Tmax
    # detrended to 2020: shift every day by slope*(2020 - year) (uniform, simple)
    adj = daily.copy(); adj["tmax"] = adj["tmax"] + slope * (2020 - adj.index.year)
    thr = THR[s.site_id]
    raw_y, adj_y = yearly(daily, thr), yearly(adj, thr)
    def rank(df, col):
        return int(df[col].rank(ascending=False, method="min").loc[2003])
    rec = {"site": s.site_id, "thr": thr, "trend_C_per_dec": round(slope * 10, 2),
           "jja_tmax_2000_09_vs_2015_25": round(jja.loc[2000:2009].mean() - jja.loc[2015:2025].mean(), 2),
           "rank2003_days_raw": rank(raw_y, "days"), "rank2003_days_adj": rank(adj_y, "days"),
           "longest_2003_raw": int(raw_y.loc[2003, "longest"]), "longest_2003_adj": int(adj_y.loc[2003, "longest"]),
           "longest_max_2015_25": int(raw_y.loc[2015:2025, "longest"].max()),
           "longest_max_yr": int(raw_y.loc[2015:2025, "longest"].idxmax()),
           "p90_longest_11y": raw_y.loc[2015:2025, "longest"].quantile(0.9),
           "p90_longest_26y_raw": raw_y["longest"].quantile(0.9), "p90_longest_26y_adj": adj_y["longest"].quantile(0.9),
           "median_days_11y": raw_y.loc[2015:2025, "days"].median(), "median_days_26y_raw": raw_y["days"].median(),
           "median_days_26y_adj": adj_y["days"].median(),
           "p90_days_11y": raw_y.loc[2015:2025, "days"].quantile(0.9), "p90_days_26y_adj": adj_y["days"].quantile(0.9)}
    summary.append(rec)
    top = adj_y.sort_values("longest", ascending=False).head(4)
    print(s.site_id, f"thr {thr}: longest runs (2020-adjusted):", ", ".join(f"{y} {int(r.longest)}d" for y, r in top.iterrows()))
out = pd.DataFrame(summary).set_index("site")
out.to_csv(ROOT / "outputs" / "review" / "baseline_2000.csv")
print(out.T.to_string())
