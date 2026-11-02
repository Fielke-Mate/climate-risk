"""Morph historical hourly weather to a future climate (Belcher et al. 2005, quantile-based).

Temperature (D19, "projecting peaks"): each day's minimum and maximum are shifted
by the model's change at the matching quantile of that month's distribution
(the day's percentile within the ERA5 2015-2025 baseline), and the hours in
between are stretched linearly:

    T' = T + dTmin + (dTmax - dTmin) * (T - Tmin_day) / (Tmax_day - Tmin_day)

Humidity: vapour pressure is scaled by the specific-humidity ratio (capped at
saturation); dew point and RH are recomputed. Radiation (GHI, DNI, DHI), longwave
and wind speed are scaled by monthly ratios. Monthly signals are interpolated
day by day between mid-month anchors to avoid steps at month boundaries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .weather import STANDARD_COLUMNS, relative_humidity_from_dewpoint, saturation_vapour_pressure

MID_MONTH_DOY = np.array([15.5, 45, 74.5, 105, 135.5, 166, 196.5, 227.5, 258, 288.5, 319, 349.5])


def _daily_month_weights(doy: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For each day-of-year: (month_a index 0-11, month_b index, weight of b), cyclic."""
    anchors = np.concatenate([[MID_MONTH_DOY[-1] - 365], MID_MONTH_DOY, [MID_MONTH_DOY[0] + 365]])
    k = np.searchsorted(anchors, doy, side="right") - 1
    k = np.clip(k, 0, len(anchors) - 2)
    w = (doy - anchors[k]) / (anchors[k + 1] - anchors[k])
    a = (k - 1) % 12
    b = k % 12
    return a, b, w


def _dew_from_vapour_pressure(e_hpa):
    gamma = np.log(np.maximum(e_hpa, 1e-3) / 6.112)
    return 243.12 * gamma / (17.62 - gamma)


def morph(hourly: pd.DataFrame, deltas: pd.DataFrame, baseline_daily: pd.DataFrame) -> pd.DataFrame:
    """Return the morphed copy of `hourly` (standard format, hour-ending UTC index).

    deltas: output of deltas.site_deltas for one site/model/scenario/period.
    baseline_daily: ERA5 baseline daily table with columns month, tmax, tmin (all years),
                    used to place each day within its month's distribution.
    """
    df = hourly[[c for c in STANDARD_COLUMNS if c in hourly.columns]].copy()
    starts = df.index - pd.Timedelta(hours=1)
    day_key = starts.normalize()
    t = df["temp_air"].to_numpy()

    # ---- per-day quantities ------------------------------------------------
    daily = pd.DataFrame({"t": t}, index=day_key).groupby(level=0)["t"].agg(["max", "min"])
    d_month = daily.index.month.to_numpy()
    d_doy = np.minimum(daily.index.day_of_year.to_numpy(), 365).astype(float)
    ma, mb, w = _daily_month_weights(d_doy)

    def percentile(values: np.ndarray, col: str) -> np.ndarray:
        """Position of each day's value within the ERA5 baseline distribution for its month."""
        out = np.empty_like(values, dtype=float)
        for m in range(1, 13):
            ref = np.sort(baseline_daily.loc[baseline_daily["month"] == m, col].to_numpy())
            sel = d_month == m
            out[sel] = np.searchsorted(ref, values[sel], side="right") / len(ref)
        return np.clip(out, 0.0, 1.0)

    def quantile_delta(var: str, q: np.ndarray) -> np.ndarray:
        tab = deltas[deltas["variable"] == var].pivot(index="month", columns="quantile", values="value")
        tab = tab.reindex(range(1, 13))
        qs = tab.columns.to_numpy(dtype=float)
        vals = tab.to_numpy()  # 12 x nq
        da = np.array([np.interp(qi, qs, vals[i]) for qi, i in zip(q, ma)])
        db = np.array([np.interp(qi, qs, vals[i]) for qi, i in zip(q, mb)])
        return (1 - w) * da + w * db

    def monthly_daily(var: str) -> np.ndarray:
        v = deltas[deltas["variable"] == var].set_index("month")["value"].reindex(range(1, 13)).to_numpy()
        return (1 - w) * v[ma] + w * v[mb]

    d_tmax = quantile_delta("tasmax", percentile(daily["max"].to_numpy(), "tmax"))
    d_tmin = quantile_delta("tasmin", percentile(daily["min"].to_numpy(), "tmin"))

    # ---- expand to hours ---------------------------------------------------
    pos = daily.index.get_indexer(day_key)
    tmax_d = daily["max"].to_numpy()[pos]
    tmin_d = daily["min"].to_numpy()[pos]
    d_max = d_tmax[pos]
    d_min = d_tmin[pos]

    def monthly(var: str) -> np.ndarray:
        return monthly_daily(var)[pos]

    rng = tmax_d - tmin_d
    frac = np.where(rng > 0.1, (t - tmin_d) / np.where(rng > 0.1, rng, 1.0), 0.5)
    t_new = t + d_min + (d_max - d_min) * np.clip(frac, 0.0, 1.0)
    df["temp_air"] = t_new

    e = saturation_vapour_pressure(np.minimum(df["temp_dew"].to_numpy(), t))
    e_new = np.minimum(e * monthly("huss"), saturation_vapour_pressure(t_new))
    df["temp_dew"] = _dew_from_vapour_pressure(e_new)
    df["relative_humidity"] = relative_humidity_from_dewpoint(t_new, df["temp_dew"].to_numpy())

    r_sw = monthly("rsds")
    for col in ("ghi", "dni", "dhi"):
        df[col] = df[col].to_numpy() * r_sw
    df["dni"] = df["dni"].clip(upper=1200.0)
    df["lw_down"] = df["lw_down"].to_numpy() * monthly("rlds")
    df["wind_speed"] = df["wind_speed"].to_numpy() * monthly("sfcWind")
    return df


def baseline_daily_table(hourly: pd.DataFrame) -> pd.DataFrame:
    """Daily max/min of the ERA5 baseline (UTC days, hour-start labels) with month."""
    starts = hourly.index - pd.Timedelta(hours=1)
    d = pd.DataFrame({"t": hourly["temp_air"].to_numpy()}, index=starts.normalize())
    g = d.groupby(level=0)["t"].agg(["max", "min", "size"])
    g = g[g["size"] >= 20]
    return pd.DataFrame({"month": g.index.month, "tmax": g["max"].to_numpy(), "tmin": g["min"].to_numpy()})
