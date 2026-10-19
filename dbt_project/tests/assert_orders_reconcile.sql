-- Dimension joins may not silently drop or multiply cleaned orders.
WITH staging AS (
  SELECT COUNT(*) AS n, COALESCE(SUM(net_amount), 0) AS revenue FROM {{ ref('stg_orders') }}
), serving AS (
  SELECT COUNT(*) AS n, COALESCE(SUM(net_amount), 0) AS revenue FROM {{ ref('mart_orders') }}
), daily AS (
  SELECT COALESCE(SUM(order_count), 0) AS n, COALESCE(SUM(total_revenue), 0) AS revenue FROM {{ ref('mart_sales_daily') }}
)
SELECT staging.n, serving.n, daily.n FROM staging, serving, daily
WHERE staging.n != serving.n OR serving.n != daily.n
   OR ABS(staging.revenue - serving.revenue) > 0.01
   OR ABS(serving.revenue - daily.revenue) > 0.01
