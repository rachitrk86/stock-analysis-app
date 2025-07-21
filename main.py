#!/usr/bin/env python3
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time as dtime, timedelta
import zoneinfo
import sqlite3
import pandas as pd
import subprocess
import os
import threading, time
# ─── Constants ────────────────────────────────────────────────
IST = zoneinfo.ZoneInfo("Asia/Kolkata")
CONFIDENCE_THRESHOLD = 0.5
MIN_TARGET_PCT = 0.025
MARKET_OPEN, MARKET_CLOSE = dtime(9,15), dtime(15,30)
AI_SCANNER_OUTPUT = "ai_scanner_output.csv"
HISTORY_DB = "history.db"

# ─── CSS Styling ──────────────────────────────────────────────
st.set_page_config(
    page_title="Swing-Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
[data-testid="stAppViewContainer"], .block-container {
    background-color: #0a1e28 !important;
    color: #cce7e8 !important;
    font-size: 0.85rem !important;
}
[data-testid="stSidebar"], .right-panel {
    background-color: #071a2b !important;
    color: #cce7e8 !important;
}
.widget-card {
    background-color: #073541;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.circle-chart {
    width: 80px; height: 80px; border-radius: 50%;
    border: 6px solid #4dd0e1;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto; font-size: 1.6em; color: #e0f7fa;
}
.stTable table {background-color: #072a3b !important; color: #cce7e8 !important; border-color: #224458 !important;}
.stTable th, .stTable td {padding: 0.5rem 0.75rem;}
button[kind="primary"], .stButton>button {
    background-color: #005f6b !important; color: #e0f7fa !important; border-radius: 6px !important;
}
button[kind="primary"]:hover, .stButton>button:hover {background-color: #00838f !important;}
h1,h2,h3,h4,h5,h6,p,label {color: #e0f7fa !important;}
</style>
""", unsafe_allow_html=True)

# ─── Autorefresh ──────────────────────────────────────────────
st_autorefresh(interval=300_000, key="refresh")  # 5 min

# ─── Load History DB for Overall Hit% ────────────────────────
conn = sqlite3.connect(HISTORY_DB, check_same_thread=False)
c    = conn.cursor()

# ─── Helper to get overall hit rate ──────────────────────────
def get_hit_rate():
    try:
        hits  = c.execute("SELECT COUNT(*) FROM history WHERE target_hit='Hit'").fetchone()[0]
        total = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        return (hits / total * 100) if total else 0.0
    except:
        return 0.0

# ─── Run scanner.py live, ONLY during market hours ───────────
def run_scanner_now():
    with st.spinner("Running AI Scanner for live picks..."):
        result = subprocess.run(
            ["python", "scanner.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            st.info("AI scanner refreshed with live data!")
        else:
            st.error("Scanner failed! See console for details.")
            st.code(result.stdout + "\n" + result.stderr)

def auto_run_scanner():
    IST = zoneinfo.ZoneInfo("Asia/Kolkata")
    while True:
        now = datetime.now(IST).time()
        if dtime(9,15) <= now <= dtime(15,30):
            os.system("python scanner.py")
        time.sleep(300)  # 5 min

# Launch in background (unsafe on Streamlit Cloud!)
if "scanner_thread_started" not in st.session_state:
    t = threading.Thread(target=auto_run_scanner, daemon=True)
    t.start()
    st.session_state.scanner_thread_started = True

# ─── Retrain Model Button ────────────────────────────────────
def retrain_model():
    st.info("⏳ Retraining AI model, please wait (1-2 mins)...")
    result = subprocess.run(
        ["python", "retrain_model_pipeline.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        st.success("✅ Model retrained and scanner re-run! Reloading picks...")
    else:
        st.error("❌ Retrain failed! Check console logs.")
        st.code(result.stdout + "\n" + result.stderr)

# ─── App Header & Controls ───────────────────────────────────
now_dt   = datetime.now(IST)
now_time = now_dt.time()
st.title("🔥 AI-Powered Swing-Trading Dashboard")
st.markdown(f"**Last refresh:** {now_dt.strftime('%Y-%m-%d %H:%M:%S')} IST")

# Sidebar: Dev override
force_open = st.sidebar.checkbox("🛠️ Force Market Open", value=False)
is_open    = force_open or (MARKET_OPEN <= now_time <= MARKET_CLOSE)

# Retrain Button (top right)
with st.sidebar:
    st.markdown("## 🤖 AI Model Control")
    if st.button("🔁 Retrain Model (Full Pipeline)"):
        retrain_model()

# ─── Main Logic: Scanner auto-refresh during open market ────
if is_open:
    run_scanner_now()

# ─── Layout: Main + Right Panel ─────────────────────────────
col_main, col_side = st.columns([3, 1])

with col_side:
    rate = get_hit_rate()
    st.markdown(f"""
    <div class="widget-card">
      <h4>Overall Hit %</h4>
      <div class="circle-chart">{rate:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col_main:
    # ─── Load Scanner Output ────────────────────────────────
    if not os.path.exists(AI_SCANNER_OUTPUT):
        st.warning("No scanner output found. Please run the scanner or retrain pipeline.")
        df_all = pd.DataFrame()
    else:
        df_all = pd.read_csv(AI_SCANNER_OUTPUT)
    st.write(f"🔍 Loaded: {df_all.shape[0]} picks", df_all.head(3))

    # ─── Filtering ─────────────────────────────────────────
    if not df_all.empty:
        # 1. AI score filter
        df_all = df_all[df_all["score"] >= CONFIDENCE_THRESHOLD]
        st.write(f"➡️ After score filter: {len(df_all)}")

        # 2. Target price hurdle (2%+ expected)
        df_all = df_all[(df_all["target_price"] / df_all["price"] - 1) >= MIN_TARGET_PCT]
        st.write(f"➡️ After target ≥ 2%: {len(df_all)}")

        # 3. Top 5 picks by score
        df_top5 = df_all.nlargest(5, "score").copy()

        # 4. Action logic (hold/sell)
        picks = []
        for _, row in df_top5.iterrows():
            entry = row["price"]
            ltp   = row["price"]    # (Optional: Replace with fresh live price if desired)
            stop_level   = entry * 0.99
            profit_level = row["target_price"]
            if ltp <= stop_level:
                action = "Sell"
            elif ltp >= profit_level:
                action = "Sell"
            else:
                action = "Hold"
            picks.append({
                "Symbol":        row["symbol"],
                "Entry Price":   round(entry,2),
                "LTP":           round(ltp,2),
                "% Change":      0.00,
                "AI Score":      round(row["score"],4),
                "Stop @":        round(stop_level,2),
                "Target Price":  round(profit_level,2),
                "Action":        action
            })
        df_picks = pd.DataFrame(picks)

        # Color logic
        def style_row(r):
            if r["Action"]=="Hold":
                return ["background-color:#144d14;color:#fff"]*len(r)
            else:
                return ["background-color:#4d1414;color:#fff"]*len(r)

        st.header("Today's Top 5 Picks (AI, Threshold ≥ 30%)")
        st.dataframe(df_picks.style.apply(style_row, axis=1), use_container_width=True)
    else:
        if is_open:
            st.warning("No picks to show for current market session. Try retraining the model or check scanner debug logs.")
        else:
            st.info("Market is CLOSED. Last picks shown below:")

    # ─── History Section ──────────────────────────────────
    st.header("📜 History of Past Picks (last 20)")
    try:
        rows = c.execute("""
            SELECT symbol, picked_at, entry_price, dropped_at, exit_price, target_price, target_hit, pct_change
            FROM history ORDER BY id DESC LIMIT 20
        """).fetchall()
        if rows:
            hist_df = pd.DataFrame(rows, columns=[
                "Symbol","Picked At","Entry Price","Dropped On",
                "Exit Price","Target Price","Hit/Miss","% Change"
            ])
            def hist_style(r):
                return ["background-color:#144d14;color:#fff"]*len(r) if r["% Change"]>=0 else ["background-color:#4d1414;color:#fff"]*len(r)
            st.dataframe(hist_df.style.apply(hist_style, axis=1), use_container_width=True)
            # Download option
            csv = hist_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Full History as CSV", data=csv,
                               file_name="swing_history.csv", mime="text/csv")
        else:
            st.info("No pick history yet.")
    except Exception as ex:
        st.info("History DB not found or empty.")

# End of script
