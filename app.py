import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- KONFIGURASI (Ganti dengan data Anda) ---
TOKEN = "MASUKKAN_TOKEN_BOT_ANDA"
CHAT_ID = "MASUKKAN_CHAT_ID_DARI_USERINFOBOT"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Gagal kirim Telegram: {e}")

# --- KONEKSI GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# Mengambil key dari st.secrets (Keamanan standar Streamlit Cloud)
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("SINYAL SAHAM").sheet1

st.title("🐋 PAUS Action Monitor")
st.write("Memantau sinyal dari Google Sheet secara real-time...")

# --- LOGIKA MONITORING ---
if "last_row_count" not in st.session_state:
    st.session_state.last_row_count = len(sheet.get_all_values())

placeholder = st.empty()

while True:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        current_row_count = len(df)

        with placeholder.container():
            st.subheader("Sinyal Action Terkini")
            # Filter hanya Entry dan Hold
            filter_df = df[df['Action'].isin(['ENTRY', 'HOLD'])].tail(10)
            st.table(filter_df)

        # Jika ada baris baru masuk
        if current_row_count > st.session_state.last_row_count:
            new_data = df.iloc[-1] # Ambil baris paling baru
            
            if new_data['Action'] in ['ENTRY', 'HOLD']:
                pesan = (f"🚀 *PAUS SIGNAL ACTION*\n\n"
                         f"Ticker: {new_data['Ticker']}\n"
                         f"Action: {new_data['Action']}\n"
                         f"Price: {new_data['Price']}\n"
                         f"Time: {new_data['Timestamp']}")
                send_telegram(pesan)
            
            st.session_state.last_row_count = current_row_count
            
    except Exception as e:
        st.error(f"Error: {e}")
    
    time.sleep(30) # Cek setiap 30 detik agar tidak kena limit Google
    st.rerun()
