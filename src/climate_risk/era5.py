"""ERA5 hourly point time series from the Copernicus Climate Data Store (CDS).

Uses the `reanalysis-era5-single-levels-timeseries` product, which returns the
nearest 0.25 degree grid point for a location. The API key is read from the
CDSAPI_KEY environment variable and is never written to disk by this module.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from .config import RAW_DIR, Site, settings
from .weather import relative_humidity_from_dewpoint, wind_speed_direction


def raw_path(site: Site, start_year: int, end_year: int) -> Path:
    return RAW_DIR / "era5" / f"{site.site_id}_{start_year}_{end_year}.zip"


def fetch(site: Site, start_year: int, end_year: int, overwrite: bool = False) -> Path:
    """Download the raw ERA5 time series for a site (cached)."""
    out = raw_path(site, start_year, end_year)
    if out.exists() and not overwrite:
        return out
    key = os.environ.get("CDSAPI_KEY")
    if not key:
        raise RuntimeError("CDSAPI_KEY environment variable is not set")
    import cdsapi  # imported lazily so the rest of the package works without it

    cfg = settings()["era5"]
    out.parent.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client(url=cfg["url"], key=key, quiet=True, progress=False)
    tmp = out.with_suffix(".part")
    client.retrieve(cfg["dataset"], {
        "variable": cfg["variables"],
        "location": {"latitude": site.lat, "longitude": site.lon},
        "date": [f"{start_year}-01-01/{end_year + 1}-01-01"],  # +1 day completes the final hour
        "data_format": "csv",
    }, str(tmp))
    tmp.replace(out)
    return out


def read_raw(path: Path) -> pd.DataFrame:
    """Read the CSV inside a CDS time-series zip (or a bare CSV)."""
    data = Path(path).read_bytes()
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            frames = [pd.read_csv(zf.open(n)) for n in zf.namelist() if n.endswith(".csv")]
        df = frames[0]
        for extra in frames[1:]:  # some requests come back split by variable group
            df = df.merge(extra, on=[c for c in ("valid_time", "latitude", "longitude") if c in extra], how="outer")
    else:
        df = pd.read_csv(io.BytesIO(data))
    return df


def standardise(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Convert raw ERA5 columns to the standard hourly format (see weather.py).

    Accumulated fields (radiation, precipitation) are totals over the hour ending
    at valid_time; they are converted to hourly means (W/m2) or mm. DNI is derived
    from the direct horizontal component and the sun position at mid-hour.
    """
    df = raw.copy()
    df["valid_time"] = pd.to_datetime(df["valid_time"], utc=True)
    df = df.set_index("valid_time").sort_index()
    df = df[~df.index.duplicated()]
    grid = {"grid_lat": float(df["latitude"].iloc[0]), "grid_lon": float(df["longitude"].iloc[0])}

    out = pd.DataFrame(index=df.index)
    out["temp_air"] = df["t2m"] - 273.15
    out["temp_dew"] = df["d2m"] - 273.15
    out["relative_humidity"] = relative_humidity_from_dewpoint(out["temp_air"], out["temp_dew"])
    out["pressure"] = df["sp"] / 100.0
    speed, direction = wind_speed_direction(df["u10"], df["v10"])
    out["wind_speed"] = speed
    out["wind_direction"] = direction

    ghi = (df["ssrd"] / 3600.0).clip(lower=0)
    direct_h = (df["fdir"] / 3600.0).clip(lower=0).clip(upper=ghi)
    mid_hour = df.index - pd.Timedelta(minutes=30)
    solpos = pvlib.solarposition.get_solarposition(mid_hour, grid["grid_lat"], grid["grid_lon"])
    cos_z = np.cos(np.radians(solpos["apparent_zenith"].to_numpy()))
    dni = np.where(cos_z > np.cos(np.radians(87.0)), direct_h.to_numpy() / np.maximum(cos_z, 1e-6), 0.0)
    out["ghi"] = ghi
    out["dni"] = np.clip(dni, 0.0, 1200.0)
    out["dhi"] = (ghi - direct_h).clip(lower=0)
    out["lw_down"] = df["strd"] / 3600.0
    if "ssr" in df:
        out["net_sw"] = df["ssr"] / 3600.0
    if "str" in df:
        out["net_lw"] = df["str"] / 3600.0
    if "tcc" in df:
        out["cloud_cover"] = df["tcc"]
    if "tp" in df:
        out["precipitation"] = (df["tp"] * 1000.0).clip(lower=0)
    return out, grid
