"""
test_connection.py
====================
Jalankan file ini SETELAH setup XAMPP + import schema.sql, untuk memastikan
Python bisa konek ke MySQL dan semua tabel ERD sudah terbentuk dengan benar.

Cara jalankan (dari root folder proyek, virtual environment aktif):
    python test_connection.py
"""

from db.database import test_connection, get_session
from db.models import City, Truck, Setting

if __name__ == "__main__":
    print("► Mengecek koneksi ke MySQL (XAMPP) ...")

    if not test_connection():
        print("\n✗ GAGAL konek. Cek:")
        print("  1. Apache & MySQL di XAMPP Control Panel sudah 'Running' (hijau)?")
        print("  2. Database 'xkargo_db' sudah dibuat & schema.sql sudah di-import?")
        print("  3. File .env sudah dibuat (copy dari .env.example) dengan kredensial benar?")
        exit(1)

    print("✓ Koneksi ke database BERHASIL.\n")

    with get_session() as session:
        n_cities  = session.query(City).count()
        n_trucks  = session.query(Truck).count()
        n_settings = session.query(Setting).count()

        print(f"  Jumlah kota terdaftar   : {n_cities}")
        print(f"  Jumlah truk terdaftar   : {n_trucks}")
        print(f"  Jumlah parameter setting: {n_settings}")

        print("\n  Daftar kota (depot):")
        for city in session.query(City).filter_by(is_depot=True).all():
            print(f"    - {city.name} (lat={city.latitude}, lon={city.longitude})")

    print("\n✓ Semua tabel ERD terbaca dengan benar. Setup database SELESAI.")