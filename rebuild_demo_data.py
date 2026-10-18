"""
重建演示数据 — 让模拟订单由真实天气和币价驱动

流程：
  1. 下载（或复用缓存）订单窗口内的历史天气与币价
  2. 清空 fact_orders / dim_weather / dim_crypto
  3. 导入历史天气与币价
  4. 重新生成订单并加载到数仓

用法：
  python rebuild_demo_data.py            # 复用 data/raw 缓存
  python rebuild_demo_data.py --refresh  # 重新下载历史数据
  python rebuild_demo_data.py --no-backup
"""
import argparse
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from config.db_connection import get_session
from config.settings import (
    DATA_RAW, DATA_PROCESSED, DB_PATH, SIM_START, SIM_END,
    WEATHER_RAIN_MM, WEATHER_RAIN_FACTOR, WEATHER_STORM_FACTOR,
    WEATHER_HEAT_C, WEATHER_HEAT_FACTOR,
    CRYPTO_RETURN_THRESHOLD, CRYPTO_SHARE_BASE,
    CRYPTO_SHARE_UP, CRYPTO_SHARE_DOWN,
)
from src.warehouse.models import FactOrders, DimWeather, DimCrypto
from src.extract.weather_api import fetch_history_all_cities
from src.extract.crypto_api import fetch_crypto_history
from src.extract.transaction_generator import generate_orders
from src.load.raw_to_staging import load_weather, load_crypto
from src.load.staging_to_warehouse import load_orders


WEATHER_CACHE = DATA_RAW / "history_weather.csv"
CRYPTO_CACHE = DATA_RAW / "history_crypto.csv"


def backup_database():
    if not DB_PATH.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = DB_PATH.with_name(f"{DB_PATH.name}.bak_{stamp}")
    shutil.copy2(DB_PATH, target)
    print(f"  [OK] 数据库已备份: {target.name}")


def get_history(refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """获取历史天气和币价，优先使用本地缓存。"""
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    if WEATHER_CACHE.exists() and not refresh:
        weather_records = pd.read_csv(WEATHER_CACHE).to_dict("records")
        print(f"  [CACHE] 天气: {len(weather_records)} 条 <- {WEATHER_CACHE.name}")
    else:
        print(f"  [API] 抓取天气 {SIM_START} ~ {SIM_END} ...")
        weather_records = fetch_history_all_cities(SIM_START, SIM_END)
        pd.DataFrame(weather_records).to_csv(WEATHER_CACHE, index=False)
        print(f"  [OK] 天气: {len(weather_records)} 条 -> {WEATHER_CACHE.name}")

    if CRYPTO_CACHE.exists() and not refresh:
        crypto_records = pd.read_csv(CRYPTO_CACHE).to_dict("records")
        print(f"  [CACHE] 币价: {len(crypto_records)} 条 <- {CRYPTO_CACHE.name}")
    else:
        print(f"  [API] 抓取币价 {SIM_START} ~ {SIM_END} ...")
        crypto_records = fetch_crypto_history(SIM_START, SIM_END)
        pd.DataFrame(crypto_records).to_csv(CRYPTO_CACHE, index=False)
        print(f"  [OK] 币价: {len(crypto_records)} 条 -> {CRYPTO_CACHE.name}")

    weather_df = pd.DataFrame(weather_records)
    crypto_df = pd.DataFrame(crypto_records)
    if len(crypto_df):
        crypto_df["recorded_at"] = (
            pd.to_datetime(crypto_df["recorded_at"], utc=True)
            .dt.tz_localize(None)
        )
    return weather_df, crypto_df


def clear_demo_tables():
    session = get_session()
    try:
        for model in (FactOrders, DimWeather, DimCrypto):
            deleted = session.query(model).delete()
            print(f"  [CLEAR] {model.__tablename__}: 删除 {deleted:,} 行")
        session.commit()
    finally:
        session.close()


def load_history(weather_df: pd.DataFrame, crypto_df: pd.DataFrame):
    weather_count = load_weather(weather_df.to_dict("records"))
    crypto_count = load_crypto(crypto_df.to_dict("records"))
    return weather_count, crypto_count


def rebuild_orders(weather_df: pd.DataFrame, crypto_df: pd.DataFrame):
    products_path = DATA_PROCESSED / "products.csv"
    customers_path = DATA_PROCESSED / "customers.csv"
    if not products_path.exists() or not customers_path.exists():
        raise FileNotFoundError(
            "缺少 data/processed/products.csv 或 customers.csv，"
            "请先运行 python -m src.extract.transaction_generator"
        )

    products_df = pd.read_csv(products_path)
    customers_df = pd.read_csv(customers_path)

    start = date.fromisoformat(SIM_START)
    end = date.fromisoformat(SIM_END)
    days = (end - start).days + 1

    print(f"  [GEN] 生成订单 {SIM_START} ~ {SIM_END}（{days} 天）...")
    orders_df = generate_orders(
        products_df, customers_df,
        start_date=start, days=days,
        weather_df=weather_df,
        crypto_prices_df=crypto_df,
    )
    orders_df.to_csv(DATA_PROCESSED / "orders.csv", index=False)
    print(f"  [OK] 生成 {len(orders_df):,} 条订单 -> data/processed/orders.csv")

    loaded = load_orders(orders_df)
    return loaded


def print_effects():
    print("\n效应设定（config/settings.py）:")
    print(f"  雨天 (>= {WEATHER_RAIN_MM:g}mm)        订单量 × {WEATHER_RAIN_FACTOR}")
    print(f"  雷暴 / 降雪                 订单量 × {WEATHER_STORM_FACTOR}")
    print(f"  高温 (>= {WEATHER_HEAT_C:g}°C)         订单量 × {WEATHER_HEAT_FACTOR}")
    print(f"  BTC 日涨 > {CRYPTO_RETURN_THRESHOLD:.0%}      加密支付占比 {CRYPTO_SHARE_UP:.0%}")
    print(f"  BTC 日跌 > {CRYPTO_RETURN_THRESHOLD:.0%}      加密支付占比 {CRYPTO_SHARE_DOWN:.0%}")
    print(f"  其他                        加密支付占比 {CRYPTO_SHARE_BASE:.0%}")


def main():
    parser = argparse.ArgumentParser(description="重建由真实天气/币价驱动的演示数据")
    parser.add_argument("--refresh", action="store_true", help="重新下载历史数据")
    parser.add_argument("--no-backup", action="store_true", help="跳过数据库备份")
    args = parser.parse_args()

    print("=" * 60)
    print("重建演示数据 — 真实天气/币价驱动的模拟订单")
    print("=" * 60)
    print_effects()

    print("\n[1/4] 准备历史数据")
    if not args.no_backup:
        backup_database()
    weather_df, crypto_df = get_history(args.refresh)

    print("\n[2/4] 清空订单与历史维度表")
    clear_demo_tables()

    print("\n[3/4] 导入历史天气与币价")
    weather_count, crypto_count = load_history(weather_df, crypto_df)
    print(f"  天气入库 {weather_count:,} 条，币价入库 {crypto_count:,} 条")

    print("\n[4/4] 重新生成订单")
    loaded = rebuild_orders(weather_df, crypto_df)

    print("\n" + "=" * 60)
    print(f"[DONE] 重建完成 — 订单 {loaded:,} 条，天气 {weather_count:,} 条，币价 {crypto_count:,} 条")
    print("下一步: cd dbt_project && dbt run --profiles-dir . && dbt test --profiles-dir .")
    print("=" * 60)


if __name__ == "__main__":
    main()
