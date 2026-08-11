"""
GSI Laba Rugi Report Bot v2
----------------------------
Fetches Google Sheet, applies 5% rebate for Ezviz & Hikvision,
generates narrative insights + detailed rows + PNG image tables,
and sends all to Telegram (text + image per period).
"""

import io
import os
import sys
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent

# ============ KONFIGURASI ============
# Dibaca dari environment variables (GitHub Secrets) kalau ada,
# jika tidak, pakai default di bawah (untuk test lokal).
def env(key, default=""):
    v = os.environ.get(key, "")
    return v.strip() if v else default

def env_list(key, default_list, sep=","):
    v = os.environ.get(key, "")
    if not v: return default_list
    return [x.strip() for x in v.split(sep) if x.strip()]

# --- Google Sheet ---
SHEET_ID   = env("SHEET_ID",  "1Z7jYIRomStLa85IqYQlK2e33RKFglAi6_GfFchcjYr8")
SHEET_GID  = env("SHEET_GID", "202348666")
CSV_URL    = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# --- Telegram ---
BOT_TOKEN  = env("TG_BOT_TOKEN", "8918248830:AAGWuHyIzu0DSDpBbVTgiZeIre4qi-iXcvE")
CHAT_IDS   = env_list("TG_CHAT_IDS", ["6400077082"])

# --- Fonnte WhatsApp ---
FONNTE_TOKEN = env("FONNTE_TOKEN", "CA3GP5mL69rSePSxC8oJ")
WA_NUMBERS   = env_list("WA_NUMBERS", ["6285803643592", "6288215320214"])
ENABLE_TELEGRAM = True
ENABLE_WHATSAPP = True

# Imgur fallback (opsional)
IMGUR_CLIENT_ID = env("IMGUR_CLIENT_ID", "")

# --- Email (Gmail SMTP) ---
ENABLE_EMAIL       = True
GMAIL_SENDER       = env("GMAIL_SENDER",       "ai.gsigroup@gmail.com")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", "zbufwxnbinvnonuk")
EMAIL_RECIPIENTS   = env_list("EMAIL_RECIPIENTS", ["bi.gsigroup@gmail.com"])

# --- Google Drive (untuk hosting gambar WA + arsip) ---
GDRIVE_FOLDER_ID   = env("GDRIVE_FOLDER_ID", "ISI_FOLDER_ID_DISINI")
GDRIVE_KEY_FILE    = str(BASE / "service_account.json")
ENABLE_GDRIVE      = False   # otomatis True kalau folder ID + key file ada

REBATE_BRANDS   = ["ezviz", "hikvision"]  # HANYA 2 brand ini yang dapat rebate 5%. Hiksemi & lain TIDAK.
REBATE_RATE     = 0.05
LOSS_THRESHOLD  = -0.05
TOP_N           = 10   # jumlah baris di tabel detail

LOG_FILE  = BASE / "report_log.txt"
IMG_DIR   = BASE / "img"; IMG_DIR.mkdir(exist_ok=True)

# ============ HELPERS ============
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _to_num(n):
    """Convert apapun ke float dengan aman."""
    if pd.isna(n): return 0.0
    if isinstance(n, (int, float)): return float(n)
    try: return parse_rp(n)
    except: return 0.0

def rp(n):
    n = _to_num(n)
    if n == 0: return "Rp0"
    sign = "-" if n < 0 else ""
    return f"{sign}Rp{abs(int(round(n))):,}".replace(",", ".")

def rp_short(n):
    """Rp 12,3 Jt / Rp 1,25 M untuk ringkas"""
    n = _to_num(n)
    if n == 0: return "Rp0"
    a = abs(n); sign = "-" if n < 0 else ""
    if a >= 1e9:  return f"{sign}Rp{a/1e9:.2f}M"
    if a >= 1e6:  return f"{sign}Rp{a/1e6:.1f}Jt"
    if a >= 1e3:  return f"{sign}Rp{a/1e3:.0f}rb"
    return f"{sign}Rp{a:.0f}"

def parse_rp(s):
    if pd.isna(s): return 0.0
    s = str(s).strip()
    if not s or s == "-": return 0.0
    neg = s.startswith("-")
    s = s.lstrip("-").replace("Rp", "").replace(",", "").strip()
    try: val = float(s)
    except: val = 0.0
    return -val if neg else val

