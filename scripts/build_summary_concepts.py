"""Build the comparison page of five summary-tab concepts (design exploration).

Reads dashboard/data.json (built by build_dashboard.py) plus daily maximum temperatures
computed here from the typical / hot reference years and their 2040 / 2050 versions.

Output: dashboard/concepts/summary_concepts.html (page content for publishing)
Usage:  python scripts/build_summary_concepts.py
"""

from __future__ import annotations

import base64
import json

import numpy as np
import pandas as pd

from climate_risk.config import ROOT, WEATHER_DIR, load_sites, settings

DASH = ROOT / "dashboard"
OUT = DASH / "concepts"


def daily_max(df: pd.DataFrame, tz: str) -> list[float]:
    """365 daily maximum temperatures (local days, 29 Feb dropped)."""
    local = (df.index - pd.Timedelta(hours=1)).tz_convert(tz)
    s = pd.Series(df["temp_air"].to_numpy(float), index=local.normalize()).groupby(level=0).max()
    s = s[~((s.index.month == 2) & (s.index.day == 29))]
    # a typical year spans one nominal year; keep the 365 days that start on 1 January
    s = s[s.index.year == s.index.year.value_counts().idxmax()]
    return [round(float(v), 1) for v in s.to_numpy()[:365]]


def main() -> None:
    cfg = settings()
    fc = cfg["future"]
    data = json.loads((DASH / "data.json").read_text())
    models = list(fc["models"])
    daily = {}
    for s in load_sites():
        hy = next(x["hot_year"] for x in data["sites"] if x["id"] == s.site_id)
        d = {"hist": daily_max(pd.read_parquet(WEATHER_DIR / "tmy" / f"{s.site_id}_tmy.parquet"), s.timezone),
             "hotref": daily_max(pd.read_parquet(WEATHER_DIR / "hot_year" / f"{s.site_id}_{hy}.parquet"), s.timezone)}
        for sc in fc["scenarios"]:
            for per in fc["periods"]:
                for kind, folder in (("", "tmy"), ("hot_", "hot_year")):
                    runs = [daily_max(pd.read_parquet(WEATHER_DIR / "future" / folder / f"{s.site_id}_{m}_{sc}_{per}.parquet"), s.timezone)
                            for m in models]
                    n = min(len(r) for r in runs)
                    d[f"{kind}{sc}_{per}"] = np.round(np.median([r[:n] for r in runs], axis=0), 1).tolist()
        daily[s.site_id] = d
        print(f"{s.site_id}: ok", flush=True)

    keep_kpi = ["days_tmax_gt30", "days_tmax_gt35", "nights_tmin_gt20", "temp_max",
                "op_days_wbgt_shade_gt_ref", "op_days_wbgt_in2_gt_ref", "op_days_wbgt_in4_gt_ref", "op_days_wbgt_sun_gt_ref",
                "op_hours_utci_in0_gt32", "op_hours_utci_sun_gt32", "warming"]
    slim = {
        "meta": data["meta"], "sites": [{k: x[k] for k in ("id", "name", "country", "hot_year")} for x in data["sites"]],
        "kpi": {sid: {m: v for m, v in k.items() if m in keep_kpi} for sid, k in data["kpi"].items()},
        "tmy": {sid: {key: {f: st[f] for f in st if f.startswith(("utci_bands", "month_hour_t", "shifts", "temp_bands"))}
                      for key, st in t.items()} for sid, t in data["tmy"].items()},
        "daily": daily,
    }
    tpl = (OUT / "summary_concepts.template.html").read_text()
    fonts = "".join(
        f'@font-face{{font-family:"{fam}";src:url(data:font/woff2;base64,'
        f'{base64.b64encode((DASH / "fonts" / fn).read_bytes()).decode()}) format("woff2");'
        f'font-weight:100 900;font-style:normal;font-display:swap;}}'
        for fam, fn in (("Geist", "geist.woff2"), ("Geist Mono", "geistmono.woff2")))
    page = tpl.replace("/*__FONTS__*/", fonts).replace("/*__DATA__*/null", json.dumps(slim, separators=(",", ":")))
    (OUT / "summary_concepts.html").write_text(page)
    (OUT / "summary_concepts_full.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n<style>html,body{margin:0}</style>\n'
        "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    print(f"summary_concepts.html {len(page) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
