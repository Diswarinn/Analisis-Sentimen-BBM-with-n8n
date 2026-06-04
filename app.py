import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 1. KONFIGURASI SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. SETUP HALAMAN
st.set_page_config(page_title="Sentimen Geopolitik & BBM", layout="wide")
st.title("📊 Analisis Sentimen Publik: Isu BBM & Geopolitik")
st.markdown("Perbandingan akurasi antara algoritma Rule-Based (JavaScript) vs LLM (Gemini AI)")

# 3. FUNGSI AMBIL DATA
@st.cache_data(ttl=30)
def get_data(table_name):
    response = supabase.table(table_name).select("*").execute()
    return pd.DataFrame(response.data)

try:
    df_js = get_data("analisis_sentimen_js")
    df_llm = get_data("analisis_sentimen_llm")

    # 4. BUAT 3 TAB UNTUK PERBANDINGAN & CHATBOT
    tab1, tab2, tab3 = st.tabs(["🤖 Hasil AI (Gemini)", "⚙️ Hasil Rule-Based (Script JS)", "💬 Asisten AI (Chatbot)"])

    # FUNGSI RENDER GRAFIK ASLI KAMU YANG SEMPAT HILANG
    def render_tab_content(df, tab_name):
        if df.empty:
            st.info(f"Menunggu data masuk dari workflow n8n ke tabel {tab_name}...")
            return

        # Deteksi otomatis nama kolom
        col_kategori = 'kategori_hasil_sortir' if 'kategori_hasil_sortir' in df.columns else ('kategori' if 'kategori' in df.columns else None)
        col_tokoh = 'tokoh_terkait' if 'tokoh_terkait' in df.columns else ('tokoh' if 'tokoh' in df.columns else None)
        col_text = 'full_text' if 'full_text' in df.columns else ('komentar' if 'komentar' in df.columns else ('text' if 'text' in df.columns else None))

        if not col_kategori:
            st.warning("Belum ada data kategori yang masuk. Tunggu n8n selesai memproses...")
            return

        col1, col2 = st.columns(2)

        # GRAFIK 1: SENTIMEN
        with col1:
            st.subheader("Distribusi Sentimen")
            sentimen_count = df[col_kategori].value_counts().reset_index()
            sentimen_count.columns = ['Kategori', 'Jumlah']
            
            color_map = {'MARAH': '#EF4444', 'PASRAH': '#94A3B8', 'SETUJU': '#22C55E'}
            fig_sentimen = px.pie(
                sentimen_count, 
                values='Jumlah', 
                names='Kategori',
                color='Kategori',
                color_discrete_map=color_map,
                hole=0.4
            )
            st.plotly_chart(fig_sentimen, use_container_width=True)

 # GRAFIK 2: TOKOH TERKAIT
        with col2:
            st.subheader("Tokoh Geopolitik yang Disorot")
            if col_tokoh:
                df_tokoh = df.dropna(subset=[col_tokoh])
                
                if not df_tokoh.empty:
                    df_clean = df_tokoh.copy()
                    
                    # Pecah string berdasar koma
                    df_clean['tokoh_split'] = df_clean[col_tokoh].astype(str).str.split(',')
                    
                    # Explode (pisahkan list jadi baris-baris baru)
                    df_exploded = df_clean.explode('tokoh_split')
                    
                    # Bersihkan spasi kosong
                    df_exploded['tokoh_split'] = df_exploded['tokoh_split'].str.strip()
                    
                    # ==========================================
                    # TAMBALAN SANITASI DATA (MENGATASI HALUSINASI LLM)
                    # ==========================================
                    # 1. Koreksi negara menjadi nama tokoh
                    mapping_koreksi = {
                        'Iran': 'Khamenei',
                        'Israel': 'Netanyahu',
                        'Zionis': 'Netanyahu'
                    }
                    df_exploded['tokoh_split'] = df_exploded['tokoh_split'].replace(mapping_koreksi)
                    
                    # 2. Hapus semua nama selain 3 tokoh utama (Otomatis membuang Prabowo, dll)
                    allowed_names = ['Khamenei', 'Trump', 'Netanyahu']
                    df_exploded = df_exploded[df_exploded['tokoh_split'].isin(allowed_names)]
                    # ==========================================

                    # Baru kita hitung jumlahnya
                    tokoh_count = df_exploded['tokoh_split'].value_counts().reset_index()
                    tokoh_count.columns = ['Tokoh', 'Jumlah Mention']
                    
                    fig_tokoh = px.bar(
                        tokoh_count,
                        x='Tokoh',
                        y='Jumlah Mention',
                        color='Tokoh',
                        text_auto=True
                    )
                    st.plotly_chart(fig_tokoh, use_container_width=True)
                else:
                    st.write("Belum ada tokoh spesifik yang terdeteksi pada batch ini.")
            else:
                st.write("Kolom tokoh belum tersedia di database.")
                
    # Render isi untuk masing-masing tab
    with tab1:
        render_tab_content(df_llm, "analisis_sentimen_llm")
        
    with tab2:
        render_tab_content(df_js, "analisis_sentimen_js")

    # ==========================================
    # KODE BARU UNTUK TAB 3 (CHATBOT)
    # ==========================================
    with tab3:
        st.subheader("💬 Asisten Analis Data Sentimen")
        st.markdown("Tanyakan apa saja seputar tren yang sudah masuk ke database. AI akan membaca 50 data terbaru untuk menjawab pertanyaanmu.")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Contoh: Tokoh siapa yang paling banyak disorot?"):
            
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner("Menggali data di database..."):
                try:
                    # ---> MASUKKAN URL PRODUCTION N8N KAMU DI SINI <---
                    WEBHOOK_URL = "http://localhost:5678/webhook/tanya-ai" 
                    
                    response = requests.post(WEBHOOK_URL, json={"pesan": prompt})
                    response.raise_for_status() 

                    ai_reply = response.text

                    st.chat_message("assistant").markdown(ai_reply)
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})

                except Exception as e:
                    st.error(f"Gagal menghubungi server n8n: {e}")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")

# Tombol Refresh Manual
if st.button('🔄 Refresh Data Terbaru'):
    st.cache_data.clear()
    st.rerun()