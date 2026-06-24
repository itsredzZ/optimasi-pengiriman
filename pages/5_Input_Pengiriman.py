"""
pages/5_Input_Pengiriman.py
===============================
Halaman "Input Pengiriman Harian" - Carry-over + Input pesanan baru.
PIC: Chelsea
"""

import streamlit as st
from db.database import get_session
from db.models import Item, DeliveryOrder, CarryoverItem, City, Setting
from datetime import date, datetime
import pandas as pd

st.set_page_config(page_title="Input Pengiriman Harian", page_icon="📝", layout="wide")


def init_session_state():
    """Inisialisasi session_state untuk pesanan hari ini."""
    if "pesanan_baru" not in st.session_state:
        st.session_state.pesanan_baru = []  # List of dict


def load_carryover_items(session):
    """Query carryover items yang belum resolved."""
    return (
        session.query(CarryoverItem)
        .filter(CarryoverItem.resolved == False)
        .all()
    )


def load_depot_options(session):
    """Load dropdown options untuk depot (kota dengan is_depot=True)."""
    depots = session.query(City).filter(
        City.is_depot == True, 
        City.is_active == True
    ).all()
    return {f"{d.name} (ID:{d.id})": d.id for d in depots}


def load_city_options(session):
    """Load dropdown options untuk semua kota aktif."""
    cities = session.query(City).filter(City.is_active == True).all()
    return {f"{c.name} (ID:{c.id})": c.id for c in cities}


def save_pesanan_to_db(session, pesanan_list, created_by=None):
    """Simpan list pesanan dari session_state ke database."""
    today = date.today()
    
    for pesanan in pesanan_list:
        # Buat DeliveryOrder header
        order = DeliveryOrder(
            order_date=today,
            origin_depot_id=pesanan["depot_asal_id"],
            destination_city_id=pesanan["kota_tujuan_id"],
            quantity=pesanan["jumlah"],
            source=pesanan.get("source", "manual"),
            created_by=created_by,
        )
        session.add(order)
        session.flush()  # Dapat order.id
        
        # Buat Item(s)
        for _ in range(pesanan["jumlah"]):
            item = Item(
                order_id=order.id,
                name=pesanan["nama_barang"],
                length_cm=pesanan["panjang"],
                width_cm=pesanan["lebar"],
                height_cm=pesanan["tinggi"],
                weight_kg=pesanan["berat"],
                status="menunggu",
                is_carryover=False,
            )
            session.add(item)
    
    session.commit()


def parse_excel_upload(uploaded_file, depot_map, city_map):
    """Parse file Excel dan return list pesanan."""
    try:
        df = pd.read_excel(uploaded_file)
        
        # Expected columns (case-insensitive)
        col_mapping = {
            "nama barang": "nama_barang",
            "nama_barang": "nama_barang",
            "nama": "nama_barang",
            "dimensi": "dimensi",
            "berat": "berat",
            "berat fisik": "berat",
            "berat_fisik": "berat",
            "depot asal": "depot_asal",
            "depot_asal": "depot_asal",
            "kota tujuan": "kota_tujuan",
            "kota_tujuan": "kota_tujuan",
            "jumlah": "jumlah",
        }
        
        # Rename columns
        df.columns = [col.lower().strip() for col in df.columns]
        df = df.rename(columns=col_mapping)
        
        pesanan_list = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Parse dimensi (format: "PxLxT" atau "P x L x T")
                dim_str = str(row.get("dimensi", "10x10x10"))
                dim_str = dim_str.replace(" ", "").replace("x", "x")
                parts = dim_str.split("x")
                if len(parts) != 3:
                    errors.append(f"Baris {idx+2}: Format dimensi salah '{dim_str}'")
                    continue
                panjang, lebar, tinggi = float(parts[0]), float(parts[1]), float(parts[2])
                
                # Cari depot ID
                depot_name = str(row.get("depot_asal", "")).strip()
                depot_id = None
                for key, val in depot_map.items():
                    if depot_name.lower() in key.lower():
                        depot_id = val
                        break
                
                # Cari kota tujuan ID
                kota_name = str(row.get("kota_tujuan", "")).strip()
                kota_id = None
                for key, val in city_map.items():
                    if kota_name.lower() in key.lower():
                        kota_id = val
                        break
                
                if not depot_id:
                    errors.append(f"Baris {idx+2}: Depot '{depot_name}' tidak ditemukan")
                    continue
                if not kota_id:
                    errors.append(f"Baris {idx+2}: Kota '{kota_name}' tidak ditemukan")
                    continue
                
                pesanan_list.append({
                    "nama_barang": str(row.get("nama_barang", f"Barang_{idx+1}")),
                    "panjang": panjang,
                    "lebar": lebar,
                    "tinggi": tinggi,
                    "berat": float(row.get("berat", 1.0)),
                    "depot_asal_id": depot_id,
                    "kota_tujuan_id": kota_id,
                    "jumlah": int(row.get("jumlah", 1)),
                    "source": "excel_upload",
                })
            except Exception as e:
                errors.append(f"Baris {idx+2}: {str(e)}")
        
        return pesanan_list, errors
    except Exception as e:
        return [], [f"Gagal membaca file Excel: {str(e)}"]


