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
        FROM mart_orders
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
        FROM mart_orders f
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
        FROM mart_orders f
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
        FROM mart_orders f
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
        FROM mart_orders f
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
        FROM mart_orders f
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
        FROM mart_orders
        WHERE order_status = 'completed'
        GROUP BY payment_method
        ORDER BY 数量 DESC
    """)


def get_rfm_segments():
    """Serve the dbt RFM model; recency is anchored to the latest business date."""
    return query_to_df("""
        SELECT customer_id, customer_name AS 客户名,
               city_name AS 城市, loyalty_tier AS 忠诚度等级,
               recency_days AS 距上次购买天,
               frequency AS 购买次数, monetary AS 消费金额,
               r_score, f_score, m_score, segment
        FROM mart_customer_segments
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


def get_recent_load_runs(limit: int = 20):
    """An older warehouse has no audit table until its next order load."""
    from sqlalchemy import inspect
    if not inspect(engine).has_table('etl_load_runs'):
        return pd.DataFrame()
    return query_to_df('''
        SELECT run_id AS 批次, status AS 状态, input_rows AS 输入行数,
               inserted_rows AS 新增行数, skipped_rows AS 跳过行数,
               started_at AS 开始时间, finished_at AS 结束时间, error_type AS 异常类型
        FROM etl_load_runs ORDER BY started_at DESC LIMIT :limit
    ''', {'limit': max(1, min(int(limit), 100))})


def get_driver_coverage():
    """订单日期与天气/币价数据的覆盖情况。

    影响分析只会使用「有订单的日期」，因此新抓取但没有订单的
    天气/币价不会进入分析结果。
    """
    return query_to_df("""
        WITH order_city_day AS (
            SELECT DISTINCT date_id, city_id
            FROM fact_orders
            WHERE order_status = 'completed'
        ),
        weather_city_day AS (
            SELECT DISTINCT date_id, city_id
            FROM dim_weather
        ),
        order_day AS (
            SELECT DISTINCT date_id
            FROM fact_orders
            WHERE order_status = 'completed'
        ),
        crypto_day AS (
            SELECT DISTINCT CAST(strftime('%Y%m%d', recorded_at) AS INTEGER) AS date_id
            FROM dim_crypto
            WHERE ticker = 'BTC'
        )
        SELECT
            (SELECT MIN(date_id) FROM order_day) AS 订单起始日,
            (SELECT MAX(date_id) FROM order_day) AS 订单结束日,
            (SELECT COUNT(*) FROM order_day)     AS 订单天数,
            (SELECT COUNT(*) FROM order_city_day) AS 订单城市日,
            (SELECT COUNT(*)
               FROM order_city_day o
               JOIN weather_city_day w
                 ON o.date_id = w.date_id AND o.city_id = w.city_id) AS 天气匹配城市日,
            (SELECT COUNT(*)
               FROM order_day o
               JOIN crypto_day c ON o.date_id = c.date_id) AS 币价匹配天数
    """).iloc[0].to_dict()


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
            FROM mart_orders f
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


def get_weather_effect():
    """天气效应还原 — 同日跨城市对比 vs 直接跨天对比。

    数据来自 dbt 模型 mart_weather_effect。isolated_ratio 用「同一天受影响城市
    均值 / 未受影响城市均值」计算，天然控制掉季节和周末效应，应接近仿真设定值；
    confounded_ratio 是不控制日期的直接比较，用来展示季节混淆的影响。
    """
    return query_to_df("""
        SELECT
            factor                        AS 因子,
            factor_desc                   AS 说明,
            affected_city_days            AS 受影响城市天数,
            comparable_days               AS 可比天数,
            isolated_ratio                AS 隔离后比值,
            confounded_ratio              AS 未隔离比值,
            setting_ratio                 AS 设定值,
            deviation_pct_points          AS 偏差百分点
        FROM mart_weather_effect
        ORDER BY factor
    """)
