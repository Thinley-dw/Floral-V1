from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image

from floral_v1.core.models import HybridDesign, PlacementPlan, SiteModel

BLENDER_SCRIPT = """#!/usr/bin/env python3
\"\"\"Minimal placeholder Blender script that reads site_map.json.\"\"\"
import json
from pathlib import Path

def main():
    data_path = Path(__file__).resolve().parent / "site_map.json"
    data = json.loads(data_path.read_text())
    print("Loaded site map for", data["site"]["name"])
    print("Assets:", len(data["assets"]))

if __name__ == "__main__":
    main()
"""


def build_blender_package(site: SiteModel, design: HybridDesign, output_dir: str) -> str:
    """
    Export a Blender-friendly bundle describing the site layout, assets, and heightmap.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    placement = design.placement
    site_payload: Dict[str, Any] = {
        "name": site.site.name,
        "latitude": site.site.latitude,
        "longitude": site.site.longitude,
        "footprint_acres": site.footprint_acres,
        "buildable_acres": site.buildable_area_acres,
        "metadata": site.metadata,
    }
    payload = {
        "site": site_payload,
        "assets": placement.asset_locations,
        "constraints": placement.constraints,
        "design": {
            "pv_capacity_kw": design.pv_capacity_kw,
            "bess_energy_mwh": design.bess_energy_mwh,
            "bess_power_mw": design.bess_power_mw,
        },
    }
    site_map_path = out_dir / "site_map.json"
    site_map_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if site.heightmap:
        array = np.array(site.heightmap.grid, dtype=float)
        if array.size == 0:
            array = np.zeros((8, 8))
        norm = array - array.min()
        if norm.max() > 0:
            norm = norm / norm.max()
        img = Image.fromarray((norm * 255).astype(np.uint8))
        img.save(out_dir / "heightmap.png")

    script_path = out_dir / "blender_render.py"
    script_path.write_text(BLENDER_SCRIPT, encoding="utf-8")
    return str(site_map_path)


def export_site_to_blender(placement: PlacementPlan, output_dir: str) -> str:
    """
    Backwards-compatible helper for legacy callers.
    """
    dummy_design = HybridDesign(
        gensets=None,  # type: ignore[arg-type]
        site=placement.site,
        placement=placement,
        pv_capacity_kw=0.0,
        bess_energy_mwh=0.0,
        bess_power_mw=0.0,
        load_profile_kw=[],
        metadata={},
    )
    return build_blender_package(placement.site, dummy_design, output_dir)
