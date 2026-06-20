-- ============================================================
-- XKargo — Database Schema (sesuai ERD proposal)
-- Target: MySQL / MariaDB via XAMPP + phpMyAdmin
--
-- CARA PAKAI:
-- 1. Buka phpMyAdmin (http://localhost/phpmyadmin)
-- 2. Buat database baru bernama: db_xkargo  (collation: utf8mb4_general_ci)
-- 3. Klik database db_xkargo -> tab "Import" -> pilih file ini -> Go
--    ATAU klik tab "SQL" -> paste seluruh isi file ini -> Go
-- ============================================================

CREATE DATABASE IF NOT EXISTS xkargo_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE xkargo_db;

-- Hapus tabel lama jika re-run (urutan dibalik dari FK dependency)
DROP TABLE IF EXISTS relocation_logs;
DROP TABLE IF EXISTS carryover_items;
DROP TABLE IF EXISTS simulation_results;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS delivery_orders;
DROP TABLE IF EXISTS depot_distances;
DROP TABLE IF EXISTS trucks;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS users;


-- ============================================================
-- 1. users — akun admin/operator
-- ============================================================
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('admin', 'operator') NOT NULL DEFAULT 'operator',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 2. cities — master kota & status depot
-- ============================================================
CREATE TABLE cities (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    latitude        DECIMAL(9,6) NOT NULL,
    longitude       DECIMAL(9,6) NOT NULL,
    is_depot        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;


-- ============================================================
-- 3. depot_distances — matrix jarak antar kota (km)
--    Satu baris = satu pasangan kota (city_a -> city_b)
-- ============================================================
CREATE TABLE depot_distances (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    city_a_id       INT NOT NULL,
    city_b_id       INT NOT NULL,
    distance_km     DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_dist_city_a FOREIGN KEY (city_a_id) REFERENCES cities(id) ON DELETE CASCADE,
    CONSTRAINT fk_dist_city_b FOREIGN KEY (city_b_id) REFERENCES cities(id) ON DELETE CASCADE,
    CONSTRAINT uq_city_pair UNIQUE (city_a_id, city_b_id)
) ENGINE=InnoDB;


-- ============================================================
-- 4. trucks — master armada truk
-- ============================================================
CREATE TABLE trucks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    plate_number    VARCHAR(20) NOT NULL UNIQUE,
    max_weight_kg   DECIMAL(10,2) NOT NULL,
    length_cm       DECIMAL(8,2) NOT NULL,
    width_cm        DECIMAL(8,2) NOT NULL,
    height_cm       DECIMAL(8,2) NOT NULL,
    home_depot_id   INT NOT NULL,
    current_city_id INT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_truck_home_depot FOREIGN KEY (home_depot_id)   REFERENCES cities(id),
    CONSTRAINT fk_truck_current_city FOREIGN KEY (current_city_id) REFERENCES cities(id)
) ENGINE=InnoDB;


-- ============================================================
-- 5. delivery_orders — header pesanan pengiriman harian
-- ============================================================
CREATE TABLE delivery_orders (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    order_date              DATE NOT NULL,
    origin_depot_id         INT NOT NULL,
    destination_city_id     INT NOT NULL,
    quantity                INT NOT NULL DEFAULT 1,
    source                  ENUM('manual', 'excel_upload') NOT NULL DEFAULT 'manual',
    created_by              INT NULL,
    CONSTRAINT fk_order_origin      FOREIGN KEY (origin_depot_id)     REFERENCES cities(id),
    CONSTRAINT fk_order_destination FOREIGN KEY (destination_city_id) REFERENCES cities(id),
    CONSTRAINT fk_order_created_by  FOREIGN KEY (created_by)          REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============================================================
-- 6. items — barang per pesanan (dimensi, berat, status)
-- ============================================================
CREATE TABLE items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    order_id        INT NOT NULL,
    name            VARCHAR(150) NOT NULL,
    length_cm       DECIMAL(8,2) NOT NULL,
    width_cm        DECIMAL(8,2) NOT NULL,
    height_cm       DECIMAL(8,2) NOT NULL,
    weight_kg       DECIMAL(10,2) NOT NULL,
    status          ENUM('menunggu', 'terkirim', 'carryover') NOT NULL DEFAULT 'menunggu',
    is_carryover    BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_item_order FOREIGN KEY (order_id) REFERENCES delivery_orders(id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 7. simulation_results — hasil tiap run PSO per truk
-- ============================================================
CREATE TABLE simulation_results (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    run_date            DATE NOT NULL,
    truck_id            INT NOT NULL,
    route_json          JSON NULL,
    total_weight_kg     DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_volume_m3     DECIMAL(10,4) NOT NULL DEFAULT 0,
    tariff_total        DECIMAL(14,2) NOT NULL DEFAULT 0,
    fuel_cost           DECIMAL(14,2) NOT NULL DEFAULT 0,
    net_profit          DECIMAL(14,2) NOT NULL DEFAULT 0,
    gbest_curve_json    JSON NULL,
    CONSTRAINT fk_simresult_truck FOREIGN KEY (truck_id) REFERENCES trucks(id)
) ENGINE=InnoDB;


-- ============================================================
-- 8. carryover_items — barang gagal terkirim, dibawa ke hari berikutnya
-- ============================================================
CREATE TABLE carryover_items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    item_id         INT NOT NULL,
    carryover_date  DATE NOT NULL,
    reason          ENUM('overflow_berat', 'overflow_volume', 'guillotine_gagal', 'depot_tanpa_truk') NOT NULL,
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_carryover_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 9. relocation_logs — riwayat keputusan relokasi truk antar depot
-- ============================================================
CREATE TABLE relocation_logs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    run_date            DATE NOT NULL,
    truck_id            INT NOT NULL,
    from_depot_id       INT NOT NULL,
    to_depot_id         INT NOT NULL,
    relocation_cost     DECIMAL(14,2) NOT NULL DEFAULT 0,
    decision            ENUM('relokasi', 'carryover') NOT NULL,
    CONSTRAINT fk_reloc_truck FOREIGN KEY (truck_id)      REFERENCES trucks(id),
    CONSTRAINT fk_reloc_from  FOREIGN KEY (from_depot_id) REFERENCES cities(id),
    CONSTRAINT fk_reloc_to    FOREIGN KEY (to_depot_id)   REFERENCES cities(id)
) ENGINE=InnoDB;


-- ============================================================
-- 10. settings — parameter PSO & operasional (dapat diubah admin)
-- ============================================================
CREATE TABLE settings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    param_group     ENUM('pso', 'operasional') NOT NULL,
    param_key       VARCHAR(50) NOT NULL,
    param_value     VARCHAR(50) NOT NULL,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_param UNIQUE (param_group, param_key)
) ENGINE=InnoDB;


-- ============================================================
-- SEED DATA — nilai default supaya aplikasi langsung jalan
-- ============================================================

-- 6 kota depot default (sesuai DEPOT_MAP di engine PSO kalian)
INSERT INTO cities (name, latitude, longitude, is_depot, is_active) VALUES
('Surabaya', -7.257500, 112.752100, TRUE, TRUE),
('Malang',   -7.979700, 112.630400, TRUE, TRUE),
('Kediri',   -7.816800, 111.966800, TRUE, TRUE),
('Madiun',   -7.629800, 111.523900, TRUE, TRUE),
('Jember',   -8.184500, 113.668000, TRUE, TRUE),
('Tuban',    -6.899700, 112.050800, TRUE, TRUE);

-- Parameter PSO default (sesuai konstanta di pso_no2_last_boss.py)
INSERT INTO settings (param_group, param_key, param_value) VALUES
('pso', 'n_partikel',        '30'),
('pso', 'n_iterasi',         '100'),
('pso', 'early_stop_iter',   '20'),
('pso', 'w_max',             '0.9'),
('pso', 'w_min',             '0.4'),
('pso', 'c1',                '2.0'),
('pso', 'c2',                '2.0'),
('pso', 'base_seed',         '42');

-- Parameter operasional default
INSERT INTO settings (param_group, param_key, param_value) VALUES
('operasional', 'harga_solar',        '6800'),
('operasional', 'tarif_dasar',        '20'),
('operasional', 'bbm_base',           '0.08'),
('operasional', 'bbm_faktor',         '0.02'),
('operasional', 'box_default_p_cm',   '200'),
('operasional', 'box_default_l_cm',   '130'),
('operasional', 'box_default_t_cm',   '130'),
('operasional', 'box_default_berat_max_kg', '1000');

-- Contoh 1 truk per depot (silakan tambah/edit lewat halaman Manajemen Truk nanti)
INSERT INTO trucks (plate_number, max_weight_kg, length_cm, width_cm, height_cm, home_depot_id, current_city_id, is_active)
SELECT CONCAT('L 1', LPAD(id, 3, '0'), ' XK'), 1000, 200, 130, 130, id, id, TRUE
FROM cities WHERE is_depot = TRUE;

-- Akun admin default — GANTI password ini, jangan dipakai untuk produksi!
-- password_hash di bawah HARUS diisi ulang lewat script Python (bcrypt),
-- baris ini hanya placeholder agar tabel tidak kosong.
INSERT INTO users (username, password_hash, role) VALUES
('admin', 'GANTI_DENGAN_HASH_BCRYPT', 'admin');
