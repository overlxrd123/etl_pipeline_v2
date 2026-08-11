-- stg_products: 产品维度清洗
SELECT
    product_id,
    product_name,
    category,
    COALESCE(subcategory, '') AS subcategory,
    COALESCE(brand, '') AS brand,
    unit_cost,
    unit_price,
    (unit_price - unit_cost) AS margin,
    ROUND((unit_price - unit_cost) / NULLIF(unit_price, 0) * 100, 1) AS margin_pct,
    COALESCE(supplier, '') AS supplier,
    sku,
    is_active
FROM dim_product
WHERE is_active = 1
