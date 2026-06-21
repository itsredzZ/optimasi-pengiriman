"""
engine/graph_builder.py
=========================
Pengganti load_adjacency_matrix(filepath_csv) dari kode asli.
Membangun adjacency matrix, city_idx, dan koordinat kota LANGSUNG dari
database (tabel `cities` + `depot_distances`), bukan dari file CSV.

Ini yang membuat halaman Master Data > Kota & Jaringan Jalan (Matrix
Editor) operator betul-betul mempengaruhi hasil A*, bukan cuma tampilan.
"""

from db.models import City, DepotDistance


def build_graph_from_db(session):
    """
    Mengembalikan:
      cities      : list nama kota (urutan tetap, dipakai sebagai index)
      city_idx    : dict nama_kota -> index
      adj         : adjacency matrix (list of list), inf jika tidak ada data jarak
      coords      : dict nama_kota -> (latitude, longitude)  -> heuristik A*
      depot_names : list nama kota yang is_depot=True dan is_active=True
    """
    city_rows = session.query(City).filter_by(is_active=True).all()

    cities = [c.name for c in city_rows]
    city_idx = {name: i for i, name in enumerate(cities)}
    coords = {c.name: (float(c.latitude), float(c.longitude)) for c in city_rows}
    depot_names = [c.name for c in city_rows if c.is_depot]

    n = len(cities)
    adj = [[float("inf")] * n for _ in range(n)]
    for i in range(n):
        adj[i][i] = 0.0

    id_to_name = {c.id: c.name for c in city_rows}

    dist_rows = session.query(DepotDistance).all()
    for d in dist_rows:
        name_a = id_to_name.get(d.city_a_id)
        name_b = id_to_name.get(d.city_b_id)
        if name_a is None or name_b is None:
            continue  # kota tidak aktif / tidak ditemukan -> skip
        if name_a not in city_idx or name_b not in city_idx:
            continue
        i, j = city_idx[name_a], city_idx[name_b]
        dist_km = float(d.distance_km)
        adj[i][j] = dist_km
        adj[j][i] = dist_km

    return cities, city_idx, adj, coords, depot_names