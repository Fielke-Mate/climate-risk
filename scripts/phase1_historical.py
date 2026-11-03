"""Phase 1: historical weather files for every pilot site.

For each site:
  1. standardise the raw ERA5 2000-2025 hourly record (from scripts/fetch_era5.py); 2015-2025 is the
     headline baseline (as observed)
  2. adjust every year of 2000-2025 to the 2020 climate with the climate models' warming (D61)
  3. build the ISO 15927-4 typical meteorological year (TMY) from 2015-2025 (D63)
  4. summarise every year; pick the hot reference year (hottest of 2015-2025, as observed) and the extreme
     reference year (hottest of the adjusted 2000-2025 record) (D62)
  5. download the PVGIS TMY as an independent cross-check
Then write summary tables and figures.

Usage:  python scripts/phase1_historical.py [--skip-pvgis] [--reuse-adjustment] [--workers 4]
The adjustment needs NEX data: scripts/fetch_nex.py (historical run + baseline humidity).
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from climate_risk import adjust, era5, pvgis, tmy, weather  # noqa: E402
from climate_risk.annual import annual_summary, select_extreme_year, select_hot_year  # noqa: E402
from climate_risk.config import ROOT, WEATHER_DIR, hourly_path, load_sites, settings  # noqa: E402

OUT = ROOT / "outputs" / "phase1"
FIG = ROOT / "docs" / "phase1" / "figures"

# Reference palette (dataviz skill): categorical slots 1-3, blue sequential ramp, text inks
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def to_float32(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].astype("float32")
    return out


def monthly_profile(df: pd.DataFrame) -> pd.DataFrame:
    starts = df.index - pd.Timedelta(hours=1)
    g = df.groupby(starts.month)
    return pd.DataFrame({
        "temp_mean": g["temp_air"].mean(),
        "rh_mean": g["relative_humidity"].mean(),
        "ghi_kwh_m2_day": g["ghi"].mean() * 24 / 1000,
    })


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


ADJ_CSV = OUT / "baseline_adjustment.csv"


def adjustment_table(sites, cfg, reuse: bool) -> pd.DataFrame:
    """D61: per-site monthly warming rates from the climate models (or the saved table)."""
    if reuse:
        return pd.read_csv(ADJ_CSV)
    fc, b = cfg["future"], cfg["baseline"]
    adj = fc["baseline_adjustment"]
    frames = [adjust.adjustment_rates(s.site_id, list(fc["models"]), fc["scenarios"], tuple(adj["early_window"]),
                                      tuple(fc["baseline_years"])).assign(site_id=s.site_id) for s in sites]
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(ADJ_CSV, index=False)
    return out


def jja_tmax(hourly: pd.DataFrame, tz: str) -> pd.Series:
    """Mean summer (JJA) daily maximum temperature per year (local days)."""
    t = hourly["temp_air"]
    loc = (t.index - pd.Timedelta(hours=1)).tz_convert(tz)
    d = t.groupby(loc.normalize()).max()
    d = d[d.index.month.isin([6, 7, 8])]
    return d.groupby(d.index.year).mean()


def process_site(job):
    """Baseline records, adjustment, TMY, yearly summaries and reference years for one site (worker process)."""
    site_id, rates, skip_pvgis = job
    cfg = settings()
    b = cfg["baseline"]
    e0, y0, y1 = b["extended_start_year"], b["start_year"], b["end_year"]
    site = next(x for x in load_sites() if x.site_id == site_id)
    raw = era5.read_raw(era5.raw_path(site, e0, y1))
    extended, grid = era5.standardise(raw)
    extended = extended[(extended.index > pd.Timestamp(f"{e0}-01-01", tz="UTC"))
                        & (extended.index <= pd.Timestamp(f"{y1 + 1}-01-01", tz="UTC"))]
    hourly = extended[extended.index > pd.Timestamp(f"{y0}-01-01", tz="UTC")]   # the 2015-2025 baseline
    problems = weather.validate(hourly)
    to_float32(hourly).to_parquet(hourly_path(site_id))
    to_float32(extended).to_parquet(hourly_path(site_id, "extended"))
    # D61: the extended record with every year moved to the reference (2020) climate with the models' warming
    adjusted = adjust.adjust_record(extended, rates, b["reference_year"])
    problems += [f"adjusted: {p}" for p in weather.validate(adjusted)]
    to_float32(adjusted).to_parquet(hourly_path(site_id, "adjusted"))
    dist_km = 111.2 * np.hypot(grid["grid_lat"] - site.lat, (grid["grid_lon"] - site.lon) * np.cos(np.radians(site.lat)))
    grid_row = {"site_id": site_id, "name": site.name, "site_lat": site.lat, "site_lon": site.lon,
                **grid, "distance_km": round(float(dist_km), 1), "hours": len(hourly)}

    t, sel = tmy.build(hourly, blend_hours=cfg["tmy"]["blend_hours"])   # D63: TMY stays on 2015-2025
    problems += [f"TMY: {p}" for p in weather.validate(t)]
    to_float32(t).to_parquet(WEATHER_DIR / "tmy" / f"{site_id}_tmy.parquet")

    summ = annual_summary(hourly, site.lat, site.lon, site.timezone, cfg)        # headline baseline
    summ_ext = annual_summary(adjusted, site.lat, site.lon, site.timezone, cfg)  # 2000-2025 in today's climate
    hot = select_hot_year(summ)
    # D62: the extreme reference year = the hottest year of the adjusted 2000-2025 record
    ext, rule = select_extreme_year(summ_ext, cfg["hot_year"]["extreme_min_wbgt_degree_hours"])
    local_year = (hourly.index - pd.Timedelta(hours=1)).tz_convert(site.timezone).year
    to_float32(hourly[local_year == hot]).to_parquet(WEATHER_DIR / "hot_year" / f"{site_id}_{hot}.parquet")
    adj_year = (adjusted.index - pd.Timedelta(hours=1)).tz_convert(site.timezone).year
    to_float32(adjusted[adj_year == ext]).to_parquet(WEATHER_DIR / "extreme_year" / f"{site_id}_{ext}.parquet")
    keys = ["op_wbgt_shade_degree_hours_gt_base", "op_hours_wbgt_shade_gt_ref", "op_days_wbgt_shade_gt_ref",
            "hours_t_gt30", "temp_max", "days_tmax_gt35", "hw30_longest"]
    hot_row = {"site_id": site_id, "name": site.name, "hot_year": hot, "extreme_year": ext, "extreme_rule": rule,
               **{f"hot_{k}": v for k, v in summ.loc[hot, keys].items()},
               **{f"extreme_{k}": v for k, v in summ_ext.loc[ext, keys].items()},
               "median_op_hours_wbgt_shade_gt_ref": float(summ["op_hours_wbgt_shade_gt_ref"].median())}
    jr, ja = jja_tmax(extended, site.timezone), jja_tmax(adjusted, site.timezone)
    jja = rates[rates.month.isin([6, 7, 8])]
    check_row = {"site_id": site_id,
                 "model_jja_tmax_c_per_decade": round(10 * float(jja["tasmax"].mean()), 2),
                 "model_jja_huss_pct_per_decade": round(100 * (float(np.exp(10 * jja["huss"].mean())) - 1), 1),
                 "era5_jja_tmax_trend_c_per_decade_observed": round(10 * np.polyfit(jr.index, jr.to_numpy(), 1)[0], 2),
                 "era5_jja_tmax_trend_c_per_decade_adjusted": round(10 * np.polyfit(ja.index, ja.to_numpy(), 1)[0], 2),
                 "jja_tmax_2000_09_minus_2015_25_observed": round(float(jr.loc[e0:e0 + 9].mean() - jr.loc[y0:y1].mean()), 2),
                 "jja_tmax_2000_09_minus_2015_25_adjusted": round(float(ja.loc[e0:e0 + 9].mean() - ja.loc[y0:y1].mean()), 2)}

    profiles = {f"ERA5 {y0}-{y1} mean": monthly_profile(hourly), "TMY (this tool)": monthly_profile(t)}
    if not skip_pvgis:
        try:
            pv, _ = pvgis.fetch_tmy(site)
            to_float32(pv).to_parquet(WEATHER_DIR / "pvgis" / f"{site_id}_pvgis_tmy.parquet")
            profiles["PVGIS TMY 2005-2023"] = monthly_profile(pv)
        except Exception as exc:  # cross-check only; never block the run
            problems.append(f"PVGIS fetch failed: {exc}")
    monthly_rows = [{"site_id": site_id, "source": label, "month": month, **r.round(3).to_dict()}
                    for label, prof in profiles.items() for month, r in prof.iterrows()]
    print(f"{site_id}: grid {grid['grid_lat']},{grid['grid_lon']} ({dist_km:.1f} km), hot year {hot}, "
          f"extreme year {ext} ({rule}), issues: {problems or 'none'}", flush=True)
    annual = [{"site_id": site_id, "year": y, **r} for y, r in summ.to_dict("index").items()]
    annual_ext = [{"site_id": site_id, "year": y, **r} for y, r in summ_ext.to_dict("index").items()]
    return (annual, annual_ext, [{"site_id": site_id, **r} for r in sel.to_dict("records")], hot_row,
            monthly_rows, grid_row, problems, check_row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pvgis", action="store_true")
    ap.add_argument("--reuse-adjustment", action="store_true",
                    help="use outputs/phase1/baseline_adjustment.csv instead of recomputing it from NEX data")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cfg = settings()
    b = cfg["baseline"]
    thr = cfg["heat"]["wbgt_reference_c"]
    sites = sorted(load_sites(), key=lambda s: s.lat)  # south to north
    for d in ("hourly", "tmy", "hot_year", "extreme_year", "pvgis"):
        (WEATHER_DIR / d).mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    rates = adjustment_table(sites, cfg, args.reuse_adjustment)
    med = rates[rates.model == "median"]
    jobs = [(s.site_id, med[med.site_id == s.site_id][["month", "tasmax", "tasmin", "huss"]], args.skip_pvgis) for s in sites]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(process_site, jobs))

    annual = pd.DataFrame([r for res in results for r in res[0]])
    annual_ext = pd.DataFrame([r for res in results for r in res[1]])
    selection = pd.DataFrame([r for res in results for r in res[2]])
    hot = pd.DataFrame([res[3] for res in results])
    monthly = pd.DataFrame([r for res in results for r in res[4]])
    grids = pd.DataFrame([res[5] for res in results])
    problems = {res[5]["site_id"]: res[6] for res in results}
    annual.to_csv(OUT / "annual_summary.csv", index=False)
    annual_ext.to_csv(OUT / "annual_summary_extended.csv", index=False)
    selection.to_csv(OUT / "tmy_month_selection.csv", index=False)
    hot.to_csv(OUT / "hot_reference_years.csv", index=False)
    monthly.to_csv(OUT / "monthly_crosscheck.csv", index=False)
    grids.to_csv(OUT / "era5_grid_points.csv", index=False)
    pd.DataFrame([res[7] for res in results]).to_csv(OUT / "baseline_adjustment_check.csv", index=False)
    (OUT / "validation.json").write_text(json.dumps(problems, indent=2))

    names = {s.site_id: s.name for s in sites}
    order = [s.site_id for s in sites][::-1]  # north at top

    # Figure 1: monthly mean temperature, small multiples
    fig, axes = plt.subplots(3, 5, figsize=(15, 8.2), sharex=True, sharey=True)
    for ax, sid in zip(axes.flat, order):
        style_axes(ax)
        for i, src in enumerate(monthly["source"].unique()):
            d = monthly[(monthly.site_id == sid) & (monthly.source == src)]
            ax.plot(d["month"], d["temp_mean"], color=SERIES[i % len(SERIES)], linewidth=2, label=src,
                    linestyle="--" if src.startswith("PVGIS") else "-")
        ax.set_title(names[sid], fontsize=9, color=INK, loc="left")
        ax.set_xticks([1, 4, 7, 10], ["Jan", "Apr", "Jul", "Oct"])
    axes[0, 0].set_ylabel("°C", color=INK2, fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.975))
    fig.suptitle("Monthly mean air temperature: ERA5 record vs typical years", x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIG / "monthly_temperature_crosscheck.png", dpi=130)
    plt.close(fig)

    # Figures 2-3: site x year heatmaps with the hot reference year outlined
    cmap = LinearSegmentedColormap.from_list("blues", ["#ffffff"] + BLUES)
    for metric, title, fname in [
        ("op_wbgt_shade_degree_hours_gt_base", "WBGT degree-hours above 25 °C in working hours (06–22), shaded WBGT (Liljegren)", "heatmap_wbgt_degree_hours.png"),
        ("op_days_wbgt_shade_gt_ref", f"Days with a working hour above WBGT {thr:g} °C (shade, moderate work, not acclimatised)", "heatmap_wbgt_days.png"),
        ("days_tmax_gt30", "Days with maximum air temperature above 30 °C", "heatmap_days_tmax30.png"),
    ]:
        piv = annual_ext.pivot(index="site_id", columns="year", values=metric).loc[order]
        fig, ax = plt.subplots(figsize=(17, 6.6))
        vmax = max(float(piv.to_numpy().max()), 1.0)
        ax.imshow(piv.to_numpy(), cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        for i, sid in enumerate(piv.index):
            for j, yr in enumerate(piv.columns):
                v = piv.loc[sid, yr]
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                        color="#ffffff" if v > 0.55 * vmax else INK)
            hy = int(hot.loc[hot.site_id == sid, "hot_year"].iloc[0])
            j = list(piv.columns).index(hy)
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=1.8))
            ey = int(hot.loc[hot.site_id == sid, "extreme_year"].iloc[0])
            j = list(piv.columns).index(ey)
            ax.add_patch(Rectangle((j - 0.42, i - 0.42), 0.84, 0.84, fill=False, edgecolor="#d1006b", linewidth=1.6, linestyle="--"))
        ax.set_xticks(range(len(piv.columns)), piv.columns)
        ax.set_yticks(range(len(piv.index)), [names[s] for s in piv.index])
        ax.tick_params(colors=INK2, labelsize=8, length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.set_title(title + f"\n{b['extended_start_year']}-{b['end_year']}, every year adjusted to the {b['reference_year']} climate. "
                     "Black outline = hot reference year (hottest of 2015-2025 as observed); magenta dashed = extreme reference year",
                     loc="left", fontsize=11, color=INK)
        fig.tight_layout()
        fig.savefig(FIG / fname, dpi=130)
        plt.close(fig)

    print("done")


if __name__ == "__main__":
    main()