def main():
    init_session_state()
    
    st.title("📝 Input Pengiriman Harian")
    
    with get_session() as session:
        # ============================================
        # BAGIAN 1: CARRY-OVER
        # ============================================
        st.subheader("⚠️ Carry-Over dari Hari Sebelumnya")
        
        carryover_items = load_carryover_items(session)
        
        if carryover_items:
            st.warning(f"**{len(carryover_items)} barang** wajib masuk truk hari ini!")
            
            # Buat dataframe untuk tampilan
            carryover_data = []
            for co in carryover_items:
                item = session.query(Item).get(co.item_id)
                if item and item.order:
                    order = item.order
                    depot = session.query(City).get(order.origin_depot_id)
                    dest = session.query(City).get(order.destination_city_id)
                    carryover_data.append({
                        "ID": co.id,
                        "Nama Barang": item.name,
                        "Berat (kg)": item.weight_kg,
                        "Depot Asal": depot.name if depot else "-",
                        "Kota Tujuan": dest.name if dest else "-",
                        "Alasan": co.reason,
                    })
            
            if carryover_data:
                st.dataframe(
                    pd.DataFrame(carryover_data),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.success("✅ Tidak ada carry-over dari kemarin")
        
        st.divider()
        
        # ============================================
        # BAGIAN 2: INPUT PESANAN BARU
        # ============================================
        st.subheader("➕ Tambah Pesanan Baru")
        
        tab_form, tab_upload = st.tabs(["📝 Form Manual", "📊 Upload Excel"])
        
        # Load options untuk dropdown
        depot_options = load_depot_options(session)
        city_options = load_city_options(session)
        
        with tab_form:
            with st.form("form_pesanan_baru"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nama_barang = st.text_input("Nama Barang", placeholder="Contoh: Elektronik TV 55 inch")
                    
                    if depot_options:
                        selected_depot = st.selectbox("Depot Asal", list(depot_options.keys()))
                    else:
                        st.warning("Belum ada depot. Tambahkan di Master Data Kota.")
                        selected_depot = None
                    
                    if city_options:
                        selected_city = st.selectbox("Kota Tujuan", list(city_options.keys()))
                    else:
                        st.warning("Belum ada kota. Tambahkan di Master Data Kota.")
                        selected_city = None
                
                with col2:
                    berat = st.number_input("Berat per Paket (kg)", min_value=0.1, value=1.0, step=0.1)
                    jumlah = st.number_input("Jumlah Paket", min_value=1, value=1, step=1)
                
                st.subheader("📦 Dimensi per Paket (cm)")
                col3, col4, col5 = st.columns(3)
                with col3:
                    panjang = st.number_input("Panjang", min_value=1.0, value=50.0, step=1.0)
                with col4:
                    lebar = st.number_input("Lebar", min_value=1.0, value=40.0, step=1.0)
                with col5:
                    tinggi = st.number_input("Tinggi", min_value=1.0, value=30.0, step=1.0)
                
                # Validasi
                can_submit = all([nama_barang, selected_depot, selected_city])
                
                submitted = st.form_submit_button(
                    "➕ Tambah ke Pesanan Hari Ini",
                    type="primary",
                    disabled=not can_submit
                )
                
                if submitted:
                    pesanan = {
                        "nama_barang": nama_barang,
                        "panjang": panjang,
                        "lebar": lebar,
                        "tinggi": tinggi,
                        "berat": berat,
                        "depot_asal_id": depot_options[selected_depot],
                        "kota_tujuan_id": city_options[selected_city],
                        "jumlah": jumlah,
                        "source": "manual",
                    }
                    st.session_state.pesanan_baru.append(pesanan)
                    st.success(f"✅ Berhasil menambahkan **{jumlah} paket {nama_barang}**")
                    st.rerun()
        
        with tab_upload:
            st.info(
                "📋 **Format Excel:**\n"
                "| Nama Barang | Dimensi (PxLxT) | Berat Fisik (kg) | Depot Asal | Kota Tujuan | Jumlah |\n"
                "|-------------|------------------|------------------|------------|-------------|-------|"
            )
            
            uploaded_file = st.file_uploader(
                "Pilih file Excel",
                type=["xlsx", "xls"],
                key="excel_upload"
            )
            
            if uploaded_file:
                with st.spinner("Membaca file..."):
                    pesanan_list, errors = parse_excel_upload(
                        uploaded_file, depot_options, city_options
                    )
                
                if errors:
                    st.error("❌ Terjadi kesalahan:")
                    for err in errors:
                        st.warning(err)
                
                if pesanan_list:
                    st.success(f"✅ Berhasil membaca **{len(pesanan_list)} jenis pesanan**")
                    
                    # Tampilkan preview
                    preview_data = []
                    for p in pesanan_list:
                        preview_data.append({
                            "Nama Barang": p["nama_barang"],
                            "Dimensi": f"{p['panjang']}x{p['lebar']}x{p['tinggi']}",
                            "Berat (kg)": p["berat"],
                            "Jumlah": p["jumlah"],
                        })
                    
                    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
                    
                    if st.button("✅ Konfirmasi Tambahkan Semua", type="primary"):
                        st.session_state.pesanan_baru.extend(pesanan_list)
                        st.success(f"✅ {len(pesanan_list)} pesanan ditambahkan!")
                        st.rerun()
        
        st.divider()
        
        # ============================================
        # BAGIAN 3: RINGKASAN PESANAN HARI INI
        # ============================================
        st.subheader("📊 Ringkasan Pesanan Hari Ini")
        
        pesanan_baru = st.session_state.pesanan_baru
        total_paket_baru = sum(p["jumlah"] for p in pesanan_baru)
        total_paket_carryover = len(carryover_items)
        total_paket = total_paket_baru + total_paket_carryover
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Total Paket", str(total_paket))
        col2.metric("⚠️ Carry-Over", str(total_paket_carryover))
        col3.metric("🆕 Pesanan Baru", str(total_paket_baru))
        
        # Tabel pesanan baru yang sudah ditambahkan
        if pesanan_baru:
            with st.expander("📋 Daftar Pesanan Baru", expanded=True):
                pesanan_df = []
                for i, p in enumerate(pesanan_baru):
                    # Cari nama depot dan kota
                    depot_name = "?"
                    for key, val in depot_options.items():
                        if val == p["depot_asal_id"]:
                            depot_name = key.split(" (ID:")[0]
                            break
                    kota_name = "?"
                    for key, val in city_options.items():
                        if val == p["kota_tujuan_id"]:
                            kota_name = key.split(" (ID:")[0]
                            break
                    
                    pesanan_df.append({
                        "No": i + 1,
                        "Nama Barang": p["nama_barang"],
                        "Dimensi (cm)": f"{p['panjang']}x{p['lebar']}x{p['tinggi']}",
                        "Berat (kg)": p["berat"],
                        "Jumlah": p["jumlah"],
                        "Depot Asal": depot_name,
                        "Kota Tujuan": kota_name,
                    })
                
                st.dataframe(pd.DataFrame(pesanan_df), use_container_width=True, hide_index=True)
                
                # Tombol hapus semua
                if st.button("🗑️ Hapus Semua Pesanan Baru", type="secondary"):
                    st.session_state.pesanan_baru = []
                    st.rerun()
        
        st.divider()
        
        # ============================================
        # BAGIAN 4: TOMBOL OPTIMASI
        # ============================================
        can_optimize = total_paket > 0
        
        if st.button(
            "🚀 Optimalkan Pengiriman Sekarang",
            type="primary",
            use_container_width=True,
            disabled=not can_optimize
        ):
            # TODO: Integrasi dengan Valen (Hari 4)
            # 1. Simpan pesanan_baru ke database
            # 2. Panggil compute_optimization() dari Valen
            # 3. Redirect ke halaman 6_Optimasi_Hasil.py
            
            # Sementara: simpan ke DB dulu
            save_pesanan_to_db(session, pesanan_baru)
            st.session_state.pesanan_baru = []
            
            st.success("✅ Pesanan disimpan ke database!")
            st.info("🔄 Fitur optimasi akan terhubung setelah modul algoritma selesai (Valen).")
            
            # Nanti ganti dengan:
            # st.switch_page("pages/6_Optimasi_Hasil.py")


if __name__ == "__main__":
    main()