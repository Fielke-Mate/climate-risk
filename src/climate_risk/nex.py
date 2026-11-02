"""NEX-GDDP-CMIP6 daily projections at the pilot sites.

Files are global, one variable-year each, stored as whole daily fields, so
point reads from S3 need the full ~245 MB file. Instead we use NASA NCCS
THREDDS "NetCDF Subset Service", which cuts a small box on the server. The
grid uses 0-360 longitudes, so western (lon < 0) and eastern sites are
requested as two boxes. Each (model, scenario, variable, year) is cached as a
small parquet table: one row per day, one column per site.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

from .config import RAW_DIR, Site, settings

NEX_DIR = RAW_DIR / "nex"
GRID_RES = 0.25


def nex_cell(lat: float, lon: float) -> tuple[float, float]:
    """Centre of the NEX-GDDP 0.25 deg cell containing the point (lon in 0-360)."""
    lon360 = lon % 360.0
    clat = np.floor(lat / GRID_RES) * GRID_RES + GRID_RES / 2
    clon = np.floor(lon360 / GRID_RES) * GRID_RES + GRID_RES / 2
    return round(float(clat), 3), round(float(clon), 3)


def file_name(var: str, model: str, scenario: str, member: str, year: int) -> str:
    grid = "gr" if model in {"EC-Earth3", "IPSL-CM6A-LR", "INM-CM5-0", "KACE-1-0-G"} else "gn"
    return f"{model}/{scenario}/{member}/{var}/{var}_day_{model}_{scenario}_{member}_{grid}_{year}_v2.0.nc"


def cache_path(model: str, scenario: str, var: str, year: int) -> Path:
    return NEX_DIR / model / scenario / var / f"{year}.parquet"


def _boxes(sites: list[Site]) -> list[tuple[list[Site], dict]]:
    west = [s for s in sites if s.lon < 0]
    east = [s for s in sites if s.lon >= 0]
    out = []
    for group in (west, east):
        if not group:
            continue
        cells = [nex_cell(s.lat, s.lon) for s in group]
        lats = [c[0] for c in cells]
        lons = [c[1] for c in cells]
        out.append((group, {"north": max(lats) + 0.2, "south": min(lats) - 0.2,
                            "west": min(lons) - 0.2, "east": max(lons) + 0.2}))
    return out


def _request(url: str, params: dict, retries: int = 4, timeout: int = 300) -> bytes:
    err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200 and r.content[:4] in (b"\x89HDF", b"CDF\x01", b"CDF\x02"):
                return r.content
            err = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as exc:
            err = exc
        time.sleep(5 * 2**attempt)
    raise RuntimeError(f"NEX request failed after {retries} attempts: {err}")


def fetch_year(sites: list[Site], model: str, member: str, scenario: str, var: str, year: int,
               overwrite: bool = False) -> Path:
    """Daily values of one variable-year at every site's NEX cell (cached)."""
    out = cache_path(model, scenario, var, year)
    if out.exists() and not overwrite:
        return out
    base = settings()["future"]["thredds"]
    url = f"{base}/{file_name(var, model, scenario, member, year)}"
    frames = []
    for group, box in _boxes(sites):
        content = _request(url, {"var": var, "temporal": "all", "accept": "netcdf4", **box})
        coder = xr.coders.CFDatetimeCoder(use_cftime=True)
        with xr.open_dataset(io.BytesIO(content), engine="h5netcdf", decode_times=coder) as ds:
            da = ds[var].load()
        cols = {}
        for s in group:
            clat, clon = nex_cell(s.lat, s.lon)
            cols[s.site_id] = da.sel(lat=clat, lon=clon, method="nearest").to_numpy()
        times = da["time"].to_numpy()
        frames.append(pd.DataFrame(cols, index=pd.Index(
            [f"{t.year:04d}-{t.month:02d}-{t.day:02d}" for t in times], name="date")))
    df = pd.concat(frames, axis=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.astype("float32").to_parquet(out)
    return out


def load_series(model: str, scenario: str, var: str, years: list[int]) -> pd.DataFrame:
    """Concatenate cached years. Index is a 'YYYY-MM-DD' string (model calendars vary)."""
    return pd.concat([pd.read_parquet(cache_path(model, scenario, var, y)) for y in years])
