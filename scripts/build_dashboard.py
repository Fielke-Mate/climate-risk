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
from climate_risk.weather import operating_hours_mask, wbgt_shaded_provisional

DASH = ROOT / "dashboard"
BASEMAP = DASH / "basemap.json"
WORLD_ATLAS = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"

# Map frame (degrees) and projection: Lambert azimuthal equal-area centred on the portfolio
LON0, LAT0 = 3.0, 46.0
BBOX = (-11.5, 34.5, 17.5, 57.5)  # lon_min, lat_min, lon_max, lat_max
MAP_W = 1000

TEMP_BANDS = [(-99, 16, "< 16"), (16, 21, "16–21"), (21, 24, "21–24 optimal"), (24, 25, "24–25"),
              (25, 30, "25–30"), (30, 35, "30–35"), (35, 99, "> 35")]
UTCI_BANDS = [(-99, -13), (-13, 0), (0, 9), (9, 26), (26, 28), (28, 32), (32, 38), (38, 46), (46, 99)]
SHIFTS = {"early": ("06:00", "14:00"), "late": ("14:00", "22:00"), "night": ("22:00", "06:00")}
KPI_METRICS = ["days_tmax_gt30", "days_tmax_gt35", "hours_t_gt30", "nights_tmin_gt20", "temp_max", "temp_mean",
               "op_wbgt_prov_degree_hours_gt_base", "op_hours_wbgt_prov_gt_threshold", "cdh24", "hdh19"]


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
    for lon in range(-10, 21, 5):
        x, y = to_px(np.full(40, lon), np.linspace(BBOX[1] - 2, BBOX[3] + 2, 40))
        grat.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y)))
    for lat in range(35, 61, 5):
        x, y = to_px(np.linspace(BBOX[0] - 4, BBOX[2] + 4, 60), np.full(60, lat))
        grat.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y)))
    return {"width": MAP_W, "height": h, "land": paths, "graticule": "".join(grat),
            "source": "Natural Earth 1:50m via world-atlas 2.0.2"}


# --------------------------------------------------------------------------- weather statistics
def hour_start_local(index, tz):
    return (index - pd.Timedelta(hours=1)).tz_convert(tz)


def tmy_stats(df: pd.DataFrame, tz: str) -> dict:
    t = df["temp_air"].to_numpy(float)
    rh = df["relative_humidity"].to_numpy(float)
    wind = np.clip(df["wind_speed"].to_numpy(float), 0.5, 17.0)
    local = hour_start_local(df.index, tz)
    month, hour = local.month.to_numpy(), local.hour.to_numpy()

    u = np.asarray(utci_model(tdb=t, tr=t, v=wind, rh=rh, limit_inputs=False).utci, float)
    wbgt = wbgt_shaded_provisional(t, rh)
    daily = pd.DataFrame({"t": t}, index=local.normalize()).groupby(level=0)["t"].max()

    shifts = {}
    for name, (a, b) in SHIFTS.items():
        m = operating_hours_mask(df.index, tz, a, b)
        shifts[name] = {"wbgt_gt28": int((wbgt[m] > 28).sum()), "wbgt_gt26": int((wbgt[m] > 26).sum()),
                        "utci_gt28": int((u[m] > 28).sum())}
    hist_bins = np.arange(-10, 47)
    return {
        "temp_bands": [int(((t >= lo) & (t < hi)).sum()) for lo, hi, _ in TEMP_BANDS],
        "temp_hist": np.histogram(np.clip(t, -10, 45.99), bins=hist_bins)[0].tolist(),
        "month_hour_t": [[round(float(t[(month == m) & (hour == h)].mean()), 2) for h in range(24)] for m in range(1, 13)],
        "monthly_tmax": [round(float(daily[daily.index.month == m].mean()), 2) for m in range(1, 13)],
        "utci_bands": [int(((u >= lo) & (u < hi)).sum()) for lo, hi in UTCI_BANDS],
        "utci_heat_by_hour": [int(((u > 28) & (hour == h)).sum()) for h in range(24)],
        "shifts": shifts,
    }


def combine(stats_list: list[dict]) -> dict:
    """Model median of every statistic, plus min/max for the scalar ones."""
    out = {}
    for key in stats_list[0]:
        vals = [s[key] for s in stats_list]
        if key == "shifts":
            out[key] = {sh: {k: [float(np.median([v[sh][k] for v in vals])), float(min(v[sh][k] for v in vals)),
                                  float(max(v[sh][k] for v in vals))] for k in vals[0][sh]} for sh in vals[0]}
        else:
            arr = np.array(vals, dtype=float)
            out[key] = np.round(np.median(arr, axis=0), 2).tolist()
            if key in ("temp_bands", "utci_bands"):
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
        c = checks[checks.site_id == s.site_id]
        k["warming"] = {f"{sc}_{per}": [round(float(v.median()), 2), round(float(v.min()), 2), round(float(v.max()), 2)]
                        for (sc, per), v in c.groupby(["scenario", "period"])["annual_warming_model_tas"]}
        kpi[s.site_id] = k

        # weather-summary statistics from typical years (TMY) and the hot reference year
        hist_tmy = pd.read_parquet(WEATHER_DIR / "tmy" / f"{s.site_id}_tmy.parquet").astype("float64", errors="ignore")
        hot_df = pd.read_parquet(WEATHER_DIR / "hot_year" / f"{s.site_id}_{hy}.parquet")
        t = {"hist": tmy_stats(hist_tmy, s.timezone), "hotref": tmy_stats(hot_df, s.timezone)}
        for sc in fc["scenarios"]:
            for per in fc["periods"]:
                per_model = [tmy_stats(pd.read_parquet(WEATHER_DIR / "future" / "tmy" / f"{s.site_id}_{m}_{sc}_{per}.parquet"), s.timezone)
                             for m in models]
                t[f"{sc}_{per}"] = combine(per_model)
        tmy[s.site_id] = t
        print(f"{s.site_id}: ok", flush=True)

    data = {
        "meta": {
            "generated": dt.date.today().isoformat(),
            "baseline": [cfg["baseline"]["start_year"], cfg["baseline"]["end_year"]],
            "models": models, "scenarios": fc["scenarios"], "periods": list(fc["periods"]),
            "temp_bands": [b[2] for b in TEMP_BANDS],
            "operating_hours": cfg["operating_hours"],
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
