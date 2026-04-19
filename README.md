# Sistem Rekap Bukti Dukung SDI
**Panduan Setup — Versi Tanpa Google OAuth (Lebih Mudah)**

---

## Komponen Sistem

| Komponen | Fungsi | Biaya |
|---|---|---|
| **GitHub Pages** | Hosting semua halaman web | Gratis |
| **Supabase** | Database + sistem login username/password | Gratis |
| **Google Drive** | OPD simpan file PDF sendiri, paste link ke form | Gratis |

> Tidak ada Google OAuth, tidak ada Google Cloud Console — jauh lebih sederhana.

---

## Alur Kerja

1. **Kominfo** buat akun untuk setiap OPD di dashboard admin
2. **OPD** terima username + password dari Kominfo
3. **OPD** upload PDF ke Google Drive mereka sendiri → salin link → paste di form
4. **Kominfo** buka dashboard → pilih indikator → klik Generate → file rekap terunduh

---

## Langkah 1: Setup Supabase

### 1a. Buat Project

1. Buka **https://supabase.com** → **Start your project**
2. Daftar / login
3. Klik **New Project**
   - Name: `rekap-sdi` (atau nama lain)
   - Database Password: buat password kuat, simpan
   - Region: **Southeast Asia (Singapore)**
4. Tunggu ~2 menit

### 1b. Salin URL dan Key

1. Klik **Settings** → **API**
2. Salin:
   - **Project URL** → `https://xxxxxx.supabase.co`
   - **anon / public key** → string panjang `eyJ...`

### 1c. Buat Tabel Database

1. Klik **SQL Editor** → **New query**
2. Copy-paste SQL berikut → klik **Run**:

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
  user_id text
);

-- Izin akses (Row Level Security)
alter table opd_users enable row level security;
alter table bukti_dukung enable row level security;

create policy "opd_users_all" on opd_users for all to authenticated using (true) with check (true);
create policy "opd_users_select_anon" on opd_users for select to anon using (true);
create policy "bukti_dukung_all" on bukti_dukung for all to authenticated using (true) with check (true);
```

3. Harus muncul "Success. No rows returned"

### 1d. Aktifkan Email Auth (untuk login username/password)

1. Klik **Authentication** → **Providers** → **Email**
2. Pastikan **Enable Email provider** aktif (ON)
3. **Matikan** opsi "Confirm email" (agar tidak perlu konfirmasi email):
   - Klik **Authentication** → **Settings**
   - Cari **"Enable email confirmations"** → matikan (OFF)
4. Klik **Save**

---

## Langkah 2: Upload ke GitHub

### 2a. Buat Repository

1. Buka **https://github.com** → login
2. Klik **+** → **New repository**
   - Name: `rekap-sdi`
   - Centang **Public**
   - Centang **Add a README file**
3. Klik **Create repository**

### 2b. Upload File

1. Di repository → **Add file** → **Upload files**
2. Upload: `index.html`, `admin.html`, `README.md`
3. Klik **Commit changes**

### 2c. Aktifkan GitHub Pages

1. **Settings** → **Pages**
2. Source: **Deploy from a branch** → branch: **main** → folder: **/ (root)**
3. **Save**
4. Tunggu 1-2 menit → URL: `https://NAMA.github.io/rekap-sdi/`

---

## Langkah 3: Isi Konfigurasi

Edit `index.html` dan `admin.html` di GitHub (klik file → ikon pensil).

**Cari bagian `CFG = {` dan ubah:**

### Di `index.html`:
```javascript
const CFG = {
  supabaseUrl: 'https://XXXXX.supabase.co',  // ← URL Supabase Anda
  supabaseKey: 'eyJhbGci...',                 // ← anon key Supabase
  kabupaten: 'Kabupaten Pesawaran',           // ← nama kabupaten/kota Anda
  indikator: [
    // sesuaikan dengan indikator yang dinilai
  ]
};
```

### Di `admin.html`:
```javascript
const CFG = {
  supabaseUrl: 'https://XXXXX.supabase.co',  // ← sama
  supabaseKey: 'eyJhbGci...',                // ← sama
  adminPassword: 'passwordKominfo2024',       // ← GANTI password admin
  kabupaten: 'Kabupaten Pesawaran',
  totalOpd: 14,                               // ← total OPD di wilayah Anda
  opd: ['Dinas Kesehatan', ...],              // ← sesuaikan
  indikator: [...]
};
```

Setelah edit → **Commit changes**

---

## Langkah 4: Buat Akun untuk Setiap OPD

