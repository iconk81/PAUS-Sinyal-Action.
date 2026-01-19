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

def color_rows(val):
    s_val = str(val).upper()
    if s_val == 'ENTRY': return 'background-color: #00FF00; color: black; font-weight: bold'
    if s_val in ['HOLD', 'OPEN']: return 'background-color: #1E90FF; color: white'
    if s_val == 'EXIT': return 'background-color: #FF4500; color: white; font-weight: bold'
    return ''

st.title("🐋 PAUS Action Monitor v2.4")
st.info("Status: Monitoring Aktif (WITA) | Multi-Row Detection Enabled")

# Inisialisasi last_row_count dengan jumlah data saat ini agar tidak spam saat start
if "last_row_count" not in st.session_state:
    try:
        initial_data = sheet.get_all_records()
        st.session_state.last_row_count = len(initial_data)
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
                styled_df = df.tail(20).style.map(color_rows, subset=[target_col])
                st.dataframe(styled_df, use_container_width=True, height=500)
                
                current_row_count = len(df)
                
                # JIKA ADA BARIS BARU (Bisa lebih dari satu baris)
                if current_row_count > st.session_state.last_row_count:
                    # Ambil semua baris baru mulai dari index terakhir yang tercatat
                    new_rows = df.iloc[st.session_state.last_row_count : current_row_count]
                    
                    for _, row in new_rows.iterrows():
                        status_aksi = str(row[target_col]).upper()
                        
                        if status_aksi in ['ENTRY', 'EXIT']:
                            ticker = row.get('Ticker', 'Stock')
                            price = row.get('Price Alert', row.get('Price', '0'))
                            
                            wita_tz = pytz.timezone('Asia/Makassar')
                            timestamp = datetime.now(wita_tz).strftime("%Y-%m-%d %H:%M:%S")
                            
                            if status_aksi == 'ENTRY':
                                icon = "🐂 BULL"
                                header = f"🔵 *PAUS ALERT: {status_aksi}*"
                            else:
                                icon = "🐻 BEAR"
                                header = f"🔴 *PAUS ALERT: {status_aksi}*"
                            
                            pesan = (f"{header}\n"
                                     f"Time : `{timestamp} WITA`\n"
                                     f"Ticker: *{ticker}* {icon}\n"
                                     f"Price: `{price}`\n"
                                     f"Status : *{status_aksi}*")
                            
                            send_telegram(pesan)
                            time.sleep(1) # Jeda antar pesan agar tidak diblokir Telegram
                    
                    st.session_state.last_row_count = current_row_count
            else:
                st.error("Kolom 'Action' tidak ditemukan.")

    except Exception as e:
        st.warning(f"Menunggu sinkronisasi... ({e})")
    
    time.sleep(30)
    st.rerun()
