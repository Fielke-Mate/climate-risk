"""Heat-stress metrics (Phase 3): WBGT (Liljegren), UTCI (sun and shade), process limits.

WBGT: Liljegren et al. (2008) model of the outdoor wet bulb globe temperature,
via the `pywbgt` package, which wraps Argonne's original C code. It predicts the
natural wet bulb and the 2-inch black globe temperature from temperature, dew
point, pressure, wind (10 m, adjusted to 2 m) and global solar radiation.
  * sun:   the full model (outdoor work in direct sun)
  * shade / indoor: the same model with solar radiation set to zero. Indoors (D52) the
           air speed is the hall's occupied-zone speed (default 0.3 m/s, exhaust-ventilated
           warehouse, no active cooling) instead of the outdoor wind, and the hall temperature
           is outdoor + `indoor_offset` (D14).
The reference for moderate work (ISO 7243 Class 2, acclimatised) is 28 C (D22).

UTCI: `pythermalcomfort` (Broede et al. 2012 polynomial).
  * indoor (naturally ventilated / unconditioned halls, D51): hall air temperature (outdoor +
           heat gain, same moisture), radiant temperature = air, still air (0.5 m/s at the 10 m
           reference height, ~0.3 m/s at body height). PMV / adaptive comfort are kept for
           mechanically conditioned rooms only.
  * shade: mean radiant temperature = air temperature, outdoor wind
  * sun:   mean radiant temperature = air temperature + the solar gain to a standing
           person from ASHRAE 55 SolarCal (direct-beam radiation, sun position, side-on
           to the sun, short-wave absorptivity 0.7, ground reflectance 0.2). The 2-inch
           globe of the WBGT model is not used for this: converting a small globe's
           temperature to a person's radiant temperature overstates it badly.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

def _dew_from_rh(temp_c, rh):
    rh = np.clip(np.asarray(rh, float), 1e-3, 100.0)
    gamma = np.log(rh / 100.0) + 17.62 * temp_c / (243.12 + temp_c)
    return 243.12 * gamma / (17.62 - gamma)


def wbgt_liljegren(df: pd.DataFrame, lat: float, lon: float, sun: bool = True,
                   indoor_offset: float = 0.0, air_speed: float | None = None) -> pd.DataFrame:
    """Liljegren WBGT for an hourly standard-format frame (UTC, hour-ending labels).

    Returns columns: tg (globe), tnwb (natural wet bulb), wbgt, speed2m [C, m/s].
    With indoor_offset > 0 the air temperature is raised and the dew point kept
    (same moisture, lower RH), which is how an indoor heat gain behaves.
    air_speed: if given, a fixed air speed [m/s] at 2 m replaces the outdoor 10 m wind
    (indoor use); the model's outdoor minimum of ~1 m/s is lowered to its absolute floor.
    """
    from metpy.units import units
    from pywbgt import liljegrenWBGT

    t = df["temp_air"].to_numpy(float) + indoor_offset
    td = np.minimum(df["temp_dew"].to_numpy(float), t)
    ghi = df["ghi"].to_numpy(float) if sun else np.zeros(len(df))
    # pywbgt centres each value at (time - avg/2); passing avg as an array breaks on
    # recent pandas, so shift hour-ending stamps to 30 s before mid-hour ourselves and
    # use the default avg (1 minute, i.e. a further 30 s shift).
    idx = (df.index.tz_convert("UTC").tz_localize(None) - pd.Timedelta(minutes=29, seconds=30)).to_numpy()
    n = len(df)
    if air_speed is None:
        wind, extra = df["wind_speed"].to_numpy(np.float32), {}
    else:
        wind = np.full(n, air_speed, dtype=np.float32)
        extra = {"zspeed": units.Quantity(np.full(n, 2.0, dtype=np.float32), "m"),
                 "min_speed": units.Quantity(0.13, "m/s")}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = liljegrenWBGT(
            idx, np.array([lat], dtype=np.float32), np.array([lon], dtype=np.float32),
            units.Quantity(ghi.astype(np.float32), "W/m**2"),
            units.Quantity(df["pressure"].to_numpy(np.float32), "hPa"),
            units.Quantity(t.astype(np.float32), "degC"),
            units.Quantity(td.astype(np.float32), "degC"),
            units.Quantity(wind, "m/s"),
            **extra,
        )
    return pd.DataFrame({
        "tg": res["Tg"].to("degC").magnitude,
        "tnwb": res["Tnwb"].to("degC").magnitude,
        "wbgt": res["Twbg"].to("degC").magnitude,
        "speed2m": res["speed"].to("m/s").magnitude,
    }, index=df.index)


def solar_delta_mrt(index: pd.DatetimeIndex, lat: float, lon: float, dni) -> np.ndarray:
    """Increase in mean radiant temperature [K] for a standing person in the sun (SolarCal)."""
    import pvlib
    from pythermalcomfort.models import solar_gain

    mid = index - pd.Timedelta(minutes=30)  # hour-ending labels -> mid-hour sun position
    # nrel_numba keeps pvlib.spa compiled; the default method reloads it in plain-Python mode,
    # which breaks pywbgt (it calls the compiled spa functions).
    elev = pvlib.solarposition.get_solarposition(mid, lat, lon, method="nrel_numba")["apparent_elevation"].to_numpy()
    dni = np.asarray(dni, float)
    day = (elev > 1.0) & (dni > 1.0)
    out = np.zeros(len(index))
    if day.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = solar_gain(sol_altitude=np.clip(elev[day], 1, 90), sharp=np.full(day.sum(), 90.0),
                           sol_radiation_dir=dni[day], sol_transmittance=1.0, f_svv=1.0, f_bes=1.0,
                           asw=0.7, posture="standing", floor_reflectance=0.2, round_output=False)
        out[day] = np.asarray(r.delta_mrt, float)
    return out


def utci(ta, tmrt, v10, rh):
    """UTCI [C]; inputs are clipped to the model's validity range."""
    from pythermalcomfort.models import utci as utci_model
    ta = np.asarray(ta, float)
    tmrt = np.clip(np.asarray(tmrt, float), ta - 30, ta + 70)
    v = np.clip(np.asarray(v10, float), 0.5, 17.0)
    return np.asarray(utci_model(tdb=ta, tr=tmrt, v=v, rh=np.asarray(rh, float), limit_inputs=False).utci, float)