1. Buka: `https://NAMA.github.io/rekap-sdi/admin.html`
2. Masukkan password admin
3. Klik tab **Kelola Akun OPD**
4. Klik **+ Tambah Akun OPD**
5. Isi:
   - Nama OPD (pilih dari dropdown)
   - Username (cth: `dinkes_pesawaran`)
   - Email internal (cth: `dinkes@pesawaran.internal` — tidak harus email nyata/aktif)
   - Password (minimal 8 karakter)
6. Klik **Buat Akun**
7. Ulangi untuk setiap OPD

> **Catatan:** Jika muncul error saat buat akun, buat user manual via Supabase Dashboard:
> Authentication → Users → **Add User** → isi email & password yang sama → klik Confirm.
> Lalu isi `user_id` di tabel `opd_users` dengan ID user yang baru dibuat.

### Cara membuat user di Supabase Dashboard (cara paling andal):

1. Supabase → **Authentication** → **Users** → **Add user** → **Create new user**
2. Isi email (cth: `dinkes@pesawaran.internal`) dan password
3. Klik **Create User**
4. Salin **User UID** yang muncul
5. Pergi ke **Table Editor** → tabel `opd_users` → **Insert row**:
   - `user_id`: paste UID dari langkah 4
   - `username`: `dinkes_pesawaran`
   - `email`: `dinkes@pesawaran.internal`
   - `opd_name`: `Dinas Kesehatan`
6. **Save**

---

## Langkah 5: Bagikan ke OPD

Kirimkan ke setiap OPD:
- **Link sistem**: `https://NAMA.github.io/rekap-sdi/`
- **Username**: (sesuai yang dibuat)
- **Password**: (sesuai yang dibuat)
- **Panduan upload**: (lihat bagian bawah)

---

## Panduan Upload untuk OPD

### Cara upload dokumen:
1. Buka link sistem yang diberikan Kominfo
2. Login dengan username dan password
3. Pilih **Kode Indikator** yang sesuai
4. Isi **Nama Dokumen** (judul lengkap dokumen)
5. Upload PDF ke **Google Drive** Anda:
   - Buka drive.google.com
   - Upload file PDF
   - Klik kanan file → **Share** → ubah akses ke **"Anyone with the link"** → **Copy link**
6. Paste link Google Drive di kolom yang tersedia
7. Tandai **nomor halaman penting** (1–5 halaman yang paling membuktikan)
8. Klik **Kirim**

---

## Cara Pakai (Kominfo)

1. Buka `admin.html` → masukkan password
2. Lihat semua dokumen di tab **Dokumen Masuk**
3. Klik nama indikator di sidebar kiri untuk filter per indikator
4. Monitor progress upload OPD (progress bar otomatis muncul)
5. Klik **Generate PDF** atau **Generate DOCX** → file rekap terunduh
6. Klik **Buka** pada setiap dokumen untuk lihat file asli di Drive
7. Klik **Review** untuk tandai dokumen sudah diperiksa
8. Klik **Hapus** jika ada dokumen yang perlu dihapus (OPD bisa upload ulang)

---

## FAQ

**Q: Apakah perlu email OPD yang aktif?**
A: Tidak. Email hanya dipakai sebagai ID login di sistem, tidak dikirim email apapun. Bisa pakai format `namaopd@pesawaran.internal`.

**Q: Bagaimana jika OPD lupa password?**
A: Admin Kominfo hapus akun lama di dashboard, buat ulang akun baru dengan password baru.

**Q: Apakah dokumen PDF tersimpan di server?**
A: Tidak. PDF tersimpan di Google Drive OPD masing-masing. Sistem hanya menyimpan link-nya.

**Q: Bisa dipakai untuk kabupaten/kota lain?**
A: Bisa. Fork repository GitHub, ubah CONFIG (nama kabupaten, daftar OPD, indikator, password admin), deploy ulang. Satu Supabase project bisa untuk beberapa kabupaten/kota sekaligus dengan menambahkan kolom `kabupaten`.

**Q: Kenapa thumbnail halaman PDF tidak muncul di rekap?**
A: File PDF tersimpan di Google Drive OPD, dan browser tidak bisa langsung merender halaman PDF dari Drive karena pembatasan keamanan. Rekap tetap memuat semua informasi + link langsung ke Drive. Penilai klik link → langsung ke dokumen asli, bisa navigasi ke halaman yang ditandai.

---

*Sistem ini sepenuhnya gratis: GitHub Pages + Supabase free tier + Google Drive pribadi OPD.*
