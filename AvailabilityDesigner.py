import simpy
import random
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.patches import Patch
import streamlit as st
import pandas as pd
from math import comb, ceil

# ----------------------------------
# SYSTEM PARAMETERS
# ----------------------------------
CHP_SIZE_MW = 2.5  # Per-CHP rating
TARGET_LOAD_MW = 45.0  # Default; updated dynamically in Streamlit app

NUM_LINES = 20
MIN_LINES_REQUIRED = 18  # For TARGET_LOAD_MW with 2.5 MW CHPs (legacy default)
SIM_HOURS = 8760 * 5  # 5 years

# Gold Book MTBF and MTTR values (reverted to industry-standard)
MTBF_chp = 12000   # CHP Engine MTBF
# CHP Engine MTTR is now sampled
def sample_mttr_chp():
    # Weighted mix of short, medium, and long repair durations for realism
    return random.choices(
        [
            random.uniform(8, 24),      # minor: quick reset or minor fault (<1 day)
            random.uniform(120, 300),   # moderate: several days repair
            random.uniform(600, 1000)   # major: mechanical overhaul
        ],
        weights=[0.4, 0.3, 0.3]
    )[0]

MTBF_rmu = 50000   # RMU MTBF
# RMU MTTR is now sampled
def sample_mttr_rmu():
    # Light: 0.5h, Moderate: 4h, Severe: 12h
    return random.choices([0.5, 4, 12], weights=[0.5, 0.4, 0.1])[0]

MTBF_swbd = 110000  # Switchboards
# Switchboard MTTR is now sampled
def sample_mttr_swbd():
    # Light: 1h, Moderate: 4h, Severe: 16h
    return random.choices([1, 4, 16], weights=[0.4, 0.4, 0.2])[0]

MTBF_gas = 8000    # Main Gas Supply
# Gas Supply MTTR is now sampled
def sample_mttr_gas():
    # Light: 1h, Moderate: 4h, Severe: 24h
    return random.choices([1, 4, 24], weights=[0.4, 0.4, 0.2])[0]

MTBF_gastank = 20000  # Gas Tank MTBF (redundant path)
# Gas Tank MTTR is now sampled
def sample_mttr_gastank():
    # Light: 0.5h, Moderate: 2h, Severe: 8h
    return random.choices([0.5, 2, 8], weights=[0.5, 0.4, 0.1])[0]

# ----------------------------------
# SIZING HELPERS
# ----------------------------------
def estimate_chp_availability():
    """Estimate single-CHP availability from MTBF and MTTR mix."""
    # Expected MTTR from the weighted distribution in sample_mttr_chp
    minor_mean = (8 + 24) / 2
    moderate_mean = (120 + 300) / 2
    major_mean = (600 + 1000) / 2
    expected_mttr = 0.4 * minor_mean + 0.3 * moderate_mean + 0.3 * major_mean
    return MTBF_chp / (MTBF_chp + expected_mttr)

def k_out_of_n_availability(n, k, a):
    """Instantaneous k-out-of-n availability for independent identical components."""
    return sum(comb(n, i) * (a ** i) * ((1 - a) ** (n - i)) for i in range(k, n + 1))

def size_chp_fleet(target_load_mw, target_avail, chp_size_mw=2.5):
    """
    Given target load and availability, pick k (min CHPs needed) and n (installed CHPs)
    using shared N+N-style redundancy (k-out-of-n).
    """
    if target_load_mw <= 0:
        raise ValueError("Target load must be positive.")
    k = int(ceil(target_load_mw / chp_size_mw))
    a = estimate_chp_availability()
    # Start with a small margin (k+2) and grow until target availability is met.
    n = max(k + 2, k)
    while k_out_of_n_availability(n, k, a) < target_avail and n < 200:
        n += 1
    return k, n

