# Sistem Rekap Bukti Dukung SDI
**Streamlit + Supabase + Auto Screenshot PDF**

---

## 🎯 Fitur Utama

✅ **Auto-screenshot halaman PDF** — Python otomatis ambil screenshot halaman yang ditandai OPD
✅ **Generate PDF rekap 1 klik** — dengan thumbnail halaman penting dari semua OPD
✅ **Login username/password** — tanpa Google OAuth
✅ **Upload via Google Drive** — OPD upload sendiri, Streamlit download & screenshot
✅ **Dashboard lengkap** — statistik, filter, review dokumen
✅ **Kelola akun OPD** — admin buat username/password untuk setiap OPD
✅ **Deploy gratis** — Streamlit Cloud (online) atau localhost

---

## 🧩 Komponen

| Komponen | Fungsi | Biaya |
|---|---|---|
| **Streamlit Cloud** | Hosting aplikasi web Python | Gratis |
| **Supabase** | Database + autentikasi | Gratis |
| **Google Drive** | OPD simpan PDF, sistem download otomatis | Gratis |
| **PyMuPDF** | Screenshot halaman PDF jadi gambar | Open source |

---

## 📋 Langkah Setup

### 1. Setup Supabase (sama seperti sebelumnya)

1. Buka **https://supabase.com** → buat project baru
2. **SQL Editor** → jalankan SQL berikut:

```sql
-- Tabel profil akun OPD
create table opd_users (
  id uuid default gen_random_uuid() primary key,
  user_id text,
  username text unique not null,
  email text not null,
  opd_name text not null,
  created_at timestamptz default now()
);

-- Tabel dokumen bukti dukung
create table bukti_dukung (
  id uuid default gen_random_uuid() primary key,
  created_at timestamptz default now(),
  opd_name text not null,
  indikator_kode text not null,
  indikator_nama text,
  doc_name text not null,
  drive_link text,
  marked_pages jsonb default '[]',
  notes text,
  submitted_by text,
  status text default 'pending',
  kabupaten text,
  has_screenshots boolean default false,
  screenshot_count int default 0
);

-- Row Level Security
alter table opd_users enable row level security;
alter table bukti_dukung enable row level security;

create policy "opd_users_all" on opd_users for all to authenticated using (true) with check (true);
create policy "opd_users_select_anon" on opd_users for select to anon using (true);
create policy "bukti_dukung_all" on bukti_dukung for all to authenticated using (true) with check (true);
```

3. **Settings** → **API** → salin:
   - **Project URL**
   - **anon / public key**

4. **Authentication** → **Providers** → **Email** → pastikan ON
5. **Authentication** → **Settings** → matikan **"Enable email confirmations"**

---

### 2. Setup Streamlit Cloud (Deploy Online)

#### A. Buat Repository GitHub

1. Buka **https://github.com** → login
2. **New repository**:
   - Name: `rekap-sdi-streamlit`
   - Public
   - ✅ Add README
3. Upload file:
   - `app.py`
   - `requirements.txt`
   - `README.md` (file ini)

#### B. Deploy ke Streamlit Cloud

1. Buka **https://share.streamlit.io** → login dengan GitHub
2. Klik **New app**
3. Pilih:
   - Repository: `rekap-sdi-streamlit`
   - Branch: `main`
   - Main file: `app.py`
4. **Advanced settings** → klik **Secrets**
5. Paste konfigurasi berikut (ganti dengan nilai Anda):

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
ADMIN_PASSWORD = "passwordKominfo2024"
```

6. Klik **Deploy**
7. Tunggu 2-3 menit → app akan jalan di URL: `https://NAMA-APP.streamlit.app`

---

### 3. Setup Localhost (Alternatif — Jalankan di Komputer Sendiri)

Jika tidak ingin deploy online, bisa jalankan lokal:

```bash
# 1. Install Python 3.9+ dari python.org

# 2. Buat folder project
mkdir rekap-sdi
cd rekap-sdi

# 3. Simpan file app.py, requirements.txt

# 4. Edit app.py baris 13-15, ganti dengan nilai Supabase Anda:
# SUPABASE_URL = "https://xxxxx.supabase.co"
# SUPABASE_KEY = "eyJhbGci..."
# ADMIN_PASSWORD = "admin123"

# 5. Install dependencies
pip install -r requirements.txt

# 6. Jalankan aplikasi
streamlit run app.py
```

Buka browser: **http://localhost:8501**

---

## 🚀 Cara Pakai

### Untuk Admin Kominfo:

1. Buka app → **Login sebagai Admin Kominfo**
2. Masukkan password admin
3. **Tab "Kelola Akun OPD"** → buat akun untuk setiap OPD:
   - Pilih nama OPD
   - Username: `dinkes_pesawaran` (huruf kecil, underscore)
   - Email: `dinkes@pesawaran.internal` (tidak harus email aktif)
   - Password: min. 8 karakter
4. Bagikan username + password ke masing-masing OPD

### Untuk OPD:

