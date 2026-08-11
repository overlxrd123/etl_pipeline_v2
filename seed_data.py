"""
种子数据初始化 — dim_date + dim_city
运行一次即可：python seed_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import date
from config.db_connection import init_db, get_session
from config.settings import DATE_START, DATE_END, WEATHER_CITIES
from src.warehouse.models import DimDate, DimCity
from src.utils.date_utils import generate_date_dimension


def seed_dim_date():
    """生成10年日历维度"""
    session = get_session()
    existing = session.query(DimDate).count()
    if existing > 0:
        print(f"  dim_date 已有 {existing} 条记录，跳过")
        session.close()
        return

    start = date.fromisoformat(DATE_START)
    end   = date.fromisoformat(DATE_END)
    rows  = generate_date_dimension(start, end)

    session.bulk_insert_mappings(DimDate, rows)
    session.commit()
    print(f"  dim_date: 插入 {len(rows)} 条 ({DATE_START} ~ {DATE_END})")
    session.close()


def seed_dim_city():
    """插入5个美国城市"""
    session = get_session()
    existing = session.query(DimCity).count()
    if existing > 0:
        print(f"  dim_city 已有 {existing} 条记录，跳过")
        session.close()
        return

    city_populations = {
        "New York":    8_804_190,
        "Los Angeles": 3_898_747,
        "Chicago":     2_746_388,
        "Houston":     2_304_580,
        "Phoenix":     1_608_139,
    }

    cities = []
    for name, (lat, lon) in WEATHER_CITIES.items():
        # 从坐标推断州名
        state_map = {
            "New York": "NY", "Los Angeles": "CA", "Chicago": "IL",
            "Houston": "TX", "Phoenix": "AZ"
        }
        cities.append(DimCity(
            city_name=name,
            state=state_map.get(name, ""),
            country="US",
            latitude=lat,
            longitude=lon,
            population=city_populations.get(name, 0),
        ))

    session.add_all(cities)
    session.commit()
    print(f"  dim_city: 插入 {len(cities)} 个城市")
    session.close()


if __name__ == "__main__":
    print("=" * 50)
    print("初始化数据仓库...")
    print("=" * 50)

    # 建表
    print("\n[1] 创建表结构...")
    init_db()
    print("  所有表已创建")

    # 种子数据
    print("\n[2] 种子数据...")
    seed_dim_date()
    seed_dim_city()

    print(f"\n数据库: {Path('warehouse.db').absolute()}")
    print("[OK] 初始化完成！")
