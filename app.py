import streamlit as st
import requests
import io
from pathlib import Path
from datetime import datetime
import json
import os
from supabase import create_client, Client
from PIL import Image
import fitz  # PyMuPDF
from fpdf import FPDF
import gdown
import re

# ========== KONFIGURASI ==========
SUPABASE_URL = os.getenv("SUPABASE_URL", "GANTI_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "GANTI_SUPABASE_ANON_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # ganti password
KABUPATEN = "Kabupaten Pesawaran"
TOTAL_OPD = 14

OPD_LIST = [
    "Dinas Kesehatan", "Dinas Kependudukan dan Pencatatan Sipil",
    "Dinas Pendidikan", "Dinas Pekerjaan Umum", "Bappeda",
    "Dinas Pertanian", "Dinas Sosial", "Dinas Komunikasi dan Informatika",
    "Dinas Perdagangan", "Dinas Lingkungan Hidup", "Dinas Perikanan",
    "Satpol PP", "BPBD", "Dinas Pariwisata"
]

INDIKATOR = [
    {"kode": "10101", "nama": "Tingkat Kematangan Penerapan Standar Data Statistik (SDS)"},
    {"kode": "10201", "nama": "Tingkat Kematangan Penerapan Metadata Statistik"},
    {"kode": "10301", "nama": "Tingkat Kematangan Penerapan Kode Referensi dan Data Induk"},
    {"kode": "10401", "nama": "Tingkat Kematangan Penerapan Data Prioritas"},
    {"kode": "20101", "nama": "Tingkat Kelengkapan Metadata Kegiatan Statistik"},
    {"kode": "20201", "nama": "Tingkat Ketersediaan Data Statistik Sektoral"},
]
# ==================================

# Page config
st.set_page_config(
    page_title="Sistem Rekap Bukti Dukung SDI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi Supabase
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---> PERBAIKAN: Pulihkan sesi auth Supabase agar Streamlit tidak lupa status login <---
if 'sb_access_token' in st.session_state and 'sb_refresh_token' in st.session_state:
    try:
        sb.auth.set_session(st.session_state.sb_access_token, st.session_state.sb_refresh_token)
    except Exception:
        pass # Abaikan jika token expired, user akan diminta login ulang

# Setup folders
Path("temp_pdfs").mkdir(exist_ok=True)
Path("temp_screenshots").mkdir(exist_ok=True)

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #F5F3EE;}
    .stButton>button {
        background-color: #2D5A3D;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {background-color: #1F4029;}
    h1 {color: #2D5A3D; font-family: 'Georgia', serif;}
    .doc-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #DDD9D0;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #DDD9D0;
        text-align: center;
    }
    .stat-num {font-size: 2rem; font-weight: bold; color: #2D5A3D;}
    .stat-label {font-size: 0.9rem; color: #6B6860;}
</style>
""", unsafe_allow_html=True)

# Helper functions
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
        raise ValueError("Link Google Drive tidak valid")
    
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        gdown.download(download_url, output_path, quiet=False)
        return True
    except:
        # Fallback: direct download
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
    """Screenshot halaman tertentu dari PDF, return list PIL Images"""
    screenshots = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in page_numbers:
            if 1 <= page_num <= len(doc):
                page = doc[page_num - 1]  # 0-indexed
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom untuk kualitas
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                screenshots.append({"page": page_num, "image": img})
        doc.close()
        return screenshots
    except Exception as e:
        st.error(f"Error screenshot PDF: {str(e)}")
        return []

def generate_pdf_rekap(docs, title, kabupaten, tahun, catatan=""):
    """Generate PDF rekap dengan thumbnail screenshots"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cover
    pdf.add_page()
    pdf.set_fill_color(45, 90, 61)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 60, '', ln=True)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 10, kabupaten, ln=True, align='C')
    pdf.cell(0, 10, f'Tahun {tahun}', ln=True, align='C')
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(200, 230, 210)
    pdf.cell(0, 80, '', ln=True)
    if catatan:
        pdf.multi_cell(0, 6, catatan, align='L')
    
    # Group by OPD
    opd_groups = {}
    for doc in docs:
        opd = doc['opd_name']
        if opd not in opd_groups:
            opd_groups[opd] = []
        opd_groups[opd].append(doc)
    
    for opd_name, opd_docs in opd_groups.items():
        # OPD Header
        pdf.add_page()
        pdf.set_fill_color(232, 242, 236)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_fill_color(45, 90, 61)
        pdf.rect(0, 0, 210, 50, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 30, '', ln=True)
        pdf.cell(0, 10, opd_name, ln=True, align='C')
        pdf.set_text_color(45, 90, 61)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 20, '', ln=True)
        pdf.cell(0, 10, f'{len(opd_docs)} dokumen', ln=True, align='C')
        
        for doc in opd_docs:
            pdf.add_page()
            pdf.set_text_color(45, 90, 61)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, doc['doc_name'], ln=True)
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"Indikator: {doc['indikator_kode']} - {doc.get('indikator_nama', '')}", ln=True)
            pdf.cell(0, 6, f"Dikirim: {doc['created_at'][:10]}", ln=True)
            if doc.get('notes'):
                pdf.multi_cell(0, 6, f"Catatan: {doc['notes']}")
            pdf.ln(4)
            
            # Halaman penting (tampilkan screenshots jika ada)
            marked_pages = doc.get('marked_pages', [])
            if marked_pages:
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(45, 90, 61)
                pdf.cell(0, 8, f'Halaman Penting ({len(marked_pages)} halaman):', ln=True)
                
                # Load screenshots jika ada
                doc_screenshots = doc.get('screenshots', [])
                if doc_screenshots:
                    y_start = pdf.get_y()
                    x_pos = 15
                    for i, screenshot_data in enumerate(doc_screenshots):
                        if i > 0 and i % 2 == 0:
                            pdf.ln(75)
                            y_start = pdf.get_y()
                            x_pos = 15
                        
                        # Simpan temporary image
                        temp_img_path = f"temp_screenshots/temp_{i}.png"
                        screenshot_data['image'].save(temp_img_path, 'PNG')
                        
                        # Add to PDF
                        pdf.image(temp_img_path, x=x_pos, y=y_start, w=90, h=120)
                        
                        # Label
                        pdf.set_xy(x_pos, y_start + 122)
                        pdf.set_fill_color(45, 90, 61)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font('Arial', 'B', 8)
                        page_info = next((p for p in marked_pages if p['page'] == screenshot_data['page']), {})
                        label = f"Hal. {screenshot_data['page']}"
                        if page_info.get('label'):
                            label += f" - {page_info['label']}"
                        pdf.cell(90, 6, align='C', fill=True, text=label)
                        
                        x_pos += 95
                        
                        # Cleanup
                        Path(temp_img_path).unlink(missing_ok=True)
                else:
                    # No screenshots - just list pages
                    for p in marked_pages:
                        pdf.set_font('Arial', '', 9)
                        pdf.set_text_color(100, 100, 100)
                        lbl = f"- Halaman {p['page']}"
                        if p.get('label'):
                            lbl += f": {p['label']}"
                        pdf.cell(0, 5, lbl, ln=True)
            
            pdf.ln(4)
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color(26, 86, 160)
            pdf.cell(0, 5, f"Link: {doc.get('drive_link', '')}", ln=True)
    
    # Output
    output_path = f"temp_pdfs/rekap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_opd' not in st.session_state:
    st.session_state.user_opd = None

