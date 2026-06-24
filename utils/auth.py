"""
utils/auth.py
==============
Modul autentikasi terpusat untuk XKargo.

Cara pakai di setiap halaman yang butuh login:
    from utils.auth import require_login, get_current_user, render_user_info
    require_login()           # taruh di baris pertama halaman
    user = get_current_user() # ambil info user yang sedang login
    render_user_info(sidebar=True) # tampilkan tombol logout di sidebar

Halaman admin-only:
    from utils.auth import require_admin
    require_admin()
"""

import bcrypt
import streamlit as st
from db.database import get_session
from db.models import User


# -----------------------------------------------------------------------
# Password hashing
# -----------------------------------------------------------------------
def hash_password(plain_text: str) -> str:
    """Buat hash bcrypt dari password plain-text. Dipakai saat buat/reset user."""
    return bcrypt.hashpw(plain_text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_text: str, hashed: str) -> bool:
    """Bandingkan password plain-text dengan hash yang tersimpan di DB."""
    try:
        return bcrypt.checkpw(plain_text.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# -----------------------------------------------------------------------
# Login / logout
# -----------------------------------------------------------------------
def login_user(username: str, password: str) -> dict | None:
    """
    Coba login. Mengembalikan dict info user jika berhasil, None jika gagal.
    Dict yang dikembalikan: { 'id', 'username', 'role' }
    """
    try:
        with get_session() as session:
            user = session.query(User).filter_by(username=username).first()
            if user and verify_password(password, user.password_hash):
                return {
                    "id":       user.id,
                    "username": user.username,
                    "role":     user.role,
                }
    except Exception as e:
        st.error(f"Gagal terhubung ke database: {e}")
    return None


def logout() -> None:
    """Hapus sesi login dari session_state."""
    for key in ("authenticated", "user"):
        st.session_state.pop(key, None)


# -----------------------------------------------------------------------
# Session state helpers
# -----------------------------------------------------------------------
def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def get_current_user() -> dict | None:
    """Kembalikan info user yang sedang login, atau None."""
    return st.session_state.get("user")


# -----------------------------------------------------------------------
# Guards — taruh di baris pertama setiap halaman
# -----------------------------------------------------------------------
def require_login() -> None:
    """
    Redirect ke halaman Login jika belum login.
    Taruh di baris PERTAMA setiap halaman (setelah import).
    """
    if not is_authenticated():
        st.switch_page("pages/0_Login.py")


def require_admin() -> None:
    """
    Redirect jika belum login, atau tampilkan error jika bukan admin.
    Pakai untuk halaman Settings (G) yang hanya boleh diakses admin.
    """
    require_login()
    user = get_current_user()
    if user and user.get("role") != "admin":
        st.error("⛔ Halaman ini hanya dapat diakses oleh admin.")
        st.stop()


# -----------------------------------------------------------------------
# UI komponen
# -----------------------------------------------------------------------
def render_user_info(sidebar: bool = True) -> None:
    """Hanya tampilkan info user — logout ditangani di app.py."""
    target = st.sidebar if sidebar else st
    user = get_current_user()
    if user:
        target.markdown(f"👤 **{user['username']}** `{user['role']}`")