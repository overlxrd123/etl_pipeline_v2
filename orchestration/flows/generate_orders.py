"""
Prefect Flow: 订单数据生成 + 加载
每日生成模拟电商订单 → 写入维度表 + 事实表
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prefect import flow, task

from src.extract.transaction_generator import (
    generate_products, generate_customers, generate_orders, load_drivers_from_db,
)
from src.load.raw_to_staging import load_products, load_customers
from src.load.staging_to_warehouse import load_orders


@task(name="gen-products")
def task_gen_products(force: bool = False):
    """生成/加载产品"""
    import pandas as pd
    from config.settings import DATA_PROCESSED
    path = DATA_PROCESSED / "products.csv"
    if path.exists() and not force:
        return pd.read_csv(path)
    df = generate_products()
    df.to_csv(path, index=False)
    return df


@task(name="gen-customers")
def task_gen_customers(force: bool = False):
    """生成/加载客户"""
    import pandas as pd
    from config.settings import DATA_PROCESSED
    path = DATA_PROCESSED / "customers.csv"
    if path.exists() and not force:
        return pd.read_csv(path)
    df = generate_customers()
    df.to_csv(path, index=False)
    return df


@task(name="gen-orders")
def task_gen_orders(products_df, customers_df, force: bool = False):
    """生成订单"""
    import pandas as pd
    from datetime import date
    from config.settings import DATA_PROCESSED, SIM_START, SIM_END
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    path = DATA_PROCESSED / "orders.csv"
    if path.exists() and not force:
        cached = pd.read_csv(path, dtype={'source_order_id': 'string'})
        expected = (int(SIM_START.replace('-', '')), int(SIM_END.replace('-', '')))
        if (int(cached.date_id.min()), int(cached.date_id.max())) != expected:
            raise ValueError("缓存订单窗口与配置不一致，请使用 rebuild_demo_data.py 显式重建")
        return cached

    # 读取真实天气/币价作为订单生成输入
    weather_df, crypto_df = load_drivers_from_db()
    from src.load.driver_validation import validate_history
    from config.settings import WEATHER_CITIES
    if weather_df is None or crypto_df is None:
        raise ValueError('历史天气或币价为空，禁止退化为无效应订单')
    validate_history(weather_df, crypto_df, SIM_START, SIM_END, WEATHER_CITIES)

    # 固定使用配置中的模拟窗口，避免驱动数据只有几天时
    # 订单窗口也跟着缩成几天
    start = date.fromisoformat(SIM_START)
    days = (date.fromisoformat(SIM_END) - start).days + 1
    df = generate_orders(products_df, customers_df,
                         start_date=start, days=days,
                         weather_df=weather_df,
                         crypto_prices_df=crypto_df)
    df.to_csv(DATA_PROCESSED / "orders.csv", index=False)
    print(f"[Orders] 生成 {len(df):,} 条订单")
    return df


@task(name="load-dimensions")
def task_load_dimensions(products_df, customers_df):
    """加载维度表"""
    load_products(products_df)
    load_customers(customers_df)


@task(name="load-fact-orders")
def task_load_fact(orders_df):
    """加载事实表"""
    return load_orders(orders_df)


@flow(name="generate-orders-flow")
def generate_orders_flow(force: bool = False):
    """订单生成完整流程"""
    print("=" * 50)
    print("[Flow: generate-orders] 开始")

    from config.db_connection import get_session
    from config.settings import DATA_PROCESSED
    from src.warehouse.models import FactOrders
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    with get_session() as session:
        has_orders = session.query(FactOrders.order_id).first() is not None
    if has_orders and (force or not (DATA_PROCESSED / "orders.csv").exists()):
        raise ValueError("已有订单时禁止隐式重新生成；请恢复原 CSV 或使用 rebuild_demo_data.py 显式重建")
    products_df = task_gen_products(force)
    customers_df = task_gen_customers(force)
    orders_df = task_gen_orders(products_df, customers_df, force)

    task_load_dimensions(products_df, customers_df)
    loaded = task_load_fact(orders_df)

    print(f"[Flow: generate-orders] 完成 — {loaded:,} 条订单入库")
    return loaded


if __name__ == "__main__":
    generate_orders_flow()
