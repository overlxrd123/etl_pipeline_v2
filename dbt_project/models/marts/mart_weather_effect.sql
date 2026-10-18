-- mart_weather_effect: 天气效应还原（同日跨城市对比）
--
-- 背景：订单由真实天气驱动，效应在 config/settings.py 里显式设定：
--   雨天 ×0.90 / 雷暴·降雪 ×0.80 / 高温 ×0.95
-- 本模型用于验证「分析管道能否把这些设定值还原出来」。
--
-- 为什么不能直接跨天比较：
--   雪天集中在冬季、高温集中在夏季，而冬季/夏季的订单基数本来就不同
--   （季节系数 + 周末效应），直接比较会把「天气效应」和「季节效应」混在一起，
--   导致还原结果失真。
--
-- 隔离方法（同日跨城市对比，即固定日期效应）：
--   每天所有城市共享同一个基础订单量，只有天气乘数不同，
--   因此 当天受影响城市均值 / 当天未受影响城市均值 就是纯粹的天气效应。
--   再对「受影响城市和未受影响城市都存在的日期」取均值。
--
-- 输出四行：rain / snow / storm / heat
--   isolated_ratio    ← 隔离日期效应后的还原值（应接近 setting_ratio）
--   confounded_ratio  ← 直接跨天比较的值（受季节混淆，用来对比说明问题）

WITH city_day AS (
    SELECT
        date_id,
        city_id,
        SUM(order_count)      AS orders,
        MAX(precipitation_mm) AS precipitation_mm,
        MAX(weather_code)     AS weather_code,
        MAX(temp_max_c)       AS temp_max_c
    FROM {{ ref('int_weather_sales') }}
    GROUP BY date_id, city_id
),

flagged AS (
    SELECT
        date_id,
        city_id,
        orders,
        CASE WHEN precipitation_mm >= 5.0 THEN 1 ELSE 0 END       AS is_rain,
        CASE WHEN weather_code IN (71, 73, 75) THEN 1 ELSE 0 END  AS is_snow,
        CASE WHEN weather_code >= 95 THEN 1 ELSE 0 END            AS is_storm,
        CASE WHEN temp_max_c >= 35.0 THEN 1 ELSE 0 END            AS is_heat
    FROM city_day
),

-- 把四个驱动因子纵向展开，每个因子一行一城市日
unpivoted AS (
    SELECT date_id, city_id, orders, 'rain'  AS factor, is_rain  AS flag FROM flagged
    UNION ALL
    SELECT date_id, city_id, orders, 'snow'  AS factor, is_snow  AS flag FROM flagged
    UNION ALL
    SELECT date_id, city_id, orders, 'storm' AS factor, is_storm AS flag FROM flagged
    UNION ALL
    SELECT date_id, city_id, orders, 'heat'  AS factor, is_heat  AS flag FROM flagged
),

-- 每天每个因子：受影响城市均值 vs 未受影响城市均值
day_level AS (
    SELECT
        date_id,
        factor,
        AVG(CASE WHEN flag = 1 THEN orders END)      AS affected_avg,
        AVG(CASE WHEN flag = 0 THEN orders END)      AS baseline_avg,
        COUNT(*)                                     AS city_days,
        SUM(flag)                                    AS affected_cities
    FROM unpivoted
    GROUP BY date_id, factor
),

day_ratio AS (
    SELECT
        date_id,
        factor,
        affected_avg,
        baseline_avg,
        affected_cities,
        CASE
            WHEN affected_avg IS NOT NULL
                 AND baseline_avg IS NOT NULL
                 AND baseline_avg > 0
            THEN affected_avg * 1.0 / baseline_avg
        END AS ratio_day
    FROM day_level
),

-- 隔离口径：只对「当天既有受影响城市、也有未受影响城市」的日期求平均
isolated AS (
    SELECT
        factor,
        COUNT(*)                                                   AS total_days,
        SUM(CASE WHEN ratio_day IS NOT NULL THEN 1 ELSE 0 END)      AS comparable_days,
        AVG(ratio_day)                                             AS isolated_ratio
    FROM day_ratio
    GROUP BY factor
),

-- 混淆口径：直接按「受影响 vs 未受影响」分组求均值（跨天，含季节效应）
confounded AS (
    SELECT
        factor,
        SUM(flag)                                                  AS affected_city_days,
        COUNT(*) - SUM(flag)                                       AS baseline_city_days,
        AVG(CASE WHEN flag = 1 THEN orders END)                     AS affected_city_day_avg,
        AVG(CASE WHEN flag = 0 THEN orders END)                     AS baseline_city_day_avg
    FROM unpivoted
    GROUP BY factor
)

SELECT
    i.factor,
    CASE i.factor
        WHEN 'rain'  THEN '雨天（日降水 ≥ 5mm）'
        WHEN 'snow'  THEN '降雪（weather_code 71/73/75）'
        WHEN 'storm' THEN '雷暴（weather_code ≥ 95）'
        WHEN 'heat'  THEN '高温（日最高温 ≥ 35°C）'
    END AS factor_desc,
    c.affected_city_days,
    c.baseline_city_days,
    i.comparable_days,
    ROUND(c.affected_city_day_avg, 1)  AS affected_city_day_avg,
    ROUND(c.baseline_city_day_avg, 1)  AS baseline_city_day_avg,
    -- 未控制日期效应的比值（受季节混淆）
    ROUND(c.affected_city_day_avg * 1.0 / NULLIF(c.baseline_city_day_avg, 0), 4)
        AS confounded_ratio,
    -- 同日跨城市对比后的比值（应接近仿真设定值）
    ROUND(i.isolated_ratio, 4)         AS isolated_ratio,
    -- 仿真设定值（与 config/settings.py 保持一致）
    CASE i.factor
        WHEN 'rain'  THEN 0.90
        WHEN 'snow'  THEN 0.80
        WHEN 'storm' THEN 0.80
        WHEN 'heat'  THEN 0.95
    END AS setting_ratio,
    -- 还原误差（百分点）
    ROUND((i.isolated_ratio - CASE i.factor
        WHEN 'rain'  THEN 0.90
        WHEN 'snow'  THEN 0.80
        WHEN 'storm' THEN 0.80
        WHEN 'heat'  THEN 0.95
    END) * 100, 2) AS deviation_pct_points
FROM isolated i
JOIN confounded c ON i.factor = c.factor
ORDER BY i.factor
