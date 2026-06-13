import requests
import json
import streamlit as st
import os
import datetime as dt

# ── [전역 보안키 자동 정화 엔진] 대소문자 및 접두사 구분 없이 보안키 자동 수색 및 유니코드 공백 원천 박멸 ──
try:
    raw_key = ""
    raw_secret = ""
    
    # 1. secrets 전체에서 APP KEY와 SECRET 관련 키를 대소문자 구분 없이 자동 역추적
    for k in st.secrets.keys():
        k_upper = k.upper()
        if "KEY" in k_upper and "APP" in k_upper:
            raw_key = st.secrets[k]
        if "SECRET" in k_upper and "APP" in k_upper:
            raw_secret = st.secrets[k]
            
    # 2. 검출되지 않았을 경우 백업 명칭으로 조회
    if not raw_key:
        raw_key = st.secrets.get("KIS_APP_KEY") or st.secrets.get("APP_KEY", "")
    if not raw_secret:
        raw_secret = st.secrets.get("KIS_APP_SECRET") or st.secrets.get("APP_SECRET", "")
        
    # 3. [중요] 비ASCII 특수문자 및 한글 더미 데이터 정화 (latin-1 에러 차단)
    # 영문, 숫자, 키보드 기호(ASCII 128 미만)만 필터링하고 공백을 제거합니다.
    APP_KEY = "".join(c for c in str(raw_key) if ord(c) < 128).strip()
    APP_SECRET = "".join(c for c in str(raw_secret) if ord(c) < 128).strip()
    
    # 4. 계좌번호 로드
    ACCOUNT_NO = st.secrets.get("ACCOUNT_NO") or st.secrets.get("KIS_ACCOUNT_NO", "44521662")
    
except Exception as e:
    # 로컬 수동 테스트용 디폴트 백업
    APP_KEY = "여기에_APP_KEY"
    APP_SECRET = "여기에_APP_SECRET"
    ACCOUNT_NO = "44521662"

BASE_URL = "https://openapi.koreainvestment.com:9443"


def get_access_token():
    token_file = "kis_token_cache.json"
    
    # 1. 로컬 캐시 파일이 존재하고 유효한지 먼저 검사
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                cache = json.load(f)
            expire_time = dt.datetime.fromisoformat(cache["expire_time"])
            if dt.datetime.now() < expire_time:
                return cache["access_token"]
        except:
            pass  # 캐시 파일 손상 시 무시하고 신규 발급 진행
    
    # 2. 자가 치유 엔진 가동 (대소문자/접두사 무관 역추적)
    app_key = ""
    app_secret = ""
    for k in st.secrets.keys():
        k_upper = k.upper()
        if "KEY" in k_upper and "APP" in k_upper:
            app_key = st.secrets[k]
        if "SECRET" in k_upper and "APP" in k_upper:
            app_secret = st.secrets[k]
            
    if not app_key:
        app_key = st.secrets.get("KIS_APP_KEY") or st.secrets.get("APP_KEY", "")
    if not app_secret:
        app_secret = st.secrets.get("KIS_APP_SECRET") or st.secrets.get("APP_SECRET", "")
        
    # 3. 유니코드 투명 공백 및 한글 더미 차단을 위한 2차 살균 정화
    app_key = "".join(c for c in str(app_key) if ord(c) < 128).strip()
    app_secret = "".join(c for c in str(app_secret) if ord(c) < 128).strip()
                
    if not app_key or not app_secret:
        raise Exception(f"대시보드 Secrets 설정에서 APP_KEY 또는 APP_SECRET을 찾을 수 없습니다. (현재 감지된 보안키 목록: {list(st.secrets.keys())})")
        
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    url = f"{BASE_URL}/oauth2/tokenP"
    res = requests.post(url, headers=headers, json=body)
    data = res.json()
    
    if "access_token" in data:
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        expire_time = dt.datetime.now() + dt.timedelta(seconds=expires_in - 3600)
        
        try:
            with open(token_file, "w") as f:
                json.dump({
                    "access_token": token,
                    "expire_time": expire_time.isoformat()
                }, f)
        except:
            pass
        return token
    else:
        err_msg = data.get("error_description", "한투 토큰 발급 실패")
        raise Exception(f"KIS Token Error: {err_msg}")


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


