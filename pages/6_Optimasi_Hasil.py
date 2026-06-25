from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db.database import get_session
from db.models import (CarryoverItem, City, Item, RelocationLog, Setting, SimulationResult, Truck)
from engine.config import load_operational_params, load_pso_params
from engine.data_models import truck_to_state
from engine.graph_builder import build_graph_from_db
from engine.item_assignment import assign_trucks_to_items
from engine.orchestrator import run_daily_optimization
from engine.relocation import putuskan_relokasi_truk
from utils.auth import render_user_info, require_login

require_login()
st.set_page_config(page_title="XKargo — Optimasi & Hasil", layout="wide")
st.title("🚀 Optimasi & Hasil Pengiriman")

# ═══════════════════════════════════════════════════════════════════════
# ADAPTER FUNCTIONS (Person 1)
# Konversi format engine → format yang dipakai chart Person 4
# ═══════════════════════════════════════════════════════════════════════

def _conv_data(gbest_curve: list) -> list[dict]:
    """gbest_curve [float,...] → [{iterasi, gbest}, ...]"""
    return [{"iterasi": i, "gbest": float(v)} for i, v in enumerate(gbest_curve)]


def _cities_map_data(cities: list, coords: dict, depot_names: list) -> list[dict]:
    """Bangun list kota untuk peta Plotly Person 4."""
    return [
        {
            "nama":     name,
            "lat":      coords[name][0],
            "lon":      coords[name][1],
            "is_depot": name in depot_names,
        }
        for name in cities if name in coords
    ]


def _route_paths(best_routes: dict) -> dict[int, list[str]]:
    """Ekstrak rute lengkap per truk (depot → kota tujuan → depot kembali)."""
    paths = {}
    for truck_id, ri in best_routes.items():
        paths[truck_id] = [ri["depot"]] + ri["rute"] + [ri["depot_kembali"]]
    return paths


# ═══════════════════════════════════════════════════════════════════════
# DUMMY DATA (Person 4) — dipakai saat PSO belum dijalankan
# ═══════════════════════════════════════════════════════════════════════

def _dummy_convergence():
    import math
    return [{"iterasi": i, "gbest": 2_000_000 * (1 - math.exp(-0.15 * i)) + 500_000}
            for i in range(30)]


def _dummy_velocity():
    import random, math
    random.seed(7)
    rows = []
    for i in range(1, 30):
        decay = math.exp(-0.05 * i)
        rows.append({
            "iterasi":  i,
            "inersia":  round(0.5 * decay + random.uniform(0, 0.1), 4),
            "kognitif": round(0.3 * decay + random.uniform(0, 0.15), 4),
            "sosial":   round(0.4 + random.uniform(0, 0.2), 4),
        })
    return rows


def _dummy_cities():
    return [
        {"nama": "Surabaya", "lat": -7.2575, "lon": 112.7521, "is_depot": True},
        {"nama": "Malang",   "lat": -7.9797, "lon": 112.6304, "is_depot": True},
        {"nama": "Kediri",   "lat": -7.8168, "lon": 111.9668, "is_depot": True},
        {"nama": "Madiun",   "lat": -7.6298, "lon": 111.5239, "is_depot": True},
        {"nama": "Jember",   "lat": -8.1845, "lon": 113.6680, "is_depot": True},
        {"nama": "Tuban",    "lat": -6.8997, "lon": 112.0508, "is_depot": True},
    ]


def _dummy_routes():
    return {
        1: ["Surabaya", "Kediri", "Madiun", "Surabaya"],
        2: ["Malang", "Jember", "Malang"],
    }


# ═══════════════════════════════════════════════════════════════════════
# LOAD DB DATA (Person 1)
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def _load_db_data():
    with get_session() as session:
        pso_settings = session.query(Setting).filter_by(param_group="pso").all()
        op_settings  = session.query(Setting).filter_by(param_group="operasional").all()
        pso_params   = load_pso_params(pso_settings)
        op_params    = load_operational_params(op_settings)

        cities, city_idx, adj, coords, depot_names = build_graph_from_db(session)

        truck_rows   = session.query(Truck).filter_by(is_active=True).all()
        trucks_state = [truck_to_state(t) for t in truck_rows]

    return pso_params, op_params, cities, city_idx, adj, coords, depot_names, trucks_state


