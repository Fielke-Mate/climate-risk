"""Typical Meteorological Year (TMY) following ISO 15927-4.

For each calendar month, the candidate years are compared using the
Finkelstein-Schafer (FS) statistic on daily means of air temperature, global
horizontal irradiance and relative humidity. Years are ranked per variable, the
ranks are summed, and of the three best years the one whose mean wind speed is
closest to the long-term monthly mean is chosen. Joins between months are
smoothed over +/- `blend_hours` by blending the two source years.

Input is the standard hourly format (UTC, hour-ending labels). February 29 is
dropped. Output is an 8760-hour year on the nominal year 2001, hour-ending labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .weather import relative_humidity_from_dewpoint

PRIMARY = ("temp_air", "ghi", "relative_humidity")
SECONDARY = "wind_speed"
BLEND_COLUMNS = ("temp_air", "temp_dew", "pressure", "wind_speed", "lw_down")
NOMINAL_YEAR = 2001


def _hour_start(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index - pd.Timedelta(hours=1)


def fs_statistic(year_values: np.ndarray, all_values: np.ndarray) -> float:
    """Finkelstein-Schafer statistic: sum over days of |F_year - Phi_long_term|."""
    x = np.sort(np.asarray(year_values, dtype=float))
    n = len(x)
    if n == 0:
        return np.inf
    f_year = np.arange(1, n + 1) / n
    all_sorted = np.sort(np.asarray(all_values, dtype=float))
    phi = np.searchsorted(all_sorted, x, side="right") / len(all_sorted)
    return float(np.abs(f_year - phi).sum())


def select_months(hourly: pd.DataFrame) -> pd.DataFrame:
    """Choose the source year for each calendar month. Returns one row per month."""
    starts = _hour_start(hourly.index)
    df = hourly.copy()
    df["_date"] = starts.normalize()
    df = df[~((starts.month == 2) & (starts.day == 29))]
    daily = df.groupby("_date")[list(PRIMARY) + [SECONDARY]].mean()
    hours_per_day = df.groupby("_date").size()
    daily = daily[hours_per_day == 24]
    daily["year"] = daily.index.year
    daily["month"] = daily.index.month

    rows = []
    for month in range(1, 13):
        dm = daily[daily["month"] == month]
        days_expected = dm.groupby("year").size().max()
        complete_years = [y for y, n in dm.groupby("year").size().items() if n == days_expected]
        dm = dm[dm["year"].isin(complete_years)]
        scores = pd.DataFrame(index=complete_years)
        for var in PRIMARY:
            scores[f"fs_{var}"] = [fs_statistic(dm.loc[dm["year"] == y, var], dm[var]) for y in complete_years]
            scores[f"rank_{var}"] = scores[f"fs_{var}"].rank(method="min")
        scores["rank_total"] = scores[[f"rank_{v}" for v in PRIMARY]].sum(axis=1)
        wind_mean = dm[SECONDARY].mean()
        scores["wind_dev"] = [abs(dm.loc[dm["year"] == y, SECONDARY].mean() - wind_mean) for y in complete_years]
        best3 = scores.sort_values(["rank_total", "wind_dev"]).head(3)
        chosen = int(best3["wind_dev"].idxmin())
        rows.append({
            "month": month, "year": chosen,
            "candidates": ",".join(str(int(y)) for y in best3.index),
            "rank_total": float(scores.loc[chosen, "rank_total"]),
            "n_years": len(complete_years),
        })
    return pd.DataFrame(rows)


def build(hourly: pd.DataFrame, selection: pd.DataFrame | None = None, blend_hours: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble the TMY. Returns (tmy_hourly, month_selection)."""
    if selection is None:
        selection = select_months(hourly)
    year_of = dict(zip(selection["month"], selection["year"]))

    starts = _hour_start(hourly.index)
    data = hourly.copy()
    data.index = starts  # work in hour-start time internally
    data = data[~((starts.month == 2) & (starts.day == 29))]

    nominal_starts = pd.date_range(f"{NOMINAL_YEAR}-01-01", periods=8760, freq="h", tz="UTC")
    numeric = [c for c in hourly.columns if pd.api.types.is_numeric_dtype(hourly[c])]

    def source_time(nominal: pd.Timestamp, year: int) -> pd.Timestamp:
        return nominal.replace(year=year)

    def lookup(times: list[pd.Timestamp]) -> pd.DataFrame:
        return data.reindex(pd.DatetimeIndex(times))[numeric]

    src_times = [source_time(t, year_of[t.month]) for t in nominal_starts]
    tmy = lookup(src_times)
    tmy.index = nominal_starts
    tmy["source_year"] = [year_of[t.month] for t in nominal_starts]
    tmy["blended"] = False

    # Smooth joins: blend the outgoing and incoming source years over +/- blend_hours.
    if blend_hours > 0:
        cols = [c for c in BLEND_COLUMNS if c in tmy.columns]
        for month in range(1, 13):
            next_month = month % 12 + 1
            year_a, year_b = year_of[month], year_of[next_month]
            if year_a == year_b:
                continue
            # The Dec -> Jan join sits at the start of the following nominal year, so that the
            # outgoing December continues into ITS next January (year_a + 1) and the incoming
            # January is preceded by ITS previous December (year_b - 1).
            boundary_year = NOMINAL_YEAR if next_month > 1 else NOMINAL_YEAR + 1
            boundary = pd.Timestamp(f"{boundary_year}-{next_month:02d}-01", tz="UTC")
            raw = [boundary + pd.Timedelta(hours=k) for k in range(-blend_hours, blend_hours)]
            a = lookup([source_time(w, year_a + (w.year - NOMINAL_YEAR)) for w in raw]).to_numpy()
            b = lookup([source_time(w, year_b + (w.year - boundary_year)) for w in raw]).to_numpy()
            # position in the nominal year (the Jan part of the Dec -> Jan join wraps to the start)
            window = [w if w.year == NOMINAL_YEAR else w.replace(year=NOMINAL_YEAR) for w in raw]
            weights = (np.arange(2 * blend_hours) + 0.5) / (2 * blend_hours)
            for j, w in enumerate(window):
                if np.isnan(a[j]).any() or np.isnan(b[j]).any():
                    continue  # edge of the record: keep the unblended value
                row = (1 - weights[j]) * a[j] + weights[j] * b[j]
                for col in cols:
                    tmy.at[w, col] = row[numeric.index(col)]
                tmy.at[w, "blended"] = True
        if {"temp_air", "temp_dew", "relative_humidity"} <= set(tmy.columns):
            tmy["temp_dew"] = np.minimum(tmy["temp_dew"], tmy["temp_air"])
            tmy["relative_humidity"] = relative_humidity_from_dewpoint(tmy["temp_air"], tmy["temp_dew"])

    tmy.index = tmy.index + pd.Timedelta(hours=1)  # back to hour-ending labels
    tmy.index.name = "time_utc"
    return tmy, selection
