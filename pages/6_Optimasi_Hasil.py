# """
# pages/6_Optimasi_Hasil.py
# =============================
# TODO: Implementasi halaman "Optimasi & Hasil".
# PIC: (isi nama anggota tim di sini)
# """

# import streamlit as st

# st.set_page_config(page_title="Optimasi & Hasil", layout="wide")
# st.title("Optimasi & Hasil")
# st.info("Halaman ini belum diimplementasikan.")

# pages/6_Optimasi_Hasil.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.auth import require_login, render_user_info

require_login()
render_user_info(sidebar=True)

st.title("⚙️ Optimasi & Hasil")

# --- Ambil data: pakai dummy dulu, nanti ganti dengan hasil PSO sungguhan ---
try:
    from engine.pso_engine import get_last_result  # akan ada setelah Valen selesai
    result = get_last_result()
    USE_DUMMY = False
except ImportError:
    from utils.dummy_data import (
        get_dummy_convergence, get_dummy_velocity_breakdown,
        get_dummy_cities, get_dummy_astar_path
    )
    USE_DUMMY = True

if USE_DUMMY:
    st.warning("⚠️ Menampilkan data dummy — PSO engine belum terhubung.", icon="🔧")

st.header("E.1 — Visualisasi Algoritma")

# ── 1. Grafik Konvergensi PSO ──────────────────────────────────────────────
st.subheader("📈 Grafik Konvergensi PSO")
conv_data = get_dummy_convergence() if USE_DUMMY else result["convergence"]
df_conv = pd.DataFrame(conv_data)

fig_conv = go.Figure()
fig_conv.add_trace(go.Scatter(
    x=df_conv["iterasi"], y=df_conv["gbest"],
    mode="lines+markers", name="Gbest",
    line=dict(color="#1f77b4", width=2),
    marker=dict(size=4),
))
fig_conv.update_layout(
    xaxis_title="Iterasi", yaxis_title="Profit Gbest (Rp)",
    height=350, margin=dict(t=30, b=30),
    hovermode="x unified",
)
st.plotly_chart(fig_conv, use_container_width=True)

# ── 2. PSO Velocity Breakdown ──────────────────────────────────────────────
st.subheader("📊 PSO Velocity Breakdown")
vel_data = get_dummy_velocity_breakdown() if USE_DUMMY else result["velocity"]
df_vel = pd.DataFrame(vel_data)

iter_selected = st.slider(
    "Pilih iterasi:", min_value=1,
    max_value=len(df_vel), value=1, step=1
)
row = df_vel[df_vel["iterasi"] == iter_selected].iloc[0]

fig_vel = go.Figure(go.Bar(
    x=["Inersia (w·v)", "Kognitif (C1·r1·(Pbest−x))", "Sosial (C2·r2·(Gbest−x))"],
    y=[row["inersia"], row["kognitif"], row["sosial"]],
    marker_color=["#2196F3", "#4CAF50", "#FF9800"],
    text=[f"{v:.3f}" for v in [row["inersia"], row["kognitif"], row["sosial"]]],
    textposition="auto",
))
fig_vel.update_layout(
    yaxis_title="Kontribusi Komponen Velocity",
    height=320, margin=dict(t=20, b=20),
)
st.plotly_chart(fig_vel, use_container_width=True)
st.caption(f"Formula: v = w·v + C1·r1·(Pbest−x) + C2·r2·(Gbest−x) | Iterasi {iter_selected}")

# ── 3. Peta A* ─────────────────────────────────────────────────────────────
st.subheader("🗺️ Peta A* — Jalur Rute")
cities = get_dummy_cities() if USE_DUMMY else result["cities"]
astar  = get_dummy_astar_path() if USE_DUMMY else result["astar_path"]

df_cities   = pd.DataFrame(cities)
path_cities = {c["nama"]: c for c in cities}

df_depot = df_cities[df_cities["is_depot"] == True]
df_kota  = df_cities[df_cities["is_depot"] == False]

fig_map = go.Figure()

# Layer 1: Kota biasa — satu trace untuk semua sekaligus
fig_map.add_trace(go.Scatter(
    x=df_kota["lon"].tolist(),
    y=df_kota["lat"].tolist(),
    mode="markers+text",
    name="Kota",
    marker=dict(size=12, color="#78909C", symbol="circle",
                line=dict(width=1.5, color="white")),
    text=df_kota["nama"].tolist(),
    textposition="top center",
    textfont=dict(size=11),
    hovertemplate="<b>%{text}</b><br>lat: %{y:.4f}<br>lon: %{x:.4f}<extra></extra>",
))

# Layer 2: Depot — satu trace untuk semua sekaligus
fig_map.add_trace(go.Scatter(
    x=df_depot["lon"].tolist(),
    y=df_depot["lat"].tolist(),
    mode="markers+text",
    name="Depot",
    marker=dict(size=18, color="#E91E63", symbol="star",
                line=dict(width=1.5, color="white")),
    text=df_depot["nama"].tolist(),
    textposition="top center",
    textfont=dict(size=12, color="#E91E63"),
    hovertemplate="<b>🏭 %{text}</b><br>lat: %{y:.4f}<br>lon: %{x:.4f}<extra></extra>",
))

# Layer 3: Garis jalur A* — satu trace semua titik sekaligus
path_lons = [path_cities[n]["lon"] for n in astar["path"]]
path_lats = [path_cities[n]["lat"] for n in astar["path"]]
fig_map.add_trace(go.Scatter(
    x=path_lons, y=path_lats,
    mode="lines+markers",
    name="Jalur A*",
    line=dict(color="#F44336", width=3),
    marker=dict(size=8, color="#F44336"),
    hoverinfo="skip",
))

# Hitung range axis otomatis + padding supaya semua titik kelihatan
all_lon = df_cities["lon"].tolist()
all_lat = df_cities["lat"].tolist()
lon_pad = (max(all_lon) - min(all_lon)) * 0.12
lat_pad = (max(all_lat) - min(all_lat)) * 0.20  # lebih besar untuk label teks di atas

fig_map.update_layout(
    height=500,
    margin=dict(t=20, b=40, l=80, r=20),
    plot_bgcolor="#1e2130",   # gelap, cocok dengan tema Streamlit dark
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        font=dict(size=12),
    ),
    xaxis=dict(
        title="Longitude",
        range=[min(all_lon) - lon_pad, max(all_lon) + lon_pad],
        showgrid=True, gridcolor="#2d3250",
        zeroline=False, color="#aaaaaa",
    ),
    yaxis=dict(
        title="Latitude",
        range=[min(all_lat) - lat_pad, max(all_lat) + lat_pad],
        showgrid=True, gridcolor="#2d3250",
        zeroline=False, color="#aaaaaa",
    ),
    font=dict(color="#dddddd"),
)

st.plotly_chart(fig_map, use_container_width=True)
st.caption(f"🔴 Jalur A*: {' → '.join(astar['path'])}  |  ⭐ = Depot  |  ● = Kota")