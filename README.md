# Floral-V1

## Dash Application

Activate the virtual environment and launch the interactive planner with:

```bash
source .venv/bin/activate
python -m floral_v1.app.app
```

This starts the Dash UI, which walks through the full pipeline:
`size_gensets -> build_site_model -> place_assets -> optimize_hybrid -> verify_availability -> run_des -> export`.
