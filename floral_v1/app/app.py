from __future__ import annotations

from dash import Dash

from floral_v1.app.callbacks import register_callbacks
from floral_v1.app.layout import get_layout


def create_app() -> Dash:
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.layout = get_layout()
    register_callbacks(app)
    return app


app = create_app()
server = app.server


def main() -> None:
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
