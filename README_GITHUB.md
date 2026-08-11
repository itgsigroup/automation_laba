# GSI Report Bot — GitHub Actions Setup

Panduan deploy script report ke GitHub Actions supaya jalan otomatis 2x/hari tanpa butuh laptop nyala.

## Ringkasan Arsitektur

- **Trigger:** Cron schedule di GitHub (10:00 & 16:00 WIB = 03:00 & 09:00 UTC)
- **Runner:** Ubuntu 22.04 di server GitHub (gratis, 2000 menit/bulan)
- **Kredensial:** Disimpan sebagai GitHub Secrets (encrypted)
- **Output:** Kirim ke Telegram + WhatsApp + Email
- **Log:** Otomatis tersimpan di GitHub, bisa dilihat 7 hari

## Langkah 1 — Daftar GitHub (Skip kalau sudah ada)

1. Buka https://github.com/signup
2. Isi email, password, username (bebas)
3. Verifikasi email

## Langkah 2 — Buat Repository Privat

1. Login GitHub → pojok kanan atas klik **+** → **New repository**
2. Repository name: `gsi-report-bot`
3. **PENTING:** pilih **Private** (biar code tidak dilihat orang)
4. Skip "Add README" (biar bersih)
5. Klik **Create repository**

## Langkah 3 — Upload File ke GitHub (2 Cara)

### Cara Mudah — Via Web (Drag & Drop)

1. Di halaman repository yang baru dibuat, klik link **"uploading an existing file"**
2. Drag file/folder ini dari komputer:
   - `gsi_report.py`
   - `requirements.txt`
   - `.gitignore`
   - `.github/` (folder dengan workflow di dalamnya)
   - `README_GITHUB.md` (opsional)
3. **JANGAN upload:**
   - `service_account.json` (akan dimasukkan sebagai Secret nanti)
   - `report_log.txt`, `run_log.txt`
   - folder `img/`
4. Scroll ke bawah, klik **Commit changes**

### Cara Developer — Via Git CLI (kalau punya Git)

```bash
cd "D:\AI Specialist\AI Projects\Automation Laba"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/gsi-report-bot.git
git push -u origin main
```

## Langkah 4 — Setup GitHub Secrets

Di repository → tab **Settings** → sidebar kiri **Secrets and variables** → **Actions** → tombol **New repository secret**.

Buat secret satu per satu (klik New repository secret untuk tiap baris):

| Name | Value |
|------|-------|
| `SHEET_ID` | ID Google Sheet (dari URL: `docs.google.com/spreadsheets/d/{SHEET_ID}/...`) |
| `SHEET_GID` | GID tab sheet (dari URL: `...#gid={SHEET_GID}`) |
| `TG_BOT_TOKEN` | Bot token dari BotFather Telegram |
| `TG_CHAT_IDS` | Chat ID Telegram (pisahkan koma kalau lebih dari 1) |
| `FONNTE_TOKEN` | Token dari dashboard Fonnte device |
| `WA_NUMBERS` | Nomor WA penerima format 628xxx (pisahkan koma) |
| `GMAIL_SENDER` | Email Gmail pengirim |
| `GMAIL_APP_PASSWORD` | App Password 16 karakter (tanpa spasi) |
| `EMAIL_RECIPIENTS` | Email penerima (pisahkan koma) |
| `GDRIVE_FOLDER_ID` | Folder ID Google Drive (opsional, untuk hosting gambar WA) |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Isi lengkap file service_account.json (opsional) |

### Tips untuk `GDRIVE_SERVICE_ACCOUNT_JSON`

- Buka file `service_account.json` di Notepad
- **Ctrl+A** → **Ctrl+C** (copy semua)
- Paste di kolom Value di GitHub Secret
- Klik **Add secret**

## Langkah 5 — Test Manual (Sebelum Nunggu Jam 10)

1. Di repository, klik tab **Actions** (di atas)
2. Klik workflow **"GSI Laba Rugi Report"** di sidebar kiri
3. Klik tombol **"Run workflow"** (kanan) → dropdown → **Run workflow**
4. Tunggu 1-2 menit → refresh halaman → lihat status
5. Klik run yang lagi jalan → lihat detail langkah
6. Cek Telegram, WA, Email — kalau semua masuk berarti sukses!

## Langkah 6 — Cek Log Kalau Ada Error

1. Tab **Actions** → klik run yang gagal (ada tanda X merah)
2. Klik job **send-report** → expand step yang gagal
3. Log detail muncul — biasanya ketahuan error apa
4. Scroll ke bawah, ada **Artifacts** → download `report-logs-XXXX.zip` untuk cek log detail

## Langkah 7 — Update Kalau Perlu

**Ubah jadwal:** edit file `.github/workflows/schedule.yml` langsung di web GitHub (klik pensil), ubah baris `cron`, commit.

**Ubah kredensial:** Settings → Secrets → klik secret → Update.

**Ubah script:** edit `gsi_report.py` langsung di web GitHub, commit. Otomatis langsung dipakai run berikutnya.

## Perbandingan Cron Time

| WIB | UTC (yang dipakai di YAML) |
|-----|---------------------------|
| 10:00 | 03:00 (`0 3 * * *`) |
| 12:00 | 05:00 (`0 5 * * *`) |
| 16:00 | 09:00 (`0 9 * * *`) |
| 18:00 | 11:00 (`0 11 * * *`) |

## Task Scheduler Windows — Boleh Dihapus atau Biarkan

- **Hapus** kalau mau full pindah ke GitHub Actions (recommended, biar tidak dobel kirim)
- **Biarkan** sebagai backup kalau internet kantor bermasalah dan GitHub sedang lambat

## Batas Free Tier GitHub Actions

- **2000 menit/bulan** untuk private repo
- Script Anda: ~2 menit per run × 2x/hari × 30 hari = **120 menit/bulan** — sangat aman di bawah limit
