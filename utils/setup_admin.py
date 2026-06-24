"""
utils/setup_admin.py
======================
Script SEKALI JALAN untuk membuat atau mereset password akun admin
di tabel `users`. Jalankan dari terminal, bukan dari Streamlit.

Cara pakai:
    python utils/setup_admin.py
"""

import getpass
import sys
import os

# Tambah root proyek ke path supaya bisa import db/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_session, test_connection
from db.models import User
from utils.auth import hash_password


def main():
    print("=== XKargo — Setup Password Admin ===\n")

    if not test_connection():
        print("✗ Gagal konek ke database. Pastikan XAMPP (MySQL) sudah running.")
        sys.exit(1)

    username = input("Username admin (default: admin): ").strip() or "admin"
    password = getpass.getpass("Password baru: ")

    if len(password) < 6:
        print("✗ Password minimal 6 karakter.")
        sys.exit(1)

    confirm = getpass.getpass("Konfirmasi password: ")
    if password != confirm:
        print("✗ Password tidak cocok.")
        sys.exit(1)

    hashed = hash_password(password)

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            user.password_hash = hashed
            print(f"\n✓ Password untuk user '{username}' berhasil diperbarui.")
        else:
            new_user = User(username=username, password_hash=hashed, role="admin")
            session.add(new_user)
            print(f"\n✓ User admin '{username}' berhasil dibuat.")
        print("  Sekarang bisa login lewat halaman Login Streamlit.")


if __name__ == "__main__":
    main()