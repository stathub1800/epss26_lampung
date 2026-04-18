# Sistem Rekap Bukti Dukung SDI
**Panduan Setup Lengkap — Tidak Perlu Coding**

---

## Gambaran Sistem

| Komponen | Fungsi | Biaya |
|---|---|---|
| **GitHub Pages** | Hosting semua halaman web | Gratis |
| **Supabase** | Simpan metadata dokumen (nama OPD, indikator, nomor halaman) | Gratis |
| **Google Drive** | Simpan file PDF asli dokumen OPD | Gratis |
| **Google OAuth** | Login akun Google untuk OPD | Gratis |

---

## Langkah 1: Buat Akun Supabase

1. Buka **https://supabase.com** → klik **Start your project**
2. Daftar dengan akun GitHub atau email
3. Klik **New Project**
4. Isi:
   - **Name**: `rekap-sdi-pesawaran` (atau nama kabupaten Anda)
   - **Database Password**: buat password yang kuat, simpan di tempat aman
   - **Region**: pilih **Southeast Asia (Singapore)**
5. Tunggu ~2 menit sampai project siap

### 1a. Salin URL dan Key Supabase

1. Di dashboard Supabase, klik **Settings** (ikon roda gigi di sidebar kiri)
2. Klik **API**
3. Salin dua nilai ini:
   - **Project URL** → contoh: `https://abcxyz.supabase.co`
   - **anon / public key** → string panjang diawali `eyJ...`
4. Simpan dua nilai ini, akan dipakai di langkah 4

### 1b. Buat Tabel Database

1. Di Supabase, klik **SQL Editor** (ikon terminal di sidebar)
2. Klik **New query**
3. Copy-paste SQL berikut, lalu klik **Run**:

```sql
create table bukti_dukung (
  id uuid default gen_random_uuid() primary key,
  created_at timestamptz default now(),
  opd_name text not null,
  indikator_kode text not null,
  indikator_nama text,
  doc_name text not null,
  drive_file_id text,
  drive_view_link text,
  marked_pages jsonb default '[]',
  notes text,
  submitted_by_email text,
  submitted_by_name text,
  status text default 'pending',
  kabupaten text
);

-- Izinkan akses dari web (Row Level Security)
alter table bukti_dukung enable row level security;

create policy "Allow insert for authenticated"
on bukti_dukung for insert
to authenticated
with check (true);

create policy "Allow select for authenticated"
on bukti_dukung for select
to authenticated
using (true);

create policy "Allow update for authenticated"
on bukti_dukung for update
to authenticated
using (true);
```

4. Klik **Run** — harus muncul pesan "Success"

### 1c. Aktifkan Google Login di Supabase

1. Di Supabase, klik **Authentication** → **Providers**
2. Cari **Google** → klik untuk expand → aktifkan toggle **Enable**
3. Anda perlu **Client ID** dan **Client Secret** dari Google — lanjut ke Langkah 2

---

## Langkah 2: Setup Google Cloud (OAuth + Drive)

### 2a. Buat Project Google Cloud

1. Buka **https://console.cloud.google.com**
2. Login dengan akun Google Kominfo
3. Klik dropdown project di atas → **New Project**
4. Nama: `Rekap SDI Pesawaran` → klik **Create**

### 2b. Aktifkan Google Drive API

1. Di menu kiri: **APIs & Services** → **Library**
2. Cari `Google Drive API` → klik → klik **Enable**

### 2c. Buat OAuth Credentials

1. Di menu kiri: **APIs & Services** → **Credentials**
2. Klik **+ Create Credentials** → pilih **OAuth client ID**
3. Jika diminta configure consent screen:
   - Pilih **External** → **Create**
   - Isi **App name**: `Rekap Bukti Dukung SDI`
   - Isi **User support email**: email Kominfo Anda
   - Isi **Developer contact**: email Kominfo Anda
   - Klik **Save and Continue** sampai selesai
