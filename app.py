"""
app.py
=======
Entry point aplikasi XKargo.
Halaman utama menampilkan Dashboard setelah login.

Untuk sekarang: Dashboard dasar + test koneksi database.
Login akan diimplementasi oleh Richelle di 0_Login.py
"""

import streamlit as st
from utils.auth import is_authenticated, get_current_user, logout

st.set_page_config(page_title="XKargo", page_icon="🚚", layout="wide")

# Handle logout SEBELUM halaman apapun dirender
if st.session_state.get("do_logout"):
    logout()
    del st.session_state["do_logout"]
    st.rerun()

if not is_authenticated():
    pg = st.navigation(
        [st.Page("pages/0_Login.py", title="Login", icon="🔐")],
        position="hidden",
    )
else:
    user = get_current_user()
    st.sidebar.markdown(f"👤 **{user['username']}** `{user['role']}`")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state["do_logout"] = True
        st.rerun()

    pg = st.navigation([
        st.Page("app_dashboard.py",            title="Dashboard",        icon="📊"),
        st.Page("pages/1_Master_Data_Kota.py", title="Master Data Kota", icon="🏙️"),
        st.Page("pages/2_Master_Data_Truk.py", title="Master Data Truk", icon="🚛"),
        st.Page("pages/3_Database_Barang.py",  title="Database Barang",  icon="📦"),
        st.Page("pages/4_Depot.py",            title="Depot",            icon="🏭"),
        st.Page("pages/5_Input_Pengiriman.py", title="Input Pengiriman", icon="📝"),
        st.Page("pages/6_Optimasi_Hasil.py",   title="Optimasi Hasil",   icon="⚙️"),
        st.Page("pages/7_Riwayat_Laporan.py",  title="Riwayat Laporan",  icon="📋"),
        st.Page("pages/8_Settings.py",         title="Settings",         icon="🔧"),
    ])

pg.run()