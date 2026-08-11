-- mart_customer_segments: RFM 客户分层
-- Recency: 距上次购买天数
-- Frequency: 总订单数
-- Monetary: 总消费金额

WITH today_date AS (
    SELECT MAX(full_date) AS today FROM {{ ref('int_daily_sales') }}
),

customer_rfm AS (
    SELECT
        o.customer_id,
        c.full_name AS customer_name,
        c.city_name,
        c.loyalty_tier,
        c.signup_date,

        -- Recency
        julianday((SELECT today FROM today_date)) -
            julianday(MAX(o.full_date)) AS recency_days,

        -- Frequency
        COUNT(DISTINCT o.order_id) AS frequency,

        -- Monetary
        SUM(o.net_amount) AS monetary,

        -- 其他
        COUNT(DISTINCT o.product_id) AS distinct_products,
        AVG(o.net_amount) AS avg_order_value,
        SUM(o.quantity) AS total_units

    FROM {{ ref('int_orders_enriched') }} o
    JOIN stg_customers c ON o.customer_id = c.customer_id
    GROUP BY o.customer_id, c.full_name, c.city_name, c.loyalty_tier, c.signup_date
),

rfm_scored AS (
    SELECT *,
        -- R score: 天数越少越好 (1-4, 4=最好)
        CASE
            WHEN recency_days <= 30 THEN 4
            WHEN recency_days <= 90 THEN 3
            WHEN recency_days <= 180 THEN 2
            ELSE 1
        END AS r_score,
        -- F score: 越多越好
        CASE
            WHEN frequency >= 50 THEN 4
            WHEN frequency >= 20 THEN 3
            WHEN frequency >= 10 THEN 2
            ELSE 1
        END AS f_score,
        -- M score: 越高越好
        CASE
            WHEN monetary >= 10000 THEN 4
            WHEN monetary >= 3000 THEN 3
            WHEN monetary >= 1000 THEN 2
            ELSE 1
        END AS m_score
    FROM customer_rfm
)

SELECT
    *,
    (r_score + f_score + m_score) AS rfm_total,
    -- 客户分层
    CASE
        WHEN r_score = 4 AND f_score = 4 AND m_score = 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal'
        WHEN r_score >= 3 AND (f_score + m_score) >= 4 THEN 'Potential'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scored
