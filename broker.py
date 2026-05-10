import requests
import json
import streamlit as st

# ── 환경변수에서 인증 정보 읽기 ──
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACCOUNT_NO = st.secrets["ACCOUNT_NO"]
except:
    # 로컬 테스트용
    APP_KEY = "여기에_APP_KEY"
    APP_SECRET = "여기에_APP_SECRET"
    ACCOUNT_NO = "44521662"

BASE_URL = "https://openapi.koreainvestment.com:9443"


def get_access_token():
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    return res.json()["access_token"]


def get_current_price(ticker, token):
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker
    }
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    if data.get("rt_cd") == "0":
        output = data["output"]
        return {
            "current": int(output["stck_prpr"]),
            "change": int(output["prdy_vrss"]),
            "change_pct": float(output["prdy_ctrt"]),
            "volume": int(output["acml_vol"])
        }
    return None