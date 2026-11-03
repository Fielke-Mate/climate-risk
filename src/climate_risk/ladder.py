"""Dry-bulb threshold ladder for the process-limit lens (D66).

For every complete year, count hours, days and spells above each rung of a ladder of outdoor dry-bulb
thresholds (config `process_lens.ladder_c`). The dashboard turns a process limit L with a hall heat gain
g into the rung L - g (the hall is outdoor air plus g, same as the worker lens), so any limit can be
shown without the hourly data. Counts use "above" (strictly greater than), like every other count.

Metrics (one row per year and metric, one column per rung):
  hours / op_hours        hours above the rung, all hours / operating hours (config operating_hours)
  early / late / night    hours above the rung in each shift (06-14, 14-22, 22-06)
  days / op_days          days with at least one hour above the rung (all hours / operating hours)
  longest / op_longest    longest run of consecutive such days
  dh / op_dh              degree-hours above the rung (C h)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .heatwave import run_lengths
from .weather import operating_hours_mask

SHIFTS = {"early": ("06:00", "14:00"), "late": ("14:00", "22:00"), "night": ("22:00", "06:00")}
METRICS = ("hours", "op_hours", "early", "late", "night", "days", "op_days", "longest", "op_longest", "dh", "op_dh")


def rungs(cfg: dict) -> np.ndarray:
    a, b, step = (float(x) for x in cfg["process_lens"]["ladder_c"])
    return np.round(np.arange(a, b + step / 2, step), 2)


def rung_names(cfg: dict) -> list[str]:
    return [f"{r:g}" for r in rungs(cfg)]


def _above(values: np.ndarray, r: np.ndarray) -> np.ndarray:
    s = np.sort(values)
    return len(s) - np.searchsorted(s, r, side="right")


def _degree_hours(values: np.ndarray, r: np.ndarray) -> np.ndarray:
    s = np.sort(values)
    k = np.searchsorted(s, r, side="right")
    tail = np.concatenate([np.cumsum(s[::-1])[::-1], [0.0]])   # tail[i] = sum of s[i:]
    return tail[k] - r * (len(s) - k)


def _longest(daily_max: np.ndarray, r: np.ndarray) -> np.ndarray:
    out = np.zeros(len(r), dtype=int)
    for i, x in enumerate(r):
        runs = run_lengths(daily_max > x)
        out[i] = runs.max() if len(runs) else 0
    return out


def ladder(hourly: pd.DataFrame, timezone: str, cfg: dict) -> pd.DataFrame:
    """Rows: (year, metric); columns: rung names. Complete local years only (as annual_summary)."""
    r = rungs(cfg)
    op_cfg = cfg["operating_hours"]
    t = hourly["temp_air"].to_numpy(float)
    starts = (hourly.index - pd.Timedelta(hours=1)).tz_convert(timezone)
    year = starts.year.to_numpy()
    date = starts.normalize().tz_localize(None).to_numpy()
    op = operating_hours_mask(hourly.index, timezone, op_cfg["start"], op_cfg["end"], op_cfg["days"])
    sh = {k: operating_hours_mask(hourly.index, timezone, a, b, op_cfg["days"]) for k, (a, b) in SHIFTS.items()}
    rows = []
    for y in np.unique(year):
        m = year == y
        if m.sum() < 8700:
            continue
        ty, dy, oy = t[m], date[m], op[m]
        # a gap-free calendar of local days (missing days would join runs; there are none in complete years)
        dall = pd.Series(ty).groupby(dy).max()
        dop = pd.Series(ty[oy]).groupby(dy[oy]).max().reindex(dall.index)   # NaN on a day with no operating hour
        vals = {
            "hours": _above(ty, r), "op_hours": _above(ty[oy], r),
            **{k: _above(ty[s[m]], r) for k, s in sh.items()},
            "days": _above(dall.to_numpy(), r), "op_days": _above(dop.dropna().to_numpy(), r),
            "longest": _longest(dall.to_numpy(), r), "op_longest": _longest(dop.fillna(-99).to_numpy(), r),
            "dh": np.round(_degree_hours(ty, r), 1), "op_dh": np.round(_degree_hours(ty[oy], r), 1),
        }
        rows += [{"year": int(y), "metric": k, **dict(zip(rung_names(cfg), v.tolist()))} for k, v in vals.items()]
    return pd.DataFrame(rows)


def ensemble(hist: pd.DataFrame, fut: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Typical (median year) and hot (90th percentile year) per rung, as ensemble_summary.csv does for the
    scalar metrics: historical from the observed years; future per model first, then the median, min and
    max across models. Columns: site_id, scenario, period, year_type, stat (median/min/max), metric, rungs."""
    cols = rung_names(cfg)
    out = []
    for (sid, metric), g in hist.groupby(["site_id", "metric"]):
        for yt, q in (("typical", 0.5), ("hot", 0.9)):
            v = g[cols].quantile(q)
            out.append({"site_id": sid, "scenario": "historical", "period": "historical", "year_type": yt,
                        "stat": "median", "metric": metric, **v.to_dict()})
    for yt, q in (("typical", 0.5), ("hot", 0.9)):
        pm = fut.groupby(["site_id", "scenario", "period", "model", "metric"])[cols].quantile(q).reset_index()
        for (sid, sc, per, metric), g in pm.groupby(["site_id", "scenario", "period", "metric"]):
            for stat, fn in (("median", "median"), ("min", "min"), ("max", "max")):
                out.append({"site_id": sid, "scenario": sc, "period": str(per), "year_type": yt, "stat": stat,
                            "metric": metric, **getattr(g[cols], fn)().to_dict()})
    return pd.DataFrame(out)
