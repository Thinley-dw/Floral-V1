# Floral-V1

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Smoke Scenarios

```bash
floral-smoke demo   # default campus
floral-smoke small  # ~3 MW reference site
floral-smoke large  # ~10 MW reference site
```

Each command runs the full pipeline (`size_gensets -> build_site_model -> place_assets -> optimize_hybrid -> verify_availability -> run_des -> export`) and prints a concise summary.

To capture a scenario snapshot:

```bash
floral-smoke demo --save exports/scenarios/demo.json
```

To replay an existing scenario without rerunning the pipeline:

```bash
floral-smoke --load exports/scenarios/demo.json
```

The Dash Export tab also exposes **Save Scenario** and **Load Scenario** controls that write/read JSON files under `exports/scenarios/`.

### Dash UI

```bash
floral-dash
```

Navigate to http://127.0.0.1:8050 to drive the workflow interactively.

### Floragen AI Diagnostics

- The Dash app now includes a **Floragen AI** tab that summarizes the current scenario and DES results using the internal AI engine stub (`floral_v1/ai_engine.py`).
- After running DES, the tab automatically shows a diagnostic narrative and lets you ask follow-up questions via "Ask Floragen".
- Developers can plug in a real LLM API by updating `generate_ai_response` to call their provider and wiring credentials through environment variables.
- From the CLI you can append `--ai-diagnostic` (e.g. `floral-smoke demo --ai-diagnostic`) to print the same narrative after a smoke scenario.

### Tests

```bash
pytest floral_v1/tests
```

## Docker

Build and run the Dash UI inside a container:

```bash
docker build -t floral-v1 -f floral_v1/infra/docker/Dockerfile .
docker run -p 8050:8050 floral-v1
```

Or use docker-compose:

```bash
cd floral_v1/infra/docker
docker compose up --build
```

## Legacy Folders

`DESModel/`, `digital_twin_ryan/`, and `siteplan-visuals/` remain in the repository for reference, but the production code path runs entirely inside `floral_v1/`.
