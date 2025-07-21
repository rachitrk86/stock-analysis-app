#!/usr/bin/env python3
import pandas as pd
import numpy as np
import joblib
import logging
import time
from fyers_connect import get_fyers_client

BATCH_SIZE   = 100
SLEEP_SEC    = 20
MODEL_PATH   = "models/ai_model.pkl"
UNIVERSE_CSV = "stock_universe.csv"
OUTPUT_CSV   = "ai_scanner_output.csv"

def get_live_quote(symbol, fyers):
    try:
        data = {"symbols": symbol}
        resp = fyers.quotes(data)
        if isinstance(resp, dict) and resp.get("s") == "ok" and "d" in resp:
            qlist = resp["d"]
            if qlist and isinstance(qlist, list) and "v" in qlist[0]:
                v = qlist[0]["v"]
                return v.get("lp", None), v.get("volume", 0)
        return None, 0
    except Exception as e:
        logging.warning(f"Quote fail for {symbol}: {e}")
        return None, 0

def fetch_recent_bars(symbol, fyers, days=30):
    try:
        date_to = pd.Timestamp.today()
        date_from = date_to - pd.Timedelta(days=days*1.5)
        data = {
            "symbol": symbol,
            "resolution": "1D",
            "date_format": "1",
            "range_from": date_from.strftime("%Y-%m-%d"),
            "range_to": date_to.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }
        resp = fyers.history(data)
        if resp.get("s") == "ok" and "candles" in resp:
            bars = resp["candles"]
            df = pd.DataFrame(bars, columns=["ts","open","high","low","close","volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="s")
            return df.tail(days)
    except Exception as e:
        logging.warning(f"History fail for {symbol}: {e}")
    return pd.DataFrame()

def compute_features(df):
    if df.empty or len(df) < 20:
        return {}
    feats = {}
    df = df.copy()
    df["TR"] = np.maximum(df["high"] - df["low"],
                          np.maximum(abs(df["high"] - df["close"].shift(1)),
                                     abs(df["low"] - df["close"].shift(1))))
    feats["ATR14"] = df["TR"].rolling(14).mean().iloc[-1]
    feats["EMA5"]  = df["close"].ewm(span=5).mean().iloc[-1]
    feats["EMA20"] = df["close"].ewm(span=20).mean().iloc[-1]
    feats["EMA_diff"] = feats["EMA5"] - feats["EMA20"]
    delta = df["close"].diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    roll_up = up.rolling(14).mean()
    roll_down = down.rolling(14).mean()
    rs = roll_up.iloc[-1] / (roll_down.iloc[-1]+1e-9)
    feats["RSI14"] = 100 - (100/(1+rs))
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_sig = macd.ewm(span=9, adjust=False).mean()
    feats["MACD"] = macd.iloc[-1]
    feats["MACD_sig"] = macd_sig.iloc[-1]
    feats["MACD_hist"] = (macd - macd_sig).iloc[-1]
    bb_mid = df["close"].rolling(20).mean().iloc[-1]
    bb_std = df["close"].rolling(20).std().iloc[-1]
    feats["BB_bandwidth"] = (2*bb_std)/bb_mid if bb_mid else 0
    feats["BB_%B"] = (df["close"].iloc[-1] - (bb_mid-2*bb_std))/(4*bb_std) if bb_std else 0
    feats["open"] = df["open"].iloc[-1]
    feats["high"] = df["high"].iloc[-1]
    feats["low"] = df["low"].iloc[-1]
    feats["close"] = df["close"].iloc[-1]
    feats["volume"] = df["volume"].iloc[-1]
    return feats

def run_scanner():
    print("===== Swing Trading AI Scanner Debug Log =====")
    # Load model
    try:
        model, feature_list = joblib.load(MODEL_PATH)
        print(f"Loaded model from {MODEL_PATH}, features: {feature_list}")
    except Exception as e:
        print("❌ Could not load AI model:", e)
        return pd.DataFrame()

    # Load universe
    universe = pd.read_csv(UNIVERSE_CSV)
    symbols = [
        f"{row['exchange'].strip().upper()}:{row['symbol'].strip().upper()}-EQ"
        for _, row in universe.iterrows()
    ]
    print(f"Loaded universe: {len(symbols)} symbols (first 5: {symbols[:5]})")
    fyers = get_fyers_client()
    records = []

    # Batch loop
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i+BATCH_SIZE]
        print(f"\nProcessing batch {i//BATCH_SIZE+1} / {(len(symbols)-1)//BATCH_SIZE+1} ({len(batch)} symbols)")
        for idx, sym in enumerate(batch, i+1):
            print(f"--- [{idx}/{len(symbols)}] {sym} ---")
            ltp, vol = get_live_quote(sym, fyers)
            print(f"  LTP: {ltp}, Volume: {vol}")
            bars = fetch_recent_bars(sym, fyers, days=30)
            print(f"  Bars fetched: {len(bars)}")
            if ltp is None or bars.empty:
                print("  ⛔ Skipped: No price or bars.\n")
                continue
            feats = compute_features(bars)
            if not feats or any(np.isnan(v) for v in feats.values()):
                print("  ⛔ Skipped: Feature NaN or empty.\n")
                continue
            feature_vec = [float(feats.get(f, 0)) for f in feature_list]
            try:
                score = model.predict_proba([feature_vec])[0][1]
            except Exception as e:
                print("  ⛔ Model prediction failed:", e)
                score = 0.0
            atr = feats.get("ATR14", 0)
            exp_ret = score * (atr/bars["close"].iloc[-1] if atr and bars["close"].iloc[-1] else 0.03)
            target_price = ltp * (1 + max(0.02, exp_ret))
            records.append({
                "symbol": sym,
                "price": ltp,
                "score": round(score,4),
                "target_price": round(target_price,2),
                "volume": vol,
                **{f: round(feats[f],6) for f in feature_list if f not in ["open","high","low","close","volume"]}
            })
            print(f"  ✅ Record: score={score:.4f} target={target_price:.2f}\n")
            time.sleep(0.1)  # Throttle each symbol
        time.sleep(SLEEP_SEC)  # Pause after each batch

    df = pd.DataFrame(records)
    print(f"Total records after scan: {len(df)}")
    if not df.empty:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
    else:
        print("❌ No records found. Check universe, model, features, filters.")
    print("\n===== Final Output Table (top 10) =====")
    print(df.head(10))
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ All done! Output: {OUTPUT_CSV}\n")
    return df

if __name__ == "__main__":
    run_scanner()
