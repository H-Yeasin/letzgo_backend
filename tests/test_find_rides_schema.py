"""
FindRideRequest radius-resolution tests.

The /rides/find endpoint accepts a legacy single `radius` plus optional
split `pickup_radius` / `destination_radius` fields. These tests pin the
fallback rules: split fields win when present, otherwise `radius` applies
to both distances (old-client behavior unchanged).
"""

import pytest
from pydantic import ValidationError

from app.schemas.ride import FindRideRequest


def make_request(**overrides):
    data = {
        "current_lat": 23.8103,
        "current_lng": 90.4125,
        "destination_lat": 23.7721,
        "destination_lng": 90.4152,
    }
    data.update(overrides)
    return FindRideRequest(**data)


class TestFindRideRequestRadii:
    def test_legacy_radius_applies_to_both(self):
        req = make_request(radius=500)
        assert req.effective_pickup_radius == 500
        assert req.effective_destination_radius == 500

    def test_split_radii_override_legacy_radius(self):
        req = make_request(radius=500, pickup_radius=5000, destination_radius=1000)
        assert req.effective_pickup_radius == 5000
        assert req.effective_destination_radius == 1000

    def test_partial_split_falls_back_to_legacy_radius(self):
        req = make_request(radius=300, pickup_radius=5000)
        assert req.effective_pickup_radius == 5000
        assert req.effective_destination_radius == 300

    def test_defaults_when_no_radius_sent(self):
        req = make_request()
        assert req.effective_pickup_radius == 500.0
        assert req.effective_destination_radius == 500.0

    def test_pickup_radius_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            make_request(pickup_radius=50)

    def test_destination_radius_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            make_request(destination_radius=20000)