# Authentication
def login_page():
    st.title("🔐 Login ke Sistem Rekap SDI")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        role = st.radio("Login sebagai:", ["OPD", "Admin Kominfo"], horizontal=True)
        
        if role == "OPD":
            username = st.text_input("Username OPD", placeholder="cth: dinkes_pesawaran")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                try:
                    # Cari user di opd_users
                    result = sb.table('opd_users').select('*').eq('username', username).execute()
                    if result.data and len(result.data) > 0:
                        user = result.data[0]
                        # Login via Supabase Auth
                        auth_result = sb.auth.sign_in_with_password({
                            "email": user['email'],
                            "password": password
                        })
                        if auth_result.user:
                            st.session_state.authenticated = True
                            st.session_state.user_role = "opd"
                            st.session_state.user_opd = user['opd_name']
                            st.session_state.username = username
                            
                            # ---> PERBAIKAN: Simpan token ke session state Streamlit <---
                            st.session_state.sb_access_token = auth_result.session.access_token
                            st.session_state.sb_refresh_token = auth_result.session.refresh_token
                            
                            st.rerun()
                        else:
                            st.error("Password salah")
                    else:
                        st.error("Username tidak ditemukan")
                except Exception as e:
                    st.error(f"Login gagal: {str(e)}")
        
        else:  # Admin
            admin_pw = st.text_input("Password Admin", type="password")
            
            if st.button("Login Admin", use_container_width=True):
                if admin_pw == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else:
                    st.error("Password admin salah")

