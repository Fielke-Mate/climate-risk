"""Project paths and settings."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WEATHER_DIR = DATA_DIR / "weather"
SITES_FILE = DATA_DIR / "sites" / "pilot_aerospace_europe.csv"


@lru_cache(maxsize=1)
def settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def shifts(cfg: dict | None = None) -> dict[str, tuple[str, str]]:
    """Shift name -> (start, end) local time, from config `shifts` (one definition for every module)."""
    return {k: (str(a), str(b)) for k, (a, b) in (cfg or settings())["shifts"].items()}


@dataclass(frozen=True)
class Site:
    site_id: str
    name: str
    country: str
    lat: float
    lon: float

    @property
    def timezone(self) -> str:
        return settings()["timezones"][self.country]


def load_sites(path: Path = SITES_FILE) -> list[Site]:
    df = pd.read_csv(path)
    return [
        Site(r.site_id, r.name, r.country, float(r.lat), float(r.lon))
        for r in df.itertuples(index=False)
    ]


def hourly_path(site_id: str, kind: str = "baseline") -> Path:
    """The site's hourly ERA5 record. kind: "baseline" (2015-2025 as observed: headline statistics, TMY,
    future morphing), "extended" (2000-2025 as observed) or "adjusted" (2000-2025, every year moved to the
    reference climate, D61)."""
    b = settings()["baseline"]
    if kind == "baseline":
        return WEATHER_DIR / "hourly" / f"{site_id}_era5_{b['start_year']}_{b['end_year']}.parquet"
    tag = {"extended": "", "adjusted": f"_adj{b['reference_year']}"}[kind]
    return WEATHER_DIR / "hourly" / f"{site_id}_era5_{b['extended_start_year']}_{b['end_year']}{tag}.parquet"