# ----------------------------------
# SIMPY RESOURCES
# ----------------------------------
class PowerSystem:
    def __init__(self, env):
        self.env = env
        self.online_lines = NUM_LINES
        self.swbd_a_up = True
        self.swbd_b_up = True
        self.outage_hours = 0
        self.history = []

        # Start component processes
        for i in range(NUM_LINES):
            env.process(self.chp_failure(i))
            env.process(self.rmu_failure(i))
        env.process(self.switchboard_failure("A"))
        env.process(self.switchboard_failure("B"))
        env.process(self.check_availability())

    def chp_failure(self, line_id):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_chp))
            self.online_lines -= 1
            yield self.env.timeout(sample_mttr_chp())
            self.online_lines += 1

    def rmu_failure(self, line_id):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_rmu))
            self.online_lines -= 1
            yield self.env.timeout(sample_mttr_rmu())
            self.online_lines += 1

    def switchboard_failure(self, swbd):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_swbd))
            if swbd == "A":
                self.swbd_a_up = False
            else:
                self.swbd_b_up = False
            yield self.env.timeout(sample_mttr_swbd())
            if swbd == "A":
                self.swbd_a_up = True
            else:
                self.swbd_b_up = True

    def check_availability(self):
        while True:
            if self.online_lines >= MIN_LINES_REQUIRED and (self.swbd_a_up or self.swbd_b_up):
                self.history.append(self.online_lines)
            else:
                self.history.append(self.online_lines)
                self.outage_hours += 1
            yield self.env.timeout(1)

#
# ----------------------------------
# InteractivePowerSystem and draw_network_status remain for Streamlit use
# ----------------------------------

class InteractivePowerSystem(PowerSystem):
    def __init__(self, env):
        self.env = env
        self.line_status_log = {i: [] for i in range(NUM_LINES)}
        self.line_states = {i: True for i in range(NUM_LINES)}  # True = operational
        self.swbd_states = {"A": True, "B": True}
        self.gas_main = True
        self.gas_tank = True
        self.outage_hours = 0
        self.history = []
        self.hours_below_target = 0
        self.yearly_outage_hours = 0
        self.yearly_hours_below_target = 0
        self.yearly_hours = 0
        for i in range(NUM_LINES):
            env.process(self.chp_failure(i))
            env.process(self.rmu_failure(i))
        env.process(self.switchboard_failure("A"))
        env.process(self.switchboard_failure("B"))
        env.process(self.gas_failure())
        env.process(self.gas_tank_failure())
        env.process(self.monitor_system())

    def toggle_component(self, component_type, component_id):
        if component_type == "line":
            if component_id in self.line_states:
                self.line_states[component_id] = not self.line_states[component_id]
        elif component_type == "switchboard":
            if component_id in self.swbd_states:
                self.swbd_states[component_id] = not self.swbd_states[component_id]

    def monitor_system(self):
        while True:
            # All healthy CHPs share the TARGET_LOAD_MW equally (if at least MIN_LINES_REQUIRED are healthy)
            online_lines = sum(1 for state in self.line_states.values() if state)
            healthy_indices = [i for i, state in self.line_states.items() if state]
            # Determine per-line MW output based on target load
            target_load = TARGET_LOAD_MW
            chp_size = CHP_SIZE_MW

            if online_lines >= MIN_LINES_REQUIRED:
                # Distribute target load equally to all healthy CHPs
                per_chp_output = target_load / online_lines
                chp_outputs = {i: per_chp_output for i in healthy_indices}
                power_output_mw = target_load
            else:
                # Not enough lines to cover target; each healthy CHP produces its full rating
                chp_outputs = {i: chp_size for i in healthy_indices}
                power_output_mw = chp_size * online_lines
            # Store for visualization
            self.chp_outputs = chp_outputs
            self.history.append((online_lines, power_output_mw))
            swbd_a = self.swbd_states["A"]
            swbd_b = self.swbd_states["B"]
            gas_ok = (self.gas_main or self.gas_tank)
            if online_lines >= MIN_LINES_REQUIRED and (swbd_a or swbd_b) and gas_ok:
                self.outage_hours += 0
                self.yearly_outage_hours += 0
            else:
                self.outage_hours += 1
                self.yearly_outage_hours += 1
            if power_output_mw < TARGET_LOAD_MW:
                self.hours_below_target += 1
                self.yearly_hours_below_target += 1
            for i in range(NUM_LINES):
                self.line_status_log[i].append(1 if self.line_states[i] else 0)
            self.yearly_hours += 1
            if self.yearly_hours == 8760:
                availability_year = (8760 - self.yearly_outage_hours) / 8760 * 100
                print(f"Year {self.env.now // 8760} Availability = {availability_year:.6f}%")
                print(f"Year {self.env.now // 8760} Outage Hours = {self.yearly_outage_hours}")
                print(f"Year {self.env.now // 8760} Hours < Target Load = {self.yearly_hours_below_target}")
                self.yearly_outage_hours = 0
                self.yearly_hours_below_target = 0
                self.yearly_hours = 0
            yield self.env.timeout(1)

    def chp_failure(self, line_id):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_chp))
            self.line_states[line_id] = False
            yield self.env.timeout(sample_mttr_chp())
            self.line_states[line_id] = True

    def rmu_failure(self, line_id):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_rmu))
            self.line_states[line_id] = False
            yield self.env.timeout(sample_mttr_rmu())
            self.line_states[line_id] = True

    def switchboard_failure(self, swbd):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_swbd))
            self.swbd_states[swbd] = False
            yield self.env.timeout(sample_mttr_swbd())
            self.swbd_states[swbd] = True

    def gas_failure(self):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_gas))
            self.gas_main = False
            yield self.env.timeout(sample_mttr_gas())
            self.gas_main = True

    def gas_tank_failure(self):
        while True:
            yield self.env.timeout(random.expovariate(1 / MTBF_gastank))
            self.gas_tank = False
            yield self.env.timeout(sample_mttr_gastank())
            self.gas_tank = True


