import random
from enum import Enum

import numpy as np
import simpy

from floral_v1.core.des import des_core
from floral_v1.core.des.des_core import InteractivePowerSystem, build_frame

# Global shared state
sim_env = None
sim_ps = None
current_hour = 0

class SimMode(str, Enum):
    RANDOM = "random"          # Pure stochastic (current behaviour)
    HYBRID = "hybrid"          # Stochastic + scheduled overlay (future)
    SCHEDULE_ONLY = "schedule" # Schedule-only / deterministic (future)

# Current simulation mode (default to RANDOM for backward compatibility)
sim_mode: SimMode = SimMode.RANDOM

# Global schedule definition pushed from the frontend when using
# HYBRID or SCHEDULE_ONLY modes. This is a list of dict-like events, e.g.:
# {
#   "asset_type": "chp" | "pv" | "bess",
#   "asset_index": 1,
#   "start_hour": 100,
#   "duration_hours": 24,
#   "event_type": "planned_maintenance" | "forced_outage"
# }
sim_schedule = []

def reset_simulation(seed=None, mode: str = "random", schedule=None):
    """Reset the DES and return the first frame.

    Args:
        seed: Optional random seed for reproducibility.
        mode: Simulation mode string: "random", "hybrid", or "schedule".
        schedule: Optional list of scheduled maintenance / outage events coming
                  from the frontend. Each event is expected to be a dict with
                  keys like:
                  {
                      "asset_type": "chp" | "pv" | "bess",
                      "asset_index": int,
                      "start_hour": int,
                      "duration_hours": int,
                      "event_type": "planned_maintenance" | "forced_outage"
                  }
    """

    global sim_env, sim_ps, current_hour, sim_mode, sim_schedule

    # Configure simulation mode (fallback to RANDOM for any invalid value)
    try:
        sim_mode = SimMode(mode)
    except ValueError:
        sim_mode = SimMode.RANDOM

    # Normalise the schedule input into a plain list stored globally
    if schedule is None:
        sim_schedule = []
    else:
        if isinstance(schedule, list):
            # shallow copy to decouple from FastAPI / caller object
            sim_schedule = list(schedule)
        else:
            # if something unexpected is passed, fall back to an empty schedule
            sim_schedule = []

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    sim_env = simpy.Environment()
    sim_ps = InteractivePowerSystem(sim_env)

    # Expose mode and schedule on the power system instance so that
    # the DES internals can choose how to apply them without having
    # to know about this module-level plumbing.
    setattr(sim_ps, "sim_mode", sim_mode.value)
    setattr(sim_ps, "sim_schedule", sim_schedule)

    current_hour = 0

    # Run the first hour safely
    try:
        sim_env.run(until=1)
        frame = build_frame(sim_ps, 0)
    except Exception as e:
        frame = {
            "hour": 0,
            "error": f"DES initialization failed: {str(e)}",
            "chp": [],
            "pv": [],
            "bess": {},
            "switchboards": {},
            "gas": {},
            "datacenter": {}
        }

    return {
        "status": "ok",
        "hour": 0,
        "mode": sim_mode.value,
        "frame": frame
    }


def run_one_step():
    global sim_env, sim_ps, current_hour, sim_mode

    if sim_env is None or sim_ps is None:
        return {"error": "Simulation not initialized", "mode": sim_mode.value}

    try:
        current_hour += 1
        sim_env.run(until=current_hour + 1)

        try:
            frame = build_frame(sim_ps, current_hour)
        except Exception as frame_err:
            frame = {
                "hour": current_hour,
                "error": f"Frame build failed: {str(frame_err)}",
                "chp": [],
                "pv": [],
                "bess": {},
                "switchboards": {},
                "gas": {},
                "datacenter": {}
            }

        return {
            "status": "ok",
            "hour": current_hour,
            "mode": sim_mode.value,
            "frame": frame
        }

    except Exception as sim_err:
        return {
            "status": "error",
            "hour": current_hour,
            "mode": sim_mode.value,
            "frame": {
                "hour": current_hour,
                "error": f"DES runtime exception: {str(sim_err)}",
                "chp": [],
                "pv": [],
                "bess": {},
                "switchboards": {},
                "gas": {},
                "datacenter": {}
            }
        }

