"""
engine/item_assignment.py
===========================
Assign truck_id ke tiap item berdasarkan truk yang parkir di depot asal
item tersebut. Ini harus berjalan SEBELUM PSO dipanggil, karena fitness.py
mengelompokkan item berdasarkan truck_id.

Dua hasil yang dikembalikan:
  - items_siap    : item yang sudah dapat truck_id → masuk ke PSO
  - items_notruk  : item yang depotnya tidak ada truknya → auto carry-over
                    SEBELUM PSO jalan (bukan gagal di dalam packer)

Kenapa dipisah dari orchestrator.py:
  Halaman 6_Optimasi_Hasil.py butuh tahu items_notruk SEBELUM PSO jalan
  supaya bisa tampilkan info ke operator ("X item langsung carry-over
  karena depotnya tidak ada truk"). Kalau digabung di orchestrator,
  info ini tidak tersedia sampai PSO selesai.
"""

from collections import defaultdict
from engine.data_models import TruckState


def build_depot_truck_map(trucks: list[TruckState]) -> dict[str, list[int]]:
    """
    Bangun peta: nama_depot -> [truck_id, ...] yang sedang parkir di sana.
    Satu depot bisa punya lebih dari satu truk.
    """
    depot_map = defaultdict(list)
    for truck in trucks:
        depot_map[truck.current_city].append(truck.id)
    return dict(depot_map)


def assign_trucks_to_items(
    items: list[dict],
    trucks: list[TruckState],
) -> tuple[list[dict], list[dict]]:
    """
    Assign truck_id ke tiap item berdasarkan current_city truk.

    Aturan assignment:
      - Item carry-over (is_carryover=True) mendapat prioritas PERTAMA
        dalam antrian per depot — urutan ini dipertahankan supaya
        carry-over selalu dapat slot sebelum barang baru.
      - Jika satu depot punya lebih dari 1 truk, semua item di depot itu
        di-assign ke truk PERTAMA (index 0) di depot tersebut. PSO yang
        akan memutuskan distribusi optimalnya lewat Direct Order.
      - Item dengan kota_asal yang tidak ada truknya → items_notruk
        (langsung carry-over, tidak masuk PSO).

    Mengembalikan:
      (items_siap, items_notruk)
      items_siap   : list item dengan truck_id terisi, carry-over di depan
      items_notruk : list item yang depotnya kosong truk
    """
    depot_truck_map = build_depot_truck_map(trucks)

    # Pisah carry-over dan baru per depot untuk jaga urutan prioritas
    carryover_per_depot: dict[str, list[dict]] = defaultdict(list)
    baru_per_depot:      dict[str, list[dict]] = defaultdict(list)
    items_notruk: list[dict] = []

    for item in items:
        depot = item.get("kota_asal", "")
        if depot not in depot_truck_map:
            # Depot tidak ada truknya → langsung carry-over
            item = dict(item)
            item["is_carryover"] = True
            items_notruk.append(item)
            continue

        if item.get("is_carryover", False):
            carryover_per_depot[depot].append(item)
        else:
            baru_per_depot[depot].append(item)

    # Gabung carry-over dulu, baru item baru — assign truck_id dari truk pertama di depot
    items_siap: list[dict] = []
    for depot, truck_ids in depot_truck_map.items():
        assigned_truck_id = truck_ids[0]
        for item in carryover_per_depot.get(depot, []):
            item = dict(item)
            item["truck_id"] = assigned_truck_id
            items_siap.append(item)
        for item in baru_per_depot.get(depot, []):
            item = dict(item)
            item["truck_id"] = assigned_truck_id
            items_siap.append(item)

    return items_siap, items_notruk