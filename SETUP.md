# GSI Report Bot — Setup Guide

## 1. Install Python (kalau belum ada)
Download dari https://www.python.org/downloads/ — saat install centang **"Add Python to PATH"**.

Cek instalasi di CMD:
```
python --version
```

## 2. Install Dependencies
Double-click `install_deps.bat` — atau di CMD:
```
pip install requests pandas
```

## 3. Test Manual (WAJIB sebelum schedule)
Di CMD, cd ke folder ini lalu:
```
python gsi_report.py
```
Cek Telegram bot Anda — harus menerima pesan report. Kalau error, cek `report_log.txt`.

## 4. Setup Windows Task Scheduler (Auto 09:00 & 12:00)

1. Buka **Task Scheduler** (Start → ketik "Task Scheduler")
2. Klik **Create Task** (bukan Basic Task)
3. **Tab General:**
   - Name: `GSI Report Pagi`
   - Centang **Run whether user is logged on or not**
   - Centang **Run with highest privileges**
4. **Tab Triggers → New:**
   - Begin: On a schedule
   - Daily, Start: **09:00:00**, Recur every 1 days
   - OK
5. **Tab Actions → New:**
   - Action: Start a program
   - Program/script: `D:\AI Specialist\AI Projects\Automation Laba\run_report.bat`
   - Start in: `D:\AI Specialist\AI Projects\Automation Laba`
6. **OK** → masukkan password Windows

**Ulangi untuk jam 12:00** — Create Task lagi dengan nama `GSI Report Siang`, trigger 12:00.

## 5. Menambah Chat ID (multi penerima)
Edit `gsi_report.py`, cari baris:
```python
CHAT_IDS = ["6400077082"]
```
Tambahkan: `CHAT_IDS = ["6400077082", "12345678", "-1001234567890"]`

## 6. Menyesuaikan Logic
- **Ubah rate rebate:** edit `REBATE_RATE = 0.05` (5%)
- **Ubah brand yang dapat rebate:** edit `REBATE_BRANDS = ["ezviz", "hikvision", "hik"]`
- **Ubah threshold rugi:** edit `LOSS_THRESHOLD = -0.05` (rugi lebih dari 5%)
- **Ubah jumlah top items:** edit `TOP_N = 5`

## Log Files
- `report_log.txt` — log detail (fetch, error, dll)
- `run_log.txt` — output dari Task Scheduler
