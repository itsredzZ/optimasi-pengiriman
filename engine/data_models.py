"""
engine/data_models.py
=======================
"""

from dataclasses import dataclass, field
from typing import Optional

# ----------------------------------------------------------------------
# Klasifikasi dimensi (Business Rule Sesuai Gambar)
# ----------------------------------------------------------------------

def klasifikasi_dimensi(panjang: float, lebar: float, tinggi: float, 
                        max_box_p: float = 200.0, 
                        max_box_l: float = 130.0, 
                        max_box_t: float = 130.0) -> tuple[str, float]:
    """
    Mengembalikan (kategori, faktor) berdasarkan panjang sisi maksimum.
    Mengecek penolakan berdasarkan batas maksimal dimensi box truk terbesar.
    
    Default nilai max_box disesuaikan dengan teks di gambar (200x130x130).
    """
    # 1. Asumsi Rotasi Horizontal (P dan L bisa ditukar agar muat ke truk)
    # Sisi terpanjang dari alas barang dicocokkan dengan Panjang Truk
    p_eval = max(panjang, lebar)
    l_eval = min(panjang, lebar)
    t_eval = tinggi # Tinggi tidak boleh dirotasi (tidak boleh ditidurkan)

    # 2. Cek Kategori: Ditolak (Melebihi dimensi box truk)
    if p_eval > max_box_p or l_eval > max_box_l or t_eval > max_box_t:
        return "Ditolak", 0.0

    # 3. Cari sisi terpanjang dari barang untuk penentuan kategori tarif
    max_sisi = max(panjang, lebar, tinggi)

    # 4. Klasifikasi Kecil, Menengah, Besar
    if max_sisi <= 50.0:
        return "Kecil", 1.0
    elif max_sisi <= 100.0:
        return "Menengah", 1.5
    else:
        # Sudah pasti ada sisi > 100 dan sudah lolos cek 'Ditolak'
        return "Besar", 2.0


# ----------------------------------------------------------------------
# Item: ORM -> dict algoritma
# ----------------------------------------------------------------------

def item_to_algo_dict(item_row, kota_asal: str, kota_tujuan: str, 
                      fleet_max_p: float = 200.0, 
                      fleet_max_l: float = 130.0, 
                      fleet_max_t: float = 130.0) -> dict:
    """
    Konversi 1 baris tabel `items` (+ kota asal/tujuan dari order terkait)
    menjadi dict dengan field yang dipakai engine.
    
    Parameter fleet_max_* adalah dimensi truk terbesar yang beroperasi hari ini,
    digunakan sebagai acuan apakah barang mutlak ditolak sejak awal.
    """
    p = float(item_row.length_cm)
    l = float(item_row.width_cm)
    t = float(item_row.height_cm)
    berat_fisik = float(item_row.weight_kg)

    berat_volumetrik = (p * l * t) / 6000.0
    berat_tagihan = max(berat_fisik, berat_volumetrik)
    
    # Memasukkan dimensi truk terbesar ke dalam fungsi klasifikasi
    kategori, faktor = klasifikasi_dimensi(p, l, t, fleet_max_p, fleet_max_l, fleet_max_t)

    return {
        "id": str(item_row.id),
        "nama": item_row.name,
        "berat_fisik": berat_fisik,
        "berat_volumetrik": berat_volumetrik,
        "berat_tagihan": berat_tagihan,
        "faktor": faktor,
        "kategori": kategori,
        "panjang": p,
        "lebar": l,
        "tinggi": t,
        "volume": p * l * t,
        "kota_asal": kota_asal,
        "kota_tujuan": kota_tujuan,
        "truck_id": None,       
        "is_carryover": bool(item_row.is_carryover),
    }


# ----------------------------------------------------------------------
# Truck: ORM -> dict state algoritma
# ----------------------------------------------------------------------

@dataclass
class TruckState:
    id: int
    plate_number: str
    max_weight_kg: float
    box_p: float          
    box_l: float           
    box_t: float            
    home_depot: str
    current_city: str       

    @property
    def box_volume(self) -> float:
        return self.box_p * self.box_l * self.box_t


def truck_to_state(truck_row, current_city_name: Optional[str] = None) -> TruckState:
    return TruckState(
        id=truck_row.id,
        plate_number=truck_row.plate_number,
        max_weight_kg=float(truck_row.max_weight_kg),
        box_p=float(truck_row.length_cm),
        box_l=float(truck_row.width_cm),
        box_t=float(truck_row.height_cm),
        home_depot=truck_row.home_depot.name,
        current_city=current_city_name or truck_row.current_city.name,
    )