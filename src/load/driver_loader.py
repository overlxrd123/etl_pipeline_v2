"""Transactional driver updates; duplicate payloads do not duplicate rows."""
from datetime import datetime
import numpy as np
import pandas as pd
from sqlalchemy import select, text

from src.warehouse.models import DimCity, DimDate, DimWeather, DimCrypto


def load_weather_records(records, factory):
    if not records:
        raise ValueError('天气输入为空，拒绝将本次采集标记为成功')
    with factory() as session:
        cities = dict(session.execute(select(DimCity.city_name, DimCity.city_id)).all())
        dates = set(session.scalars(select(DimDate.date_id)).all())
        prepared = {}
        for source in records:
            city_id = cities.get(source.get('city_name'))
            stamp = pd.Timestamp(source.get('date'))
            date_id = int(stamp.strftime('%Y%m%d')) if not pd.isna(stamp) else 0
            if city_id is None or date_id not in dates:
                raise ValueError('天气城市或日期维度不存在')
            row = {key: source.get(key) for key in ('temp_max_c', 'temp_min_c', 'temp_avg_c', 'precipitation_mm', 'wind_speed_kmh', 'weather_code', 'weather_desc')}
            for key in ('temp_max_c', 'temp_min_c', 'precipitation_mm', 'wind_speed_kmh', 'weather_code'):
                row[key] = float(row[key])
                if not np.isfinite(row[key]):
                    raise ValueError(f'天气字段 {key} 无效')
            if row['precipitation_mm'] < 0 or row['wind_speed_kmh'] < 0 or row['temp_max_c'] < row['temp_min_c']:
                raise ValueError('天气数值范围无效')
            row['weather_code'] = int(row['weather_code'])
            row['temp_avg_c'] = (row['temp_min_c'] + row['temp_max_c']) / 2
            prepared[(city_id, date_id)] = row
        existing = {(r.city_id, r.date_id): r for r in session.scalars(
            select(DimWeather).where(DimWeather.date_id.in_({d for _, d in prepared})))}
        inserted = 0
        for (city_id, date_id), row in prepared.items():
            target = existing.get((city_id, date_id))
            if target is None:
                target = DimWeather(city_id=city_id, date_id=date_id)
                session.add(target)
                inserted += 1
            for key, value in row.items():
                setattr(target, key, value)
            target.fetched_at = datetime.now()
        session.commit()
        return inserted


def load_crypto_records(records, factory):
    if not records:
        raise ValueError('币价输入为空')
    prepared = {}
    for source in records:
        ticker = source['ticker']
        price = float(source['price_usd'])
        stamp = pd.Timestamp(source['recorded_at'])
        if ticker not in ('BTC', 'ETH') or not np.isfinite(price) or price <= 0 or pd.isna(stamp):
            raise ValueError('币种、价格或记录时间无效')
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert('UTC').tz_localize(None)
        stamp = stamp.to_pydatetime()
        prepared[(ticker, stamp)] = price
    with factory() as session:
        with session.get_bind().begin() as connection:
            connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_crypto_ticker_timestamp ON dim_crypto (ticker, recorded_at)'))
        existing = {(r.ticker, r.recorded_at): r for r in session.scalars(select(DimCrypto))}
        inserted = 0
        for (ticker, stamp), price in prepared.items():
            target = existing.get((ticker, stamp))
            if target is None:
                target = DimCrypto(ticker=ticker, recorded_at=stamp)
                session.add(target)
                inserted += 1
            target.price_usd = price
            target.fetched_at = datetime.now()
        session.commit()
        return inserted
