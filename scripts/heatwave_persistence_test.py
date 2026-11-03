"""Perfect-model test: how much heatwave lengthening does morphing miss?

Morphing shifts each historical day by the projected change at its percentile, but keeps the
order of days. Inside each climate model we can test what that loses:

  base     the model's own daily Tmax/Tmin, 2015-2025
  morphed  `base` shifted with exactly the quantile deltas the pipeline uses (outputs/phase2/deltas.parquet),
           i.e. what our method would produce if the model's 2015-2025 were the observed record
  direct   the same model's actual daily series for 2031-2050 ("2040") or 2041-2060 ("2050")

`morphed` and `direct` have almost the same monthly distribution of daily values, so differences in
heatwave statistics come from changes in persistence (the order of days) that morphing cannot add.
Statistics are per year, averaged over each window. Needs NEX tasmax/tasmin
(scripts/fetch_nex.py --variables tasmax,tasmin).

Usage: python scripts/heatwave_persistence_test.py
Writes outputs/review/heatwave_persistence.csv and prints a summary.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from climate_risk import nex
from climate_risk.config import ROOT, load_sites, settings
from climate_risk.heatwave import calendar_mask, run_lengths
from climate_risk.morph import _daily_month_weights

OUT = ROOT / "outputs" / "review"
MIN_DAYS = settings()["heatwave"]["min_days"]


def load(model: str, scen: str, var: str, years: tuple[int, int]) -> pd.DataFrame:
    df = nex.load_series(model, scen, var, list(range(years[0], years[1] + 1))) - 273.15
    df.index = pd.to_datetime(df.index, errors="coerce")       # 360-day calendars would give NaT
    return df[df.index.notna()]


def morph_daily(base: pd.Series, d: pd.DataFrame, var: str) -> pd.Series:
    """Daily version of morph.morph's temperature step (same quantile placement and interpolation)."""
    tab = d[d.variable == var].pivot(index="month", columns="quantile", values="value").reindex(range(1, 13))
    qs, vals = tab.columns.to_numpy(float), tab.to_numpy()
    month = base.index.month.to_numpy()
    pct = np.empty(len(base))
    for m in range(1, 13):
        sel = month == m
        ref = np.sort(base.to_numpy()[sel])
        pct[sel] = np.searchsorted(ref, base.to_numpy()[sel], side="right") / len(ref)
    ma, mb, w = _daily_month_weights(np.minimum(base.index.day_of_year.to_numpy(), 365).astype(float))
    da = np.array([np.interp(p, qs, vals[i]) for p, i in zip(pct, ma)])
    db = np.array([np.interp(p, qs, vals[i]) for p, i in zip(pct, mb)])
    return base + (1 - w) * da + w * db


def stats(series: pd.Series, thr: float) -> dict:
    m = calendar_mask(series, thr)
    years = m.index.year
    n_years = len(np.unique(years))
    runs = np.concatenate([run_lengths(g.to_numpy()) for _, g in m.groupby(years)])
    longest = m.groupby(years).apply(lambda g: run_lengths(g.to_numpy()).max() if g.any() else 0)
    ev = runs[runs >= MIN_DAYS]
    return {"hot_days": m.sum() / n_years, "events": len(ev) / n_years, "event_days": ev.sum() / n_years,
            "mean_event_len": ev.mean() if len(ev) else np.nan, "longest": longest.mean(),
            "longest_p90": float(longest.quantile(0.9))}  # not the max: windows differ in length (11 vs 20 years)


def main() -> None:
    fc = settings()["future"]
    deltas = pd.read_parquet(ROOT / "outputs" / "phase2" / "deltas.parquet")
    sites = load_sites()
    rows = []
    for model in fc["models"]:
        for scen in fc["scenarios"]:
            base = {v: load(model, scen, v, tuple(fc["baseline_years"])) for v in ("tasmax", "tasmin")}
            for period, window in fc["periods"].items():
                fut = {v: load(model, scen, v, tuple(window)) for v in ("tasmax", "tasmin")}
                for s in sites:
                    d = deltas[(deltas.site_id == s.site_id) & (deltas.model == model) &
                               (deltas.scenario == scen) & (deltas.period == period)]
                    bx, fx = base["tasmax"][s.site_id], fut["tasmax"][s.site_id]
                    bn, fn = base["tasmin"][s.site_id], fut["tasmin"][s.site_id]
                    mx, mn = morph_daily(bx, d, "tasmax"), morph_daily(bn, d, "tasmin")
                    # thresholds: fixed 30 / 35 C, plus a site-relative one (the model's baseline
                    # summer 90th percentile of Tmax) so every site has events to compare
                    jja = bx[bx.index.month.isin([6, 7, 8])]
                    thrs = {"tx30": (30.0, "tasmax"), "tx35": (35.0, "tasmax"),
                            "tx_p90": (float(jja.quantile(0.9)), "tasmax"), "tn20": (20.0, "tasmin")}
                    for name, (thr, var) in thrs.items():
                        series = {"base": bx, "morphed": mx, "direct": fx} if var == "tasmax" else \
                                 {"base": bn, "morphed": mn, "direct": fn}
                        for kind, x in series.items():
                            rows.append({"site_id": s.site_id, "model": model, "scenario": scen, "period": period,
                                         "threshold": name, "threshold_c": round(thr, 1), "series": kind, **stats(x, thr)})
                print(model, scen, period, flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "heatwave_persistence.csv", index=False)


if __name__ == "__main__":
    main()
