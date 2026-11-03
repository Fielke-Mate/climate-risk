"""D60 heatwave length: run detection and the yearly metrics."""
import numpy as np
import pandas as pd

from climate_risk.annual import annual_summary
from climate_risk.config import settings
from climate_risk.heatwave import calendar_mask, daily_heatwave_metrics, heatwave_metric_names, run_lengths, spell_stats

CFG = {"heatwave": {"min_days": 3, "tmax_thresholds_c": [30, 35], "tropical_night_c": 20}}


def test_run_lengths_and_spells():
    m = [0, 1, 1, 0, 1, 1, 1, 1, 0, 1]
    assert list(run_lengths(m)) == [2, 4, 1]
    assert spell_stats(m, 3) == (1, 4, 4)          # one event of 4 days; longest run 4
    assert spell_stats([0, 0], 3) == (0, 0, 0)


def test_gap_in_record_ends_a_run():
    days = pd.to_datetime(["2022-07-01", "2022-07-02", "2022-07-04", "2022-07-05"])  # 3 July missing
    m = calendar_mask(pd.Series([31.0] * 4, index=days), 30.0)
    assert len(m) == 5 and list(run_lengths(m.to_numpy())) == [2, 2]


def test_daily_metrics_per_year():
    days = pd.date_range("2021-01-01", "2022-12-31", freq="D")
    tmax = pd.Series(20.0, index=days)
    tmax["2021-07-10":"2021-07-14"] = 31.0           # 5-day event above 30
    tmax["2022-08-01":"2022-08-02"] = 36.0           # 2 days above 35 (and 30): too short for an event
    tmax["2022-08-10":"2022-08-13"] = 32.0           # 4-day event above 30
    tmin = pd.Series(15.0, index=days)
    tmin["2022-08-10":"2022-08-12"] = 21.0
    hw = daily_heatwave_metrics(tmax, tmin, CFG)
    assert list(hw.columns) == heatwave_metric_names(CFG)
    assert hw.loc[2021, ["hw30_events", "hw30_days", "hw30_longest"]].tolist() == [1, 5, 5]
    assert hw.loc[2022, ["hw30_events", "hw30_days", "hw30_longest"]].tolist() == [1, 4, 4]
    assert hw.loc[2022, ["hw35_events", "hw35_days", "hw35_longest"]].tolist() == [0, 0, 2]
    assert hw.loc[2022, "tn20_longest"] == 3 and hw.loc[2021, "tn20_longest"] == 0


def test_annual_summary_has_heatwave_and_spell_columns():
    """A synthetic year with one 6-day hot humid spell: hot-day and heat-safety runs agree."""
    idx = pd.date_range("2022-01-01 01:00", "2023-01-01 00:00", freq="h", tz="UTC")
    hour = (idx - pd.Timedelta(hours=1)).hour.to_numpy()
    t = 15 + 5 * np.sin((hour - 9) / 24 * 2 * np.pi)
    hot = (idx > pd.Timestamp("2022-07-10", tz="Europe/Paris")) & (idx <= pd.Timestamp("2022-07-16", tz="Europe/Paris"))
    t = np.where(hot, t + 20, t)                        # ~35-40 C afternoons for 6 days
    df = pd.DataFrame({"temp_air": t, "temp_dew": np.where(hot, 22.0, 8.0), "pressure": 1010.0,
                       "wind_speed": 1.5, "wind_direction": 180.0, "ghi": 0.0, "dni": 0.0, "dhi": 0.0,
                       "lw_down": 350.0}, index=idx)
    df["relative_humidity"] = 50.0
    s = annual_summary(df, 43.6, 1.4, "Europe/Paris", settings()).loc[2022]
    assert s["hw30_events"] == 1 and s["hw30_longest"] == 6
    assert s["op_longest_wbgt_shade_gt_ref"] == 6 and s["op_spells_wbgt_shade_gt_ref"] == 1
