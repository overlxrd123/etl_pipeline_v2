"""
加密汇率 API 客户端
按顺序尝试多个免费行情源（CoinGecko → Binance → Gate.io），
返回第一个成功源的数据。不同网络环境下总有一个能通。
"""
import requests
from datetime import datetime, timezone, timedelta
from config.settings import COINGECKO_API, CRYPTO_TICKERS

BINANCE_API = "https://data-api.binance.vision/api/v3/ticker/price"
BINANCE_KLINES = "https://data-api.binance.vision/api/v3/klines"
GATE_API = "https://api.gateio.ws/api/v4/spot/tickers"

TICKER_LABELS = {"bitcoin": "BTC", "ethereum": "ETH"}

# 币种 → 各数据源的交易对
SYMBOL_MAP = {
    "bitcoin":  {"binance": "BTCUSDT", "gate": "BTC_USDT"},
    "ethereum": {"binance": "ETHUSDT", "gate": "ETH_USDT"},
}


def _fetch_coingecko(tickers: list[str], timeout: int) -> list[dict]:
    """CoinGecko: /simple/price"""
    resp = requests.get(
        COINGECKO_API,
        params={"ids": ",".join(tickers), "vs_currencies": "usd"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"ticker": TICKER_LABELS.get(k, k.upper()), "price_usd": v.get("usd")}
        for k, v in data.items() if v.get("usd") is not None
    ]


def _fetch_binance(tickers: list[str], timeout: int) -> list[dict]:
    """Binance 现货最新成交价（data-api 域名在部分网络下可访问）"""
    rows = []
    for t in tickers:
        symbol = SYMBOL_MAP.get(t, {}).get("binance")
        if not symbol:
            continue
        resp = requests.get(BINANCE_API, params={"symbol": symbol}, timeout=timeout)
        resp.raise_for_status()
        rows.append({
            "ticker": TICKER_LABELS.get(t, t.upper()),
            "price_usd": float(resp.json()["price"]),
        })
    return rows


def _fetch_gate(tickers: list[str], timeout: int) -> list[dict]:
    """Gate.io 现货 ticker 最新价"""
    rows = []
    for t in tickers:
        pair = SYMBOL_MAP.get(t, {}).get("gate")
        if not pair:
            continue
        resp = requests.get(GATE_API, params={"currency_pair": pair}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            rows.append({
                "ticker": TICKER_LABELS.get(t, t.upper()),
                "price_usd": float(data[0]["last"]),
            })
    return rows


# 按顺序尝试的数据源
SOURCES = [
    ("CoinGecko", _fetch_coingecko),
    ("Binance",   _fetch_binance),
    ("Gate.io",   _fetch_gate),
]


def fetch_crypto_prices(tickers: list[str] | None = None,
                        timeout: int = 8) -> list[dict]:
    """
    获取 BTC/ETH 当前美元价格，自动在多个行情源之间切换。

    Returns:
        [{ticker: "BTC", price_usd: 67890.12, recorded_at: datetime}, ...]
    """
    tickers = tickers or CRYPTO_TICKERS
    errors = []

    for name, fetcher in SOURCES:
        try:
            rows = fetcher(tickers, timeout)
            if not rows:
                raise ValueError("返回数据为空")
            now = datetime.now(timezone.utc)
            for r in rows:
                r["recorded_at"] = now
                r["fetched_at"] = now
            print(f"  [OK] 行情源: {name}")
            return rows
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            print(f"  [FAIL] {name}: {type(e).__name__}")

    raise RuntimeError("所有行情源均失败:\n  " + "\n  ".join(errors))


def fetch_crypto_history(start_date, end_date,
                         tickers: list[str] | None = None,
                         timeout: int = 20) -> list[dict]:
    """
    获取历史每日收盘价（Binance 日 K 线，UTC 00:00 开盘时间）。

    Args:
        start_date/end_date: date 或 "YYYY-MM-DD"

    Returns:
        [{ticker: "BTC", price_usd: 67890.12, recorded_at: datetime}, ...]
        每天每个币种一条记录
    """
    from datetime import date as date_cls

    def _as_date(d):
        return date_cls.fromisoformat(d) if isinstance(d, str) else d

    start = _as_date(start_date)
    end = _as_date(end_date)
    start_ms = int(datetime(start.year, start.month, start.day,
                            tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(end.year, end.month, end.day,
                          tzinfo=timezone.utc).timestamp() * 1000) + 86_400_000

    tickers = tickers or CRYPTO_TICKERS
    results = []

    for t in tickers:
        symbol = SYMBOL_MAP.get(t, {}).get("binance")
        if not symbol:
            continue
        resp = requests.get(
            BINANCE_KLINES,
            params={
                "symbol": symbol,
                "interval": "1d",
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        for k in resp.json():
            results.append({
                "ticker": TICKER_LABELS.get(t, t.upper()),
                "price_usd": float(k[4]),  # 收盘价
                "recorded_at": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
            })
        print(f"  [OK] {t.upper()} 历史日线: {len(resp.json())} 条")

    return results


if __name__ == "__main__":
    print("=" * 50)
    print("测试: CoinGecko 加密 API")
    print("=" * 50)
    try:
        prices = fetch_crypto_prices()
        for p in prices:
            print(f"  {p['ticker']}: ${p['price_usd']:,.2f}  ({p['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC)")
    except Exception as e:
        print(f"  ❌ API调用失败: {e}")
        print("  提示: CoinGecko免费API可能有频率限制，稍后重试")
