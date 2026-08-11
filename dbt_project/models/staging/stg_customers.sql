-- stg_customers: 客户维度清洗
SELECT
    c.customer_id,
    COALESCE(c.first_name || ' ' || c.last_name, 'Unknown') AS full_name,
    c.first_name,
    c.last_name,
    c.email,
    c.city_id,
    ci.city_name,
    COALESCE(ci.state, '') AS state,
    c.signup_date,
    c.loyalty_tier,
    c.is_active
FROM dim_customer c
LEFT JOIN dim_city ci ON c.city_id = ci.city_id
WHERE c.is_active = 1
