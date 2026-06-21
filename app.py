"""
app.py
=======
Entry point aplikasi XKargo. Untuk sekarang baru kerangka dasar untuk
memastikan environment + koneksi database sudah jalan. Halaman Login,
Dashboard, dsb akan dibangun di atas kerangka ini oleh masing-masing PIC.
"""

import streamlit as st

from db.database import test_connection

st.set_page_config(
    page_title="XKargo",
    page_icon="\U0001F69A",
    layout="wide",
)

st.title("XKargo \u2014 Sistem Optimasi Distribusi Barang Multi-Depot")
st.caption("Versi awal kerangka proyek. Halaman Login & Dashboard menyusul.")

st.divider()

st.subheader("Status Setup")

if test_connection():
    st.success("Koneksi ke database MySQL (XAMPP) berhasil.")
else:
    st.error(
        "Belum bisa konek ke database. Pastikan XAMPP (Apache + MySQL) "
        "sudah running, schema.sql sudah di-import, dan file .env sudah dibuat."
    )

st.info(
    "Navigasi ke halaman lain melalui sidebar di kiri "
    "(folder `pages/` akan terisi seiring pengembangan fitur)."
)
