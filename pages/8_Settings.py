# pages/8_Settings.py — admin only
import streamlit as st

from utils.auth import get_current_user
user = get_current_user()
if not user or user.get("role") != "admin":
    st.error("⛔ Halaman ini hanya dapat diakses oleh admin.")
    st.stop()

st.title("⚙️ Pengaturan Sistem")

try:
    from db.database import get_session
    from db.models import Setting
    with get_session() as session:
        all_settings = session.query(Setting).all()
    db_vals = {f"{s.param_group}/{s.param_key}": s.param_value for s in all_settings}
except Exception:
    db_vals = {}
    st.info("DB belum terhubung — perubahan belum bisa disimpan.", icon="ℹ️")

# ── Parameter PSO ───────────────────────────────────────────────────────────
st.subheader("🧠 Parameter PSO")
with st.form("form_pso"):
    c1, c2 = st.columns(2)
    n_particles  = c1.number_input("Jumlah Partikel",    value=int(db_vals.get("pso/n_partikel", 30)),   min_value=5)
    max_iter     = c2.number_input("Maks Iterasi",        value=int(db_vals.get("pso/n_iterasi", 100)),    min_value=10)
    w_max        = c1.number_input("W_MAX (Inersia Max)", value=float(db_vals.get("pso/w_max", 0.9)),     step=0.05, format="%.2f")
    w_min        = c2.number_input("W_MIN (Inersia Min)", value=float(db_vals.get("pso/w_min", 0.4)),     step=0.05, format="%.2f")
    c1_val       = c1.number_input("C1 (Kognitif)",       value=float(db_vals.get("pso/c1", 1.5)),        step=0.1,  format="%.1f")
    c2_val       = c2.number_input("C2 (Sosial)",         value=float(db_vals.get("pso/c2", 1.5)),        step=0.1,  format="%.1f")
    early_stop   = c1.number_input("Early Stop Threshold",value=int(db_vals.get("pso/early_stop_iter", 20)),   min_value=1)
    base_seed    = c2.number_input("Base Seed",            value=int(db_vals.get("pso/base_seed", 42)))

    if st.form_submit_button("💾 Simpan Parameter PSO", type="primary"):
        _save_settings("pso", {
            "n_partikel":      n_particles,
            "n_iterasi":       max_iter,
            "early_stop_iter": early_stop,
            "w_max": w_max, "w_min": w_min,
            "c1": c1_val, "c2": c2_val,
            "base_seed": base_seed,
        })
        st.success("Parameter PSO berhasil disimpan.")

# ── Parameter Operasional ───────────────────────────────────────────────────
st.subheader("🚛 Parameter Operasional")
with st.form("form_ops"):
    c1, c2 = st.columns(2)
    harga_solar   = c1.number_input("Harga Solar (Rp/liter)",   value=float(db_vals.get("ops/harga_solar", 6500)),   step=100.0)
    bbm_base      = c2.number_input("Konsumsi BBM (liter/km)",  value=float(db_vals.get("ops/bbm_base", 0.35)),     step=0.01, format="%.2f")
    tarif_dasar   = c1.number_input("Tarif Dasar (Rp/kg·km)",   value=float(db_vals.get("ops/tarif_dasar", 150)),   step=10.0)
    max_berat     = c2.number_input("Kapasitas Berat Default (kg)", value=float(db_vals.get("ops/max_berat", 2000)), step=50.0)

    if st.form_submit_button("💾 Simpan Parameter Operasional", type="primary"):
        _save_settings("ops", {
            "harga_solar": harga_solar, "bbm_base": bbm_base,
            "tarif_dasar": tarif_dasar, "max_berat": max_berat,
        })
        st.success("Parameter operasional berhasil disimpan.")


def _save_settings(group: str, params: dict):
    """Helper: simpan/update baris settings ke DB."""
    try:
        from db.database import get_session
        from db.models import Setting
        with get_session() as session:
            for key, val in params.items():
                row = session.query(Setting).filter_by(
                    param_group=group, param_key=key).first()
                if row:
                    row.param_value = str(val)
                else:
                    session.add(Setting(param_group=group, param_key=key, param_value=str(val)))
    except Exception as e:
        st.error(f"Gagal simpan ke DB: {e}")