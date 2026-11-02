"""Standard hourly weather format and unit conversions.

Every weather source (ERA5, PVGIS, EPW, ...) is converted to the same hourly
DataFrame, indexed by UTC timestamps that mark the END of each hour (instantaneous
values are at that time; radiation is the mean over the preceding hour), with
these columns:

    temp_air          air temperature at 2 m [C]
    temp_dew          dew point at 2 m [C]
    relative_humidity [%]
    pressure          surface pressure [hPa]
    wind_speed        at 10 m [m/s]
    wind_direction    at 10 m, direction the wind blows FROM [deg]
    ghi               global horizontal irradiance [W/m2]
    dni               direct normal irradiance [W/m2]
    dhi               diffuse horizontal irradiance [W/m2]
    lw_down           downward longwave (thermal) radiation [W/m2]

Optional columns (ERA5 only): net_sw, net_lw [W/m2], cloud_cover [0-1],
precipitation [mm].
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STANDARD_COLUMNS = [
    "temp_air", "temp_dew", "relative_humidity", "pressure",
    "wind_speed", "wind_direction", "ghi", "dni", "dhi", "lw_down",
]


def saturation_vapour_pressure(temp_c):
    """Saturation vapour pressure over water [hPa] (Magnus, WMO-No. 8 coefficients)."""
    temp_c = np.asarray(temp_c, dtype=float)
    return 6.112 * np.exp(17.62 * temp_c / (243.12 + temp_c))


def relative_humidity_from_dewpoint(temp_c, dew_c):
    """Relative humidity [%] from air temperature and dew point [C], clipped to 0-100."""
    rh = 100.0 * saturation_vapour_pressure(dew_c) / saturation_vapour_pressure(temp_c)
    return np.clip(rh, 0.0, 100.0)


def wind_speed_direction(u, v):
    """Wind speed [m/s] and meteorological direction [deg, blowing FROM] from u/v components."""
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    speed = np.hypot(u, v)
    direction = (np.degrees(np.arctan2(-u, -v)) + 360.0) % 360.0
    return speed, direction


def wet_bulb_stull(temp_c, rh_pct):
    """Psychrometric wet-bulb temperature [C] (Stull 2011 empirical fit).

    Valid roughly for RH 5-99 % and T -20 to 50 C at sea-level pressure.
    """
    t = np.asarray(temp_c, dtype=float)
    rh = np.clip(np.asarray(rh_pct, dtype=float), 5.0, 99.0)
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )


def wbgt_shaded_provisional(temp_c, rh_pct):
    """PROVISIONAL shaded/indoor WBGT [C] = 0.7 * wet bulb + 0.3 * air temperature.

    Assumes no radiant load (globe temperature = air temperature) and uses the
    psychrometric wet bulb in place of the natural wet bulb. Natural wet bulb is
    usually a little higher in still air, so this tends to UNDERESTIMATE WBGT.
    Used in Phase 1 only to rank years; Phase 3 replaces it with the Liljegren method.
    """
    t = np.asarray(temp_c, dtype=float)
    return 0.7 * wet_bulb_stull(t, rh_pct) + 0.3 * t


def operating_hours_mask(index_utc: pd.DatetimeIndex, timezone: str, start: str = "06:00",
                         end: str = "22:00", days=(0, 1, 2, 3, 4, 5, 6),
                         hour_label: str = "end") -> np.ndarray:
    """True for hours inside local operating hours [start, end) on the given weekdays.

    The standard format labels each record with the time at the END of its hour
    (as ERA5 and EPW do), so by default the hour (t-1h, t] is tested by its start
    time t-1h. Pass hour_label="start" for data labelled at the start of the hour.
    """
    starts = index_utc - pd.Timedelta(hours=1) if hour_label == "end" else index_utc
    local = starts.tz_convert(timezone)
    minutes = local.hour * 60 + local.minute
    h0, m0 = (int(x) for x in start.split(":"))
    h1, m1 = (int(x) for x in end.split(":"))
    start_min, end_min = h0 * 60 + m0, h1 * 60 + m1
    if start_min <= end_min:
        in_hours = (minutes >= start_min) & (minutes < end_min)
    else:  # crosses midnight, e.g. 22:00-06:00
        in_hours = (minutes >= start_min) | (minutes < end_min)
    return np.asarray(in_hours & local.day_of_week.isin(list(days)))


def validate(df: pd.DataFrame) -> list[str]:
    """Basic plausibility checks; returns a list of problems (empty if fine)."""
    problems = []
    missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")
    if df.index.tz is None:
        problems.append("index is not timezone-aware (expected UTC)")
    if df.index.has_duplicates:
        problems.append("duplicate timestamps")
    gaps = df.index.to_series().diff().dropna()
    if (gaps != pd.Timedelta(hours=1)).any():
        problems.append(f"{int((gaps != pd.Timedelta(hours=1)).sum())} non-hourly steps")
    checks = {
        "temp_air": (-50, 55), "relative_humidity": (0, 100), "pressure": (500, 1100),
        "wind_speed": (0, 60), "ghi": (0, 1400), "dni": (0, 1400), "dhi": (0, 900),
    }
    for col, (lo, hi) in checks.items():
        if col in df and ((df[col] < lo) | (df[col] > hi)).any():
            problems.append(f"{col} outside {lo}..{hi}")
    if df[STANDARD_COLUMNS].isna().any().any() if not missing else False:
        problems.append("NaNs in standard columns")
    return problems
