# XKargo — Setup Guide

Panduan ini mencakup: setup GitHub + environment Python di VSCode, dan setup database MySQL via XAMPP/phpMyAdmin sesuai ERD.

## 1. Prasyarat (install dulu kalau belum ada)

- **Python 3.11+** — cek dengan `python --version`
- **Git** — cek dengan `git --version`
- **VSCode** — install extension: Python (ms-python.python), Pylance, GitLens. Saat folder ini dibuka di VSCode, akan muncul notifikasi "Recommended Extensions" dari `.vscode/extensions.json` — klik Install All.
- **XAMPP** — pastikan modul Apache & MySQL tersedia.

## 2. Setup GitHub Repo

1. Salah satu anggota buat repo baru di GitHub (privat, isi nama misal `xkargo`).
2. Clone ke laptop masing-masing:
   ```bash
   git clone https://github.com/USERNAME/xkargo.git
   cd xkargo
   ```
3. Salin seluruh isi folder skeleton ini ke dalam folder hasil clone tadi.
4. Commit awal:
   ```bash
   git add .
   git commit -m "Initial project skeleton"
   git push origin main
   ```
5. Anggota lain `git clone` repo yang sama agar semua mulai dari titik yang identik.
6. Mulai sekarang, setiap orang kerja di branch sendiri, contoh:
   ```bash
   git checkout -b feature/master-data-kota
   ```
   Pull Request ke `main` setelah fitur versi minimum selesai.

## 3. Setup Environment Python (tiap anggota, di laptop masing-masing)

Dari root folder proyek di VSCode terminal:

```bash
# buat virtual environment
python -m venv venv

# aktifkan
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# install semua dependensi
pip install -r requirements.txt
```

Pastikan VSCode memakai interpreter dari `venv` ini: `Ctrl+Shift+P` → "Python: Select Interpreter" → pilih yang ada `venv` di path-nya.

## 4. Setup Database (MySQL via XAMPP + phpMyAdmin)

1. Buka **XAMPP Control Panel**, klik **Start** pada modul **Apache** dan **MySQL** (keduanya harus hijau).
2. Buka browser ke `http://localhost/phpmyadmin`.
3. Klik tab **Import** di bagian atas.
4. Klik **Choose File**, pilih file `schema.sql` dari folder proyek ini.
5. Scroll ke bawah, klik tombol **Go**.
6. Jika berhasil, akan muncul database baru bernama **xkargo_db** di sidebar kiri berisi 10 tabel: `users`, `cities`, `depot_distances`, `trucks`, `delivery_orders`, `items`, `simulation_results`, `carryover_items`, `relocation_logs`, `settings`.
7. `schema.sql` sudah otomatis mengisi data awal: 6 kota depot (Surabaya, Malang, Kediri, Madiun, Jember, Tuban), parameter PSO & operasional default, serta 1 truk contoh per depot — jadi tabel tidak kosong dan bisa langsung dites.

> Catatan: kredensial default XAMPP adalah user `root` tanpa password. Kalau MySQL di laptop kalian sudah diberi password sebelumnya, sesuaikan di langkah berikut.

## 5. Hubungkan Python ke Database

1. Copy `.env.example` jadi `.env`:
   ```bash
   # Mac/Linux
   cp .env.example .env
   # Windows (PowerShell)
   copy .env.example .env
   ```
2. Buka `.env`, sesuaikan kalau kredensial XAMPP kalian berbeda dari default.
3. Tes koneksi:
   ```bash
   python test_connection.py
   ```
   Kalau berhasil akan muncul daftar 6 kota depot dan jumlah truk/setting. Kalau gagal, ikuti pesan error yang muncul (biasanya Apache/MySQL belum running, atau schema belum di-import).

## 6. Jalankan Aplikasi (kerangka awal)

```bash
streamlit run app.py
```

Akan terbuka browser menampilkan status koneksi database. Dari titik ini, masing-masing PIC mulai mengisi file di `pages/` sesuai pembagian tugas.

## Struktur Folder

```
xkargo/
├── app.py                  # entry point Streamlit
├── pages/                  # satu file = satu halaman (lihat pembagian tugas)
├── engine/                 # nanti diisi hasil refactor pso_no2_last_boss.py
├── db/
│   ├── database.py         # koneksi SQLAlchemy ke MySQL
│   └── models.py           # ORM models, sinkron dengan schema.sql
├── utils/                  # excel_import.py, excel_export.py, pdf_export.py, dst
├── schema.sql              # import sekali ke phpMyAdmin
├── test_connection.py      # cek koneksi DB
├── requirements.txt
├── .env.example
└── .gitignore
```

## Catatan Penting

- **Jangan commit `.env`** ke GitHub — sudah masuk `.gitignore`, berisi kredensial.
- Kalau ada perubahan struktur tabel di kemudian hari, ubah **schema.sql** dan **db/models.py** bersamaan supaya tetap sinkron.
- File `engine/` masih kosong — ini menunggu hasil refactor `pso_no2_last_boss.py` (lihat catatan refactor di pembahasan sebelumnya: parameter dari tabel `settings`/`trucks`, bukan konstanta global; return value terstruktur, bukan `print()`).
