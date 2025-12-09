from __future__ import annotations

from dash import Dash

from . import (
    ai_callbacks,
    availability_callbacks,
    des_callbacks,
    export_callbacks,
    geometry_callbacks,
    optimizer_callbacks,
    pipeline_callbacks,
    site_plan_callbacks,
    sizing_callbacks,
    user_callbacks,
)


def register_callbacks(app: Dash) -> None:
    user_callbacks.register(app)
    sizing_callbacks.register(app)
    site_plan_callbacks.register(app)
    optimizer_callbacks.register(app)
    availability_callbacks.register(app)
    des_callbacks.register(app)
    export_callbacks.register(app)
    ai_callbacks.register(app)
    geometry_callbacks.register(app)
    pipeline_callbacks.register(app)
