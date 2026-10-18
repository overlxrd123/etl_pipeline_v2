"""
把数仓当前数据导出为 Power BI 可直接读取的 CSV。

这些 CSV 是派生数据：内容完全来自 warehouse.db，重新导出即可刷新，
因此不纳入 Git 版本管理（见 .gitignore）。

用法：
  python export_pbi_demo.py                  # 导出到 ./pbi_demo
  python export_pbi_demo.py --output-dir out # 导出到指定目录
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from config.settings import DB_PATH

# 列顺序与 Power BI 模型保持一致，避免每次导出列顺序变化
TABLES = {
    "fact_orders": [
        "order_id", "customer_id", "product_id", "date_id", "city_id",
        "quantity", "unit_price", "discount_pct", "net_amount",
        "payment_method", "crypto_ticker", "crypto_rate_usd",
        "order_status", "order_timestamp",
    ],
    "dim_city": [
        "city_id", "city_name", "state", "country",
        "latitude", "longitude", "population",
    ],
    "dim_customer": [
        "customer_id", "first_name", "last_name", "email", "city_id",
        "signup_date", "loyalty_tier", "is_active", "created_at",
    ],
    "dim_date": [
        "date_id", "full_date", "year", "quarter", "month", "day",
        "day_of_week", "day_of_year", "week_of_year", "is_weekend",
        "is_holiday", "month_name", "day_name", "fiscal_year", "fiscal_quarter",
    ],
    "dim_product": [
        "product_id", "product_name", "category", "subcategory", "brand",
        "unit_cost", "unit_price", "supplier", "sku", "is_active",
    ],
    "dim_weather": [
        "weather_id", "city_id", "date_id", "temp_max_c", "temp_min_c",
        "temp_avg_c", "precipitation_mm", "wind_speed_kmh",
        "weather_code", "weather_desc", "fetched_at",
    ],
}


def export_pbi_demo(output_dir: Path = None, db_path: Path = None) -> int:
    """导出所有表，返回导出的总行数。"""
    output_dir = Path(output_dir or Path(__file__).parent / "pbi_demo")
    db_path = Path(db_path or DB_PATH)

    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}，请先运行 seed_data.py / rebuild_demo_data.py")

    output_dir.mkdir(parents=True, exist_ok=True)
    total = 0

    with sqlite3.connect(db_path) as conn:
        existing = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = set(TABLES) - existing
        if missing:
            raise RuntimeError(f"数据库缺少表: {', '.join(sorted(missing))}")

        for table, columns in TABLES.items():
            df = pd.read_sql(
                f"SELECT {', '.join(columns)} FROM {table}", conn
            )
            path = output_dir / f"{table}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            total += len(df)
            print(f"  [OK] {table:<14} {len(df):>8,} 行 -> {path}")

    print(f"  导出完成：{len(TABLES)} 张表，共 {total:,} 行 -> {output_dir}")
    return total


def main():
    parser = argparse.ArgumentParser(description="导出 Power BI 演示 CSV")
    parser.add_argument(
        "--output-dir", default=None,
        help="输出目录（默认 ./pbi_demo）",
    )
    args = parser.parse_args()
    export_pbi_demo(args.output_dir)


if __name__ == "__main__":
    main()
