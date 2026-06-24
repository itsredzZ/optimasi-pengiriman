"""
engine/routing.py
===================
Nearest Neighbor routing & Guillotine 3D Bin Packing.

Perubahan dari versi sebelumnya:
  1. guillotine_pack() menerima dimensi box sebagai parameter (bukan
     konstanta global) — tiap truk bisa punya dimensi berbeda.
  2. nearest_neighbor_route() menerima depot_names dari database.
  3. [BARU] ROTASI HORIZONTAL: guillotine_pack() mencoba memutar barang
     (P<->L) kalau orientasi aslinya tidak muat ke ruang kosong.
     Tinggi TIDAK pernah diputar. Hanya 2 orientasi dicek per ruang.
"""

from engine.astar import astar_cached


class Ruang:
    def __init__(self, p, l, t):
        self.p = p
        self.l = l
        self.t = t
        self.volume = p * l * t

    def bisa_muat(self, ip, il, it):
        return ip <= self.p and il <= self.l and it <= self.t

    def guillotine_split(self, ip, il, it):
        sisa = []
        if self.p - ip > 0:
            sisa.append(Ruang(self.p - ip, self.l, self.t))
        if self.l - il > 0:
            sisa.append(Ruang(ip, self.l - il, self.t))
        if self.t - it > 0:
            sisa.append(Ruang(ip, il, self.t - it))
        return sisa


def _kandidat_orientasi(item):
    """2 orientasi horizontal. Tinggi selalu tetap (tidak ditidurkan)."""
    p, l, t = item["panjang"], item["lebar"], item["tinggi"]
    return [
        (p, l, t, "normal"),
        (l, p, t, "diputar_90"),
    ]


def guillotine_pack(items_ordered, box_p, box_l, box_t,
                    orientasi_terpakai: dict = None) -> set:
    """
    Best-fit Guillotine packing dengan rotasi horizontal.

    orientasi_terpakai: kirim None saat dipanggil dari loop PSO (default,
    tidak ada overhead). Kirim dict kosong {} dari halaman Hasil Operasional
    kalau mau tahu orientasi tiap barang untuk manifest loading.
    """
    ruang_list = [Ruang(box_p, box_l, box_t)]
    berhasil_id = set()

    for item in items_ordered:
        best_idx   = -1
        best_vol   = float("inf")
        best_dims  = None
        best_label = None

        for idx, ruang in enumerate(ruang_list):
            for (cp, cl, ct, label) in _kandidat_orientasi(item):
                if ruang.bisa_muat(cp, cl, ct) and ruang.volume < best_vol:
                    best_vol   = ruang.volume
                    best_idx   = idx
                    best_dims  = (cp, cl, ct)
                    best_label = label

        if best_idx >= 0:
            r = ruang_list[best_idx]
            cp, cl, ct = best_dims
            ruang_list.pop(best_idx)
            ruang_list.extend(r.guillotine_split(cp, cl, ct))
            berhasil_id.add(item["id"])
            if orientasi_terpakai is not None:
                orientasi_terpakai[item["id"]] = best_label

    return berhasil_id


def nearest_neighbor_route(depot, kota_tujuan_list, adj, city_idx, cities,
                            coords, cache, depot_names):
    unique_kota = list(dict.fromkeys(kota_tujuan_list))
    if not unique_kota:
        return [], 0.0, depot

    route, visited, current, total_dist = [], set(), depot, 0.0

    while len(visited) < len(unique_kota):
        best_kota, best_dist = None, float("inf")
        for kota in unique_kota:
            if kota in visited:
                continue
            d = astar_cached(adj, city_idx, cities, current, kota, coords, cache)
            if d < best_dist:
                best_dist, best_kota = d, kota
        if best_kota is None or best_dist == float("inf"):
            break
        route.append(best_kota)
        visited.add(best_kota)
        total_dist += best_dist
        current = best_kota

    best_depot, best_depot_dist = depot, float("inf")
    for dep in depot_names:
        d = astar_cached(adj, city_idx, cities, current, dep, coords, cache)
        if d < best_depot_dist:
            best_depot_dist, best_depot = d, dep

    if best_depot_dist < float("inf") and current != best_depot:
        total_dist += best_depot_dist

    return route, total_dist, best_depot