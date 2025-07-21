import sys, os
# Ensure the 'src' folder is on Python's import path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import json
import logging
import webbrowser
from fyers_apiv3 import fyersModel

# ——— CONFIG ———
APP_ID       = os.getenv("FYERS_APP_ID",       "1STQ57NNRI-100")
SECRET_KEY   = os.getenv("FYERS_SECRET_KEY",   "HNVJE2C9WU")
REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI", "https://google.com")  # must exactly match your FYERS app
TOKEN_FILE   = os.getenv("FYERS_TOKEN_FILE",   "fyers_token.json")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_fyers_client = None  # singleton placeholder

def _load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("access_token")
    return None

def _save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": token}, f)
    logger.info(f"Saved token to {TOKEN_FILE}")

def _authenticate():
    session = fyersModel.SessionModel(
        client_id    = APP_ID,
        secret_key   = SECRET_KEY,
        redirect_uri = REDIRECT_URI,
        response_type= "code",
        grant_type   = "authorization_code",
        state        = "state123"
    )
    auth_url = session.generate_authcode()
    print("\n▶ Open this URL in your browser:\n", auth_url, "\n")
    webbrowser.open(auth_url, new=1)
    code = input("Paste the auth_code here: ").strip()
    session.set_token(code)
    resp = session.generate_token()
    if "access_token" not in resp:
        raise RuntimeError(f"Auth failed: {resp}")
    token = resp["access_token"]
    _save_token(token)
    return token

def get_fyers_client():
    """
    Returns a singleton FyersModel instance, prompting for auth only once.
    """
    global _fyers_client
    if _fyers_client:
        return _fyers_client

    token = _load_token() or _authenticate()
    _fyers_client = fyersModel.FyersModel(
        client_id = APP_ID,
        token     = token,
        log_path  = ".",
        is_async  = False
    )
    logger.info("✅ FYERS client initialized")
    return _fyers_client
