-- 验证所有订单金额为正数
SELECT order_id, net_amount
FROM {{ ref('stg_orders') }}
WHERE net_amount <= 0