try:
    pso_params, op_params, cities, city_idx, adj, coords, depot_names, trucks_state = _load_db_data()
except Exception as e:
    st.error(f"Gagal memuat data dari database: {e}")
    st.info("Pastikan XAMPP (MySQL) sudah running dan schema.sql sudah di-import.")
    st.stop()

if not trucks_state:
    st.error("Tidak ada truk aktif. Tambahkan truk dulu di Master Data > Truk.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════
# RINGKASAN ITEM HARI INI (Person 1)
# ═══════════════════════════════════════════════════════════════════════

raw_items = st.session_state.get("items_hari_ini")

if raw_items is None:
    st.warning(
        "⚠️ Belum ada data pesanan dari halaman Input Pengiriman. "
        "Menampilkan **data dummy** untuk testing."
    )
    from engine.dev_data_generator import generate_dummy_items
    raw_items = generate_dummy_items(trucks_state, depot_names, cities, n_min=8, n_max=12, seed=42)

items_siap, items_notruk = assign_trucks_to_items(raw_items, trucks_state)
n_co = sum(1 for it in raw_items if it.get("is_carryover"))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Item",                     len(raw_items))
col2.metric("Carry-over (prioritas)",          n_co)
col3.metric("Siap dioptimasi",                 len(items_siap))
col4.metric("Auto carry-over (depot kosong)",  len(items_notruk))

if items_notruk:
    with st.expander(f"⚠️ {len(items_notruk)} item auto carry-over", expanded=False):
        st.dataframe(
            pd.DataFrame([{"Nama": it["nama"], "Depot Asal": it["kota_asal"],
                           "Tujuan": it["kota_tujuan"]} for it in items_notruk]),
            use_container_width=True, hide_index=True,
        )

if not items_siap:
    st.error("Tidak ada item yang bisa dioptimasi.")
    st.stop()

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# TOMBOL OPTIMASI (Person 1)
# ═══════════════════════════════════════════════════════════════════════

if "hasil_optimasi" not in st.session_state:
    st.session_state["hasil_optimasi"] = None

col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_clicked = st.button(
        "🚀 Optimalkan Pengiriman Sekarang",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state["hasil_optimasi"] is not None),
    )
with col_info:
    if st.session_state["hasil_optimasi"] is not None:
        st.success("Optimasi selesai. Tinjau hasil di bawah, lalu klik **Selesai & Simpan**.")
    else:
        st.info(
            f"PSO: {pso_params.n_iterasi} iterasi × {pso_params.n_partikel} partikel. "
            "Estimasi: 5–30 detik."
        )

if run_clicked:
    progress_bar = st.progress(0, text="Menginisialisasi PSO...")

    def _progress_cb(it, n_iter, gbest):
        progress_bar.progress(
            int((it / n_iter) * 100),
            text=f"Iterasi {it}/{n_iter} — Gbest: Rp {gbest:,.0f}",
        )

    with st.spinner("PSO + A* + Guillotine 3D Bin Packing sedang berjalan..."):
        hasil = run_daily_optimization(
            items=items_siap, trucks=trucks_state,
            adj=adj, city_idx=city_idx, cities=cities, coords=coords,
            depot_names=depot_names,
            pso_params=pso_params, op_params=op_params,
            progress_callback=_progress_cb,
        )

    progress_bar.progress(100, text="Selesai!")
    st.session_state["hasil_optimasi"]        = hasil
    st.session_state["items_notruk_hari_ini"] = items_notruk
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# Resolve data: pakai hasil nyata kalau ada, fallback ke dummy (Person 4)
# ═══════════════════════════════════════════════════════════════════════

hasil = st.session_state.get("hasil_optimasi")

