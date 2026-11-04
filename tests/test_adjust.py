"""D61 baseline adjustment: years move to the reference climate by the models' warming rate."""
import numpy as np
import pandas as pd

from climate_risk.adjust import adjust_record, smooth_months
from climate_risk.weather import saturation_vapour_pressure


def _record(years=(2000, 2020)):
    idx = pd.date_range(f"{years[0]}-01-01 01:00", f"{years[1] + 1}-01-01 00:00", freq="h", tz="UTC")
    hour = (idx - pd.Timedelta(hours=1)).hour.to_numpy()
    t = 15 + 5 * np.sin((hour - 9) / 24 * 2 * np.pi)
    return pd.DataFrame({"temp_air": t, "temp_dew": t - 8, "relative_humidity": 50.0, "pressure": 1010.0,
                         "wind_speed": 2.0, "wind_direction": 180.0, "ghi": 100.0, "dni": 50.0, "dhi": 50.0,
                         "lw_down": 330.0}, index=idx)


def _rates(tmax=0.04, tmin=0.02, huss=0.0):
    return pd.DataFrame({"month": range(1, 13), "tasmax": tmax, "tasmin": tmin, "huss": huss})


def test_shift_scales_with_years_to_reference():
    rec = _record()
    out = adjust_record(rec, _rates(), 2020)
    day = lambda d: (out["temp_air"] - rec["temp_air"])[(rec.index - pd.Timedelta(hours=1)).normalize() == pd.Timestamp(d, tz="UTC")]
    # 1 July 2000 is ~20 years before mid-2020: Tmax +0.8, Tmin +0.4
    d2000 = day("2000-07-01")
    assert abs(d2000.max() - 0.8) < 0.02 and abs(d2000.min() - 0.4) < 0.02
    # mid-2020 is the reference: no change
    assert day("2020-07-01").abs().max() < 0.01
    # radiation and wind untouched
    assert (out[["ghi", "dni", "wind_speed"]] == rec[["ghi", "dni", "wind_speed"]]).all().all()


def test_later_years_are_cooled():
    rec = _record((2024, 2025))
    out = adjust_record(rec, _rates(), 2020)
    assert (out["temp_air"] - rec["temp_air"]).max() < 0


def test_humidity_scales_vapour_pressure():
    rec = _record()
    out = adjust_record(rec, _rates(0.0, 0.0, huss=np.log(1.01)), 2020)   # +1 % specific humidity per year
    sel = (rec.index - pd.Timedelta(hours=1)).normalize() == pd.Timestamp("2000-07-01", tz="UTC")
    ratio = saturation_vapour_pressure(out["temp_dew"][sel].to_numpy()) / saturation_vapour_pressure(rec["temp_dew"][sel].to_numpy())
    assert np.allclose(ratio, 1.01 ** 20, rtol=0.01)
    assert (out["relative_humidity"] <= 100.0).all()


def test_smooth_months_keeps_the_annual_mean():
    v = np.arange(12, dtype=float)
    assert np.isclose(smooth_months(v).mean(), v.mean())
    assert np.isclose(smooth_months(v)[5], 0.25 * 4 + 0.5 * 5 + 0.25 * 6)


def test_extreme_year_falls_back_to_dry_heat_where_humid_heat_is_negligible():
    from climate_risk.annual import select_extreme_year
    humid = pd.DataFrame({"op_wbgt_shade_degree_hours_gt_base": [120.0, 300.0, 50.0], "hours_t_gt30": [400, 100, 900],
                          "temp_max": [40.0, 38.0, 42.0], "op_hours_wbgt_shade_gt_ref": [0, 0, 0]}, index=[2003, 2015, 2022])
    assert select_extreme_year(humid, 50.0)[0] == 2015          # humid heat decides (D42 ranking)
    north = humid.assign(op_wbgt_shade_degree_hours_gt_base=[1.0, 9.0, 3.0])
    year, rule = select_extreme_year(north, 50.0)
    assert year == 2022 and rule.startswith("dry heat")         # a few humid hours don't decide


def test_hot_year_uses_the_lower_threshold():
    """D68: the hot year falls back to dry heat only below 20 WBGT degree-hours; Madrid-like sites (47) keep humid ranking."""
    from climate_risk.annual import select_reference_year
    from climate_risk.config import settings
    thr = settings()["hot_year"]["hot_min_wbgt_degree_hours"]
    assert thr == 20.0
    madrid = pd.DataFrame({"op_wbgt_shade_degree_hours_gt_base": [47.0, 20.0], "hours_t_gt30": [800, 900],
                           "temp_max": [41.0, 42.0]}, index=[2022, 2025])
    assert select_reference_year(madrid, thr) == (2022, "humid heat (WBGT degree-hours)")
    hamburg = madrid.assign(op_wbgt_shade_degree_hours_gt_base=[9.1, 2.0], hours_t_gt30=[20, 39])
    assert select_reference_year(hamburg, thr)[0] == 2025
