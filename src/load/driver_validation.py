"""Fail closed on incomplete historical drivers before rebuilding demo tables."""
from datetime import date
import pandas as pd
import numpy as np


def validate_history(weather_df, crypto_df, start_date, end_date, cities):
    days = pd.date_range(start_date, end_date).strftime('%Y-%m-%d').tolist()
    if not days:
        raise ValueError('历史窗口为空')
    required_weather = {'city_name', 'date', 'weather_code', 'temp_max_c', 'temp_min_c', 'precipitation_mm', 'wind_speed_kmh'}
    required_crypto = {'ticker', 'recorded_at', 'price_usd'}
    if not required_weather <= set(weather_df) or not required_crypto <= set(crypto_df):
        raise ValueError('历史驱动数据缺少必要字段')
    weather = weather_df.copy()
    weather['date'] = pd.to_datetime(weather['date'], errors='raise').dt.strftime('%Y-%m-%d')
    expected_weather = {(city, day) for city in cities for day in days}
    actual_weather = set(zip(weather.city_name, weather.date))
    if expected_weather - actual_weather:
        raise ValueError(f'天气覆盖不足：缺少 {len(expected_weather - actual_weather)} 个城市日')
    if weather.duplicated(['city_name', 'date']).any():
        raise ValueError('历史天气存在重复城市日')
    numeric = weather[['weather_code', 'temp_max_c', 'temp_min_c', 'precipitation_mm', 'wind_speed_kmh']].apply(pd.to_numeric, errors='raise')
    if not np.isfinite(numeric.to_numpy()).all() or (numeric.precipitation_mm < 0).any():
        raise ValueError('历史天气数值无效')
    crypto = crypto_df.copy()
    crypto['day'] = pd.to_datetime(crypto.recorded_at, utc=True, errors='raise').dt.strftime('%Y-%m-%d')
    expected_crypto = {(ticker, day) for ticker in ('BTC', 'ETH') for day in days}
    if expected_crypto - set(zip(crypto.ticker, crypto.day)):
        raise ValueError('历史币价没有完整覆盖 BTC/ETH 与订单日期')
    prices = pd.to_numeric(crypto.price_usd, errors='raise')
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError('历史币价必须为有限正数')