USE_DUMMY = (hasil is None)
if USE_DUMMY:
    # Visualisasi tetap tampil dengan dummy supaya Person 4 bisa test
    # chart-nya tanpa harus tunggu PSO selesai
    conv_data   = _dummy_convergence()
    vel_data    = _dummy_velocity()
    cities_data = _dummy_cities()
    route_paths = _dummy_routes()
else:
    conv_data   = _conv_data(hasil["gbest_curve"])
    vel_data    = hasil["velocity_breakdown"]          # sudah cocok formatnya
    cities_data = _cities_map_data(cities, coords, depot_names)
    route_paths = _route_paths(hasil["best_routes"])

# ═══════════════════════════════════════════════════════════════════════
# E.1 — VISUALISASI ALGORITMA (Person 4)
# ═══════════════════════════════════════════════════════════════════════

st.header("E.1 — Visualisasi Algoritma")
if USE_DUMMY:
    st.warning("⚠️ Menampilkan data dummy — klik Optimalkan untuk data nyata.", icon="🔧")

# ── 1. Grafik Konvergensi PSO ──────────────────────────────────────────
st.subheader("📈 Grafik Konvergensi PSO")
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

# ── 2. PSO Velocity Breakdown ──────────────────────────────────────────
st.subheader("📊 PSO Velocity Breakdown")
df_vel = pd.DataFrame(vel_data)

iter_selected = st.slider(
    "Pilih iterasi:",
    min_value=int(df_vel["iterasi"].min()),
    max_value=int(df_vel["iterasi"].max()),
    value=int(df_vel["iterasi"].min()),
    step=1,
)
row = df_vel[df_vel["iterasi"] == iter_selected].iloc[0]

fig_vel = go.Figure(go.Bar(
    x=["Inersia (w·v)", "Kognitif (C1·r1·(Pbest−x))", "Sosial (C2·r2·(Gbest−x))"],
    y=[row["inersia"], row["kognitif"], row["sosial"]],
    marker_color=["#2196F3", "#4CAF50", "#FF9800"],
    text=[f"{v:.4f}" for v in [row["inersia"], row["kognitif"], row["sosial"]]],
    textposition="auto",
))
fig_vel.update_layout(
    yaxis_title="Kontribusi Komponen Velocity",
    height=320, margin=dict(t=20, b=20),
)
st.plotly_chart(fig_vel, use_container_width=True)

# Tampilkan nilai w saat iterasi terpilih jika data nyata tersedia
w_val = row.get("w", None)
w_str = f" | w = {w_val:.3f}" if w_val is not None else ""
st.caption(
    f"Formula: v = w·v + C1·r1·(Pbest−x) + C2·r2·(Gbest−x) "
    f"| Iterasi {iter_selected}{w_str}"
)

# ── 3. Peta Rute Aktif ─────────────────────────────────────────────────
st.subheader("🗺️ Peta Rute Aktif")
df_cities   = pd.DataFrame(cities_data)
city_coord  = {c["nama"]: c for c in cities_data}

df_depot = df_cities[df_cities["is_depot"] == True]
df_kota  = df_cities[df_cities["is_depot"] == False]

ROUTE_COLORS = [
    "#F44336", "#2196F3", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#FF5722", "#607D8B",
]

fig_map = go.Figure()

# Kota biasa
if not df_kota.empty:
    fig_map.add_trace(go.Scatter(
        x=df_kota["lon"].tolist(), y=df_kota["lat"].tolist(),
        mode="markers+text", name="Kota",
        marker=dict(size=12, color="#78909C", symbol="circle",
                    line=dict(width=1.5, color="white")),
        text=df_kota["nama"].tolist(), textposition="top center",
        textfont=dict(size=11),
        hovertemplate="<b>%{text}</b><br>lat: %{y:.4f}<br>lon: %{x:.4f}<extra></extra>",
    ))

