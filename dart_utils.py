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
def get_dart_roe(stock_code, year=2024):
    api_key = st.secrets.get("DART_API_KEY", "")
    if not api_key:
        return None

    corp_map = get_corp_code_map()
    corp_code = corp_map.get(stock_code)
    if not corp_code:
        return None

    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    for fs_div in ["CFS", "OFS"]:
        try:
            params = {
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": str(year),
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

            if net_income and total_equity and total_equity != 0:
                roe = round(net_income / total_equity * 100, 2)
                return roe
        except:
            continue

    return None
