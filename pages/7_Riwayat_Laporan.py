# pages/7_Riwayat_Laporan.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.title("📋 Riwayat & Laporan")

# ── Filter tanggal ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Dari tanggal", value=date.today() - timedelta(days=7))
with col2:
    end_date = st.date_input("Sampai tanggal", value=date.today())

if start_date > end_date:
    st.error("Tanggal mulai tidak boleh lebih dari tanggal akhir.")
    st.stop()

# ── Ambil data dari DB ──────────────────────────────────────────────────────
try:
    from db.database import get_session
    from db.models import SimulationResult
    with get_session() as session:
        rows = session.query(SimulationResult).filter(
            SimulationResult.run_date >= start_date,
            SimulationResult.run_date <= end_date,
        ).all()
    df = pd.DataFrame([{
        "Tanggal":            r.run_date,
        "Barang Terkirim":    r.total_weight_kg,
        "Total Tarif (Rp)":   r.tariff_total,
        "Biaya BBM (Rp)":     r.fuel_cost,
        "Profit Bersih (Rp)": r.net_profit,
        "Carry-Over":         "-",
    } for r in rows])

    # ← Tambahkan ini: kalau DB kosong, pakai dummy
    if df.empty:
        raise ValueError("DB kosong, pakai dummy")

except Exception:
    df = pd.DataFrame({
        "Tanggal":            pd.date_range(start_date, periods=5),
        "Barang Terkirim":    [12, 15, 10, 18, 14],
        "Total Tarif (Rp)":   [4500000, 5200000, 3800000, 6100000, 4900000],
        "Biaya BBM (Rp)":     [850000, 920000, 730000, 1100000, 880000],
        "Profit Bersih (Rp)": [3650000, 4280000, 3070000, 5000000, 4020000],
        "Carry-Over":         [2, 0, 3, 1, 0],
    })
    st.info("Menampilkan data dummy — belum ada data simulasi.", icon="ℹ️")

# ── Tampilkan tabel ─────────────────────────────────────────────────────────
st.dataframe(
    df.style.format({
        "Total Tarif (Rp)":   "Rp {:,.0f}",
        "Biaya BBM (Rp)":     "Rp {:,.0f}",
        "Profit Bersih (Rp)": "Rp {:,.0f}",
    }),
    use_container_width=True,
)

# ── Ringkasan ───────────────────────────────────────────────────────────────
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Profit Bersih", f"Rp {df['Profit Bersih (Rp)'].sum():,.0f}")
    c2.metric("Total Barang Terkirim", int(df["Barang Terkirim"].sum()))
    c3.metric("Total Carry-Over", str(df["Carry-Over"].replace("-", 0).sum()))

st.divider()

col_xl, col_pdf = st.columns(2)

# ── Export Excel ────────────────────────────────────────────────────────────
with col_xl:
    import io
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        label="⬇️ Export Excel",
        data=buffer.getvalue(),
        file_name=f"laporan_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="btn_export_excel",
    )

# ── Export PDF ──────────────────────────────────────────────────────────────
with col_pdf:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Judul
    elements.append(Paragraph("Laporan Riwayat XKargo", styles['Title']))
    elements.append(Paragraph(f"Periode: {start_date} s/d {end_date}", styles['Normal']))
    elements.append(Spacer(1, 16))

    # Data tabel
    data = [list(df.columns)]  # header
    for _, row in df.iterrows():
        data.append([str(v) for v in row.values])

    # Buat tabel
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#1e2130')),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, 0),  8),
        ('ALIGN',        (0, 0), (-1, 0),  'CENTER'),
        # Isi
        ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',     (0, 1), (-1, -1), 8),
        ('ALIGN',        (0, 1), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        # Border
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    # Ringkasan
    elements.append(Spacer(1, 16))
    total_profit = f"Rp {df['Profit Bersih (Rp)'].sum():,.0f}"
    total_barang = int(df["Barang Terkirim"].sum())
    elements.append(Paragraph(f"<b>Total Profit Bersih:</b> {total_profit}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total Barang Terkirim:</b> {total_barang}", styles['Normal']))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()  # sudah pasti bytes, tidak perlu konversi

    st.download_button(
        label="⬇️ Export PDF",
        data=pdf_bytes,
        file_name=f"laporan_{start_date}_{end_date}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="btn_export_pdf",
    )