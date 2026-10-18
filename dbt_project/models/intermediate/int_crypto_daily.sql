-- int_crypto_daily: 每个币种每天的收盘价（当天最后一条快照）
-- dim_crypto 可能是日线，也可能是每5分钟的快照，这里统一成日粒度

WITH ranked AS (
    SELECT
        ticker,
        date(recorded_at)   AS price_date,
        price_usd,
        ROW_NUMBER() OVER (
            PARTITION BY ticker, date(recorded_at)
            ORDER BY recorded_at DESC
        ) AS rn
    FROM {{ ref('stg_crypto') }}
)

SELECT
    ticker,
    price_date,
    price_usd AS close_price_usd
FROM ranked
WHERE rn = 1