def parse_date(s):
    if pd.isna(s): return None
    for fmt in ("%d/%b/%Y", "%d/%B/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: continue
    return None

# ============ FETCH ============
def fetch_data():
    log("Fetching Google Sheet...")
    r = requests.get(CSV_URL, timeout=30); r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [c.strip() for c in df.columns]
    log(f"Rows: {len(df)}")

    df["Tgl"]        = df["Tgl Inv"].apply(parse_date)
    df["TotalHarga"] = df["Total Harga"].apply(parse_rp)
    df["HPP"]        = df["BPP / HPP"].apply(parse_rp)
    df["Laba"]       = df["Laba"].apply(parse_rp)
    df["BrandLower"] = df["Brand"].astype(str).str.lower().str.strip()

    is_rebate = df["BrandLower"].isin([b.lower() for b in REBATE_BRANDS])
    df["Rebate"]  = 0.0
    df.loc[is_rebate, "Rebate"] = df.loc[is_rebate, "TotalHarga"] * REBATE_RATE
    df["LabaAdj"] = df["Laba"] + df["Rebate"]
    df["Margin"]  = df.apply(
        lambda r: (r["LabaAdj"]/r["TotalHarga"]) if r["TotalHarga"] else 0.0, axis=1)

    return df.dropna(subset=["Tgl"])

# ============ INSIGHT BISNIS per periode ============
def build_insight(df, label, date_range):
    """Insight bisnis fokus laba rugi: ringkasan keuangan + analisis kontribusi + list item profit/rugi."""
    if len(df) == 0:
        return f"===== {label} =====\nPeriode: {date_range}\nTIDAK ADA TRANSAKSI.\n"

    n          = len(df)
    omset      = df["TotalHarga"].sum()
    hpp_total  = df["HPP"].sum()
    laba       = df["LabaAdj"].sum()
    laba_ori   = df["Laba"].sum()
    rebate_tot = df["Rebate"].sum()
    margin     = (laba/omset*100) if omset else 0
    profit_df  = df[df["LabaAdj"] > 0]
    rugi_df    = df[df["LabaAdj"] < 0]
    rugi_berat = df[df["Margin"] < LOSS_THRESHOLD]

    # === RINGKASAN KEUANGAN ===
    lines = [
        f"===== LAPORAN {label} =====",
        f"Periode : {date_range}",
        f"",
        f"[ RINGKASAN KEUANGAN ]",
        f"  Total Transaksi    : {n} invoice-item",
        f"  Omset              : {rp(omset)}",
        f"  HPP (Modal)        : {rp(hpp_total)}",
        f"  Laba Original      : {rp(laba_ori)}",
        f"  Rebate 5% (Ezv+Hik): {rp(rebate_tot)}",
        f"  LABA NET FINAL     : {rp(laba)}",
        f"  Margin             : {margin:+.2f}%",
        f"",
        f"[ ANALISIS BISNIS ]",
    ]

    # Analisis naratif business-focused
    if margin > 20:
        analisis = "Kinerja SANGAT BAIK. Margin di atas 20% menunjukkan pricing dan efisiensi HPP optimal."
    elif margin > 10:
        analisis = "Kinerja SEHAT. Margin di kisaran 10-20% berada dalam target industri distribusi CCTV."
    elif margin > 5:
        analisis = "Kinerja CUKUP. Margin single digit — pertimbangkan naikkan harga jual atau nego HPP."
    elif margin > 0:
        analisis = "Kinerja TIPIS. Margin dibawah 5% berisiko — evaluasi item dengan HPP tinggi."
    else:
        analisis = "PERINGATAN. Periode ini RUGI — evaluasi seluruh item dan kebijakan harga."
    lines.append(f"  {analisis}")

    # Kontribusi profit vs rugi
    profit_val = profit_df["LabaAdj"].sum()
    rugi_val   = rugi_df["LabaAdj"].sum()
    lines.append(f"  Profit dari {len(profit_df)} item menyumbang {rp(profit_val)}.")
    lines.append(f"  Rugi dari {len(rugi_df)} item mengurangi {rp(rugi_val)}.")
    if len(rugi_berat):
        pct_rugi = len(rugi_berat) / n * 100
        lines.append(f"  {len(rugi_berat)} item ({pct_rugi:.1f}% dari total) rugi >5% — perlu tindakan segera.")

    # === ITEM PENYUMBANG LABA (list agregat per barang) ===
    by_barang = (df.groupby("Nama Barang")
                   .agg(Qty=("LabaAdj","count"),
                        Omset=("TotalHarga","sum"),
                        Laba=("LabaAdj","sum"))
                   .sort_values("Laba", ascending=False))
    top_items_profit = by_barang[by_barang["Laba"] > 0].head(10)

    if len(top_items_profit):
        lines.append("")
        lines.append(f"[ ITEM PENYUMBANG LABA (Top 10) ]")
        for i, (name, r) in enumerate(top_items_profit.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"  {i:>2}. {str(name)[:42]:<42} | {int(r['Qty']):>3}x | {rp(r['Laba'])} ({m:+.1f}%)")

    # Item rugi
    loss_items = by_barang[by_barang["Laba"] < 0].sort_values("Laba").head(5)
    if len(loss_items):
        lines.append("")
        lines.append(f"[ ITEM PENYEBAB RUGI (Top 5) ]")
        for i, (name, r) in enumerate(loss_items.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"  {i}. {str(name)[:42]:<42} | {int(r['Qty']):>3}x | {rp(r['Laba'])} ({m:+.1f}%)")

    # === RANKING SALES ===
    if "Nama Sales" in df.columns:
        by_sales = (df.groupby("Nama Sales")
                      .agg(Trx=("LabaAdj","count"),
                           Omset=("TotalHarga","sum"),
                           Laba=("LabaAdj","sum"))
                      .sort_values("Laba", ascending=False).head(5))
        if len(by_sales):
            lines.append("")
            lines.append("[ TOP 5 SALES (kontribusi laba) ]")
            for i, (name, r) in enumerate(by_sales.iterrows(), 1):
                m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
                lines.append(f"  {i}. {str(name)[:20]:<20} | {int(r['Trx']):>3} trx | Omset {rp(r['Omset'])} | Laba {rp(r['Laba'])} ({m:+.1f}%)")

    # === RANKING BRAND ===
    by_brand = (df.groupby("Brand")
                  .agg(Trx=("LabaAdj","count"),
                       Omset=("TotalHarga","sum"),
                       Laba=("LabaAdj","sum"))
                  .sort_values("Laba", ascending=False).head(5))
    if len(by_brand):
        lines.append("")
        lines.append("[ TOP 5 BRAND (kontribusi laba) ]")
        for i, (name, r) in enumerate(by_brand.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"  {i}. {str(name)[:15]:<15} | {int(r['Trx']):>3} trx | Omset {rp(r['Omset'])} | Laba {rp(r['Laba'])} ({m:+.1f}%)")

    # === RANKING CUSTOMER ===
    if "Nama Pelanggan" in df.columns:
        by_cust = (df.groupby("Nama Pelanggan")
                     .agg(Trx=("LabaAdj","count"),
                          Omset=("TotalHarga","sum"),
                          Laba=("LabaAdj","sum"))
                     .sort_values("Laba", ascending=False).head(5))
        if len(by_cust):
            lines.append("")
            lines.append("[ TOP 5 CUSTOMER (kontribusi laba) ]")
            for i, (name, r) in enumerate(by_cust.iterrows(), 1):
                m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
                lines.append(f"  {i}. {str(name)[:24]:<24} | {int(r['Trx']):>3} trx | Laba {rp(r['Laba'])} ({m:+.1f}%)")

    return "\n".join(lines)

# ============ IMAGE — full detail table ============
def make_full_table_image(df, title, subtitle, out_path):
    """Render SEMUA transaksi periode ini sebagai PNG dengan 12 kolom lengkap.
       Row rugi >5% highlight merah, row profit tinggi highlight hijau, netral putih."""
    if len(df) == 0:
        return None

    # Sort: rugi terbesar di atas, lalu profit tertinggi ke bawah
    df_sorted = df.sort_values("LabaAdj").reset_index(drop=True)

    cols = ["No. Inv", "Sales", "Customer", "Tgl", "Nama Barang",
            "Brand", "Kts", "Harga", "Total", "HPP", "Laba", "Diskon"]

    rows, colors = [], []
    for _, r in df_sorted.iterrows():
        row = [
            str(r.get("No. Inv","-"))[:18],
            str(r.get("Nama Sales","-"))[:14],
            str(r.get("Nama Pelanggan","-"))[:22],
            r["Tgl"].strftime("%d/%m/%y") if pd.notna(r["Tgl"]) else "-",
            str(r.get("Nama Barang","-"))[:36],
            str(r.get("Brand","-"))[:10],
            str(r.get("Kts (","")).strip(),
            rp_short(r.get("@Harga", 0)),
            rp_short(r["TotalHarga"]),
            rp_short(r["HPP"]),
            rp_short(r["LabaAdj"]),
            rp_short(r.get("Diskon", 0)),
        ]
        if r["Margin"] < LOSS_THRESHOLD:
            bg = "#FDECEA"
        elif r["LabaAdj"] > 0 and r["Margin"] > 0.15:
            bg = "#E7F6E7"
        else:
            bg = "#FFFFFF"
        rows.append(row); colors.append([bg]*len(cols))

    fig_h = max(3.5, 0.32 * (len(rows) + 3))
    fig, ax = plt.subplots(figsize=(22, fig_h))
    ax.axis("off")
    ax.text(0, 1.0, title, fontsize=16, fontweight="bold", transform=ax.transAxes)
    ax.text(0, 0.975, subtitle, fontsize=10, color="#555555", transform=ax.transAxes)

    tbl = ax.table(cellText=rows, colLabels=cols, cellColours=colors,
                   colColours=["#1F3A5F"]*len(cols), loc="center",
                   cellLoc="left", colLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(8)
    tbl.scale(1, 1.25)
    for i in range(len(cols)):
        tbl[0, i].set_text_props(color="white", fontweight="bold")

    col_widths = [0.10, 0.08, 0.13, 0.06, 0.20, 0.07, 0.03, 0.06, 0.07, 0.06, 0.08, 0.06]
    for i, w in enumerate(col_widths):
        for j in range(len(rows)+1):
            tbl[j, i].set_width(w)

    plt.savefig(out_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path

# ============ SEND ============
def tg_send_text(text):
    if not ENABLE_TELEGRAM: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for cid in CHAT_IDS:
        for i in range(0, len(text), 4000):
            resp = requests.post(url, data={"chat_id": cid, "text": text[i:i+4000]}, timeout=30)
            log(f"TG text -> {cid}: {resp.status_code}")

def tg_send_photo(img_path, caption=""):
    if not ENABLE_TELEGRAM: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    for cid in CHAT_IDS:
        with open(img_path, "rb") as f:
            resp = requests.post(url, data={"chat_id": cid, "caption": caption[:1024]},
                                 files={"photo": f}, timeout=60)
        log(f"TG photo -> {cid}: {resp.status_code}")

# --- Fonnte WhatsApp ---
def wa_send_text(text):
    if not ENABLE_WHATSAPP: return
    url = "https://api.fonnte.com/send"
    for num in WA_NUMBERS:
        for i in range(0, len(text), 3500):
            resp = requests.post(url,
                data={"target": num, "message": text[i:i+3500], "countryCode": "62"},
                headers={"Authorization": FONNTE_TOKEN}, timeout=30)
            log(f"WA text -> {num}: {resp.status_code} {resp.text[:120]}")

# ============ EMAIL (Gmail SMTP) ============
_email_buffer = {"body": [], "images": []}   # kumpulan konten untuk 1 email

def email_append_text(text):
    if ENABLE_EMAIL:
        _email_buffer["body"].append(text)

def email_append_image(img_path, caption=""):
    if ENABLE_EMAIL:
        _email_buffer["images"].append((str(img_path), caption))
        _email_buffer["body"].append(f"[Gambar: {caption}]")

def email_flush():
    if not ENABLE_EMAIL or not EMAIL_RECIPIENTS: return
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage

    body = "\n".join(_email_buffer["body"])
    subject = f"GSI Laba Rugi Report - {datetime.now().strftime('%d %b %Y %H:%M')}"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER
    msg["To"]   = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for path, cap in _email_buffer["images"]:
        try:
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-Disposition", "attachment", filename=Path(path).name)
            msg.attach(img)
        except Exception as e:
            log(f"Email attach fail {path}: {e}")

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as srv:
            srv.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())
        log(f"Email terkirim ke {len(EMAIL_RECIPIENTS)} recipient")
    except Exception as e:
        log(f"Email FAIL: {e}")

    _email_buffer["body"].clear()
    _email_buffer["images"].clear()

# ============ GOOGLE DRIVE UPLOAD ============
_gdrive_service = None

def _init_gdrive():
    global _gdrive_service, ENABLE_GDRIVE
    if _gdrive_service is not None: return _gdrive_service
    if not Path(GDRIVE_KEY_FILE).exists() or "ISI_" in GDRIVE_FOLDER_ID:
        ENABLE_GDRIVE = False
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            GDRIVE_KEY_FILE, scopes=["https://www.googleapis.com/auth/drive"])
        _gdrive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        ENABLE_GDRIVE = True
        return _gdrive_service
    except Exception as e:
        log(f"GDrive init fail: {e}")
        ENABLE_GDRIVE = False
        return None

def upload_to_gdrive(img_path):
    """Upload gambar ke Drive folder, set public, return direct URL."""
    svc = _init_gdrive()
    if not svc: return None
    try:
        from googleapiclient.http import MediaFileUpload
        meta = {"name": Path(img_path).name, "parents": [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(str(img_path), mimetype="image/png")
        f = svc.files().create(body=meta, media_body=media, fields="id").execute()
        fid = f["id"]
        svc.permissions().create(fileId=fid,
            body={"type":"anyone","role":"reader"}).execute()
        url = f"https://drive.google.com/uc?export=view&id={fid}"
        log(f"GDrive upload OK: {url}")
        return url
    except Exception as e:
        log(f"GDrive upload fail: {e}")
        return None

def get_image_public_url(img_path):
    """Coba GDrive dulu, fallback Imgur."""
    url = upload_to_gdrive(img_path)
    if url: return url
    if IMGUR_CLIENT_ID:
        try:
            import base64
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            r = requests.post("https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"},
                data={"image": b64, "type": "base64"}, timeout=60)
            if r.status_code == 200:
                return r.json()["data"]["link"]
        except Exception as e:
            log(f"Imgur fail: {e}")
    return None

# Override wa_send_photo untuk pakai GDrive/Imgur URL
def wa_send_photo(img_path, caption=""):
    if not ENABLE_WHATSAPP: return
    img_url = get_image_public_url(img_path)
    if not img_url:
        wa_send_text(f"[Gambar gagal diupload]\n{caption}")
        return
    url = "https://api.fonnte.com/send"
    for num in WA_NUMBERS:
        resp = requests.post(url,
            data={"target": num, "message": caption[:1000], "url": img_url, "countryCode": "62"},
            headers={"Authorization": FONNTE_TOKEN}, timeout=60)
        log(f"WA photo -> {num}: {resp.status_code} {resp.text[:120]}")

# --- Multi-channel wrappers ---
def send_text(text):
    tg_send_text(text)
    wa_send_text(text)
    email_append_text(text)

def send_photo(img_path, caption=""):
    tg_send_photo(img_path, caption)
    wa_send_photo(img_path, caption)
    email_append_image(img_path, caption)

# ============ MAIN ============
def main():
    try:
        df = fetch_data()
        now = datetime.now()
        today = now.date()
        week_start  = today - timedelta(days=6)
        month_start = today.replace(day=1)

        periods = [
            ("HARI INI", today, today, df[df["Tgl"].dt.date == today]),
            ("7 HARI TERAKHIR", week_start, today,
                df[(df["Tgl"].dt.date >= week_start) & (df["Tgl"].dt.date <= today)]),
            ("BULAN INI", month_start, today,
                df[(df["Tgl"].dt.date >= month_start) & (df["Tgl"].dt.date <= today)]),
        ]

        # === HEADER MESSAGE ===
        header = (f"REPORT LABA RUGI GSI\n"
                  f"{now.strftime('%A, %d %b %Y  %H:%M')}\n"
                  f"{'='*40}\n"
                  f"Rebate 5% aktif untuk brand: {', '.join(REBATE_BRANDS)}\n"
                  f"Threshold rugi: margin di bawah -5%\n"
                  f"3 periode: Hari Ini | 7 Hari Terakhir | Bulan Ini\n")
        send_text(header)

        # === PER PERIODE: kirim GAMBAR full detail + INSIGHT text ===
        for label, d1, d2, sub in periods:
            date_range = f"{d1.strftime('%d %b %Y')} - {d2.strftime('%d %b %Y')}"

            # 1) Kirim gambar detail lengkap (12 kolom, semua transaksi periode)
            if len(sub):
                img_path = IMG_DIR / f"report_{label.replace(' ','_')}_{today}.png"
                title = f"DETAIL {label}"
                subtitle = f"Periode: {date_range}   |   {len(sub)} transaksi"
                if make_full_table_image(sub, title, subtitle, img_path):
                    send_photo(img_path, caption=f"{label} — {date_range}")

            # 2) Kirim insight naratif + ranking untuk periode ini
            insight = build_insight(sub, label, date_range)
            send_text(insight)

        email_flush()   # kirim semua konten sebagai 1 email dengan attachment
        log("Selesai.")
    except Exception as e:
        err = f"ERROR: {type(e).__name__}: {e}"
        log(err)
        try: send_text(f"GSI Report Bot GAGAL:\n{err}")
        except: pass
        sys.exit(1)

if __name__ == "__main__":
    main()
