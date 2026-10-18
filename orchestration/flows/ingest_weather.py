"""
Prefect Flow: 天气数据采集 + 加载
从 Open-Meteo 获取 5 个城市最近 N 天天气（默认 7 天）→ 写入 dim_weather
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prefect import flow, task
from datetime import date

from src.extract.weather_api import fetch_all_cities
from src.load.raw_to_staging import load_weather


@task(name="fetch-weather", retries=3, retry_delay_seconds=60)
def task_fetch_weather(days_back: int = 7):
    """从 API 获取天气数据"""
    print(f"[Weather] 获取最近 {days_back} 天天气...")
    rows = fetch_all_cities(days_back=days_back)
    print(f"[Weather] 获取到 {len(rows)} 条记录")
    return rows


@task(name="load-weather")
def task_load_weather(rows: list[dict]):
    """加载天气数据到数仓"""
    if not rows:
        print("[Weather] 无数据，跳过加载")
        return 0
    return load_weather(rows)


@flow(name="ingest-weather")
def ingest_weather(days_back: int = 7):
    """天气数据采集完整流程"""
    print("=" * 50)
    print(f"[Flow: ingest-weather] 开始 — {date.today()}")
    print("=" * 50)

    rows = task_fetch_weather(days_back)
    inserted = task_load_weather(rows)

    print(f"[Flow: ingest-weather] 完成 — 新增 {inserted} 条天气记录")
    return inserted


if __name__ == "__main__":
    ingest_weather()
