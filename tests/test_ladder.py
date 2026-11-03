"""Dry-bulb ladder (D66): counts against brute force, internal consistency, agreement with annual_summary."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from climate_risk.config import settings
from climate_risk.heatwave import run_lengths
from climate_risk.ladder import ensemble, ladder, rung_names, rungs

ROOT = Path(__file__).resolve().parents[1]


def synthetic(seed=1, tz="Europe/Madrid"):
    idx = pd.date_range("2021-01-01 00:00", "2022-01-01 00:00", freq="h", tz="UTC")[1:]   # hour-ending, one year
    rng = np.random.default_rng(seed)
    loc = (idx - pd.Timedelta(hours=1)).tz_convert(tz)
    doy, hr = loc.dayofyear.to_numpy(), loc.hour.to_numpy()
    t = 18 + 12 * np.sin((doy - 110) / 365 * 2 * np.pi) + 6 * np.sin((hr - 9) / 24 * 2 * np.pi) + rng.normal(0, 2, len(idx))
    return pd.DataFrame({"temp_air": t}, index=idx), loc


def test_counts_match_brute_force():
    cfg = settings()
    df, loc = synthetic()
    lad = ladder(df, "Europe/Madrid", cfg)
    ys = lad.year.unique()
    lad = lad[lad.year == 2021].set_index("metric")
    t = df["temp_air"].to_numpy()
    m = loc.year == 2021
    op = (loc.hour >= 6) & (loc.hour < 22)
    for r in (25.0, 30.0, 32.5, 35.0):
        c = f"{r:g}"
        assert lad.loc["hours", c] == int((t[m] > r).sum())
        assert lad.loc["op_hours", c] == int((t[m & op] > r).sum())
        assert lad.loc["op_hours", c] == lad.loc["early", c] + lad.loc["late", c]
        assert lad.loc["hours", c] == lad.loc["early", c] + lad.loc["late", c] + lad.loc["night", c]
        dmax = pd.Series(t[m]).groupby(loc.normalize()[m]).max()
        assert lad.loc["days", c] == int((dmax > r).sum())
        runs = run_lengths((dmax > r).to_numpy())
        assert lad.loc["longest", c] == (runs.max() if len(runs) else 0)
        assert lad.loc["op_dh", c] == pytest.approx(float(np.clip(t[m & op] - r, 0, None).sum()), abs=0.1)
    assert list(ys) == [2021]


def test_monotonic_in_the_rung():
    cfg = settings()
    df, _ = synthetic(seed=3)
    lad = ladder(df, "Europe/Madrid", cfg).set_index("metric")[rung_names(cfg)]
    for metric in ("hours", "op_hours", "days", "op_days", "longest", "dh"):
        assert (np.diff(lad.loc[metric].to_numpy(float)) <= 1e-9).all(), metric


def test_ensemble_stays_monotonic():
    cfg = settings()
    rows = []
    for k, seed in enumerate(range(5)):
        df, _ = synthetic(seed=seed)
        rows.append(ladder(df, "Europe/Madrid", cfg).assign(site_id="X", year=2015 + k))
    hist = pd.concat(rows)
    fut = pd.concat([h.assign(model=m, scenario="ssp245", period="2050") for m, h in (("a", hist), ("b", hist))])
    ens = ensemble(hist, fut, cfg)
    for _, row in ens[ens.metric == "op_hours"].iterrows():
        v = row[rung_names(cfg)].to_numpy(float)
        assert (np.diff(v) <= 1e-9).all()


@pytest.mark.skipif(not (ROOT / "outputs/phase1/dbt_ladder.parquet").exists(), reason="pipeline output not built")
def test_agrees_with_annual_summary():
    """Rungs that coincide with existing metrics give the same counts (30 C, and the placeholder process limits)."""
    lad = pd.read_parquet(ROOT / "outputs/phase1/dbt_ladder.parquet")
    ann = pd.read_csv(ROOT / "outputs/phase1/annual_summary.csv")
    h = lad[lad.metric == "hours"].merge(ann, on=["site_id", "year"])
    assert len(h) == len(ann)
    assert (h["30"] == h["hours_t_gt30"]).all()
    assert (h["35"] == h["proc_hours_paint_application_max_temp"]).all()
    assert (h["32"] == h["proc_hours_composite_room_cooling"]).all()
    d = lad[lad.metric == "days"].merge(ann, on=["site_id", "year"])
    assert (d["30"] == d["days_tmax_gt30"]).all() and (d["35"] == d["days_tmax_gt35"]).all()
    assert list(rungs(settings()))[0] == 16.0
