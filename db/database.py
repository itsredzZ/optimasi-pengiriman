"""
db/database.py
================
Mengatur koneksi SQLAlchemy ke MySQL (XAMPP) menggunakan kredensial dari .env.

Cara pakai di halaman Streamlit lain:

    from db.database import get_session

    with get_session() as session:
        cities = session.query(City).all()
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # baca file .env di root proyek

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "db_xkargo")

# pymysql sebagai driver MySQL (sudah ada di requirements.txt)
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# pool_pre_ping=True -> auto-reconnect kalau koneksi XAMPP idle/terputus
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session():
    """
    Context manager untuk session database.
    Otomatis commit jika sukses, rollback jika error, lalu selalu close.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """Cek cepat apakah koneksi ke MySQL XAMPP berhasil."""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception as e:
        print(f"[ERROR] Gagal konek ke database: {e}")
        return False