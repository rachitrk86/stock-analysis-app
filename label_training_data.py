#!/usr/bin/env python3
"""
label_training_data.py

Loads your daily bars with features,
labels each row as "profitable swing trade" (1) or not (0)
using a rolling lookahead window, and saves for AI training.
"""

import pandas as pd
from datetime import timedelta

# PARAMETERS — adjust as per your strategy!
PROFIT_TARGET = 0.03    # +3% profit
STOP_LOSS     = 0.01    # -1% loss
HORIZON_DAYS  = 3       # Max holding period

INPUT_CSV = "nse_daily_features.csv"
OUTPUT_CSV    = "training_data_labeled.csv"

def label_swing_trades(df, profit_target=PROFIT_TARGET, stop_loss=STOP_LOSS, horizon=HORIZON_DAYS):
    # Ensure proper sorting by symbol and date/timestamp
    df = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    df["label"] = 0  # Default to not hit
    symbols = df["symbol"].unique()
    for symbol in symbols:
        sub = df[df["symbol"] == symbol].reset_index()
        closes = sub["close"].values
        for i in range(len(sub) - horizon):
            entry = closes[i]
            max_close = max(closes[i+1:i+1+horizon])
            min_close = min(closes[i+1:i+1+horizon])
            # Did it hit profit first?
            if (max_close - entry) / entry >= profit_target:
                df.loc[sub.loc[i, "index"], "label"] = 1
            # Optionally: can handle stop-loss first logic here if you want!
            # elif (min_close - entry) / entry <= -stop_loss:
            #     df.loc[sub.loc[i, "index"], "label"] = 0
            else:
                df.loc[sub.loc[i, "index"], "label"] = 0
    return df

if __name__ == "__main__":
    print(f"Loading: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # If your timestamp is not in datetime, convert
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    elif "date" in df.columns:
        df["timestamp"] = pd.to_datetime(df["date"])

    print(f"Labeling {len(df)} rows...")
    df_labeled = label_swing_trades(df)
    print("Label distribution:", df_labeled["label"].value_counts(normalize=True))

    # Save to file
    df_labeled.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved labeled training data to {OUTPUT_CSV}")