# Depot
fig_map.add_trace(go.Scatter(
    x=df_depot["lon"].tolist(), y=df_depot["lat"].tolist(),
    mode="markers+text", name="Depot",
    marker=dict(size=18, color="#E91E63", symbol="star",
                line=dict(width=1.5, color="white")),
    text=df_depot["nama"].tolist(), textposition="top center",
    textfont=dict(size=12, color="#E91E63"),
    hovertemplate="<b>🏭 %{text}</b><br>lat: %{y:.4f}<br>lon: %{x:.4f}<extra></extra>",
))

# Rute tiap truk — masing-masing warna berbeda
truck_map_local = {t.id: t for t in trucks_state}
for idx, (truck_id, path) in enumerate(route_paths.items()):
    color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
    valid_path = [p for p in path if p in city_coord]
    if len(valid_path) < 2:
        continue
    path_lons = [city_coord[n]["lon"] for n in valid_path]
    path_lats = [city_coord[n]["lat"] for n in valid_path]
    truck      = truck_map_local.get(truck_id)
    label      = truck.plate_number if truck else f"Truk #{truck_id}"
    fig_map.add_trace(go.Scatter(
        x=path_lons, y=path_lats,
        mode="lines+markers", name=f"🚚 {label}",
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color),
        hovertemplate=f"<b>{label}</b><br>%{{hovertext}}<extra></extra>",
        hovertext=valid_path,
    ))

all_lon = df_cities["lon"].tolist()
all_lat = df_cities["lat"].tolist()
lon_pad = (max(all_lon) - min(all_lon)) * 0.12
lat_pad = (max(all_lat) - min(all_lat)) * 0.20

fig_map.update_layout(
    height=500,
    margin=dict(t=20, b=40, l=80, r=20),
    plot_bgcolor="#1e2130",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="left", x=0, font=dict(size=12)),
    xaxis=dict(title="Longitude",
               range=[min(all_lon) - lon_pad, max(all_lon) + lon_pad],
               showgrid=True, gridcolor="#2d3250", zeroline=False, color="#aaaaaa"),
    yaxis=dict(title="Latitude",
               range=[min(all_lat) - lat_pad, max(all_lat) + lat_pad],
               showgrid=True, gridcolor="#2d3250", zeroline=False, color="#aaaaaa"),
    font=dict(color="#dddddd"),
)
st.plotly_chart(fig_map, use_container_width=True)
st.caption("⭐ = Depot  |  ● = Kota  |  Tiap warna = rute satu truk")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# E.2 — HASIL OPERASIONAL (Person 1)
# Bagian ini hanya tampil setelah PSO sungguhan selesai
# ═══════════════════════════════════════════════════════════════════════

if hasil is None:
    st.info("Jalankan optimasi di atas untuk melihat hasil operasional.")
    st.stop()

best_routes     = hasil["best_routes"]
carryover_items = hasil["carryover_items"]
truck_akhir     = hasil["truck_depot_akhir"]
truck_map_db    = {t.id: t for t in trucks_state}

st.header("E.2 — Hasil Operasional")

# Alokasi per truk
st.markdown("#### 🚚 Alokasi Per Truk")
if not best_routes:
    st.warning("PSO tidak menghasilkan alokasi. Kemungkinan semua item melebihi kapasitas truk.")
else:
    for truck_id, ri in best_routes.items():
        truck  = truck_map_db.get(truck_id)
        plate  = truck.plate_number if truck else f"Truk #{truck_id}"
        cap_kg = truck.max_weight_kg if truck else 1000
        box_v  = (truck.box_volume / 1_000_000) if truck else 3.38
        vol_m3 = sum(it["volume"] for it in ri["items"]) / 1_000_000

        with st.expander(
            f"🚚 {plate} — {len(ri['items'])} item | "
            f"Rp {ri['tarif']:,.0f} tarif | Rp {ri['biaya_bbm']:,.0f} BBM",
            expanded=False,
        ):
            col_r, col_s = st.columns([2, 1])
            with col_r:
                st.markdown(
                    f"**Rute:** **{ri['depot']}** → "
                    + " → ".join(ri["rute"])
                    + f" → **{ri['depot_kembali']}**"
                )
                st.caption(
                    f"Total jarak: {ri['total_dist']:.1f} km | "
                    f"Konsumsi BBM: {ri['konsumsi_bbm']:.2f} L/km"
                )
            with col_s:
                st.metric("Berat muatan", f"{ri['berat_muatan']:.1f} kg",
                          delta=f"{ri['berat_muatan']/cap_kg*100:.0f}% kap.")
                st.metric("Volume", f"{vol_m3:.3f} m³",
                          delta=f"{vol_m3/box_v*100:.0f}% box")

            st.dataframe(
                pd.DataFrame([{
                    "Nama Barang":  it["nama"],
                    "Tujuan":       it["kota_tujuan"],
                    "Dimensi (cm)": f"{it['panjang']}×{it['lebar']}×{it['tinggi']}",
                    "Berat (kg)":   it["berat_fisik"],
                    "Golongan":     it["kategori"],
                    "Carry-over":   "✓" if it["is_carryover"] else "",
                } for it in ri["items"]]),
                use_container_width=True, hide_index=True,
            )

