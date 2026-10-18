"""
Open-Meteo 天气 API 客户端
免费，无需 Key，每天 10000 次调用
API文档: https://open-meteo.com/
"""
import time
import requests
from datetime import datetime, date
from typing import Optional
from config.settings import (
    WEATHER_CITIES, WEATHER_API, WEATHER_ARCHIVE_API, DATA_RAW
)


# 天气代码→描述映射
WMO_CODES = {
    0:  "Clear", 1:  "Mostly Clear", 2:  "Partly Cloudy",
    3:  "Overcast", 45: "Foggy", 48: "Rime Fog",
    51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
    80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
    95: "Thunderstorm", 96: "Hail Thunderstorm", 99: "Severe Thunderstorm",
}


def fetch_weather_for_city(lat: float, lon: float, city_name: str,
                           start_date: str, end_date: str,
                           api_url: str = WEATHER_API) -> list[dict]:
    """
    获取单个城市的每日天气数据。

    Args:
        lat/lon: 经纬度
        city_name: 城市名（用于日志）
        start_date/end_date: YYYY-MM-DD 格式

    Returns:
        [{city_name, date, temp_max, temp_min, precip, wind, weather_code, weather_desc}, ...]
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "wind_speed_10m_max,weather_code",
        "timezone": "America/Chicago",
        "start_date": start_date,
        "end_date": end_date,
    }

    resp = requests.get(api_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    daily = data.get("daily", {})
    dates    = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    precips  = daily.get("precipitation_sum", [])
    winds    = daily.get("wind_speed_10m_max", [])
    codes    = daily.get("weather_code", [])

    for i, d in enumerate(dates):
        code = int(codes[i]) if i < len(codes) else 0
        tmax = temps_max[i] if i < len(temps_max) else None
        tmin = temps_min[i] if i < len(temps_min) else None

        rows.append({
            "city_name": city_name,
            "date": d,
            "temp_max_c": tmax,
            "temp_min_c": tmin,
            "temp_avg_c": round((tmax + tmin) / 2, 1) if tmax is not None and tmin is not None else None,
            "precipitation_mm": precips[i] if i < len(precips) else 0,
            "wind_speed_kmh": winds[i] if i < len(winds) else 0,
            "weather_code": code,
            "weather_desc": WMO_CODES.get(code, "Unknown"),
        })

    return rows


def fetch_all_cities(days_back: int = 7) -> list[dict]:
    """
    获取所有5个城市的天气数据。

    Args:
        days_back: 向前追溯天数（Open-Meteo 免费版支持历史+预报）

    Returns:
        所有城市的天气记录列表
    """
    end = date.today()
    start = end.replace(day=end.day - days_back) if days_back < end.day else end.replace(month=end.month - 1, day=1)
    start_str = start.isoformat()
    end_str = end.isoformat()

    all_rows = []
    for city_name, (lat, lon) in WEATHER_CITIES.items():
        try:
            print(f"  [*] Fetching {city_name} weather... ({start_str} ~ {end_str})")
            rows = fetch_weather_for_city(lat, lon, city_name, start_str, end_str)
            all_rows.extend(rows)
            print(f"    [OK] {len(rows)} records")
            time.sleep(0.3)
        except Exception as e:
            print(f"    [FAIL] {city_name}: {e}")

    return all_rows


def fetch_history_all_cities(start_date, end_date) -> list[dict]:
    """
    获取所有城市的历史每日天气（Open-Meteo 归档 API，1940年至今）。

    Args:
        start_date/end_date: date 或 "YYYY-MM-DD"

    Returns:
        所有城市的天气记录列表
    """
    start_str = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
    end_str = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)

    all_rows = []
    for city_name, (lat, lon) in WEATHER_CITIES.items():
        try:
            print(f"  [*] Fetching {city_name} history... ({start_str} ~ {end_str})")
            rows = fetch_weather_for_city(
                lat, lon, city_name, start_str, end_str,
                api_url=WEATHER_ARCHIVE_API,
            )
            all_rows.extend(rows)
            print(f"    [OK] {len(rows)} records")
            time.sleep(0.3)
        except Exception as e:
            print(f"    [FAIL] {city_name}: {e}")

    return all_rows


if __name__ == "__main__":
    print("=" * 50)
    print("[Test] Open-Meteo Weather API")
    print("=" * 50)
    rows = fetch_all_cities(days_back=7)
    if rows:
        for r in rows[:3]:
            print(f"  {r['city_name']} {r['date']}: {r['weather_desc']} "
                  f"{r['temp_min_c']}~{r['temp_max_c']}C precip {r['precipitation_mm']}mm")
    print(f"\nTotal: {len(rows)} weather records")
