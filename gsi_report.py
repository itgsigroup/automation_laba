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
SHEET_ID   = env("SHEET_ID",  "")
SHEET_GID  = env("SHEET_GID", "0")
CSV_URL    = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# --- Telegram ---
BOT_TOKEN  = env("TG_BOT_TOKEN", "")
CHAT_IDS   = env_list("TG_CHAT_IDS", [])

# --- Fonnte WhatsApp ---
FONNTE_TOKEN = env("FONNTE_TOKEN", "")
WA_NUMBERS   = env_list("WA_NUMBERS", [])
ENABLE_TELEGRAM = bool(BOT_TOKEN and CHAT_IDS)
ENABLE_WHATSAPP = bool(FONNTE_TOKEN and WA_NUMBERS)

# Imgur fallback (opsional)
IMGUR_CLIENT_ID = env("IMGUR_CLIENT_ID", "")

# --- Email (Gmail SMTP) ---
GMAIL_SENDER       = env("GMAIL_SENDER",       "")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS   = env_list("EMAIL_RECIPIENTS", [])
ENABLE_EMAIL       = bool(GMAIL_SENDER and GMAIL_APP_PASSWORD and EMAIL_RECIPIENTS)

# --- Google Drive (untuk hosting gambar WA + arsip) ---
GDRIVE_FOLDER_ID   = env("GDRIVE_FOLDER_ID", "")
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

# ============ INSIGHT — 3 layer sesuai fokus periode ============
def _fmt_item_row(i, name, r, pad_name=42):
    m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
    return f"  {i:>2}. {str(name)[:pad_name]:<{pad_name}} | {int(r['Qty']):>3}x | {rp(r['Laba'])} ({m:+.1f}%)"

def _agg_by_item(df):
    return (df.groupby("Nama Barang")
              .agg(Qty=("LabaAdj","count"), Omset=("TotalHarga","sum"), Laba=("LabaAdj","sum"))
              .sort_values("Laba", ascending=False))

def _agg_by_brand(df):
    return (df.groupby("Brand")
              .agg(Qty=("LabaAdj","count"), Omset=("TotalHarga","sum"), Laba=("LabaAdj","sum"))
              .sort_values("Laba", ascending=False))

def _recurring_loss(df, min_occurrence=2):
    """Item yang muncul >= min_occurrence kali DAN mayoritas trx-nya rugi."""
    if len(df) == 0: return pd.DataFrame()
    g = df.groupby("Nama Barang").agg(
        Total=("LabaAdj","count"),
        RugiCount=("LabaAdj", lambda x: (x < 0).sum()),
        LabaTot=("LabaAdj","sum"),
        OmsetTot=("TotalHarga","sum"))
    g = g[(g["Total"] >= min_occurrence) & (g["RugiCount"] >= g["Total"]*0.5)]
    return g.sort_values("LabaTot").head(10)

def _rebate_impact(df):
    """Item Ezviz/Hikvision yang tanpa rebate akan rugi, tapi setelah rebate jadi profit."""
    rebate_df = df[df["BrandLower"].isin([b.lower() for b in REBATE_BRANDS])]
    if len(rebate_df) == 0:
        return None
    total_rebate  = rebate_df["Rebate"].sum()
    tanpa_rebate  = (rebate_df["Laba"] < 0).sum()
    setelah_reb   = (rebate_df["LabaAdj"] < 0).sum()
    diselamatkan  = tanpa_rebate - setelah_reb
    return {
        "total_rebate": total_rebate,
        "item_ezv_hik": len(rebate_df),
        "rugi_tanpa_rebate": tanpa_rebate,
        "rugi_setelah_rebate": setelah_reb,
        "diselamatkan": diselamatkan,
    }

def _header_finansial(df, label, date_range):
    """Bagian ringkasan keuangan universal untuk semua insight."""
    n         = len(df)
    omset     = df["TotalHarga"].sum()
    hpp       = df["HPP"].sum()
    laba      = df["LabaAdj"].sum()
    margin    = (laba/omset*100) if omset else 0
    return [
        f"===== {label} =====",
        f"Periode: {date_range}   |   {n} transaksi",
        f"",
        f"[ RINGKASAN KEUANGAN ]",
        f"  Omset          : {rp(omset)}",
        f"  HPP (Modal)    : {rp(hpp)}",
        f"  Gross Profit   : {rp(laba)}",
        f"  Margin         : {margin:+.2f}%",
    ], margin


