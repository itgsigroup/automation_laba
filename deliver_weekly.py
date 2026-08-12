"""
GSI Weekly PDF Delivery
------------------------
BUKAN untuk generate PDF (itu tugas Claude Scheduled Task).
Script ini HANYA MEMBACA file PDF terbaru dari folder weekly_out/
lalu MENGIRIM ke Telegram, WhatsApp (Fonnte), dan Email.

Trigger: Sabtu 20:00 WIB via Task Scheduler atau GitHub Actions.
"""

import os, sys
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent
try:
    import config_local  # noqa
except ImportError:
    pass

# ============ CONFIG ============
def env(k, d=""):
    v = os.environ.get(k, "")
    return v.strip() if v else d

def env_list(k, d, sep=","):
    v = os.environ.get(k, "")
    if not v: return d
    return [x.strip() for x in v.split(sep) if x.strip()]

BOT_TOKEN  = env("TG_BOT_TOKEN", "")
CHAT_IDS   = env_list("TG_CHAT_IDS", [])
FONNTE_TOKEN = env("FONNTE_TOKEN", "")
WA_NUMBERS   = env_list("WA_NUMBERS", [])
GMAIL_SENDER       = env("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS   = env_list("EMAIL_RECIPIENTS", [])

# Folder tempat Claude Scheduled Task menaruh PDF
PDF_FOLDER = BASE / "weekly_out"
LOG_FILE   = BASE / "deliver_log.txt"

# ============ HELPERS ============
def log(m):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {m}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(line+"\n")

def find_latest_pdf():
    """Cari file PDF paling baru di folder weekly_out/."""
    if not PDF_FOLDER.exists():
        log(f"Folder {PDF_FOLDER} tidak ada.")
        return None
    pdfs = sorted(PDF_FOLDER.glob("Weekly_Brief_GSI_*.pdf"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not pdfs:
        log(f"Tidak ada PDF Weekly_Brief_GSI_*.pdf di {PDF_FOLDER}")
        return None
    return pdfs[0]

def pdf_is_this_week(pdf_path):
    """Cek apakah PDF di-generate dalam 7 hari terakhir."""
    if not pdf_path: return False
    mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime)
    age_days = (datetime.now() - mtime).days
    return age_days <= 7

# ============ SEND ============
def tg_send_pdf(pdf_path, caption=""):
    if not BOT_TOKEN or not CHAT_IDS:
        log("Telegram config kosong, skip.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    for cid in CHAT_IDS:
        try:
            with open(pdf_path, "rb") as f:
                r = requests.post(url,
                    data={"chat_id": cid, "caption": caption[:1024]},
                    files={"document": f}, timeout=120)
            log(f"TG -> {cid}: {r.status_code}")
        except Exception as e:
            log(f"TG ERROR {cid}: {e}")

def wa_send_pdf(pdf_path, caption=""):
    if not FONNTE_TOKEN or not WA_NUMBERS:
        log("WA config kosong, skip.")
        return
    url = "https://api.fonnte.com/send"
    for num in WA_NUMBERS:
        try:
            with open(pdf_path, "rb") as f:
                r = requests.post(url,
                    data={"target": num, "message": caption[:1000], "countryCode": "62"},
                    files={"file": f},
                    headers={"Authorization": FONNTE_TOKEN}, timeout=120)
            log(f"WA -> {num}: {r.status_code} {r.text[:120]}")
        except Exception as e:
            log(f"WA ERROR {num}: {e}")

def email_send_pdf(pdf_path, subject, body):
    if not GMAIL_SENDER or not EMAIL_RECIPIENTS:
        log("Email config kosong, skip.")
        return
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER
    msg["To"]   = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "pdf"); part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=Path(pdf_path).name)
    msg.attach(part)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as srv:
            srv.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())
        log(f"Email PDF terkirim ke {len(EMAIL_RECIPIENTS)} recipients")
    except Exception as e:
        log(f"Email ERROR: {e}")

# ============ MAIN ============
def main():
    now_wib = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)
    log(f"Delivery start {now_wib.strftime('%A, %d %b %Y %H:%M')} WIB")

    pdf = find_latest_pdf()
    if not pdf:
        log("Tidak ada PDF untuk dikirim.")
        # Notifikasi ke admin bahwa PDF belum ada
        if BOT_TOKEN and CHAT_IDS:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            for cid in CHAT_IDS:
                requests.post(url, data={"chat_id": cid,
                    "text": f"[ALERT] Weekly Report PDF tidak ditemukan di folder weekly_out/. Cek Claude Scheduled Task."},
                    timeout=30)
        sys.exit(1)

    if not pdf_is_this_week(pdf):
        log(f"WARNING: PDF terakhir sudah > 7 hari ({pdf.name}). Kemungkinan generate gagal.")

    file_size_mb = pdf.stat().st_size / 1024 / 1024
    log(f"Mengirim PDF: {pdf.name} ({file_size_mb:.2f} MB)")

    caption = (f"GSI Weekly Sales Brief\n"
               f"{now_wib.strftime('%A, %d %b %Y')}\n"
               f"File: {pdf.name}")

    tg_send_pdf(pdf, caption)
    wa_send_pdf(pdf, caption)
    email_send_pdf(pdf,
                   subject=f"GSI Weekly Brief - {now_wib.strftime('%d %b %Y')}",
                   body=caption + "\n\nDetail lengkap di PDF terlampir.")

    log("Delivery SELESAI.")

if __name__ == "__main__":
    main()