def get_foreign_institution_trade(token, div_cls="0", market="J"):
    """투자자별 순매수 상위 종목 조회
    div_cls: "0" = 외국인, "1" = 기관, "2" = 개인
    TR: FHKST01700000
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor-trend-estimate"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01700000"
    }
    # div_cls 매핑: "0"=외국인, "1"=기관, "2"=개인
    div_map = {"0": "1", "1": "2", "2": "3"}
    params = {
        "FID_COND_MRKT_DIV_CODE": market,
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",
        "FID_DIV_CLS_CODE": div_map.get(div_cls, "1"),
        "FID_BLNG_CLS_CODE": "0",
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "0000000000",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_DATE_1": ""
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        print(f"[KIS 수급 TR응답] rt_cd={data.get('rt_cd')} msg={data.get('msg1')} output수={len(data.get('output', []))}")
        if data.get("rt_cd") == "0" and data.get("output"):
            # 필드명 정규화
            normalized = []
            for item in data.get("output", []):
                name = item.get("hts_kor_isnm") or item.get("stck_shrn_iscd", "")
                qty = (item.get("frgn_ntby_qty")
                       or item.get("orgn_ntby_qty")
                       or item.get("prsn_ntby_qty")
                       or item.get("ntby_qty", "0"))
                if name:
                    normalized.append({
                        "hts_kor_isnm": name,
                        "frgn_ntby_qty": qty
                    })
            data["output"] = normalized
            return data
    except Exception as e:
        print(f"[KIS 수급 오류] {e}")

    return {"rt_cd": "9", "msg1": "KIS 수급 API 호출 실패", "output": []}


# ── 카카오톡 나에게 보내기 ──

def refresh_kakao_token():
    """Refresh Token으로 Access Token 갱신"""
    try:
        client_id = st.secrets["KAKAO_CLIENT_ID"]
        client_secret = st.secrets["KAKAO_CLIENT_SECRET"]
        refresh_token = st.secrets["KAKAO_REFRESH_TOKEN"]
    except:
        return None

    res = requests.post("https://kauth.kakao.com/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    })
    data = res.json()
    return data.get("access_token")


def send_kakao_message(message: str) -> dict:
    """나에게 카카오톡 메시지 보내기 (Access Token 만료 시 자동 갱신)"""
    try:
        access_token = st.secrets["KAKAO_ACCESS_TOKEN"]
    except:
        return {"error": "KAKAO_ACCESS_TOKEN not found in secrets"}

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://quant-trading-app-gdvn3rpskejdaihwjjjqzf.streamlit.app",
                "mobile_web_url": "https://quant-trading-app-gdvn3rpskejdaihwjjjqzf.streamlit.app"
            }
        }, ensure_ascii=False)
    }

    res = requests.post(url, headers=headers, data=data)
    result = res.json()

    # Access Token 만료 시 refresh 후 재시도
    if result.get("code") == -401:
        new_token = refresh_kakao_token()
        if new_token:
            headers["Authorization"] = f"Bearer {new_token}"
            res = requests.post(url, headers=headers, data=data)
            result = res.json()

    return result


def get_stock_investor(ticker, token, market="J"):
    """종목별 외국인/기관 순매수 현황 조회
    TR: FHKST01010900 (주식현재가 투자자)
    ※ 당일 데이터는 장 종료 후 제공됨 (장중에는 전일 데이터)
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010900"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": market,
        "FID_INPUT_ISCD": ticker
    }
    res = requests.get(url, headers=headers, params=params)
    return res.json()