# ---------------- TODAY (Operational) — ringkas ----------------
def build_insight_today(df, label, date_range):
    if len(df) == 0:
        return f"===== {label} =====\nPeriode: {date_range}\nTIDAK ADA TRANSAKSI HARI INI.\n"

    lines, margin = _header_finansial(df, label, date_range)
    by_item = _agg_by_item(df)
    top_profit = by_item[by_item["Laba"] > 0].head(5)
    rugi5 = df[df["Margin"] < LOSS_THRESHOLD]
    total_untung = df[df["LabaAdj"] > 0]["LabaAdj"].sum()
    total_rugi   = df[df["LabaAdj"] < 0]["LabaAdj"].sum()

    lines += [
        f"",
        f"[ TOP 5 ITEM PALING UNTUNG ]",
    ]
    if len(top_profit):
        for i, (name, r) in enumerate(top_profit.iterrows(), 1):
            lines.append(_fmt_item_row(i, name, r))
    else:
        lines.append("  (tidak ada item profit hari ini)")

    lines += [
        f"",
        f"[ RUGI >5% HARI INI ]",
        f"  Jumlah transaksi: {len(rugi5)}",
        f"  Total kerugian  : {rp(rugi5['LabaAdj'].sum() if len(rugi5) else 0)}",
        f"  (Detail per item di GAMBAR TABEL RUGI >5%)",
    ]

    lines += ["", "[ INSIGHT OPERASIONAL ]"]
    if len(top_profit):
        best = top_profit.index[0]; best_val = top_profit.iloc[0]["Laba"]
        lines.append(f"  Produk paling menghasilkan laba hari ini: '{str(best)[:50]}' ({rp(best_val)}).")
    if margin < 5 and margin > 0:
        lines.append(f"  PERHATIAN: margin hari ini hanya {margin:.1f}% - review pricing atau HPP.")
    elif margin < 0:
        lines.append(f"  ALERT: hari ini net RUGI {margin:.1f}% - butuh review segera.")

    return "\n".join(lines)


# ---------------- LAST 7 DAYS (Monitoring) — ringkas ----------------
def build_insight_7d(df, label, date_range):
    if len(df) == 0:
        return f"===== {label} =====\nPeriode: {date_range}\nTIDAK ADA TRANSAKSI.\n"

    lines, margin = _header_finansial(df, label, date_range)
    by_item = _agg_by_item(df)
    top_profit = by_item[by_item["Laba"] > 0].head(5)
    rugi5 = df[df["Margin"] < LOSS_THRESHOLD]
    recurring  = _recurring_loss(df, min_occurrence=2)
    reb = _rebate_impact(df)

    lines += [f"", f"[ TOP 5 PROFIT ITEM ]"]
    if len(top_profit):
        for i, (name, r) in enumerate(top_profit.iterrows(), 1):
            lines.append(_fmt_item_row(i, name, r))
    else:
        lines.append("  (tidak ada item profit)")

    lines += [
        f"",
        f"[ RUGI >5% (7 HARI) ]",
        f"  Jumlah transaksi: {len(rugi5)} ({(len(rugi5)/len(df)*100):.1f}% dari total)",
        f"  Total kerugian  : {rp(rugi5['LabaAdj'].sum() if len(rugi5) else 0)}",
        f"  (Detail per item di GAMBAR TABEL RUGI >5%)",
    ]

    lines += [f"", f"[ RECURRING LOSS — Item berulang-ulang rugi ]"]
    if len(recurring):
        for i, (name, r) in enumerate(recurring.head(5).iterrows(), 1):
            lines.append(f"  {i}. {str(name)[:42]:<42} | {int(r['Total'])}x trx, {int(r['RugiCount'])}x rugi | {rp(r['LabaTot'])}")
    else:
        lines.append("  (tidak ada pola recurring loss di 7 hari terakhir)")

    lines += [f"", f"[ DAMPAK REBATE HIKVISION & EZVIZ ]"]
    if reb:
        lines += [
            f"  Total rebate diperoleh    : {rp(reb['total_rebate'])}",
            f"  Diselamatkan rebate       : {reb['diselamatkan']} item (dari rugi jadi profit)",
        ]

    lines += ["", "[ INSIGHT MONITORING ]"]
    if len(top_profit):
        star = top_profit.index[0]
        lines.append(f"  Item konsisten profit: '{str(star)[:50]}' ({int(top_profit.iloc[0]['Qty'])}x, {rp(top_profit.iloc[0]['Laba'])}).")
    if len(recurring):
        prob = recurring.index[0]
        lines.append(f"  Item berulang rugi   : '{str(prob)[:50]}' — {int(recurring.iloc[0]['Total'])}x, {int(recurring.iloc[0]['RugiCount'])}x rugi.")
        lines.append(f"  Rekomendasi: review harga jual atau stop pengadaan item recurring loss.")

    return "\n".join(lines)


