"""
engine/dev_data_generator.py
==============================
PERINGATAN: HANYA UNTUK TESTING/DEVELOPMENT, JANGAN DIPAKAI DI PRODUKSI.

Kode asli (generate_daily_delivery / generate_daily_delivery_multiday)
men-generate barang pengiriman secara ACAK dari database 118 item CSV.
Itu cocok untuk simulasi akademik, tapi TIDAK BOLEH dipakai di aplikasi
operasional -- barang produksi harus berasal dari input form/Excel
operator sungguhan (lihat halaman 5_Input_Pengiriman.py), bukan random.

Modul ini disediakan supaya Person 1 (atau siapa pun) bisa MENGUJI
pipeline PSO/A*/Guillotine end-to-end SEBELUM halaman Input Pengiriman
selesai dibangun oleh Person 3 -- jadi tidak saling blocking. Begitu
halaman Input Pengiriman sungguhan jalan, modul ini tidak lagi dipanggil
dari alur produksi.
"""

import random

from engine.data_models import klasifikasi_dimensi


def generate_dummy_items(trucks, depot_names, all_city_names, n_min=10, n_max=15, seed=None):
    """
    Generate barang dummy untuk testing -- satu batch per truk yang sedang
    parkir di sebuah depot.

    Parameter:
      trucks         : list TruckState (lihat data_models.py)
      depot_names    : list nama depot aktif
      all_city_names : list semua nama kota (termasuk non-depot), untuk tujuan acak
      n_min, n_max   : jumlah item dummy per truk
      seed           : random seed (reproducible)

    Mengembalikan: list item dict (format sama dengan item_to_algo_dict),
    sudah punya 'truck_id' terisi sesuai truk yang menampungnya.
    """
    if seed is not None:
        random.seed(seed)

    kandidat_tujuan_global = [c for c in all_city_names]

    items = []
    item_counter = 0

    for truck in trucks:
        depot = truck.current_city
        n_items = random.randint(n_min, n_max)
        kandidat_tujuan = [c for c in kandidat_tujuan_global if c != depot]

        for _ in range(n_items):
            item_counter += 1
            p = round(random.uniform(20, min(120, truck.box_p)), 1)
            l = round(random.uniform(20, min(100, truck.box_l)), 1)
            t = round(random.uniform(15, min(100, truck.box_t)), 1)
            berat_fisik = round(random.uniform(2, 80), 1)

            berat_volumetrik = (p * l * t) / 6000.0
            berat_tagihan = max(berat_fisik, berat_volumetrik)
            kategori, faktor = klasifikasi_dimensi(p, l, t)

            items.append({
                "id": f"DUMMY_{item_counter:04d}",
                "nama": f"Barang Dummy #{item_counter}",
                "berat_fisik": berat_fisik,
                "berat_volumetrik": berat_volumetrik,
                "berat_tagihan": berat_tagihan,
                "faktor": faktor,
                "kategori": kategori,
                "panjang": p,
                "lebar": l,
                "tinggi": t,
                "volume": p * l * t,
                "kota_asal": depot,
                "kota_tujuan": random.choice(kandidat_tujuan),
                "truck_id": truck.id,
                "is_carryover": False,
            })

    return items