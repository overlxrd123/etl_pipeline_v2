"""
Streamlit 数据查询层 — 所有 SQL 查询集中管理
列名统一中文，图表直接使用
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from sqlalchemy import text
from config.db_connection import engine


def query_to_df(sql: str, params: dict = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def get_kpi_summary():
    return query_to_df("""
        SELECT
            COUNT(DISTINCT order_id) AS total_orders,
            SUM(net_amount)          AS total_revenue,
            AVG(net_amount)          AS avg_order_value,
            COUNT(DISTINCT customer_id) AS unique_customers,
            SUM(quantity)            AS total_units
        FROM fact_orders
        WHERE order_status = 'completed'
    """).iloc[0].to_dict()


def get_daily_sales(days: int = 90):
    return query_to_df(f"""
        SELECT
            d.full_date       AS 日期,
            d.is_weekend      AS 是否周末,
            COUNT(f.order_id)        AS 订单数,
            SUM(f.net_amount)        AS 营收,
            AVG(f.net_amount)        AS 客单价,
            COUNT(DISTINCT f.customer_id) AS 客户数
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE f.order_status = 'completed'
        GROUP BY d.full_date, d.is_weekend
        ORDER BY d.full_date DESC
        LIMIT {days}
    """).sort_values("日期")


def get_category_revenue():
    return query_to_df("""
        SELECT
            p.category         AS 品类,
            COUNT(f.order_id)  AS 订单数,
            SUM(f.net_amount)  AS 营收,
            AVG(f.net_amount)  AS 客单价,
            SUM(f.quantity)    AS 销量,
            AVG(f.discount_pct) AS 平均折扣
        FROM fact_orders f
        JOIN dim_product p ON f.product_id = p.product_id
        WHERE f.order_status = 'completed'
        GROUP BY p.category
        ORDER BY 营收 DESC
    """)


def get_city_revenue():
    return query_to_df("""
        SELECT
            ci.city_name        AS 城市,
            COUNT(f.order_id)   AS 订单数,
            SUM(f.net_amount)   AS 营收,
            AVG(f.net_amount)   AS 客单价,
            COUNT(DISTINCT f.customer_id) AS 客户数
        FROM fact_orders f
        JOIN dim_city ci ON f.city_id = ci.city_id
        WHERE f.order_status = 'completed'
        GROUP BY ci.city_name
        ORDER BY 营收 DESC
    """)


def get_monthly_trend():
    return query_to_df("""
        SELECT
            d.year             AS 年份,
            d.month            AS 月份,
            d.month_name       AS 月份名,
            SUM(f.net_amount)  AS 营收,
            COUNT(f.order_id)  AS 订单数
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE f.order_status = 'completed'
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """)


def get_top_products(n: int = 10):
    return query_to_df(f"""
        SELECT
            p.product_name     AS 产品名,
            p.category         AS 品类,
            COUNT(f.order_id)  AS 订单数,
            SUM(f.net_amount)  AS 营收,
            SUM(f.quantity)    AS 销量
        FROM fact_orders f
        JOIN dim_product p ON f.product_id = p.product_id
        WHERE f.order_status = 'completed'
        GROUP BY p.product_name, p.category
        ORDER BY 营收 DESC
        LIMIT {n}
    """)


def get_payment_breakdown():
    return query_to_df("""
        SELECT
            CASE payment_method
                WHEN 'credit_card' THEN '信用卡'
                WHEN 'crypto_btc'  THEN '比特币'
                WHEN 'crypto_eth'  THEN '以太坊'
            END                 AS 支付方式,
            COUNT(*)            AS 数量,
            SUM(net_amount)     AS 营收
        FROM fact_orders
        WHERE order_status = 'completed'
        GROUP BY payment_method
        ORDER BY 数量 DESC
    """)


def get_rfm_segments():
    return query_to_df("""
        WITH customer_rfm AS (
            SELECT
                f.customer_id,
                c.first_name || ' ' || c.last_name AS 客户名,
                ci.city_name                        AS 城市,
                c.loyalty_tier                      AS 忠诚度等级,
                julianday('now') - julianday(MAX(d.full_date)) AS 距上次购买天,
                COUNT(DISTINCT f.order_id)          AS 购买次数,
                SUM(f.net_amount)                   AS 消费金额
            FROM fact_orders f
            JOIN dim_customer c ON f.customer_id = c.customer_id
            JOIN dim_date d    ON f.date_id = d.date_id
            JOIN dim_city ci   ON c.city_id = ci.city_id
            WHERE f.order_status = 'completed'
            GROUP BY f.customer_id
        )
        SELECT *,
            CASE
                WHEN 距上次购买天 <= 30  THEN 4
                WHEN 距上次购买天 <= 90  THEN 3
                WHEN 距上次购买天 <= 180 THEN 2
                ELSE 1
            END AS r_score,
            CASE
                WHEN 购买次数 >= 50 THEN 4
                WHEN 购买次数 >= 20 THEN 3
                WHEN 购买次数 >= 10 THEN 2
                ELSE 1
            END AS f_score,
            CASE
                WHEN 消费金额 >= 10000 THEN 4
                WHEN 消费金额 >= 3000  THEN 3
                WHEN 消费金额 >= 1000  THEN 2
                ELSE 1
            END AS m_score
        FROM customer_rfm
    """)


def get_pipeline_stats():
    return query_to_df("""
        SELECT 'fact_orders' AS 表名, COUNT(*) AS 行数 FROM fact_orders
        UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
        UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
        UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
        UNION ALL SELECT 'dim_city', COUNT(*) FROM dim_city
        UNION ALL SELECT 'dim_weather', COUNT(*) FROM dim_weather
        UNION ALL SELECT 'dim_crypto', COUNT(*) FROM dim_crypto
    """)


def get_weather_sales_summary():
    return query_to_df("""
        SELECT
            w.weather_desc                 AS 天气,
            COUNT(DISTINCT f.order_id)     AS 订单数,
            SUM(f.net_amount)              AS 营收,
            AVG(f.net_amount)              AS 客单价
        FROM fact_orders f
        JOIN dim_weather w
            ON f.city_id = w.city_id AND f.date_id = w.date_id
        WHERE f.order_status = 'completed'
        GROUP BY w.weather_desc
        ORDER BY 营收 DESC
    """)
