"""
电商交易数据生成器
生成具有现实商业特征的模拟订单数据：
- 50个电子产品 × 500个客户 × 5个城市
- 周末效应、季节性波动、品类折扣规律
- 支持信用卡/加密支付混合
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path
from config.settings import (
    PRODUCT_CATEGORIES, NUM_PRODUCTS, NUM_CUSTOMERS, ORDERS_PER_DAY,
    WEATHER_CITIES, PAYMENT_METHODS, DATA_PROCESSED,
)

np.random.seed(42)

# ═══════════════════════════════════════════
# 产品目录
# ═══════════════════════════════════════════

PRODUCT_SPECS = {
    "Smartphones": {
        "brands": ["Apple", "Samsung", "Google", "OnePlus", "Nothing"],
        "subcategories": ["Flagship", "Mid-range", "Budget"],
        "cost_range": (200, 800), "price_range": (399, 1499),
        "suppliers": ["Foxconn", "Pegatron", "Wistron"],
    },
    "Laptops": {
        "brands": ["Apple", "Dell", "Lenovo", "HP", "ASUS"],
        "subcategories": ["Ultrabook", "Gaming", "Business"],
        "cost_range": (400, 1500), "price_range": (699, 2999),
        "suppliers": ["Quanta", "Compal", "Wistron"],
    },
    "Headphones": {
        "brands": ["Sony", "Bose", "Apple", "Sennheiser", "JBL"],
        "subcategories": ["Over-ear", "In-ear", "Noise-cancelling"],
        "cost_range": (20, 200), "price_range": (49, 549),
        "suppliers": ["Goertek", "Luxshare", "Merry"],
    },
    "Tablets": {
        "brands": ["Apple", "Samsung", "Microsoft", "Lenovo", "Xiaomi"],
        "subcategories": ["Premium", "Mid-range", "Budget"],
        "cost_range": (100, 600), "price_range": (199, 1299),
        "suppliers": ["Foxconn", "Pegatron", "BYD"],
    },
    "Wearables": {
        "brands": ["Apple", "Garmin", "Fitbit", "Samsung", "Amazfit"],
        "subcategories": ["Smartwatch", "Fitness Tracker", "Ring"],
        "cost_range": (30, 300), "price_range": (79, 799),
        "suppliers": ["Quanta", "Compal", "Luxshare"],
    },
}


def generate_products() -> pd.DataFrame:
    """生成50个产品"""
    products = []
    pid = 1
    for cat in PRODUCT_CATEGORIES:
        spec = PRODUCT_SPECS[cat]
        per_cat = NUM_PRODUCTS // len(PRODUCT_CATEGORIES)
        for i in range(per_cat):
            brand = spec["brands"][i % len(spec["brands"])]
            subcat = spec["subcategories"][i % len(spec["subcategories"])]
            cost = round(np.random.uniform(*spec["cost_range"]), 2)
            markup = np.random.uniform(1.3, 2.0)   # 30%-100% markup
            price = round(cost * markup, 2)
            products.append({
                "product_id": pid,
                "product_name": f"{brand} {subcat} {cat[:-1]} Gen{i+1}",
                "category": cat,
                "subcategory": subcat,
                "brand": brand,
                "unit_cost": cost,
                "unit_price": price,
                "supplier": spec["suppliers"][i % len(spec["suppliers"])],
                "sku": f"SKU-{cat[:3].upper()}-{pid:04d}",
                "is_active": True,
            })
            pid += 1
    return pd.DataFrame(products)


# ═══════════════════════════════════════════
# 客户
# ═══════════════════════════════════════════

FIRST_NAMES = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
               "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica"]
LAST_NAMES  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
               "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas"]
CITY_NAMES  = list(WEATHER_CITIES.keys())  # ["New York", "Los Angeles", ...]


def generate_customers() -> pd.DataFrame:
    """生成500个客户，均匀分布在5个城市"""
    customers = []
    for i in range(1, NUM_CUSTOMERS + 1):
        city = CITY_NAMES[(i - 1) % 5]
        tier_roll = np.random.random()
        if tier_roll < 0.05:
            tier = "Platinum"
        elif tier_roll < 0.20:
            tier = "Gold"
        elif tier_roll < 0.50:
            tier = "Silver"
        else:
            tier = "Bronze"

        signup_days = np.random.randint(30, 1095)  # 1 month to 3 years ago
        signup = date.today() - timedelta(days=int(signup_days))

        customers.append({
            "customer_id": i,
            "first_name": np.random.choice(FIRST_NAMES),
            "last_name": np.random.choice(LAST_NAMES),
            "email": f"customer{i}@example.com",
            "city_name": city,
            "signup_date": signup,
            "loyalty_tier": tier,
            "is_active": np.random.random() > 0.05,
            "created_at": datetime.now(),
        })
    return pd.DataFrame(customers)


# ═══════════════════════════════════════════
# 订单生成（核心，有真实业务模式）
# ═══════════════════════════════════════════

def _seasonal_multiplier(d: date) -> float:
    """季节性乘数：11-12月旺季、1月淡季、7月Prime Day"""
    m = d.month
    if m == 11: return 1.6     # Black Friday
    if m == 12: return 1.8     # Christmas
    if m == 1:  return 0.7     # Post-holiday
    if m == 7:  return 1.2     # Prime Day
    return 1.0


def _weekend_multiplier(d: date) -> float:
    """周末乘数：周末订单量更高"""
    return 1.3 if d.weekday() >= 5 else 1.0


def _payment_method():
    """按概率选择支付方式"""
    r = np.random.random()
    if r < 0.70:
        return "credit_card", None, None
    elif r < 0.85:
        return "crypto_btc", "BTC", None   # 汇率稍后从 crypto 数据关联
    else:
        return "crypto_eth", "ETH", None


def generate_orders(products_df: pd.DataFrame, customers_df: pd.DataFrame,
                    start_date: date = None, days: int = 365,
                    crypto_rates: dict = None) -> pd.DataFrame:
    """
    生成模拟订单。

    Args:
        products_df: 产品表
        customers_df: 客户表
        start_date: 起始日期，默认365天前
        days: 模拟天数
        crypto_rates: {"BTC": 68000, "ETH": 3400} 用于加密支付汇率

    Returns:
        订单DataFrame
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=days)

    crypto_rates = crypto_rates or {"BTC": 68000, "ETH": 3400}
    product_list = products_df.to_dict("records")
    customer_list = customers_df.to_dict("records")

    orders = []
    min_orders, max_orders = ORDERS_PER_DAY

    for day_offset in range(days):
        d = start_date + timedelta(days=day_offset)

        # 当天订单数 = 基础范围 × 季节性 × 周末效应
        base_count = np.random.randint(min_orders, max_orders + 1)
        multiplier = _seasonal_multiplier(d) * _weekend_multiplier(d)
        daily_count = max(10, int(base_count * multiplier))

        # 添加随机波动
        daily_count = int(daily_count * np.random.uniform(0.85, 1.15))

        for _ in range(daily_count):
            customer = customer_list[np.random.randint(0, len(customer_list))]
            product  = product_list[np.random.randint(0, len(product_list))]

            # 数量：大部分买1件，偶尔买2-5件
            qty = 1 if np.random.random() < 0.85 else np.random.randint(2, 6)

            # 折扣：根据品类不同
            cat_discount = {
                "Smartphones": np.random.choice([0, 5, 10], p=[0.6, 0.3, 0.1]),
                "Laptops":     np.random.choice([0, 5, 10, 15], p=[0.5, 0.3, 0.15, 0.05]),
                "Headphones":  np.random.choice([0, 10, 20], p=[0.4, 0.4, 0.2]),
                "Tablets":     np.random.choice([0, 10, 15], p=[0.5, 0.35, 0.15]),
                "Wearables":   np.random.choice([0, 15, 25], p=[0.35, 0.4, 0.25]),
            }.get(product["category"], 0)

            # 周末额外折扣
            if d.weekday() >= 5 and np.random.random() < 0.2:
                cat_discount = min(50, cat_discount + 10)

            unit_price = product["unit_price"]
            net_amount = round(unit_price * qty * (1 - cat_discount / 100), 2)

            # 支付方式
            pay_method, ticker, rate = _payment_method()
            if ticker:
                rate = crypto_rates.get(ticker, 0)

            # 时间戳（在当天的随机时刻）
            hour = np.random.randint(6, 23)
            minute = np.random.randint(0, 60)
            order_time = datetime(d.year, d.month, d.day, hour, minute)

            orders.append({
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "date_id": int(d.strftime("%Y%m%d")),
                "city_name": customer["city_name"],
                "quantity": qty,
                "unit_price": unit_price,
                "discount_pct": cat_discount,
                "net_amount": net_amount,
                "payment_method": pay_method,
                "crypto_ticker": ticker,
                "crypto_rate_usd": rate,
                "order_status": "completed" if np.random.random() < 0.95 else "cancelled",
                "order_timestamp": order_time,
            })

    df = pd.DataFrame(orders)
    return df


