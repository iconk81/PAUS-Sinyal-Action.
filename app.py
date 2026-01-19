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

st.title("🐋 PAUS Action Monitor v3.2")

if "last_row_count" not in st.session_state:
    try:
        # Untuk inisialisasi awal, ambil total baris yang ada
        st.session_state.last_row_count = len(sheet.get_all_values())
    except:
        st.session_state.last_row_count = 0

placeholder = st.empty()

while True:
    try:
        # --- OPTIMASI: Hanya ambil 1000 baris terakhir ---
        all_values = sheet.get_all_values()
        header = all_values[0]
        # Jika data lebih dari 1000, potong ambil yang bawah saja
        if len(all_values) > 1000:
            data_rows = all_values[-1000:]
        else:
            data_rows = all_values[1:]
            
        df = pd.DataFrame(data_rows, columns=header)
        current_total_rows = len(all_values)
        
        target_col = next((col for col in df.columns if col.lower() == 'action'), None)
        time_col = next((col for col in df.columns if col.lower() == 'timestamp'), None)
        
        wita_tz = pytz.timezone('Asia/Makassar')
        today_date = datetime.now(wita_tz).strftime("%Y-%m-%d")

        with placeholder.container():
            if target_col:
                # Summary hari ini
                st.subheader(f"📅 Summary Hari Ini ({today_date})")
                if time_col:
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

                # Tampilan Dashboard
                st.subheader("📊 Live Trading Dashboard (Last 20)")
                styled_df = df.tail(20).style.apply(highlight_style, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Deteksi baris baru
                if current_total_rows > st.session_state.last_row_count:
                    # Hitung berapa banyak baris baru
                    diff = current_total_rows - st.session_state.last_row_count
                    new_added_rows = df.tail(diff)
                    
                    for _, row in new_added_rows.iterrows():
                        status_aksi = str(row[target_col]).upper()
                        if status_aksi in ['ENTRY', 'EXIT']:
                            ticker = row.get('Ticker', 'Stock')
                            price = row.get('Price Alert', row.get('Price', '0'))
                            timestamp_msg = datetime.now(wita_tz).strftime("%Y-%m-%d %H:%M:%S")
                            
                            header_msg = "👍🏻 PAUS ALERT: ENTRY" if status_aksi == 'ENTRY' else "👎 PAUS ALERT: EXIT"
                            status_line = "🔵 ENTRY" if status_aksi == 'ENTRY' else "🔴 EXIT"
                            
                            pesan = (f"*{header_msg}*\n"
                                     f"Time : {timestamp_msg} WITA\n"
                                     f"Ticker: {ticker}\n"
                                     f"Price: {price}\n"
                                     f"Status : {status_line}")
                            
                            send_telegram(pesan)
                    
                    st.session_state.last_row_count = current_total_rows
            else:
                st.error("Kolom 'Action' tidak ditemukan.")

    except Exception as e:
        st.warning(f"Menunggu sinkronisasi...")
    
    time.sleep(15)
    st.rerun()