# OPD Dashboard
def opd_dashboard():
    st.title(f"📤 Upload Bukti Dukung - {st.session_state.user_opd}")
    
    with st.sidebar:
        st.markdown("### 👤 Informasi")
        st.info(f"**OPD:** {st.session_state.user_opd}")
        
        # ---> PERBAIKAN LOGOUT OPD <---
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            if 'sb_access_token' in st.session_state:
                del st.session_state['sb_access_token']
            if 'sb_refresh_token' in st.session_state:
                del st.session_state['sb_refresh_token']
            try:
                sb.auth.sign_out()
            except:
                pass
            st.rerun()
    
    # Form Upload
    st.markdown("### 📝 Form Upload Dokumen")
    
    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            indikator_kode = st.selectbox(
                "Kode Indikator *",
                options=[i['kode'] for i in INDIKATOR],
                format_func=lambda x: f"{x} - {next(i['nama'] for i in INDIKATOR if i['kode']==x)[:50]}..."
            )
        
        with col2:
            doc_name = st.text_input("Nama Dokumen *", placeholder="cth: Profil Kesehatan 2023")
        
        drive_link = st.text_input(
            "Link Google Drive *",
            placeholder="https://drive.google.com/file/d/...",
            help="Upload PDF ke Google Drive Anda, ubah akses ke 'Anyone with the link', lalu paste link di sini"
        )
        
        st.markdown("**Tandai Halaman Penting**")
        st.caption("Masukkan nomor halaman yang paling membuktikan (dipisah koma, cth: 1,3,7)")
        
        page_numbers_str = st.text_input("Nomor Halaman", placeholder="1,3,7")
        page_labels_str = st.text_input(
            "Keterangan per Halaman (opsional, dipisah | )",
            placeholder="Cover|Tabel data|Tanda tangan",
            help="Pisahkan dengan | sesuai urutan halaman"
        )
        
        notes = st.text_area("Catatan Tambahan (opsional)", placeholder="Catatan untuk Kominfo...")
        
        submitted = st.form_submit_button("📨 Kirim Bukti Dukung", use_container_width=True)
        
        if submitted:
            if not doc_name or not drive_link:
                st.error("Nama dokumen dan link Drive wajib diisi!")
            elif not page_numbers_str:
                st.error("Minimal tandai 1 halaman penting!")
            else:
                # Parse page numbers
                try:
                    page_nums = [int(p.strip()) for p in page_numbers_str.split(',')]
                    page_labels = page_labels_str.split('|') if page_labels_str else []
                    
                    marked_pages = []
                    for i, pn in enumerate(page_nums):
                        marked_pages.append({
                            "page": pn,
                            "label": page_labels[i].strip() if i < len(page_labels) else ""
                        })
                    
                    # Download PDF dan screenshot
                    with st.spinner("📥 Mengunduh PDF dari Google Drive..."):
                        pdf_path = f"temp_pdfs/{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        success = download_pdf_from_drive(drive_link, pdf_path)
                    
                    if not success:
                        st.error("❌ Gagal mengunduh PDF. Pastikan link sudah diset 'Anyone with the link' di Google Drive")
                    else:
                        with st.spinner("📸 Screenshot halaman penting..."):
                            screenshots = screenshot_pdf_pages(pdf_path, page_nums)
                        
                        if not screenshots:
                            st.warning("⚠️ Tidak bisa screenshot otomatis, tapi dokumen tetap akan disimpan")
                        
                        # Simpan ke database
                        indikator_obj = next(i for i in INDIKATOR if i['kode'] == indikator_kode)
                        
                        data = {
                            "opd_name": st.session_state.user_opd,
                            "indikator_kode": indikator_kode,
                            "indikator_nama": indikator_obj['nama'],
                            "doc_name": doc_name,
                            "drive_link": drive_link,
                            "marked_pages": marked_pages,
                            "notes": notes,
                            "submitted_by": st.session_state.username,
                            "status": "pending",
                            "kabupaten": KABUPATEN,
                            "has_screenshots": len(screenshots) > 0,
                            "screenshot_count": len(screenshots)
                        }
                        
                        result = sb.table('bukti_dukung').insert(data).execute()
                        
                        # Cleanup temp file
                        Path(pdf_path).unlink(missing_ok=True)
                        
                        st.success("✅ Dokumen berhasil dikirim!")
                        st.balloons()
                        
                        if screenshots:
                            st.info(f"✨ Berhasil screenshot {len(screenshots)} halaman secara otomatis")
                            with st.expander("🔍 Preview Screenshot"):
                                cols = st.columns(min(3, len(screenshots)))
                                for i, ss in enumerate(screenshots):
                                    with cols[i % len(cols)]:
                                        st.image(ss['image'], caption=f"Halaman {ss['page']}", use_container_width=True)
                        
                except ValueError:
                    st.error("Format nomor halaman salah. Gunakan angka dipisah koma (cth: 1,3,7)")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Admin Dashboard
