"""
engine/routing.py
===================
Nearest Neighbor routing & Guillotine 3D Bin Packing — logika identik
dengan kode asli, dengan dua perubahan:

  1. guillotine_pack() sekarang menerima dimensi box (box_p, box_l, box_t)
     sebagai parameter, bukan konstanta global BOX_P/BOX_L/BOX_T — karena
     tiap truk kini bisa punya dimensi berbeda (lihat data_models.TruckState).

  2. nearest_neighbor_route() menerima `depot_names` (list kota depot aktif
     dari database) sebagai parameter, menggantikan DEPOT_MAP.keys() yang
     dulu hardcoded 6 nama depot tetap.
"""

from engine.astar import astar_cached


class Ruang:
    """Representasi satu ruang kosong di dalam box truk."""

    def __init__(self, p, l, t):
        self.p = p
        self.l = l
        self.t = t
        self.volume = p * l * t

    def bisa_muat(self, ip, il, it):
        return ip <= self.p and il <= self.l and it <= self.t

    def guillotine_split(self, ip, il, it):
        """
        Potong ruang jadi 3 sub-ruang setelah item ditempatkan:
          - Sisa Depan : (P_ruang - P_item) x L_ruang x T_ruang
          - Sisa Kanan : P_item x (L_ruang - L_item) x T_ruang
          - Sisa Atas  : P_item x L_item x (T_ruang - T_item)
        """
        sisa = []
        if self.p - ip > 0:
            sisa.append(Ruang(self.p - ip, self.l, self.t))
        if self.l - il > 0:
            sisa.append(Ruang(ip, self.l - il, self.t))
        if self.t - it > 0:
            sisa.append(Ruang(ip, il, self.t - it))
        return sisa


def guillotine_pack(items_ordered, box_p, box_l, box_t) -> set:
    """
    Coba muat barang (urutan = prioritas loading dari PSO) ke dalam satu
    box berdimensi box_p x box_l x box_t. Best-fit pada ruang tersisa.
    Mengembalikan set ID barang yang berhasil dimuat.
    """
    ruang_list = [Ruang(box_p, box_l, box_t)]
    berhasil_id = set()

    for item in items_ordered:
        ip, il, it = item["panjang"], item["lebar"], item["tinggi"]

        best_idx = -1
        best_vol = float("inf")
        for idx, ruang in enumerate(ruang_list):
            if ruang.bisa_muat(ip, il, it) and ruang.volume < best_vol:
                best_vol = ruang.volume
                best_idx = idx

        if best_idx >= 0:
            r = ruang_list[best_idx]
            ruang_baru = r.guillotine_split(ip, il, it)
            ruang_list.pop(best_idx)
            ruang_list.extend(ruang_baru)
            berhasil_id.add(item["id"])

    return berhasil_id


def nearest_neighbor_route(depot, kota_tujuan_list, adj, city_idx, cities,
                            coords, cache, depot_names):
    """
    Bangun rute: depot -> kota terdekat berturut-turut -> depot terdekat
    (untuk kembali). Jarak dihitung via A* (astar_cached).

    depot_names: list nama kota depot aktif (dari database), dipakai saat
    mencari depot mana yang TERDEKAT untuk kembali parkir.

    Mengembalikan: (urutan_rute, total_jarak_km, depot_kembali)
    """
    unique_kota = list(dict.fromkeys(kota_tujuan_list))
    if not unique_kota:
        return [], 0.0, depot

    route = []
    visited = set()
    current = depot
    total_dist = 0.0

    while len(visited) < len(unique_kota):
        best_kota = None
        best_dist = float("inf")
        for kota in unique_kota:
            if kota in visited:
                continue
            d = astar_cached(adj, city_idx, cities, current, kota, coords, cache)
            if d < best_dist:
                best_dist = d
                best_kota = kota

        if best_kota is None or best_dist == float("inf"):
            break

        route.append(best_kota)
        visited.add(best_kota)
        total_dist += best_dist
        current = best_kota

    # Kembali ke depot TERDEKAT dari kota terakhir
    best_depot = depot
    best_depot_dist = float("inf")
    for dep in depot_names:
        d = astar_cached(adj, city_idx, cities, current, dep, coords, cache)
        if d < best_depot_dist:
            best_depot_dist = d
            best_depot = dep

    if best_depot_dist < float("inf") and current != best_depot:
        total_dist += best_depot_dist

    return route, total_dist, best_depot