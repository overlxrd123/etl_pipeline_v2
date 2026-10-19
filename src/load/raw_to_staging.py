"""
加载层 Step 1: 原始数据 -> 维度表
将 product/customer CSV 和 API 数据加载到对应的维度表中
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from datetime import datetime
from config.db_connection import get_session
from config.settings import DATA_PROCESSED, WEATHER_CITIES
from src.warehouse.models import (
    DimProduct, DimCustomer, DimCity, DimWeather, DimCrypto, DimDate
)


def load_products(products_df: pd.DataFrame = None):
    """加载产品维度表"""
    session = get_session()
    if session.query(DimProduct).count() > 0:
        print("  [SKIP] dim_product 已有数据")
        session.close()
        return

    if products_df is None:
        path = DATA_PROCESSED / "products.csv"
        if not path.exists():
            print("  [WARN] products.csv 不存在，请先运行 transaction_generator")
            session.close()
            return
        products_df = pd.read_csv(path)

    records = products_df.to_dict("records")
    for r in records:
        session.add(DimProduct(**{k: v for k, v in r.items()
                                   if k in DimProduct.__table__.columns.keys()}))

    session.commit()
    print(f"  [OK] dim_product: 插入 {len(records)} 条")
    session.close()


def load_customers(customers_df: pd.DataFrame = None):
    """加载客户维度表（同时解析 city_name -> city_id）"""
    session = get_session()
    if session.query(DimCustomer).count() > 0:
        print("  [SKIP] dim_customer 已有数据")
        session.close()
        return

    if customers_df is None:
        path = DATA_PROCESSED / "customers.csv"
        if not path.exists():
            print("  [WARN] customers.csv 不存在，请先运行 transaction_generator")
            session.close()
            return
        customers_df = pd.read_csv(path)

    # 获取 city_name -> city_id 映射
    cities = {c.city_name: c.city_id for c in session.query(DimCity).all()}

    records = customers_df.to_dict("records")
    count = 0
    for r in records:
        city_id = cities.get(r.get("city_name"))
        session.add(DimCustomer(
            customer_id=r["customer_id"],
            first_name=r.get("first_name"),
            last_name=r.get("last_name"),
            email=r.get("email"),
            city_id=city_id,
            signup_date=datetime.strptime(r["signup_date"], "%Y-%m-%d").date()
                if isinstance(r.get("signup_date"), str) else r.get("signup_date"),
            loyalty_tier=r.get("loyalty_tier", "Bronze"),
            is_active=r.get("is_active", True),
            created_at=datetime.now(),
        ))
        count += 1

    session.commit()
    print(f"  [OK] dim_customer: 插入 {count} 条")
    session.close()


def load_weather(weather_records: list[dict] = None):
    """Insert or update weather by city/date, as one transaction."""
    from src.load.driver_loader import load_weather_records
    return load_weather_records(weather_records, get_session)


def load_crypto(crypto_records: list[dict] = None):
    """Insert or update snapshots by ticker/timestamp."""
    from src.load.driver_loader import load_crypto_records
    return load_crypto_records(crypto_records, get_session)


if __name__ == "__main__":
    print("=" * 50)
    print("[Load] 加载原始数据 -> 维度表")
    print("=" * 50)

    load_products()
    load_customers()
    # Weather 和 Crypto 需要先调用 API 获取数据，这里跳过
    print("\n提示: 天气和加密数据需先运行 API 提取器")
