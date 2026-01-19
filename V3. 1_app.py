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

st.title("🐋 PAUS Action Monitor v3.1")

if "last_row_count" not in st.session_state:
    try:
        current_data = sheet.get_all_records()
        st.session_state.last_row_count = len(current_data)
    except:
        st.session_state.last_row_count = 0

placeholder = st.empty()

while True:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        target_col = next((col for col in df.columns if col.lower() == 'action'), None)
        time_col = next((col for col in df.columns if col.lower() == 'timestamp'), None)
        
        # Penentuan Waktu WITA
        wita_tz = pytz.timezone('Asia/Makassar')
        today_date = datetime.now(wita_tz).strftime("%Y-%m-%d")

        with placeholder.container():
            if target_col:
                # --- LOGIKA SUMMARY HARIAN BERDASARKAN TIMESTAMP ---
                st.subheader(f"📅 Summary Hari Ini ({today_date})")
                
                if time_col:
                    # Ambil 10 karakter pertama dari Timestamp (YYYY-MM-DD)
                    # Kita gunakan .str[:10] untuk memastikan filter hanya pada tanggalnya saja
                    today_df = df[df[time_col].astype(str).str.contains(today_date)]
                    total_entry = len(today_df[today_df[target_col].str.upper() == 'ENTRY'])
                    total_exit = len(today_df[today_df[target_col].str.upper() == 'EXIT'])
                else:
                    total_entry = len(df[df[target_col].str.upper() == 'ENTRY'])
                    total_exit = len(df[df[target_col].str.upper() == 'EXIT'])

                c1, c2 = st.columns(2)
                c1.metric("Total ENTRY Hari Ini", f"{total_entry}")
                c2.metric("Total EXIT Hari Ini", f"{total_exit}")
                
                st.divider()

                st.subheader("📊 Live Trading Dashboard")
                styled_df = df.tail(20).style.apply(highlight_style, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                current_row_count = len(df)
                
                if current_row_count > st.session_state.last_row_count:
                    new_rows = df.iloc[st.session_state.last_row_count : current_row_count]
                    for _, row in new_rows.iterrows():
                        status_aksi = str(row[target_col]).upper()
                        if status_aksi in ['ENTRY', 'EXIT']:
                            ticker = row.get('Ticker', 'Stock')
                            price = row.get('Price Alert', row.get('Price', '0'))
                            timestamp_msg = datetime.now(wita_tz).strftime("%Y-%m-%d %H:%M:%S")
                            
                            header = "👍🏻 PAUS ALERT: ENTRY" if status_aksi == 'ENTRY' else "👎 PAUS ALERT: EXIT"
                            status_line = "🔵 ENTRY" if status_aksi == 'ENTRY' else "🔴 EXIT"
                            
                            pesan = (f"*{header}*\n"
                                     f"Time : {timestamp_msg} WITA\n"
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