def draw_network_status(hour):
    G = nx.DiGraph()

    # Nodes
    G.add_node("Gas", label="Gas Main")
    G.add_node("GasTank", label="Gas Tank")
    for i in range(NUM_LINES):
        G.add_node(f"L{i}", label=f"CHP L{i}")
        G.add_node(f"RMU{i}", label=f"RMU{i}")
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
    G.add_edge("SWBD A", "Datacenter")
    G.add_edge("SWBD B", "Datacenter")

    def is_operational(col):
        return col != 'red' and col != 'grey'

    if hour < len(interactive_ps.history):
        online_lines, power_output = interactive_ps.history[hour]
    else:
        online_lines = sum(1 for s in interactive_ps.line_states.values() if s)
        power_output = online_lines * CHP_SIZE_MW

    if hasattr(interactive_ps, "chp_outputs_history") and hour < len(interactive_ps.chp_outputs_history):
        chp_outputs_at_hour = interactive_ps.chp_outputs_history[hour]
    elif hasattr(interactive_ps, "chp_outputs"):
        chp_outputs_at_hour = interactive_ps.chp_outputs
    else:
        chp_outputs_at_hour = {}

    cmap = plt.cm.Greens
    node_color_map = {}

    node_color_map["Gas"] = 'green' if interactive_ps.gas_main else 'red'
    # Updated gas tank coloring logic
    if interactive_ps.gas_main:
        node_color_map["GasTank"] = 'grey'
        gas_tank_status_string = "Standby"
    else:
        if interactive_ps.gas_tank:
            node_color_map["GasTank"] = 'green'
            gas_tank_status_string = "Active"
        else:
            node_color_map["GasTank"] = 'red'
            gas_tank_status_string = "Failed"

    for i in range(NUM_LINES):
        status = interactive_ps.line_status_log[i][hour] if i in interactive_ps.line_status_log and hour < len(interactive_ps.line_status_log[i]) else (1 if interactive_ps.line_states.get(i, True) else 0)
        line_node = f"L{i}"
        rmu_node = f"RMU{i}"

        if status == 0:
            node_color_map[line_node] = 'red'
            node_color_map[rmu_node] = 'red'
        else:
            line_output = chp_outputs_at_hour.get(i, 0.0)
            if line_output == 0.0:
                if online_lines >= MIN_LINES_REQUIRED:
                    line_output = TARGET_LOAD_MW / max(online_lines, 1)
                else:
                    line_output = CHP_SIZE_MW
            load_fraction = min(max(line_output / CHP_SIZE_MW, 0.0), 1.0)
            # Enhanced gradient: strong contrast at high load (90–100%)
            gradient_map = [
                (0.0, 0.05),   # very light green (all CHPs on, low load)
                (0.25, 0.18),  # light green
                (0.5, 0.25),   # medium green
                (0.75, 0.55),  # darker green for rising load
                (0.9, 0.75),   # strong darkening begins
                (1.0, 0.98)    # very dark, nearly forest green at full load
            ]
            # Interpolate colormap intensity
            for threshold, cmap_val in gradient_map:
                if load_fraction <= threshold:
                    color_val = cmap(cmap_val)
                    break
            else:
                color_val = cmap(0.9)
            node_color_map[line_node] = mcolors.to_hex(color_val)
            node_color_map[rmu_node] = mcolors.to_hex(color_val)

    swbd_a_up = interactive_ps.swbd_states.get("A", True)
    swbd_b_up = interactive_ps.swbd_states.get("B", True)
    node_color_map["SWBD A"] = 'green' if swbd_a_up else 'red'
    node_color_map["SWBD B"] = 'grey' if swbd_a_up and swbd_b_up else ('green' if swbd_b_up else 'red')

    gas_ok = interactive_ps.gas_main or interactive_ps.gas_tank
    if (is_operational(node_color_map.get("SWBD A", 'grey')) or is_operational(node_color_map.get("SWBD B", 'grey'))) and gas_ok:
        node_color_map["Datacenter"] = 'green'
    else:
        node_color_map["Datacenter"] = 'red'

    node_colors = [node_color_map.get(n, 'grey') for n in G.nodes()]
    edge_colors = []
    for u, v in G.edges():
        u_col = node_color_map.get(u, 'grey')
        v_col = node_color_map.get(v, 'grey')
        if u == "Gas":
            edge_colors.append('green' if interactive_ps.gas_main else 'grey')
        elif u == "GasTank":
            edge_colors.append('grey' if interactive_ps.gas_main else ('green' if interactive_ps.gas_tank else 'red'))
        elif u.startswith("L") and v.startswith("RMU"):
            edge_colors.append('red' if u_col == 'red' else u_col)
        elif u.startswith("RMU") and v in ["SWBD A", "SWBD B"]:
            if u_col == 'red' or v_col == 'red':
                edge_colors.append('red')
            elif is_operational(u_col) and is_operational(v_col):
                edge_colors.append('green')
            else:
                edge_colors.append('grey')
        elif u in ["SWBD A", "SWBD B"] and v == "Datacenter":
            edge_colors.append('green' if node_color_map.get(u) == 'green' else ('grey' if node_color_map.get(u) == 'grey' else 'red'))
        else:
            edge_colors.append('red' if u_col == 'red' or v_col == 'red' else ('green' if is_operational(u_col) and is_operational(v_col) else 'grey'))

    plt.clf()
    if hour < len(interactive_ps.history):
        _, power_output = interactive_ps.history[hour]
    alert_text = f"\n⚠️ Under {TARGET_LOAD_MW:.1f} MW Target!" if power_output < TARGET_LOAD_MW else ""
    plt.title(f"System Status at Hour {hour}\nPower Output: {power_output:.1f} MW{alert_text}\nGreen=Operational, Red=Failed")

    pos = {f"L{i}": (1, NUM_LINES/2 - i) for i in range(NUM_LINES)}
    pos.update({f"RMU{i}": (2, NUM_LINES/2 - i) for i in range(NUM_LINES)})
    pos.update({"Gas": (0, 0), "GasTank": (0, -1), "SWBD A": (3, 1), "SWBD B": (3, -1), "Datacenter": (4, 0)})

    nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'),
            node_color=node_colors, edge_color=edge_colors, node_size=900, font_size=8,
            font_weight='bold', arrowsize=15)

    # -------------------------
    # Legend: CHP load fraction -> colour explanation
    # -------------------------
    legend_levels = [0.20, 0.45, 0.70, 0.95]
    legend_labels = [
        "<= 20% of CHP rating (low output)",
        "20% - 45% of CHP rating (partial output)",
        "45% - 70% of CHP rating (high output)",
        "> 70% of CHP rating (near full)"
    ]

    legend_patches = []
    for frac, lab in zip(legend_levels, legend_labels):
        color_hex = mcolors.to_hex(cmap(0.18 + 0.77 * frac))
        legend_patches.append(Patch(facecolor=color_hex, edgecolor='k', label=lab))

    legend_patches.append(Patch(facecolor='red', edgecolor='k', label='Failed'))
    legend_patches.append(Patch(facecolor='grey', edgecolor='k', label='Standby / Unused'))
    legend_patches.append(Patch(facecolor=mcolors.to_hex(cmap(0.18 + 0.77 * 1.0)), edgecolor='k', label='Active (sufficient)'))

    plt.legend(handles=legend_patches, loc='upper left', bbox_to_anchor=(1.01, 0.95), borderaxespad=0.)

    plt.text(pos["GasTank"][0] + 0.1, pos["GasTank"][1], f"🛢️ Gas Tank Status: {gas_tank_status_string}", fontsize=10, ha="left")
    plt.pause(0.5)

