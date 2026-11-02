"""Climate change signals (deltas) from NEX-GDDP-CMIP6 daily data.

For each site, model, scenario and future period, by calendar month:
  * tasmax / tasmin: quantile deltas  Q_future(q) - Q_baseline(q)  [K]
    (so hot days get the hot-day warming: "projecting peaks", D19)
  * tas:            mean delta [K] (used for checks)
  * huss, rsds, rlds, sfcWind: ratio  mean_future / mean_baseline
The baseline window matches the ERA5 baseline (2015-2025, taken from the start
of each scenario run, D29); futures are 20-year windows centred on 2040 / 2050.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import nex

QUANTILE_VARS = ("tasmax", "tasmin")
MEAN_DELTA_VARS = ("tas",)
RATIO_VARS = ("huss", "rsds", "rlds", "sfcWind")
RATIO_LIMITS = {"huss": (0.7, 1.6), "rsds": (0.8, 1.25), "rlds": (0.9, 1.15), "sfcWind": (0.8, 1.2)}


def _by_month(series: pd.Series) -> dict[int, np.ndarray]:
    months = series.index.str.slice(5, 7).astype(int)
    return {m: series.to_numpy()[months == m] for m in range(1, 13)}


def site_deltas(site_id: str, model: str, scenario: str, baseline: tuple[int, int],
                period: tuple[int, int], quantiles: list[float]) -> pd.DataFrame:
    """Tidy table: variable, month, quantile (NaN for means/ratios), kind, value."""
    b_years = list(range(baseline[0], baseline[1] + 1))
    f_years = list(range(period[0], period[1] + 1))
    rows = []
    for var in QUANTILE_VARS + MEAN_DELTA_VARS + RATIO_VARS:
        base = _by_month(nex.load_series(model, scenario, var, b_years)[site_id])
        fut = _by_month(nex.load_series(model, scenario, var, f_years)[site_id])
        for m in range(1, 13):
            if var in QUANTILE_VARS:
                qb = np.quantile(base[m], quantiles)
                qf = np.quantile(fut[m], quantiles)
                rows += [{"variable": var, "month": m, "quantile": q, "kind": "delta", "value": float(f - b)}
                         for q, b, f in zip(quantiles, qb, qf)]
            elif var in MEAN_DELTA_VARS:
                rows.append({"variable": var, "month": m, "quantile": np.nan, "kind": "delta",
                             "value": float(fut[m].mean() - base[m].mean())})
            else:
                lo, hi = RATIO_LIMITS[var]
                ratio = float(fut[m].mean() / base[m].mean()) if base[m].mean() > 0 else 1.0
                rows.append({"variable": var, "month": m, "quantile": np.nan, "kind": "ratio",
                             "value": float(np.clip(ratio, lo, hi))})
    return pd.DataFrame(rows)
