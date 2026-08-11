-- int_orders_enriched: 订单事实表 + 所有维度信息
-- 核心中间表，后续所有分析基于此表

SELECT
    o.order_id,
    o.customer_id,
    c.full_name AS customer_name,
    c.city_name AS customer_city,
    c.state         AS customer_state,
    c.loyalty_tier,
    c.signup_date,

    o.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,
    p.unit_cost,
    p.unit_price AS list_price,
    p.margin,
    p.margin_pct,

    o.date_id,
    d.full_date,
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    d.day_of_week,
    d.day_name,
    d.is_weekend,
    d.is_holiday,
    d.week_of_year,

    o.city_id,
    o.quantity,
    o.unit_price AS sold_price,
    o.discount_pct,
    o.net_amount,
    o.unit_price * o.quantity AS gross_amount,
    o.unit_price * o.quantity - o.net_amount AS discount_amount,
    o.payment_method,
    o.crypto_ticker,
    o.crypto_rate_usd,
    o.order_timestamp

FROM fact_orders o
JOIN dim_customer c   ON o.customer_id = c.customer_id
JOIN dim_product p    ON o.product_id  = p.product_id
JOIN dim_date d       ON o.date_id     = d.date_id
WHERE o.order_status = 'completed'
  AND o.net_amount > 0
