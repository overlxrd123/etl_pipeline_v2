-- int_daily_sales: 每日销售汇总（按日期×城市×品类）

SELECT
    date_id,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day_of_week,
    day_name,
    is_weekend,
    city_id,
    order_city AS city_name,
    category,
    COUNT(DISTINCT order_id)  AS order_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(quantity)             AS units_sold,
    SUM(net_amount)           AS total_revenue,
    AVG(net_amount)           AS avg_order_value,
    SUM(discount_amount)      AS total_discounts,
    AVG(discount_pct)         AS avg_discount_pct
FROM {{ ref('int_orders_enriched') }}
GROUP BY
    date_id, full_date, year, quarter, month, month_name,
    day_of_week, day_name, is_weekend,
    city_id, order_city, category