# ---------------- LAST 30 DAYS (Business) — insight LENGKAP, no image ----------------
def build_insight_30d(df, label, date_range):
    if len(df) == 0:
        return f"===== {label} =====\nPeriode: {date_range}\nTIDAK ADA TRANSAKSI.\n"

    lines, margin = _header_finansial(df, label, date_range)
    by_item  = _agg_by_item(df)
    by_brand = _agg_by_brand(df)
    top_profit_item = by_item[by_item["Laba"] > 0].head(3)   # 3 barang saja
    top_loss_item   = by_item[by_item["Laba"] < 0].sort_values("Laba").head(5)   # 5 item paling rugi
    rugi5    = df[df["Margin"] < LOSS_THRESHOLD]
    recurring= _recurring_loss(df, min_occurrence=3)
    reb      = _rebate_impact(df)

    # Total agregat
    total_untung = df[df["LabaAdj"] > 0]["LabaAdj"].sum()
    total_rugi   = df[df["LabaAdj"] < 0]["LabaAdj"].sum()
    n_untung     = (df["LabaAdj"] > 0).sum()
    n_rugi       = (df["LabaAdj"] < 0).sum()

    # === TOTAL UNTUNG & 3 ITEM PENYUMBANG ===
    lines += [
        f"",
        f"[ TOTAL KEUNTUNGAN 30 HARI ]",
        f"  Total profit     : {rp(total_untung)} dari {n_untung} transaksi",
        f"",
        f"  3 ITEM PENYUMBANG UNTUNG TERBESAR:",
    ]
    if len(top_profit_item):
        for i, (name, r) in enumerate(top_profit_item.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"    {i}. {str(name)[:50]}")
            lines.append(f"       Qty {int(r['Qty'])}x  |  Omset {rp(r['Omset'])}  |  Laba {rp(r['Laba'])} ({m:+.1f}%)")

    # === TOTAL RUGI & ITEM YANG PALING BANYAK RUGI ===
    lines += [
        f"",
        f"[ TOTAL KERUGIAN 30 HARI ]",
        f"  Total loss        : {rp(total_rugi)} dari {n_rugi} transaksi",
        f"  Loss margin >5%   : {rp(rugi5['LabaAdj'].sum() if len(rugi5) else 0)} dari {len(rugi5)} transaksi ({(len(rugi5)/len(df)*100):.1f}%)",
        f"",
        f"  ITEM YANG PALING BANYAK MERUGI:",
    ]
    if len(top_loss_item):
        for i, (name, r) in enumerate(top_loss_item.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"    {i}. {str(name)[:50]}")
            lines.append(f"       Qty {int(r['Qty'])}x  |  Omset {rp(r['Omset'])}  |  Loss {rp(r['Laba'])} ({m:+.1f}%)")
    else:
        lines.append("    (tidak ada item net-loss di 30 hari)")

    # === RECURRING LOSS ===
    lines += [f"", f"[ RECURRING LOSS (item berulang rugi min 3x) ]"]
    if len(recurring):
        for i, (name, r) in enumerate(recurring.head(5).iterrows(), 1):
            lines.append(f"  {i}. {str(name)[:42]:<42} | {int(r['Total'])}x trx, {int(r['RugiCount'])}x rugi | {rp(r['LabaTot'])}")
    else:
        lines.append("  (tidak ada pattern recurring loss signifikan)")

    # === BRAND ANALYSIS ===
    profit_brand = by_brand[by_brand["Laba"] > 0].head(3)
    loss_brand   = by_brand[by_brand["Laba"] < 0].sort_values("Laba").head(3)

    lines += [f"", f"[ TOP 3 BRAND PALING UNTUNG ]"]
    for i, (name, r) in enumerate(profit_brand.iterrows(), 1):
        m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
        lines.append(f"  {i}. {str(name):<15} | {int(r['Qty']):>4} trx | Laba {rp(r['Laba'])} ({m:+.1f}%)")

    lines += [f"", f"[ TOP 3 BRAND PALING RUGI ]"]
    if len(loss_brand):
        for i, (name, r) in enumerate(loss_brand.iterrows(), 1):
            m = (r["Laba"]/r["Omset"]*100) if r["Omset"] else 0
            lines.append(f"  {i}. {str(name):<15} | {int(r['Qty']):>4} trx | Loss {rp(r['Laba'])} ({m:+.1f}%)")
    else:
        lines.append("  (semua brand net-profit)")

    # === REBATE IMPACT ===
    lines += [f"", f"[ DAMPAK REBATE HIKVISION & EZVIZ ]"]
    if reb:
        pct_rebate = (reb["total_rebate"]/df["LabaAdj"].sum()*100) if df["LabaAdj"].sum() else 0
        lines += [
            f"  Total rebate       : {rp(reb['total_rebate'])} ({pct_rebate:.1f}% dari laba net)",
            f"  Item Ezviz/Hik     : {reb['item_ezv_hik']} transaksi",
            f"  Diselamatkan rebate: {reb['diselamatkan']} item (dari rugi jadi profit)",
        ]

    # === REKOMENDASI ===
    lines += ["", "[ REKOMENDASI BISNIS ]"]
    if len(profit_brand):
        b_star = profit_brand.index[0]; v = profit_brand.iloc[0]["Laba"]
        lines.append(f"  1. Pertahankan stock & prioritas promo: brand {b_star} ({rp(v)}).")
    if len(loss_brand):
        b_worst = loss_brand.index[0]
        lines.append(f"  2. Evaluasi supplier / diskon: brand {b_worst}.")
    if len(top_loss_item):
        item_worst = top_loss_item.index[0]
        lines.append(f"  3. Item bermasalah: '{str(item_worst)[:45]}' — pertimbangkan naik harga atau stop pengadaan.")
    if len(recurring) >= 3:
        lines.append(f"  4. {len(recurring)} item recurring loss — audit pricing & sourcing.")
    if margin < 10:
        lines.append(f"  5. Margin {margin:.1f}% di bawah target industri (10-15%) — tinjau strategi pricing.")

    return "\n".join(lines)


