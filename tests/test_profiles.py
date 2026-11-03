"""D59 worker profiles: effective references and the metric names every pipeline stage shares."""
import pytest

from climate_risk.annual import wbgt_metric_names, wbgt_profiles
from climate_risk.config import settings


def test_profiles_from_settings():
    p = wbgt_profiles(settings()["heat"])
    assert p[""] == (26.0, 28.0)            # default = moderate work, not acclimatised headline (D58)
    assert p["_ppe"] == (24.0, 26.0)        # coveralls + hood lower the reference by the clothing adjustment
    assert p["_light"][0] > p[""][0] > p["_heavy"][0]


def test_default_profile_must_match_headline():
    hc = {"wbgt_reference_c": 26.0, "wbgt_reference_acclimatised_c": 28.0, "default_worker_profile": "moderate",
          "worker_profiles": {"moderate": {"reference_c": 27.0, "reference_acclimatised_c": 28.0}}}
    with pytest.raises(ValueError):
        wbgt_profiles(hc)


def test_metric_names_cover_profiles_exposures_and_shifts():
    names = wbgt_metric_names(settings()["heat"])
    assert len(names) == len(set(names))
    for n in ("op_days_wbgt_shade_gt_ref", "op_hours_wbgt_sun_gt_ref_acc", "op_hours_wbgt_in4_gt_ref_ppe_late",
              "op_days_wbgt_in2_gt_ref_heavy", "op_hours_wbgt_shade_gt_ref_light_acc"):
        assert n in names
