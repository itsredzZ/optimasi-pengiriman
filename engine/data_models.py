"""
engine/data_models.py
=======================
Jembatan antara baris ORM (db/models.py) dan struct dict yang dipakai
engine PSO/A*/Guillotine.

KATEGORI/FAKTOR DIMENSI — TIDAK PERLU KOLOM BARU DI SKEMA:
─────────────────────────────────────────────────────────
Kategori & faktor tarif dihitung DINAMIS dari dimensi barang vs dimensi
truk yang membawanya — tidak perlu kolom `kategori`/`faktor` di tabel
`items`. Ini penting karena dimensi box tiap truk sekarang bisa berbeda
(dikelola admin lewat halaman Manajemen Truk).

Golongan (sesuai business rule tim):
  Kecil    : semua sisi <= 50 cm                               faktor 1.0
  Menengah : semua sisi <= 100 cm, tapi min. 1 sisi > 50 cm   faktor 1.5
  Besar    : min. 1 sisi > 100 cm, semua sisi <= box truk      faktor 2.0
  Ditolak  : ada sisi melebihi dimensi box truk                faktor 0.0

KONSISTENSI DENGAN GUILLOTINE PACKER (routing.py):
─────────────────────────────────────────────────
routing.py mencoba 2 orientasi horizontal (normal dan diputar 90° P<->L)
saat muat barang ke ruang kosong. Maka klasifikasi_dimensi() di sini JUGA
mempertimbangkan rotasi P<->L saat cek "Ditolak" — barang dianggap Ditolak
hanya jika KEDUA orientasi tidak muat. Tinggi tidak diputar di keduanya.
"""

from dataclasses import dataclass
from typing import Optional

DEFAULT_BOX_P = 200.0
DEFAULT_BOX_L = 130.0
DEFAULT_BOX_T = 130.0


def klasifikasi_dimensi(panjang: float, lebar: float, tinggi: float,
                         max_box_p: float = DEFAULT_BOX_P,
                         max_box_l: float = DEFAULT_BOX_L,
                         max_box_t: float = DEFAULT_BOX_T) -> tuple[str, float]:
    """
    Mengembalikan (kategori, faktor).

    Cek "Ditolak" mempertimbangkan rotasi horizontal (P<->L) — barang
    dianggap Ditolak hanya jika KEDUA orientasi tidak muat ke box truk.
    Tinggi tidak diputar. Ini konsisten dengan Guillotine packer.
    """
    if tinggi > max_box_t:
        return "Ditolak", 0.0

    orientasi_normal_muat = (panjang <= max_box_p and lebar <= max_box_l)
    orientasi_putar_muat  = (lebar   <= max_box_p and panjang <= max_box_l)

    if not orientasi_normal_muat and not orientasi_putar_muat:
        return "Ditolak", 0.0

    max_sisi = max(panjang, lebar, tinggi)
    if max_sisi <= 50.0:
        return "Kecil", 1.0
    elif max_sisi <= 100.0:
        return "Menengah", 1.5
    else:
        return "Besar", 2.0


def is_item_valid(item: dict) -> bool:
    """True jika barang bukan Ditolak. Pakai ini di halaman Input Pengiriman."""
    return item.get("kategori") != "Ditolak"


def item_to_algo_dict(item_row, kota_asal: str, kota_tujuan: str,
                       truck_box_p: float = DEFAULT_BOX_P,
                       truck_box_l: float = DEFAULT_BOX_L,
                       truck_box_t: float = DEFAULT_BOX_T) -> dict:
    p = float(item_row.length_cm)
    l = float(item_row.width_cm)
    t = float(item_row.height_cm)
    berat_fisik = float(item_row.weight_kg)

    berat_volumetrik = (p * l * t) / 6000.0
    berat_tagihan    = max(berat_fisik, berat_volumetrik)
    kategori, faktor = klasifikasi_dimensi(p, l, t, truck_box_p, truck_box_l, truck_box_t)

    return {
        "id":               str(item_row.id),
        "nama":             item_row.name,
        "berat_fisik":      berat_fisik,
        "berat_volumetrik": berat_volumetrik,
        "berat_tagihan":    berat_tagihan,
        "faktor":           faktor,
        "kategori":         kategori,
        "panjang":          p,
        "lebar":            l,
        "tinggi":           t,
        "volume":           p * l * t,
        "kota_asal":        kota_asal,
        "kota_tujuan":      kota_tujuan,
        "truck_id":         None,
        "is_carryover":     bool(item_row.is_carryover),
    }


@dataclass
class TruckState:
    id:            int
    plate_number:  str
    max_weight_kg: float
    box_p:         float
    box_l:         float
    box_t:         float
    home_depot:    str
    current_city:  str

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