# Dispatcher
def build_insight(df, label, date_range):
    """Route ke fungsi insight yang tepat berdasarkan label periode."""
    if "HARI INI" in label:
        return build_insight_today(df, label, date_range)
    if "7 HARI" in label:
        return build_insight_7d(df, label, date_range)
    if "30 HARI" in label:
        return build_insight_30d(df, label, date_range)
    return build_insight_7d(df, label, date_range)  # fallback

# ============ IMAGE — full detail table ============
def make_loss_table_image(df, title, subtitle, out_path):
    """Render HANYA transaksi rugi >5% dengan 9 kolom fokus:
       Tanggal | Invoice | Sales | Customer | Nama Barang | Qty | Omset | Laba | Margin"""
    losses = df[df["Margin"] < LOSS_THRESHOLD].sort_values("LabaAdj").reset_index(drop=True)
    if len(losses) == 0:
        return None

    cols = ["Tanggal", "Invoice", "Sales", "Customer", "Nama Barang", "Qty", "Omset", "Laba", "Margin"]

    rows, colors = [], []
    for _, r in losses.iterrows():
        row = [
            r["Tgl"].strftime("%d/%m/%y") if pd.notna(r["Tgl"]) else "-",
            str(r.get("No. Inv","-"))[:18],
            str(r.get("Nama Sales","-"))[:14],
            str(r.get("Nama Pelanggan","-"))[:22],
            str(r.get("Nama Barang","-"))[:38],
            str(r.get("Kts (","")).strip(),
            rp_short(r["TotalHarga"]),
            rp_short(r["LabaAdj"]),
            f"{r['Margin']*100:+.1f}%",
        ]
        # Warna intensitas merah berdasarkan margin
        m = r["Margin"]
        if m < -0.30:      bg = "#F8B4B4"   # merah kuat
        elif m < -0.15:    bg = "#FBD3D3"   # merah sedang
        else:              bg = "#FDECEA"   # merah muda
        rows.append(row); colors.append([bg]*len(cols))

    fig_h = max(3.5, 0.34 * (len(rows) + 3))
    fig, ax = plt.subplots(figsize=(20, fig_h))
    ax.axis("off")
    ax.text(0, 1.0, title, fontsize=16, fontweight="bold", color="#8B0000", transform=ax.transAxes)
    ax.text(0, 0.975, subtitle, fontsize=10, color="#555555", transform=ax.transAxes)

    tbl = ax.table(cellText=rows, colLabels=cols, cellColours=colors,
                   colColours=["#8B0000"]*len(cols), loc="center",
                   cellLoc="left", colLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9)
    tbl.scale(1, 1.30)
    for i in range(len(cols)):
        tbl[0, i].set_text_props(color="white", fontweight="bold")

    col_widths = [0.07, 0.11, 0.09, 0.15, 0.22, 0.04, 0.09, 0.09, 0.07]
    for i, w in enumerate(col_widths):
        for j in range(len(rows)+1):
            tbl[j, i].set_width(w)

    plt.savefig(out_path, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path

# --- STUB legacy (dipakai kalau perlu full table image untuk kebutuhan lain) ---
def make_full_table_image(df, title, subtitle, out_path, max_rows=None):
    """DEPRECATED: dulu untuk tabel semua transaksi. Sekarang pakai make_loss_table_image."""
    if len(df) == 0:
        return None
    df_sorted = df.sort_values("LabaAdj").reset_index(drop=True)
    if max_rows and len(df_sorted) > max_rows:
        rugi = df_sorted[df_sorted["Margin"] < LOSS_THRESHOLD]
        profit_slots = max(1, max_rows - len(rugi))
        profit = df_sorted[df_sorted["LabaAdj"] > 0].sort_values("LabaAdj", ascending=False).head(profit_slots)
        df_sorted = pd.concat([rugi, profit]).drop_duplicates().reset_index(drop=True)
        subtitle += f"   |   Ditampilkan: {len(df_sorted)} baris (lengkap di CSV)"

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

    plt.savefig(out_path, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path

def export_csv(df, out_path):
    """Export dataframe periode ke CSV untuk attach di email (jauh lebih ringan dari PNG)."""
    if len(df) == 0: return None
    cols_out = ["No. Inv", "Nama Sales", "Nama Pelanggan", "Tgl Inv",
                "Kode Pric", "Nama Barang", "Brand", "Kts (",
                "@Harga", "Total Harga", "BPP / HPP", "Laba", "Rebate", "LabaAdj", "Margin", "Diskon"]
    cols_exist = [c for c in cols_out if c in df.columns]
    df_out = df.sort_values("LabaAdj")[cols_exist].copy()
    if "Margin" in df_out.columns:
        df_out["Margin"] = (df_out["Margin"]*100).round(2).astype(str) + "%"
    df_out.to_csv(out_path, index=False, encoding="utf-8-sig")
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

def email_append_file(file_path, caption=""):
    """Attach file umum (CSV, dsb)."""
    if ENABLE_EMAIL:
        _email_buffer.setdefault("files", []).append((str(file_path), caption))

# Batas aman email (Gmail limit 25MB, kita cap 20MB untuk safety)
EMAIL_MAX_ATTACHMENT_MB = 5    # skip attach gambar > 5MB per file
EMAIL_MAX_TOTAL_MB      = 20   # total semua attachment

def email_flush():
    if not ENABLE_EMAIL or not EMAIL_RECIPIENTS: return
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from email.mime.base import MIMEBase
    from email import encoders

    body = "\n".join(_email_buffer["body"])
    subject = f"GSI Laba Rugi Report - {datetime.now().strftime('%d %b %Y %H:%M')}"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER
    msg["To"]   = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject

    skipped_note = []
    total_bytes  = 0
    max_per_file = EMAIL_MAX_ATTACHMENT_MB * 1024 * 1024
    max_total    = EMAIL_MAX_TOTAL_MB * 1024 * 1024

    # Attach images (skip yang > 5MB atau kalau total sudah mendekati limit)
    for path, cap in _email_buffer["images"]:
        try:
            size = Path(path).stat().st_size
            if size > max_per_file:
                skipped_note.append(f"[SKIP] {Path(path).name} ({size/1024/1024:.1f}MB) terlalu besar untuk email.")
                continue
            if total_bytes + size > max_total:
                skipped_note.append(f"[SKIP] {Path(path).name} melebihi total limit email.")
                continue
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-Disposition", "attachment", filename=Path(path).name)
            msg.attach(img)
            total_bytes += size
        except Exception as e:
            log(f"Email attach image fail {path}: {e}")

    # Attach files umum (CSV) — CSV kecil biasanya < 500KB, jarang skip
    for path, cap in _email_buffer.get("files", []):
        try:
            size = Path(path).stat().st_size
            if total_bytes + size > max_total:
                skipped_note.append(f"[SKIP] {Path(path).name} melebihi total limit email.")
                continue
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=Path(path).name)
            msg.attach(part)
            total_bytes += size
        except Exception as e:
            log(f"Email attach file fail {path}: {e}")

    if skipped_note:
        body += "\n\n" + "="*40 + "\nCATATAN:\n" + "\n".join(skipped_note)
        body += "\n(File berukuran besar dapat dilihat di Telegram atau Google Drive folder GSI Report Images)"

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as srv:
            srv.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())
        log(f"Email terkirim ke {len(EMAIL_RECIPIENTS)} recipient (total attachment ~{total_bytes/1024/1024:.1f}MB)")
    except Exception as e:
        log(f"Email FAIL: {e}")

    _email_buffer["body"].clear()
    _email_buffer["images"].clear()
    _email_buffer["files"] = []

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
        week_start  = today - timedelta(days=6)   # 7 hari termasuk hari ini
        month_start = today - timedelta(days=29)  # 30 hari termasuk hari ini

        periods = [
            ("HARI INI (Operational)", today, today, df[df["Tgl"].dt.date == today]),
            ("7 HARI TERAKHIR (Monitoring)", week_start, today,
                df[(df["Tgl"].dt.date >= week_start) & (df["Tgl"].dt.date <= today)]),
            ("30 HARI TERAKHIR (Business)", month_start, today,
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

        # === PER PERIODE: kirim INSIGHT text + GAMBAR RUGI >5% + CSV ===
        for label, d1, d2, sub in periods:
            date_range = f"{d1.strftime('%d %b %Y')} - {d2.strftime('%d %b %Y')}"
            slug = label.split(" (")[0].replace(" ","_")

            # 1) Insight text → semua channel (TG + WA + Email)
            insight = build_insight(sub, label, date_range)
            send_text(insight)

            if len(sub):
                # 2) GAMBAR khusus RUGI >5% (semua periode, kalau ada rugi)
                rugi_count = (sub["Margin"] < LOSS_THRESHOLD).sum()
                if rugi_count > 0:
                    img_path = IMG_DIR / f"rugi_{slug}_{today}.png"
                    title = f"TABEL RUGI >5% — {label}"
                    subtitle = f"Periode: {date_range}   |   {rugi_count} transaksi rugi >5%"
                    if make_loss_table_image(sub, title, subtitle, img_path):
                        tg_send_photo(img_path, caption=f"Rugi >5% | {label}")
                        wa_send_photo(img_path, caption=f"Rugi >5% | {label}")
                        email_append_image(img_path, caption=f"Rugi >5% {label}")

                # 3) CSV data lengkap → attach ke email saja
                csv_path = IMG_DIR / f"data_{slug}_{today}.csv"
                if export_csv(sub, csv_path):
                    email_append_file(csv_path, caption=label)

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
