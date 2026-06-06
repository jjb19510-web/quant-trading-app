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
def get_balance(token):
    """계좌 잔고 조회"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC8434R"
    }
    params = {
        "CANO": ACCOUNT_NO,
        "ACNT_PRDT_CD": "01",
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(url, headers=headers, params=params)
    return res.json()


def buy_order(ticker, qty, token):
    """시장가 매수 주문"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC0802U"
    }
    body = {
        "CANO": ACCOUNT_NO,
        "ACNT_PRDT_CD": "01",
        "PDNO": ticker,
        "ORD_DVSN": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0"
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    return res.json()


def sell_order(ticker, qty, token):
    """시장가 매도 주문"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC0801U"
    }
    body = {
        "CANO": ACCOUNT_NO,
        "ACNT_PRDT_CD": "01",
        "PDNO": ticker,
        "ORD_DVSN": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0"
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    return res.json()

def get_foreign_institution_trade(token, market="J"):
    """외국인/기관 매매종목 가집계"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPTJ04400000"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": market,
        "FID_COND_SCR_DIV_CODE": "16449",
        "FID_INPUT_ISCD": "0001",
        "FID_DIV_CLS_CODE": "0",
        "FID_RANK_SORT_CLS_CODE": "0",
        "FID_ETC_CLS_CODE": "0"
    }
    res = requests.get(url, headers=headers, params=params)
    return res.json()