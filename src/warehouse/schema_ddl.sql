-- ═══════════════════════════════════════════════════════════
-- 电商数据仓库 — 星型模型 DDL (参考用，实际建表由SQLAlchemy管理)
-- ═══════════════════════════════════════════════════════════

-- ── 维度表 ─────────────────────────────────────

CREATE TABLE dim_date (
    date_id       INTEGER PRIMARY KEY,         -- YYYYMMDD
    full_date     DATE NOT NULL UNIQUE,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,           -- 1-4
    month         INTEGER NOT NULL,           -- 1-12
    day           INTEGER NOT NULL,           -- 1-31
    day_of_week   INTEGER NOT NULL,           -- 0=Mon..6=Sun
    day_of_year   INTEGER NOT NULL,           -- 1-366
    week_of_year  INTEGER NOT NULL,
    is_weekend    INTEGER NOT NULL DEFAULT 0, -- 0/1
    is_holiday    INTEGER NOT NULL DEFAULT 0,
    month_name    TEXT,
    day_name      TEXT,
    fiscal_year   INTEGER,
    fiscal_quarter INTEGER
);

CREATE TABLE dim_city (
    city_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name  TEXT NOT NULL UNIQUE,
    state      TEXT,
    country    TEXT DEFAULT 'US',
    latitude   REAL,
    longitude  REAL,
    population INTEGER
);

CREATE TABLE dim_product (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    subcategory  TEXT,
    brand        TEXT,
    unit_cost    REAL NOT NULL,
    unit_price   REAL NOT NULL,
    supplier     TEXT,
    sku          TEXT UNIQUE,
    is_active    INTEGER DEFAULT 1
);
CREATE INDEX ix_dim_product_category ON dim_product(category);

CREATE TABLE dim_customer (
    customer_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name   TEXT,
    last_name    TEXT,
    email        TEXT,
    city_id      INTEGER REFERENCES dim_city(city_id),
    signup_date  DATE,
    loyalty_tier TEXT DEFAULT 'Bronze',
    is_active    INTEGER DEFAULT 1,
    created_at   DATETIME
);
CREATE INDEX ix_dim_customer_city ON dim_customer(city_id);

CREATE TABLE dim_weather (
    weather_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id          INTEGER NOT NULL REFERENCES dim_city(city_id),
    date_id          INTEGER NOT NULL REFERENCES dim_date(date_id),
    temp_max_c       REAL,
    temp_min_c       REAL,
    temp_avg_c       REAL,
    precipitation_mm REAL,
    wind_speed_kmh   REAL,
    weather_code     INTEGER,
    weather_desc     TEXT,
    fetched_at       DATETIME,
    UNIQUE(city_id, date_id)
);

CREATE TABLE dim_crypto (
    crypto_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    price_usd   REAL NOT NULL,
    recorded_at DATETIME NOT NULL,
    fetched_at  DATETIME
);
CREATE INDEX ix_dim_crypto_ticker ON dim_crypto(ticker);
CREATE INDEX ix_dim_crypto_recorded ON dim_crypto(recorded_at);

-- ── 事实表 ─────────────────────────────────────

CREATE TABLE fact_orders (
    order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    product_id      INTEGER NOT NULL REFERENCES dim_product(product_id),
    date_id         INTEGER NOT NULL REFERENCES dim_date(date_id),
    city_id         INTEGER NOT NULL REFERENCES dim_city(city_id),
    quantity        INTEGER NOT NULL DEFAULT 1,
    unit_price      REAL NOT NULL,
    discount_pct    REAL DEFAULT 0.0,
    net_amount      REAL NOT NULL,
    payment_method  TEXT NOT NULL,
    crypto_ticker   TEXT,
    crypto_rate_usd REAL,
    order_status    TEXT DEFAULT 'completed',
    order_timestamp DATETIME NOT NULL
);
CREATE INDEX ix_fact_orders_date ON fact_orders(date_id);
CREATE INDEX ix_fact_orders_customer ON fact_orders(customer_id);
CREATE INDEX ix_fact_orders_product ON fact_orders(product_id);

-- ── 示例查询 ───────────────────────────────────

-- 每日销售KPI
-- SELECT d.full_date, COUNT(*) as orders, SUM(f.net_amount) as revenue
-- FROM fact_orders f JOIN dim_date d ON f.date_id = d.date_id
-- GROUP BY d.full_date ORDER BY d.full_date;

-- 天气对销售的影响
-- SELECT w.weather_desc, COUNT(*) as orders, AVG(f.net_amount) as avg_order
-- FROM fact_orders f
-- JOIN dim_weather w ON f.city_id = w.city_id AND f.date_id = w.date_id
-- GROUP BY w.weather_desc;
