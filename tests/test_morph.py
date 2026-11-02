import numpy as np
import pandas as pd
import pytest

from climate_risk import morph, weather


def _hourly(days=730, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2016-01-01 01:00", periods=days * 24, freq="h", tz="UTC")
    h = (idx - pd.Timedelta(hours=1)).hour.to_numpy()
    doy = (idx - pd.Timedelta(hours=1)).day_of_year.to_numpy()
    daily_noise = np.repeat(rng.normal(0, 3, days), 24)
    t = 15 + 8 * np.sin(2 * np.pi * (doy - 110) / 365) + 5 * np.sin(2 * np.pi * (h - 9) / 24) + daily_noise
    df = pd.DataFrame(index=idx)
    df["temp_air"] = t
    df["temp_dew"] = t - 7
    df["relative_humidity"] = weather.relative_humidity_from_dewpoint(t, t - 7)
    df["pressure"] = 1010.0
    df["wind_speed"] = 3.0
    df["wind_direction"] = 180.0
    df["ghi"] = np.clip(500 * np.sin(2 * np.pi * (h - 6) / 24), 0, None)
    df["dni"] = df["ghi"] * 0.7
    df["dhi"] = df["ghi"] * 0.3
    df["lw_down"] = 320.0
    return df


def _deltas(dmax_lo, dmax_hi, dmin=1.0, huss=1.0, rsds=1.0):
    qs = [0.05, 0.5, 0.95]
    rows = []
    for m in range(1, 13):
        for q, v in zip(qs, [dmax_lo, (dmax_lo + dmax_hi) / 2, dmax_hi]):
            rows.append({"variable": "tasmax", "month": m, "quantile": q, "kind": "delta", "value": v})
            rows.append({"variable": "tasmin", "month": m, "quantile": q, "kind": "delta", "value": dmin})
        for var, val in (("huss", huss), ("rsds", rsds), ("rlds", 1.0), ("sfcWind", 1.0)):
            rows.append({"variable": var, "month": m, "quantile": np.nan, "kind": "ratio", "value": val})
    return pd.DataFrame(rows)


def test_uniform_delta_shifts_every_hour():
    h = _hourly()
    out = morph.morph(h, _deltas(2.0, 2.0, dmin=2.0), morph.baseline_daily_table(h))
    assert np.allclose(out["temp_air"] - h["temp_air"], 2.0)
    assert weather.validate(out) == []


def test_hot_days_get_larger_warming_than_cool_days():
    h = _hourly()
    out = morph.morph(h, _deltas(1.0, 3.0, dmin=1.0), morph.baseline_daily_table(h))
    starts = h.index - pd.Timedelta(hours=1)
    tmax_before = h["temp_air"].groupby(starts.normalize()).max()
    tmax_after = out["temp_air"].groupby(starts.normalize()).max()
    jul = tmax_before.index.month == 7
    hot = tmax_before[jul] > tmax_before[jul].quantile(0.8)
    cool = tmax_before[jul] < tmax_before[jul].quantile(0.2)
    change = tmax_after[jul] - tmax_before[jul]
    assert change[hot].mean() > change[cool].mean() + 1.0


def test_humidity_scaling_and_saturation_cap():
    h = _hourly()
    out = morph.morph(h, _deltas(0.0, 0.0, dmin=0.0, huss=1.1), morph.baseline_daily_table(h))
    e0 = weather.saturation_vapour_pressure(h["temp_dew"])
    e1 = weather.saturation_vapour_pressure(out["temp_dew"])
    assert np.allclose(e1 / e0, 1.1, rtol=1e-3)
    out2 = morph.morph(h, _deltas(0.0, 0.0, dmin=0.0, huss=1.6), morph.baseline_daily_table(h))
    assert out2["relative_humidity"].max() <= 100.0 + 1e-9


def test_radiation_ratio_applied():
    h = _hourly()
    out = morph.morph(h, _deltas(0, 0, dmin=0, rsds=1.05), morph.baseline_daily_table(h))
    assert out["ghi"].sum() == pytest.approx(h["ghi"].sum() * 1.05, rel=1e-6)


def test_month_weights_continuous():
    a, b, w = morph._daily_month_weights(np.array([1.0, 15.5, 30.0, 45.0, 364.0]))
    assert (a[1], b[1], w[1]) == (0, 1, 0.0) or (b[1] == 0 and w[1] == pytest.approx(1.0))
    assert 0 <= w.min() and w.max() <= 1
