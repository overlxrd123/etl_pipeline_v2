"""
CoinGecko 加密汇率 API 客户端
免费，每分钟 10-30 次调用
API: /api/v3/simple/price
"""
import requests
from datetime import datetime, timezone
from config.settings import COINGECKO_API, CRYPTO_TICKERS


def fetch_crypto_prices(tickers: list[str] | None = None) -> list[dict]:
    """
    获取 BTC/ETH 当前美元价格。

    Returns:
        [{ticker: "BTC", price_usd: 67890.12, recorded_at: datetime}, ...]
    """
    tickers = tickers or CRYPTO_TICKERS
    params = {
        "ids": ",".join(tickers),
        "vs_currencies": "usd",
    }

    resp = requests.get(COINGECKO_API, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    now = datetime.now(timezone.utc)

    results = []
    ticker_map = {"bitcoin": "BTC", "ethereum": "ETH"}
    for key, values in data.items():
        results.append({
            "ticker": ticker_map.get(key, key.upper()),
            "price_usd": values.get("usd"),
            "recorded_at": now,
            "fetched_at": now,
        })

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
