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
from .heatwave import daily_heatwave_metrics, run_lengths
from .weather import operating_hours_mask


def _count(s, thr):
    return int((s > thr).sum())


from .config import settings as _settings, shifts as _shifts

SHIFTS = _shifts(_settings())   # config `shifts`


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
    plus heat-safety spells (D60: longest run of consecutive operating days with a working hour above
    the reference, and the number of runs of at least `heatwave.min_days`), for each exposure and
    worker profile."""
    return [n for suf in wbgt_profiles(hc) for x in wbgt_exposures(hc)
            for n in (f"op_days_wbgt_{x}_gt_ref{suf}", f"op_hours_wbgt_{x}_gt_ref{suf}", f"op_hours_wbgt_{x}_gt_ref{suf}_acc",
                      *[f"op_hours_wbgt_{x}_gt_ref{suf}_{sh}" for sh in SHIFTS],
                      f"op_longest_wbgt_{x}_gt_ref{suf}", f"op_spells_wbgt_{x}_gt_ref{suf}")]


def annual_summary(hourly: pd.DataFrame, lat: float, lon: float, timezone: str, cfg: dict,
                   heat: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per calendar year (local time) with temperature and heat-stress indicators."""
    hc, op_cfg = cfg["heat"], cfg["operating_hours"]
    dh_base = cfg["hot_year"]["wbgt_degree_hour_base_c"]
    if heat is None:
        heat = heat_frame(hourly, lat, lon, indoor_air_speed=hc.get("indoor_air_speed_ms", 0.3))   # hall = outside;
        # warmer halls are the indoor_offsets_sensitivity cases below (the dashboard's hall gain)
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
    # D60: heatwave length (runs of consecutive hot days / warm nights) on a gap-free calendar
    local_days = daily.index.tz_localize(None)
    hw = daily_heatwave_metrics(pd.Series(daily["tmax"].to_numpy(), index=local_days),
                                pd.Series(daily["tmin"].to_numpy(), index=local_days), cfg)
    dy = dy.join(hw)
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
    cols = {}   # collected and joined once (assigning ~200 columns one by one fragments the frame)
    cols["op_hours_utci_in0_gt28"] = go["utci_indoor"].apply(lambda s: _count(s, 28))
    cols["op_hours_utci_in0_gt32"] = go["utci_indoor"].apply(lambda s: _count(s, 32))
    cols["op_hours_utci_sun_gt32"] = go["utci_sun"].apply(lambda s: _count(s, 32))
    for o in offsets:
        tag = f"in{int(o)}"
        cols[f"op_hours_utci_{tag}_gt28"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 28))
        cols[f"op_hours_utci_{tag}_gt32"] = go[f"utci_{tag}"].apply(lambda s: _count(s, 32))
    # WBGT counts for every exposure and worker profile (D58, D59): days with a working hour above the
    # reference, working hours above it (and above the acclimatised reference), and hours per shift
    # (D57: the story cards use these, so the shift split agrees with the headline numbers; night is
    # outside the default operating hours).
    expo_cols = {"shade": "wbgt_shade", "sun": "wbgt_sun", **{tag: c for c, tag in in_cols.items()}}
    shift_groups = {sh: df[operating_hours_mask(df.index, timezone, a, b, op_cfg["days"])].groupby("year")
                    for sh, (a, b) in SHIFTS.items()}
    gd = opd.groupby("year")
    min_days = int(cfg["heatwave"]["min_days"])

    def spells(s, r):  # runs over consecutive operating days (a non-working day doesn't end a spell)
        runs = run_lengths((s > r).to_numpy())
        return (int(runs.max()) if len(runs) else 0), int((runs >= min_days).sum())
    for suf, (ref, ref_a) in wbgt_profiles(hc).items():
        for tag, col in expo_cols.items():
            cols[f"op_days_wbgt_{tag}_gt_ref{suf}"] = gd[col].apply(lambda s, r=ref: int((s > r).sum()))
            cols[f"op_hours_wbgt_{tag}_gt_ref{suf}"] = go[col].apply(lambda s, r=ref: _count(s, r))
            cols[f"op_hours_wbgt_{tag}_gt_ref{suf}_acc"] = go[col].apply(lambda s, r=ref_a: _count(s, r))
            sp = gd[col].apply(lambda s, r=ref: spells(s, r))
            cols[f"op_longest_wbgt_{tag}_gt_ref{suf}"] = sp.str[0]
            cols[f"op_spells_wbgt_{tag}_gt_ref{suf}"] = sp.str[1]
            for sh, gs in shift_groups.items():
                cols[f"op_hours_wbgt_{tag}_gt_ref{suf}_{sh}"] = gs[col].apply(lambda s, r=ref: _count(s, r))
    for name, lim in hc.get("process_limits", {}).items():
        cols[f"proc_hours_{name}"] = g[lim["variable"]].apply(lambda s, a=lim["above"]: _count(s, a)) if lim["variable"] in df else 0
    cols = {k: (v if isinstance(v, pd.Series) else pd.Series(v, index=summary.index)) for k, v in cols.items()}
    summary = pd.concat([summary, pd.DataFrame(cols).reindex(summary.index)], axis=1)
    summary = summary.fillna(0)
    summary = summary[summary["hours"] >= 8700]  # complete years only
    return summary


def select_hot_year(summary: pd.DataFrame) -> int:
    """Hottest year by WBGT degree-hours above the base (25 C) in working hours (D42).

    Ties (e.g. all zero at very cool sites) are broken by hours above 30 C, then annual max temperature.
    """
    ranked = summary.sort_values(["op_wbgt_shade_degree_hours_gt_base", "hours_t_gt30", "temp_max"], ascending=False)
    return int(ranked.index[0])


def select_reference_year(summary: pd.DataFrame, min_wbgt_degree_hours: float) -> tuple[int, str]:
    """A reference year and the rule used: ranked on humid heat (D42) unless humid heat is negligible at the
    site (its best year has fewer WBGT degree-hours than `min_wbgt_degree_hours`); then on dry heat. Used for
    the extreme year (D62, adjusted 2000-2025 record) and the hot year (D68, observed 2015-2025)."""
    if summary["op_wbgt_shade_degree_hours_gt_base"].max() >= min_wbgt_degree_hours:
        return select_hot_year(summary), "humid heat (WBGT degree-hours)"
    ranked = summary.sort_values(["hours_t_gt30", "temp_max"], ascending=False)
    return int(ranked.index[0]), "dry heat (hours above 30 °C)"


def select_extreme_year(summary: pd.DataFrame, min_wbgt_degree_hours: float) -> tuple[int, str]:
    """D62: the extreme reference year (alias kept for callers and tests)."""
    return select_reference_year(summary, min_wbgt_degree_hours)
