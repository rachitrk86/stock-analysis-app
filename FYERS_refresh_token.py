import requests
import json
import os

def refresh_access_token():
    with open("fyers_token.json") as f:
        tokens = json.load(f)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("No refresh token found. Please authenticate manually first.")
        return

    client_id = os.getenv("FYERS_APP_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    url = "https://api.fyers.in/api/v3/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "secret_key": secret_key,
        "refresh_token": refresh_token
    }
    resp = requests.post(url, data=payload).json()
    if resp.get("s") == "ok":
        print("New access token:", resp["access_token"])
        tokens["access_token"] = resp["access_token"]
        # Optionally, update refresh_token if provided
        if "refresh_token" in resp:
            tokens["refresh_token"] = resp["refresh_token"]
        with open("fyers_token.json", "w") as f:
            json.dump(tokens, f)
        print("✅ Refreshed and saved new token.")
    else:
        print("Failed to refresh token:", resp)

refresh_access_token()
