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
st.set_page_config(page_title="PAUS Action Monitor", layout="wide")
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("SINYAL SAHAM").worksheet("SUMMARY")
except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
    st.stop()

# --- FUNGSI PEWARNAAN DASHBOARD ---
def highlight_style(row):
    target_col = next((col for col in row.index if col.lower() == 'action'), None)
    ticker_col = next((col for col in row.index if col.lower() == 'ticker'), None)
    styles = [''] * len(row)
    if target_col:
        status = str(row[target_col]).upper()
        idx_action = row.index.get_loc(target_col)
        idx_ticker = row.index.get_loc(ticker_col) if ticker_col else -1
        if status == 'ENTRY':
            color = 'background-color: #90EE90; color: black; font-weight: bold'
            styles[idx_action] = color
            if idx_ticker != -1: styles[idx_ticker] = color
        elif status == 'EXIT':
            color = 'background-color: #FF4500; color: white; font-weight: bold'
            styles[idx_action] = color
            if idx_ticker != -1: styles[idx_ticker] = color
    return styles

st.title("🐋 PAUS Action Monitor v2.9")

if "last_row_count" not in st.session_state:
    try:
        current_data = sheet.get_all_records()
        # Set agar baris terakhir saat ini langsung jadi alert saat startup
        st.session_state.last_row_count = len(current_data) - 1
    except:
        st.session_state.last_row_count = 0

placeholder = st.empty()

while True:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        target_col = next((col for col in df.columns if col.lower() == 'action'), None)

        with placeholder.container():
            if target_col:
                st.subheader("📊 Live Trading Dashboard")
                styled_df = df.tail(20).style.apply(highlight_style, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=500)
                
                current_row_count = len(df)
                
                if current_row_count > st.session_state.last_row_count:
                    new_rows = df.iloc[st.session_state.last_row_count : current_row_count]
                    
                    for _, row in new_rows.iterrows():
                        status_aksi = str(row[target_col]).upper()
                        if status_aksi in ['ENTRY', 'EXIT']:
                            ticker = row.get('Ticker', 'Stock')
                            price = row.get('Price Alert', row.get('Price', '0'))
                            wita_tz = pytz.timezone('Asia/Makassar')
                            timestamp = datetime.now(wita_tz).strftime("%Y-%m-%d %H:%M:%S")
                            
                            # SUSUNAN PESAN SESUAI PERMINTAAN TERAKHIR
                            if status_aksi == 'ENTRY':
                                header = "👍🏻 PAUS ALERT: ENTRY"
                                status_line = "🔵 ENTRY"
                            else:
                                header = "👎 PAUS ALERT: EXIT"
                                status_line = "🔴 EXIT"
                            
                            pesan = (f"*{header}*\n"
                                     f"Time : {timestamp} WITA\n"
                                     f"Ticker: {ticker}\n"
                                     f"Price: {price}\n"
                                     f"Status : {status_line}")
                            
                            send_telegram(pesan)
                    
                    st.session_state.last_row_count = current_row_count
            else:
                st.error("Kolom 'Action' tidak ditemukan.")

    except Exception as e:
        st.warning(f"Menunggu sinkronisasi...")
    
    time.sleep(15)
    st.rerun()
