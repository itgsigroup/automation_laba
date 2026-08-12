# GSI Weekly Report Setup Guide

Weekly report otomatis dikirim tiap **Sabtu malam** via GitHub Actions.

## Format Output

PDF 2 halaman:
- **Halaman 1**: Executive Summary + KPI Cards + Chart Harian + Chart Cabang + Tabel Cabang WoW
- **Halaman 2**: Top Sales Chart + Trend 8 Minggu + SO WHAT Brand + Tabel Sales + Rekomendasi AI

## 1. Daftar Gemini API (Gratis)

Trial gratis: 60 request/menit, sangat cukup untuk 1 weekly report/minggu.

1. Buka **https://aistudio.google.com/app/apikey**
2. Login dengan Google
3. Klik **Create API key** → **Create API key in new project**
4. Copy API key (mulai dengan `AIza...`)

## 2. Daftar Claude API (Opsional, Berbayar Tapi Murah)

Backup kalau Gemini limit. Cost ~Rp 200-500/report pakai Haiku.

1. Buka **https://console.anthropic.com/settings/keys**
2. Daftar → verifikasi email + kartu kredit
3. Klik **Create Key** → beri nama "GSI Weekly Report"
4. Copy API key (mulai dengan `sk-ant-...`)

## 3. Setup GitHub Secrets

Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | AIza... (dari Google AI Studio) |
| `CLAUDE_API_KEY` | sk-ant-... (dari Anthropic, opsional) |
| `AI_PROVIDER` | `gemini` (utama) atau `claude` |

Semua secret existing (SHEET_ID, TG_BOT_TOKEN, dll) sudah dipakai juga.

## 4. Test Manual

### Local (di komputer):
1. Edit `config_local.py`, isi `GEMINI_API_KEY`
2. Install deps kalau belum: `pip install -r requirements.txt`
3. Jalankan: `python weekly_report.py`
4. Cek folder `weekly_out/` untuk PDF hasil
5. Cek Telegram/WA/Email untuk PDF terlampir

### GitHub Actions:
1. Tab **Actions** → workflow **"GSI Weekly Sales Brief"**
2. Klik **Run workflow** → Run
3. Tunggu 3-5 menit → cek run status
4. Download **weekly-brief-XXXX.zip** dari Artifacts untuk lihat PDF

## 5. Jadwal Otomatis

File `weekly.yml` sudah set cron **Sabtu 19:45 WIB** (= 12:45 UTC = `45 12 * * 6`).

Dimajukan 15 menit dari target 20:00 sebagai buffer untuk delay GitHub Actions.

Cron format:
```
45 12 * * 6
   |   |  ^-- Sabtu (0=Min, 6=Sab)
   |   ^----- setiap bulan
   |   
   ^--------- 12:45 UTC = 19:45 WIB
```

## 6. Isi PDF Weekly Report

### Halaman 1 — Executive & Cabang

**6 KPI Cards** (dengan delta WoW):
- Revenue
- Laba Kotor
- Margin
- Invoice + Pelanggan
- AOV + Total baris
- Kerugian + % baris rugi

**Executive Summary AI** — 3-4 kalimat interpretasi bisnis

**SO WHAT? Operational** — box oranye dengan actionable next step

**Chart 1**: Revenue harian bar + margin line
**Chart 2**: Revenue vs Laba per Cabang (label = margin)

**Tabel Cabang WoW** — Revenue, Laba, Margin minggu ini vs minggu lalu

### Halaman 2 — Sales & Rekomendasi

**Chart 3**: Top 8 Sales
**Chart 4**: Trend 8 minggu (revenue + margin)

**SO WHAT? Brand** — box merah, masalah utama brand mana

**Tabel Kinerja Sales** — Top 8 dengan Margin WoW + Catatan

**Tabel Rekomendasi AI** — 5 tindakan prioritas dengan Pemilik & Target

## Estimasi Cost per Weekly Report

- **Gemini Flash**: Gratis (di bawah free tier)
- **Claude Haiku**: ~Rp 200-500 per report
- **GitHub Actions**: 3-5 menit runtime / week (gratis di free tier)
- **Total**: praktis **Rp 0 - 500 per minggu**

## Troubleshooting

**"narasi AI tidak tersedia — cek API key"** di PDF:
- Cek secret `GEMINI_API_KEY` atau `CLAUDE_API_KEY` di GitHub sudah diisi
- Cek `AI_PROVIDER` sudah sesuai (`gemini` atau `claude`)

**PDF error atau kosong**:
- Cek `weekly_log.txt` di artifact
- Kemungkinan: sheet tidak ada data minggu berjalan

**Rekomendasi table hanya 1 baris**:
- AI response tidak valid JSON. Cek log — kadang Gemini/Claude balas dengan format berbeda.
