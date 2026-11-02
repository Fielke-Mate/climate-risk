"""Per-year summary statistics and hot reference year selection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .weather import operating_hours_mask, wbgt_shaded_provisional


def add_derived(hourly: pd.DataFrame) -> pd.DataFrame:
    out = hourly.copy()
    out["wbgt_shade_prov"] = wbgt_shaded_provisional(out["temp_air"], out["relative_humidity"])
    return out


def annual_summary(hourly: pd.DataFrame, timezone: str, op_hours: dict, wbgt_threshold: float = 28.0,
                   hdh_base: float = 19.0, cdh_base: float = 24.0, wbgt_dh_base: float = 25.0) -> pd.DataFrame:
    """One row per calendar year (local time) with headline heat indicators."""
    df = add_derived(hourly)
    starts_local = (df.index - pd.Timedelta(hours=1)).tz_convert(timezone)
    df["year"] = starts_local.year
    df["date"] = starts_local.normalize()
    op = operating_hours_mask(df.index, timezone, op_hours["start"], op_hours["end"], op_hours["days"])
    df["op"] = op

    daily = df.groupby("date").agg(tmax=("temp_air", "max"), tmin=("temp_air", "min"), n=("temp_air", "size"))
    daily = daily[daily["n"] >= 23]  # DST days have 23/25 hours
    daily["year"] = daily.index.year
    dy = daily.groupby("year").agg(
        days_tmax_gt30=("tmax", lambda s: int((s > 30).sum())),
        days_tmax_gt35=("tmax", lambda s: int((s > 35).sum())),
        nights_tmin_gt20=("tmin", lambda s: int((s > 20).sum())),
    )
    g = df.groupby("year")
    summary = pd.DataFrame({
        "hours": g.size(),
        "temp_mean": g["temp_air"].mean().round(2),
        "temp_max": g["temp_air"].max().round(1),
        "temp_min": g["temp_air"].min().round(1),
        "hours_t_gt30": g["temp_air"].apply(lambda s: int((s > 30).sum())),
        "wbgt_prov_max": g["wbgt_shade_prov"].max().round(1),
        "op_hours_wbgt_prov_gt_threshold": df[df["op"]].groupby("year")["wbgt_shade_prov"].apply(
            lambda s: int((s > wbgt_threshold).sum())),
        "op_wbgt_prov_degree_hours_gt_base": df[df["op"]].groupby("year")["wbgt_shade_prov"].apply(
            lambda s: float(np.clip(s - wbgt_dh_base, 0, None).sum())).round(1),
        "hdh19": g["temp_air"].apply(lambda s: float(np.clip(hdh_base - s, 0, None).sum())).round(0),
        "cdh24": g["temp_air"].apply(lambda s: float(np.clip(s - cdh_base, 0, None).sum())).round(0),
    }).join(dy)
    summary["op_hours_wbgt_prov_gt_threshold"] = summary["op_hours_wbgt_prov_gt_threshold"].fillna(0).astype(int)
    summary = summary[summary["hours"] >= 8700]  # complete years only
    return summary


def select_hot_year(summary: pd.DataFrame) -> int:
    """Hottest year by WBGT degree-hours above the base (default 25 C) in working hours (D42).

    Ties (e.g. all zero at very cool sites) are broken by hours above 30 C, then annual max temperature.
    """
    ranked = summary.sort_values(["op_wbgt_prov_degree_hours_gt_base", "hours_t_gt30", "temp_max"], ascending=False)
    return int(ranked.index[0])
