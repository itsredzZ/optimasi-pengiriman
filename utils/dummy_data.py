# utils/dummy_data.py — data dummy untuk develop visualisasi sebelum PSO selesai

def get_dummy_convergence():
    """Simulasi kurva Gbest per iterasi"""
    import random
    random.seed(42)
    gbest = 5000000
    history = []
    for i in range(50):
        gbest += random.randint(50000, 300000) * (1 - i/60)
        history.append({"iterasi": i+1, "gbest": round(gbest)})
    return history

def get_dummy_velocity_breakdown():
    """Komponen velocity PSO per iterasi"""
    import random
    random.seed(7)
    data = []
    for i in range(50):
        w = max(0.4, 0.9 - i * 0.01)
        data.append({
            "iterasi": i+1,
            "inersia": round(w * random.uniform(0.3, 0.8), 3),
            "kognitif": round(random.uniform(0.1, 0.6), 3),
            "sosial": round(random.uniform(0.1, 0.6), 3),
        })
    return data

def get_dummy_cities():
    """Koordinat kota Jawa Timur untuk peta A*"""
    return [
        {"nama": "Surabaya",   "lat": -7.2575,  "lon": 112.7521, "is_depot": True},
        {"nama": "Malang",     "lat": -7.9839,  "lon": 112.6214, "is_depot": True},
        {"nama": "Sidoarjo",   "lat": -7.4478,  "lon": 112.7183, "is_depot": False},
        {"nama": "Gresik",     "lat": -7.1565,  "lon": 112.6555, "is_depot": False},
        {"nama": "Mojokerto",  "lat": -7.4713,  "lon": 112.4346, "is_depot": False},
        {"nama": "Jember",     "lat": -8.1845,  "lon": 113.6678, "is_depot": True},
        {"nama": "Banyuwangi", "lat": -8.2193,  "lon": 114.3691, "is_depot": False},
        {"nama": "Madiun",     "lat": -7.6298,  "lon": 111.5238, "is_depot": False},
    ]

def get_dummy_astar_path():
    """Contoh jalur A* dari Surabaya ke Jember"""
    return {
        "start": "Surabaya",
        "goal": "Jember",
        "path": ["Surabaya", "Sidoarjo", "Malang", "Jember"],
        "explored": ["Surabaya", "Sidoarjo", "Gresik", "Mojokerto", "Malang", "Jember"],
    }