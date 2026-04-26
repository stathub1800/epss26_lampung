import streamlit as st
import streamlit.components.v1 as components
import requests
import io
import os
import re
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from PIL import Image
import fitz  # PyMuPDF
from fpdf import FPDF
import gdown

# ========== KONFIGURASI ==========
SUPABASE_URL = os.getenv("SUPABASE_URL", "GANTI_DENGAN_URL_SUPABASE_ANDA")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "GANTI_DENGAN_KEY_SUPABASE_ANDA")

# Service Role Key — untuk operasi admin (INSERT/DELETE) yang bypass RLS
# Ambil dari: Supabase Dashboard → Project Settings → API → service_role (secret)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "GANTI_DENGAN_SERVICE_ROLE_KEY_ANDA")

# Password Admin diubah menjadi hardcode agar tidak error terbaca env variable yang kosong
ADMIN_PASSWORD = "kominfo123"

PROVINSI = "Provinsi Lampung"

# Disesuaikan dengan lokus
OPD_LIST = [
    "Dinas Peternakan dan Kesehatan Hewan",
    "Dinas Ketahanan Pangan, Tanaman Pangan dan Hortikultura"
]

# Kredensial khusus untuk masing-masing OPD
OPD_PASSWORDS = {
    "Dinas Peternakan dan Kesehatan Hewan": "ternaklampungmaju",
    "Dinas Ketahanan Pangan, Tanaman Pangan dan Hortikultura": "tanilampungmaju"
}

# Simulasi 38 Indikator (Bisa ditambahkan sesuai kebutuhan)
INDIKATOR = [
    {"kode": "10101", "nama": "Tingkat Kematangan Penerapan Standar Data Statistik (SDS)"},
    {"kode": "10201", "nama": "Tingkat Kematangan Penerapan Metadata Statistik"},
    {"kode": "10301", "nama": "Tingkat Kematangan Penerapan Kode Referensi dan Data Induk"},
    {"kode": "10401", "nama": "Tingkat Kematangan Penerapan Data Prioritas"},
    {"kode": "20101", "nama": "Tingkat Kelengkapan Metadata Kegiatan Statistik"},
    {"kode": "20201", "nama": "Tingkat Ketersediaan Data Statistik Sektoral"},
    {"kode": "30101", "nama": "Tingkat Kematangan Proses Bisnis Statistik"},
]
# ==================================

# Inisialisasi Supabase
@st.cache_resource
def init_supabase():
    # Client biasa (anon key) — untuk SELECT/read
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def init_supabase_admin():
    # Client admin (service_role key) — untuk INSERT/DELETE, bypass RLS
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

try:
    sb = init_supabase()
    sb_admin = init_supabase_admin()
except Exception as e:
    st.error("Gagal koneksi ke Supabase. Cek URL dan KEY.")

# Setup folders untuk temp files saat proses generate
Path("temp_pdfs").mkdir(exist_ok=True)
Path("temp_screenshots").mkdir(exist_ok=True)

