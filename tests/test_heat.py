import numpy as np
import pandas as pd
import pytest

from climate_risk import heat


def _frame(t, rh_dew, ghi, dni, wind=2.0, when="2022-07-13 14:00"):
    idx = pd.DatetimeIndex([pd.Timestamp(when, tz="UTC")])
    return pd.DataFrame({"temp_air": [t], "temp_dew": [rh_dew], "relative_humidity": [50.0], "pressure": [1010.0],
                         "wind_speed": [wind], "ghi": [ghi], "dni": [dni]}, index=idx)


def test_wbgt_sun_exceeds_shade_and_shade_close_to_psychrometric_estimate():
    df = _frame(35.0, 20.0, 900.0, 800.0)
    sun = heat.wbgt_liljegren(df, 40.0, -3.7, sun=True)["wbgt"].iloc[0]
    shade = heat.wbgt_liljegren(df, 40.0, -3.7, sun=False)["wbgt"].iloc[0]
    assert sun > shade + 2.0
    assert 26.0 < shade < 31.0   # 35 C, dew point 20 C


def test_indoor_offset_raises_shade_wbgt():
    df = _frame(30.0, 18.0, 0.0, 0.0)
    base = heat.wbgt_liljegren(df, 50.0, 2.0, sun=False)["wbgt"].iloc[0]
    warm = heat.wbgt_liljegren(df, 50.0, 2.0, sun=False, indoor_offset=3.0)["wbgt"].iloc[0]
    assert warm > base + 0.5


def test_solar_delta_mrt_zero_at_night_and_plausible_at_noon():
    idx = pd.DatetimeIndex([pd.Timestamp("2022-07-13 01:00", tz="UTC"), pd.Timestamp("2022-07-13 13:00", tz="UTC")])
    d = heat.solar_delta_mrt(idx, 40.0, -3.7, np.array([0.0, 800.0]))
    assert d[0] == 0.0
    assert 20.0 < d[1] < 45.0


def test_utci_reference_point():
    # UTCI equals air temperature for the reference condition (Tmrt = Ta, 0.5 m/s at 10 m, RH 50 %, Ta 20 C) to within ~1 K
    assert float(np.ravel(heat.utci(20.0, 20.0, 0.5, 50.0))[0]) == pytest.approx(20.0, abs=1.5)
