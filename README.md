# Floral V1 – Integrated CHP / PV / BESS Planning Suite

Floral V1 is an end-to-end reliability planner for hybrid energy campuses. It sizes CHP fleets, ingests site context, lays out assets, optimizes PV/BESS integration, verifies analytical availability targets, runs a SimPy-based DES, and produces AI-style diagnostics through the Floragen AI tab. The project bundles both a modern Dash web app and CLI tools so that users can explore scenarios interactively or automate them through scripts.

```
UserRequest → Sizing → SiteModel/Placement → Hybrid Optimization → Analytical Availability → DES → AI Diagnostics / Export
```

## Repository Structure

- `floral_v1/core/` – Canonical dataclasses plus real logic for sizing, site planning, placement, optimization, analytical availability, DES, and visualization helpers.
- `floral_v1/app/` – Dash application (layout, callbacks, state serialization) that orchestrates each pipeline stage with dcc.Store state.
- `floral_v1/ai_engine.py` – Backend AI engine interface used by the Floragen AI tab and CLI diagnostics. Ships with a stub that can be replaced with a real LLM call.
- `floral_v1/scenarios.py` – Scenario serialization utilities (save/load JSON snapshots of every pipeline artifact).
- `floral_v1/scripts/smoke_pipeline.py` – Reference pipeline runner with named scenarios (demo/small/large) and helper builders.
- `floral_v1/cli_smoke.py` / `floral_v1/cli_dash.py` – Console entrypoints installed as `floral-smoke` and `floral-dash`.
- `floral_v1/tests/` – Pytest suite covering sizing, optimization, DES outputs, and SimulationResult metadata.
- `floral_v1/infra/docker/` – Dockerfile and docker-compose configuration for containerized Dash deployments.
- Legacy folders (`DESModel/`, `digital_twin_ryan/`, `siteplan-visuals/`, `AvailabilityDesigner.py`) remain for historical reference only; all runtime code lives under `floral_v1/`.

## Installation (from scratch)

1. Clone this repository (standard `git clone` steps).
2. Create a Python virtual environment:
   - macOS/Linux: `python3 -m venv .venv`
   - Windows (PowerShell): `py -3 -m venv .venv`
3. Activate the environment:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
4. Upgrade pip and install Floral V1 in editable mode: `pip install --upgrade pip && pip install -e .`
5. (Optional) Install development extras, such as pytest, via `pip install -r requirements.txt`.
6. Optional AI engine configuration:
   - `AI_ENGINE_API_KEY`: leave unset to use the built-in stub; set to a valid key when hooking up a real LLM.
   - `AI_ENGINE_MODEL`: optional override (defaults to a sensible value such as `gpt-4o-mini` in the stub).

## Running the Dash App

1. Activate the virtual environment.
2. Launch the server: `floral-dash`
3. Open http://127.0.0.1:8050 in your browser.

### Dashboard Tour & Workflow

- **Inputs** – Enter project name, site coordinates, target load, availability target, genset size, PV land, load profile (CSV or newline), and objective weights. Save the request and click **Size Gensets** to populate the first stage.
- **Site & Placement** – Click **Build Site & Placement** to generate the footprint, heightmap metadata, and placement coordinates. Inspect summaries and the placement map.
- **Optimization** – After sizing and site steps, click **Optimize Hybrid** to run the migrated optimization engine (PV/BESS). KPI tiles and charts summarize the hybrid design.
- **Availability & DES** – Press **Verify Availability** (analytical k-of-n). Configure **Simulation Hours** and **DES Mode** (stochastic / scheduled / hybrid) before clicking **Run DES**. KPI cards, a timeline, and an energy-split pie render instantly.
- **Export** – Save/load scenarios and trigger **Export Blender Bundle** for 3D visualization packages.
- **Floragen AI** – Shows a scenario-aware diagnostic narrative after DES. Use **Ask Floragen** to pose follow-up questions. (Uses the stub AI engine unless `AI_ENGINE_API_KEY` is configured.)

## Running the Pipeline via CLI

- `floral-smoke demo`
- `floral-smoke small`
- `floral-smoke large`

Each command executes the complete pipeline (sizing → site → placement → optimization → availability → DES) using prebuilt reference scenarios and prints summary metrics for each step. Sample usage:

- Save a scenario (JSON stored under `exports/scenarios/`): `floral-smoke demo --save exports/scenarios/my_demo.json`
- Reload a historical scenario without recomputation: `floral-smoke --load exports/scenarios/my_demo.json`
- Request the AI diagnostic from the CLI: `floral-smoke demo --ai-diagnostic`

These commands rely on the scenario helpers inside `floral_v1/scenarios.py`.

## Tests

Run `pytest floral_v1/tests` (from an activated env). The suite verifies core invariants such as:
- Sizing outputs: installed vs required units, availability bounds.
- Optimizer: PV/BESS capacities and non-null hybrid structures.
- DES: SimulationResult metrics (availability range, outage hours, energy splits).

## Docker Usage

Containerized runs use the files under `floral_v1/infra/docker/`:
- `docker build -t floral-v1 -f floral_v1/infra/docker/Dockerfile .`
- `docker run -p 8050:8050 floral-v1`

Or via docker-compose:
- `cd floral_v1/infra/docker && docker compose up --build`

Expose environment variables (e.g., `AI_ENGINE_API_KEY`, `AI_ENGINE_MODEL`) through `docker-compose.yml` to enable a real AI backend inside the container.

## Customizing & Extending

- **Visualization & Styling** – Adjust Plotly themes in `floral_v1/core/visualization/plots.py` and Dash layout semantics in `floral_v1/app/layout.py`.
- **AI Engine** – Plug a real LLM call into `generate_ai_response` inside `floral_v1/ai_engine.py`. Read credentials from env vars to swap the stub for production use.
- **Optimizer & Availability** – Tweak optimizer logic under `floral_v1/core/optimizer/` and analytical routines under `floral_v1/core/availability/`.
- **New Reference Scenarios** – Extend `floral_v1/scripts/smoke_pipeline.py` with additional builders and register them in `cli_smoke.py` for immediate CLI exposure.

## Quick Command Reference

- Start Dash UI: `floral-dash`
- Run smoke scenarios: `floral-smoke demo|small|large`
- Save scenario: `floral-smoke demo --save exports/scenarios/demo.json`
- Load scenario: `floral-smoke --load exports/scenarios/demo.json`
- Run tests: `pytest floral_v1/tests`
- Build Docker image: `docker build -t floral-v1 -f floral_v1/infra/docker/Dockerfile .`

With these steps, a new user can clone the repo, set up the environment, run tests, drive the full workflow via UI or CLI, inspect DES diagnostics, and optionally pipe scenarios through Floragen AI. For deeper customization, the core modules under `floral_v1/` are organized so you can iterate on sizing, site heuristics, optimization, availability, DES, and AI diagnostics independently.
