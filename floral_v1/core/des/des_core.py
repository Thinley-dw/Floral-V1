import simpy
import random
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.patches import Patch

"""DES.py
Standalone DES animation for CHP + PV + BESS using SimPy + NetworkX + Matplotlib.
All MW numbers and counts live in ARCH and can be overwritten later by other code.
"""

def to_native(obj):
    """
    Recursively convert NumPy types (np.bool_, np.int64, np.float64, etc.)
    and tuples into pure Python types so FastAPI can JSON-encode them.
    """
    import numpy as np

    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]

    if isinstance(obj, np.generic):
        return obj.item()

    return obj

# ======================================================
#  ICON CONFIGURATION FOR NETWORK VISUALISATION
# ======================================================
ICON_FILES = {
    "Gas": "icons/gas_main.png",
    "GasTank": "icons/gas_tank.png",
    "CHP": "icons/chp.png",
    "RMU": "icons/rmu.png",
    "PV": "icons/pv_block.png",
    "BESS": "icons/bess.png",
    "SWBD": "icons/swbd.png",
    "Datacenter": "icons/datacenter.png",
}

# Load icon images up front (if files are missing, we fall back to default nodes)
ICON_IMAGES = {}
for key, path in ICON_FILES.items():
    try:
        ICON_IMAGES[key] = plt.imread(path)
    except Exception:
        ICON_IMAGES[key] = None

# ======================================================
#  ARCHITECTURE PLACEHOLDER (CAN BE OVERWRITTEN)
# ======================================================
ARCH = {
    "num_lines": 20,             # CHP lines (engine + RMU)
    "engine_rating_mw": 2.5,     # per-CHP rating
    "guaranteed_mw": 45.0,       # placeholder guaranteed power
    "load_mw": 45.0,             # placeholder data centre demand

    # PV – placeholder, to be replaced
    "pv_blocks": 8,
    "pv_block_rating_mw": 8.0,   # each block (oversized so PV can exceed load at peak and charge BESS)

    # BESS – placeholder, to be replaced
    "bess_power_mw": 15.0,
    "bess_energy_mwh": 60.0,
    "bess_pcs_units": 3,
    "bess_string_groups": 3,
}

# ======================================================
#  RELIABILITY (MTBF / MTTR)
# ======================================================
SIM_YEARS = 1  # simulate 1 year(s)
SIM_HOURS = 8760 * SIM_YEARS

NUM_LINES = ARCH["num_lines"]
MIN_LINES_REQUIRED = int(ARCH["guaranteed_mw"] / ARCH["engine_rating_mw"])


def configure_arch(overrides: dict, sim_hours: int | None = None) -> None:
    """Apply runtime architecture overrides sourced from HybridDesign."""
    global ARCH, NUM_LINES, MIN_LINES_REQUIRED, SIM_HOURS
    ARCH = {**ARCH, **overrides}
    NUM_LINES = int(ARCH["num_lines"])
    engine_rating = max(ARCH["engine_rating_mw"], 1e-6)
    MIN_LINES_REQUIRED = max(1, int(round(ARCH["guaranteed_mw"] / engine_rating)))
    if sim_hours is not None and sim_hours > 0:
        SIM_HOURS = int(sim_hours)
MTBF_gas = 8000
MTBF_gastank = 20000

MTBF_chp = 3000


def sample_mttr_chp() -> float:
    """Weighted mix of short/medium/long repairs for CHP.
Tuned so the average MTTR is ~140–150 hours when combined with
MTBF_chp = 3000 h, giving ~95% availability per engine."""
    return random.choices(
        [
            random.uniform(8, 24),    # minor outage (hours)
            random.uniform(80, 200),  # moderate outage (hours)
            random.uniform(300, 500), # major outage but less extreme
        ],
        weights=[0.4, 0.4, 0.2],
    )[0]


MTBF_rmu = 10000


def sample_mttr_rmu() -> float:
    return random.choices([0.5, 4, 12], weights=[0.5, 0.4, 0.1])[0]


MTBF_swbd = 20000


def sample_mttr_swbd() -> float:
    return random.choices([1, 4, 16], weights=[0.4, 0.4, 0.2])[0]


def sample_mttr_gas() -> float:
    return random.choices([1, 4, 24], weights=[0.4, 0.4, 0.2])[0]

