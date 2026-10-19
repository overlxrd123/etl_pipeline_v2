"""Warehouse publication gate; errors stop dbt before marts are replaced."""
from sqlalchemy import text


def check_warehouse(factory):
    queries = {
        'fact_orders_count': 'SELECT COUNT(*) FROM fact_orders',
        'completed_orders_count': "SELECT COUNT(*) FROM fact_orders WHERE order_status='completed'",
        'dim_product_count': 'SELECT COUNT(*) FROM dim_product',
        'dim_customer_count': 'SELECT COUNT(*) FROM dim_customer',
        'invalid_amount': 'SELECT COUNT(*) FROM fact_orders WHERE net_amount IS NULL OR net_amount <= 0 OR unit_price IS NULL OR unit_price <= 0 OR quantity IS NULL OR quantity <= 0 OR discount_pct IS NULL OR discount_pct < 0 OR discount_pct > 100',
        'inconsistent_amount': 'SELECT COUNT(*) FROM fact_orders WHERE ABS(net_amount - unit_price * quantity * (1 - discount_pct / 100.0)) > 0.021',
        'invalid_payment': "SELECT COUNT(*) FROM fact_orders WHERE payment_method NOT IN ('credit_card','crypto_btc','crypto_eth') OR payment_method IS NULL OR (payment_method IN ('crypto_btc','crypto_eth') AND (crypto_ticker IS NULL OR crypto_rate_usd IS NULL OR crypto_rate_usd <= 0)) OR (payment_method='crypto_btc' AND crypto_ticker!='BTC') OR (payment_method='crypto_eth' AND crypto_ticker!='ETH') OR (payment_method='credit_card' AND (crypto_ticker IS NOT NULL OR crypto_rate_usd IS NOT NULL))",
        'invalid_order_time': 'SELECT COUNT(*) FROM fact_orders f JOIN dim_date d ON f.date_id=d.date_id WHERE f.order_timestamp IS NULL OR SUBSTR(CAST(f.order_timestamp AS TEXT),1,10)!=CAST(d.full_date AS TEXT)',
        'invalid_weather': 'SELECT COUNT(*) FROM dim_weather WHERE temp_max_c IS NULL OR temp_min_c IS NULL OR precipitation_mm IS NULL OR weather_code IS NULL OR temp_max_c < temp_min_c OR precipitation_mm < 0',
        'invalid_crypto': 'SELECT COUNT(*) FROM dim_crypto WHERE price_usd IS NULL OR price_usd <= 0 OR recorded_at IS NULL',
        'orphan_customer': 'SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_customer d ON f.customer_id=d.customer_id WHERE d.customer_id IS NULL',
        'orphan_product': 'SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_product d ON f.product_id=d.product_id WHERE d.product_id IS NULL',
        'orphan_date': 'SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_date d ON f.date_id=d.date_id WHERE d.date_id IS NULL',
        'orphan_city': 'SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_city d ON f.city_id=d.city_id WHERE d.city_id IS NULL',
        'missing_weather': "SELECT COUNT(*) FROM (SELECT DISTINCT city_id,date_id FROM fact_orders WHERE order_status='completed') f LEFT JOIN dim_weather w ON f.city_id=w.city_id AND f.date_id=w.date_id WHERE w.weather_id IS NULL",
        'missing_crypto': "SELECT COUNT(*) FROM (SELECT DISTINCT date_id FROM fact_orders WHERE order_status='completed') f JOIN dim_date d ON f.date_id=d.date_id WHERE (SELECT COUNT(DISTINCT c.ticker) FROM dim_crypto c WHERE c.ticker IN ('BTC','ETH') AND SUBSTR(CAST(c.recorded_at AS TEXT),1,10)=CAST(d.full_date AS TEXT)) < 2",
    }
    with factory() as session:
        checks = {name: session.execute(text(sql)).scalar_one() for name, sql in queries.items()}
    failures = [name for name, count in checks.items() if (count == 0 if name.endswith('_count') else count > 0)]
    if failures:
        raise ValueError('质量检查失败，停止发布: ' + ', '.join(f'{name}={checks[name]}' for name in failures))
    return checks
