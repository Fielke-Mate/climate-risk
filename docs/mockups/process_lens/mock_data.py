"""Mock-up data for the process-limit lens: hourly dry bulb per site and year variant, uint8 at 0.25 C from -10 C.
Today = typical year (TMY) and hot reference year as they are. Futures = the same year plus the month x hour mean
change between the dashboard's future and today series (an approximation of the morph; tails slightly understated)."""
import base64, json, sys
import numpy as np, pandas as pd
R = "/home/user/climate-risk"
d = json.load(open(f"{R}/dashboard/data.json"))
out = {}
for s in d["sites"]:
    sid, tz, hy = s["id"], s["tz"], s["hot_year"]
    T = d["tmy"][sid]
    bases = {"hist": pd.read_parquet(f"{R}/data/weather/tmy/{sid}_tmy.parquet"),
             "hotref": pd.read_parquet(f"{R}/data/weather/hot_year/{sid}_{hy}.parquet"),
             "extref": pd.read_parquet(f"{R}/data/weather/extreme_year/{sid}_{s['extreme_year']}.parquet")}
    site = {"v": {}, "loc": {}}
    for b, df in bases.items():
        local = (df.index - pd.Timedelta(hours=1)).tz_convert(tz)
        m, h = local.month.to_numpy() - 1, local.hour.to_numpy()
        ld = local.strftime("%m-%d").to_numpy(); day = np.concatenate([[0], np.cumsum(ld[1:] != ld[:-1])])
        site["loc"][b] = base64.b64encode(np.concatenate([m.astype(np.uint8), h.astype(np.uint8)]).tobytes()).decode()
        site["loc"][b + "_day"] = base64.b64encode(day.astype(np.uint16).tobytes()).decode()
        t0 = df["temp_air"].to_numpy(float)
        variants = {b: t0}
        for sc in ("ssp245", "ssp585"):
            for per in ("2040", "2050"):
                key = {"hist": f"{sc}_{per}", "hotref": f"hot_{sc}_{per}", "extref": f"ext_{sc}_{per}"}[b]
                dl = np.array(T[key]["month_hour_t"]) - np.array(T[b]["month_hour_t"])
                variants[key] = t0 + dl[m, h]
        for k, t in variants.items():
            q = np.clip(np.round((t + 10) * 4), 0, 255).astype(np.uint8)
            site["v"][k] = base64.b64encode(q.tobytes()).decode()
    out[sid] = site
js = json.dumps(out, separators=(",", ":"))
open(sys.argv[1], "w").write(js)
print(len(js) / 1e6, "MB")