# Carry-over
all_carryover = carryover_items + st.session_state.get("items_notruk_hari_ini", [])
st.markdown(f"#### ⚠️ Carry-over ({len(all_carryover)} item)")
if not all_carryover:
    st.success("Semua item berhasil dimuat! Tidak ada carry-over hari ini. 🎉")
else:
    ALASAN_LABEL = {
        "overflow_berat":   "Melebihi kapasitas berat truk",
        "overflow_volume":  "Melebihi kapasitas volume truk",
        "guillotine_gagal": "Guillotine 3D packing gagal",
        "depot_tanpa_truk": "Depot asal tidak ada truk",
    }
    st.dataframe(
        pd.DataFrame([{
            "Nama Barang": it["nama"],
            "Depot Asal":  it["kota_asal"],
            "Tujuan":      it["kota_tujuan"],
            "Alasan":      ALASAN_LABEL.get(it.get("alasan_carryover", ""), "Gagal dimuat"),
            "Was CO":      "✓" if it.get("is_carryover") else "",
        } for it in all_carryover]),
        use_container_width=True, hide_index=True,
    )

# Relokasi
st.markdown("#### 🔄 Keputusan Relokasi Truk")
items_besok = {}
for it in all_carryover:
    items_besok.setdefault(it["kota_asal"], []).append(it)

