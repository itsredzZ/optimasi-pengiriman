"""
pages/0_Login.py
=================
Halaman Login XKargo.
PIC: Person 4 (Richelle)
"""

import streamlit as st
from utils.auth import login_user, is_authenticated

st.set_page_config(
    page_title="XKargo — Login",
    page_icon="🚚",
    layout="centered",
)

# Kalau sudah login, langsung ke Dashboard
if is_authenticated():
    st.rerun()

# -----------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------
st.markdown("", unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    st.markdown("## 🚚 XKargo")
    st.markdown("##### Sistem Optimasi Distribusi Barang Multi-Depot")
    st.divider()

    with st.form("form_login", clear_on_submit=False):
        username  = st.text_input("Username", placeholder="Masukkan username")
        password  = st.text_input("Password", type="password", placeholder="Masukkan password")
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

    if submitted:
        if not username or not password:
            st.warning("Username dan password tidak boleh kosong.")
        else:
            with st.spinner("Memverifikasi..."):
                user = login_user(username, password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["user"] = user
                st.success(f"Selamat datang, {user['username']}!")
                st.rerun()
            else:
                st.error("Username atau password salah.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("XKargo © 2026 — Universitas Kristen Petra Surabaya")