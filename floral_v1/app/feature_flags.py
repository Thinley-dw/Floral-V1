from __future__ import annotations

try:
    import dash_leaflet as _dash_leaflet
except ModuleNotFoundError:
    _dash_leaflet = None

HAS_DASH_LEAFLET = _dash_leaflet is not None
DASH_LEAFLET = _dash_leaflet
