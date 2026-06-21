"""
engine/astar.py
=================
A* search untuk jarak antar kota — logika identik dengan pso_no2_last_boss.py
(REV-5), hanya satu perubahan penting:

  PERUBAHAN: cache A* (_ASTAR_CACHE) yang di kode asli adalah dict GLOBAL
  di level modul. Itu berbahaya di Streamlit karena satu proses bisa
  melayani beberapa sesi/pengguna sekaligus -> cache bisa "bocor" antar
  sesi atau (lebih buruk) antar hari simulasi yang berbeda graph-nya.

  Solusinya: cache sekarang adalah dict biasa yang dibuat oleh PEMANGGIL
  (satu per run optimasi) dan diteruskan sebagai parameter eksplisit.
  Fungsionalitas caching-nya sama persis, hanya scope-nya yang dikontrol.
"""

import heapq
import numpy as np


def euclidean_km(coord1, coord2) -> float:
    """
    Jarak Euclidean antara dua koordinat (lat, lon) dalam km.
    Dipakai sebagai heuristik h(n) pada A* — admissible karena jalan
    darat selalu >= garis lurus.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = (lat2 - lat1) * 111.0
    dlon = (lon2 - lon1) * 111.0 * abs(np.cos(np.radians((lat1 + lat2) / 2)))
    return float(np.sqrt(dlat**2 + dlon**2))


def astar_distance(adj, city_idx, cities, start, end, coords) -> float:
    """
    Jarak terpendek start->end via A*. f(n) = g(n) + h(n).
    Mengembalikan jarak dalam km, atau inf jika tidak terjangkau.
    """
    if start == end:
        return 0.0

    n = len(cities)
    src = city_idx[start]
    dst = city_idx[end]
    coord_dst = coords[end]

    def h(node_idx):
        return euclidean_km(coords[cities[node_idx]], coord_dst)

    g = [float("inf")] * n
    g[src] = 0.0
    pq = [(h(src), src)]

    while pq:
        f_cur, u = heapq.heappop(pq)
        if u == dst:
            return g[dst]
        if f_cur > g[u] + h(u) + 1e-9:
            continue
        for v in range(n):
            w = adj[u][v]
            if w < float("inf"):
                g_new = g[u] + w
                if g_new < g[v]:
                    g[v] = g_new
                    heapq.heappush(pq, (g_new + h(v), v))

    return g[dst]


def astar_cached(adj, city_idx, cities, start, end, coords, cache: dict) -> float:
    """
    Wrapper A* dengan cache eksplisit. `cache` adalah dict biasa yang
    dibuat sekali oleh pemanggil (mis. orchestrator) di awal satu run
    optimasi, lalu diteruskan ke seluruh fungsi yang butuh jarak
    (routing, fitness, relocation) supaya tidak hitung ulang pasangan
    kota yang sama berkali-kali dalam loop PSO.
    """
    key = (start, end)
    if key not in cache:
        cache[key] = astar_distance(adj, city_idx, cities, start, end, coords)
    return cache[key]