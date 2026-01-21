import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Konfigurasi Halaman
st.set_page_config(page_title="PAUS ACTION MONITOR", layout="wide")

# Setup Koneksi GSheet menggunakan Secrets Streamlit
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Gunakan st.secrets agar lebih aman di Cloud
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

client = init_connection()

def get_data():
    sheet = client.open("SINYAL SAHAM").worksheet("SUMMARY")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Logika Auto-Sort agar sinkron dengan listener.py
    if not df.empty:
        # Prioritas: BULLISH (0), NEW (1), HOLD (2), EXIT (3)
        sort_order = {'ENTRY (BULLISH)': 0, 'ENTRY (NEW)': 1, 'HOLD (SIDEWAYS)': 2, 'EXIT (BEARISH)': 3}
        df['sort_idx'] = df['Action'].map(sort_order).fillna(4)
        df = df.sort_values(by=['sort_idx', 'Frequency'], ascending=[True, False]).drop(columns=['sort_idx'])
    return df

st.title("🚀 PAUS ACTION - LIVE MONITORING")
st.write("Real-time Summary Saham dari @DataSaham6Bot")

try:
    df = get_data()
    
    # Styling Tabel
    def highlight_status(val):
        color = 'white'
        if val == 'ENTRY (BULLISH)': color = '#00ff00'
        elif val == 'EXIT (BEARISH)': color = '#ff4b4b'
        elif val == 'ENTRY (NEW)': color = '#1ecbe1'
        return f'color: {color}'

    st.dataframe(df.style.applymap(highlight_status, subset=['Action']), use_container_width=True)
    
    st.success(f"✅ Data tersinkronisasi. Update terakhir: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tombol Download (Konsistensi Fitur)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Data CSV", csv, "PAUS_Trading.csv", "text/csv")

except Exception as e:
    st.error(f"Koneksi GSheet Terputus: {e}")

# Refresh otomatis (Streamlit Cloud akan reload setiap kali ada perubahan data di GSheet)
