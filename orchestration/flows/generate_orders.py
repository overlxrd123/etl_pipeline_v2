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
def task_gen_orders(products_df, customers_df):
    """生成订单"""
    import pandas as pd
    from datetime import date
    from config.settings import DATA_PROCESSED, SIM_START, SIM_END

    # 读取真实天气/币价作为订单生成输入
    weather_df, crypto_df = load_drivers_from_db()

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

    products_df = task_gen_products(force)
    customers_df = task_gen_customers(force)
    orders_df = task_gen_orders(products_df, customers_df)

    task_load_dimensions(products_df, customers_df)
    loaded = task_load_fact(orders_df)

    print(f"[Flow: generate-orders] 完成 — {loaded:,} 条订单入库")
    return loaded


if __name__ == "__main__":
    generate_orders_flow(force=True)