def fast_forward(hours: int):
    global sim_env, sim_ps, current_hour, sim_mode

    if sim_env is None or sim_ps is None:
        return {"error": "Simulation not initialized", "mode": sim_mode.value}

    try:
        hours = int(hours)
        if hours <= 0:
            frame = build_frame(sim_ps, current_hour)
            history = get_history()
            return {
                "status": "ok",
                "hour": current_hour,
                "mode": sim_mode.value,
                "frame": frame,
                "history": history,
            }

        last_frame = None

        for _ in range(hours):
            step_result = run_one_step()
            if step_result.get("status") != "ok":
                return {
                    "status": step_result.get("status", "error"),
                    "hour": step_result.get("hour", current_hour),
                    "mode": sim_mode.value,
                    "frame": step_result.get("frame"),
                    "history": get_history(),
                }
            last_frame = step_result["frame"]

        frame = last_frame if last_frame is not None else build_frame(sim_ps, current_hour)
        history = get_history()

        return {
            "status": "ok",
            "hour": current_hour,
            "mode": sim_mode.value,
            "frame": frame,
            "history": history,
        }

    except Exception as sim_err:
        return {
            "status": "error",
            "hour": current_hour,
            "mode": sim_mode.value,
            "frame": {
                "hour": current_hour,
                "error": f"DES fast-forward exception: {str(sim_err)}",
                "chp": [],
                "pv": [],
                "bess": {},
                "switchboards": {},
                "gas": {},
                "datacenter": {}
            }
        }

def get_history():
    global sim_ps
    if sim_ps is None or not getattr(sim_ps, "history", None):
        return []

    frames = []
    n = len(sim_ps.history)

    for h in range(n):
        try:
            frame = build_frame(sim_ps, h)
        except Exception as frame_err:
            frame = {
                "hour": h,
                "error": f"History frame build failed: {str(frame_err)}",
                "chp": [],
                "pv": [],
                "bess": {},
                "switchboards": {},
                "gas": {},
                "datacenter": {},
            }
        frames.append(frame)

    return frames

