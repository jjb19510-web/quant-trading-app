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


# ── [고성능 캐싱 기반 듀얼 주가 수집 엔진] ──
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
                    open_p = df_fdr["Open"]
                    high_p = df_fdr["High"]
                    low_p = df_fdr["Low"]
                    close_p = df_fdr["Close"]
                    volume = df_fdr["Volume"]
                    return df, open_p, high_p, low_p, close_p, volume
            else:
                dfs = []
                for ct, t in zip(clean_tickers, tickers):
                    temp_df = fdr.DataReader(ct, start_date, end_date)[["Close"]]
                    temp_df.columns = [t]
                    dfs.append(temp_df)
                df = pd.concat(dfs, axis=1).dropna()
                chart_col = df.columns[0]
                chart_raw = chart_col.replace(".KS", "").replace(".KQ", "")
                df_fdr_single = fdr.DataReader(chart_raw, start_date, end_date)
                open_p = df_fdr_single["Open"]
                high_p = df_fdr_single["High"]
                low_p = df_fdr_single["Low"]
                close_p = df_fdr_single["Close"]
                volume = df_fdr_single["Volume"]
                return df, open_p, high_p, low_p, close_p, volume
        except:
            pass

    if not df.empty:
        df.columns = [str(c) for c in df.columns]
        chart_col = df.columns[0]
        if len(tickers) == 1:
            open_p = ohlc["Open"].squeeze() if "Open" in ohlc else pd.Series()
            high_p = ohlc["High"].squeeze() if "High" in ohlc else pd.Series()
            low_p = ohlc["Low"].squeeze() if "Low" in ohlc else pd.Series()
            close_p = ohlc["Close"].squeeze() if "Close" in ohlc else pd.Series()
            volume = ohlc["Volume"].squeeze() if "Volume" in ohlc else pd.Series()
        else:
            open_p = ohlc["Open"][chart_col] if isinstance(ohlc["Open"], pd.DataFrame) else ohlc["Open"]
            high_p = ohlc["High"][chart_col] if isinstance(ohlc["High"], pd.DataFrame) else ohlc["High"]
            low_p = ohlc["Low"][chart_col] if isinstance(ohlc["Low"], pd.DataFrame) else ohlc["Low"]
            close_p = df[chart_col]
            volume = ohlc["Volume"][chart_col] if isinstance(ohlc["Volume"], pd.DataFrame) else ohlc["Volume"]
        return df, open_p, high_p, low_p, close_p, volume

    return pd.DataFrame(), pd.Series(), pd.Series(), pd.Series(), pd.Series(), pd.Series()


# ── [실시간 상장사 목록 로드 엔진] ──
@st.cache_data(ttl=86400)
def load_krx_listing():
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        if df is not None and not df.empty:
            return df
    except:
        pass
    try:
        return pd.read_csv("https://raw.githubusercontent.com/corazzon/finance-data-analysis/main/krx.csv")
    except:
        return None


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