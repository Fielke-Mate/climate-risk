import numpy as np
import pandas as pd
import pytest

from climate_risk import tmy, weather
from climate_risk.annual import annual_summary, select_hot_year
from climate_risk.config import settings


def test_relative_humidity_bounds_and_saturation():
    assert weather.relative_humidity_from_dewpoint(20.0, 20.0) == pytest.approx(100.0)
    rh = weather.relative_humidity_from_dewpoint(30.0, 15.0)
    assert 38 < rh < 42  # ~40 % (psychrometric tables)


def test_wind_direction_convention():
    # wind blowing from the west (towards +x): u > 0, v = 0 -> direction 270
    speed, direction = weather.wind_speed_direction(5.0, 0.0)
    assert speed == pytest.approx(5.0)
    assert direction == pytest.approx(270.0)
    _, from_north = weather.wind_speed_direction(0.0, -3.0)
    assert from_north == pytest.approx(0.0)


def test_wet_bulb_stull_reference_value():
    # Stull (2011): T = 20 C, RH = 50 % -> Tw ~ 13.7 C
    assert weather.wet_bulb_stull(20.0, 50.0) == pytest.approx(13.7, abs=0.1)


def test_operating_hours_mask_local_time():
    idx = pd.date_range("2022-07-01 00:00", periods=48, freq="h", tz="UTC") + pd.Timedelta(hours=1)
    mask = weather.operating_hours_mask(idx, "Europe/Madrid", "06:00", "22:00")
    assert mask.sum() == 32  # 16 hours per day
    starts_local = (idx - pd.Timedelta(hours=1)).tz_convert("Europe/Madrid")
    assert set(starts_local[mask].hour) == set(range(6, 22))


def test_fs_statistic_zero_for_identical_distribution():
    vals = np.arange(30, dtype=float)
    assert tmy.fs_statistic(vals, np.tile(vals, 5)) == pytest.approx(0.0, abs=1e-9)
    assert tmy.fs_statistic(vals + 10, np.tile(vals, 5)) > 5


def _synthetic(years=range(2015, 2020), seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{years[0]}-01-01 01:00", f"{years[-1] + 1}-01-01 00:00", freq="h", tz="UTC")
    doy = idx.day_of_year.to_numpy()
    hour = idx.hour.to_numpy()
    offset = {y: (y - 2017) * 1.5 for y in years}  # 2017 is the "typical" year
    base = 12 + 10 * np.sin(2 * np.pi * (doy - 110) / 365) + 5 * np.sin(2 * np.pi * (hour - 9) / 24)
    temp = base + np.array([offset[y] for y in (idx - pd.Timedelta(hours=1)).year]) + rng.normal(0, 0.5, len(idx))
    df = pd.DataFrame(index=idx)
    df["temp_air"] = temp
    df["temp_dew"] = temp - 6
    df["relative_humidity"] = weather.relative_humidity_from_dewpoint(df["temp_air"], df["temp_dew"])
    df["pressure"] = 1013.0
    df["wind_speed"] = 3 + rng.normal(0, 0.2, len(idx)).clip(-2, 2)
    df["wind_direction"] = 200.0
    df["ghi"] = np.clip(600 * np.sin(2 * np.pi * (hour - 6) / 24), 0, None)
    df["dni"] = df["ghi"] * 0.8
    df["dhi"] = df["ghi"] * 0.2
    df["lw_down"] = 330.0
    return df


def test_tmy_picks_typical_year_and_has_8760_hours():
    hourly = _synthetic()
    out, sel = tmy.build(hourly)
    assert len(out) == 8760
    assert out.index[0] == pd.Timestamp("2001-01-01 01:00", tz="UTC")
    # ISO 15927-4: wind speed picks among the 3 best-ranked years, so the extreme
    # years (coldest 2015, warmest 2019) must never be chosen.
    assert set(sel["year"]) <= {2016, 2017, 2018}
    assert sel["candidates"].str.contains("2017").all()
    assert not out[["temp_air", "relative_humidity", "ghi"]].isna().any().any()
    assert weather.validate(out) == []


def test_hot_year_is_the_warmest_synthetic_year():
    hourly = _synthetic()
    hourly["temp_air"] += 12  # push summer working hours above WBGT 28
    hourly["temp_dew"] = hourly["temp_air"] - 4
    hourly["relative_humidity"] = weather.relative_humidity_from_dewpoint(hourly["temp_air"], hourly["temp_dew"])
    summary = annual_summary(hourly, 40.3, -3.7, "Europe/Madrid", settings())
    assert select_hot_year(summary) == 2019


def test_hot_year_degree_hours_separates_years_without_exceedances():
    hourly = _synthetic()
    hourly["temp_air"] += 9  # WBGT reaches the mid-20s but not 28
    hourly["temp_dew"] = hourly["temp_air"] - 6
    hourly["relative_humidity"] = weather.relative_humidity_from_dewpoint(hourly["temp_air"], hourly["temp_dew"])
    summary = annual_summary(hourly, 40.3, -3.7, "Europe/Madrid", settings())
    assert summary["op_wbgt_shade_degree_hours_gt_base"].nunique() > 1
    assert select_hot_year(summary) == 2019
