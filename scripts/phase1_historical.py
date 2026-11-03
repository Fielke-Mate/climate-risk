"""Phase 1: historical weather files for every pilot site.

For each site:
  1. standardise the raw ERA5 2015-2025 hourly record (from scripts/fetch_era5.py)
  2. build the ISO 15927-4 typical meteorological year (TMY)
  3. summarise every year and pick the per-site hot reference year
  4. download the PVGIS TMY as an independent cross-check
Then write summary tables, figures and a short report.

Usage:  python scripts/phase1_historical.py [--skip-pvgis]
"""

from __future__ import annotations

import argparse
import json
import time

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from climate_risk import era5, pvgis, tmy, weather  # noqa: E402
from climate_risk.annual import annual_summary, select_hot_year  # noqa: E402
from climate_risk.config import ROOT, WEATHER_DIR, load_sites, settings  # noqa: E402

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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pvgis", action="store_true")
    args = ap.parse_args()

    cfg = settings()
    b, op = cfg["baseline"], cfg["operating_hours"]
    thr = cfg["heat"]["wbgt_reference_c"]
    sites = sorted(load_sites(), key=lambda s: s.lat)  # south to north
    for d in ("hourly", "tmy", "hot_year", "pvgis"):
        (WEATHER_DIR / d).mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    annual_rows, selection_rows, hot_rows, monthly_rows, grid_rows, problems = [], [], [], [], [], {}
    for site in sites:
        raw = era5.read_raw(era5.raw_path(site, b["start_year"], b["end_year"]))
        hourly, grid = era5.standardise(raw)
        hourly = hourly[(hourly.index > pd.Timestamp(f"{b['start_year']}-01-01", tz="UTC"))
                        & (hourly.index <= pd.Timestamp(f"{b['end_year'] + 1}-01-01", tz="UTC"))]
        problems[site.site_id] = weather.validate(hourly)
        to_float32(hourly).to_parquet(WEATHER_DIR / "hourly" / f"{site.site_id}_era5_{b['start_year']}_{b['end_year']}.parquet")
        dist_km = 111.2 * np.hypot(grid["grid_lat"] - site.lat, (grid["grid_lon"] - site.lon) * np.cos(np.radians(site.lat)))
        grid_rows.append({"site_id": site.site_id, "name": site.name, "site_lat": site.lat, "site_lon": site.lon,
                          **grid, "distance_km": round(float(dist_km), 1), "hours": len(hourly)})

        t, sel = tmy.build(hourly, blend_hours=cfg["tmy"]["blend_hours"])
        problems[site.site_id] += [f"TMY: {p}" for p in weather.validate(t)]
        to_float32(t).to_parquet(WEATHER_DIR / "tmy" / f"{site.site_id}_tmy.parquet")
        selection_rows += [{"site_id": site.site_id, **r} for r in sel.to_dict("records")]

        summ = annual_summary(hourly, site.lat, site.lon, site.timezone, cfg)
        hot = select_hot_year(summ)
        local_year = (hourly.index - pd.Timedelta(hours=1)).tz_convert(site.timezone).year
        to_float32(hourly[local_year == hot]).to_parquet(WEATHER_DIR / "hot_year" / f"{site.site_id}_{hot}.parquet")
        annual_rows += [{"site_id": site.site_id, "year": y, **r} for y, r in summ.to_dict("index").items()]
        hot_rows.append({"site_id": site.site_id, "name": site.name, "hot_year": hot,
                         **{f"hot_{k}": v for k, v in summ.loc[hot, ["op_wbgt_shade_degree_hours_gt_base", "op_hours_wbgt_shade_gt_ref", "op_days_wbgt_shade_gt_ref", "hours_t_gt30", "temp_max", "days_tmax_gt35"]].items()},
                         "median_op_hours_wbgt_shade_gt_ref": float(summ["op_hours_wbgt_shade_gt_ref"].median())})

        profiles = {"ERA5 2015-2025 mean": monthly_profile(hourly), "TMY (this tool)": monthly_profile(t)}
        if not args.skip_pvgis:
            try:
                pv, meta = pvgis.fetch_tmy(site)
                to_float32(pv).to_parquet(WEATHER_DIR / "pvgis" / f"{site.site_id}_pvgis_tmy.parquet")
                profiles["PVGIS TMY 2005-2023"] = monthly_profile(pv)
                time.sleep(1)
            except Exception as exc:  # cross-check only; never block the run
                problems[site.site_id].append(f"PVGIS fetch failed: {exc}")
        for label, prof in profiles.items():
            for month, r in prof.iterrows():
                monthly_rows.append({"site_id": site.site_id, "source": label, "month": month, **r.round(3).to_dict()})
        print(f"{site.site_id}: grid {grid['grid_lat']},{grid['grid_lon']} ({dist_km:.1f} km), hot year {hot}, "
              f"issues: {problems[site.site_id] or 'none'}", flush=True)

    annual = pd.DataFrame(annual_rows)
    selection = pd.DataFrame(selection_rows)
    hot = pd.DataFrame(hot_rows)
    monthly = pd.DataFrame(monthly_rows)
    grids = pd.DataFrame(grid_rows)
    annual.to_csv(OUT / "annual_summary.csv", index=False)
    selection.to_csv(OUT / "tmy_month_selection.csv", index=False)
    hot.to_csv(OUT / "hot_reference_years.csv", index=False)
    monthly.to_csv(OUT / "monthly_crosscheck.csv", index=False)
    grids.to_csv(OUT / "era5_grid_points.csv", index=False)
    (OUT / "validation.json").write_text(json.dumps(problems, indent=2))

    names = {s.site_id: s.name for s in sites}
    order = [s.site_id for s in sites][::-1]  # north at top

    # Figure 1: monthly mean temperature, small multiples
    fig, axes = plt.subplots(3, 5, figsize=(15, 8.2), sharex=True, sharey=True)
    for ax, sid in zip(axes.flat, order):
        style_axes(ax)
        for i, src in enumerate(monthly["source"].unique()):
            d = monthly[(monthly.site_id == sid) & (monthly.source == src)]
            ax.plot(d["month"], d["temp_mean"], color=SERIES[i], linewidth=2, label=src,
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
        piv = annual.pivot(index="site_id", columns="year", values=metric).loc[order]
        fig, ax = plt.subplots(figsize=(11, 6.6))
        vmax = max(float(piv.to_numpy().max()), 1.0)
        ax.imshow(piv.to_numpy(), cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        for i, sid in enumerate(piv.index):
            for j, yr in enumerate(piv.columns):
                v = piv.loc[sid, yr]
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="#ffffff" if v > 0.55 * vmax else INK)
            hy = int(hot.loc[hot.site_id == sid, "hot_year"].iloc[0])
            j = list(piv.columns).index(hy)
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=1.8))
        ax.set_xticks(range(len(piv.columns)), piv.columns)
        ax.set_yticks(range(len(piv.index)), [names[s] for s in piv.index])
        ax.tick_params(colors=INK2, labelsize=8, length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.set_title(title + "\nBlack outline = hot reference year for the site", loc="left", fontsize=11, color=INK)
        fig.tight_layout()
        fig.savefig(FIG / fname, dpi=130)
        plt.close(fig)

    print("done")


if __name__ == "__main__":
    main()
