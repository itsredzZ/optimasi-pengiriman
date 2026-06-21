Folder ini akan diisi modul algoritma hasil refactor dari `pso_no2_last_boss.py`:

- data_models.py   -> struktur data item, truk, depot
- pso_engine.py    -> init_particle, update_velocity, update_position, run_pso
- astar.py         -> astar_distance, astar_cached, load_adjacency_matrix
- routing.py       -> nearest_neighbor_route, guillotine_pack, Ruang
- fitness.py       -> evaluate_fitness, hitung_tarif_per_barang, hitung_konsumsi_bbm
- relocation.py    -> putuskan_relokasi_truk, update_posisi_truk

Lihat catatan refactor di chat sebelumnya untuk daftar lengkap perubahan yang diperlukan
(parameter dari DB, bukan konstanta global; return value terstruktur, bukan print()).