def sample_mttr_gastank() -> float:
    return random.choices([0.5, 2, 8], weights=[0.5, 0.4, 0.1])[0]


MTBF_pv_block = 30000


def sample_mttr_pv_block() -> float:
    return random.choices([4, 12, 48], weights=[0.5, 0.3, 0.2])[0]


MTBF_bess_pcs = 20000


def sample_mttr_bess_pcs() -> float:
    return random.choices([2, 6, 24], weights=[0.5, 0.3, 0.2])[0]


MTBF_bess_strings = 40000


def sample_mttr_bess_strings() -> float:
    return random.choices([4, 24, 72], weights=[0.5, 0.3, 0.2])[0]


# ======================================================
#  SIMPLE IRRADIANCE PROFILE 0–1
# ======================================================

def pv_profile(hour: int) -> float:
    """Very simple day/night sinusoid (no seasons for now)."""
    h = hour % 24
    if 6 <= h <= 18:
        x = (h - 6) / 12.0
        return max(0.0, np.sin(np.pi * x))
    return 0.0


# ======================================================
#  INTERACTIVE POWER SYSTEM
# ======================================================


class InteractivePowerSystem:
    def __init__(self, env: simpy.Environment):
        self.env = env

        # CHP / RMU / SWBD / Gas
        self.line_states = {i: True for i in range(NUM_LINES)}
        self.rmu_states = {i: True for i in range(NUM_LINES)}
        self.swbd_states = {"A": True, "B": True}
        self.gas_main = True
        self.gas_tank = True

        # PV & BESS
        self.pv_states = {i: True for i in range(ARCH["pv_blocks"])}
        self.bess_pcs_states = {i: True for i in range(ARCH["bess_pcs_units"])}
        self.bess_string_states = {i: True for i in range(ARCH["bess_string_groups"])}
        self.bess_soc = 0.5 * ARCH["bess_energy_mwh"]  # start half full

        # History & metrics
        self.history = []  # (online_lines, total_power, pv_gen, bess_dis)
        self.line_log = {i: [] for i in range(NUM_LINES)}
        # Per-PV-block log of effective online state (after applying schedule)
        self.pv_log = {i: [] for i in range(ARCH["pv_blocks"])}
        self.chp_output_hist = []
        self.pv_power_hist = []
        self.bess_dis_hist = []
        self.bess_ch_hist = []
        self.bess_soc_hist = []
        self.outage_hours = 0
        self.hours_below_load = 0

        # Simulation mode and schedule may be injected from outside (des_engine).
        # Defaults keep standalone DES behaviour unchanged.
        self.sim_mode = getattr(self, "sim_mode", "random")  # "random" | "hybrid" | "schedule"
        self.sim_schedule = getattr(self, "sim_schedule", [])

        # Start stochastic failure and monitor processes
        for i in range(NUM_LINES):
            self.env.process(self.chp_fail(i))
            self.env.process(self.rmu_fail(i))
        self.env.process(self.swbd_fail("A"))
        self.env.process(self.swbd_fail("B"))
        self.env.process(self.gas_fail())
        self.env.process(self.gas_tank_fail())

        for i in range(ARCH["pv_blocks"]):
            self.env.process(self.pv_fail(i))
        for i in range(ARCH["bess_pcs_units"]):
            self.env.process(self.bess_pcs_fail(i))
        for i in range(ARCH["bess_string_groups"]):
            self.env.process(self.bess_string_fail(i))

        # Core hourly monitor
        self.env.process(self.monitor())
    # -------------- Scheduling helpers --------------
    def _is_scheduled_outage(self, asset_type: str, display_index: int, hour: int) -> bool:
        """
        Return True if the given asset (by display index, 1-based as seen in the UI)
        is under a scheduled outage at the given hour.

        asset_type:
          - "chp":  display_index = CHP line number (1..NUM_LINES)
          - "pv":   display_index = PV block number (1..ARCH["pv_blocks"])
          - "bess": display_index = 1 means the whole BESS asset

        The schedule is expected to be a list of dicts with keys:
          - asset_type, asset_index, start_hour, duration_hours
        """
        schedule = getattr(self, "sim_schedule", []) or []
        for ev in schedule:
            try:
                if ev.get("asset_type") != asset_type:
                    continue
                ev_index = int(ev.get("asset_index", 0))
                # For BESS we treat asset_index=1 as "entire BESS"; ignore others.
                if asset_type != "bess" and ev_index != display_index:
                    continue
                if asset_type == "bess" and ev_index != 1:
                    continue

                start = int(ev.get("start_hour", 0))
                dur = int(ev.get("duration_hours", 0))
                if dur <= 0:
                    continue
                if start <= hour < start + dur:
                    return True
            except Exception as e:
                print("[WARN] invalid schedule event:", e, ev)
                continue
        return False

    # -------------- Failure models --------------
    def chp_fail(self, i: int):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_chp))
                self.line_states[i] = False
                yield self.env.timeout(sample_mttr_chp())
                self.line_states[i] = True
            except Exception as e:
                print(f"[ERROR] chp_fail crashed:", e)
                yield self.env.timeout(1)

    def rmu_fail(self, i: int):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_rmu))
                self.rmu_states[i] = False
                yield self.env.timeout(sample_mttr_rmu())
                self.rmu_states[i] = True
            except Exception as e:
                print(f"[ERROR] rmu_fail crashed:", e)
                yield self.env.timeout(1)

    def swbd_fail(self, sw: str):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_swbd))
                self.swbd_states[sw] = False
                yield self.env.timeout(sample_mttr_swbd())
                self.swbd_states[sw] = True
            except Exception as e:
                print(f"[ERROR] swbd_fail crashed:", e)
                yield self.env.timeout(1)

    def gas_fail(self):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_gas))
                self.gas_main = False
                yield self.env.timeout(sample_mttr_gas())
                self.gas_main = True
            except Exception as e:
                print(f"[ERROR] gas_fail crashed:", e)
                yield self.env.timeout(1)

    def gas_tank_fail(self):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_gastank))
                self.gas_tank = False
                yield self.env.timeout(sample_mttr_gastank())
                self.gas_tank = True
            except Exception as e:
                print(f"[ERROR] gas_tank_fail crashed:", e)
                yield self.env.timeout(1)

    def pv_fail(self, i: int):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_pv_block))
                self.pv_states[i] = False
                yield self.env.timeout(sample_mttr_pv_block())
                self.pv_states[i] = True
            except Exception as e:
                print(f"[ERROR] pv_fail crashed:", e)
                yield self.env.timeout(1)

    def bess_pcs_fail(self, i: int):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_bess_pcs))
                self.bess_pcs_states[i] = False
                yield self.env.timeout(sample_mttr_bess_pcs())
                self.bess_pcs_states[i] = True
            except Exception as e:
                print(f"[ERROR] bess_pcs_fail crashed:", e)
                yield self.env.timeout(1)

    def bess_string_fail(self, i: int):
        while True:
            try:
                yield self.env.timeout(random.expovariate(1 / MTBF_bess_strings))
                self.bess_string_states[i] = False
                yield self.env.timeout(sample_mttr_bess_strings())
                self.bess_string_states[i] = True
            except Exception as e:
                print(f"[ERROR] bess_string_fail crashed:", e)
                yield self.env.timeout(1)

    # -------------- Core hourly monitor / dispatch --------------
    def monitor(self):
        while True:
            try:
                hour = int(self.env.now)
                load = ARCH["load_mw"]

                # Ensure we pick up any mode/schedule injected after __init__
                mode = getattr(self, "sim_mode", "random") or "random"

                # Effective CHP line states after applying schedule/mode
                effective_line_states = {}
                for i in range(NUM_LINES):
                    base_up = self.line_states[i]
                    # In schedule-only mode we ignore stochastic CHP failures and
                    # start from an "all up" baseline.
                    if mode == "schedule":
                        base_up = True
                    # Overlay scheduled outages (UI is 1-based indexing)
                    if self._is_scheduled_outage("chp", i + 1, hour):
                        eff_up = False
                    else:
                        eff_up = base_up
                    effective_line_states[i] = eff_up

                online = sum(effective_line_states.values())
                healthy = [i for i, v in effective_line_states.items() if v]

                # PV side (apply schedule / mode to PV availability)
                pv_norm = pv_profile(hour)
                effective_pv_states = {}
                for i in range(ARCH["pv_blocks"]):
                    base_up = self.pv_states[i]
                    if mode == "schedule":
                        base_up = True
                    if self._is_scheduled_outage("pv", i + 1, hour):
                        eff_up = False
                    else:
                        eff_up = base_up
                    effective_pv_states[i] = eff_up

                pv_up = sum(1 for v in effective_pv_states.values() if v)
                pv_cap = pv_up * ARCH["pv_block_rating_mw"]
                pv_possible = pv_cap * pv_norm

                # BESS side (apply schedule / mode to overall BESS availability)
                pcs_up = sum(self.bess_pcs_states.values())
                str_up = sum(self.bess_string_states.values())

                if mode == "schedule":
                    # Ignore stochastic failures for schedule-only runs
                    pcs_up = ARCH["bess_pcs_units"]
                    str_up = ARCH["bess_string_groups"]

                bess_forced_out = self._is_scheduled_outage("bess", 1, hour)
                if bess_forced_out:
                    pcs_up = 0
                    str_up = 0

                bess_pmax = ARCH["bess_power_mw"] * (pcs_up / max(1, ARCH["bess_pcs_units"]))
                bess_emax = ARCH["bess_energy_mwh"] * (str_up / max(1, ARCH["bess_string_groups"]))
                self.bess_soc = min(self.bess_soc, bess_emax)

                # Dispatch: PV -> BESS -> CHP
                rem = load

                # PV serves load first
                pv_gen = min(rem, pv_possible)
                rem -= pv_gen

                # BESS discharge
                bess_dis = 0.0
                if bess_pmax > 0 and self.bess_soc > 0:
                    bess_dis = min(rem, bess_pmax, self.bess_soc)
                    self.bess_soc -= bess_dis
                    rem -= bess_dis

                # CHP covers remainder or idles
                chp_out = {}
                chp_gen = 0.0
                if healthy:
                    if rem > 0:
                        per = min(ARCH["engine_rating_mw"], rem / len(healthy))
                        for i in healthy:
                            chp_out[i] = per
                        chp_gen = per * len(healthy)
                        rem -= chp_gen
                    else:
                        # PV + BESS covered load -> low turndown for colour
                        per = 0.1 * ARCH["engine_rating_mw"]
                        for i in healthy:
                            chp_out[i] = per
                        chp_gen = per * len(healthy)

                # PV surplus to BESS (simple)
                pv_surplus = max(0.0, pv_possible - pv_gen)
                bess_ch = 0.0
                if pv_surplus > 0 and bess_pmax > 0 and self.bess_soc < bess_emax:
                    bess_ch = min(pv_surplus, bess_pmax, bess_emax - self.bess_soc)
                    self.bess_soc += bess_ch

                total_power = pv_gen + bess_dis + chp_gen
                unserved = max(0.0, load - total_power)

                # Path / availability logic
                swbd_a = self.swbd_states["A"]
                swbd_b = self.swbd_states["B"]
                gas_ok = (self.gas_main or self.gas_tank)
                path_ok = (swbd_a or swbd_b) and gas_ok and online >= MIN_LINES_REQUIRED

                if not path_ok or unserved > 1e-6:
                    self.outage_hours += 1
                if total_power < load - 1e-6:
                    self.hours_below_load += 1

                # Log history
                self.history.append((online, total_power, pv_gen, bess_dis))
                self.chp_output_hist.append(dict(chp_out))
                self.pv_power_hist.append(pv_gen)
                self.bess_dis_hist.append(bess_dis)
                self.bess_ch_hist.append(bess_ch)
                self.bess_soc_hist.append(self.bess_soc)

                # Log effective states (after applying schedule/mode) for visualisation
                for i in range(NUM_LINES):
                    self.line_log[i].append(1 if effective_line_states.get(i, False) else 0)
                for i in range(ARCH["pv_blocks"]):
                    self.pv_log[i].append(1 if effective_pv_states.get(i, False) else 0)
            except Exception as e:
                print("[ERROR] monitor() crashed:", e)
            finally:
                yield self.env.timeout(1)