def indoor_wind_10m(air_speed: float) -> float:
    """UTCI's wind input is at 10 m: body-height speed x1.5 (UTCI convention), floored at 0.5 m/s."""
    return max(0.5, 1.5 * air_speed)


def utci_indoor(df: pd.DataFrame, offset: float = 0.0, air_speed: float = 0.3) -> np.ndarray:
    """UTCI inside an exhaust-ventilated hall: air = outdoor + offset (same moisture), Tmrt = air, indoor air speed."""
    from .weather import relative_humidity_from_dewpoint
    t = df["temp_air"].to_numpy(float) + offset
    rh = relative_humidity_from_dewpoint(t, np.minimum(df["temp_dew"].to_numpy(float), t))
    return utci(t, t, np.full(len(t), indoor_wind_10m(air_speed)), rh)


def heat_frame(df: pd.DataFrame, lat: float, lon: float, indoor_offset: float = 0.0,
               indoor_air_speed: float = 0.3) -> pd.DataFrame:
    """All Phase 3 hourly heat variables for one weather record.

    wbgt_shade / utci_indoor are the INDOOR values (no solar, hall air speed, hall = outdoor + offset).
    utci_shade keeps the outdoor-shade UTCI (outdoor wind) for reference.
    """
    sun = wbgt_liljegren(df, lat, lon, sun=True)
    shade = wbgt_liljegren(df, lat, lon, sun=False, indoor_offset=indoor_offset, air_speed=indoor_air_speed)
    ta, rh, v10 = df["temp_air"].to_numpy(float), df["relative_humidity"].to_numpy(float), df["wind_speed"].to_numpy(float)
    d_mrt = solar_delta_mrt(df.index, lat, lon, df["dni"].to_numpy(float))
    out = pd.DataFrame(index=df.index)
    out["wbgt_sun"] = sun["wbgt"].to_numpy()
    out["wbgt_shade"] = shade["wbgt"].to_numpy()
    out["tmrt_sun"] = ta + d_mrt
    out["utci_sun"] = utci(ta, ta + d_mrt, v10, rh)
    out["utci_shade"] = utci(ta, ta, v10, rh)
    out["utci_indoor"] = utci_indoor(df, indoor_offset, indoor_air_speed)
    return out
