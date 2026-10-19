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
    """Validate, deduplicate and resume committed order batches; returns newly inserted rows."""
    from src.load.order_loader import load_orders_resumable
    if orders_df is None:
        path = DATA_PROCESSED / "orders.csv"
        if not path.exists():
            raise FileNotFoundError("orders.csv 不存在，请先运行 transaction_generator")
        orders_df = pd.read_csv(path, dtype={'source_order_id': 'string'})
    return load_orders_resumable(orders_df.copy(), get_session, batch_size)


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