# ======================================================
#  VISUALISATION: NETWORKX ANIMATED TOPOLOGY
# ======================================================


def draw_network_status(ps: InteractivePowerSystem, hour: int):
    # Create / reuse figure and split into network + HUD axes
    fig = plt.gcf()
    fig.clf()
    gs = fig.add_gridspec(1, 2, width_ratios=[3, 1])
    ax_net = fig.add_subplot(gs[0, 0])
    ax_hud = fig.add_subplot(gs[0, 1])

    G = nx.DiGraph()

    # Nodes
    G.add_node("Gas", label="Gas Main")
    G.add_node("GasTank", label="Gas Tank")

    for i in range(len(ps.pv_states)):
        G.add_node(f"PV{i}", label=f"PV{i}")

    for i in range(NUM_LINES):
        G.add_node(f"L{i}", label=f"CHP L{i}")
        G.add_node(f"RMU{i}", label=f"RMU{i}")

    G.add_node("BESS", label="BESS")
    G.add_node("SWBD A", label="Switchboard A")
    G.add_node("SWBD B", label="Switchboard B")
    G.add_node("Datacenter", label="Datacenter")

    # Edges
    for i in range(NUM_LINES):
        G.add_edge("Gas", f"L{i}")
        G.add_edge("GasTank", f"L{i}")
        G.add_edge(f"L{i}", f"RMU{i}")
        G.add_edge(f"RMU{i}", "SWBD A")
        G.add_edge(f"RMU{i}", "SWBD B")

    for i in range(len(ps.pv_states)):
        G.add_edge(f"PV{i}", "Datacenter")

    G.add_edge("BESS", "Datacenter")
    G.add_edge("SWBD A", "Datacenter")
    G.add_edge("SWBD B", "Datacenter")

    # Colours
    cmap_nodes = plt.cm.Greens
    cmap_edges = plt.cm.plasma
    node_color_map = {}

    # Gas nodes
    node_color_map["Gas"] = "green" if ps.gas_main else "red"
    if ps.gas_main:
        node_color_map["GasTank"] = "grey"
        gas_tank_status = "Standby"
    else:
        if ps.gas_tank:
            node_color_map["GasTank"] = "green"
            gas_tank_status = "Active"
        else:
            node_color_map["GasTank"] = "red"
            gas_tank_status = "Failed"

    # State at this hour
    if hour < len(ps.history):
        online, total_power, pv_gen, bess_dis = ps.history[hour]
    else:
        online = sum(ps.line_states.values())
        total_power = online * ARCH["engine_rating_mw"]
        pv_gen = 0.0
        bess_dis = 0.0

    load = ARCH["load_mw"]
    chp_out_hour = ps.chp_output_hist[hour] if hour < len(ps.chp_output_hist) else {}

    # CHP & RMU nodes with gradient
    for i in range(NUM_LINES):
        status = ps.line_log[i][hour] if hour < len(ps.line_log[i]) else (1 if ps.line_states[i] else 0)
        line_node = f"L{i}"
        rmu_node = f"RMU{i}"
        if status == 0:
            node_color_map[line_node] = "red"
            node_color_map[rmu_node] = "red"
        else:
            line_output = chp_out_hour.get(i, 0.0)
            frac = min(max(line_output / ARCH["engine_rating_mw"], 0.0), 1.0)
            color_val = cmap_nodes(0.18 + 0.77 * frac)
            hex_col = mcolors.to_hex(color_val)
            node_color_map[line_node] = hex_col
            node_color_map[rmu_node] = hex_col

    # NOTE: pv_states keys assumed to be sequential integers 0..N; update if upstream model changes key format.
    # PV nodes – prefer logged effective state (pv_log) if available
    pv_blocks_up = 0
    pv_state_now = {}
    for i in range(len(ps.pv_states)):
        if hasattr(ps, "pv_log") and i in ps.pv_log and hour < len(ps.pv_log[i]):
            up = bool(ps.pv_log[i][hour])
        else:
            up = bool(ps.pv_states[i])
        pv_state_now[i] = up
        if up:
            pv_blocks_up += 1

    pv_per_block = pv_gen / max(pv_blocks_up, 1) if pv_blocks_up > 0 else 0.0
    for i in range(len(ps.pv_states)):
        up = pv_state_now[i]
        if not up:
            node_color_map[f"PV{i}"] = "red"
        else:
            node_color_map[f"PV{i}"] = "#ffd54f" if pv_per_block > 0 else "#555555"

    # BESS node
    any_pcs_up = any(ps.bess_pcs_states.values())
    any_str_up = any(ps.bess_string_states.values())
    if not any_pcs_up or not any_str_up:
        node_color_map["BESS"] = "red"
    else:
        if bess_dis > 0:
            node_color_map["BESS"] = "#4aa8ff"
        elif (ps.bess_ch_hist[hour] > 0.0) if hour < len(ps.bess_ch_hist) else False:
            node_color_map["BESS"] = "#82cfff"
        else:
            node_color_map["BESS"] = "#1b3b5f"

    # SWBDs
    swbd_a_up = ps.swbd_states["A"]
    swbd_b_up = ps.swbd_states["B"]
    node_color_map["SWBD A"] = "green" if swbd_a_up else "red"
    node_color_map["SWBD B"] = "grey" if swbd_a_up and swbd_b_up else ("green" if swbd_b_up else "red")

    # Datacenter node
    gas_ok = ps.gas_main or ps.gas_tank
    if total_power + 1e-6 >= load and (swbd_a_up or swbd_b_up) and gas_ok:
        node_color_map["Datacenter"] = "green"
    elif total_power > 0:
        node_color_map["Datacenter"] = "orange"
    else:
        node_color_map["Datacenter"] = "red"

    def is_operational(col: str) -> bool:
        return col not in ("red", "grey")

    # Node & edge colours (with MW-based gradients)
    node_colors = [node_color_map.get(n, "grey") for n in G.nodes()]
    edge_colors = []
    edge_widths = []

    # Normalise helpers
    max_chp_mw = ARCH["engine_rating_mw"]
    max_pv_mw = ARCH["pv_block_rating_mw"]
    max_bess_mw = ARCH["bess_power_mw"]

    # Initialize safe defaults for frac values before the edge loop
    frac = 0.0
    frac_pv = 0.0
    frac_bess = 0.0

    for u, v in G.edges():
        u_col = node_color_map.get(u, "grey")
        v_col = node_color_map.get(v, "grey")
        color = "grey"
        width = 1.0

        if u == "Gas":
            color = "green" if ps.gas_main else "grey"
        elif u == "GasTank":
            if ps.gas_main:
                color = "grey"
            else:
                color = "green" if ps.gas_tank else "red"
        elif u.startswith("L") and v.startswith("RMU"):
            # CHP line -> RMU edge based on that CHP's output
            # Replace with: color = "green" if u_col != "red" else "red"
            color = "green" if u_col != "red" else "red"
            idx = int(u[1:])
            line_output = chp_out_hour.get(idx, 0.0)
            frac = min(max(line_output / max_chp_mw, 0.0), 1.0)
            width = 1.0 + 2.0 * frac
        elif u.startswith("RMU") and v in ("SWBD A", "SWBD B"):
            if u_col == "red" or v_col == "red":
                color = "red"
            elif is_operational(u_col) and is_operational(v_col):
                color = "green"
            else:
                color = "grey"
            width = 1.2
        elif u in ("SWBD A", "SWBD B") and v == "Datacenter":
            if node_color_map.get(u) == "green":
                color = "green"
            elif node_color_map.get(u) == "grey":
                color = "grey"
            else:
                color = "red"
            width = 2.0
        elif u.startswith("PV"):
            # PV -> Datacenter edge based on PV per block
            # Replace with: color = "green" if pv_per_block > 0 else "grey"
            if pv_per_block > 0:
                color = "green"
                width = 0.5 + 2.0 * min(max(pv_per_block / max_pv_mw, 0.0), 1.0) if max_pv_mw > 0 else 0.5
            else:
                color = "grey"
                width = 0.5
        elif u == "BESS":
            # Replace with: color = "green" if bess_dis > 0 else "grey"
            if bess_dis > 0:
                color = "green"
                width = 0.5 + 2.0 * min(max(bess_dis / max_bess_mw, 0.0), 1.0) if max_bess_mw > 0 else 0.5
            else:
                color = "grey"
                width = 0.5
        else:
            # For all other edges:
            # If either node is failed → color = "red"
            # If path is unused but operational → color = "grey"
            # Otherwise → color = "green"
            if u_col == "red" or v_col == "red":
                color = "red"
            elif is_operational(u_col) and is_operational(v_col):
                color = "green"
            else:
                color = "grey"

        edge_colors.append(color)
        edge_widths.append(width)

    # Layout
    pos = {}
    for i in range(NUM_LINES):
        pos[f"L{i}"] = (1, NUM_LINES / 2 - i)
        pos[f"RMU{i}"] = (2, NUM_LINES / 2 - i)

    pos["Gas"] = (0, 1)
    pos["GasTank"] = (0, -1)

    for i in range(len(ps.pv_states)):
        pos[f"PV{i}"] = (0.5 + 0.5 * i, NUM_LINES / 2 + 2)

    # Place BESS visually near the PV row (clustered logically with PV)
    if len(ps.pv_states) > 0:
        pv_center_x = 0.5 + 0.5 * (len(ps.pv_states) - 1) / 2.0
        pos["BESS"] = (pv_center_x, NUM_LINES / 2 + 0.5)
    else:
        pos["BESS"] = (1, NUM_LINES / 2 + 0.5)
    pos["SWBD A"] = (3, 1)
    pos["SWBD B"] = (3, -1)
    pos["Datacenter"] = (4, 0)

    # Draw base network (nodes as transparent circles; icons on top)
    nx.draw(
        G,
        pos,
        with_labels=False,
        node_color=node_colors,
        edge_color=edge_colors,
        node_size=900,
        font_size=8,
        font_weight="bold",
        arrowsize=15,
        width=edge_widths,
        ax=ax_net,
    )

    # Overlay icons on top of nodes
    icon_size = 0.35  # half-size for extent around node position
    for node, (x, y) in pos.items():
        if node == "Gas":
            icon = ICON_IMAGES.get("Gas")
        elif node == "GasTank":
            icon = ICON_IMAGES.get("GasTank")
        elif node.startswith("L"):
            icon = ICON_IMAGES.get("CHP")
        elif node.startswith("RMU"):
            icon = ICON_IMAGES.get("RMU")
        elif node.startswith("PV"):
            icon = ICON_IMAGES.get("PV")
        elif node == "BESS":
            icon = ICON_IMAGES.get("BESS")
        elif node.startswith("SWBD"):
            icon = ICON_IMAGES.get("SWBD")
        elif node == "Datacenter":
            icon = ICON_IMAGES.get("Datacenter")
        else:
            icon = None

        if icon is not None:
            ax_net.imshow(
                icon,
                extent=(x - icon_size, x + icon_size, y - icon_size, y + icon_size),
                zorder=3,
            )
        # Add text labels for each component underneath icons
        ax_net.text(
            x,
            y - 0.45,
            node,
            fontsize=7,
            color="white",
            ha="center",
            va="top",
            zorder=4,
        )

    # Display real-time power delivered to the Datacenter
    if "Datacenter" in pos:
        dc_x, dc_y = pos["Datacenter"]
        ax_net.text(
            dc_x + 0.1,
            dc_y + 0.5,
            f"{total_power:.1f} MW",
            fontsize=9,
            color="cyan",
            ha="left",
            va="bottom",
            fontweight="bold",
            zorder=5,
        )

    ax_net.set_axis_off()

    # Title with alert
    alert_text = ""
    if total_power < load - 1e-6:
        alert_text = "\n⚠️ Under Load Threshold!"

    ax_net.set_title(
        f"System Status at Hour {hour}\n"
        f"Total Power: {total_power:.1f} MW (Load {load:.1f} MW){alert_text}\n"
        f"Green=Operational, Red=Failed, Yellow=PV, Blue=BESS",
        fontsize=10,
    )

    # HUD panel (clean text summary)
    ax_hud.set_facecolor("#111111")
    ax_hud.set_axis_off()

    pv_str = f"{pv_gen:.2f} MW"
    bess_str = f"{bess_dis:.2f} MW"
    chp_str = f"{max(0.0, total_power - pv_gen - bess_dis):.2f} MW"
    soc = ps.bess_soc_hist[hour] if hour < len(ps.bess_soc_hist) else ps.bess_soc
    bess_soc_pct = 0.0
    if ARCH["bess_energy_mwh"] > 0:
        bess_soc_pct = min(max(soc / ARCH["bess_energy_mwh"] * 100.0, 0.0), 100.0)

    hud_lines = [
        "POWER SUMMARY",
        "--------------",
        f"Load:        {load:.2f} MW",
        f"CHP Output:  {chp_str}",
        f"PV Output:   {pv_str}",
        f"BESS Disch.: {bess_str}",
        "",
        "BESS STATUS",
        "--------------",
        f"SOC:         {bess_soc_pct:.1f} %",
        "",
        "ASSET STATUS",
        "--------------",
        f"CHPs Online: {online}/{NUM_LINES}",
        f"SWBD A:      {'UP' if swbd_a_up else 'DOWN'}",
        f"SWBD B:      {'UP' if swbd_b_up else 'DOWN'}",
        f"Gas Main:    {'UP' if ps.gas_main else 'DOWN'}",
        f"Gas Tank:    {gas_tank_status}",
        "",
        "SIMULATION",
        "--------------",
        f"Hour: {hour} / {SIM_HOURS}",
    ]

    y = 0.95
    for line in hud_lines:
        ax_hud.text(
            0.02,
            y,
            line,
            transform=ax_hud.transAxes,
            fontsize=9,
            color="white",
            va="top",
        )
        y -= 0.045

    fig.tight_layout()
    plt.pause(0.05)


