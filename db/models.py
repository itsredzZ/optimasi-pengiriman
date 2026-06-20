"""
db/models.py
=============
ORM models — definisi tabel dengan SQLAlchemy, harus tetap SINKRON dengan
schema.sql (ERD). Jika ada perubahan struktur tabel, ubah KEDUANYA:
schema.sql (sumber kebenaran untuk phpMyAdmin) dan file ini (dipakai kode Python).
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, JSON,
    Numeric, String, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("admin", "operator"), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    is_depot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DepotDistance(Base):
    __tablename__ = "depot_distances"
    __table_args__ = (UniqueConstraint("city_a_id", "city_b_id", name="uq_city_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_a_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    city_b_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    distance_km: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    city_a = relationship("City", foreign_keys=[city_a_id])
    city_b = relationship("City", foreign_keys=[city_b_id])


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    max_weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    length_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    width_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    height_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    home_depot_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    current_city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    home_depot = relationship("City", foreign_keys=[home_depot_id])
    current_city = relationship("City", foreign_keys=[current_city_id])


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    origin_depot_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    destination_city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(Enum("manual", "excel_upload"), default="manual")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    items = relationship("Item", back_populates="order", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("delivery_orders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    length_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    width_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    height_cm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Enum("menunggu", "terkirim", "carryover"), default="menunggu")
    is_carryover: Mapped[bool] = mapped_column(Boolean, default=False)

    order = relationship("DeliveryOrder", back_populates="items")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"))
    route_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_volume_m3: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    tariff_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    fuel_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    net_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gbest_curve_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    truck = relationship("Truck")


class CarryoverItem(Base):
    __tablename__ = "carryover_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    carryover_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(
        Enum("overflow_berat", "overflow_volume", "guillotine_gagal", "depot_tanpa_truk")
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    item = relationship("Item")


class RelocationLog(Base):
    __tablename__ = "relocation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"))
    from_depot_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    to_depot_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    relocation_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    decision: Mapped[str] = mapped_column(Enum("relokasi", "carryover"))

    truck = relationship("Truck")
    from_depot = relationship("City", foreign_keys=[from_depot_id])
    to_depot = relationship("City", foreign_keys=[to_depot_id])


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("param_group", "param_key", name="uq_param"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    param_group: Mapped[str] = mapped_column(Enum("pso", "operasional"), nullable=False)
    param_key: Mapped[str] = mapped_column(String(50), nullable=False)
    param_value: Mapped[str] = mapped_column(String(50), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)