"""
星型模型 ORM 定义 — 7张表

        dim_product ──┐
        dim_customer ─┤
        dim_date ─────┼── fact_orders ──┬── dim_city ── dim_weather
        dim_crypto ───┘                 │
                                        └── dim_weather (via city_id + date_id)
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Date, DateTime,
    Boolean, ForeignKey, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from config.db_connection import Base


# ═══════════════════════════════════════════════
# 维度表
# ═══════════════════════════════════════════════

class DimDate(Base):
    """日期维度 — 预生成10年日历"""
    __tablename__ = "dim_date"

    date_id      = Column(Integer, primary_key=True, autoincrement=False)  # YYYYMMDD
    full_date    = Column(Date, nullable=False, unique=True)
    year         = Column(Integer, nullable=False)
    quarter      = Column(Integer, nullable=False)   # 1-4
    month        = Column(Integer, nullable=False)   # 1-12
    day          = Column(Integer, nullable=False)   # 1-31
    day_of_week  = Column(Integer, nullable=False)   # 0=Mon..6=Sun
    day_of_year  = Column(Integer, nullable=False)   # 1-366
    week_of_year = Column(Integer, nullable=False)
    is_weekend   = Column(Boolean, nullable=False)
    is_holiday   = Column(Boolean, nullable=False, default=False)
    month_name   = Column(String(10))
    day_name     = Column(String(10))
    fiscal_year  = Column(Integer)                   # 财年
    fiscal_quarter = Column(Integer)

    # 关系
    weather = relationship("DimWeather", back_populates="date")
    orders  = relationship("FactOrders", back_populates="date")

    def __repr__(self):
        return f"<DimDate({self.date_id} {self.full_date})>"


class DimCity(Base):
    """城市维度"""
    __tablename__ = "dim_city"

    city_id     = Column(Integer, primary_key=True, autoincrement=True)
    city_name   = Column(String(100), nullable=False, unique=True)
    state       = Column(String(50))
    country     = Column(String(50), default="US")
    latitude    = Column(Float)
    longitude   = Column(Float)
    population  = Column(Integer)

    # 关系
    customers   = relationship("DimCustomer", back_populates="city")
    weather     = relationship("DimWeather", back_populates="city")

    def __repr__(self):
        return f"<DimCity({self.city_name})>"


class DimProduct(Base):
    """产品维度"""
    __tablename__ = "dim_product"

    product_id   = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    category     = Column(String(50), nullable=False, index=True)
    subcategory  = Column(String(50))
    brand        = Column(String(100))
    unit_cost    = Column(Float, nullable=False)       # 成本 USD
    unit_price   = Column(Float, nullable=False)       # 售价 USD
    supplier     = Column(String(100))
    sku          = Column(String(50), unique=True)
    is_active    = Column(Boolean, default=True)

    # 关系
    orders = relationship("FactOrders", back_populates="product")

    def __repr__(self):
        return f"<DimProduct({self.product_name} ${self.unit_price})>"


class DimCustomer(Base):
    """客户维度"""
    __tablename__ = "dim_customer"

    customer_id  = Column(Integer, primary_key=True, autoincrement=True)
    first_name   = Column(String(50))
    last_name    = Column(String(50))
    email        = Column(String(200))
    city_id      = Column(Integer, ForeignKey("dim_city.city_id"), index=True)
    signup_date  = Column(Date)
    loyalty_tier = Column(String(20), default="Bronze")  # Bronze/Silver/Gold/Platinum
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime)

    # 关系
    city   = relationship("DimCity", back_populates="customers")
    orders = relationship("FactOrders", back_populates="customer")

    def __repr__(self):
        return f"<DimCustomer({self.first_name} {self.last_name})>"


class DimWeather(Base):
    """天气维度 — 按城市×日期粒度的每日天气"""
    __tablename__ = "dim_weather"
    __table_args__ = (
        UniqueConstraint("city_id", "date_id", name="uq_weather_city_date"),
    )

    weather_id      = Column(Integer, primary_key=True, autoincrement=True)
    city_id         = Column(Integer, ForeignKey("dim_city.city_id"), nullable=False)
    date_id         = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    temp_max_c      = Column(Float)
    temp_min_c      = Column(Float)
    temp_avg_c      = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh  = Column(Float)
    weather_code    = Column(Integer)
    weather_desc    = Column(String(50))   # Sunny/Cloudy/Rainy/Snowy
    fetched_at      = Column(DateTime)

    # 关系
    city = relationship("DimCity", back_populates="weather")
    date = relationship("DimDate", back_populates="weather")

    def __repr__(self):
        return f"<DimWeather({self.city_id}:{self.date_id} {self.weather_desc})>"


class DimCrypto(Base):
    """加密汇率维度"""
    __tablename__ = "dim_crypto"
    __table_args__ = (UniqueConstraint("ticker", "recorded_at", name="uq_crypto_ticker_time"),)

    crypto_id    = Column(Integer, primary_key=True, autoincrement=True)
    ticker       = Column(String(10), nullable=False, index=True)   # BTC / ETH
    price_usd    = Column(Float, nullable=False)
    recorded_at  = Column(DateTime, nullable=False, index=True)
    fetched_at   = Column(DateTime)

    def __repr__(self):
        return f"<DimCrypto({self.ticker} ${self.price_usd} at {self.recorded_at})>"


# ═══════════════════════════════════════════════
# 事实表
# ═══════════════════════════════════════════════

class FactOrders(Base):
    """订单事实表 — 粒度：单行订单明细"""
    __tablename__ = "fact_orders"
    __table_args__ = (
        Index("ix_fact_orders_date", "date_id"),
        Index("ix_fact_orders_customer", "customer_id"),
        Index("ix_fact_orders_product", "product_id"),
    )

    order_id        = Column(Integer, primary_key=True, autoincrement=True)
    customer_id     = Column(Integer, ForeignKey("dim_customer.customer_id"), nullable=False)
    product_id      = Column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    date_id         = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    city_id         = Column(Integer, ForeignKey("dim_city.city_id"), nullable=False)

    quantity        = Column(Integer, nullable=False, default=1)
    unit_price      = Column(Float, nullable=False)
    discount_pct    = Column(Float, default=0.0)          # 折扣百分比 0-100
    net_amount      = Column(Float, nullable=False)        # 实付金额
    payment_method  = Column(String(20), nullable=False)   # credit_card / crypto_btc / crypto_eth
    crypto_ticker   = Column(String(10))                   # 加密支付时的币种
    crypto_rate_usd = Column(Float)                        # 支付时的汇率
    order_status    = Column(String(20), default="completed")
    order_timestamp = Column(DateTime, nullable=False)

    # 关系
    customer = relationship("DimCustomer", back_populates="orders")
    product  = relationship("DimProduct", back_populates="orders")
    date     = relationship("DimDate", back_populates="orders")

    def __repr__(self):
        return f"<FactOrders({self.order_id} ${self.net_amount})>"


class EtlOrderKey(Base):
    """Durable source identity; committed with each order, including legacy CSV imports."""
    __tablename__ = "etl_order_keys"
    source_key = Column(String(240), primary_key=True)
    order_id = Column(Integer, ForeignKey("fact_orders.order_id"), nullable=False, unique=True)
    fingerprint = Column(String(64), nullable=False)


class EtlLoadRun(Base):
    """Order-load audit trail. A failed run can retain earlier committed batches."""
    __tablename__ = "etl_load_runs"
    run_id = Column(String(36), primary_key=True)
    status = Column(String(20), nullable=False)
    input_rows = Column(Integer, nullable=False, default=0)
    inserted_rows = Column(Integer, nullable=False, default=0)
    skipped_rows = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    error_type = Column(String(100))
