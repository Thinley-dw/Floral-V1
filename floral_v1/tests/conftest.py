from __future__ import annotations

import pytest

from floral_v1.core.models import SiteContext, UserRequest


@pytest.fixture
def demo_request() -> UserRequest:
    site = SiteContext(name="Test Campus", latitude=1.35, longitude=103.82)
    load_profile = [45000.0] * 24
    return UserRequest(
        project_name="demo",
        target_load_mw=45.0,
        availability_target=0.999,
        site=site,
        load_profile_kw=load_profile,
        genset_size_mw=2.5,
        pv_land_m2=20000.0,
        objectives={"lcoe": 1.0},
    )
