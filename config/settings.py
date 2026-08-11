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

# ── 日期维度 ────────────────────────────────────
DATE_START = "2023-01-01"
DATE_END   = "2032-12-31"            # 10年日期维度

# ── 日志 ────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
