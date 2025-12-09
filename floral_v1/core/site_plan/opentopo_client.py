from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import requests
from PIL import Image

from floral_v1.core.models import Heightmap

SITEPLAN_ROOT = Path(__file__).resolve().parents[3] / "siteplan-visuals"
FALLBACK_HEIGHTMAP = SITEPLAN_ROOT / "site_heightmap.png"


def _chunk(seq: Iterable[str], size: int) -> Iterable[List[str]]:
    seq_list = list(seq)
    for idx in range(0, len(seq_list), size):
        yield seq_list[idx : idx + size]


def _fetch_from_api(latitudes: List[float], longitudes: List[float]) -> List[float]:
    dataset = os.getenv("OPENTOPO_DATASET", "srtm90m")
    base_url = os.getenv("OPENTOPO_BASE_URL", "https://api.opentopodata.org/v1")
    url = f"{base_url.rstrip('/')}/{dataset}"
    coords = [f"{la:.6f},{lo:.6f}" for la in latitudes for lo in longitudes]
    results: List[float] = []
    session = requests.Session()
    for chunk in _chunk(coords, 90):
        response = session.get(url, params={"locations": "|".join(chunk)}, timeout=10)
        response.raise_for_status()
        data = response.json()
        for entry in data.get("results", []):
            results.append(entry.get("elevation", 0.0))
    return results


def _fallback_heightmap() -> Heightmap:
    if FALLBACK_HEIGHTMAP.exists():
        img = Image.open(FALLBACK_HEIGHTMAP).convert("L")
        arr = np.array(img, dtype=float)
        grid = arr.tolist()
        return Heightmap(grid=grid, resolution_m=1.0, source="siteplan-local")
    grid = [[0.0 for _ in range(8)] for _ in range(8)]
    return Heightmap(grid=grid, resolution_m=50.0, source="synthetic")


def fetch_heightmap(bounds: Dict[str, float]) -> Heightmap:
    lat = float(bounds.get("lat", 0.0))
    lon = float(bounds.get("lon", 0.0))
    size_km = max(bounds.get("size_km", 1.0), 0.1)
    samples = int(max(bounds.get("samples", 12), 4))

    lat_span = size_km / 111.0
    lon_span = size_km / (111.0 * max(math.cos(math.radians(lat)), 1e-3))
    half_lat = lat_span / 2.0
    half_lon = lon_span / 2.0
    latitudes = list(np.linspace(lat - half_lat, lat + half_lat, samples))
    longitudes = list(np.linspace(lon - half_lon, lon + half_lon, samples))

    try:
        elevations = _fetch_from_api(latitudes, longitudes)
        if not elevations:
            raise ValueError("empty elevation response")
        grid = [
            elevations[row * len(longitudes) : (row + 1) * len(longitudes)]
            for row in range(len(latitudes))
        ]
        resolution_m = size_km * 1000 / max(samples - 1, 1)
        return Heightmap(grid=grid, resolution_m=resolution_m, source="opentopodata")
    except Exception:
        return _fallback_heightmap()
