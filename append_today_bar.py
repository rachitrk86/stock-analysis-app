import pandas as pd
import time
from datetime import datetime
from fyers_connect import get_fyers_client

def fetch_today_bar(symbol, fyers):
    today = datetime.now().strftime("%Y-%m-%d")
    params = {
        "symbol": symbol,
        "resolution": "1D",
        "date_format": "1",
        "range_from": today,
        "range_to": today,
        "cont_flag": "1"
    }
    resp = fyers.history(params)
    bars = resp.get("candles", [])
    if not bars:
        print(f"x No bar for {symbol}")
        return None
    # FYERS: [timestamp, open, high, low, close, volume]
    bar = bars[-1]
    return {
        "symbol": symbol,
        "timestamp": bar[0],
        "open": bar[1],
        "high": bar[2],
        "low": bar[3],
        "close": bar[4],
        "volume": bar[5],
    }

if __name__ == "__main__":
    fyers = get_fyers_client()
    stock_list = pd.read_csv("stock_universe.csv")
    bars_file = "nse_daily_bars_fyers.csv"
    try:
        df_bars = pd.read_csv(bars_file)
    except FileNotFoundError:
        df_bars = pd.DataFrame(
            columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"]
        )

    # Build symbols as "NSE:TCS-EQ"
    symbols = [
        f"{row['exchange'].strip().upper()}:{row['symbol'].strip().upper()}-EQ"
        for _, row in stock_list.iterrows()
    ]

    batch_size = 100
    appended = 0
    total_batches = (len(symbols) + batch_size - 1) // batch_size
    time.sleep(10)
    for batch_idx in range(total_batches):
        batch_symbols = symbols[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        print(f"\n=== Processing batch {batch_idx + 1} of {total_batches} ===")
        for symbol in batch_symbols:
            print(f"Fetching {symbol}...", end="")
            bar = fetch_today_bar(symbol, fyers)
            if bar is None:
                print(" skip")
                continue
            # Check if already present (by symbol and timestamp)
            if not ((df_bars["symbol"] == bar["symbol"]) & (df_bars["timestamp"] == bar["timestamp"])).any():
                df_bars = pd.concat([df_bars, pd.DataFrame([bar])], ignore_index=True)
                appended += 1
                print(" done")
            else:
                print(" already exists")
            time.sleep(0.25)  # Rate limit protection between requests
        if batch_idx != total_batches - 1:  # No need to sleep after the last batch
            print(f"Sleeping for 60 seconds after batch {batch_idx + 1}...")
            time.sleep(20)

    df_bars.to_csv(bars_file, index=False)
    print(f"ok Appended {appended} new bars. Saved to {bars_file}")
