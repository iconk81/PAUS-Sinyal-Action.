import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- KONFIGURASI TELEGRAM ---
TOKEN = "MASUKKAN_TOKEN_BOT_ANDA"
CHAT_ID = "MASUKKAN_CHAT_ID_ANDA"

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
    # Membaca tab SUMMARY sesuai struktur Anda
    sheet = client.open("SINYAL SAHAM").worksheet("SUMMARY")
except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
    st.stop()

st.title("🐋 PAUS Action Monitor")
st.info("Mode: Fleksibel (Mendeteksi Kolom Action/ACTION)")

if "last_row_count" not in st.session_state:
    st.session_state.last_row_count = len(sheet.get_all_values())

placeholder = st.empty()

while True:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # MENCARI KOLOM ACTION SECARA OTOMATIS (Case-Insensitive)
        # Ini agar Anda tidak perlu ubah Google Sheet
        target_col = None
        for col in df.columns:
            if col.lower() == 'action':
                target_col = col
                break

        with placeholder.container():
            if target_col:
                st.subheader(f"Sinyal Terkini (Kolom: {target_col})")
                st.dataframe(df.tail(15), use_container_width=True)
                
                current_row_count = len(df)
                if current_row_count > st.session_state.last_row_count:
                    new_data = df.iloc[-1]
                    status_aksi = str(new_data[target_col]).upper()
                    
                    if status_aksi in ['ENTRY', 'HOLD', 'OPEN']:
                        ticker = new_data.get('Ticker', 'Stock')
                        price = new_data.get('Current Price', new_data.get('Price', '0'))
                        
                        pesan = (f"🚀 *PAUS SIGNAL DETECTED*\n\n"
                                 f"Ticker: `{ticker}`\n"
                                 f"Action: *{status_aksi}*\n"
                                 f"Price: {price}\n"
                                 f"Source: Tab SUMMARY")
                        send_telegram(pesan)
                    
                    st.session_state.last_row_count = current_row_count
            else:
                st.error("Kolom 'Action' tidak ditemukan. Harap cek baris pertama Tab SUMMARY.")

    except Exception as e:
        st.warning(f"Menunggu data baru... ({e})")
    
    time.sleep(30)
    st.rerun()
