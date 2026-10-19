"""
Prefect Flow: 加密汇率采集 + 加载
从 Binance 获取 BTC/ETH 现货价（CoinGecko / Gate.io 兜底）→ 写入 dim_crypto
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prefect import flow, task
from datetime import datetime

from src.extract.crypto_api import fetch_crypto_prices, fetch_crypto_history
from src.load.raw_to_staging import load_crypto


@task(name="fetch-crypto", retries=3, retry_delay_seconds=30)
def task_fetch_crypto(start_date=None, end_date=None):
    """从 API 获取加密价格"""
    print(f"[Crypto] 获取 BTC/ETH 价格... ({datetime.now().strftime('%H:%M:%S')})")
    if bool(start_date) != bool(end_date):
        raise ValueError("历史币价必须同时提供起止日期")
    rows = fetch_crypto_history(start_date, end_date) if start_date else fetch_crypto_prices()
    for r in rows:
        print(f"  {r['ticker']}: ${r['price_usd']:,.2f}")
    return rows


@task(name="load-crypto")
def task_load_crypto(rows: list[dict]):
    """加载加密数据到数仓"""
    if not rows:
        raise ValueError("币价采集为空，拒绝继续加载")
    return load_crypto(rows)


@flow(name="ingest-crypto")
def ingest_crypto(start_date=None, end_date=None):
    """加密汇率采集完整流程"""
    rows = task_fetch_crypto(start_date, end_date)
    count = task_load_crypto(rows)
    print(f"[Flow: ingest-crypto] 完成 — {count} 条")
    return count


if __name__ == "__main__":
    ingest_crypto()
