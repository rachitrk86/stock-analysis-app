import pandas as pd
import numpy as np

def add_features(df):
    """
    Add technical indicator features to daily OHLCV DataFrame.
    Expects columns: symbol, timestamp, open, high, low, close, volume
    """

    # Ensure proper types and sorting
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    df = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    result_frames = []

    for symbol, group in df.groupby("symbol"):
        g = group.copy()
        # EMA
        g["EMA5"] = g["close"].ewm(span=5, adjust=False).mean()
        g["EMA20"] = g["close"].ewm(span=20, adjust=False).mean()
        g["EMA_diff"] = g["EMA5"] - g["EMA20"]
        # RSI14
        delta = g["close"].diff()
        up = np.where(delta > 0, delta, 0)
        down = np.where(delta < 0, -delta, 0)
        roll_up = pd.Series(up).rolling(window=14, min_periods=1).mean()
        roll_down = pd.Series(down).rolling(window=14, min_periods=1).mean()
        rs = roll_up / (roll_down + 1e-8)
        g["RSI14"] = 100 - (100 / (1 + rs))
        # MACD
        ema12 = g["close"].ewm(span=12, adjust=False).mean()
        ema26 = g["close"].ewm(span=26, adjust=False).mean()
        g["MACD"] = ema12 - ema26
        g["MACD_sig"] = g["MACD"].ewm(span=9, adjust=False).mean()
        g["MACD_hist"] = g["MACD"] - g["MACD_sig"]
        # Bollinger Bands
        ma20 = g["close"].rolling(window=20, min_periods=1).mean()
        std20 = g["close"].rolling(window=20, min_periods=1).std()
        g["BB_upper"] = ma20 + 2 * std20
        g["BB_lower"] = ma20 - 2 * std20
        g["BB_%B"] = (g["close"] - g["BB_lower"]) / (g["BB_upper"] - g["BB_lower"] + 1e-8)
        g["BB_bandwidth"] = (g["BB_upper"] - g["BB_lower"]) / (ma20 + 1e-8)
        # ATR14 (Safe way)
        prev_close = g["close"].shift()
        tr = pd.concat([
            g["high"] - g["low"],
            (g["high"] - prev_close).abs(),
            (g["low"] - prev_close).abs()
        ], axis=1).max(axis=1)
        g["ATR14"] = tr.rolling(window=14, min_periods=1).mean()
        # OBV
        obv = [0]
        for i in range(1, len(g)):
            if g["close"].iloc[i] > g["close"].iloc[i-1]:
                obv.append(obv[-1] + g["volume"].iloc[i])
            elif g["close"].iloc[i] < g["close"].iloc[i-1]:
                obv.append(obv[-1] - g["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        g["OBV"] = obv
        # Append to result
        result_frames.append(g)

    features = pd.concat(result_frames).sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    # Clean up: keep only feature columns and core info
    keep_cols = [
        "symbol", "timestamp", "open", "high", "low", "close", "volume",
        "EMA5", "EMA20", "EMA_diff", "RSI14", "MACD", "MACD_sig", "MACD_hist",
        "BB_%B", "BB_bandwidth", "ATR14", "OBV"
    ]
    features = features[keep_cols]
    return features

if __name__ == "__main__":
    df = pd.read_csv("nse_daily_bars_fyers.csv")
    print(f"Loaded: {df.shape}")
    features = add_features(df)
    print("With features:", features.shape)
    print(features.head(10))
    features.to_csv("training_features.csv", index=False)
    print("✅ Features saved to training_features.csv")
