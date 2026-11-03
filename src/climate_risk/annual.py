"""Per-year summary statistics and hot reference year selection.

Phase 3: heat-stress metrics use the full methods in heat.py (Liljegren WBGT, UTCI).
"Working hours" follow config operating_hours.

Naming: columns called "*wbgt_shade*" hold the INDOOR value with the hall at outdoor
temperature (no solar radiation, indoor air speed, D52); "*in2*" / "*in4*" are the same
with the hall 2 / 4 C warmer. "*sun*" is outdoor work in direct sun. "hours_utci_shade_gt28"
is outdoor shade (outdoor wind); "op_hours_utci_in*" are indoor UTCI.
"*_gt_ref" counts are above the headline WBGT reference (ISO 7243 Class 2, not acclimatised,
26 C, D58); "*_gt_ref_acc" are above the acclimatised reference (28 C), kept as a sensitivity.
D59: the same counts are made for every worker profile (work class x clothing); the default
profile keeps the plain names, the others add "_<profile>" after "gt_ref".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .heat import heat_frame, utci_indoor, wbgt_liljegren
from .weather import operating_hours_mask


def _count(s, thr):
    return int((s > thr).sum())


SHIFTS = {"early": ("06:00", "14:00"), "late": ("14:00", "22:00"), "night": ("22:00", "06:00")}


def wbgt_profiles(hc: dict) -> dict[str, tuple[float, float]]:
    """Column suffix -> (reference, acclimatised reference) in C, both lowered by the clothing
    adjustment. The default profile has suffix "" (plain "*_gt_ref" names)."""
    default = hc.get("default_worker_profile")
    out = {"": (float(hc["wbgt_reference_c"]), float(hc["wbgt_reference_acclimatised_c"]))}
    for name, p in hc.get("worker_profiles", {}).items():
        cav = float(p.get("clothing_adjustment_c", 0.0))
        refs = (float(p["reference_c"]) - cav, float(p["reference_acclimatised_c"]) - cav)
        if name == default:
            if refs != out[""]:
                raise ValueError(f"default worker profile '{name}' {refs} does not match wbgt_reference_c {out['']}")
        else:
            out[f"_{name}"] = refs
    return out


def wbgt_exposures(hc: dict) -> list[str]:
    return ["shade", "sun", *[f"in{int(float(o))}" for o in hc.get("indoor_offsets_sensitivity", [])]]


def wbgt_metric_names(hc: dict) -> list[str]:
    """Every WBGT count annual_summary makes: days, hours, acclimatised hours and hours per shift,
    for each exposure and worker profile."""
    return [n for suf in wbgt_profiles(hc) for x in wbgt_exposures(hc)
            for n in (f"op_days_wbgt_{x}_gt_ref{suf}", f"op_hours_wbgt_{x}_gt_ref{suf}", f"op_hours_wbgt_{x}_gt_ref{suf}_acc",
                      *[f"op_hours_wbgt_{x}_gt_ref{suf}_{sh}" for sh in SHIFTS])]


def annual_summary(hourly: pd.DataFrame, lat: float, lon: float, timezone: str, cfg: dict,
                   heat: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per calendar year (local time) with temperature and heat-stress indicators."""
    hc, op_cfg = cfg["heat"], cfg["operating_hours"]
    dh_base = cfg["hot_year"]["wbgt_degree_hour_base_c"]
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
        "op_wbgt_shade_degree_hours_gt_base": go["wbgt_shade"].apply(lambda s: float(np.clip(s - dh_base, 0, None).sum())).round(1),
        "hours_utci_shade_gt28": g["utci_shade"].apply(lambda s: _count(s, hc["utci_heat_stress_c"])),
        "hours_utci_sun_gt32": g["utci_sun"].apply(lambda s: _count(s, 32)),
        "hours_utci_sun_gt38": g["utci_sun"].apply(lambda s: _count(s, 38)),
    }).join(dy)
    summary["op_hours_utci_in0_gt28"] = go["utci_indoor"].apply(lambda s: _count(s, 28))
    summary["op_hours_utci_in0_gt32"] = go["utci_indoor"].apply(lambda s: _count(s, 32))
    summary["op_hours_utci_sun_gt32"] = go["utci_sun"].apply(lambda s: _count(s, 32))
    for o in offsets:
        tag = f"in{int(o)}"
        summary[f"op_hours_utci_{tag}_gt28"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 28))
        summary[f"op_hours_utci_{tag}_gt32"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 32))
    # WBGT counts for every exposure and worker profile (D58, D59): days with a working hour above the
    # reference, working hours above it (and above the acclimatised reference), and hours per shift
    # (D57: the story cards use these, so the shift split agrees with the headline numbers; night is
    # outside the default operating hours).
    expo_cols = {"shade": "wbgt_shade", "sun": "wbgt_sun", **{tag: c for c, tag in in_cols.items()}}
    shift_groups = {sh: df[operating_hours_mask(df.index, timezone, a, b, op_cfg["days"])].groupby("year")
                    for sh, (a, b) in SHIFTS.items()}
    gd = opd.groupby("year")
    for suf, (ref, ref_a) in wbgt_profiles(hc).items():
        for tag, col in expo_cols.items():
            summary[f"op_days_wbgt_{tag}_gt_ref{suf}"] = gd[col].apply(lambda s, r=ref: int((s > r).sum()))
            summary[f"op_hours_wbgt_{tag}_gt_ref{suf}"] = go[col].apply(lambda s, r=ref: _count(s, r))
            summary[f"op_hours_wbgt_{tag}_gt_ref{suf}_acc"] = go[col].apply(lambda s, r=ref_a: _count(s, r))
            for sh, gs in shift_groups.items():
                summary[f"op_hours_wbgt_{tag}_gt_ref{suf}_{sh}"] = gs[col].apply(lambda s, r=ref: _count(s, r))
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