1. Buka app → **Login sebagai OPD**
2. Masukkan username & password dari Kominfo
3. **Form Upload Dokumen**:
   - Pilih indikator
   - Nama dokumen
   - Upload PDF ke **Google Drive Anda** → Share → **"Anyone with the link"** → Copy link → paste
   - Tandai halaman penting (pisah koma): `1,3,7`
   - (Opsional) Keterangan per halaman (pisah `|`): `Cover|Tabel|Tanda tangan`
   - Klik **Kirim**
4. Sistem akan:
   - Download PDF dari Drive Anda
   - **Auto-screenshot halaman yang ditandai**
   - Simpan ke database
   - Tampilkan preview screenshot

### Generate Rekap:

1. Admin login
2. **Tab "Dokumen Masuk"**
3. Filter indikator yang ingin direkap
4. Klik **🔴 Generate PDF Rekap**
5. Sistem akan:
   - Download semua PDF dari Drive
   - Screenshot halaman penting (jika belum ada)
   - Susun jadi 1 PDF rekap lengkap dengan thumbnail
   - File otomatis terunduh

---

## 📸 Screenshot Otomatis

**Cara kerjanya:**

1. OPD paste link Google Drive → tandai halaman (cth: `1,3,7`)
2. Saat OPD klik **Kirim**:
   - Streamlit download PDF dari Drive (pakai library `gdown`)
   - PyMuPDF buka PDF → ekstrak halaman 1, 3, 7
   - Convert jadi gambar PNG (resolusi tinggi)
   - Simpan metadata ke database: `has_screenshots: true`
3. Saat Admin generate rekap:
   - Streamlit ambil semua screenshot yang sudah tersimpan
   - Susun jadi thumbnail di PDF rekap
   - Tambahkan label halaman + keterangan

**Keunggulan vs JavaScript di browser:**
- ✅ Python bisa download langsung dari Google Drive
- ✅ PyMuPDF render PDF server-side (tidak ada batasan CORS)
- ✅ Screenshot resolusi tinggi, hasil profesional
- ✅ Bisa batch processing banyak PDF sekaligus

---

## 🔧 Troubleshooting

### "Error download PDF dari Google Drive"

**Solusi:**
1. Pastikan link sudah diset **"Anyone with the link"** di Google Drive
2. Cek link mengandung `/file/d/` atau `id=`
3. Coba buka link di browser incognito — harus bisa download tanpa login

### "Gagal membuat akun OPD"

**Solusi manual via Supabase Dashboard:**
1. Supabase → **Authentication** → **Users** → **Add user**
2. Isi email & password → **Create User**
3. Salin **User UID**
4. **Table Editor** → `opd_users` → **Insert row**:
   - `user_id`: paste UID
   - `username`: `dinkes_pesawaran`
   - `email`: sama dengan di step 2
   - `opd_name`: `Dinas Kesehatan`

### "Screenshot gagal / tidak muncul"

Kemungkinan:
- PDF dilindungi password → minta OPD upload versi tanpa password
- PDF corrupt → minta OPD upload ulang
- File terlalu besar (>100MB) → minta OPD compress dulu

---

## 💡 Kelebihan Sistem Ini

✅ **Tidak perlu Google Cloud Console** — langsung download dari Drive public link
✅ **Screenshot otomatis server-side** — tidak tergantung browser user
✅ **Deploy gratis selamanya** — Streamlit Cloud + Supabase free tier
✅ **Bisa diakses dari mana saja** — online 24/7
✅ **Satu aplikasi untuk semua** — OPD & Admin dalam 1 app
✅ **Database cloud** — data aman, tersinkron
✅ **Bisa untuk banyak kabupaten/kota** — tinggal ganti CONFIG

---

## 📝 Catatan Penting

1. **Streamlit Cloud gratis** tapi ada limit:
   - 1 app bisa idle otomatis jika tidak diakses 7 hari
   - Maksimal 1GB RAM (cukup untuk sistem ini)
   - Bisa upgrade ke paid jika perlu

2. **Supabase gratis** tapi ada limit:
   - 500MB database (cukup untuk ribuan dokumen)
   - 50,000 monthly active users
   - 2GB bandwidth/bulan

3. **Alternative deploy:**
   - Heroku (gratis dengan kartu kredit)
   - Railway (gratis $5/bulan credit)
   - Google Cloud Run (gratis tier tersedia)
   - VPS sendiri (DigitalOcean, Vultr, dll)

4. **Backup data:**
   - Export dari Supabase → **Database** → **Backups**
   - Download manual jadi SQL file

---

## 🎓 Pengembangan Lanjutan

Bisa ditambahkan:
- Export rekap ke Word (.docx) dengan `python-docx`
- Email notifikasi ke Kominfo saat OPD upload (pakai SendGrid/Mailgun)
- Dashboard analytics dengan chart progress per OPD
- OCR untuk PDF hasil scan (pakai `pytesseract`)
- Multi-tenant untuk beberapa kabupaten/kota dalam 1 app

---

*Sistem ini dibuat dengan Python + Streamlit + Supabase. Semua gratis dan open source.*
