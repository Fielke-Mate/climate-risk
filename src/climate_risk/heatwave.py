"""Heatwave length: runs of consecutive hot days (D60).

Morphing keeps the historical order of days, so these metrics on morphed years capture the
lengthening that comes from warmer days crossing a fixed threshold more often (most of the
projected change), but not changes in how persistent hot spells are. See
docs/climate_science_review.md, section 3.3.

Definitions (config `heatwave`):
  * hot-day heatwave: at least `min_days` consecutive days with daily max air temperature above
    each threshold in `tmax_thresholds_c` (e.g. 30 and 35 C). Per year: number of events, days in
    events and the longest run of hot days (any length).
  * warm nights: longest run of nights with daily min above `tropical_night_c`.
  * heat-safety spells (worker): runs of consecutive operating days with at least one working hour
    above the WBGT reference, for every exposure and worker profile (computed in annual.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def run_lengths(mask) -> np.ndarray:
    """Lengths of the runs of True in a 1-D boolean sequence."""
    m = np.concatenate([[0], np.asarray(mask, dtype=int), [0]])
    d = np.diff(m)
    return np.flatnonzero(d == -1) - np.flatnonzero(d == 1)


def spell_stats(mask, min_days: int) -> tuple[int, int, int]:
    """(events of at least min_days, days in those events, longest run of any length)."""
    r = run_lengths(mask)
    ev = r[r >= min_days]
    return int(len(ev)), int(ev.sum()), int(r.max()) if len(r) else 0


def calendar_mask(values: pd.Series, threshold: float) -> pd.Series:
    """values > threshold on a gap-free daily calendar; missing days count as not hot,
    so a gap in the record ends a run instead of joining two runs."""
    idx = pd.date_range(values.index.min(), values.index.max(), freq="D")
    return (values > threshold).reindex(idx, fill_value=False)


def heatwave_metric_names(cfg: dict) -> list[str]:
    hw = cfg["heatwave"]
    names = []
    for t in hw["tmax_thresholds_c"]:
        k = f"hw{int(t)}"
        names += [f"{k}_events", f"{k}_days", f"{k}_longest"]
    return names + [f"tn{int(hw['tropical_night_c'])}_longest"]


def daily_heatwave_metrics(tmax: pd.Series, tmin: pd.Series, cfg: dict) -> pd.DataFrame:
    """One row per calendar year. tmax / tmin: daily values indexed by local date."""
    hw = cfg["heatwave"]
    n = int(hw["min_days"])
    out = {}
    for t in hw["tmax_thresholds_c"]:
        k = f"hw{int(t)}"
        m = calendar_mask(tmax, float(t))
        stats = m.groupby(m.index.year).apply(lambda s: spell_stats(s.to_numpy(), n))
        out[f"{k}_events"] = stats.str[0]
        out[f"{k}_days"] = stats.str[1]
        out[f"{k}_longest"] = stats.str[2]
    tn = float(hw["tropical_night_c"])
    m = calendar_mask(tmin, tn)
    out[f"tn{int(tn)}_longest"] = m.groupby(m.index.year).apply(lambda s: spell_stats(s.to_numpy(), n)[2])
    df = pd.DataFrame(out)
    df.index.name = "year"
    return df
