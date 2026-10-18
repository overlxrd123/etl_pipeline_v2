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
            5 - NTILE(4) OVER (ORDER BY 距上次购买天 ASC) AS r_score,
            NTILE(4) OVER (ORDER BY 购买次数 ASC)        AS f_score,
            NTILE(4) OVER (ORDER BY 消费金额 ASC)        AS m_score
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


def get_crypto_impact():
    """每日 BTC 价格、涨跌幅与加密支付占比"""
    return query_to_df("""
        SELECT
            price_date              AS 日期,
            close_price_usd         AS BTC价格,
            daily_return_pct        AS BTC日涨跌幅,
            total_orders            AS 订单数,
            crypto_orders           AS 加密订单数,
            crypto_order_share_pct  AS 加密支付占比,
            crypto_revenue          AS 加密支付营收,
            btc_movement            AS 行情
        FROM mart_crypto_impact
        ORDER BY price_date
    """)


def get_crypto_impact_summary():
    """按 BTC 行情分组，比较加密支付占比"""
    return query_to_df("""
        SELECT
            btc_movement                        AS 行情,
            COUNT(*)                            AS 天数,
            ROUND(AVG(crypto_order_share_pct), 2) AS 平均加密支付占比,
            ROUND(AVG(total_orders), 0)         AS 平均日订单数
        FROM mart_crypto_impact
        WHERE btc_movement IN ('上涨 >2%', '下跌 <-2%', '震荡')
        GROUP BY btc_movement
        ORDER BY 平均加密支付占比 DESC
    """)


def get_weather_sales_summary():
    """按天气类别比较城市日平均；订单指数已剔除日期/季节波动。

    订单指数 = 当天该城市订单份额 / 该城市全年平均份额 × 100
    100 表示平常水平，低于 100 表示需求下降。
    """
    return query_to_df("""
        WITH city_day AS (
            SELECT
                f.date_id,
                f.city_id,
                COUNT(*)          AS orders,
                SUM(f.net_amount) AS revenue
            FROM fact_orders f
            WHERE f.order_status = 'completed'
            GROUP BY f.date_id, f.city_id
        ),
        city_share AS (
            SELECT
                *,
                orders * 1.0 / SUM(orders) OVER (PARTITION BY date_id) AS day_share
            FROM city_day
        ),
        city_base AS (
            SELECT city_id, AVG(day_share) AS base_share
            FROM city_share
            GROUP BY city_id
        ),
        normalized AS (
            SELECT
                s.*,
                s.day_share / b.base_share AS orders_index
            FROM city_share s
            JOIN city_base b ON s.city_id = b.city_id
        )
        SELECT
            CASE
                WHEN w.weather_code >= 95
                     OR w.weather_code IN (71, 73, 75) THEN '雷暴/降雪'
                WHEN w.precipitation_mm >= 5           THEN '雨天'
                WHEN w.temp_max_c >= 35                THEN '高温'
                ELSE '无雨'
            END AS 天气,
            COUNT(*)                                      AS 城市天数,
            ROUND(AVG(n.orders), 1)                       AS 订单数,
            ROUND(AVG(n.revenue), 2)                      AS 营收,
            ROUND(AVG(n.revenue * 1.0 / n.orders), 2)     AS 客单价,
            ROUND(AVG(n.orders_index) * 100, 1)           AS 订单指数
        FROM normalized n
        JOIN dim_weather w
            ON n.city_id = w.city_id AND n.date_id = w.date_id
        GROUP BY 天气
        ORDER BY 订单指数 DESC
    """)
