"""
集中配置管理 — 所有路径、API参数、常量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 路径 ───────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "warehouse.db"
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ── Open-Meteo 天气 API ─────────────────────────
# 免费，无需 Key，每天 10000 次调用额度
WEATHER_CITIES = {
    "New York":    (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Chicago":     (41.8781, -87.6298),
    "Houston":     (29.7604, -95.3698),
    "Phoenix":     (33.4484, -112.0740),
}
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
WEATHER_ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

# ── CoinGecko 加密 API ──────────────────────────
# 免费，每分钟 10-30 次
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
CRYPTO_TICKERS = ["bitcoin", "ethereum"]

# ── 电商交易模拟器 ──────────────────────────────
NUM_PRODUCTS = 50
NUM_CUSTOMERS = 500
ORDERS_PER_DAY = (200, 500)          # 每日订单数范围
SIM_DAYS = 365                       # 模拟天数（1年）
PRODUCT_CATEGORIES = [
    "Smartphones", "Laptops", "Headphones", "Tablets", "Wearables"
]
PAYMENT_METHODS = {
    "credit_card": 0.70,
    "crypto_btc":  0.15,
    "crypto_eth":  0.15,
}

# ── 模拟效应参数（已知因果，用于验证分析管道）────
# 订单由真实天气/币价驱动，效应大小在此显式设定。
# 分析结果应当能还原这些设定值。
WEATHER_RAIN_MM = 5.0           # 日降水量达到该值视为雨天
WEATHER_RAIN_FACTOR = 0.90      # 雨天订单量 ×0.90
WEATHER_STORM_FACTOR = 0.80     # 雷暴/降雪订单量 ×0.80
WEATHER_HEAT_C = 35.0           # 最高温达到该值视为高温
WEATHER_HEAT_FACTOR = 0.95      # 高温订单量 ×0.95

CRYPTO_RETURN_THRESHOLD = 0.02  # BTC 日涨跌幅阈值（2%）
CRYPTO_SHARE_BASE = 0.30        # 基准加密支付占比（BTC 15% + ETH 15%）
CRYPTO_SHARE_UP = 0.40          # BTC 单日上涨 >2% 时的加密支付占比
CRYPTO_SHARE_DOWN = 0.20        # BTC 单日下跌 >2% 时的加密支付占比

# ── 日期维度 ────────────────────────────────────
DATE_START = "2023-01-01"
DATE_END   = "2032-12-31"            # 10年日期维度

# ── 历史模拟窗口（订单与天气/币价严格对齐）──────
SIM_START = "2025-08-11"
SIM_END   = "2026-08-10"

# ── 日志 ────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
