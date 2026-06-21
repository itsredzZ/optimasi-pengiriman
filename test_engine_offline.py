"""
test_engine_offline.py
========================
Sanity test untuk folder engine/ TANPA perlu database menyala — memakai
graph kota & truk sintetis. Jalankan ini duluan untuk memastikan algoritma
PSO/A*/Guillotine/relokasi tidak error, SEBELUM mencoba hubungkan ke MySQL.

Cara jalankan:
    python test_engine_offline.py
"""

from engine.data_models import TruckState
from engine.config import PSOParams, OperationalParams
from engine.dev_data_generator import generate_dummy_items
from engine.orchestrator import run_daily_optimization
from engine.relocation import putuskan_relokasi_truk

# ---- Graph sintetis: 4 kota, 2 di antaranya depot ----
cities = ["Surabaya", "Malang", "Kediri", "Madiun"]
city_idx = {c: i for i, c in enumerate(cities)}
coords = {
    "Surabaya": (-7.2575, 112.7521),
    "Malang":   (-7.9797, 112.6304),
    "Kediri":   (-7.8168, 111.9668),
    "Madiun":   (-7.6298, 111.5239),
}
adj = [
    [0,   90,  130, 170],
    [90,  0,   100, 220],
    [130, 100, 0,   120],
    [170, 220, 120, 0],
]
depot_names = ["Surabaya", "Malang"]

# ---- 2 truk dengan kapasitas BERBEDA (menguji generalisasi multi-truk) ----
trucks = [
    TruckState(id=1, plate_number="L1001XK", max_weight_kg=500,
               box_p=180, box_l=120, box_t=120,
               home_depot="Surabaya", current_city="Surabaya"),
    TruckState(id=2, plate_number="L1002XK", max_weight_kg=800,
               box_p=200, box_l=130, box_t=130,
               home_depot="Malang", current_city="Malang"),
]

pso_params = PSOParams(n_partikel=8, n_iterasi=15, early_stop=5, base_seed=42)
op_params = OperationalParams()

print("=== TEST 1: generate_dummy_items ===")
items = generate_dummy_items(trucks, depot_names, cities, n_min=5, n_max=8, seed=1)
print(f"  {len(items)} item dummy ter-generate")
assert len(items) > 0

print("\n=== TEST 2: run_daily_optimization (PSO + A* + Guillotine) ===")


def progress_cb(it, n_iter, gbest):
    if it % 5 == 0 or it == n_iter:
        print(f"  iter {it}/{n_iter}  gbest=Rp{gbest:,.0f}")


result = run_daily_optimization(
    items=items, trucks=trucks,
    adj=adj, city_idx=city_idx, cities=cities, coords=coords,
    depot_names=depot_names,
    pso_params=pso_params, op_params=op_params,
    progress_callback=progress_cb,
)

print(f"\n  Gbest val        : Rp{result['gbest_val']:,.0f}")
print(f"  Truk beroperasi  : {list(result['best_routes'].keys())}")
print(f"  Terkirim         : {result['n_terkirim']} item")
print(f"  Carry-over       : {result['n_carryover']} item")
print(f"  Kurva gbest (panjang)        : {len(result['gbest_curve'])}")
print(f"  Velocity breakdown (panjang) : {len(result['velocity_breakdown'])}")
print(f"  Posisi truk akhir : {result['truck_depot_akhir']}")

print("\n=== TEST 3: putuskan_relokasi_truk ===")
truck_depot_current = {1: "Surabaya", 2: "Surabaya"}  # Malang sengaja dikosongkan
items_by_depot_next = {
    "Malang": [
        {"berat_tagihan": 10, "kota_tujuan": "Kediri", "faktor": 1.0},
        {"berat_tagihan": 15, "kota_tujuan": "Madiun", "faktor": 1.3},
    ]
}
cache = {}
decisions, updated = putuskan_relokasi_truk(
    truck_depot_current, items_by_depot_next,
    adj, city_idx, cities, coords, cache, op_params, depot_names,
)
print(f"  Keputusan  : {decisions}")
print(f"  Posisi truk setelah relokasi: {updated}")

print("\n✓ SEMUA TEST LULUS — engine berjalan tanpa error.")
