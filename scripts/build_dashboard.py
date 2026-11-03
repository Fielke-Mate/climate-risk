"""Build the dashboard prototype: one self-contained HTML page with its data embedded.

Outputs
  dashboard/data.json       the data the page uses (inspectable)
  dashboard/page.html       page content for publishing as a claude.ai page
  dashboard/index.html      the same page as a full HTML document (GitHub Pages)

Usage: python scripts/build_dashboard.py
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import math

import numpy as np
import pandas as pd
import requests
from pythermalcomfort.models import utci as utci_model

from climate_risk.config import ROOT, WEATHER_DIR, load_sites, settings
from concurrent.futures import ProcessPoolExecutor

from climate_risk.heat import heat_frame, utci_indoor, wbgt_liljegren
from climate_risk.weather import operating_hours_mask

DASH = ROOT / "dashboard"
BASEMAP = DASH / "basemap.json"
WORLD_ATLAS = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"

# Map frame (degrees) and projection: Lambert azimuthal equal-area centred on the portfolio
LON0, LAT0 = 3.0, 46.0
BBOX = (-24.0, 33.0, 30.0, 59.0)  # lon_min, lat_min, lon_max, lat_max (wide, so the map can be landscape)
MAP_W = 1000

TEMP_BANDS = [(-99, 16, "< 16"), (16, 21, "16–21"), (21, 24, "21–24 optimal"), (24, 25, "24–25"),
              (25, 30, "25–30"), (30, 35, "30–35"), (35, 99, "> 35")]
UTCI_BANDS = [(-99, -13), (-13, 0), (0, 9), (9, 26), (26, 28), (28, 32), (32, 38), (38, 46), (46, 99)]
SHIFTS = {"early": ("06:00", "14:00"), "late": ("14:00", "22:00"), "night": ("22:00", "06:00")}
KPI_METRICS = ["days_tmax_gt30", "days_tmax_gt35", "hours_t_gt30", "nights_tmin_gt20", "temp_max", "temp_mean",
               "op_days_wbgt_sun_gt_ref", "op_days_wbgt_shade_gt_ref", "op_hours_wbgt_sun_gt_ref", "op_hours_wbgt_shade_gt_ref",
               "op_hours_wbgt_shade_gt_ref_acc", "op_wbgt_shade_degree_hours_gt_base", "wbgt_sun_max", "wbgt_shade_max",
               "op_days_wbgt_in2_gt_ref", "op_days_wbgt_in4_gt_ref", "op_hours_wbgt_in2_gt_ref", "op_hours_wbgt_in4_gt_ref",
               "op_hours_wbgt_in2_gt_ref_acc", "op_hours_wbgt_in4_gt_ref_acc",
               "op_hours_utci_in0_gt28", "op_hours_utci_in0_gt32", "op_hours_utci_in2_gt28", "op_hours_utci_in2_gt32",
               "op_hours_utci_in4_gt28", "op_hours_utci_in4_gt32", "op_hours_utci_sun_gt32",
               *[f"op_hours_wbgt_{x}_gt_ref_{sh}" for x in ("shade", "sun", "in2", "in4") for sh in ("early", "late", "night")],
               "hours_utci_shade_gt28", "hours_utci_sun_gt32", "hours_utci_sun_gt38",
               "proc_hours_paint_application_max_temp", "proc_hours_paint_application_max_rh", "proc_hours_composite_room_cooling",
               "cdh24", "hdh19"]
INDOOR_OFFSETS = [0.0, 2.0, 4.0]


# --------------------------------------------------------------------------- projection / basemap
def laea(lon, lat):
    lam, phi = np.radians(np.asarray(lon, float) - LON0), np.radians(np.asarray(lat, float))
    phi0 = math.radians(LAT0)
    k = np.sqrt(2 / (1 + math.sin(phi0) * np.sin(phi) + math.cos(phi0) * np.cos(phi) * np.cos(lam)))
    x = k * np.cos(phi) * np.sin(lam)
    y = k * (math.cos(phi0) * np.sin(phi) - math.sin(phi0) * np.cos(phi) * np.cos(lam))
    return x, y


def frame():
    lons = np.linspace(BBOX[0], BBOX[2], 60)
    lats = np.linspace(BBOX[1], BBOX[3], 60)
    gx, gy = laea(*np.meshgrid(lons, lats))
    x0, x1, y0, y1 = gx.min(), gx.max(), gy.min(), gy.max()
    scale = MAP_W / (x1 - x0)
    return x0, y1, scale, round((y1 - y0) * scale)


def to_px(lon, lat):
    x0, y1, scale, _ = frame()
    x, y = laea(lon, lat)
    return (x - x0) * scale, (y1 - y) * scale


def build_basemap() -> dict:
    topo = requests.get(WORLD_ATLAS, timeout=120).json()
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        a = np.cumsum(np.array(arc, dtype=float), axis=0)
        arcs.append(np.column_stack([a[:, 0] * sx + tx, a[:, 1] * sy + ty]))

    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        return np.array(pts)

    _, _, _, h = frame()
    paths = []
    for geom in topo["objects"]["countries"]["geometries"]:
        polys = geom.get("arcs", [])
        polys = polys if geom["type"] == "MultiPolygon" else [polys]
        d = []
        for poly in polys:
            for r in poly:
                pts = ring(r)
                if not ((pts[:, 0].max() > BBOX[0] - 3) and (pts[:, 0].min() < BBOX[2] + 3)
                        and (pts[:, 1].max() > BBOX[1] - 3) and (pts[:, 1].min() < BBOX[3] + 3)):
                    continue
                x, y = to_px(pts[:, 0], pts[:, 1])
                keep = [0]
                for i in range(1, len(x)):
                    if math.hypot(x[i] - x[keep[-1]], y[i] - y[keep[-1]]) > 1.2:
                        keep.append(i)
                if len(keep) < 4:
                    continue
                d.append("M" + "L".join(f"{x[i]:.1f},{y[i]:.1f}" for i in keep) + "Z")
        if d:
            paths.append("".join(d))
    # graticule
    grat = []
    for lon in range(-25, 36, 5):
        x, y = to_px(np.full(40, lon), np.linspace(BBOX[1] - 2, BBOX[3] + 2, 40))
        grat.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y)))
    for lat in range(30, 66, 5):
        x, y = to_px(np.linspace(BBOX[0] - 4, BBOX[2] + 4, 60), np.full(60, lat))
        grat.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y)))
    return {"width": MAP_W, "height": h, "land": paths, "graticule": "".join(grat),
            "source": "Natural Earth 1:50m via world-atlas 2.0.2"}


# --------------------------------------------------------------------------- weather statistics
def hour_start_local(index, tz):
    return (index - pd.Timedelta(hours=1)).tz_convert(tz)


def tmy_stats(df: pd.DataFrame, site) -> dict:
    tz = site.timezone
    df = df.astype({c: "float64" for c in df.columns if df[c].dtype == "float32"})
    t = df["temp_air"].to_numpy(float)
    local = hour_start_local(df.index, tz)
    month, hour = local.month.to_numpy(), local.hour.to_numpy()
    hc = settings()["heat"]
    v_in, ref, ref_a = hc.get("indoor_air_speed_ms", 0.3), hc["wbgt_reference_c"], hc["wbgt_reference_acclimatised_c"]
    hf = heat_frame(df, site.lat, site.lon, indoor_air_speed=v_in)
    u_sh, u_su = hf["utci_shade"].to_numpy(), hf["utci_sun"].to_numpy()
    u_in = {off: utci_indoor(df, off, v_in) for off in INDOOR_OFFSETS}
    w_su = hf["wbgt_sun"].to_numpy()
    w_in = {off: (hf["wbgt_shade"].to_numpy() if off == 0 else
                  wbgt_liljegren(df, site.lat, site.lon, sun=False, indoor_offset=off, air_speed=v_in)["wbgt"].to_numpy())
            for off in INDOOR_OFFSETS}
    daily = pd.DataFrame({"t": t}, index=local.normalize()).groupby(level=0)["t"].max()
    shifts = {}
    for name, (a, b) in SHIFTS.items():
        m = operating_hours_mask(df.index, tz, a, b)
        # "gt_ref" = above the headline (not acclimatised) WBGT reference, "gt_ref_acc" = acclimatised (D58)
        sh = {"sun_gt_ref": int((w_su[m] > ref).sum()), "sun_gt_ref_acc": int((w_su[m] > ref_a).sum())}
        for off, w in w_in.items():
            sh[f"in{int(off)}_gt_ref"] = int((w[m] > ref).sum())
            sh[f"in{int(off)}_gt_ref_acc"] = int((w[m] > ref_a).sum())
        shifts[name] = sh
    hist_bins = np.arange(-10, 47)
    return {
        "temp_bands": [int(((t >= lo) & (t < hi)).sum()) for lo, hi, _ in TEMP_BANDS],
        "temp_hist": np.histogram(np.clip(t, -10, 45.99), bins=hist_bins)[0].tolist(),
        "month_hour_t": [[round(float(t[(month == m) & (hour == h)].mean()), 2) for h in range(24)] for m in range(1, 13)],
        "monthly_tmax": [round(float(daily[daily.index.month == m].mean()), 2) for m in range(1, 13)],
        "utci_bands": [int(((u_sh >= lo) & (u_sh < hi)).sum()) for lo, hi in UTCI_BANDS],
        "utci_bands_sun": [int(((u_su >= lo) & (u_su < hi)).sum()) for lo, hi in UTCI_BANDS],
        "utci_heat_by_hour": [int(((u_sh > 28) & (hour == h)).sum()) for h in range(24)],
        "utci_heat_by_hour_sun": [int(((u_su > 28) & (hour == h)).sum()) for h in range(24)],
        **{f"utci_bands_in{int(o)}": [int(((u >= lo) & (u < hi)).sum()) for lo, hi in UTCI_BANDS] for o, u in u_in.items()},
        **{f"utci_heat_by_hour_in{int(o)}": [int(((u > 28) & (hour == h)).sum()) for h in range(24)] for o, u in u_in.items()},
        "shifts": shifts,
    }


def site_tmy_block(job):
    """All weather-summary statistics for one site (runs in a worker process)."""
    sid, hot_year, models, scenarios, periods = job
    site = next(s for s in load_sites() if s.site_id == sid)
    t = {"hist": tmy_stats(pd.read_parquet(WEATHER_DIR / "tmy" / f"{sid}_tmy.parquet"), site),
         "hotref": tmy_stats(pd.read_parquet(WEATHER_DIR / "hot_year" / f"{sid}_{hot_year}.parquet"), site)}
    for sc in scenarios:
        for per in periods:
            t[f"{sc}_{per}"] = combine([tmy_stats(pd.read_parquet(WEATHER_DIR / "future" / "tmy" / f"{sid}_{m}_{sc}_{per}.parquet"), site)
                                        for m in models])
            t[f"hot_{sc}_{per}"] = combine([tmy_stats(pd.read_parquet(WEATHER_DIR / "future" / "hot_year" / f"{sid}_{m}_{sc}_{per}.parquet"), site)
                                            for m in models])
    print(f"{sid}: ok", flush=True)
    return sid, t


def combine(stats_list: list[dict]) -> dict:
    """Model median of every statistic, plus min/max for the scalar ones."""
    out = {}
    for key in stats_list[0]:
        vals = [s[key] for s in stats_list]
        if key == "shifts":
            out[key] = {sh: {k: [float(np.median([v[sh][k] for v in vals])), float(min(v[sh][k] for v in vals)),
                                  float(max(v[sh][k] for v in vals))] for k in vals[0][sh]} for sh in vals[0]}
            continue
        else:
            arr = np.array(vals, dtype=float)
            out[key] = np.round(np.median(arr, axis=0), 2).tolist()
            if key.startswith("temp_bands") or key.startswith("utci_bands"):
                out[key + "_min"] = np.round(arr.min(axis=0), 1).tolist()
                out[key + "_max"] = np.round(arr.max(axis=0), 1).tolist()
    return out


# --------------------------------------------------------------------------- main
def main() -> None:
    cfg = settings()
    fc = cfg["future"]
    models = list(fc["models"])
    sites = sorted(load_sites(), key=lambda s: -s.lat)
    grid = pd.read_csv(ROOT / "outputs/phase1/era5_grid_points.csv").set_index("site_id")
    hot = pd.read_csv(ROOT / "outputs/phase1/hot_reference_years.csv").set_index("site_id")
    hist_annual = pd.read_csv(ROOT / "outputs/phase1/annual_summary.csv")
    ens = pd.read_csv(ROOT / "outputs/phase2/ensemble_summary.csv", dtype={"period": str})
    checks = pd.read_csv(ROOT / "outputs/phase2/morph_checks.csv", dtype={"period": str})
    fut_annual = pd.read_csv(ROOT / "outputs/phase2/annual_summary_future.csv", dtype={"period": str})

    if not BASEMAP.exists():
        BASEMAP.write_text(json.dumps(build_basemap()))
    basemap = json.loads(BASEMAP.read_text())

    site_rows, kpi, tmy = [], {}, {}
    for s in sites:
        x, y = to_px(s.lon, s.lat)
        hy = int(hot.loc[s.site_id, "hot_year"])
        g = grid.loc[s.site_id]
        site_rows.append({"id": s.site_id, "name": s.name, "country": s.country, "lat": s.lat, "lon": s.lon,
                          "x": round(float(x), 1), "y": round(float(y), 1), "hot_year": hy,
                          "grid": [float(g.grid_lat), float(g.grid_lon), float(g.distance_km)], "tz": s.timezone})
        # headline indicators (multi-year analysis)
        k = {}
        e = ens[ens.site_id == s.site_id]
        hr = hist_annual[(hist_annual.site_id == s.site_id) & (hist_annual.year == hy)].iloc[0]
        # the hot reference year adjusted to each future climate ("2025 weather in 2050"), across models
        hf = fut_annual[(fut_annual.site_id == s.site_id) & (fut_annual.source_year == hy)]
        for m in KPI_METRICS:
            em = e[e.metric == m]
            k[m] = {"hist": {yt: round(float(em[(em.scenario == "historical") & (em.year_type == yt)]["median"].iloc[0]), 1)
                             for yt in ("typical", "hot")},
                    "hotref": round(float(hr[m]), 1)}
            for sc in fc["scenarios"]:
                for per in fc["periods"]:
                    for yt in ("typical", "hot"):
                        r = em[(em.scenario == sc) & (em.period == per) & (em.year_type == yt)].iloc[0]
                        k[m][f"{sc}_{per}_{yt}"] = [round(float(r["median"]), 1), round(float(r["min"]), 1), round(float(r["max"]), 1)]
                    v = hf[(hf.scenario == sc) & (hf.period == per)][m]
                    k[m][f"hotref_{sc}_{per}"] = [round(float(v.median()), 1), round(float(v.min()), 1), round(float(v.max()), 1)]
        c = checks[checks.site_id == s.site_id]
        k["warming"] = {f"{sc}_{per}": [round(float(v.median()), 2), round(float(v.min()), 2), round(float(v.max()), 2)]
                        for (sc, per), v in c.groupby(["scenario", "period"])["annual_warming_model_tas"]}
        kpi[s.site_id] = k


    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [(x["id"], x["hot_year"], models, fc["scenarios"], list(fc["periods"])) for x in site_rows]
        tmy = dict(pool.map(site_tmy_block, jobs))

    data = {
        "meta": {
            "generated": dt.date.today().isoformat(),
            "baseline": [cfg["baseline"]["start_year"], cfg["baseline"]["end_year"]],
            "models": models, "scenarios": fc["scenarios"], "periods": list(fc["periods"]),
            "temp_bands": [b[2] for b in TEMP_BANDS],
            "operating_hours": cfg["operating_hours"],
            "indoor_offsets": INDOOR_OFFSETS,
            "indoor_air_speed": cfg["heat"].get("indoor_air_speed_ms", 0.3),
            "wbgt_ref": cfg["heat"]["wbgt_reference_c"],
            "wbgt_ref_acc": cfg["heat"]["wbgt_reference_acclimatised_c"],
            "process_limits": {k: v["label"] for k, v in cfg["heat"]["process_limits"].items()},
        },
        "basemap": basemap, "sites": site_rows, "kpi": kpi, "tmy": tmy,
    }
    DASH.mkdir(exist_ok=True)
    (DASH / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    template = (DASH / "template.html").read_text()
    fonts = "".join(
        f'@font-face{{font-family:"{fam}";src:url(data:font/woff2;base64,'
        f'{base64.b64encode((DASH / "fonts" / fn).read_bytes()).decode()}) format("woff2");'
        f'font-weight:100 900;font-style:normal;font-display:swap;}}'
        for fam, fn in (("Geist", "geist.woff2"), ("Geist Mono", "geistmono.woff2")))
    page = template.replace("/*__FONTS__*/", fonts).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    (DASH / "page.html").write_text(page)
    (DASH / "index.html").write_text(
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        "<style>html,body{margin:0}</style>\n</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    print(f"page.html {len(page) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
