import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Konfigurasi Halaman Dasar
st.set_page_config(
    page_title="PAUS VWAP MONITOR",
    page_icon="🚀",
    layout="wide"
)

# 2. Fungsi Koneksi Aman ke GSheet
def init_connection():
    # Scope yang dibutuhkan untuk Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Mengambil kredensial dari Streamlit Secrets (untuk GitHub)
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception as e:
        st.error(f"Gagal memuat Secrets: {e}")
        st.stop()
        
    return gspread.authorize(creds)

# 3. Fungsi Ambil dan Olah Data
def get_vwap_data():
    client = init_connection()
    try:
        # Membuka Spreadsheet dan Tab Khusus VWAP
        sheet = client.open("SINYAL SAHAM").worksheet("VWAP_SUMMARY")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Pastikan kolom Frequency ada
            if 'Frequency' not in df.columns:
                df['Frequency'] = 0
                
            # Logika Auto-Sort: Sesuai Instruksi Bapak (Bullish/Golden dulu, baru Frequency)
            sort_order = {
                'ENTRY (VWAP GOLDEN)': 0,
                'HOLD (VWAP TREND)': 1,
                'WAITING': 2,
                'EXIT (VWAP DEATH)': 3
            }
            df['sort_idx'] = df['Action'].map(sort_order).fillna(4)
            df = df.sort_values(by=['sort_idx', 'Frequency'], ascending=[True, False]).drop(columns=['sort_idx'])
            
        return df
    except Exception as e:
        st.error(f"Error pembacaan data: {e}")
        return pd.DataFrame()

# 4. Tampilan Dashboard
st.title("🚀 PAUS VWAP(6) HOURLY MONITOR")
st.markdown("---")

# Tombol Refresh Manual
if st.button('🔄 Refresh Data Sekarang'):
    st.rerun()

# Load Data
df = get_vwap_data()

if not df.empty:
    # Fungsi Styling Warna untuk Kolom Action
    def style_action(val):
        color = 'white'
        if val == 'ENTRY (VWAP GOLDEN)': color = '#00ff00' # Hijau
        elif val == 'EXIT (VWAP DEATH)': color = '#ff4b4b' # Merah
        elif val == 'HOLD (VWAP TREND)': color = '#f9d342' # Kuning
        return f'color: {color}; font-weight: bold'

    # Menampilkan Tabel Utama
    st.subheader("Live Strategy: VWAP Summary")
    st.dataframe(
        df.style.applymap(style_action, subset=['Action']), 
        use_container_width=True,
        height=500
    )

    # Footer Informasi & Download (Konsistensi Fitur)
    st.success(f"✅ Terhubung ke Tab VWAP_SUMMARY. Update: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download VWAP Data (CSV)",
            data=csv,
            file_name=f'PAUS_VWAP_{pd.Timestamp.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
else:
    st.warning("Menunggu data dari listener_vwap.py masuk ke tab VWAP_SUMMARY...")

# Auto Refresh UI (Opsional: setiap 2 menit)
st.empty()
