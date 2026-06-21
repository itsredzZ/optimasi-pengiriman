"""
engine/relocation.py
======================
Keputusan relokasi truk cost-benefit & update posisi truk setelah operasi
harian. Logika identik dengan kode asli (REV-6), satu perubahan: daftar
depot sekarang datang dari `depot_names` (database, bisa berapa pun),
bukan dari DEPOT_MAP yang hardcoded 6 depot.
"""

from collections import defaultdict

from engine.astar import astar_cached


def hitung_biaya_relokasi_truk(kota_dari, kota_ke, adj, city_idx, cities,
                                coords, cache, op_params) -> float:
    """Biaya BBM relokasi truk KOSONG (tanpa muatan) dari kota_dari ke kota_ke."""
    jarak = astar_cached(adj, city_idx, cities, kota_dari, kota_ke, coords, cache)
    if jarak == float("inf"):
        return float("inf")
    return op_params.bbm_base * jarak * op_params.harga_solar


def putuskan_relokasi_truk(truck_depot_current: dict, items_by_depot: dict,
                            adj, city_idx, cities, coords, cache, op_params,
                            depot_names):
    """
    Tentukan apakah truk perlu direlokasi ke depot yang kehabisan truk,
    dan dari depot mana (donor harus punya truk LEBIH DARI 1, supaya
    depot donor tidak ikut kosong setelah mendonasikan satu truknya).

    Parameter:
      truck_depot_current : dict truck_id -> nama_kota (posisi saat ini)
      items_by_depot       : dict nama_kota -> list item (preview hari berikutnya)
      depot_names           : list semua nama depot aktif (dari database)

    Mengembalikan:
      relokasi_decisions   : list dict detail keputusan per depot target
      truck_depot_updated  : dict truck_id -> nama_kota (setelah relokasi diterapkan)
    """
    trucks_at_depot = defaultdict(list)
    for truck_id, depot in truck_depot_current.items():
        trucks_at_depot[depot].append(truck_id)

    depot_punya_truck = set(truck_depot_current.values())
    depot_punya_barang = {dep for dep, items in items_by_depot.items() if items}
    depot_butuh_truck = depot_punya_barang - depot_punya_truck

    relokasi_decisions = []
    truck_depot_updated = dict(truck_depot_current)
    trucks_available = {depot: list(tids) for depot, tids in trucks_at_depot.items()}

    for target_depot in sorted(depot_butuh_truck):
        items_di_target = items_by_depot.get(target_depot, [])
        if not items_di_target:
            continue

        estimasi_tarif = sum(
            it["berat_tagihan"]
            * astar_cached(adj, city_idx, cities, target_depot, it["kota_tujuan"], coords, cache)
            * it["faktor"] * op_params.tarif_dasar
            for it in items_di_target
        )

        best_truck_id = None
        best_biaya = float("inf")
        best_dari_depot = None

        for donor_depot, avail_list in trucks_available.items():
            if donor_depot == target_depot:
                continue
            if len(avail_list) <= 1:
                continue  # donor harus punya excess (>1), supaya tidak ikut kosong

            biaya = hitung_biaya_relokasi_truk(
                donor_depot, target_depot, adj, city_idx, cities, coords, cache, op_params
            )
            if biaya < best_biaya:
                best_biaya = biaya
                best_truck_id = avail_list[0]
                best_dari_depot = donor_depot

        if best_truck_id is None:
            relokasi_decisions.append({
                "truck_id": None,
                "dari": None,
                "ke": target_depot,
                "biaya": 0.0,
                "estimasi_tarif": estimasi_tarif,
                "relokasi": False,
                "alasan": "Tidak ada depot dengan truk berlebih (semua <= 1 truk)",
            })
            continue

        should_relocate = (estimasi_tarif > best_biaya) and (best_biaya < float("inf"))

        relokasi_decisions.append({
            "truck_id": best_truck_id,
            "dari": best_dari_depot,
            "ke": target_depot,
            "biaya": best_biaya,
            "estimasi_tarif": estimasi_tarif,
            "relokasi": should_relocate,
            "alasan": ("Tarif > Biaya Relokasi" if should_relocate
                       else "Tarif <= Biaya Relokasi (item carry-over)"),
        })

        if should_relocate:
            truck_depot_updated[best_truck_id] = target_depot
            trucks_available[best_dari_depot].remove(best_truck_id)
            trucks_available.setdefault(target_depot, []).append(best_truck_id)

    return relokasi_decisions, truck_depot_updated


def update_posisi_truk(best_routes: dict, truck_depot_current: dict) -> dict:
    """
    Posisi truk baru = depot_kembali dari rute terbaiknya hari ini.
    Truk yang tidak beroperasi (tidak ada di best_routes) tetap di posisi semula.
    """
    truck_depot_baru = dict(truck_depot_current)
    for truck_id, route_info in best_routes.items():
        depot_kembali = route_info.get("depot_kembali")
        if depot_kembali:
            truck_depot_baru[truck_id] = depot_kembali
    return truck_depot_baru


def get_carryover_items(all_items: list, best_routes: dict) -> list:
    """
    Item yang ID-nya tidak muncul di best_routes manapun = carry-over.
    Flag is_carryover di-set True supaya diprioritaskan (key=-1.0) besok.
    """
    terkirim_ids = set()
    for route_info in best_routes.values():
        for item in route_info.get("items", []):
            terkirim_ids.add(item["id"])

    carryover = [it for it in all_items if it["id"] not in terkirim_ids]
    for item in carryover:
        item["is_carryover"] = True
    return carryover