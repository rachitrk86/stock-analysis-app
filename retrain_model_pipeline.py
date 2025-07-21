#!/usr/bin/env python3
"""
retrain_model_pipeline.py

Runs the full retrain pipeline:
1. Append today's bar
2. Feature engineering
3. Label data
4. Train model
5. Run scanner to update picks (ai_scanner_output.csv)
"""

import subprocess
import sys

def run_step(label, cmd):
    print(f"\n==== {label} ====")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Step FAILED: {label}")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_step("Step 1: Append Today's Bar", "python append_today_bar.py")
    run_step("Step 2: Feature Engineering", "python feature_engineering.py")
    run_step("Step 3: Label Data", "python label_data.py")
    run_step("Step 4: Train Model", "python train_model.py")
    run_step("Step 5: Run Scanner", "python scanner.py")
    print("\n✅ Full retrain pipeline complete! Picks ready in ai_scanner_output.csv")
