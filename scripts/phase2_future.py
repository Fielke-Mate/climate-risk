"""Phase 2: future weather (2040, 2050) for every pilot site.

For each site x model x scenario x period:
  * climate change deltas from NEX-GDDP-CMIP6 (quantile deltas for Tmax/Tmin, ratios otherwise)
  * morph all 11 ERA5 baseline years and the TMY to the future climate
  * annual indicators per morphed year (same as Phase 1)
Then ensemble summaries (typical = median year, hot = 90th percentile year; median and
range across models), consistency checks, figures.

Usage: python scripts/phase2_future.py [--sites SVQ,TLS]
"""

from __future__ import annotations

import argparse
import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from climate_risk import deltas as dl  # noqa: E402
from climate_risk import morph, weather  # noqa: E402
from climate_risk.annual import annual_summary  # noqa: E402
from climate_risk.config import ROOT, WEATHER_DIR, load_sites, settings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

OUT = ROOT / "outputs" / "phase2"
FIG = ROOT / "docs" / "phase2" / "figures"
FUT = WEATHER_DIR / "future"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
METRICS = ["temp_mean", "temp_max", "hours_t_gt30", "days_tmax_gt30", "days_tmax_gt35", "nights_tmin_gt20",
           "op_hours_wbgt_shade_gt_ref", "op_hours_wbgt_shade_gt_ref_unacc", "op_hours_wbgt_sun_gt_ref",
           "op_days_wbgt_shade_gt_ref", "op_days_wbgt_sun_gt_ref", "op_wbgt_shade_degree_hours_gt_base",
           "op_days_wbgt_in2_gt_ref", "op_days_wbgt_in4_gt_ref", "op_hours_wbgt_in2_gt_ref", "op_hours_wbgt_in4_gt_ref",
           "op_hours_wbgt_in2_gt_ref_unacc", "op_hours_wbgt_in4_gt_ref_unacc",
           "op_hours_utci_in0_gt28", "op_hours_utci_in0_gt32", "op_hours_utci_in2_gt28", "op_hours_utci_in2_gt32",
           "op_hours_utci_in4_gt28", "op_hours_utci_in4_gt32", "op_hours_utci_sun_gt32",
           "wbgt_shade_max", "wbgt_sun_max", "hours_utci_shade_gt28", "hours_utci_sun_gt32", "hours_utci_sun_gt38",
           "proc_hours_paint_application_max_temp", "proc_hours_paint_application_max_rh", "proc_hours_composite_room_cooling",
           "cdh24", "hdh19"]


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def process_site(job):
    """Deltas, morphed years, annual indicators and morphed TMYs for one site (runs in a worker)."""
    site_id, fc = job
    cfg = settings()
    b = cfg["baseline"]
    site = next(s for s in load_sites() if s.site_id == site_id)
    hourly = pd.read_parquet(WEATHER_DIR / "hourly" / f"{site.site_id}_era5_{b['start_year']}_{b['end_year']}.parquet")
    hourly = hourly.astype({c: "float64" for c in hourly.columns if hourly[c].dtype == "float32"})
    tmy_hist = pd.read_parquet(WEATHER_DIR / "tmy" / f"{site.site_id}_tmy.parquet")
    hot_year = int(pd.read_csv(ROOT / "outputs" / "phase1" / "hot_reference_years.csv").set_index("site_id").loc[site.site_id, "hot_year"])
    hot_hist = pd.read_parquet(WEATHER_DIR / "hot_year" / f"{site.site_id}_{hot_year}.parquet")
    hot_hist = hot_hist.astype({c: "float64" for c in hot_hist.columns if hot_hist[c].dtype == "float32"})
    base_daily = morph.baseline_daily_table(hourly)
    starts = hourly.index - pd.Timedelta(hours=1)
    hist_monthly = hourly["temp_air"].groupby(starts.month).mean()
    delta_frames, annual_rows, checks = [], [], []
    for model in fc["models"]:
        for scen in fc["scenarios"]:
            for period, window in fc["periods"].items():
                d = dl.site_deltas(site.site_id, model, scen, tuple(fc["baseline_years"]), tuple(window),
                                   fc["temperature_quantiles"])
                delta_frames.append(d.assign(site_id=site.site_id, model=model, scenario=scen, period=period))
                fut = morph.morph(hourly, d, base_daily)
                probs = weather.validate(fut)
                fut_monthly = fut["temp_air"].groupby(starts.month).mean()
                tas = d[d.variable == "tas"].set_index("month")["value"]
                diff = (fut_monthly - hist_monthly) - tas
                checks.append({"site_id": site.site_id, "model": model, "scenario": scen, "period": period,
                               "annual_warming_morphed": round(float((fut_monthly - hist_monthly).mean()), 3),
                               "annual_warming_model_tas": round(float(tas.mean()), 3),
                               "max_abs_monthly_diff": round(float(diff.abs().max()), 3),
                               "rh_max": round(float(fut["relative_humidity"].max()), 2),
                               "issues": "; ".join(probs)})
                summ = annual_summary(fut, site.lat, site.lon, site.timezone, cfg)
                annual_rows += [{"site_id": site.site_id, "model": model, "scenario": scen, "period": period,
                                 "source_year": y, **r} for y, r in summ.to_dict("index").items()]
                tmy_f = morph.morph(tmy_hist, d, base_daily)
                tmy_f["source_year"] = tmy_hist["source_year"].to_numpy()
                tmy_f.astype({c: "float32" for c in tmy_f.columns if tmy_f[c].dtype == "float64"}).to_parquet(
                    FUT / "tmy" / f"{site.site_id}_{model}_{scen}_{period}.parquet")
                # the site's hot reference year (actual weather) adjusted to the same future climate
                hot_f = morph.morph(hot_hist, d, base_daily)
                hot_f.astype({c: "float32" for c in hot_f.columns if hot_f[c].dtype == "float64"}).to_parquet(
                    FUT / "hot_year" / f"{site.site_id}_{model}_{scen}_{period}.parquet")
    print(f"{site.site_id}: done", flush=True)
    return delta_frames, annual_rows, checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default="")
    ap.add_argument("--models", default="", help="comma list; default all configured models")
    ap.add_argument("--out", default="", help="override output folder (for trial runs)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cfg = settings()
    fc, op, b = cfg["future"], cfg["operating_hours"], cfg["baseline"]
    sites = sorted(load_sites(), key=lambda s: s.lat)
    if args.sites:
        sites = [s for s in sites if s.site_id in args.sites.split(",")]
    if args.models:
        fc = {**fc, "models": {m: fc["models"][m] for m in args.models.split(",")}}
    global OUT, FIG
    if args.out:
        OUT = FIG = ROOT / args.out
    for d in (OUT, FIG, FUT / "tmy", FUT / "hot_year"):
        d.mkdir(parents=True, exist_ok=True)

    jobs = [(site.site_id, fc) for site in sites]
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        results = list(pool.map(process_site, jobs))
    delta_frames = [f for r in results for f in r[0]]
    annual_rows = [x for r in results for x in r[1]]
    checks = [x for r in results for x in r[2]]

    deltas_all = pd.concat(delta_frames, ignore_index=True)
    deltas_all.to_parquet(OUT / "deltas.parquet", index=False)
    fut_annual = pd.DataFrame(annual_rows)
    fut_annual.to_csv(OUT / "annual_summary_future.csv", index=False)
    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(OUT / "morph_checks.csv", index=False)

    # ---- ensemble summary: typical (median year) and hot (90th pct year) -----------------
    hist = pd.read_csv(ROOT / "outputs" / "phase1" / "annual_summary.csv")
    hist = hist[hist.site_id.isin([s.site_id for s in sites])]
    rows = []
    for sid, g in hist.groupby("site_id"):
        for stat, fn in (("typical", lambda s: s.median()), ("hot", lambda s: s.quantile(0.9))):
            rows += [{"site_id": sid, "scenario": "historical", "period": "historical", "year_type": stat,
                      "metric": m, "median": float(fn(g[m])), "min": np.nan, "max": np.nan} for m in METRICS]
    per_model = fut_annual.groupby(["site_id", "scenario", "period", "model"])[METRICS]
    for stat, q in (("typical", 0.5), ("hot", 0.9)):
        pm = per_model.quantile(q).reset_index()
        for (sid, scen, per), g in pm.groupby(["site_id", "scenario", "period"]):
            rows += [{"site_id": sid, "scenario": scen, "period": per, "year_type": stat, "metric": m,
                      "median": float(g[m].median()), "min": float(g[m].min()), "max": float(g[m].max())}
                     for m in METRICS]
    ens = pd.DataFrame(rows)
    ens.to_csv(OUT / "ensemble_summary.csv", index=False)

    # ---- figures ------------------------------------------------------------------------
    names = {s.site_id: s.name for s in sites}
    order = [s.site_id for s in sites]  # south first (bottom of chart = north after invert)
    warm = checks_df.groupby(["site_id", "scenario", "period"])["annual_warming_model_tas"].agg(["median", "min", "max"]).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2), sharey=True, sharex=True)
    for ax, per in zip(axes, fc["periods"]):
        style(ax)
        for k, scen in enumerate(fc["scenarios"]):
            w = warm[(warm.period == per) & (warm.scenario == scen)].set_index("site_id").loc[order]
            y = np.arange(len(order)) + (k - 0.5) * 0.28
            ax.hlines(y, w["min"], w["max"], color=SERIES[k], linewidth=2)
            ax.plot(w["median"], y, "o", color=SERIES[k], markersize=7, label={"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}[scen],
                    markeredgecolor="white", markeredgewidth=1.5)
        ax.set_title(f"{per} (vs 2015–2025)", loc="left", fontsize=10, color=INK)
        ax.set_xlabel("Change in annual mean temperature (°C)", fontsize=8, color=INK2)
    axes[0].set_yticks(range(len(order)), [names[s] for s in order])
    axes[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.suptitle(f"Projected warming by site: dot = median of {len(fc['models'])} models, line = model range", x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "warming_by_site.png", dpi=130)
    plt.close(fig)

    for metric, label, fname in [("days_tmax_gt30", "Days with max temperature above 30 °C", "days_tmax30_projection.png"),
                                 ("op_wbgt_shade_degree_hours_gt_base", "WBGT degree-hours above 25 °C in working hours (shade, Liljegren)", "wbgt_degree_hours_projection.png"),
                                 ("op_days_wbgt_shade_gt_ref", "Days with a working hour above WBGT 28 °C (shade, moderate work)", "wbgt_days_projection.png")]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 6.2), sharey=True, sharex=True)
        for ax, scen in zip(axes, fc["scenarios"]):
            style(ax)
            e = ens[(ens.metric == metric) & (ens.year_type == "typical")]
            cols = [("historical", "historical", "Historical (2015–2025)", "#9a9890"),
                    (scen, "2040", "2040", SERIES[0]), (scen, "2050", "2050", SERIES[1])]
            for k, (sc, per, lab, colr) in enumerate(cols):
                v = e[(e.scenario == sc) & (e.period == per)].set_index("site_id").loc[order]
                y = np.arange(len(order)) + (k - 1) * 0.25
                if sc != "historical":
                    ax.hlines(y, v["min"], v["max"], color=colr, linewidth=2)
                ax.plot(v["median"], y, "o", color=colr, markersize=6, label=lab, markeredgecolor="white", markeredgewidth=1.2)
            ax.set_title({"ssp245": "SSP2-4.5 (middle)", "ssp585": "SSP5-8.5 (high)"}[scen], loc="left", fontsize=10, color=INK)
        axes[0].set_yticks(range(len(order)), [names[s] for s in order])
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, frameon=False, fontsize=9, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.95))
        fig.suptitle(f"{label}: typical year (median), line = range across {len(fc['models'])} models", x=0.01, ha="left", fontsize=12, color=INK)
        fig.tight_layout(rect=(0, 0, 1, 0.91))
        fig.savefig(FIG / fname, dpi=130)
        plt.close(fig)

    # quantile delta profile, July, two contrasting sites
    pick = [s for s in ("SVQ", "XFW") if s in names]
    if pick:
        fig, axes = plt.subplots(1, len(pick), figsize=(6 * len(pick), 4.2), sharey=True, squeeze=False)
        for ax, sid in zip(axes[0], pick):
            style(ax)
            ax.grid(axis="y", color=GRID, linewidth=0.8)
            q = deltas_all[(deltas_all.site_id == sid) & (deltas_all.variable == "tasmax") & (deltas_all.month == 7)
                           & (deltas_all.scenario == "ssp585") & (deltas_all.period == "2050")]
            prof = q.groupby("quantile")["value"].agg(["median", "min", "max"])
            ax.fill_between(prof.index * 100, prof["min"], prof["max"], color=SERIES[1], alpha=0.18, linewidth=0, label="Model range")
            ax.plot(prof.index * 100, prof["median"], color=SERIES[1], linewidth=2, label=f"Median of {len(fc['models'])} models")
            ax.set_title(f"{names[sid]}: July daily max, SSP5-8.5, 2050", loc="left", fontsize=10, color=INK)
            ax.set_xlabel("Percentile of daily maximum temperature", fontsize=8, color=INK2)
        axes[0][0].set_ylabel("Warming (°C)", fontsize=8, color=INK2)
        axes[0][0].legend(frameon=False, fontsize=8, loc="upper left")
        fig.tight_layout()
        fig.savefig(FIG / "quantile_deltas_july.png", dpi=130)
        plt.close(fig)

    print(json.dumps({"checks_max_abs_monthly_diff": float(checks_df["max_abs_monthly_diff"].max()),
                      "issues": int((checks_df["issues"] != "").sum())}))


if __name__ == "__main__":
    main()
