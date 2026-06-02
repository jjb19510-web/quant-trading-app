import streamlit as st
import requests
import io
import zipfile
import xml.etree.ElementTree as ET

@st.cache_data(ttl=86400)
def get_corp_code_map():
    api_key = st.secrets.get("DART_API_KEY", "")
    if not api_key:
        return {}
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    try:
        res = requests.get(url, timeout=15)
        zf = zipfile.ZipFile(io.BytesIO(res.content))
        xml_data = zf.read(zf.namelist()[0])
        root = ET.fromstring(xml_data)
        mapping = {}
        for company in root.iter("list"):
            stock_code = company.findtext("stock_code", "").strip()
            corp_code = company.findtext("corp_code", "").strip()
            if stock_code and corp_code:
                mapping[stock_code] = corp_code
        return mapping
    except:
        return {}


@st.cache_data(ttl=3600)
def get_dart_financial_raw(stock_code, year=2025):
    """최신 연도(2025)부터 조회하여 자본총계와 당기순이익을 역순 수집합니다."""
    api_key = st.secrets.get("DART_API_KEY", "")
    if not api_key:
        return None, None

    corp_map = get_corp_code_map()
    corp_code = corp_map.get(stock_code)
    if not corp_code:
        return None, None

    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    
    # 2025년 데이터가 아직 없거나 불러올 수 없는 경우 2024년으로 자동 후퇴합니다.
    for y in [year, year - 1]:
        for fs_div in ["CFS", "OFS"]:
            try:
                params = {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(y),
                    "reprt_code": "11011",
                    "fs_div": fs_div,
                }
                res = requests.get(url, params=params, timeout=15)
                data = res.json()
                if data.get("status") != "000":
                    continue

                items = data.get("list", [])

                def find_amount(keyword):
                    for item in items:
                        if keyword in item.get("account_nm", ""):
                            val = item.get("thstrm_amount", "").replace(",", "").strip()
                            try:
                                return float(val)
                            except:
                                return None
                    return None

                net_income = find_amount("당기순이익")
                total_equity = find_amount("자본총계")

                if net_income is not None or total_equity is not None:
                    return net_income, total_equity
            except:
                continue

    return None, None


@st.cache_data(ttl=3600)
def get_dart_roe(stock_code, year=2025):
    net_income, total_equity = get_dart_financial_raw(stock_code, year)
    if net_income and total_equity and total_equity != 0:
        return round(net_income / total_equity * 100, 2)
    return None


@st.cache_data(ttl=3600)
def get_dart_stock_count(stock_code, year=2025):
    """최신 연도(2025) 및 직전 연도(2024) 기준으로 발행주식수를 안전하게 호출합니다."""
    api_key = st.secrets.get("DART_API_KEY", "")
    if not api_key:
        return None

    corp_map = get_corp_code_map()
    corp_code = corp_map.get(stock_code)
    if not corp_code:
        return None

    url = "https://opendart.fss.or.kr/api/stockTotqySttus.json"
    
    # 2025년 우선 조회 후 없으면 2024년 순으로 탐색
    for y in [year, year - 1]:
        try:
            params = {
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": str(y),
                "reprt_code": "11011",
            }
            res = requests.get(url, params=params, timeout=15)
            data = res.json()
            if data.get("status") != "000":
                continue

            items = data.get("list", [])
            for item in items:
                if "보통주" in item.get("se", ""):
                    val = item.get("istc_totqy", "").replace(",", "").strip()
                    try: return float(val)
                    except: pass
            for item in items:
                if "합계" in item.get("se", ""):
                    val = item.get("istc_totqy", "").replace(",", "").strip()
                    try: return float(val)
                    except: pass
        except:
            continue
    return None


@st.cache_data(ttl=3600)
def get_dart_per_pbr(stock_code, current_price, year=2025):
    if not current_price or current_price <= 0:
        return None, None

    net_income, total_equity = get_dart_financial_raw(stock_code, year)
    if net_income is None or total_equity is None:
        return None, None

    shares = get_dart_stock_count(stock_code, year)
    if not shares or shares <= 0:
        return None, None

    eps = net_income / shares
    bps = total_equity / shares

    per = round(current_price / eps, 2) if eps > 0 else None
    pbr = round(current_price / bps, 2) if bps > 0 else None

    return per, pbr