-- stg_orders: 订单数据清洗
-- 过滤取消订单，补全缺失字段

WITH raw_orders AS (
    SELECT * FROM fact_orders
)

SELECT
    order_id,
    customer_id,
    product_id,
    date_id,
    city_id,
    quantity,
    unit_price,
    COALESCE(discount_pct, 0) AS discount_pct,
    net_amount,
    payment_method,
    COALESCE(crypto_ticker, '') AS crypto_ticker,
    COALESCE(crypto_rate_usd, 0) AS crypto_rate_usd,
    order_status,
    order_timestamp
FROM raw_orders
WHERE order_status = 'completed'
  AND net_amount > 0
