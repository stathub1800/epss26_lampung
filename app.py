import streamlit as st
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
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "kominfo123") 

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
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    sb = init_supabase()
except Exception as e:
    st.error("Gagal koneksi ke Supabase. Cek URL dan KEY.")

# Setup folders untuk temp files saat proses generate
Path("temp_pdfs").mkdir(exist_ok=True)
Path("temp_screenshots").mkdir(exist_ok=True)

# Page config
st.set_page_config(page_title="Evaluasi SDI Provinsi Lampung", page_icon="📊", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button { background-color: #2b5c8f; color: white; border-radius: 6px; }
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
        
        # Tulis ke PDF bahwa sedang memproses (ini untuk UX jika text di render)
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
                
                if pdf.get_y() > 220: # Auto page break jika space tinggal sedikit
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
                    
                    # Hitung rasio agar proporsional di A4 (lebar max A4 = ~190mm usable)
                    img_w, img_h = img_data['image'].size
                    target_w = 160
                    target_h = (target_w / img_w) * img_h
                    
                    # Jika gambar kepanjangan, kecilkan lagi atau auto page break
                    if pdf.get_y() + target_h > 280:
                        pdf.add_page()
                    
                    # Pusatkan gambar
                    x_pos = (210 - target_w) / 2
                    pdf.image(temp_img_path, x=x_pos, y=pdf.get_y(), w=target_w, h=target_h)
                    pdf.set_y(pdf.get_y() + target_h + 5)
                    
                    # Cleanup image file
                    Path(temp_img_path).unlink(missing_ok=True)
                else:
                    pdf.set_text_color(255, 0, 0)
                    pdf.cell(0, 6, f"[Gagal mengambil screenshot Halaman {hal}]", ln=True)
                    pdf.set_text_color(0, 0, 0)
            
            # Cleanup PDF file
            Path(pdf_path).unlink(missing_ok=True)
            
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(0, 6, "Gagal mengunduh file PDF dari Google Drive. Pastikan akses link bersifat 'Siapa saja yang memiliki link' (Public).")
            pdf.set_text_color(0, 0, 0)

    # Output file FPDF
    output_filename = f"temp_pdfs/Rekap_{indikator_kode}_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(output_filename)
    return output_filename

# ========== HALAMAN OTENTIKASI ==========

if 'auth_role' not in st.session_state:
    st.session_state.auth_role = None

def login_page():
    st.markdown("<h1 style='text-align: center;'>Portal Evaluasi SDI<br>Provinsi Lampung</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role = st.selectbox("Masuk Sebagai:", ["Dinas (Lokus)", "Walidata (Kominfo)"])
        
        if role == "Dinas (Lokus)":
            opd = st.selectbox("Pilih OPD", OPD_LIST)
            password = st.text_input("Password", type="password", placeholder="Masukkan password OPD")
            
            if st.button("Masuk", use_container_width=True):
                # Validasi password berdasarkan OPD yang dipilih
                if opd in OPD_PASSWORDS and password == OPD_PASSWORDS[opd]:
                    st.session_state.auth_role = "opd"
                    st.session_state.opd_name = opd
                    st.rerun()
                else:
                    st.error("Password salah untuk instansi tersebut!")
                    
        elif role == "Walidata (Kominfo)":
            password = st.text_input("Password Admin", type="password")
            if st.button("Masuk Walidata", use_container_width=True):
                if password == ADMIN_PASSWORD:
                    st.session_state.auth_role = "admin"
                    st.rerun()
                else:
                    st.error("Password admin salah!")

# ========== DASHBOARD OPD ==========

def opd_dashboard():
    st.title("📤 Upload Bukti Dukung")
    st.info(f"Login sebagai: **{st.session_state.opd_name}**")
    
    with st.sidebar:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth_role = None
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
                # Parsing halaman_input
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
                
                # Insert data ke Supabase
                indikator_nama = next(i['nama'] for i in INDIKATOR if i['kode']==indikator_kode)
                data = {
                    "opd_name": st.session_state.opd_name,
                    "indikator_kode": indikator_kode,
                    "indikator_nama": indikator_nama,
                    "doc_name": doc_name,
                    "drive_link": drive_link,
                    "marked_pages": marked_pages
                }
                
                sb.table('bukti_dukung').insert(data).execute()
                st.success("✅ Bukti dukung berhasil disimpan!")
                st.balloons()

# ========== DASHBOARD ADMIN / WALIDATA ==========

def admin_dashboard():
    st.title("🎛️ Ruang Kerja Walidata (Kominfo)")
    
    with st.sidebar:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth_role = None
            st.rerun()
            
    st.write("### 📄 Rekapitulasi Berdasarkan Indikator")
    
    # Ambil semua data
    result = sb.table('bukti_dukung').select('*').order('created_at', desc=True).execute()
    semua_dokumen = result.data if result.data else []
    
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        pilih_indikator = st.selectbox(
            "Pilih Indikator untuk di-Rekap",
            [i['kode'] for i in INDIKATOR],
            format_func=lambda x: f"{x} - {next(i['nama'] for i in INDIKATOR if i['kode']==x)}"
        )
    
    # Filter dokumen sesuai indikator terpilih
    docs_filtered = [d for d in semua_dokumen if d['indikator_kode'] == pilih_indikator]
    
    with col_filter2:
        st.write("") # Spacer
        st.write("")
        if st.button("🎯 GENERATE REKAP PDF", type="primary", use_container_width=True):
            if not docs_filtered:
                st.warning("Belum ada OPD yang mengupload bukti dukung untuk indikator ini.")
            else:
                with st.spinner("⏳ Sedang memproses... Mengunduh PDF, memotong halaman, dan menyusun laporan. Harap tunggu..."):
                    indikator_nama = next(i['nama'] for i in INDIKATOR if i['kode']==pilih_indikator)
                    
                    try:
                        # Fungsi ini akan melakukan pekerjaan berat secara real-time
                        pdf_path = create_pdf_rekap(docs_filtered, pilih_indikator, indikator_nama)
                        
                        # Baca file PDF untuk tombol download
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
                        
                # Tombol hapus
                if st.button("🗑️ Hapus Evaluasi Ini", key=f"del_{doc['id']}"):
                    sb.table('bukti_dukung').delete().eq('id', doc['id']).execute()
                    st.rerun()

# ========== MAIN ROUTING ==========

def main():
    if st.session_state.auth_role == "opd":
        opd_dashboard()
    elif st.session_state.auth_role == "admin":
        admin_dashboard()
    else:
        login_page()

if __name__ == "__main__":
    main()