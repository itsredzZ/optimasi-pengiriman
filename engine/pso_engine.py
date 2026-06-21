"""
engine/pso_engine.py
======================
Inti algoritma PSO — w dinamis (linear decay), inisialisasi random murni,
PSO Direct Order. Logika numerik identik dengan kode asli. Dua perubahan:

  1. TIDAK ADA print() sama sekali. Kode asli mencetak progress ke console
     (gaya Colab). Di sini setiap langkah penting di-return sebagai data
     terstruktur, supaya Streamlit bisa render via st.dataframe/Plotly,
     dan hasilnya bisa disimpan ke `simulation_results`.

  2. Velocity breakdown DITANGKAP. Kode asli menghitung w*v, c1*r1*(pbest-x),
     c2*r2*(gbest-x) lalu langsung menjumlahkannya (komponennya dibuang).
     Proposal menjanjikan chart "PSO Velocity Breakdown" yang butuh
     ketiga komponen ini terpisah per iterasi -> sekarang direkam.

  progress_callback (opsional): dipanggil tiap iterasi dengan
  (current_iter, n_iterasi, gbest_val) supaya halaman Streamlit bisa
  update st.progress()/st.spinner() secara live.
"""

import numpy as np

from engine.fitness import evaluate_fitness


def init_particle_random(n_items: int, rng: np.random.Generator):
    return np.round(rng.uniform(0.00, 0.99, n_items), 2)


def compute_w(it: int, n_iterasi: int, w_max: float, w_min: float) -> float:
    """w(t) = W_MAX - (W_MAX - W_MIN) * (t / N_ITERASI)  (linear decay)."""
    return w_max - (w_max - w_min) * (it / n_iterasi)


def update_velocity(v_lama, x_lama, pbest, gbest, w, c1, c2, rng: np.random.Generator):
    """
    V_baru = w*V_lama + c1*r1*(Pbest-X) + c2*r2*(Gbest-X)

    Mengembalikan (v_baru, komponen) di mana `komponen` adalah dict berisi
    magnitude rata-rata (mean absolute) tiap suku, untuk visualisasi
    PSO Velocity Breakdown.
    """
    n = len(v_lama)
    r1 = rng.uniform(0, 1, n)
    r2 = rng.uniform(0, 1, n)

    suku_inersia = w * v_lama
    suku_kognitif = c1 * r1 * (pbest - x_lama)
    suku_sosial = c2 * r2 * (gbest - x_lama)

    v_baru = suku_inersia + suku_kognitif + suku_sosial

    komponen = {
        "inersia": float(np.mean(np.abs(suku_inersia))),
        "kognitif": float(np.mean(np.abs(suku_kognitif))),
        "sosial": float(np.mean(np.abs(suku_sosial))),
    }
    return v_baru, komponen


def update_position(x_lama, v_baru):
    """X_baru = X_lama + V_baru, dengan wrap-around ke range [0.00, 0.99]."""
    x_baru = x_lama + v_baru
    x_baru = np.where(x_baru < 0.00, x_baru + 1.0, x_baru)
    x_baru = np.where(x_baru > 0.99, x_baru - 1.0, x_baru)
    x_baru = np.clip(x_baru, 0.00, 0.99)
    return np.round(x_baru, 2)


def run_pso(items, trucks, adj, city_idx, cities, coords, depot_names,
            pso_params, op_params, progress_callback=None):
    """
    Jalankan PSO lengkap untuk satu hari/satu batch item.

    Mengembalikan dict siap-pakai untuk disimpan ke `simulation_results`
    dan dirender di halaman Optimasi & Hasil:

      {
        "gbest_val": float,
        "gbest_pos": np.ndarray,
        "best_routes": dict (truck_id -> detail rute, lihat fitness.py),
        "gbest_curve": list[float]           -> untuk Grafik Konvergensi
        "velocity_breakdown": list[dict]     -> untuk PSO Velocity Breakdown
        "n_iterasi_aktual": int,
        "early_stopped": bool,
      }
    """
    n_items = len(items)
    cache = {}  # cache A* untuk satu run optimasi ini (lihat astar.py)
    rng = np.random.default_rng(pso_params.base_seed)

    def fitness_of(particle):
        return evaluate_fitness(
            particle, items, trucks, adj, city_idx, cities, coords,
            cache, op_params, depot_names,
        )

    # ---- Inisialisasi (iterasi ke-0): semua partikel RANDOM ----
    particles, velocities, pbest_pos, pbest_val = [], [], [], []
    for _ in range(pso_params.n_partikel):
        x = init_particle_random(n_items, rng)
        v = np.zeros(n_items)
        fitness, _ = fitness_of(x)

        particles.append(x.copy())
        velocities.append(v.copy())
        pbest_pos.append(x.copy())
        pbest_val.append(fitness)

    gbest_idx = int(np.argmax(pbest_val))
    gbest_pos = pbest_pos[gbest_idx].copy()
    gbest_val = pbest_val[gbest_idx]

    gbest_curve = [gbest_val]
    velocity_breakdown = []  # belum ada velocity di iterasi 0
    no_improve_count = 0
    early_stopped = False
    it_terakhir = 0

    if progress_callback:
        progress_callback(0, pso_params.n_iterasi, gbest_val)

    # ---- Iterasi PSO ----
    for it in range(1, pso_params.n_iterasi + 1):
        it_terakhir = it
        w_saat_ini = compute_w(it, pso_params.n_iterasi, pso_params.w_max, pso_params.w_min)

        komponen_iter = {"inersia": 0.0, "kognitif": 0.0, "sosial": 0.0}

        for p in range(pso_params.n_partikel):
            v_baru, komponen_p = update_velocity(
                velocities[p], particles[p], pbest_pos[p], gbest_pos,
                w=w_saat_ini, c1=pso_params.c1, c2=pso_params.c2, rng=rng,
            )
            x_baru = update_position(particles[p], v_baru)
            fitness_baru, _ = fitness_of(x_baru)

            particles[p] = x_baru
            velocities[p] = v_baru

            for k in komponen_iter:
                komponen_iter[k] += komponen_p[k]

            if fitness_baru > pbest_val[p]:
                pbest_pos[p] = x_baru.copy()
                pbest_val[p] = fitness_baru

        # Rata-rata komponen velocity di iterasi ini (untuk chart)
        for k in komponen_iter:
            komponen_iter[k] /= pso_params.n_partikel
        komponen_iter["iterasi"] = it
        komponen_iter["w"] = w_saat_ini
        velocity_breakdown.append(komponen_iter)

        # Update Global Best
        best_p = int(np.argmax(pbest_val))
        if pbest_val[best_p] > gbest_val:
            gbest_pos = pbest_pos[best_p].copy()
            gbest_val = pbest_val[best_p]
            no_improve_count = 0
        else:
            no_improve_count += 1

        gbest_curve.append(gbest_val)

        if progress_callback:
            progress_callback(it, pso_params.n_iterasi, gbest_val)

        if no_improve_count >= pso_params.early_stop:
            early_stopped = True
            break

    _, best_routes = fitness_of(gbest_pos)

    return {
        "gbest_val": float(gbest_val),
        "gbest_pos": gbest_pos,
        "best_routes": best_routes,
        "gbest_curve": gbest_curve,
        "velocity_breakdown": velocity_breakdown,
        "n_iterasi_aktual": it_terakhir,
        "early_stopped": early_stopped,
    }