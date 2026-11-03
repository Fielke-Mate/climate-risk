"""Per-year summary statistics and hot reference year selection.

Phase 3: heat-stress metrics use the full methods in heat.py (Liljegren WBGT, UTCI).
"Working hours" follow config operating_hours.

Naming: columns called "*wbgt_shade*" hold the INDOOR value with the hall at outdoor
temperature (no solar radiation, indoor air speed, D52); "*in2*" / "*in4*" are the same
with the hall 2 / 4 C warmer. "*sun*" is outdoor work in direct sun. "hours_utci_shade_gt28"
is outdoor shade (outdoor wind); "op_hours_utci_in*" are indoor UTCI.
"*_gt_ref" counts are above the headline WBGT reference (ISO 7243 Class 2, not acclimatised,
26 C, D58); "*_gt_ref_acc" are above the acclimatised reference (28 C), kept as a sensitivity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .heat import heat_frame, utci_indoor, wbgt_liljegren
from .weather import operating_hours_mask


def _count(s, thr):
    return int((s > thr).sum())


def annual_summary(hourly: pd.DataFrame, lat: float, lon: float, timezone: str, cfg: dict,
                   heat: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per calendar year (local time) with temperature and heat-stress indicators."""
    hc, op_cfg = cfg["heat"], cfg["operating_hours"]
    ref, ref_a, dh_base = hc["wbgt_reference_c"], hc["wbgt_reference_acclimatised_c"], cfg["hot_year"]["wbgt_degree_hour_base_c"]
    if heat is None:
        heat = heat_frame(hourly, lat, lon, indoor_offset=hc.get("indoor_offset_c", 0.0),
                          indoor_air_speed=hc.get("indoor_air_speed_ms", 0.3))
    df = pd.concat([hourly[["temp_air", "relative_humidity"]], heat], axis=1)
    offsets = [float(o) for o in hc.get("indoor_offsets_sensitivity", [])]
    for off in offsets:  # indoor sensitivity: hall warmer than outside by `off` C, no solar (shade)
        v_in = hc.get("indoor_air_speed_ms", 0.3)
        df[f"wbgt_in{int(off)}"] = wbgt_liljegren(hourly, lat, lon, sun=False, indoor_offset=off, air_speed=v_in)["wbgt"].to_numpy()
        df[f"utci_in{int(off)}"] = utci_indoor(hourly, off, v_in)
    starts_local = (df.index - pd.Timedelta(hours=1)).tz_convert(timezone)
    df["year"] = starts_local.year
    df["date"] = starts_local.normalize()
    df["op"] = operating_hours_mask(df.index, timezone, op_cfg["start"], op_cfg["end"], op_cfg["days"])

    daily = df.groupby("date").agg(tmax=("temp_air", "max"), tmin=("temp_air", "min"), n=("temp_air", "size"))
    daily = daily[daily["n"] >= 23]
    daily["year"] = daily.index.year
    dy = daily.groupby("year").agg(
        days_tmax_gt30=("tmax", lambda s: int((s > 30).sum())),
        days_tmax_gt35=("tmax", lambda s: int((s > 35).sum())),
        nights_tmin_gt20=("tmin", lambda s: int((s > 20).sum())),
    )
    op = df[df["op"]]
    in_cols = {f"wbgt_in{int(o)}": f"in{int(o)}" for o in offsets}
    opd = op.groupby("date")[["wbgt_shade", "wbgt_sun", *in_cols]].max()
    opd["year"] = opd.index.year
    od = pd.DataFrame({
        "op_days_wbgt_shade_gt_ref": opd.groupby("year")["wbgt_shade"].apply(lambda s: int((s > ref).sum())),
        "op_days_wbgt_sun_gt_ref": opd.groupby("year")["wbgt_sun"].apply(lambda s: int((s > ref).sum())),
        **{f"op_days_wbgt_{tag}_gt_ref": opd.groupby("year")[c].apply(lambda s: int((s > ref).sum())) for c, tag in in_cols.items()},
    })
    g, go = df.groupby("year"), op.groupby("year")
    summary = pd.DataFrame({
        "hours": g.size(),
        "temp_mean": g["temp_air"].mean().round(2),
        "temp_max": g["temp_air"].max().round(1),
        "temp_min": g["temp_air"].min().round(1),
        "hours_t_gt30": g["temp_air"].apply(lambda s: _count(s, 30)),
        "hdh19": g["temp_air"].apply(lambda s: float(np.clip(19.0 - s, 0, None).sum())).round(0),
        "cdh24": g["temp_air"].apply(lambda s: float(np.clip(s - 24.0, 0, None).sum())).round(0),
        "wbgt_shade_max": g["wbgt_shade"].max().round(1),
        "wbgt_sun_max": g["wbgt_sun"].max().round(1),
        "op_hours_wbgt_shade_gt_ref": go["wbgt_shade"].apply(lambda s: _count(s, ref)),
        "op_hours_wbgt_shade_gt_ref_acc": go["wbgt_shade"].apply(lambda s: _count(s, ref_a)),
        "op_hours_wbgt_sun_gt_ref": go["wbgt_sun"].apply(lambda s: _count(s, ref)),
        "op_wbgt_shade_degree_hours_gt_base": go["wbgt_shade"].apply(lambda s: float(np.clip(s - dh_base, 0, None).sum())).round(1),
        "hours_utci_shade_gt28": g["utci_shade"].apply(lambda s: _count(s, hc["utci_heat_stress_c"])),
        "hours_utci_sun_gt32": g["utci_sun"].apply(lambda s: _count(s, 32)),
        "hours_utci_sun_gt38": g["utci_sun"].apply(lambda s: _count(s, 38)),
    }).join(dy).join(od)
    summary["op_hours_utci_in0_gt28"] = go["utci_indoor"].apply(lambda s: _count(s, 28))
    summary["op_hours_utci_in0_gt32"] = go["utci_indoor"].apply(lambda s: _count(s, 32))
    summary["op_hours_utci_sun_gt32"] = go["utci_sun"].apply(lambda s: _count(s, 32))
    for o in offsets:
        tag = f"in{int(o)}"
        summary[f"op_hours_utci_{tag}_gt28"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 28))
        summary[f"op_hours_utci_{tag}_gt32"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 32))
    for c, tag in in_cols.items():
        summary[f"op_hours_wbgt_{tag}_gt_ref"] = go[c].apply(lambda s: _count(s, ref))
        summary[f"op_hours_wbgt_{tag}_gt_ref_acc"] = go[c].apply(lambda s: _count(s, ref_a))
    # working hours above the WBGT reference by shift, for every exposure (D57: story cards use these,
    # so the shift split agrees with the headline numbers). Night is outside the default operating hours.
    shifts = {"early": ("06:00", "14:00"), "late": ("14:00", "22:00"), "night": ("22:00", "06:00")}
    expo_cols = {"shade": "wbgt_shade", "sun": "wbgt_sun", **{tag: c for c, tag in in_cols.items()}}
    for sh, (a, b) in shifts.items():
        m = operating_hours_mask(df.index, timezone, a, b, op_cfg["days"])
        gs = df[m].groupby("year")
        for tag, col in expo_cols.items():
            summary[f"op_hours_wbgt_{tag}_gt_ref_{sh}"] = gs[col].apply(lambda s: _count(s, ref))
    for name, lim in hc.get("process_limits", {}).items():
        summary[f"proc_hours_{name}"] = g[lim["variable"]].apply(lambda s, a=lim["above"]: _count(s, a)) if lim["variable"] in df else 0
    summary = summary.fillna(0)
    summary = summary[summary["hours"] >= 8700]  # complete years only
    return summary


def select_hot_year(summary: pd.DataFrame) -> int:
    """Hottest year by WBGT degree-hours above the base (25 C) in working hours (D42).

    Ties (e.g. all zero at very cool sites) are broken by hours above 30 C, then annual max temperature.
    """
    ranked = summary.sort_values(["op_wbgt_shade_degree_hours_gt_base", "hours_t_gt30", "temp_max"], ascending=False)
    return int(ranked.index[0])
