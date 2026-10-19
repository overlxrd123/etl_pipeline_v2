"""Validated, resumable order loading. Never deletes existing warehouse data."""
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import select, insert, func

from src.warehouse.models import DimCity, DimCustomer, DimDate, DimProduct, EtlLoadRun, EtlOrderKey, FactOrders

FIELDS = ('customer_id', 'product_id', 'date_id', 'city_id', 'quantity', 'unit_price',
          'discount_pct', 'net_amount', 'payment_method', 'crypto_ticker',
          'crypto_rate_usd', 'order_status', 'order_timestamp')


def fingerprint(row):
    def normalized(value):
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (datetime, pd.Timestamp)):
            return pd.Timestamp(value).isoformat()
        if isinstance(value, (int, float, np.number, Decimal)):
            return str(Decimal(str(value)).normalize())
        return str(value)
    payload = [normalized(row.get(key)) for key in FIELDS]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def _integer(value, field):
    number = float(value)
    if not np.isfinite(number) or not number.is_integer() or number <= 0:
        raise ValueError(f'{field} 必须为正整数')
    return int(number)


def prepare_orders(frame, session):
    required = {'customer_id', 'product_id', 'date_id', 'city_name', 'unit_price',
                'net_amount', 'payment_method', 'order_timestamp'}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f'订单缺少字段: {sorted(missing)}')
    cities = dict(session.execute(select(DimCity.city_name, DimCity.city_id)).all())
    ids = {name: set(session.scalars(select(model)).all()) for name, model in (
        ('customer_id', DimCustomer.customer_id), ('product_id', DimProduct.product_id),
        ('date_id', DimDate.date_id))}
    occurrences, seen, prepared = Counter(), {}, []
    for index, source in enumerate(frame.to_dict('records'), 1):
        try:
            row = {key: source.get(key) for key in FIELDS}
            row['city_id'] = cities.get(source['city_name'])
            if row['city_id'] is None:
                raise ValueError('城市不存在')
            for key in ('customer_id', 'product_id', 'date_id'):
                row[key] = _integer(row[key], key)
                if row[key] not in ids[key]:
                    raise ValueError(f'{key} 没有对应维度记录')
            row['quantity'] = _integer(source.get('quantity', 1), 'quantity')
            row['discount_pct'] = float(source.get('discount_pct', 0))
            row['unit_price'] = float(row['unit_price'])
            row['net_amount'] = float(row['net_amount'])
            if not all(np.isfinite(row[k]) for k in ('discount_pct', 'unit_price', 'net_amount')):
                raise ValueError('金额和折扣不能缺失或无限大')
            if row['unit_price'] <= 0 or row['net_amount'] <= 0 or not 0 <= row['discount_pct'] <= 100:
                raise ValueError('金额必须为正数，折扣必须在 0 到 100 之间')
            expected = round(row['unit_price'] * row['quantity'] * (1 - row['discount_pct'] / 100), 2)
            if abs(expected - row['net_amount']) > .021:
                raise ValueError('实付金额与数量、单价和折扣不一致')
            timestamp = pd.Timestamp(row['order_timestamp'])
            if pd.isna(timestamp) or timestamp.tzinfo is not None:
                raise ValueError('订单时间必须为有效的无时区业务时间')
            if int(timestamp.strftime('%Y%m%d')) != row['date_id']:
                raise ValueError('订单时间与 date_id 不一致')
            row['order_timestamp'] = timestamp.to_pydatetime()
            row['order_status'] = source.get('order_status', 'completed')
            if row['order_status'] not in ('completed', 'cancelled'):
                raise ValueError('不支持的订单状态')
            payment = row['payment_method']
            if payment not in ('credit_card', 'crypto_btc', 'crypto_eth'):
                raise ValueError('不支持的支付方式')
            for key in ('crypto_ticker', 'crypto_rate_usd'):
                if pd.isna(row[key]):
                    row[key] = None
            if payment != 'credit_card':
                expected_ticker = 'BTC' if payment == 'crypto_btc' else 'ETH'
                rate = float(row['crypto_rate_usd'] or 0)
                if row['crypto_ticker'] != expected_ticker or not np.isfinite(rate) or rate <= 0:
                    raise ValueError('加密支付的币种或汇率无效')
                row['crypto_rate_usd'] = rate
            elif row['crypto_ticker'] is not None or row['crypto_rate_usd'] is not None:
                raise ValueError('信用卡订单不应包含加密支付信息')
            fp = fingerprint(row)
            occurrences[fp] += 1
            legacy_key = f'legacy:{fp}:{occurrences[fp]}'
            raw_key = source.get('source_order_id')
            explicit = raw_key is not None and not pd.isna(raw_key)
            if explicit and (not str(raw_key).strip() or len(str(raw_key)) > 200):
                raise ValueError('source_order_id 必须为 1–200 个字符')
            key = f'source:{str(raw_key).strip()}' if explicit else legacy_key
            if key in seen:
                if seen[key] != fp:
                    raise ValueError('同一来源订单 ID 对应不同内容')
                continue
            seen[key] = fp
            prepared.append((key, legacy_key, fp, row))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ValueError(f'第 {index} 行订单无效: {exc}') from exc
    return prepared


