"""The committed dashboard data snapshot (dashboard/data.json, D71) must match the repo's sites and config.

CI renders the page from data.json without the pipeline, so a branch that adds a site or changes
config but doesn't rebuild the snapshot would publish stale data. These checks fail instead.
Fix: run scripts/build_dashboard.py (needs the pipeline inputs) and commit data.json.
"""

import json

import pytest

from climate_risk.config import ROOT, load_sites, settings, shifts

DATA = ROOT / "dashboard" / "data.json"


@pytest.fixture(scope="module")
def data():
    if not DATA.exists():
        pytest.fail("dashboard/data.json is missing: run scripts/build_dashboard.py and commit it")
    return json.loads(DATA.read_text())


def test_sites_match(data):
    assert sorted(s["id"] for s in data["sites"]) == sorted(s.site_id for s in load_sites())


def test_every_site_has_data_blocks(data):
    ids = {s["id"] for s in data["sites"]}
    for block in ("kpi", "tmy", "hourly"):
        assert set(data[block]) == ids, block


def test_config_matches(data):
    cfg, meta = settings(), data["meta"]
    fc = cfg["future"]
    assert meta["models"] == list(fc["models"])
    assert meta["scenarios"] == fc["scenarios"]
    assert meta["periods"] == list(fc["periods"])
    assert meta["operating_hours"] == cfg["operating_hours"]
    assert meta["risk_bands_days"] == cfg["heat"]["risk_bands_days"]
    assert meta["map_breaks_days"] == cfg["heat"]["map_breaks_days"]
    assert meta["wbgt_ref"] == cfg["heat"]["wbgt_reference_c"]
    assert meta["shifts"] == {k: list(v) for k, v in shifts().items()}
