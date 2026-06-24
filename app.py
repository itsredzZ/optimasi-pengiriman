"""
app.py
=======
Entry point aplikasi XKargo.
Halaman utama menampilkan Dashboard setelah login.

Untuk sekarang: Dashboard dasar + test koneksi database.
Login akan diimplementasi oleh Richelle di 0_Login.py
"""

import streamlit as st
from db.database import get_session, test_connection
from db.models import SimulationResult, Item, Truck, CarryoverItem, City
from datetime import date, timedelta
import pandas as pd

st.set_page_config(
    page_title="XKargo",
    page_icon="🚛",
    layout="wide",
)


def get_today_stats(session):
    """Query statistik hari ini untuk metric cards."""
    today = date.today()
    
    # Profit hari ini
    profit_result = session.query(
        func.coalesce(func.sum(SimulationResult.net_profit), 0)
    ).filter(SimulationResult.run_date == today).scalar()
    
    # Barang terkirim hari ini
    terkirim_count = session.query(Item).join(DeliveryOrder).filter(
        DeliveryOrder.order_date == today,
        Item.status == "terkirim"
    ).count()
    
    # Carry-over yang belum resolved
    carryover_count = session.query(CarryoverItem).filter(
        CarryoverItem.resolved == False
    ).count()
    
    # Truk aktif
    truk_aktif = session.query(Truck).filter(Truck.is_active == True).count()
    
    return {
        "profit": float(profit_result) if profit_result else 0,
        "terkirim": terkirim_count,
        "carryover": carryover_count,
        "truk_aktif": truk_aktif,
    }


def get_profit_history(session, days=7):
    """Query riwayat profit beberapa hari terakhir."""
    start_date = date.today() - timedelta(days=days)
    
    results = session.query(
        SimulationResult.run_date,
        func.sum(SimulationResult.tariff_total).label("tarif"),
        func.sum(SimulationResult.fuel_cost).label("bbm"),
        func.sum(SimulationResult.net_profit).label("profit"),
    ).filter(
        SimulationResult.run_date >= start_date
    ).group_by(
        SimulationResult.run_date
    ).order_by(
        SimulationResult.run_date
    ).all()
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    df.columns = ["Tanggal", "Total Tarif", "Biaya BBM", "Profit Bersih"]
    return df


# Need to import func
from sqlalchemy import func
from db.models import DeliveryOrder


def main():
    # ============================================
    # HEADER
    # ============================================
    st.title("🚛 XKargo Dashboard")
    st.caption("Sistem Optimasi Distribusi Barang Multi-Depot di Jawa Timur")
    
    # Cek koneksi database
    if not test_connection():
        st.error(
            "❌ **Gagal konek ke database!**\n\n"
            "Pastikan:\n"
            "1. XAMPP (Apache + MySQL) sudah running\n"
            "2. Database `db_xkargo` sudah dibuat\n"
            "3. File `.env` sudah dikonfigurasi"
        )
        st.stop()
    
    with get_session() as session:
        # ============================================
        # METRIC CARDS
        # ============================================
        stats = get_today_stats(session)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Profit Hari Ini",
                value=f"Rp {stats['profit']:,.0f}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="📦 Barang Terkirim",
                value=str(stats["terkirim"]),
            )
        
        with col3:
            st.metric(
                label="⚠️ Carry-Over",
                value=str(stats["carryover"]),
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                label="🚛 Truk Aktif",
                value=str(stats["truk_aktif"]),
            )
        
        st.divider()
        
        # ============================================
        # REKAP PROFIT KUMULATIF
        # ============================================
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📈 Rekap Profit 7 Hari Terakhir")
            
            profit_df = get_profit_history(session, days=7)
            
            if profit_df.empty:
                st.info("Belum ada data simulasi. Jalankan optimasi pertama untuk melihat riwayat.")
            else:
                # Format angka
                for col in ["Total Tarif", "Biaya BBM", "Profit Bersih"]:
                    profit_df[col] = profit_df[col].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "Rp 0")
                
                st.dataframe(
                    profit_df,
                    use_container_width=True,
                    hide_index=True,
                )
        
        with col_right:
            st.subheader("📋 Status Cepat")
            
            # Cek apakah ada pesanan menunggu hari ini
            menunggu_count = session.query(Item).join(DeliveryOrder).filter(
                DeliveryOrder.order_date == date.today(),
                Item.status == "menunggu"
            ).count()
            
            if menunggu_count > 0:
                st.warning(f"📝 **{menunggu_count} barang** menunggu dioptimasi")
                if st.button("👉 Buka Input Pengiriman", use_container_width=True):
                    st.switch_page("pages/5_Input_Pengiriman.py")
            else:
                st.success("✅ Tidak ada barang menunggu hari ini")
            
            st.divider()
            
            # Posisi truk per depot
            st.subheader("🚛 Posisi Truk")
            depots = session.query(City).filter(City.is_depot == True).all()
            
            for depot in depots:
                trucks_at_depot = session.query(Truck).filter(
                    Truck.current_city_id == depot.id,
                    Truck.is_active == True
                ).count()
                
                if trucks_at_depot > 0:
                    st.markdown(f"**{depot.name}:** {trucks_at_depot} truk")
        
        st.divider()
        
        # ============================================
        # INFORMASI SETUP
        # ============================================
        with st.expander("ℹ️ Status Setup Sistem"):
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                city_count = session.query(City).count()
                depot_count = session.query(City).filter(City.is_depot == True).count()
                st.metric("🏙️ Kota / Depot", f"{city_count} / {depot_count}")
            
            with col_info2:
                truck_count = session.query(Truck).count()
                st.metric("🚛 Total Truk", str(truck_count))
            
            with col_info3:
                item_count = session.query(Item).count()
                st.metric("📦 Total Item", str(item_count))
            
            if city_count == 0 or truck_count == 0:
                st.warning(
                    "⚠️ **Setup belum lengkap!** Tambahkan data master di halaman sidebar:\n"
                    "- Master Data Kota & Jaringan\n"
                    "- Master Data Truk"
                )


if __name__ == "__main__":
    main()