"""Adjust the extended ERA5 record (2000-2025) to the climate of the reference year (D61).

Summers in 2000-2009 were 0.8-1.5 C cooler than in 2015-2025 at most pilot sites, so the early
years can't be used as they are: they would understate today's risk. Each year is shifted to the
2020 climate (the centre of the 2015-2025 window the future deltas are measured from) with the
climate models' own warming, not a trend fitted to the site's record, which is too noisy over
26 years (Sevilla's ERA5 cell even shows summer cooling).

Rates per site and calendar month, from the NEX-GDDP-CMIP6 models used for the future deltas:
  * tasmax, tasmin: change in the monthly mean between the early window (2000-2010, historical
    run) and the late window (2015-2025, mean of the scenario runs), divided by the 15 years
    between the window centres -> C per year
  * huss: log of the ratio of monthly means, per year
The median across models is taken (single runs are noisy over 15 years) and smoothed over
neighbouring months (1-2-1). The shift is the same at every percentile of the month (no change
in shape: the hot-day signal over 15 years is within the noise; see the climate science review).

Each day d is moved by (reference + 0.5 - decimal year of d) years at that month's rate, interpolated
between mid-month anchors, through the same hour-by-hour step as future morphing. Radiation and wind
are not changed. Years after the reference (2021-2025) are cooled slightly, so the whole record
represents one climate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import nex
from .morph import _daily_month_weights, shift_temperature_humidity

VARS = ("tasmax", "tasmin", "huss")


def _monthly_means(model: str, scenario: str, var: str, years: list[int], site_id: str) -> np.ndarray:
    s = nex.load_series(model, scenario, var, years)[site_id]
    months = s.index.str.slice(5, 7).astype(int)
    return np.array([s.to_numpy()[months == m].mean() for m in range(1, 13)])


def _window(model: str, scenarios: list[str], var: str, years: tuple[int, int], site_id: str) -> np.ndarray:
    """Monthly means over a window that may span the historical run (to 2014) and the scenario runs."""
    hist = [y for y in range(years[0], years[1] + 1) if y <= 2014]
    fut = [y for y in range(years[0], years[1] + 1) if y > 2014]
    parts, weights = [], []
    if hist:
        parts.append(_monthly_means(model, "historical", var, hist, site_id))
        weights.append(len(hist))
    if fut:  # the scenario runs are near-identical before 2025: average them as two samples
        parts.append(np.mean([_monthly_means(model, sc, var, fut, site_id) for sc in scenarios], axis=0))
        weights.append(len(fut))
    return np.average(np.array(parts), axis=0, weights=weights)


def smooth_months(v: np.ndarray) -> np.ndarray:
    """Cyclic 1-2-1 smoothing over calendar months."""
    return 0.25 * np.roll(v, 1) + 0.5 * v + 0.25 * np.roll(v, -1)


def adjustment_rates(site_id: str, models: list[str], scenarios: list[str],
                     early: tuple[int, int], late: tuple[int, int]) -> pd.DataFrame:
    """Per-model and ensemble rates (rows: model incl. 'median', month; columns: tasmax, tasmin, huss)."""
    years = (late[0] + late[1]) / 2 - (early[0] + early[1]) / 2
    rows = []
    for model in models:
        rate = {}
        for var in VARS:
            e = _window(model, scenarios, var, early, site_id)
            lt = _window(model, scenarios, var, late, site_id)
            rate[var] = (np.log(lt / e) if var == "huss" else lt - e) / years
        rows += [{"model": model, "month": m + 1, **{v: float(rate[v][m]) for v in VARS}} for m in range(12)]
    df = pd.DataFrame(rows)
    med = df.groupby("month")[list(VARS)].median()
    med = pd.DataFrame({v: smooth_months(med[v].to_numpy()) for v in VARS}, index=med.index).reset_index()
    return pd.concat([df, med.assign(model="median")], ignore_index=True)


def adjust_record(hourly: pd.DataFrame, rates: pd.DataFrame, reference_year: int) -> pd.DataFrame:
    """Copy of `hourly` (standard format, hour-ending UTC) with every day moved to the reference climate.
    rates: one row per month (1-12) with tasmax, tasmin (C/yr) and huss (log-ratio/yr)."""
    df = hourly.copy()
    starts = df.index - pd.Timedelta(hours=1)
    day_key = starts.normalize()
    daily = pd.DataFrame({"t": df["temp_air"].to_numpy()}, index=day_key).groupby(level=0)["t"].agg(["max", "min"])
    doy = np.minimum(daily.index.day_of_year.to_numpy(), 365).astype(float)
    ma, mb, w = _daily_month_weights(doy)
    r = rates.set_index("month").reindex(range(1, 13))

    def per_day(var: str) -> np.ndarray:
        v = r[var].to_numpy()
        return (1 - w) * v[ma] + w * v[mb]

    years = (reference_year + 0.5) - (daily.index.year.to_numpy() + (doy - 0.5) / 365.25)
    pos = daily.index.get_indexer(day_key)
    shift_temperature_humidity(df, daily, pos, (years * per_day("tasmax"))[pos], (years * per_day("tasmin"))[pos],
                               np.exp(years * per_day("huss"))[pos])
    return df
