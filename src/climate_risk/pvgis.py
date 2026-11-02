"""PVGIS typical meteorological year (cross-check only).

PVGIS 5.3 TMY: ERA5 meteorology + SARAH-3 satellite radiation, 2005-2023.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests

from .config import Site, settings


def fetch_tmy(site: Site, timeout: int = 120) -> tuple[pd.DataFrame, dict]:
    url = settings()["pvgis"]["url"]
    r = requests.get(url, params={"lat": site.lat, "lon": site.lon, "outputformat": "json"}, timeout=timeout)
    r.raise_for_status()
    js = r.json()
    raw = pd.DataFrame(js["outputs"]["tmy_hourly"])
    idx = pd.DatetimeIndex(pd.to_datetime(raw["time(UTC)"], format="%Y%m%d:%H%M", utc=True))
    df = pd.DataFrame({
        "temp_air": raw["T2m"].to_numpy(),
        "relative_humidity": raw["RH"].to_numpy(),
        "pressure": raw["SP"].to_numpy() / 100.0,
        "wind_speed": raw["WS10m"].to_numpy(),
        "wind_direction": raw["WD10m"].to_numpy(),
        "ghi": raw["G(h)"].to_numpy(),
        "dni": raw["Gb(n)"].to_numpy(),
        "dhi": raw["Gd(h)"].to_numpy(),
        "lw_down": raw["IR(h)"].to_numpy(),
    }, index=idx)
    # Dew point from RH (inverse Magnus)
    rh = np.clip(df["relative_humidity"].to_numpy(), 1, 100)
    gamma = np.log(rh / 100.0) + 17.62 * df["temp_air"] / (243.12 + df["temp_air"])
    df["temp_dew"] = 243.12 * gamma / (17.62 - gamma)
    df["source_year"] = idx.year
    months = pd.DataFrame(js["outputs"]["months_selected"])
    meta = {"inputs": js["inputs"].get("meteo_data", {}), "months_selected": months.to_dict("records")}
    return df, meta