# ======================================================
#  RUN SIMULATION + ANIMATION
# ======================================================





def build_frame(ps: InteractivePowerSystem, hour: int) -> dict:
    """Build a single simulation frame for React."""
    
    load = ARCH["load_mw"]

    # Safe access to stored history
    if hour >= len(ps.history):
        hour = len(ps.history) - 1
    online, total_power, pv_gen, bess_dis = ps.history[hour]
    chp_outputs = ps.chp_output_hist[hour] if hour < len(ps.chp_output_hist) else {}

    # CHP
    chp_list = []
    for i in range(NUM_LINES):
        chp_list.append({
            "id": i,
            "online": bool(ps.line_log[i][hour]),
            "mw": chp_outputs.get(i, 0.0)
        })

    # PV
    pv_list = []
    pv_up = 0
    pv_online_flags = {}

    for i in range(len(ps.pv_states)):
        # Use logged effective state if available, else fall back to current state
        if hasattr(ps, "pv_log") and i in ps.pv_log and hour < len(ps.pv_log[i]):
            eff_up = bool(ps.pv_log[i][hour])
        else:
            eff_up = bool(ps.pv_states[i])
        pv_online_flags[i] = eff_up
        if eff_up:
            pv_up += 1

    pv_per_block = pv_gen / pv_up if pv_up > 0 else 0.0
    for i in range(len(ps.pv_states)):
        online = pv_online_flags[i]
        pv_list.append({
            "id": i,
            "online": online,
            "mw": pv_per_block if online else 0.0
        })

    # BESS
    soc = ps.bess_soc_hist[hour] if hour < len(ps.bess_soc_hist) else ps.bess_soc
    soc_pct = float(soc) / float(ARCH["bess_energy_mwh"]) * 100.0

    bess = {
        "soc_mwh": soc,
        "soc_pct": soc_pct,
        "discharge_mw": bess_dis,
        "charge_mw": ps.bess_ch_hist[hour] if hour < len(ps.bess_ch_hist) else 0.0
    }

    # Switchboards
    swbd = {
        "A": bool(ps.swbd_states["A"]),
        "B": bool(ps.swbd_states["B"])
    }
    swbd = {"A": bool(swbd["A"]), "B": bool(swbd["B"])}

    # Gas
    gas = {
        "main": bool(ps.gas_main),
        "tank": bool(ps.gas_tank)
    }
    gas = {"main": bool(gas["main"]), "tank": bool(gas["tank"])}

    # Datacenter
    datacenter = {
        "served_mw": total_power,
        "underpowered": total_power + 1e-6 < load
    }

    return {
        "hour": hour,
        "load_mw": load,
        "datacenter": datacenter,
        "chp": chp_list,
        "pv": pv_list,
        "bess": bess,
        "switchboards": swbd,
        "gas": gas
    }

def run_des_once(seed: int | None = None) -> list[dict]:
    """
    Runs a 1-year DES simulation (randomised failures).
    Returns a list of hourly frames for React visualization.
    """
    
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    env = simpy.Environment()
    ps = InteractivePowerSystem(env)

    frames = []

    for hour in range(SIM_HOURS):
        env.run(until=hour + 1)
        frame = build_frame(ps, hour)
        frames.append(frame)

    return to_native(frames)
