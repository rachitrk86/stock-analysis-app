#!/usr/bin/env python3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import joblib

# ─── Load Data ───────────────────────────────────────────────────────
print("Loading: training_data_labeled.csv")
df = pd.read_csv("training_data_labeled.csv")

# ─── Define Feature Columns ──────────────────────────────────────────
feature_cols = [
    "open", "high", "low", "close", "volume",
    "EMA5", "EMA20", "EMA_diff", "RSI14", "MACD", "MACD_sig", "MACD_hist",
    "BB_%B", "BB_bandwidth", "ATR14", "OBV"
]
feature_cols = [f for f in feature_cols if f in df.columns]

# ─── Impute missing values (Median for each feature) ─────────────────
df[feature_cols] = df[feature_cols].fillna(df[feature_cols].median())

# (Optional: also drop any remaining rows with NaN label)
df = df.dropna(subset=["label"])

print(f"Using features: {feature_cols}")
# ─── Prepare Train/Test Sets ─────────────────────────────────────────
X = df[feature_cols]
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, shuffle=True  # set shuffle=False for pure time-series
)

print(f"Train: {X_train.shape}, Test: {X_test.shape}")

# ─── Train Model ─────────────────────────────────────────────────────
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    n_jobs=-1,
    random_state=42
)
model.fit(X_train, y_train)

# ─── Evaluation ──────────────────────────────────────────────────────
probs = model.predict_proba(X_test)[:,1]
preds = model.predict(X_test)
roc = roc_auc_score(y_test, probs)
acc = accuracy_score(y_test, preds)
cm  = confusion_matrix(y_test, preds)

print("\nTest ROC AUC: ", round(roc, 4))
print("Test Accuracy:", round(acc, 4))
print("Label ratio in test:", np.mean(y_test))
print("Confusion Matrix:\n", cm)
print(classification_report(y_test, preds, digits=3))

# ─── Feature Importances ─────────────────────────────────────────────
fi = pd.Series(model.feature_importances_, index=feature_cols)
fi = fi.sort_values(ascending=False)
print("\nTop Feature Importances:")
print(fi)

# ─── Save Model and Features ─────────────────────────────────────────
joblib.dump((model, feature_cols), "models/ai_model.pkl")
print("✅ Model and feature list saved to models/ai_model.pkl")

# (optional) Save feature importances for your dashboard
fi.to_csv("feature_importances.csv")
print("✅ Feature importances saved to feature_importances.csv")
