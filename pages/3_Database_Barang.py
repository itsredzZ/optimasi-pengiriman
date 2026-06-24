"""
pages/3_Database_Barang.py
==============================
Halaman "Database Barang" - Menampilkan semua item yang pernah diinput.
PIC: Chelsea
"""

import streamlit as st
from db.database import get_session
from db.models import Item, DeliveryOrder, City, CarryoverItem
from datetime import date
import pandas as pd

st.set_page_config(page_title="Database Barang", page_icon="📦", layout="wide")


def load_items_to_dataframe(session, filter_status, filter_depot_id, filter_date):
    """Query items berdasarkan filter, return DataFrame."""
    query = (
        session.query(
            Item.id,
            Item.name,
            Item.length_cm,
            Item.width_cm,
            Item.height_cm,
            Item.weight_kg,
            Item.status,
            Item.is_carryover,
            DeliveryOrder.order_date,
            DeliveryOrder.quantity,
            City.name.label("depot_asal"),
            City.name.label("kota_tujuan"),  # Akan di-fix di join
        )
        .join(DeliveryOrder, Item.order_id == DeliveryOrder.id)
        .outerjoin(City, DeliveryOrder.origin_depot_id == City.id)
    )
    
    # Filter status
    if filter_status != "Semua":
        status_map = {
            "Menunggu": "menunggu",
            "Terkirim": "terkirim",
            "Carry-over": "carryover",
        }
        if filter_status in status_map:
            query = query.filter(Item.status == status_map[filter_status])
    
    # Filter depot
    if filter_depot_id:
        query = query.filter(DeliveryOrder.origin_depot_id == filter_depot_id)
    
    # Filter tanggal
    if filter_date:
        query = query.filter(DeliveryOrder.order_date == filter_date)
    
    results = query.all()
    
    if not results:
        return pd.DataFrame()
    
    # Query kota tujuan terpisah (karena join City sudah dipakai untuk depot)
    # Alternatif: subquery, tapi untuk simplicity kita update setelah
    df = pd.DataFrame(results)
    
    # Update kota_tujuan dengan query terpisah
    for idx, row in df.iterrows():
        order = session.query(DeliveryOrder).get(row["order_id"])
        if order:
            dest_city = session.query(City).get(order.destination_city_id)
            if dest_city:
                df.at[idx, "kota_tujuan"] = dest_city.name
    
    return df


def main():
    st.title("📦 Database Barang")
    st.caption("Daftar semua item yang pernah diinput ke sistem")
    
    with get_session() as session:
        # ============================================
        # FILTER SECTION
        # ============================================
        with st.expander("🔍 Filter Data", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_status = st.selectbox(
                    "Status", 
                    ["Semua", "Menunggu", "Terkirim", "Carry-over"],
                    key="filter_status"
                )
            
            with col2:
                # Query depot untuk dropdown
                depots = session.query(City).filter(City.is_depot == True, City.is_active == True).all()
                depot_options = {"Semua": None}
                for d in depots:
                    depot_options[d.name] = d.id
                
                selected_depot = st.selectbox(
                    "Depot Asal",
                    list(depot_options.keys()),
                    key="filter_depot"
                )
                filter_depot_id = depot_options[selected_depot]
            
            with col3:
                filter_date = st.date_input("Tanggal Pesanan", value=None, key="filter_date")
        
        st.divider()
        
        # ============================================
        # LOAD & TAMPILKAN DATA
        # ============================================
        df = load_items_to_dataframe(session, filter_status, filter_depot_id, filter_date)
        
        if df.empty:
            st.info("Tidak ada data barang yang sesuai filter.")
            return
        
        # Rename kolom untuk tampilan
        display_df = df.rename(columns={
            "id": "ID",
            "name": "Nama Barang",
            "length_cm": "P (cm)",
            "width_cm": "L (cm)",
            "height_cm": "T (cm)",
            "weight_kg": "Berat (kg)",
            "status": "Status",
            "is_carryover": "Carry-Over",
            "order_date": "Tanggal",
            "quantity": "Jumlah",
            "depot_asal": "Depot Asal",
            "kota_tujuan": "Kota Tujuan",
        })
        
        # Format status untuk tampilan
        status_map = {
            "menunggu": "⏳ Menunggu",
            "terkirim": "✅ Terkirim",
            "carryover": "⚠️ Carry-over",
        }
        display_df["Status"] = display_df["Status"].map(status_map).fillna(display_df["Status"])
        
        # Format carry-over
        display_df["Carry-Over"] = display_df["Carry-Over"].apply(lambda x: "Ya" if x else "Tidak")
        
        # Tampilkan dengan data_editor (read-only untuk sekarang)
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(disabled=True),
                "P (cm)": st.column_config.NumberColumn(format="%.1f"),
                "L (cm)": st.column_config.NumberColumn(format="%.1f"),
                "T (cm)": st.column_config.NumberColumn(format="%.1f"),
                "Berat (kg)": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        
        st.divider()
        
        # ============================================
        # TOMBOL KONFIRMASI TERKIRIM
        # ============================================
        st.subheader("✅ Konfirmasi Barang Terkirim")
        
        # Query item yang statusnya "menunggu"
        waiting_items = session.query(Item).filter(Item.status == "menunggu").all()
        
        if not waiting_items:
            st.success("Semua barang sudah diproses!")
            return
        
        st.caption(f"{len(waiting_items)} barang menunggu konfirmasi:")
        
        # Tampilkan per item dengan tombol
        cols = st.columns(2)
        for i, item in enumerate(waiting_items):
            with cols[i % 2]:
                with st.container(border=True):
                    order = session.query(DeliveryOrder).get(item.order_id)
                    depot = session.query(City).get(order.origin_depot_id) if order else None
                    dest = session.query(City).get(order.destination_city_id) if order else None
                    
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"**{item.name}**")
                        st.caption(f"{item.weight_kg}kg | {depot.name if depot else '-'} → {dest.name if dest else '-'}")
                    with col_btn:
                        if st.button("✓", key=f"confirm_{item.id}", type="primary"):
                            item.status = "terkirim"
                            session.commit()
                            st.rerun()


if __name__ == "__main__":
    main()