import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- KONFIGURASI TELEGRAM ---
# Pastikan Token dan Chat ID sudah benar
TOKEN = "MASUKKAN_TOKEN_BOT_TELEGRAM_ANDA"
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
    # Mengambil key dari st.secrets (Streamlit Cloud)
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # MEMBUKA TAB 2 (SUMMARY) sesuai saran struktur sebelumnya
    sheet = client.open("SINYAL SAHAM").worksheet("SUMMARY")
except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
    st.stop()

st.title("🐋 PAUS Action Monitor")
st.info("Memantau Tab: SUMMARY secara real-time")

# --- LOGIKA MONITORING ---
if "last_row_count" not in st.session_state:
    st.session_state.last_row_count = len(sheet.get_all_values())

placeholder = st.empty()

while True:
    try:
        # Ambil semua data dari tab SUMMARY
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        current_row_count = len(df)

        with placeholder.container():
            st.subheader("Sinyal Trading Terkini")
            
            # Cek apakah kolom 'ACTION' ada (huruf besar sesuai gambar)
            if 'ACTION' in df.columns:
                # Menampilkan 10 data terakhir yang memiliki status sinyal
                display_df = df.tail(10)
                st.dataframe(display_df, use_container_width=True)
                
                # JIKA ADA BARIS BARU MASUK
                if current_row_count > st.session_state.last_row_count:
                    new_data = df.iloc[-1] # Ambil baris paling bawah
                    
                    # Filter: Hanya kirim ke Telegram jika ACTION adalah ENTRY, HOLD, atau OPEN
                    status_aksi = str(new_data['ACTION']).upper()
                    if status_aksi in ['ENTRY', 'HOLD', 'OPEN']:
                        ticker = new_data.get('Ticker', 'Unknown')
                        price = new_data.get('Price', '0')
                        waktu = new_data.get('Timestamp', '-')
                        
                        pesan = (f"🚀 *PAUS SIGNAL DETECTED*\n\n"
                                 f"Ticker: `{ticker}`\n"
                                 f"Action: *{status_aksi}*\n"
                                 f"Price: {price}\n"
                                 f"Time: {waktu}")
                        
                        send_telegram(pesan)
                    
                    st.session_state.last_row_count = current_row_count
            else:
                st.error("Error: Kolom 'ACTION' tidak ditemukan. Pastikan header di tab SUMMARY sudah benar.")

    except Exception as e:
        st.warning(f"Sedang sinkronisasi data... ({e})")
    
    time.sleep(30) # Cek setiap 30 detik
    st.rerun()
