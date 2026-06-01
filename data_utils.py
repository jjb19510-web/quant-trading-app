import json
import os
import streamlit as st

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
