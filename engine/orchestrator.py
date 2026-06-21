"""
engine/orchestrator.py
========================
Entry point SATU HARI yang akan dipanggil halaman Streamlit
"6_Optimasi_Hasil.py" saat tombol "Optimalkan Pengiriman Sekarang" diklik.

Ini pengganti run_multiday_pso() dari kode asli, yang dulu menjalankan
BANYAK hari sekaligus dalam satu pemanggilan fungsi (cocok untuk
eksperimen di Colab, tidak cocok untuk aplikasi web di mana satu hari
= satu klik tombol oleh operator, dengan state tersimpan di database
di antara dua hari).

Fungsi relokasi (putuskan_relokasi_truk) SENGAJA dipisah, tidak dipanggil
otomatis di sini -> karena butuh preview item BESOK yang baru tersedia
saat operator membuka halaman Input Pengiriman hari berikutnya. Lihat
relocation.py untuk dipanggil terpisah dari halaman tersebut.
"""

from engine.pso_engine import run_pso


def run_daily_optimization(items, trucks, adj, city_idx, cities, coords,
                            depot_names, pso_params, op_params,
                            progress_callback=None):
    """
    Jalankan satu siklus optimasi untuk satu hari.

    Parameter:
      items   : list item dict (lihat data_models.item_to_algo_dict), HARUS
                sudah berisi gabungan carry-over (is_carryover=True) + barang
                baru hari ini, dan setiap item sudah punya 'truck_id' yang
                valid (truk yang ada di depot asal item tersebut). Item yang
                depotnya kosong truk JANGAN dimasukkan ke sini -- treat
                sebagai auto-carryover oleh caller (lihat catatan di bawah).
      trucks  : list TruckState -- truk yang beroperasi hari ini (posisi
                current_city sudah sesuai akhir hari kemarin)

    Mengembalikan dict siap pakai untuk:
      - disimpan ke `simulation_results` (satu baris per truck_id di
        result["best_routes"])
      - disimpan ke `carryover_items` (result["carryover_items"])
      - update posisi truk untuk hari berikutnya (result["truck_depot_akhir"])
      - render Plotly di halaman hasil (result["gbest_curve"],
        result["velocity_breakdown"])
    """
    from engine.relocation import get_carryover_items, update_posisi_truk

    pso_result = run_pso(
        items=items,
        trucks=trucks,
        adj=adj, city_idx=city_idx, cities=cities, coords=coords,
        depot_names=depot_names,
        pso_params=pso_params,
        op_params=op_params,
        progress_callback=progress_callback,
    )

    truck_depot_current = {t.id: t.current_city for t in trucks}
    truck_depot_akhir = update_posisi_truk(pso_result["best_routes"], truck_depot_current)
    carryover_items = get_carryover_items(items, pso_result["best_routes"])

    total_tarif = sum(r["tarif"] for r in pso_result["best_routes"].values())
    total_bbm = sum(r["biaya_bbm"] for r in pso_result["best_routes"].values())
    n_terkirim = sum(len(r["items"]) for r in pso_result["best_routes"].values())

    return {
        **pso_result,
        "truck_depot_akhir": truck_depot_akhir,
        "carryover_items": carryover_items,
        "total_tarif": total_tarif,
        "total_bbm": total_bbm,
        "n_terkirim": n_terkirim,
        "n_carryover": len(carryover_items),
    }