# Page config (Logo shield)
st.set_page_config(page_title="Andan Sektoral Lampung", page_icon="🛡️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Mengatasi padding bawaan Streamlit agar tombol tidak terpotong (diperbesar padding top nya) */
    .block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 100%; }
    .stButton>button { background-color: #2b5c8f; color: white; border-radius: 6px; padding-top: 0.5rem; padding-bottom: 0.5rem;}
    .stButton>button:hover { background-color: #1a3c61; border-color: white;}
    .doc-card { background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 1rem; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)


# ========== HELPER FUNCTIONS ==========

def extract_file_id_from_drive_link(link):
    """Ekstrak file ID dari berbagai format link Google Drive"""
    patterns = [
        r'/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/file/d/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    return None

def download_pdf_from_drive(drive_link, output_path):
    """Download PDF dari Google Drive"""
    file_id = extract_file_id_from_drive_link(drive_link)
    if not file_id:
        return False
    
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        # Coba gunakan gdown
        gdown.download(download_url, output_path, quiet=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except:
        pass
    
    # Fallback requests biasa
    try:
        response = requests.get(download_url, allow_redirects=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def screenshot_pdf_pages(pdf_path, page_numbers):
    """Screenshot halaman tertentu dari PDF, return list of dicts"""
    screenshots = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in page_numbers:
            if 1 <= page_num <= len(doc):
                page = doc[page_num - 1]  # 0-indexed di PyMuPDF
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Zoom 2x agar teks terbaca jelas
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                screenshots.append({"page": page_num, "image": img})
        doc.close()
        return screenshots
    except Exception as e:
        print(f"Error screenshot PDF: {str(e)}")
        return []

def create_pdf_rekap(docs, indikator_kode, indikator_nama):
    """Fungsi utama merakit PDF Recap (Download -> Screenshot -> Tempel ke FPDF)"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- HALAMAN COVER ---
    pdf.add_page()
    pdf.set_fill_color(43, 92, 143)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(255, 255, 255)
    
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 70, '', ln=True)
    pdf.multi_cell(0, 10, "REKAPITULASI BUKTI DUKUNG", align='C')
    pdf.multi_cell(0, 10, "EVALUASI PENYELENGGARAAN STATISTIK SEKTORAL", align='C')
    
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 15, '', ln=True)
    pdf.multi_cell(0, 8, f"Indikator {indikator_kode}", align='C')
    pdf.set_font('Arial', 'B', 14)
    pdf.multi_cell(0, 8, indikator_nama, align='C')
    
    pdf.cell(0, 30, '', ln=True)
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 8, PROVINSI.upper(), align='C', ln=True)
    pdf.cell(0, 8, f"Tahun {datetime.now().year}", align='C', ln=True)

    # --- KONTEN DOKUMEN ---
    for doc in docs:
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        
        # Header OPD
        pdf.set_fill_color(230, 240, 250)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 12, f" {doc['opd_name']}", ln=True, fill=True)
        pdf.ln(5)
        
        # Info Dokumen
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(40, 6, "Nama Dokumen", 0, 0)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, f": {doc['doc_name']}")
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(40, 6, "Link Drive", 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 255)
        pdf.multi_cell(0, 6, f": {doc['drive_link'][:80]}...")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        marked_pages = doc.get('marked_pages', [])
        
        if not marked_pages:
            pdf.cell(0, 10, "Tidak ada halaman yang ditandai untuk discreenshot.", ln=True)
            continue

        # Proses Download & Screenshot di belakang layar
        pdf_path = f"temp_pdfs/temp_{doc['id']}.pdf"
        
        # Tulis ke PDF bahwa sedang memproses
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Bukti Dukung (Screenshot):", ln=True)
        
        success_download = download_pdf_from_drive(doc['drive_link'], pdf_path)
        
        if success_download:
            page_numbers_to_ss = [p['page'] for p in marked_pages]
            screenshots = screenshot_pdf_pages(pdf_path, page_numbers_to_ss)
            
            for p_info in marked_pages:
                hal = p_info['page']
                narasi = p_info['narasi']
                
                # Cari image data
                img_data = next((ss for ss in screenshots if ss['page'] == hal), None)
                
                if pdf.get_y() > 220:
                    pdf.add_page()
                else:
                    pdf.ln(5)

                # Kotak Narasi
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, f"Halaman {hal}:", ln=True)
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, narasi)
                pdf.ln(2)
                
                # Tempel Gambar
                if img_data:
                    temp_img_path = f"temp_screenshots/img_{doc['id']}_{hal}.png"
                    img_data['image'].save(temp_img_path, 'PNG')
                    
                    img_w, img_h = img_data['image'].size
                    target_w = 160
                    target_h = (target_w / img_w) * img_h
                    
                    if pdf.get_y() + target_h > 280:
                        pdf.add_page()
                    
                    x_pos = (210 - target_w) / 2
                    pdf.image(temp_img_path, x=x_pos, y=pdf.get_y(), w=target_w, h=target_h)
                    pdf.set_y(pdf.get_y() + target_h + 5)
                    
                    Path(temp_img_path).unlink(missing_ok=True)
                else:
                    pdf.set_text_color(255, 0, 0)
                    pdf.cell(0, 6, f"[Gagal mengambil screenshot Halaman {hal}]", ln=True)
                    pdf.set_text_color(0, 0, 0)
            
            Path(pdf_path).unlink(missing_ok=True)
            
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(0, 6, "Gagal mengunduh file PDF dari Google Drive. Pastikan akses link bersifat 'Siapa saja yang memiliki link' (Public).")
            pdf.set_text_color(0, 0, 0)

    output_filename = f"temp_pdfs/Rekap_{indikator_kode}_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(output_filename)
    return output_filename

# ========== HALAMAN OTENTIKASI & LANDING PAGE ==========

# Inisialisasi State Aplikasi
if 'auth_role' not in st.session_state:
    st.session_state.auth_role = None
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

# Logo Perisai (Shield) + Grafik Batang di dalamnya (Diubah jadi 1 baris agar tidak merusak parser Markdown Streamlit)
SVG_LOGO = '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><line x1="9" y1="15" x2="9" y2="12"></line><line x1="12" y1="15" x2="12" y2="9"></line><line x1="15" y1="15" x2="15" y2="13"></line></svg>'

def landing_page():
    # Bagian Header/Navbar Native Streamlit yang sejajar
    col_logo, col_space, col_btn = st.columns([5, 4, 2])
    with col_logo:
        st.markdown(f"""
<div style="display: flex; align-items: center; gap: 12px; padding-top: 2px;">
    <div style="width: 45px; height: 45px; background: linear-gradient(135deg, #0ea5e9, #2563eb); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);">
        {SVG_LOGO.format(size=24)}
    </div>
    <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px;">Andan<span style="color: #2563eb;">Sektoral</span></h1>
</div>
""", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True) # micro-adjustment agar sejajar
        if st.button("🔑 Masuk / Login", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()

    # Konten Split-Screen Landing Page dengan Diagram Alur / Timeline Vertikal
    infografis_html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
            body {{
                font-family: 'Inter', sans-serif;
                background-color: transparent; 
            }}
            /* Styling untuk hover pada item timeline */
            .timeline-item {{
                transition: all 0.3s ease;
            }}
            .timeline-item:hover {{
                transform: translateX(5px);
            }}
            .timeline-item:hover .timeline-icon {{
                transform: scale(1.1);
                box-shadow: 0 0 15px rgba(37, 99, 235, 0.3);
            }}
        </style>
    </head>
    <body class="text-slate-800">
        <main class="flex items-center pt-8 lg:pt-12 pb-10">
            <div class="w-full">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-12 items-center">
                    
                    <!-- BAGIAN KIRI: Teks Utama -->
                    <div class="space-y-8 pr-0 lg:pr-8">
                        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-bold uppercase tracking-wide shadow-sm">
                            <span class="relative flex h-2 w-2">
                              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                              <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                            </span>
                            Sistem Rekapitulasi Otomatis
                        </div>
                        
                        <h2 class="text-4xl xl:text-5xl font-extrabold text-slate-900 leading-[1.15] tracking-tight">
                            Bukti Dukung <br/>
                            <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Statistik Sektoral</span>
                        </h2>
                        
                        <p class="text-slate-600 text-base lg:text-lg leading-relaxed">
                            Aplikasi web cerdas untuk menyatukan ratusan dokumen PDF dari berbagai dinas. Mengekstrak halaman dan mengambil <em>screenshot</em> secara otomatis menjadi satu laporan final yang proporsional sebagai upaya <em>andan</em> (merawat dan menjaga) kualitas data statistik sektoral daerah.
                        </p>
                        
                        <div class="pt-6 border-t border-slate-200">
                            <div class="flex flex-wrap items-center gap-3">
                                <div class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-md border border-slate-200 shadow-sm">
                                    <i class="fa-solid fa-building text-emerald-500 text-sm"></i>
                                    <span class="text-xs font-semibold text-slate-700">Dinas Lokus</span>
                                </div>
                                <div class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-md border border-slate-200 shadow-sm">
                                    <i class="fa-solid fa-shield-halved text-blue-500 text-sm"></i>
                                    <span class="text-xs font-semibold text-slate-700">Walidata</span>
                                </div>
                                <div class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-md border border-slate-200 shadow-sm">
                                    <i class="fa-solid fa-chart-pie text-amber-500 text-sm"></i>
                                    <span class="text-xs font-semibold text-slate-700">Penilai BPS</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- BAGIAN KANAN: Diagram Alur (Timeline Flowchart) -->
                    <div class="relative w-full max-w-lg mx-auto lg:ml-auto">
                        <!-- Efek cahaya background -->
                        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl -z-10"></div>
                        
                        <!-- Timeline Container -->
                        <div class="relative space-y-6">
                            
                            <!-- Garis Penghubung Vertikal -->
                            <div class="absolute left-[1.35rem] top-4 bottom-8 w-0.5 bg-gradient-to-b from-blue-500 via-indigo-400 to-emerald-400 -z-10"></div>
                            
                            <!-- Step 1 -->
                            <div class="relative flex items-start gap-5 timeline-item cursor-default">
                                <div class="w-11 h-11 rounded-full bg-white border-4 border-blue-50 text-blue-600 shadow-md flex items-center justify-center font-bold text-lg flex-shrink-0 timeline-icon z-10">
                                    1
                                </div>
                                <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex-1">
                                    <h3 class="font-bold text-slate-800 text-base mb-1">Upload ke Drive</h3>
                                    <p class="text-sm text-slate-500 leading-relaxed">Dinas mengunggah dokumen PDF ke Google Drive dan mengatur akses link menjadi publik.</p>
                                </div>
                            </div>

                            <!-- Step 2 -->
                            <div class="relative flex items-start gap-5 timeline-item cursor-default">
                                <div class="w-11 h-11 rounded-full bg-white border-4 border-blue-50 text-indigo-600 shadow-md flex items-center justify-center font-bold text-lg flex-shrink-0 timeline-icon z-10">
                                    2
                                </div>
                                <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex-1">
                                    <h3 class="font-bold text-slate-800 text-base mb-1">Input di Sistem</h3>
                                    <p class="text-sm text-slate-500 leading-relaxed">Dinas login ke portal, menempelkan link Drive, lalu menentukan halaman target <em>screenshot</em> beserta narasinya.</p>
                                </div>
                            </div>

                            <!-- Step 3 -->
                            <div class="relative flex items-start gap-5 timeline-item cursor-default">
                                <div class="w-11 h-11 rounded-full bg-white border-4 border-blue-50 text-purple-600 shadow-md flex items-center justify-center font-bold text-lg flex-shrink-0 timeline-icon z-10">
                                    3
                                </div>
                                <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex-1">
                                    <h3 class="font-bold text-slate-800 text-base mb-1">Generate Otomatis</h3>
                                    <p class="text-sm text-slate-500 leading-relaxed">Walidata menekan tombol proses. Mesin mengunduh PDF, mengekstrak, dan memotong tangkapan layar.</p>
                                </div>
                            </div>

                            <!-- Step 4 (Final) -->
                            <div class="relative flex items-start gap-5 timeline-item cursor-default">
                                <div class="w-11 h-11 rounded-full bg-emerald-500 border-4 border-emerald-100 text-white shadow-lg flex items-center justify-center font-bold text-lg flex-shrink-0 timeline-icon z-10">
                                    <i class="fa-solid fa-check"></i>
                                </div>
                                <div class="bg-gradient-to-br from-slate-900 to-slate-800 p-4 rounded-xl border border-slate-700 shadow-md flex-1 text-white relative overflow-hidden">
                                    <i class="fa-solid fa-file-pdf absolute -right-2 -bottom-4 text-5xl text-white/5"></i>
                                    <h3 class="font-bold text-white text-base mb-1">Laporan Siap!</h3>
                                    <p class="text-sm text-slate-300 leading-relaxed">PDF rekapitulasi final tersusun dengan proporsional dan siap diserahkan ke BPS.</p>
                                </div>
                            </div>

                        </div>
                    </div>

                </div>
            </div>
        </main>
    </body>
    </html>
    """
    # Mengurangi tinggi agar tidak menyebabkan layout bolong/scroll berlebih di layar
    components.html(infografis_html, height=650, scrolling=False)


def login_page():
    # Tombol Kembali
    col_back, _ = st.columns([1, 6])
    with col_back:
        if st.button("⬅️ Kembali ke Beranda", use_container_width=True):
            st.session_state.show_login = False
            st.rerun()

    st.write("")
    
    # Form Login Centered
    col_space1, col_login, col_space2 = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown(f"""
<div style='background-color: white; padding: 40px; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05); margin-bottom: 20px; display: flex; flex-direction: column; align-items: center;'>
    <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #0ea5e9, #2563eb); border-radius: 16px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3); margin-bottom: 15px;">
        {SVG_LOGO.format(size=32)}
    </div>
    <h2 style='margin-top: 0; text-align: center; color: #1e293b; font-weight: 800; margin-bottom: 5px; font-size: 28px;'>Andan<span style="color: #2563eb;">Sektoral</span></h2>
    <p style='text-align: center; color: #64748b; font-weight: 500; margin-bottom: 25px;'>Provinsi Lampung</p>
    <div style="width: 100%; height: 1px; background-color: #e2e8f0; margin-bottom: 25px;"></div>
    <p style='text-align: center; color: #475569; font-weight: 600; margin-bottom: 20px;'>Masuk ke Akun Anda</p>
</div>
""", unsafe_allow_html=True)
        
        role = st.selectbox("Masuk Sebagai:", ["Dinas (Lokus)", "Walidata (Kominfo)"])
        st.write("")
        
        if role == "Dinas (Lokus)":
            opd = st.selectbox("Pilih OPD", OPD_LIST)
            password = st.text_input("Password", type="password", placeholder="Masukkan password OPD Anda")
            
            st.write("")
            if st.button("🚀 Masuk", use_container_width=True, type="primary"):
                # Validasi password berdasarkan OPD yang dipilih
                if opd in OPD_PASSWORDS and password == OPD_PASSWORDS[opd]:
                    st.session_state.auth_role = "opd"
                    st.session_state.opd_name = opd
                    st.rerun()
                else:
                    st.error("❌ Password salah untuk instansi tersebut!")
                    
        elif role == "Walidata (Kominfo)":
            password = st.text_input("Password Admin", type="password", placeholder="Masukkan password administrator")
            
            st.write("")
            if st.button("🚀 Masuk Walidata", use_container_width=True, type="primary"):
                if password == ADMIN_PASSWORD:
                    st.session_state.auth_role = "admin"
                    st.rerun()
                else:
                    st.error("❌ Password admin salah!")

# ========== DASHBOARD OPD ==========

def opd_dashboard():
    st.markdown(f"""
<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
    <div style="width: 50px; height: 50px; background: linear-gradient(135deg, #0ea5e9, #2563eb); border-radius: 14px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);">
        {SVG_LOGO.format(size=28)}
    </div>
    <div>
        <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px; line-height: 1.2;">Andan<span style="color: #2563eb;">Sektoral</span></h1>
        <p style="margin: 0; font-size: 14px; color: #64748b; font-weight: 500;">Panel Dinas (Lokus)</p>
    </div>
</div>
""", unsafe_allow_html=True)
    st.info(f"Login sebagai: **{st.session_state.opd_name}**")
    
    with st.sidebar:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth_role = None
            st.session_state.show_login = False
            st.rerun()

    with st.form("upload_form"):
        indikator_kode = st.selectbox(
            "Pilih Indikator *", 
            [i['kode'] for i in INDIKATOR],
            format_func=lambda x: f"{x} - {next(i['nama'] for i in INDIKATOR if i['kode']==x)}"
        )
        
        doc_name = st.text_input("Nama Dokumen *", placeholder="Misal: SK Walidata atau Laporan Evaluasi 2023")
        drive_link = st.text_input("Link Google Drive (PDF) *", placeholder="https://drive.google.com/file/d/..../view")
        
        st.markdown("""
        **Tentukan Halaman & Narasi** Ketikkan nomor halaman yang ingin di-screenshot, diikuti tanda strip `-`, lalu ketik narasinya. Setiap halaman dipisah dengan **baris baru (Enter)**.
        """)
        
        halaman_input = st.text_area(
            "Input Halaman dan Narasi *", 
            height=150,
            placeholder="1 - Ini adalah halaman Cover yang membuktikan ketersediaan dokumen.\n5 - Tabel daftar standar data yang digunakan dinas."
        )
        
        submit = st.form_submit_button("Kirim Bukti Dukung", type="primary")
        
        if submit:
            if not doc_name or not drive_link or not halaman_input:
                st.error("Harap lengkapi semua isian yang wajib (*)!")
            else:
                marked_pages = []
                try:
                    for line in halaman_input.split('\n'):
                        if line.strip() and '-' in line:
                            parts = line.split('-', 1)
                            hal = int(parts[0].strip())
                            narasi = parts[1].strip()
                            marked_pages.append({"page": hal, "narasi": narasi})
                            
                    if not marked_pages:
                        st.error("Format input halaman salah. Gunakan format: Nomor - Narasi")
                        st.stop()
                        
                except ValueError:
                    st.error("Pastikan nomor halaman berupa ANGKA (misal: 1, bukan satu).")
                    st.stop()
                
                indikator_nama = next(i['nama'] for i in INDIKATOR if i['kode']==indikator_kode)
                data = {
                    "opd_name": st.session_state.opd_name,
                    "indikator_kode": indikator_kode,
                    "indikator_nama": indikator_nama,
                    "doc_name": doc_name,
                    "drive_link": drive_link,
                    "marked_pages": marked_pages
                }
                
                sb_admin.table('bukti_dukung').insert(data).execute()
                st.success("✅ Bukti dukung berhasil disimpan!")
                st.balloons()

# ========== DASHBOARD ADMIN / WALIDATA ==========

def admin_dashboard():
    st.markdown(f"""
<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
    <div style="width: 50px; height: 50px; background: linear-gradient(135deg, #0ea5e9, #2563eb); border-radius: 14px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);">
        {SVG_LOGO.format(size=28)}
    </div>
    <div>
        <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px; line-height: 1.2;">Andan<span style="color: #2563eb;">Sektoral</span></h1>
        <p style="margin: 0; font-size: 14px; color: #64748b; font-weight: 500;">Ruang Kerja Walidata (Kominfo)</p>
    </div>
</div>
""", unsafe_allow_html=True)
    
    with st.sidebar:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth_role = None
            st.session_state.show_login = False
            st.rerun()
            
    st.write("### 📄 Rekapitulasi Berdasarkan Indikator")
    
    result = sb.table('bukti_dukung').select('*').order('created_at', desc=True).execute()
    semua_dokumen = result.data if result.data else []
    
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        pilih_indikator = st.selectbox(
            "Pilih Indikator untuk di-Rekap",
            [i['kode'] for i in INDIKATOR],
            format_func=lambda x: f"{x} - {next(i['nama'] for i in INDIKATOR if i['kode']==x)}"
        )
    
    docs_filtered = [d for d in semua_dokumen if d['indikator_kode'] == pilih_indikator]
    
    with col_filter2:
        st.write("") 
        st.write("")
        if st.button("🎯 GENERATE REKAP PDF", type="primary", use_container_width=True):
            if not docs_filtered:
                st.warning("Belum ada OPD yang mengupload bukti dukung untuk indikator ini.")
            else:
                with st.spinner("⏳ Sedang memproses... Mengunduh PDF, memotong halaman, dan menyusun laporan. Harap tunggu..."):
                    indikator_nama = next(i['nama'] for i in INDIKATOR if i['kode']==pilih_indikator)
                    try:
                        pdf_path = create_pdf_rekap(docs_filtered, pilih_indikator, indikator_nama)
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                            
                        st.success("✅ File Rekap Berhasil Dibuat!")
                        st.download_button(
                            label="⬇️ DOWNLOAD FILE REKAP PDF",
                            data=pdf_bytes,
                            file_name=f"Rekap_{pilih_indikator}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat generate: {str(e)}")

    st.markdown("---")
    st.write("### 📚 Kelola Data Bukti Dukung (Edit/Remove)")
    
    if not semua_dokumen:
        st.info("Belum ada data masuk.")
    else:
        for doc in semua_dokumen:
            with st.container():
                st.markdown(f"""
<div class="doc-card">
    <h4>{doc['opd_name']}</h4>
    <p style="margin-bottom: 5px;"><strong>Indikator:</strong> {doc['indikator_kode']} - {doc['indikator_nama']}</p>
    <p style="margin-bottom: 5px;"><strong>Dokumen:</strong> {doc['doc_name']} <a href="{doc['drive_link']}" target="_blank">(Buka Drive)</a></p>
</div>
""", unsafe_allow_html=True)
                
                with st.expander("Detail Halaman & Narasi"):
                    for p in doc.get('marked_pages', []):
                        st.write(f"**Hal {p['page']}:** {p['narasi']}")
                        
                if st.button("🗑️ Hapus Evaluasi Ini", key=f"del_{doc['id']}"):
                    try:
                        # Gunakan sb_admin (service_role key) agar bisa DELETE meski RLS aktif
                        sb_admin.table('bukti_dukung').delete().eq('id', doc['id']).execute()
                        # Supabase v2 mengembalikan res.data = [] saat DELETE berhasil — ini normal
                        # Cukup pastikan tidak ada exception, lalu rerun
                        st.success("✅ Data berhasil dihapus!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal menghapus: {str(e)}")

# ========== MAIN ROUTING ==========

def main():
    if st.session_state.auth_role == "opd":
        opd_dashboard()
    elif st.session_state.auth_role == "admin":
        admin_dashboard()
    else:
        if st.session_state.show_login:
            login_page()
        else:
            landing_page()

if __name__ == "__main__":
    main()