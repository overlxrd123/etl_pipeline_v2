-- mart_crypto_impact: 币价对订单支付行为的影响
-- 按天关联 BTC 涨跌幅与加密支付占比

WITH btc AS (
    SELECT
        price_date,
        close_price_usd,
        LAG(close_price_usd) OVER (ORDER BY price_date) AS prev_close_usd
    FROM {{ ref('int_crypto_daily') }}
    WHERE ticker = 'BTC'
),

btc_with_return AS (
    SELECT
        price_date,
        close_price_usd,
        prev_close_usd,
        ROUND(
            (close_price_usd - prev_close_usd) / NULLIF(prev_close_usd, 0) * 100,
            2
        ) AS daily_return_pct
    FROM btc
),

daily_orders AS (
    SELECT
        date_id,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN payment_method IN ('crypto_btc', 'crypto_eth')
                 THEN 1 ELSE 0 END) AS crypto_orders,
        SUM(CASE WHEN payment_method IN ('crypto_btc', 'crypto_eth')
                 THEN net_amount ELSE 0 END) AS crypto_revenue,
        SUM(net_amount) AS total_revenue
    FROM {{ ref('int_orders_enriched') }}
    GROUP BY date_id
)

SELECT
    CAST(strftime('%Y%m%d', b.price_date) AS INTEGER) AS date_id,
    b.price_date,
    b.close_price_usd,
    b.prev_close_usd,
    b.daily_return_pct,
    o.total_orders,
    o.crypto_orders,
    o.crypto_revenue,
    o.total_revenue,
    ROUND(o.crypto_orders * 100.0 / NULLIF(o.total_orders, 0), 2)
        AS crypto_order_share_pct,
    CASE
        WHEN b.daily_return_pct > 2  THEN '上涨 >2%'
        WHEN b.daily_return_pct < -2 THEN '下跌 <-2%'
        WHEN b.daily_return_pct IS NULL THEN '无前一日数据'
        ELSE '震荡'
    END AS btc_movement
FROM btc_with_return b
LEFT JOIN daily_orders o
    ON o.date_id = CAST(strftime('%Y%m%d', b.price_date) AS INTEGER)
WHERE o.total_orders IS NOT NULL   -- 只保留订单覆盖的日期
ORDER BY b.price_date
