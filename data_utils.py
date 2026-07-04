import json
import os
import streamlit as st
import yfinance as yf
import pandas as pd
import requests

WATCHLIST_FILE = "watchlist.json"
NOTES_FILE = "investment_notes.json"
SECTORS_FILE = "sectors.json"
BACKTEST_FILE = "backtest_results.json"
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return []

def save_watchlist(wl):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(wl, f)

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False)

def load_sectors():
    if os.path.exists(SECTORS_FILE):
        with open(SECTORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sectors(sectors):
    with open(SECTORS_FILE, "w", encoding="utf-8") as f:
        json.dump(sectors, f, ensure_ascii=False)

def load_backtest():
    if os.path.exists(BACKTEST_FILE):
        with open(BACKTEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_backtest(results):
    with open(BACKTEST_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

def init_session_state():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = load_watchlist()
    if "notes" not in st.session_state:
        st.session_state.notes = load_notes()
    if "sectors" not in st.session_state:
        st.session_state.sectors = load_sectors()
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = load_backtest()


@st.cache_data(ttl=600)
def load_market_data(tickers, start_date, end_date, market):
    try:
        ohlc = yf.download(tickers, start=str(start_date), end=str(end_date), progress=False)
        df = ohlc["Close"] if isinstance(ohlc, pd.DataFrame) and "Close" in ohlc else pd.DataFrame()
    except:
        df = pd.DataFrame()
        ohlc = pd.DataFrame()

    if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
        try:
            import FinanceDataReader as fdr
            clean_tickers = [t.replace(".KS", "").replace(".KQ", "") for t in tickers]
            if len(clean_tickers) == 1:
                df_fdr = fdr.DataReader(clean_tickers[0], start_date, end_date)
                if not df_fdr.empty:
                    df = pd.DataFrame({tickers[0]: df_fdr["Close"]})
                    return df, df_fdr["Open"], df_fdr["High"], df_fdr["Low"], df_fdr["Close"], df_fdr["Volume"]
            else:
                dfs = []
                for ct, t in zip(clean_tickers, tickers):
                    temp_df = fdr.DataReader(ct, start_date, end_date)[["Close"]]
                    temp_df.columns = [t]
                    dfs.append(temp_df)
                df = pd.concat(dfs, axis=1).dropna()
                chart_raw = df.columns[0].replace(".KS", "").replace(".KQ", "")
                df_fdr_single = fdr.DataReader(chart_raw, start_date, end_date)
                return df, df_fdr_single["Open"], df_fdr_single["High"], df_fdr_single["Low"], df_fdr_single["Close"], df_fdr_single["Volume"]
        except:
            pass

    if not df.empty:
        chart_col = df.columns[0] if hasattr(df.columns, '__iter__') else tickers[0]
        chart_raw = str(chart_col).replace(".KS", "").replace(".KQ", "")
        try:
            close_p = df[chart_col]
            open_p = ohlc["Open"][chart_col] if "Open" in ohlc else close_p
            high_p = ohlc["High"][chart_col] if "High" in ohlc else close_p
            low_p = ohlc["Low"][chart_col] if "Low" in ohlc else close_p
            volume = ohlc["Volume"][chart_col] if "Volume" in ohlc else pd.Series(dtype=float)
            return df, open_p, high_p, low_p, close_p, volume
        except:
            pass

    return pd.DataFrame(), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    # 2. 야후 파이낸스 실패 및 한국 주식인 경우 자체 초정밀 Naver Sise XML 파서 구동 (강력한 폴백)
    if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
        try:
            import requests
            import re
            from datetime import datetime
            
            # 단일 종목 및 다중 종목 구분을 위한 Naver Sise 개별 다운로더 정의
            def fetch_naver_sise(symbol):
                raw_sym = symbol.replace(".KS", "").replace(".KQ", "")
                try:
                    delta = datetime.combine(end_date, datetime.min.time()) - datetime.combine(start_date, datetime.min.time())
                    count_days = max(delta.days, 100)
                except:
                    count_days = 1000
                
                url = f"https://fchart.stock.naver.com/sise.nhn?symbol={raw_sym}&timeframe=day&count={count_days}&requestType=0"
                try:
                    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    if res.status_code == 200:
                        matches = re.findall(r'<item\s+data="([^"]+)"\s*/>', res.text)
                        records = []
                        for m in matches:
                            parts = m.split('|')
                            if len(parts) >= 6:
                                records.append({
                                    "Date": datetime.strptime(parts[0], "%Y%m%d"),
                                    "Open": float(parts[1]),
                                    "High": float(parts[2]),
                                    "Low": float(parts[3]),
                                    "Close": float(parts[4]),
                                    "Volume": float(parts[5])
                                })
                        if records:
                            temp_df = pd.DataFrame(records).set_index("Date")
                            start_dt = pd.to_datetime(start_date)
                            end_dt = pd.to_datetime(end_date)
                            return temp_df.loc[start_dt:end_dt]
                except:
                    pass
                return pd.DataFrame()

            # 개별 다운로더 실행
            if len(tickers) == 1:
                single_df = fetch_naver_sise(tickers[0])
                if not single_df.empty:
                    df = pd.DataFrame({tickers[0]: single_df["Close"]})
                    open_p = single_df["Open"]
                    high_p = single_df["High"]
                    low_p = single_df["Low"]
                    close_p = single_df["Close"]
                    volume = single_df["Volume"]
                    return df, open_p, high_p, low_p, close_p, volume
            else:
                dfs = []
                for t in tickers:
                    t_df = fetch_naver_sise(t)
                    if not t_df.empty:
                        dfs.append(t_df[["Close"]].rename(columns={"Close": t}))
                if dfs:
                    df = pd.concat(dfs, axis=1).dropna()
                    chart_col = df.columns[0]
                    # 메인 차트 종목의 풀 OHLCV 재다운로드 및 매핑
                    single_df = fetch_naver_sise(chart_col)
                    if not single_df.empty:
                        # 공통 인덱스 동기화
                        single_df = single_df.reindex(df.index).ffill()
                        open_p = single_df["Open"]
                        high_p = single_df["High"]
                        low_p = single_df["Low"]
                        close_p = single_df["Close"]
                        volume = single_df["Volume"]
                        return df, open_p, high_p, low_p, close_p, volume
        except Exception as ex:
            pass

    # 3. 야후 파이낸스 실패 및 한국 주식인 경우 FinanceDataReader 2차 폴백 (기존 유지)
    if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
        try:
            import FinanceDataReader as fdr
            clean_tickers = [t.replace(".KS", "").replace(".KQ", "") for t in tickers]
            if len(clean_tickers) == 1:
                df_fdr = fdr.DataReader(clean_tickers[0], str(start_date), str(end_date))
                if not df_fdr.empty:
                    df = pd.DataFrame({tickers[0]: df_fdr["Close"]})
                    open_p = df_fdr["Open"]
                    high_p = df_fdr["High"]
                    low_p = df_fdr["Low"]
                    close_p = df_fdr["Close"]
                    volume = df_fdr["Volume"]
                    return df, open_p, high_p, low_p, close_p, volume
            else:
                dfs = []
                for ct, t in zip(clean_tickers, tickers):
                    temp_df = fdr.DataReader(ct, str(start_date), str(end_date))[["Close"]]
                    temp_df.columns = [t]
                    dfs.append(temp_df)
                df = pd.concat(dfs, axis=1).dropna()
                chart_col = df.columns[0]
                chart_raw = chart_col.replace(".KS", "").replace(".KQ", "")
                df_fdr_single = fdr.DataReader(chart_raw, str(start_date), str(end_date))
                open_p = df_fdr_single["Open"]
                high_p = df_fdr_single["High"]
                low_p = df_fdr_single["Low"]
                close_p = df_fdr_single["Close"]
                volume = df_fdr_single["Volume"]
                return df, open_p, high_p, low_p, close_p, volume
        except:
            pass

    # 4. 성공적인 데이터 확보 시 규격 매핑 및 Series 추출
    if not df.empty:
        if isinstance(df, pd.Series):
            df = df.to_frame()
        df.columns = [str(c) for c in df.columns]
        chart_col = df.columns[0]
        
        def extract_series(metric):
            try:
                if isinstance(ohlc.columns, pd.MultiIndex):
                    if metric in ohlc.columns.get_level_values(0):
                        series_data = ohlc[metric]
                        if isinstance(series_data, pd.DataFrame):
                            if chart_col in series_data.columns:
                                return series_data[chart_col]
                            return series_data.iloc[:, 0]
                        return series_data
                else:
                    if metric in ohlc.columns:
                        series_data = ohlc[metric]
                        if isinstance(series_data, pd.DataFrame):
                            return series_data.squeeze()
                        return series_data
            except:
                pass
            return pd.Series(dtype='float64')

        open_p = extract_series("Open")
        high_p = extract_series("High")
        low_p = extract_series("Low")
        close_p = extract_series("Close")
        volume = extract_series("Volume")
        
        return df, open_p, high_p, low_p, close_p, volume

    return pd.DataFrame(), pd.Series(), pd.Series(), pd.Series(), pd.Series(), pd.Series()


# ── [실시간 상장사 목록 로드 엔진] ──
# 최신 상장 종목 수동 보완 테이블
MANUAL_STOCK_MAP = {
    "삼양컴텍": ("484590", "KOSPI"),
    "에이피알": ("278470", "KOSPI"),
    "시프트업": ("462870", "KOSPI"),
    "LG CNS": ("064400", "KOSPI"),
    "엘지씨엔에스": ("064400", "KOSPI"),
    "LG씨엔에스": ("064400", "KOSPI"),
}
    
@st.cache_data(ttl=86400)
def load_krx_listing():
    # 1. FinanceDataReader 시도
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        if df is not None and not df.empty:
            manual_rows = []
            for name, (code, market) in MANUAL_STOCK_MAP.items():
                if not (df['Name'].str.upper() == name.upper()).any():
                    manual_rows.append({'Name': name, 'Symbol': code, 'Market': market})
            if manual_rows:
                manual_df = pd.DataFrame(manual_rows)
                df = pd.concat([df, manual_df], ignore_index=True)
            return df
    except:
        pass
    # 2. GitHub CSV 폴백
    try:
        base_df = pd.read_csv("https://raw.githubusercontent.com/corazzon/finance-data-analysis/main/krx.csv")
        manual_rows = [{'Name': n, 'Symbol': c, 'Market': m} for n, (c, m) in MANUAL_STOCK_MAP.items()]
        manual_df = pd.DataFrame(manual_rows)
        return pd.concat([base_df, manual_df], ignore_index=True)
    except:
        pass
    # 3. MANUAL_STOCK_MAP만 반환
    manual_rows = [{'Name': n, 'Symbol': c, 'Market': m} for n, (c, m) in MANUAL_STOCK_MAP.items()]
    return pd.DataFrame(manual_rows)


def search_ticker_by_name(name):
    """네이버 자동완성 API로 종목명 → 코드 변환 (FDR 실패 시 폴백)"""
    try:
        res = requests.get(
            f"https://ac.finance.naver.com/ac?q={name}&q_enc=UTF-8&t_koreng=1&st=111&r_format=json&r_enc=UTF-8&r_adj=0",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=5
        )
        data = res.json()
        items = data.get("items", [[]])[0]
        for item in items:
            if len(item) >= 2:
                code = str(item[1]).zfill(6)
                if code.isdigit() and len(code) == 6:
                    item_name = str(item[0])
                    return code, item_name
    except:
        pass
    return None, None

# ── [상장사 이름 매핑 맵 수집 엔진] ──
@st.cache_data(ttl=86400)
def get_krx_name_map():
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        code_col = next((c for c in ['Symbol', 'Code'] if c in df.columns), None)
        name_col = next((c for c in ['Name'] if c in df.columns), None)
        if code_col and name_col:
            return dict(zip(df[code_col].astype(str).str.split('.').str[0].str.zfill(6), df[name_col]))
    except:
        pass
    return {}