4. Kembali buat OAuth client ID:
   - **Application type**: pilih **Web application**
   - **Name**: `Rekap SDI Web`
   - Di **Authorized JavaScript origins**, tambahkan:
     ```
     https://NAMA_AKUN_GITHUB_ANDA.github.io
     http://localhost
     ```
   - Di **Authorized redirect URIs**, tambahkan URL dari Supabase:
     Formatnya: `https://SUPABASE_PROJECT_ID.supabase.co/auth/v1/callback`
     > Cari SUPABASE_PROJECT_ID di URL Supabase Anda (bagian antara `https://` dan `.supabase.co`)
5. Klik **Create**
6. Salin **Client ID** dan **Client Secret** yang muncul

### 2d. Masukkan ke Supabase

1. Kembali ke Supabase → **Authentication** → **Providers** → **Google**
2. Isi:
   - **Client ID**: paste dari langkah 2c
   - **Client Secret**: paste dari langkah 2c
3. Klik **Save**

### 2e. Buat Folder Google Drive

1. Buka **Google Drive** (drive.google.com) dengan akun Kominfo
2. Buat folder baru: klik **+ New** → **Folder** → nama: `Bukti Dukung SDI 2024`
3. Buka folder tersebut
4. Salin **ID folder** dari URL browser:
   - URL contoh: `https://drive.google.com/drive/folders/1ABC123def456XYZ`
   - ID folder-nya: `1ABC123def456XYZ` (bagian setelah `folders/`)
5. Klik kanan folder → **Share** → ubah akses menjadi **Anyone with the link** → **Viewer** → **Done**

---

## Langkah 3: Upload ke GitHub Pages

### 3a. Buat Repository GitHub

1. Buka **https://github.com** → login
2. Klik **+** di pojok kanan atas → **New repository**
3. Isi:
   - **Repository name**: `rekap-sdi` (atau nama lain yang mudah diingat)
   - Centang **Public**
   - Centang **Add a README file**
4. Klik **Create repository**

### 3b. Upload File

1. Di halaman repository, klik **Add file** → **Upload files**
2. Upload ketiga file:
   - `index.html`
   - `admin.html`
   - `README.md` (file ini)
3. Klik **Commit changes**

### 3c. Aktifkan GitHub Pages

1. Di repository, klik **Settings** (tab di atas)
2. Di sidebar kiri, klik **Pages**
3. Di bagian **Source**, pilih **Deploy from a branch**
4. Branch: pilih **main** → folder: **/ (root)**
5. Klik **Save**
6. Tunggu 1-2 menit
7. Akan muncul URL: `https://NAMA_AKUN.github.io/rekap-sdi/`

---

## Langkah 4: Isi Konfigurasi di Kode

Ini langkah paling penting. Anda perlu mengubah beberapa baris di file `index.html` dan `admin.html`.

### Cara Edit di GitHub

1. Di repository GitHub, klik file `index.html`
2. Klik ikon pensil (Edit) di kanan atas
3. Cari bagian `CONFIG` (sekitar baris 190-220)
4. Ubah nilai-nilai berikut:

**Di `index.html`:**
```javascript
const CONFIG = {
  supabaseUrl: 'https://XXXXX.supabase.co',  // ← ganti XXXXX
  supabaseKey: 'eyJhbGci...',                 // ← paste anon key Supabase
  googleClientId: '123456-abc.apps.googleusercontent.com', // ← dari langkah 2c
  googleDriveFolderId: '1ABC123def456XYZ',    // ← ID folder Drive dari langkah 2e
  kabupatenKota: 'Kabupaten Pesawaran',       // ← ganti nama kabupaten/kota Anda

  opd: [
    'Dinas Kesehatan',
    'Dinas Kependudukan dan Pencatatan Sipil',
    // ... tambah/hapus sesuai OPD di wilayah Anda
  ],

  indikator: [
    { kode: '10101', nama: 'Tingkat Kematangan Penerapan Standar Data Statistik (SDS)' },
    // ... sesuaikan dengan indikator yang dinilai
  ]
};
```

