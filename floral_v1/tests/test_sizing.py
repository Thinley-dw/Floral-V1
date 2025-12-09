from __future__ import annotations

from floral_v1.core.sizing.engine import size_gensets


def test_size_gensets_returns_valid_design(demo_request):
    design = size_gensets(demo_request)
    assert design.installed_units >= design.required_units
    assert design.per_unit_mw > 0
    assert 0 < design.expected_availability <= 1.0
