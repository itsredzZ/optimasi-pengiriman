"""
engine/fitness.py
===================
Evaluasi fitness (profit harian) untuk satu partikel PSO.

PERUBAHAN PALING PENTING dari kode asli:
─────────────────────────────────────────
Kode asli (evaluate_fitness di pso_no2_last_boss.py):
    for truck_id in range(1, 7):           # <- HARDCODED selalu 6 truk
        depot = effective_depot.get(truck_id, TRUCK_DEPOT.get(truck_id))
        ...
        if (cum_vol + item['volume'] <= BOX_VOL and               # <- konstanta GLOBAL
            cum_berat_fisik + item['berat_fisik'] <= BOX_BERAT_MAX):

Di sini, truk diterima sebagai LIST OF TruckState (jumlah & kapasitas
bebas, dikelola admin lewat halaman Manajemen Truk), dan setiap truk
memakai kapasitas (box_volume, max_weight_kg) MILIKNYA SENDIRI, bukan
satu nilai global yang dipakai semua truk.

Sisanya — PSO Direct Order, carry-over priority (key=-1.0), pre-filter
kapasitas, Guillotine packing, perhitungan tarif/BBM — identik dengan
logika asli.
"""

from collections import defaultdict

from engine.astar import astar_cached
from engine.routing import nearest_neighbor_route, guillotine_pack


def hitung_konsumsi_bbm(berat_muatan_kg: float, bbm_base: float, bbm_faktor: float) -> float:
    return bbm_base + (berat_muatan_kg / 1000.0) * bbm_faktor


def hitung_tarif_per_barang(item: dict, jarak_km: float, tarif_dasar: float) -> float:
    return item["berat_tagihan"] * jarak_km * item["faktor"] * tarif_dasar


def evaluate_fitness(particle, items, trucks, adj, city_idx, cities, coords,
                      cache, op_params, depot_names):
    """
    Evaluasi satu partikel -> (profit, detail_routes).

    Parameter:
      particle    : array desimal [0.00, 0.99], satu nilai per item di `items`
                    (urutan elemen particle harus selaras dengan urutan items)
      items       : list item dict (lihat data_models.item_to_algo_dict),
                    setiap item sudah punya 'truck_id' hasil assignment
                    orchestrator berdasarkan posisi truk hari ini
      trucks      : list TruckState (lihat data_models.py) — truk yang
                    SEDANG beroperasi hari ini (sudah py punya posisi current_city)
      op_params   : engine.config.OperationalParams (tarif_dasar, bbm_base, dst)
      depot_names : list nama kota depot aktif (untuk nearest_neighbor_route)

    Mengembalikan: (profit: float, detail_routes: dict[truck_id -> info])
    """
    truck_groups = defaultdict(list)
    for i, item in enumerate(items):
        if item.get("is_carryover", False):
            priority = -1.0  # Carry-over: selalu masuk duluan (WAJIB MASUK)
        else:
            priority = particle[i]
        truck_groups[item["truck_id"]].append((priority, item))

    total_tarif = 0.0
    total_bbm = 0.0
    detail_routes = {}

    for truck in trucks:
        depot = truck.current_city
        group = truck_groups.get(truck.id, [])
        if not group:
            continue

        # TAHAP 1: sort berdasarkan decimal key PSO (ascending)
        group.sort(key=lambda x: x[0])
        sorted_items = [x[1] for x in group]

        # TAHAP 2: pre-filter kumulatif (kapasitas MILIK TRUK INI, bukan global)
        pre_filtered = []
        cum_vol = 0.0
        cum_berat_fisik = 0.0
        for item in sorted_items:
            if (cum_vol + item["volume"] <= truck.box_volume and
                    cum_berat_fisik + item["berat_fisik"] <= truck.max_weight_kg):
                pre_filtered.append(item)
                cum_vol += item["volume"]
                cum_berat_fisik += item["berat_fisik"]

        if not pre_filtered:
            continue

        # TAHAP 3: Nearest Neighbor routing (estimasi awal)
        kota_tujuan_list = [item["kota_tujuan"] for item in pre_filtered]
        rute, _, _ = nearest_neighbor_route(
            depot, kota_tujuan_list, adj, city_idx, cities, coords, cache, depot_names
        )
        if not rute:
            continue

        # TAHAP 4: Guillotine 3D Bin Packing (dimensi box MILIK TRUK INI)
        berhasil_id = guillotine_pack(pre_filtered, truck.box_p, truck.box_l, truck.box_t)
        final_items = [it for it in pre_filtered if it["id"] in berhasil_id]
        if not final_items:
            continue

        # TAHAP 5: rebuild rute dari item yang lolos Guillotine
        final_destinations = [it["kota_tujuan"] for it in final_items]
        final_rute, final_dist, depot_kembali = nearest_neighbor_route(
            depot, final_destinations, adj, city_idx, cities, coords, cache, depot_names
        )
        if final_dist == 0:
            continue

        # TAHAP 6: tarif & BBM
        berat_muatan_fisik = sum(it["berat_fisik"] for it in final_items)
        konsumsi_bbm = hitung_konsumsi_bbm(berat_muatan_fisik, op_params.bbm_base, op_params.bbm_faktor)
        biaya_bbm = konsumsi_bbm * final_dist * op_params.harga_solar

        tarif_truck = 0.0
        for it in final_items:
            jarak = astar_cached(adj, city_idx, cities, depot, it["kota_tujuan"], coords, cache)
            tarif_truck += hitung_tarif_per_barang(it, jarak, op_params.tarif_dasar)

        total_tarif += tarif_truck
        total_bbm += biaya_bbm

        detail_routes[truck.id] = {
            "depot": depot,
            "rute": final_rute,
            "depot_kembali": depot_kembali,
            "items": final_items,
            "total_dist": final_dist,
            "biaya_bbm": biaya_bbm,
            "tarif": tarif_truck,
            "berat_muatan": berat_muatan_fisik,
            "konsumsi_bbm": konsumsi_bbm,
        }

    profit = total_tarif - total_bbm
    return profit, detail_routes