# ═══════════════════════════════════════════
# 便捷函数：一键生成所有数据
# ═══════════════════════════════════════════

def generate_all(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    一键生成产品、客户、订单数据。
    结果同时保存到 data/processed/ 目录。

    Returns:
        {"products": df, "customers": df, "orders": df}
    """
    print("=" * 50)
    print("[E-commerce] 电商交易数据生成器")
    print("=" * 50)

    # 产品
    products_path = DATA_PROCESSED / "products.csv"
    if products_path.exists() and not force:
        print(f"  [SKIP] 产品数据已存在，跳过生成")
        products_df = pd.read_csv(products_path)
    else:
        products_df = generate_products()
        products_df.to_csv(products_path, index=False)
        print(f"  [OK] 生成 {len(products_df)} 个产品 -> {products_path}")

    # 客户
    customers_path = DATA_PROCESSED / "customers.csv"
    if customers_path.exists() and not force:
        print(f"  [SKIP] 客户数据已存在，跳过生成")
        customers_df = pd.read_csv(customers_path)
    else:
        customers_df = generate_customers()
        customers_df.to_csv(customers_path, index=False)
        print(f"  [OK] 生成 {len(customers_df)} 个客户 -> {customers_path}")

    # 订单
    orders_path = DATA_PROCESSED / "orders.csv"
    if orders_path.exists() and not force:
        print(f"  [SKIP] 订单数据已存在，跳过生成")
        orders_df = pd.read_csv(orders_path)
    else:
        orders_df = generate_orders(products_df, customers_df)
        orders_df.to_csv(orders_path, index=False)
        print(f"  [OK] 生成 {len(orders_df):,} 条订单 -> {orders_path}")

    # 统计
    print(f"\n[Summary] 数据概览:")
    print(f"  产品: {products_df['category'].nunique()} 品类, {len(products_df)} SKU")
    print(f"  客户: {customers_df['city_name'].nunique()} 城市, {len(customers_df)} 人")
    print(f"  订单: {len(orders_df):,} 条, "
          f"总营收 ${orders_df['net_amount'].sum():,.0f}")
    print(f"  日期范围: {orders_df['date_id'].min()} ~ {orders_df['date_id'].max()}")

    return {"products": products_df, "customers": customers_df, "orders": orders_df}


if __name__ == "__main__":
    generate_all(force=True)
