"""
加载层 Step 2: 维度表就绪 -> 事实表
将生成的订单 CSV 加载到 fact_orders 表（解析 city_name -> city_id）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from datetime import datetime
from config.db_connection import get_session
from config.settings import DATA_PROCESSED
from src.warehouse.models import FactOrders, DimCity


def load_orders(orders_df: pd.DataFrame = None, batch_size: int = 10000):
    """加载订单事实表"""
    session = get_session()

    existing = session.query(FactOrders).count()
    if existing > 0:
        print(f"  [SKIP] fact_orders 已有 {existing:,} 条数据")
        session.close()
        return existing

    if orders_df is None:
        path = DATA_PROCESSED / "orders.csv"
        if not path.exists():
            print("  [WARN] orders.csv 不存在，请先运行 transaction_generator")
            session.close()
            return
        orders_df = pd.read_csv(path)

    # city_name -> city_id 映射
    cities = {c.city_name: c.city_id for c in session.query(DimCity).all()}

    # 解析时间戳
    orders_df["order_timestamp"] = pd.to_datetime(orders_df["order_timestamp"])

    records = orders_df.to_dict("records")
    total = len(records)
    loaded = 0

    for i, r in enumerate(records):
        city_id = cities.get(r.get("city_name"))
        if not city_id:
            continue

        session.add(FactOrders(
            customer_id=r["customer_id"],
            product_id=r["product_id"],
            date_id=r["date_id"],
            city_id=city_id,
            quantity=r.get("quantity", 1),
            unit_price=r["unit_price"],
            discount_pct=r.get("discount_pct", 0),
            net_amount=r["net_amount"],
            payment_method=r["payment_method"],
            crypto_ticker=r.get("crypto_ticker") if pd.notna(r.get("crypto_ticker")) else None,
            crypto_rate_usd=r.get("crypto_rate_usd") if pd.notna(r.get("crypto_rate_usd")) else None,
            order_status=r.get("order_status", "completed"),
            order_timestamp=r["order_timestamp"].to_pydatetime()
                if hasattr(r["order_timestamp"], "to_pydatetime")
                else r["order_timestamp"],
        ))
        loaded += 1

        # 分批提交
        if loaded % batch_size == 0:
            session.commit()
            print(f"  ... {loaded}/{total} ({loaded*100//total}%)")

    session.commit()
    print(f"  [OK] fact_orders: 插入 {loaded:,} 条 (共 {total:,} 条)")
    session.close()
    return loaded


def run_full_load():
    """一键执行完整加载流程"""
    from src.load.raw_to_staging import load_products, load_customers

    print("=" * 50)
    print("[Load] 完整数据加载流程")
    print("=" * 50)

    print("\n-- Phase 1: 维度表 --")
    load_products()
    load_customers()

    print("\n-- Phase 2: 事实表 --")
    load_orders()

    print("\n[DONE] 数据仓库加载完成")


if __name__ == "__main__":
    run_full_load()