def compute_diagnostics(window_hours: int | None = None) -> dict:
    """
    Compute high-level system diagnostics from the DES state.
    This is used by the AI 'Digital Engineer' to explain system behaviour.

    window_hours:
      - None -> use full history
      - N    -> only analyse the last N hours if available
    """
    global sim_ps

    # If simulation not ready
    if sim_ps is None or not getattr(sim_ps, "history", None):
        return {
            "ready": False,
            "message": "Simulation not initialised or no history recorded yet.",
        }

    hist = sim_ps.history  # list of (online_lines, total_power, pv_gen, bess_dis)
    n_total = len(hist)
    if n_total == 0:
        return {
            "ready": False,
            "message": "No history entries recorded yet.",
        }

    # Choose window (full history or last N hours)
    if window_hours is not None and window_hours > 0:
        start_idx = max(0, n_total - window_hours)
    else:
        start_idx = 0

    hist_slice = hist[start_idx:]
    n_slice = len(hist_slice)

    load = des_core.ARCH["load_mw"]

    # --- Core time-series metrics ---
    total_power_series = []
    pv_series = []
    bess_dis_series = []

    for (online_lines, total_power, pv_gen, bess_dis) in hist_slice:
        total_power_series.append(float(total_power))
        pv_series.append(float(pv_gen))
        bess_dis_series.append(float(bess_dis))

    hours_underpowered = sum(
        1 for tp in total_power_series if tp + 1e-6 < load
    )
    frac_underpowered = hours_underpowered / n_slice if n_slice > 0 else 0.0

    avg_power = sum(total_power_series) / n_slice if n_slice > 0 else 0.0

    total_pv = sum(pv_series)
    total_bess_dis = sum(bess_dis_series)
    total_energy_served = sum(total_power_series)

    pv_share = (
        total_pv / total_energy_served if total_energy_served > 1e-6 else 0.0
    )
    bess_share = (
        total_bess_dis / total_energy_served if total_energy_served > 1e-6 else 0.0
    )

    # --- BESS behaviour ---
    bess_e = des_core.ARCH.get("bess_energy_mwh", 0.0) or 0.0
    bess_soc_hist = getattr(sim_ps, "bess_soc_hist", [sim_ps.bess_soc])
    bess_soc_slice = bess_soc_hist[start_idx : start_idx + n_slice]

    soc_pct_series = []
    if bess_e > 0.0:
        for s in bess_soc_slice:
            soc_pct_series.append(float(s) / bess_e * 100.0)
    else:
        soc_pct_series = [0.0 for _ in bess_soc_slice]

    avg_soc_pct = (
        sum(soc_pct_series) / len(soc_pct_series) if soc_pct_series else 0.0
    )
    hours_soc_below_20 = sum(1 for s in soc_pct_series if s < 20.0)
    frac_soc_below_20 = (
        hours_soc_below_20 / n_slice if n_slice > 0 else 0.0
    )
    hours_bess_used = sum(
        1 for v in bess_dis_series if v > 1e-6
    )
    frac_bess_used = hours_bess_used / n_slice if n_slice > 0 else 0.0

    # --- CHP fleet behaviour / stress ---
    chp_per_engine_uptime = []
    chp_per_engine_avg_load_frac = []

    # engine rating in MW for normalisation
    engine_rating = des_core.ARCH["engine_rating_mw"]

    for i in range(des_core.NUM_LINES):
        log = sim_ps.line_log.get(i, [])
        log_slice = log[start_idx : start_idx + n_slice]
        if log_slice:
            uptime_frac = sum(log_slice) / len(log_slice)
        else:
            uptime_frac = 0.0

        # Average load fraction for this engine over the slice
        total_frac = 0.0
        count = 0
        for t in range(start_idx, start_idx + n_slice):
            if t < len(sim_ps.chp_output_hist):
                out = sim_ps.chp_output_hist[t].get(i, 0.0)
                total_frac += float(out) / engine_rating if engine_rating > 0 else 0.0
                count += 1
        avg_frac = total_frac / count if count > 0 else 0.0

        chp_per_engine_uptime.append(uptime_frac)
        chp_per_engine_avg_load_frac.append(avg_frac)

    # Fleet-wide stats
    if chp_per_engine_uptime:
        fleet_uptime_avg = sum(chp_per_engine_uptime) / len(chp_per_engine_uptime)
    else:
        fleet_uptime_avg = 0.0

    # Simple imbalance index: standard deviation of avg load fractions
    if chp_per_engine_avg_load_frac:
        mean_load = sum(chp_per_engine_avg_load_frac) / len(
            chp_per_engine_avg_load_frac
        )
        var = sum(
            (x - mean_load) ** 2 for x in chp_per_engine_avg_load_frac
        ) / max(len(chp_per_engine_avg_load_frac), 1)
        load_imbalance_index = var**0.5  # standard deviation
    else:
        mean_load = 0.0
        load_imbalance_index = 0.0

    # --- PV stats ---
    avg_pv_mw = total_pv / n_slice if n_slice > 0 else 0.0
    hours_with_pv = sum(1 for v in pv_series if v > 1e-6)
    frac_hours_with_pv = hours_with_pv / n_slice if n_slice > 0 else 0.0

    # --- Infrastructure state (current snapshot) ---
    gas_main_up = bool(getattr(sim_ps, "gas_main", True))
    gas_tank_up = bool(getattr(sim_ps, "gas_tank", True))
    swbd_a_up = bool(sim_ps.swbd_states.get("A", True))
    swbd_b_up = bool(sim_ps.swbd_states.get("B", True))

    # --- Availability so far (full run) ---
    outage_hours = getattr(sim_ps, "outage_hours", 0)
    hours_below_load = getattr(sim_ps, "hours_below_load", 0)
    availability = 1.0 - (outage_hours / n_total) if n_total > 0 else 1.0

    return {
        "ready": True,
        "window": {
            "total_hours_simulated": n_total,
            "hours_analysed": n_slice,
            "from_hour": start_idx,
            "to_hour": start_idx + n_slice - 1,
        },
        "overall": {
            "load_mw": load,
            "avg_power_mw": avg_power,
            "fraction_hours_underpowered": frac_underpowered,
            "availability_overall": availability,
            "hours_underpowered": hours_underpowered,
            "hours_below_load_metric": hours_below_load,
        },
        "load_management": {
            "total_energy_served_mwh": total_energy_served,
            "total_pv_mwh": total_pv,
            "total_bess_discharge_mwh": total_bess_dis,
            "pv_share_of_energy": pv_share,
            "bess_share_of_energy": bess_share,
        },
        "bess": {
            "avg_soc_pct": avg_soc_pct,
            "fraction_hours_soc_below_20": frac_soc_below_20,
            "fraction_hours_bess_used": frac_bess_used,
        },
        "pv": {
            "avg_pv_mw": avg_pv_mw,
            "fraction_hours_with_pv": frac_hours_with_pv,
        },
        "chp": {
            "fleet_uptime_avg": fleet_uptime_avg,
            "fleet_avg_load_frac": mean_load,
            "load_imbalance_index": load_imbalance_index,
            "per_engine": [
                {
                    "id": i,
                    "uptime_fraction": chp_per_engine_uptime[i],
                    "avg_load_fraction": chp_per_engine_avg_load_frac[i],
                }
                for i in range(des_core.NUM_LINES)
            ],
        },
        "infrastructure": {
            "gas_main_up": gas_main_up,
            "gas_tank_up": gas_tank_up,
            "swbd_a_up": swbd_a_up,
            "swbd_b_up": swbd_b_up,
        },
    }
