-- mart_product_performance: 产品维度分析
-- 排名、贡献度、利润率

WITH product_metrics AS (
    SELECT
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        MAX(list_price) AS current_price,
        MAX(unit_cost)  AS unit_cost,
        MAX(margin_pct) AS margin_pct,

        COUNT(DISTINCT order_id)       AS total_orders,
        SUM(quantity)                  AS total_units,
        SUM(net_amount)                AS total_revenue,
        SUM(discount_amount)           AS total_discounts,
        COUNT(DISTINCT customer_id)    AS unique_buyers,
        MIN(full_date)                 AS first_sale_date,
        MAX(full_date)                 AS last_sale_date

    FROM {{ ref('int_orders_enriched') }}
    GROUP BY product_id, product_name, category, subcategory, brand
),

ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
        RANK() OVER (ORDER BY total_units DESC)   AS units_rank,
        -- 品类内排名
        RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS category_rank,
        -- 营收占比
        ROUND(total_revenue / SUM(total_revenue) OVER() * 100, 2) AS revenue_share_pct
    FROM product_metrics
)

SELECT * FROM ranked
ORDER BY revenue_rank
