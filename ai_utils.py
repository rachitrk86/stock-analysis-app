# ai_utils.py

import joblib
import pickle

def load_model(path="models/ai_model.pkl"):
    """
    Load your AI model from disk. Supports both joblib and pickle formats,
    and unpacks a tuple if necessary (e.g. (model, vectorizer)).
    """
    try:
        loaded = joblib.load(path)
    except Exception:
        with open(path, "rb") as f:
            loaded = pickle.load(f)

    # If the file contains a tuple, assume the first element is the model
    model = loaded[0] if isinstance(loaded, tuple) else loaded

    # Verify it has the right interface
    if not (hasattr(model, "predict") or hasattr(model, "predict_proba")):
        raise AttributeError(f"Loaded object has no predict methods: {type(model)}")

    return model


def extract_features(quote, history_df, sector_strength):
    """
    Build exactly the features your model expects. Assumes history_df
    is a minute-bar DataFrame indexed by timestamp, with columns:
      ['open','high','low','close','volume'].

    Returns a dict with keys:
      price, volume, atp,
      atr_pct, price_change_pct, vwap_distance,
      sector_strength
    """
    # Current quote fields
    price = quote.get("price", 0.0)
    volume = quote.get("volume", 0)
    atp = quote.get("atp", 0.0)

    # Compute ATR% over the last 14 bars
    high = history_df["high"]
    low  = history_df["low"]
    close = history_df["close"]
    atr = (high.rolling(14).max() - low.rolling(14).min()) / close.rolling(14).mean() * 100
    atr_pct = float(atr.iloc[-1]) if not atr.empty else 0.0

    # Price change %: (price – previous close) / previous close * 100
    prev_close = history_df["close"].shift(1)
    if not prev_close.empty and prev_close.iloc[-1]:
        price_change_pct = (price - prev_close.iloc[-1]) / prev_close.iloc[-1] * 100
    else:
        price_change_pct = 0.0

    # VWAP distance: (price – VWAP) / VWAP
    # Approximate VWAP as volume-weighted avg price over history_df
    typical_price = (history_df["high"] + history_df["low"] + history_df["close"]) / 3
    vwap = (typical_price * history_df["volume"]).sum() / history_df["volume"].sum() if history_df["volume"].sum() else 0.0
    if vwap:
        vwap_distance = (price - vwap) / vwap
    else:
        vwap_distance = 0.0

    return {
        "price":             price,
        "volume":            volume,
        "atp":               atp,
        "atr_pct":           atr_pct,
        "price_change_pct":  price_change_pct,
        "vwap_distance":     vwap_distance,
        "sector_strength":   sector_strength
    }