**Di `admin.html`:**
```javascript
const CONFIG = {
  supabaseUrl: 'https://XXXXX.supabase.co',  // ← sama dengan index.html
  supabaseKey: 'eyJhbGci...',                // ← sama dengan index.html
  adminPassword: 'passwordKominfo2024',       // ← GANTI dengan password pilihan Anda
  kabupatenKota: 'Kabupaten Pesawaran',       // ← sama
  totalOpd: 14,                               // ← total jumlah OPD di wilayah Anda
};
```

5. Setelah selesai edit, klik **Commit changes** → **Commit changes**

---

## Langkah 5: Test Sistem

### Test halaman OPD:
1. Buka: `https://NAMA_AKUN.github.io/rekap-sdi/`
2. Klik **Masuk dengan Google**
3. Login dengan akun Google OPD
4. Isi form, upload PDF, tandai halaman
5. Klik Kirim — harus muncul pesan sukses

### Test halaman Admin:
1. Buka: `https://NAMA_AKUN.github.io/rekap-sdi/admin.html`
2. Masukkan password yang Anda set di CONFIG
3. Cek apakah dokumen test dari langkah sebelumnya muncul
4. Klik sebuah indikator di sidebar → klik **Generate PDF**
5. File harus terunduh otomatis

---

## Cara Pakai Sehari-hari

### Untuk Operator OPD:
1. Buka link sistem (bagikan URL `index.html` ke semua OPD)
2. Login dengan akun Google instansi
3. Isi form: pilih OPD, pilih indikator, tulis nama dokumen
4. Upload file PDF
5. Tandai nomor halaman penting (1-5 halaman yang paling mewakili bukti)
6. Tambahkan catatan jika perlu
7. Klik Kirim

### Untuk Admin Kominfo:
1. Buka link admin
2. Masukkan password
3. Lihat semua dokumen masuk di dashboard
4. Monitor progress upload per indikator di sidebar
5. Klik nama indikator → klik **Generate PDF** atau **Generate DOCX**
6. File rekap otomatis terunduh
7. Bisa juga klik **Review** per dokumen untuk menandai sudah diperiksa

---

## Pertanyaan Umum

**Q: Apakah OPD harus login dengan email pemerintah?**
A: Tidak harus, bisa akun Google manapun. Namun disarankan pakai akun instansi agar tercatat dengan benar.

**Q: Bagaimana kalau file PDF besar, lama uploadnya?**
A: File terkirim langsung ke Google Drive OPD yang login, bukan melalui server. Kecepatan upload tergantung koneksi internet OPD.

**Q: Apakah data aman?**
A: Metadata tersimpan di Supabase (terenkripsi). File PDF tersimpan di Google Drive Kominfo. Hanya yang punya link yang bisa mengakses.

**Q: Bagaimana kalau OPD upload dokumen salah?**
A: Admin Kominfo bisa hapus dokumen langsung dari Supabase dashboard (https://supabase.com → Table Editor → bukti_dukung → hapus baris yang salah). OPD kemudian bisa upload ulang.

**Q: Bisa dipakai untuk kabupaten/kota lain?**
A: Bisa. Cukup fork repository GitHub, ubah CONFIG di kedua file (nama kabupaten, daftar OPD, daftar indikator, password admin), deploy ulang.

**Q: Thumbnail halaman PDF tidak muncul di rekap?**
A: Ini terjadi karena Google Drive membatasi akses langsung ke file PDF dari browser (CORS). Rekap tetap berisi semua informasi dokumen dan link langsung ke Drive. Untuk mengatasi ini, bisa menggunakan Google Apps Script sebagai proxy — hubungi pengembang jika diperlukan.

---

## Bantuan & Kontak

Jika ada kendala teknis saat setup, catat:
1. Langkah mana yang bermasalah
2. Pesan error yang muncul (screenshot jika bisa)

Lalu minta bantuan dengan informasi tersebut.

---

*Sistem ini dibuat dengan GitHub Pages + Supabase + Google Drive. Semua komponen menggunakan tier gratis.*