# ----------------------------------
# STREAMLIT APP
# ----------------------------------
def main():
    st.title("CHP Microgrid Availability Designer (DES-based)")
    st.markdown(
        "Design a CHP-based microgrid to meet a target load with a target availability using the same N+N shared architecture. "
        "The model auto-sizes the number of engines and runs a discrete-event simulation (DES) to validate performance."
    )

    # Sidebar inputs
    st.sidebar.header("Design Inputs")

    base_load = 45.0
    target_load = st.sidebar.number_input(
        "Target Load (MW)",
        min_value=5.0,
        max_value=500.0,
        value=base_load,
        step=5.0,
    )

    target_avail_pct = st.sidebar.number_input(
        "Target Availability (% for meeting target load)",
        min_value=90.0,
        max_value=99.9999,
        value=99.999,
        step=0.001,
        format="%.6f",
    )

    sim_years = st.sidebar.number_input(
        "Simulation Duration (years)",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
    )

    uploaded_profile = st.sidebar.file_uploader(
        "Optional: Load profile CSV with 'load_mw' column (uses max load for sizing)",
        type=["csv"],
    )

    load_profile = None
    if uploaded_profile is not None:
        try:
            df = pd.read_csv(uploaded_profile)
            if "load_mw" in df.columns:
                load_profile = df["load_mw"].astype(float).tolist()
                if len(load_profile) > 0:
                    target_load = max(load_profile)
                    st.sidebar.success(
                        f"Loaded load profile. Using max load {target_load:.1f} MW for sizing."
                    )
        except Exception as e:
            st.sidebar.error(f"Error reading load profile: {e}")

    if st.sidebar.button("Run Design & Simulation"):
        target_avail = target_avail_pct / 100.0

        # Set global target load for use in DES classes
        global TARGET_LOAD_MW
        TARGET_LOAD_MW = target_load

        # Size the fleet (k-out-of-n shared redundancy)
        k, n = size_chp_fleet(target_load, target_avail)

        # Apply sizing to global parameters for the DES classes
        global NUM_LINES, MIN_LINES_REQUIRED, SIM_HOURS
        NUM_LINES = n
        MIN_LINES_REQUIRED = k
        SIM_HOURS = int(8760 * sim_years)

        # -----------------------------
        # Static availability simulation
        # -----------------------------
        env = simpy.Environment()
        ps = PowerSystem(env)
        env.run(until=SIM_HOURS)

        availability = (SIM_HOURS - ps.outage_hours) / SIM_HOURS * 100

        # Summary
        st.subheader("Design Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Target Load (MW)", f"{target_load:.1f}")
            st.metric("CHP Size (MW)", "2.5")
            st.metric("Min CHPs Required (k)", f"{k}")
        with col2:
            st.metric("Installed CHPs (n)", f"{n}")
            st.metric("Simulated Availability (%)", f"{availability:.6f}")
            st.metric("Outage Hours (< Target Load)", f"{ps.outage_hours}")

        # Time series plot: CHPs online vs required
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(ps.history, label="CHP Lines Online")
        ax.axhline(MIN_LINES_REQUIRED, color="red", linestyle="--", label=f"Min Required ({MIN_LINES_REQUIRED})")
        ax.set_title("CHP Lines Online Over Time (DES simulation)")
        ax.set_xlabel("Hour")
        ax.set_ylabel("Lines Online")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        # -----------------------------
        # DES network visualization snapshot
        # -----------------------------
        st.subheader("DES Network Snapshot (N+N Architecture)")

        # Initialize interactive DES with same parameters
        env2 = simpy.Environment()
        global interactive_ps
        interactive_ps = InteractivePowerSystem(env2)

        snapshot_hour = min(SIM_HOURS, 8760)
        env2.run(until=snapshot_hour)

        # Ensure outputs history exists for coloring
        if not hasattr(interactive_ps, "chp_outputs_history"):
            interactive_ps.chp_outputs_history = []
        if hasattr(interactive_ps, "chp_outputs"):
            interactive_ps.chp_outputs_history.append(dict(interactive_ps.chp_outputs))
        else:
            interactive_ps.chp_outputs_history.append({})

        # Draw snapshot
        draw_network_status(snapshot_hour - 1)
        st.pyplot(plt.gcf())

        st.caption(
            "Snapshot shows gas supply, CHPs, RMUs, switchboards, and datacenter status under the simulated conditions. "
            "Greens indicate operational paths; reds indicate failures."
        )

if __name__ == "__main__":
    main()