relokasi_decisions = []
if items_besok:
    relokasi_decisions, _ = putuskan_relokasi_truk(
        truck_depot_current=truck_akhir,
        items_by_depot=items_besok,
        adj=adj, city_idx=city_idx, cities=cities, coords=coords,
        cache={}, op_params=op_params, depot_names=depot_names,
    )
    st.dataframe(
        pd.DataFrame([{
            "Truk":             truck_map_db[d["truck_id"]].plate_number
                                if d.get("truck_id") and d["truck_id"] in truck_map_db else "—",
            "Dari":             d.get("dari") or "—",
            "Ke":               d["ke"],
            "Biaya Relokasi":   f"Rp {d['biaya']:,.0f}" if d.get("truck_id") else "—",
            "Est. Tarif Besok": f"Rp {d['estimasi_tarif']:,.0f}",
            "Keputusan":        "✅ Relokasi" if d["relokasi"] else "❌ Carry-over",
            "Alasan":           d["alasan"],
        } for d in relokasi_decisions]),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("Tidak ada carry-over → tidak perlu relokasi truk untuk besok.")

# Ringkasan profit
st.divider()
st.markdown("#### 💰 Ringkasan Profit Hari Ini")
total_tarif    = hasil["total_tarif"]
total_bbm      = hasil["total_bbm"]
biaya_relokasi = sum(
    d["biaya"] for d in relokasi_decisions
    if d.get("relokasi") and d.get("biaya")
)
profit_bersih  = total_tarif - total_bbm - biaya_relokasi

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tarif",      f"Rp {total_tarif:,.0f}")
c2.metric("Biaya BBM",        f"Rp {total_bbm:,.0f}")
c3.metric("Biaya Relokasi",   f"Rp {biaya_relokasi:,.0f}")
c4.metric("💰 Profit Bersih", f"Rp {profit_bersih:,.0f}",
          delta="positif" if profit_bersih >= 0 else "negatif")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# SELESAI & SIMPAN (Person 1)
# ═══════════════════════════════════════════════════════════════════════

if st.session_state.get("sudah_disimpan"):
    st.success("✅ Data hari ini sudah tersimpan. Carry-over tercatat untuk besok.")
    if st.button("🔄 Mulai Hari Baru", type="secondary"):
        for key in ("hasil_optimasi", "items_hari_ini",
                    "items_notruk_hari_ini", "sudah_disimpan"):
            st.session_state.pop(key, None)
        st.rerun()
    st.stop()

col_save, col_ulang = st.columns([1, 3])
with col_save:
    save_clicked = st.button("✅ Selesai & Simpan Hari Ini",
                             type="primary", use_container_width=True)
with col_ulang:
    if st.button("🔁 Ulangi Optimasi", type="secondary"):
        st.session_state.pop("hasil_optimasi", None)
        st.rerun()

if save_clicked:
    today = date.today()
    gbest_curve = hasil["gbest_curve"]
    try:
        with get_session() as session:

            # simulation_results per truk
            for truck_id, ri in best_routes.items():
                rute_kota = [ri["depot"]] + ri["rute"] + [ri["depot_kembali"]]
                vol_m3    = sum(it["volume"] for it in ri["items"]) / 1_000_000
                session.add(SimulationResult(
                    run_date=today, truck_id=truck_id,
                    route_json={"rute": rute_kota,
                                "items_id": [it["id"] for it in ri["items"]]},
                    total_weight_kg=ri["berat_muatan"], total_volume_m3=vol_m3,
                    tariff_total=ri["tarif"], fuel_cost=ri["biaya_bbm"],
                    net_profit=ri["tarif"] - ri["biaya_bbm"],
                    gbest_curve_json={"curve": [float(v) for v in gbest_curve]},
                ))

            # Update status item terkirim
            terkirim_ids = {
                it["id"] for ri in best_routes.values() for it in ri["items"]
            }
            for item_id in terkirim_ids:
                if not str(item_id).startswith("DUMMY_"):
                    db_item = session.query(Item).filter_by(id=int(item_id)).first()
                    if db_item:
                        db_item.status = "terkirim"

            # carryover_items
            _alasan_valid = {
                "overflow_berat", "overflow_volume",
                "guillotine_gagal", "depot_tanpa_truk",
            }
            for it in all_carryover:
                raw    = it.get("alasan_carryover", "guillotine_gagal")
                alasan = raw if raw in _alasan_valid else "guillotine_gagal"
                if not str(it["id"]).startswith("DUMMY_"):
                    db_item = session.query(Item).filter_by(id=int(it["id"])).first()
                    if db_item:
                        db_item.status       = "carryover"
                        db_item.is_carryover = True
                        session.add(CarryoverItem(
                            item_id=db_item.id, carryover_date=today,
                            reason=alasan, resolved=False,
                        ))

            # relocation_logs
            for d in relokasi_decisions:
                if not d.get("truck_id"):
                    continue
                from_city = session.query(City).filter_by(name=d["dari"]).first()
                to_city   = session.query(City).filter_by(name=d["ke"]).first()
                if from_city and to_city:
                    session.add(RelocationLog(
                        run_date=today, truck_id=d["truck_id"],
                        from_depot_id=from_city.id, to_depot_id=to_city.id,
                        relocation_cost=d["biaya"],
                        decision="relokasi" if d["relokasi"] else "carryover",
                    ))

            # Update current_city truk
            for truck_id, kota_baru in truck_akhir.items():
                db_truck = session.query(Truck).filter_by(id=truck_id).first()
                kota_row = session.query(City).filter_by(name=kota_baru).first()
                if db_truck and kota_row:
                    db_truck.current_city_id = kota_row.id

        st.session_state["sudah_disimpan"] = True
        _load_db_data.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Gagal menyimpan ke database: {e}")