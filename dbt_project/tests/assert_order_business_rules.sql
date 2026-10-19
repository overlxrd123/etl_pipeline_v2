SELECT order_id FROM {{ ref('mart_orders') }}
WHERE quantity <= 0 OR sold_price <= 0 OR discount_pct < 0 OR discount_pct > 100
   OR ABS(net_amount - sold_price * quantity * (1 - discount_pct / 100.0)) > 0.021
   OR payment_method NOT IN ('credit_card', 'crypto_btc', 'crypto_eth')
