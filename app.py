import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json
import time

# --- CONFIG PAGE ---
st.set_page_config(page_title="PAUS TRADING DASHBOARD", layout="wide", page_icon="🚀")

# --- SETUP GSHEETS (Menggunakan Streamlit Secrets) ---
def get_data():
    # Mengambil kredensial dari Secrets Streamlit alih-alih file fisik
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client_gs = gspread.authorize(creds)
    
    # Buka GSheet
    sh = client_gs.open("SINYAL SAHAM")
    tab_summary = sh.worksheet("SUMMARY")
    
    # Load ke Pandas DataFrame
    data = tab_summary.get_all_records()
    return pd.DataFrame(data)

# --- UI TAMPILAN ---
st.title("🚀 PAUS ACTION - LIVE MONITORING")
st.subheader("Real-time Summary Saham dari @DataSaham6Bot")

try:
    df = get_data()

    if not df.empty:
        # Format tampilan tabel
        def highlight_action(val):
            if val == 'ENTRY': color = '#2ecc71' # Hijau
            elif val == 'EXIT': color = '#e74c3c' # Merah
            elif val == 'HOLD': color = '#f1c40f' # Kuning
            else: color = 'transparent'
            return f'background-color: {color}; color: black; font-weight: bold'

        # Menampilkan tabel dengan sorting terbaru di atas
        df['Last_Update'] = pd.to_datetime(df['Last_Update'])
        df = df.sort_values(by='Last_Update', ascending=False)
        
        st.dataframe(
            df.style.applymap(highlight_action, subset=['Action']),
            use_container_width=True,
            height=500
        )
        
        st.write(f"✅ Data tersinkronisasi. Update terakhir: {df['Last_Update'].iloc[0]}")
    else:
        st.info("Menunggu data dari GSheet...")

except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
    st.info("Pastikan Secrets 'gcp_service_account' sudah dikonfigurasi di Streamlit Cloud.")

# Auto Refresh 30 detik
time.sleep(30)
st.rerun()