def admin_dashboard():
    st.title("🎛️ Dashboard Admin Kominfo")
    
    with st.sidebar:
        st.markdown("### 🔧 Menu")
        menu = st.radio("Pilih Menu:", ["📊 Dokumen Masuk", "👥 Kelola Akun OPD"], label_visibility="collapsed")
        
        st.markdown("---")
        
        # ---> PERBAIKAN LOGOUT ADMIN <---
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            if 'sb_access_token' in st.session_state:
                del st.session_state['sb_access_token']
            if 'sb_refresh_token' in st.session_state:
                del st.session_state['sb_refresh_token']
            try:
                sb.auth.sign_out()
            except:
                pass
            st.rerun()
    
    if menu == "📊 Dokumen Masuk":
        admin_dokumen_page()
    else:
        admin_akun_page()

def admin_dokumen_page():
    # Load all documents
    result = sb.table('bukti_dukung').select('*').order('created_at', desc=True).execute()
    docs = result.data if result.data else []
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{len(docs)}</div>
            <div class="stat-label">Total Dokumen</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        unique_opd = len(set(d['opd_name'] for d in docs))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{unique_opd}/{TOTAL_OPD}</div>
            <div class="stat-label">OPD Sudah Upload</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pending = len([d for d in docs if d['status'] == 'pending'])
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{pending}</div>
            <div class="stat-label">Pending Review</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        has_ss = len([d for d in docs if d.get('has_screenshots')])
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{has_ss}</div>
            <div class="stat-label">Ada Screenshot</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filter
    st.markdown("### 🔍 Filter & Generate")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        filter_indikator = st.selectbox(
            "Filter Indikator",
            ["Semua"] + [i['kode'] for i in INDIKATOR],
            format_func=lambda x: f"Semua Indikator" if x == "Semua" else f"{x} - {next((i['nama'] for i in INDIKATOR if i['kode']==x), '')[:40]}..."
        )
    
    with col2:
        filter_opd = st.selectbox("Filter OPD", ["Semua"] + sorted(set(d['opd_name'] for d in docs)))
    
    with col3:
        filter_status = st.selectbox("Status", ["Semua", "Pending", "Reviewed"])
    
    # Apply filters
    filtered_docs = docs
    if filter_indikator != "Semua":
        filtered_docs = [d for d in filtered_docs if d['indikator_kode'] == filter_indikator]
    if filter_opd != "Semua":
        filtered_docs = [d for d in filtered_docs if d['opd_name'] == filter_opd]
    if filter_status != "Semua":
        filtered_docs = [d for d in filtered_docs if d['status'].lower() == filter_status.lower()]
    
    # Generate button
    if filter_indikator != "Semua" and len(filtered_docs) > 0:
        st.markdown("### 📄 Generate Rekap")
        
        col_gen1, col_gen2 = st.columns(2)
        
        with col_gen1:
            if st.button("🔴 Generate PDF Rekap", use_container_width=True, type="primary"):
                with st.spinner("⏳ Sedang membuat rekap PDF..."):
                    # Download & screenshot semua PDF yang belum ada screenshotnya
                    for doc in filtered_docs:
                        if not doc.get('has_screenshots') and doc.get('drive_link'):
                            try:
                                pdf_path = f"temp_pdfs/temp_{doc['id']}.pdf"
                                if download_pdf_from_drive(doc['drive_link'], pdf_path):
                                    page_nums = [p['page'] for p in doc.get('marked_pages', [])]
                                    screenshots = screenshot_pdf_pages(pdf_path, page_nums)
                                    doc['screenshots'] = screenshots
                                    Path(pdf_path).unlink(missing_ok=True)
                            except:
                                pass
                    
                    # Generate PDF
                    title = f"Rekap Bukti Dukung Indikator {filter_indikator}"
                    tahun = datetime.now().year
                    
                    pdf_path = generate_pdf_rekap(
                        filtered_docs,
                        title,
                        KABUPATEN,
                        tahun,
                        f"Dokumen ini berisi {len(filtered_docs)} bukti dukung dari {len(set(d['opd_name'] for d in filtered_docs))} OPD."
                    )
                    
                    with open(pdf_path, 'rb') as f:
                        st.download_button(
                            "⬇️ Download PDF Rekap",
                            f,
                            file_name=f"Rekap_{filter_indikator}_{tahun}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    st.success(f"✅ Rekap PDF berhasil dibuat! Total {len(filtered_docs)} dokumen")
    
    # Documents list
    st.markdown("### 📚 Daftar Dokumen")
    
    if len(filtered_docs) == 0:
        st.info("Belum ada dokumen untuk filter ini")
    else:
        for doc in filtered_docs:
            with st.container():
                st.markdown(f"""
                <div class="doc-card">
                    <h4>{doc['doc_name']}</h4>
                    <p style="color: #6B6860; font-size: 0.9rem;">
                        <strong>OPD:</strong> {doc['opd_name']} | 
                        <strong>Indikator:</strong> {doc['indikator_kode']} | 
                        <strong>Status:</strong> {doc['status']} | 
                        <strong>Dikirim:</strong> {doc['created_at'][:10]}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col_doc1, col_doc2, col_doc3, col_doc4 = st.columns([3, 2, 1, 1])
                
                with col_doc1:
                    marked = doc.get('marked_pages', [])
                    if marked:
                        st.caption(f"📌 Halaman: {', '.join(str(p['page']) for p in marked)}")
                    if doc.get('notes'):
                        st.caption(f"💬 {doc['notes'][:100]}{'...' if len(doc['notes']) > 100 else ''}")
                
                with col_doc2:
                    if doc.get('drive_link'):
                        st.link_button("🔗 Buka di Drive", doc['drive_link'], use_container_width=True)
                
                with col_doc3:
                    if doc['status'] == 'pending':
                        if st.button("✅ Review", key=f"rev_{doc['id']}", use_container_width=True):
                            sb.table('bukti_dukung').update({"status": "reviewed"}).eq('id', doc['id']).execute()
                            st.rerun()
                
                with col_doc4:
                    if st.button("🗑️ Hapus", key=f"del_{doc['id']}", use_container_width=True):
                        sb.table('bukti_dukung').delete().eq('id', doc['id']).execute()
                        st.rerun()
                
                st.markdown("---")

def admin_akun_page():
    st.markdown("### 👥 Kelola Akun OPD")
    
    # Load existing accounts
    result = sb.table('opd_users').select('*').order('opd_name').execute()
    akun_list = result.data if result.data else []
    
    st.info(f"**Total akun:** {len(akun_list)} dari {len(OPD_LIST)} OPD")
    
    # Form tambah akun
    with st.expander("➕ Tambah Akun OPD Baru", expanded=len(akun_list) == 0):
        with st.form("form_akun"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_opd = st.selectbox("Nama OPD", OPD_LIST)
                new_username = st.text_input("Username", placeholder="cth: dinkes_pesawaran")
            
            with col2:
                new_email = st.text_input("Email Internal", placeholder="cth: dinkes@pesawaran.internal")
                new_password = st.text_input("Password", type="password", placeholder="Min. 8 karakter")
            
            submit_akun = st.form_submit_button("Buat Akun", use_container_width=True)
            
            if submit_akun:
                if not new_username or not new_email or not new_password:
                    st.error("Semua field wajib diisi!")
                elif len(new_password) < 8:
                    st.error("Password minimal 8 karakter!")
                else:
                    try:
                        # Sign up via Supabase Auth
                        auth_result = sb.auth.sign_up({
                            "email": new_email,
                            "password": new_password
                        })
                        
                        if auth_result.user:
                            # Simpan profil di opd_users
                            sb.table('opd_users').insert({
                                "user_id": auth_result.user.id,
                                "username": new_username,
                                "email": new_email,
                                "opd_name": new_opd
                            }).execute()
                            
                            st.success(f"✅ Akun {new_username} berhasil dibuat!")
                            st.rerun()
                        else:
                            st.error("Gagal membuat akun. Email mungkin sudah terdaftar.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.info("💡 Jika error, coba buat user manual di Supabase Dashboard → Authentication → Users")
    
    # List akun
    st.markdown("### 📋 Daftar Akun OPD")
    
    if len(akun_list) == 0:
        st.info("Belum ada akun OPD. Buat akun di atas.")
    else:
        for akun in akun_list:
            col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 2, 1])
            
            with col_a1:
                st.markdown(f"**{akun['opd_name']}**")
            with col_a2:
                st.caption(f"👤 {akun['username']}")
            with col_a3:
                st.caption(f"📧 {akun['email']}")
            with col_a4:
                if st.button("🗑️", key=f"del_akun_{akun['id']}", help="Hapus akun"):
                    sb.table('opd_users').delete().eq('id', akun['id']).execute()
                    st.rerun()

# Main routing
def main():
    if not st.session_state.authenticated:
        login_page()
    else:
        if st.session_state.user_role == "opd":
            opd_dashboard()
        elif st.session_state.user_role == "admin":
            admin_dashboard()

if __name__ == "__main__":
    main()