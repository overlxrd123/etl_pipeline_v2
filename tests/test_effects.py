"""核心业务逻辑单元测试：天气乘数、支付方式、RFM 分层。

运行：python -m pytest -q
"""
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from config.settings import (
    WEATHER_RAIN_FACTOR,
    WEATHER_STORM_FACTOR,
    WEATHER_HEAT_FACTOR,
)
from src.extract.transaction_generator import _payment_method, _weather_multiplier

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "warehouse.db"


def _weather(code: int, precip: float, temp_max: float) -> dict:
    return {
        "weather_code": code,
        "precipitation_mm": precip,
        "temp_max_c": temp_max,
    }


def test_dry_weather_is_neutral():
    assert _weather_multiplier(_weather(0, 0.0, 25.0)) == 1.0
    assert _weather_multiplier(None) == 1.0


def test_rain_reduces_orders():
    factor = _weather_multiplier(_weather(61, 8.0, 20.0))
    assert factor == pytest.approx(WEATHER_RAIN_FACTOR)


def test_light_rain_below_threshold_is_neutral():
    factor = _weather_multiplier(_weather(51, 1.0, 20.0))
    assert factor == pytest.approx(1.0)


def test_snow_uses_storm_factor():
    factor = _weather_multiplier(_weather(71, 2.0, -3.0))
    assert factor == pytest.approx(WEATHER_STORM_FACTOR)


def test_rain_and_heat_stack():
    factor = _weather_multiplier(_weather(61, 8.0, 36.0))
    assert factor == pytest.approx(WEATHER_RAIN_FACTOR * WEATHER_HEAT_FACTOR)


def test_payment_mix_matches_crypto_share():
    np.random.seed(0)
    n = 20_000
    methods = [_payment_method(0.40)[0] for _ in range(n)]

    crypto_share = sum(m.startswith("crypto") for m in methods) / n
    btc_share = sum(m == "crypto_btc" for m in methods) / n

    assert crypto_share == pytest.approx(0.40, abs=0.02)
    assert btc_share == pytest.approx(0.20, abs=0.02)


def test_rfm_segments_have_multiple_categories():
    if not DB_PATH.exists():
        pytest.skip("warehouse.db 不存在，先运行 rebuild_demo_data.py")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT segment, COUNT(*) FROM mart_customer_segments GROUP BY segment"
        ).fetchall()

    assert len(rows) >= 3, f"RFM 分层只有 {len(rows)} 类，分位数打分可能失效"
    assert sum(n for _, n in rows) > 0
