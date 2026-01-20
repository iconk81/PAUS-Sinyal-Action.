import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
from datetime import datetime
import pytz

# --- KONFIGURASI TELEGRAM ---
TOKEN = st.secrets["telegram"]["token"]
CHAT_ID = st.secrets["telegram"]["chat_id"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Gagal kirim Telegram: {e}")

# --- KONEKSI GOOGLE SHEETS ---
# UPDATE: Versi dirubah ke v3.4 sesuai permintaan
st.set_page_config(page_title="PAUS Action Monitor v3.4", layout="wide")
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    ss = client.open("SINYAL SAHAM")
    sheet = ss.worksheet("SUMMARY")
    
    # Mencoba mengambil data Profit Summary dari GSheet (jika ada)
    try:
        sheet_profit = ss.worksheet("PROFIT_SUMMARY")
    except:
        sheet_profit = None
except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
    st.stop()

def highlight_style(row):
    target_col = next((col for col in row.index if col.lower() == 'action'), None)
    ticker_col = next((col for col in row.index if col.lower() == 'ticker'), None)
    styles = [''] * len(row)
    if target_col:
        status = str(row[target_col]).upper()
        idx_action = row.index.get_loc(target_col)
        idx_ticker = row.index.get_loc(ticker_col) if ticker_col else -1
        if status in ['ENTRY', 'OPEN']:
            color = 'background-color: #90EE90; color: black; font-weight: bold'
            styles[idx_action] = color
            if idx_ticker != -1: styles[idx_ticker] = color
        elif status == 'EXIT':
            color = 'background-color: #FF4500; color: white; font-weight: bold'
            styles[idx_action] = color
            if idx_ticker != -1: styles[idx_ticker] = color
    return styles

# Judul Dashboard v3.4
st.title("🐋 PAUS Action Monitor v3.4")

# --- FITUR BARU: TABEL PERBANDINGAN PROFIT (DARI GSHEET) ---
st.subheader("📊 Strategi Comparison (Manual vs yFinance)")
if sheet_profit:
    try:
        p_data = sheet_profit.get_all_records()
        if p_data:
            st.table(pd.DataFrame(p_data))
        else:
            st.info("Data profit belum tersedia di GSheet.")
    except:
        st.warning("Gagal memproses data PROFIT_SUMMARY.")
else:
    st.info("Silakan buat Tab baru 'PROFIT_SUMMARY' di Google Sheets 'SINYAL SAHAM' Anda.")

st.divider()

if "last_row_count" not in st.session_state:
    try:
        all_vals = sheet.get_all_values()
        st.session_state.last_row_count = len(all_vals)
    except:
        st.session_state.last_row_count = 0

placeholder = st.empty()

while True:
    try:
        all_values = sheet.get_all_values()
        header = all_values[0]
        data_rows = all_values[-1000:] if len(all_values) > 1000 else all_values[1:]
        df = pd.DataFrame(data_rows, columns=header)
        current_total_rows = len(all_values)
        
        target_col = next((col for col in df.columns if col.lower() == 'action'), None)
        time_col = next((col for col in df.columns if col.lower() == 'timestamp'), None)
        wita_tz = pytz.timezone('Asia/Makassar')
        today_date = datetime.now(wita_tz).strftime("%Y-%m-%d")

        with placeholder.container():
            if target_col:
                st.subheader(f"📅 Summary Hari Ini ({today_date})")
                today_df = df[df[time_col].astype(str).str.contains(today_date)] if time_col else df
                total_entry = len(today_df[today_df[target_col].str.upper().isin(['ENTRY', 'OPEN'])])
                total_exit = len(today_df[today_df[target_col].str.upper() == 'EXIT'])

                c1, c2 = st.columns(2)
                c1.metric("Total ENTRY/OPEN Hari Ini", f"{total_entry}")
                c2.metric("Total EXIT Hari Ini", f"{total_exit}")
                
                st.divider()
                st.subheader("📊 Live Trading Dashboard (Last 20)")
                styled_df = df.tail(20).style.apply(highlight_style, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                if current_total_rows > st.session_state.last_row_count:
                    diff = current_total_rows - st.session_state.last_row_count
                    for _, row in df.tail(diff).iterrows():
                        status_aksi = str(row[target_col]).upper()
                        if status_aksi in ['ENTRY', 'EXIT', 'OPEN']:
                            ticker = row.get('Ticker', 'Stock')
                            # Mencari harga yang valid
                            price_val = row.get('Price Alert') or row.get('Price') or row.get('Current Price') or '0'
                            timestamp_msg = datetime.now(wita_tz).strftime("%H:%M:%S")
                            is_entry = status_aksi in ['ENTRY', 'OPEN']
                            header_msg = "👍🏻 PAUS ALERT: ENTRY" if is_entry else "👎 PAUS ALERT: EXIT"
                            status_line = "🔵 ENTRY" if is_entry else "🔴 EXIT"
                            
                            pesan = (f"*{header_msg}*\n"
                                     f"Time : {timestamp_msg} WITA\n"
                                     f"Ticker: {ticker}\n"
                                     f"Price: {price_val}\n"
                                     f"Status : {status_line}")
                            send_telegram(pesan)
                    st.session_state.last_row_count = current_total_rows
    except Exception as e:
        st.warning(f"Sedang sinkronisasi data... ({e})")
    
    time.sleep(15)
    st.rerun()
