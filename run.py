import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. SETUP ---
st.set_page_config(page_title="Mission Control: Data Integrity", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #3e445e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA & MATH ENGINE ---
def calculate_mission_state(error_pct):
    t_range = np.linspace(0, 10, 100)
    t_snapshot = 7.5 # We'll look at the math for this specific point in time
    r_base = 7000
    omega = 0.5
    
    # Path Math
    x_t = r_base * np.cos(omega * t_range)
    y_t = r_base * np.sin(omega * t_range)
    z_t = t_range * 100
    
    # Error Math
    r_err = r_base * (1 + error_pct / 100)
    x_e = r_err * np.cos(omega * t_range)
    y_e = r_err * np.sin(omega * t_range)
    z_e = z_t
    
    # Snapshot values for the Live Equation
    snap_xt = r_base * np.cos(omega * t_snapshot)
    snap_yt = r_base * np.sin(omega * t_snapshot)
    snap_xe = r_err * np.cos(omega * t_snapshot)
    snap_ye = r_err * np.sin(omega * t_snapshot)
    
    return (x_t, y_t, z_t), (x_e, y_e, z_e), (snap_xt, snap_yt, snap_xe, snap_ye, r_err)

# --- 3. SIDEBAR ---
st.sidebar.title("Satellite Control")
db_mode = st.sidebar.radio("Database State", ["Normalized (Healthy)", "Unnormalized (Data Anomaly)"])
error_val = 0 if db_mode == "Normalized (Healthy)" else st.sidebar.slider("Anomaly Severity (%)", 5, 50, 20)

paths_t, paths_e, snap = calculate_mission_state(error_val)

# --- 4. TOP METRICS (Live Number Changes) ---
st.title("Satellite Trajectory & Data Integrity")
m1, m2, m3 = st.columns(3)

with m1:
    st.metric("System Radius", f"7000 km", help="Target Radius from Source of Truth")
with m2:
    delta = f"{error_val}%" if error_val > 0 else None
    st.metric("DB Reported Radius", f"{snap[4]:.0f} km", delta=delta, delta_color="inverse")
with m3:
    drift = np.sqrt((snap[0]-snap[2])**2 + (snap[1]-snap[3])**2)
    st.metric("Targeting Drift", f"{drift:.2f} km", delta="CRITICAL" if drift > 500 else "OK")

st.divider()

# --- 5. 3D GRAPH & LIVE MATH ---
col_graph, col_math = st.columns([2, 1])

with col_graph:
    fig = go.Figure()
    # Earth
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(size=15, color='deepskyblue'), name="Earth"))
    # Paths
    fig.add_trace(go.Scatter3d(x=paths_t[0], y=paths_t[1], z=paths_t[2], mode='lines', line=dict(color='#00ff00', width=5), name="Real Path"))
    if error_val > 0:
        fig.add_trace(go.Scatter3d(x=paths_e[0], y=paths_e[1], z=paths_e[2], mode='lines', line=dict(color='#ff4b4b', width=5, dash='dot'), name="Ghost Path"))
    
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, b=0, t=0), height=500, scene_xaxis_title="X (km)")
    st.plotly_chart(fig, use_container_width=True)

with col_math:
    st.subheader(" Equation Resolution")
    st.write("Calculating Position at $T = 7.5s$")
    
    st.write("**Healthy Calculation:**")
    st.latex(rf"X = 7000 \cdot \cos(0.5 \cdot 7.5) = {snap[0]:.2f}")
    
    if error_val > 0:
        st.write("**Anomaly Calculation:**")
        st.latex(rf"X = {snap[4]:.0f} \cdot \cos(0.5 \cdot 7.5) = {snap[2]:.2f}")
        st.error(f"Error Offset: {abs(snap[0]-snap[2]):.2f} km")
    else:
        st.success("Mathematical alignment is 100%")

# --- 6. DATABASE TABLES ---
st.divider()
st.subheader(" Database Inspector")
t1, t2 = st.tabs(["Normalized Tables", "Unnormalized Table"])

with t1:
    c1, c2 = st.columns(2)
    c1.write("**Table: Satellites**")
    c1.table(pd.DataFrame({"ID": [1], "Name": ["Sat-A"], "Radius": [7000]}))
    c2.write("**Table: Telemetry**")
    c2.table(pd.DataFrame({"Ping": [101, 102], "SatID": [1, 1], "Time": ["12:00", "12:01"]}))

with t2:
    st.write("**Table: Master_List (Redundant Data)**")
    df_un = pd.DataFrame({
        "Ping": [101, 102],
        "Name": ["Sat-A", "Sat-A"],
        "Radius": [7000, 7000 * (1+error_val/100)],
        "Log": ["Verified", "UPDATE FAILED (Anomaly)"]
    })
    st.table(df_un)