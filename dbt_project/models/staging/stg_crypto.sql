-- stg_crypto: 加密汇率维度清洗 + 小时标记
SELECT
    crypto_id,
    ticker,
    price_usd,
    recorded_at,
    -- 按小时分组用于趋势分析
    strftime('%Y-%m-%d %H:00:00', recorded_at) AS recorded_hour,
    fetched_at
FROM dim_crypto
WHERE price_usd > 0
