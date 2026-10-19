"""Failure/retry and quality-gate regressions; all writes use in-memory databases."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from config.db_connection import Base
from src.warehouse.models import DimCity, DimDate, DimProduct, DimCustomer, DimWeather, DimCrypto, FactOrders, EtlOrderKey, EtlLoadRun
from src.utils.date_utils import generate_date_dimension
from src.load.order_loader import load_orders_resumable
from src.load.driver_loader import load_weather_records, load_crypto_records
from src.utils.quality import check_warehouse


@pytest.fixture
def warehouse():
    engine = create_engine('sqlite:///:memory:')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as s:
        s.add(DimCity(city_id=1, city_name='Test City'))
        s.add(DimProduct(product_id=1, product_name='Test Product', category='Tablets', unit_price=10, unit_cost=5))
        s.bulk_insert_mappings(DimDate, generate_date_dimension(date(2026, 1, 1), date(2026, 1, 3)))
        s.commit()
        s.add(DimCustomer(customer_id=1, city_id=1))
        s.commit()
    yield factory
    engine.dispose()


def frame(count=3, explicit=True):
    rows = []
    for i in range(count):
        row = dict(customer_id=1, product_id=1, date_id=20260101, city_name='Test City', quantity=1,
                   unit_price=10, net_amount=10, discount_pct=0, payment_method='credit_card',
                   order_timestamp=datetime(2026, 1, 1, 12, 0, i))
        if explicit:
            row['source_order_id'] = f'order-{i}'
        rows.append(row)
    return pd.DataFrame(rows)


def test_repeat_load_is_idempotent(warehouse):
    assert load_orders_resumable(frame(), warehouse, 2) == 3
    assert load_orders_resumable(frame(), warehouse, 2) == 0
    with warehouse() as s:
        assert s.query(FactOrders).count() == 3
        assert s.query(EtlOrderKey).count() == 3


def test_retry_completes_only_uncommitted_batch(warehouse):
    failed = False
    def faulty_factory():
        session = warehouse()
        @event.listens_for(session, 'before_flush')
        def fail_third_order(s, *_):
            nonlocal failed
            if not failed and any(isinstance(o, FactOrders) and o.order_timestamp.second == 2 for o in s.new):
                failed = True
                raise OSError('simulated database interruption')
        return session
    with pytest.raises(OSError):
        load_orders_resumable(frame(), faulty_factory, 2)
    with warehouse() as s:
        assert s.query(FactOrders).count() == 2
        run = s.query(EtlLoadRun).one()
        assert run.status == 'failed' and run.inserted_rows == 2
    assert load_orders_resumable(frame(), warehouse, 2) == 1
    with warehouse() as s:
        assert s.query(FactOrders).count() == 3


def test_legacy_rows_are_adopted_without_new_ids(warehouse):
    data = frame(2, explicit=False)
    with warehouse() as s:
        for row in data.to_dict('records'):
            row['city_id'] = 1
            row.pop('city_name')
            s.add(FactOrders(**row))
        s.commit()
        before = list(s.scalars(select(FactOrders.order_id)))
    assert load_orders_resumable(data, warehouse) == 0
    assert load_orders_resumable(frame(2), warehouse) == 0
    with warehouse() as s:
        assert list(s.scalars(select(FactOrders.order_id))) == before


def test_identical_legacy_rows_keep_multiplicity(warehouse):
    data = pd.concat([frame(1, explicit=False)] * 2, ignore_index=True)
    assert load_orders_resumable(data, warehouse) == 2
    assert load_orders_resumable(data, warehouse) == 0


def test_duplicate_source_ids_deduplicate_but_conflicts_fail(warehouse):
    data = pd.concat([frame(1)] * 2, ignore_index=True)
    assert load_orders_resumable(data, warehouse) == 1
    changed = frame(1)
    changed.loc[0, ['unit_price', 'net_amount']] = 12
    with pytest.raises(ValueError, match='内容不同'):
        load_orders_resumable(changed, warehouse)
    with warehouse() as s:
        assert s.query(FactOrders).one().net_amount == 10


@pytest.mark.parametrize('column,value', [('city_name','Unknown'), ('customer_id',99), ('net_amount',-1),
                                          ('unit_price',float('nan')), ('date_id',20260102), ('quantity',1.5)])
def test_invalid_input_inserts_no_orders(warehouse, column, value):
    data = frame()
    if column == 'quantity':
        data[column] = data[column].astype(float)
    data.loc[2, column] = value
    with pytest.raises(ValueError):
        load_orders_resumable(data, warehouse, 2)
    with warehouse() as s:
        assert s.query(FactOrders).count() == 0
        assert s.query(EtlLoadRun).one().status == 'failed'


def weather_row():
    return dict(city_name='Test City', date='2026-01-01', temp_max_c=20, temp_min_c=10,
                precipitation_mm=0, wind_speed_kmh=5, weather_code=0, weather_desc='Clear')


def test_weather_refresh_updates_existing_city_day(warehouse):
    row = weather_row()
    assert load_weather_records([row, row], warehouse) == 1
    row['temp_max_c'] = 22
    assert load_weather_records([row], warehouse) == 0
    with warehouse() as s:
        assert s.query(DimWeather).one().temp_max_c == 22


def test_crypto_retry_deduplicates_and_updates(warehouse):
    row = dict(ticker='BTC', price_usd=100, recorded_at=datetime(2026,1,1,tzinfo=timezone.utc))
    assert load_crypto_records([row, row], warehouse) == 1
    row['price_usd'] = 110
    assert load_crypto_records([row], warehouse) == 0
    with warehouse() as s:
        assert s.query(DimCrypto).one().price_usd == 110


def test_quality_gate_requires_driver_coverage(warehouse):
    load_orders_resumable(frame(1), warehouse)
    with pytest.raises(ValueError, match='missing_weather'):
        check_warehouse(warehouse)
    load_weather_records([weather_row()], warehouse)
    rows = [dict(ticker=t, price_usd=100, recorded_at=datetime(2026,1,1)) for t in ('BTC','ETH')]
    load_crypto_records(rows, warehouse)
    assert check_warehouse(warehouse)['fact_orders_count'] == 1


@pytest.mark.parametrize('today', [date(2026,1,3), date(2026,3,2), date(2026,10,1)])
def test_weather_window_crosses_month_and_year(monkeypatch, today):
    from src.extract import weather_api as api
    class Clock(date):
        @classmethod
        def today(cls):
            return today
    fetch = Mock(return_value=[{}] * 7)
    monkeypatch.setattr(api, 'date', Clock)
    monkeypatch.setattr(api, 'fetch_weather_for_city', fetch)
    monkeypatch.setattr(api.time, 'sleep', lambda _: None)
    api.fetch_all_cities(7)
    assert fetch.call_args.args[3:5] == ((today - timedelta(days=7)).isoformat(), (today - timedelta(days=1)).isoformat())


def test_partial_weather_failure_is_not_success(monkeypatch):
    from src.extract import weather_api as api
    monkeypatch.setattr(api, 'WEATHER_CITIES', {'A':(1,2), 'B':(3,4)})
    monkeypatch.setattr(api.time, 'sleep', lambda _: None)
    monkeypatch.setattr(api, 'fetch_weather_for_city', Mock(side_effect=[[{}]*7, OSError('network')]))
    with pytest.raises(RuntimeError, match='B'):
        api.fetch_all_cities()


def test_quality_failure_stops_dbt(monkeypatch):
    from orchestration.flows import run_full_pipeline as module
    import config.db_connection as connection
    import seed_data
    monkeypatch.setattr(connection, 'init_db', lambda: None)
    monkeypatch.setattr(seed_data, 'seed_dim_date', lambda: None)
    monkeypatch.setattr(seed_data, 'seed_dim_city', lambda: None)
    monkeypatch.setattr(module, 'generate_orders_flow', lambda **kwargs: 1)
    monkeypatch.setattr(module, 'task_quality_check', Mock(side_effect=ValueError('quality failed')))
    dbt = Mock()
    monkeypatch.setattr(module, 'task_run_dbt', dbt)
    with pytest.raises(ValueError, match='quality failed'):
        module.run_full_pipeline.fn(skip_api=True)
    dbt.assert_not_called()


def test_nonfinite_values_fail_generic_validators():
    from src.utils.validators import check_positive, check_range
    data = pd.DataFrame({'x':[1., float('nan'), float('inf')]})
    assert not check_positive(data, 'x')['passed']
    assert not check_range(data, 'x', 0, 10)['passed']


def test_incomplete_history_is_rejected_before_rebuild():
    from src.load.driver_validation import validate_history
    weather = pd.DataFrame([weather_row()])
    crypto = pd.DataFrame([dict(ticker=t, price_usd=100, recorded_at='2026-01-01') for t in ('BTC','ETH')])
    validate_history(weather, crypto, '2026-01-01', '2026-01-01', ['Test City'])
    with pytest.raises(ValueError, match='天气覆盖不足'):
        validate_history(weather, crypto, '2026-01-01', '2026-01-02', ['Test City'])


def test_generation_reuses_original_csv(monkeypatch, tmp_path):
    import config.settings as settings
    from orchestration.flows import generate_orders as module
    frame().to_csv(tmp_path / 'orders.csv', index=False)
    monkeypatch.setattr(settings, 'DATA_PROCESSED', tmp_path)
    monkeypatch.setattr(settings, 'SIM_START', '2026-01-01')
    monkeypatch.setattr(settings, 'SIM_END', '2026-01-01')
    drivers = Mock(side_effect=AssertionError('cached orders must not be regenerated'))
    monkeypatch.setattr(module, 'load_drivers_from_db', drivers)
    assert len(module.task_gen_orders.fn(None, None)) == 3
    drivers.assert_not_called()


def test_existing_orders_block_implicit_regeneration(warehouse, monkeypatch, tmp_path):
    import config.db_connection as connection
    import config.settings as settings
    from orchestration.flows.generate_orders import generate_orders_flow
    load_orders_resumable(frame(1), warehouse)
    monkeypatch.setattr(connection, 'get_session', warehouse)
    monkeypatch.setattr(settings, 'DATA_PROCESSED', tmp_path)
    with pytest.raises(ValueError, match='禁止隐式重新生成'):
        generate_orders_flow.fn(force=True)


def test_incomplete_live_crypto_uses_next_source(monkeypatch):
    from src.extract import crypto_api as api
    incomplete = Mock(return_value=[dict(ticker='BTC', price_usd=100)])
    complete = Mock(return_value=[dict(ticker=t, price_usd=100) for t in ('BTC', 'ETH')])
    monkeypatch.setattr(api, 'SOURCES', [('incomplete', incomplete), ('complete', complete)])
    result = api.fetch_crypto_prices()
    assert {r['ticker'] for r in result} == {'BTC', 'ETH'}
    complete.assert_called_once()


def test_csv_business_ids_preserve_leading_zeros(warehouse, monkeypatch, tmp_path):
    from src.load import staging_to_warehouse as loader
    data = frame(1)
    data['source_order_id'] = '001'
    data.to_csv(tmp_path / 'orders.csv', index=False)
    monkeypatch.setattr(loader, 'DATA_PROCESSED', tmp_path)
    monkeypatch.setattr(loader, 'get_session', warehouse)
    assert loader.load_orders() == 1
    assert loader.load_orders(data) == 0