def load_orders_resumable(frame, session_factory, batch_size=10000):
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError('batch_size 必须为正整数')
    session = session_factory()
    run_id = str(uuid.uuid4())
    inserted = skipped = 0
    run_started = False
    try:
        bind = session.get_bind()
        EtlOrderKey.__table__.create(bind, checkfirst=True)
        EtlLoadRun.__table__.create(bind, checkfirst=True)
        session.add(EtlLoadRun(run_id=run_id, status='running', input_rows=len(frame), started_at=datetime.now()))
        session.commit()
        run_started = True
        # Validate the whole input before inserting any orders.
        prepared = prepare_orders(frame, session)
        skipped = len(frame) - len(prepared)
        existing = {key: (order_id, fp) for key, order_id, fp in session.execute(
            select(EtlOrderKey.source_key, EtlOrderKey.order_id, EtlOrderKey.fingerprint))}
        mapped = {order_id for order_id, _ in existing.values()}
        # Upgrade old databases without rewriting order IDs or business values.
        occurrences, upgrades = Counter(), []
        if session.scalar(select(func.count()).select_from(FactOrders)) > len(mapped):
            for order in session.scalars(select(FactOrders).order_by(FactOrders.order_id)).yield_per(1000):
                fp = fingerprint({field: getattr(order, field) for field in FIELDS})
                occurrences[fp] += 1
                key = f'legacy:{fp}:{occurrences[fp]}'
                if order.order_id not in mapped:
                    upgrades.append(dict(source_key=key, order_id=order.order_id, fingerprint=fp))
                    existing[key] = (order.order_id, fp)
                if len(upgrades) >= 1000:
                    session.execute(insert(EtlOrderKey), upgrades)
                    upgrades.clear()
            if upgrades:
                session.execute(insert(EtlOrderKey), upgrades)
        session.commit()
        pending = []
        for key, legacy_key, fp, row in prepared:
            found = existing.get(key)
            if not found and key.startswith('source:') and legacy_key in existing:
                found = existing.pop(legacy_key)
                mapping = session.get(EtlOrderKey, legacy_key)
                mapping.source_key = key
                existing[key] = found
            if found:
                if found[1] != fp:
                    raise ValueError(f'来源订单 {key} 已存在，但内容不同；请显式处理更正数据')
                skipped += 1
            else:
                pending.append((key, fp, row))
        session.commit()
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            orders = [FactOrders(**row) for _, _, row in batch]
            session.add_all(orders)
            session.flush()
            session.add_all([EtlOrderKey(source_key=key, order_id=order.order_id, fingerprint=fp)
                             for (key, fp, _), order in zip(batch, orders)])
            run = session.get(EtlLoadRun, run_id)
            run.inserted_rows = inserted + len(batch)
            run.skipped_rows = skipped
            session.commit()  # Orders, identities and checkpoint are atomic within a batch.
            inserted += len(batch)
        run = session.get(EtlLoadRun, run_id)
        run.status, run.inserted_rows, run.skipped_rows = 'completed', inserted, skipped
        run.finished_at = datetime.now()
        session.commit()
        print(f'[Orders] 新增 {inserted:,}，已存在 {skipped:,}，批次 {run_id}')
        return inserted
    except Exception as exc:
        session.rollback()
        run = session.get(EtlLoadRun, run_id) if run_started else None
        if run is not None:
            run.status, run.error_type, run.finished_at = 'failed', type(exc).__name__, datetime.now()
            session.commit()
        raise
    finally:
        session.close()
