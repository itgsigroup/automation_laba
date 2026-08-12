"""
GSI Weekly Sales & Profitability Brief
---------------------------------------
Generate PDF 2 halaman (Executive+Cabang, Sales+Rekomendasi) dengan:
- KPI Cards + delta WoW
- Chart: Revenue harian, Revenue vs Laba per Cabang, Top Sales, 8-week trend
- Tabel Cabang, Sales, Pelanggan, Brand
- Narasi AI otomatis (Gemini / Claude)

Trigger: Sabtu malam (via GitHub Actions weekly.yml)
"""

import io, os, sys, json
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
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

SHEET_ID   = env("SHEET_ID", "")
SHEET_GID  = env("SHEET_GID", "0")
CSV_URL    = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

BOT_TOKEN  = env("TG_BOT_TOKEN", "")
CHAT_IDS   = env_list("TG_CHAT_IDS", [])
FONNTE_TOKEN = env("FONNTE_TOKEN", "")
WA_NUMBERS   = env_list("WA_NUMBERS", [])
GMAIL_SENDER       = env("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS   = env_list("EMAIL_RECIPIENTS", [])

# AI providers (isi salah satu atau keduanya untuk fallback)
GEMINI_API_KEY = env("GEMINI_API_KEY", "")
CLAUDE_API_KEY = env("CLAUDE_API_KEY", "")
AI_PROVIDER    = env("AI_PROVIDER", "gemini")  # 'gemini' atau 'claude'

REBATE_BRANDS = ["ezviz", "hikvision"]
REBATE_RATE   = 0.05
LOSS_THRESHOLD = -0.05

OUT_DIR = BASE / "weekly_out"; OUT_DIR.mkdir(exist_ok=True)
LOG     = BASE / "weekly_log.txt"

# ============ HELPERS ============
def log(m):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {m}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line+"\n")

def rp_jt(n):
    if pd.isna(n): return "-"
    a = abs(n); s = "-" if n < 0 else ""
    if a >= 1e9: return f"{s}Rp{a/1e9:.2f} M"
    if a >= 1e6: return f"{s}Rp{a/1e6:.0f} jt"
    if a >= 1e3: return f"{s}Rp{a/1e3:.0f} rb"
    return f"{s}Rp{a:.0f}"

def parse_rp(s):
    if pd.isna(s): return 0.0
    s = str(s).strip()
    if not s or s == "-": return 0.0
    neg = s.startswith("-")
    s = s.lstrip("-").replace("Rp", "").replace(",", "").strip()
    try: v = float(s)
    except: v = 0.0
    return -v if neg else v

def parse_date(s):
    if pd.isna(s): return None
    for fmt in ("%d/%b/%Y", "%d/%B/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: continue
    return None

def pct_change(new, old):
    if old == 0 or pd.isna(old): return None
    return (new - old) / abs(old) * 100

def fmt_delta(v, suffix="%"):
    if v is None: return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}{suffix}"

# ============ FETCH & PREP ============
def fetch_data():
    log("Fetching Google Sheet...")
    r = requests.get(CSV_URL, timeout=60); r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [c.strip() for c in df.columns]

    df["Tgl"]        = df["Tgl Inv"].apply(parse_date)
    df["TotalHarga"] = df["Total Harga"].apply(parse_rp)
    df["HPP"]        = df["BPP / HPP"].apply(parse_rp)
    df["Laba"]       = df["Laba"].apply(parse_rp)
    df["BrandLower"] = df["Brand"].astype(str).str.lower().str.strip()
    is_rebate = df["BrandLower"].isin(REBATE_BRANDS)
    df["Rebate"] = 0.0
    df.loc[is_rebate, "Rebate"] = df.loc[is_rebate, "TotalHarga"] * REBATE_RATE
    df["LabaAdj"] = df["Laba"] + df["Rebate"]
    df["Margin"] = df.apply(lambda r: r["LabaAdj"]/r["TotalHarga"] if r["TotalHarga"] else 0.0, axis=1)
    df = df.dropna(subset=["Tgl"])
    log(f"Rows: {len(df)}")
    return df

def week_range(anchor_date):
    """Sen-Sab dari anchor (biasanya Sabtu)."""
    weekday = anchor_date.weekday()   # Mon=0 ... Sun=6
    # Kalau anchor bukan Sabtu, cari Sabtu terdekat sebelumnya
    days_back = (weekday - 5) % 7
    sat = anchor_date - timedelta(days=days_back)
    mon = sat - timedelta(days=5)
    return mon, sat

# ============ KPI ============
def kpi_period(df):
    if len(df) == 0:
        return dict(rev=0, laba=0, margin=0, n_inv=0, n_cust=0, aov=0, n_rows=0, loss=0, loss_pct=0)
    n_rows = len(df)
    rev = df["TotalHarga"].sum()
    laba = df["LabaAdj"].sum()
    margin = laba/rev*100 if rev else 0
    n_inv = df["No. Inv"].nunique() if "No. Inv" in df.columns else 0
    n_cust = df["Nama Pelanggan"].nunique() if "Nama Pelanggan" in df.columns else 0
    aov = rev/n_inv if n_inv else 0
    loss_rows = df[df["LabaAdj"] < 0]
    loss = loss_rows["LabaAdj"].sum()
    loss_pct = len(loss_rows)/n_rows*100 if n_rows else 0
    return dict(rev=rev, laba=laba, margin=margin, n_inv=n_inv, n_cust=n_cust,
                aov=aov, n_rows=n_rows, loss=abs(loss), loss_pct=loss_pct)

# ============ CHARTS ============
COLOR_ORANGE = "#E67E22"
COLOR_DARK   = "#2C3E50"
COLOR_RED    = "#C0392B"
COLOR_GREEN  = "#27AE60"

def chart_daily_revenue_margin(df_week, out_path):
    daily = df_week.groupby(df_week["Tgl"].dt.date).agg(
        Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum")).reset_index()
    daily["Margin"] = daily.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)
    daily["Label"] = daily["Tgl"].apply(lambda d: d.strftime("%a %d"))

    fig, ax1 = plt.subplots(figsize=(6, 3.5))
    ax1.bar(daily["Label"], daily["Rev"]/1e6, color=COLOR_ORANGE, alpha=0.85)
    ax1.set_ylabel("Revenue (Rp juta)", color=COLOR_DARK)
    ax2 = ax1.twinx()
    ax2.plot(daily["Label"], daily["Margin"], color=COLOR_DARK, marker='o', linewidth=2)
    for i, r in daily.iterrows():
        ax2.annotate(f"{r['Margin']:.1f}%", (i, r["Margin"]), textcoords="offset points",
                     xytext=(0,8), ha='center', fontsize=8, fontweight='bold')
    ax2.set_ylabel("Margin (%)", color=COLOR_DARK)
    ax1.set_title("Revenue & Margin Harian", fontsize=11, fontweight='bold', loc='left')
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches='tight')
    plt.close(fig)

def chart_branch(df_week, out_path):
    if "Nama Cabang" not in df_week.columns:
        return None
    g = df_week.groupby("Nama Cabang").agg(
        Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum")).sort_values("Rev", ascending=False)
    g["Margin"] = g.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    x = range(len(g))
    ax.bar([i-0.2 for i in x], g["Rev"]/1e6, width=0.4, label="Revenue", color=COLOR_ORANGE)
    ax.bar([i+0.2 for i in x], g["Laba"]/1e6, width=0.4, label="Laba", color=COLOR_DARK)
    for i, (name, r) in enumerate(g.iterrows()):
        ax.annotate(f"{r['Margin']:.1f}%", (i, r["Rev"]/1e6), textcoords="offset points",
                    xytext=(0,8), ha='center', fontsize=9, fontweight='bold', color=COLOR_RED)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(n)[:12] for n in g.index], rotation=15, ha='right')
    ax.set_ylabel("Rp juta")
    ax.set_title("Revenue vs Laba per Cabang (label = margin)", fontsize=11, fontweight='bold', loc='left')
    ax.legend(loc='upper right', fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches='tight')
    plt.close(fig)

def chart_top_sales(df_week, out_path):
    if "Nama Sales" not in df_week.columns:
        return None
    g = df_week.groupby("Nama Sales").agg(
        Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum")).sort_values("Rev", ascending=False).head(8)
    g["Margin"] = g.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)
    g = g.iloc[::-1]

    fig, ax = plt.subplots(figsize=(6, 3.5))
    y = range(len(g))
    ax.barh([i-0.2 for i in y], g["Rev"]/1e6, height=0.4, label="Revenue", color=COLOR_ORANGE)
    ax.barh([i+0.2 for i in y], g["Laba"]/1e6, height=0.4, label="Laba", color=COLOR_DARK)
    for i, (name, r) in enumerate(g.iterrows()):
        ax.annotate(f"{r['Margin']:.1f}%", (r["Rev"]/1e6, i), textcoords="offset points",
                    xytext=(6,0), va='center', fontsize=8, fontweight='bold',
                    color=COLOR_RED if r["Margin"] < 5 else COLOR_GREEN)
    ax.set_yticks(list(y))
    ax.set_yticklabels([str(n)[:15] for n in g.index])
    ax.set_xlabel("Rp juta")
    ax.set_title("Top 8 Sales (label = margin)", fontsize=11, fontweight='bold', loc='left')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches='tight')
    plt.close(fig)

def chart_8week_trend(df, sat_date, out_path):
    weeks = []
    for i in range(7, -1, -1):
        w_sat = sat_date - timedelta(weeks=i)
        w_mon = w_sat - timedelta(days=5)
        w_df = df[(df["Tgl"].dt.date >= w_mon) & (df["Tgl"].dt.date <= w_sat)]
        rev = w_df["TotalHarga"].sum()
        laba = w_df["LabaAdj"].sum()
        margin = laba/rev*100 if rev else 0
        weeks.append(dict(label=w_mon.strftime("%d %b"), rev=rev/1e9, margin=margin))
    wdf = pd.DataFrame(weeks)

    fig, ax1 = plt.subplots(figsize=(9, 3.2))
    colors = [COLOR_ORANGE]*8; colors[-1] = COLOR_RED
    ax1.bar(wdf["label"], wdf["rev"], color=colors, alpha=0.85)
    ax1.set_ylabel("Revenue (Rp M)", color=COLOR_DARK)
    ax2 = ax1.twinx()
    ax2.plot(wdf["label"], wdf["margin"], color=COLOR_DARK, marker='o', linewidth=2)
    for i, r in wdf.iterrows():
        ax2.annotate(f"{r['margin']:.1f}%", (i, r["margin"]), textcoords="offset points",
                     xytext=(0,8), ha='center', fontsize=8, fontweight='bold')
    ax2.set_ylabel("Margin (%)", color=COLOR_DARK)
    ax1.set_title("Tren 8 Minggu: Revenue & Margin (kolom merah = minggu berjalan)",
                  fontsize=11, fontweight='bold', loc='left')
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches='tight')
    plt.close(fig)

# ============ TABLES ============
def branch_wow_table(df_week, df_prev):
    if "Nama Cabang" not in df_week.columns: return pd.DataFrame()
    cur  = df_week.groupby("Nama Cabang").agg(Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum"))
    prev = df_prev.groupby("Nama Cabang").agg(RevPrev=("TotalHarga","sum"), LabaPrev=("LabaAdj","sum"))
    j = cur.join(prev, how="outer").fillna(0)
    j["Margin"] = j.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)
    j["MarginPrev"] = j.apply(lambda r: r["LabaPrev"]/r["RevPrev"]*100 if r["RevPrev"] else 0, axis=1)
    j["RevWoW"]  = j.apply(lambda r: pct_change(r["Rev"], r["RevPrev"]), axis=1)
    j["LabaWoW"] = j.apply(lambda r: pct_change(r["Laba"], r["LabaPrev"]), axis=1)
    return j.sort_values("Rev", ascending=False)

def sales_wow_table(df_week, df_prev):
    if "Nama Sales" not in df_week.columns: return pd.DataFrame()
    cur  = df_week.groupby("Nama Sales").agg(Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum"))
    prev = df_prev.groupby("Nama Sales").agg(RevPrev=("TotalHarga","sum"), LabaPrev=("LabaAdj","sum"))
    j = cur.join(prev, how="outer").fillna(0)
    j["Margin"] = j.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)
    j["MarginPrev"] = j.apply(lambda r: r["LabaPrev"]/r["RevPrev"]*100 if r["RevPrev"] else 0, axis=1)
    j["RevWoW"] = j.apply(lambda r: pct_change(r["Rev"], r["RevPrev"]), axis=1)
    j["LabaWoW"] = j.apply(lambda r: pct_change(r["Laba"], r["LabaPrev"]), axis=1)
    return j.sort_values("Rev", ascending=False)

def customer_table(df_week):
    if "Nama Pelanggan" not in df_week.columns: return pd.DataFrame()
    g = df_week.groupby("Nama Pelanggan").agg(Rev=("TotalHarga","sum"), Laba=("LabaAdj","sum"))
    g["Margin"] = g.apply(lambda r: r["Laba"]/r["Rev"]*100 if r["Rev"] else 0, axis=1)
    top_profit = g[g["Laba"] > 0].sort_values("Laba", ascending=False).head(3)
    top_loss   = g[g["Laba"] < 0].sort_values("Laba").head(3)
    return pd.concat([top_profit, top_loss])

# ============ AI NARRATIVE ============
def ai_narrative(prompt):
    """Try AI_PROVIDER first, fallback ke yang lain kalau gagal."""
    providers = [AI_PROVIDER, "gemini" if AI_PROVIDER=="claude" else "claude"]
    for p in providers:
        try:
            if p == "gemini" and GEMINI_API_KEY:
                return call_gemini(prompt)
            if p == "claude" and CLAUDE_API_KEY:
                return call_claude(prompt)
        except Exception as e:
            log(f"AI {p} failed: {e}")
    return "(narasi AI tidak tersedia — cek API key)"

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts":[{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def call_claude(prompt):
    url = "https://api.anthropic.com/v1/messages"
    headers = {"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": "claude-haiku-4-5-20251001", "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}]}
    r = requests.post(url, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()

def build_ai_prompts(kpi_cur, kpi_prev, branch_df, sales_df, cust_df, brand_top, brand_worst):
    """Return: exec_summary, so_what_ops, so_what_branch, so_what_brand, rekomendasi (list of dict)"""
    context = f"""
Data Weekly Report GSI:
Revenue minggu ini: Rp{kpi_cur['rev']/1e6:.0f}jt (WoW {fmt_delta(pct_change(kpi_cur['rev'], kpi_prev['rev']))})
Laba: Rp{kpi_cur['laba']/1e6:.0f}jt (WoW {fmt_delta(pct_change(kpi_cur['laba'], kpi_prev['laba']))})
Margin: {kpi_cur['margin']:.2f}% (minggu lalu {kpi_prev['margin']:.2f}%)
Total invoice: {kpi_cur['n_inv']}, pelanggan: {kpi_cur['n_cust']}, AOV: Rp{kpi_cur['aov']/1e6:.1f}jt
Kerugian dari transaksi: Rp{kpi_cur['loss']/1e6:.0f}jt ({kpi_cur['loss_pct']:.1f}% baris merugi)

Per Cabang:
{branch_df[['Rev','Laba','Margin','RevWoW','LabaWoW']].head(5).to_string()}

Top Sales:
{sales_df[['Rev','Laba','Margin']].head(6).to_string()}

Pelanggan bermasalah (laba negatif):
{cust_df[cust_df['Laba']<0].to_string() if len(cust_df[cust_df['Laba']<0]) else '(tidak ada)'}

Brand terbesar (laba): {brand_top}
Brand paling merugikan: {brand_worst}
"""
    prompts = {
        "exec": f"""Kamu analis bisnis distribusi CCTV. Berdasarkan data ini, tulis 1 paragraf ringkas (3-4 kalimat) executive summary weekly report untuk manajemen. Bahasa Indonesia profesional, langsung ke poin bisnis (bukan angka semata). Kalau margin naik atau turun signifikan, jelaskan implikasinya.

{context}""",
        "so_what_ops": f"""Tulis paragraf singkat 'SO WHAT?' operasional (2-3 kalimat) — apa yang HARUS DIJAGA agar minggu depan tidak turun. Bahasa Indonesia, actionable.

{context}""",
        "so_what_brand": f"""Tulis paragraf 'SO WHAT?' analisis brand (2-3 kalimat) — brand mana yang menghabiskan margin, dan apa yang harus dilakukan. Bahasa Indonesia, tegas.

{context}""",
        "rekomendasi": f"""Berdasarkan data, berikan 5 REKOMENDASI TINDAKAN prioritas untuk minggu depan. Setiap rekomendasi harus punya: (1) tindakan spesifik, (2) pemilik/PIC, (3) target terukur. Format sebagai JSON array:
[{{"prioritas":1, "tindakan":"...", "pemilik":"...", "target":"..."}}, ...]
Hanya return JSON, tanpa penjelasan lain.

{context}""",
    }

    return {
        "exec":         ai_narrative(prompts["exec"]),
        "so_what_ops":  ai_narrative(prompts["so_what_ops"]),
        "so_what_brand":ai_narrative(prompts["so_what_brand"]),
        "rekomendasi":  ai_narrative(prompts["rekomendasi"]),
    }

# ============ PDF LAYOUT ============
def render_pdf(sat_date, kpi_cur, kpi_prev, branch_df, sales_df, cust_df,
               ch_daily, ch_branch, ch_sales, ch_trend, ai, out_pdf):
    mon_date = sat_date - timedelta(days=5)
    period_str = f"{mon_date.strftime('%d')} – {sat_date.strftime('%d %B %Y')}"

    with PdfPages(out_pdf) as pdf:
        # ============ PAGE 1 — Executive + Cabang ============
        fig = plt.figure(figsize=(11.7, 16.5))   # A3 portrait
        fig.suptitle(f"GSI | WEEKLY SALES & PROFITABILITY BRIEF   —   {period_str}",
                     fontsize=14, fontweight='bold', y=0.98, color=COLOR_DARK)

        # KPI CARDS (row)
        cards = [
            ("REVENUE", rp_jt(kpi_cur["rev"]), fmt_delta(pct_change(kpi_cur["rev"], kpi_prev["rev"]))+" vs minggu lalu"),
            ("LABA KOTOR", rp_jt(kpi_cur["laba"]), fmt_delta(pct_change(kpi_cur["laba"], kpi_prev["laba"]))+" vs minggu lalu"),
            ("MARGIN", f"{kpi_cur['margin']:.2f}%", f"vs {kpi_prev['margin']:.2f}% mgg lalu"),
            ("INVOICE", f"{kpi_cur['n_inv']:,}", f"{kpi_cur['n_cust']} pelanggan"),
            ("AOV", rp_jt(kpi_cur["aov"]), f"{kpi_cur['n_rows']:,} baris"),
            ("KERUGIAN", rp_jt(kpi_cur["loss"]), f"{kpi_cur['loss_pct']:.1f}% baris rugi"),
        ]
        for i, (title, val, sub) in enumerate(cards):
            ax = fig.add_axes([0.05 + i*0.155, 0.86, 0.14, 0.06])
            ax.axis("off")
            ax.text(0.5, 0.85, val, fontsize=13, fontweight='bold', ha='center', color=COLOR_ORANGE)
            ax.text(0.5, 0.45, title, fontsize=8, ha='center', color=COLOR_DARK, fontweight='bold')
            ax.text(0.5, 0.15, sub, fontsize=7, ha='center', color="gray")

        # Exec summary
        ax = fig.add_axes([0.05, 0.72, 0.9, 0.12])
        ax.axis("off")
        ax.text(0, 1, ai.get("exec", "")[:2000], fontsize=10, va='top', wrap=True, color=COLOR_DARK)

        # SO WHAT? operational
        ax = fig.add_axes([0.05, 0.62, 0.9, 0.08])
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0.02", ec=COLOR_ORANGE, fc="#FFF3E0", transform=ax.transAxes))
        ax.text(0.02, 0.85, "SO WHAT?", fontsize=10, fontweight='bold', color=COLOR_ORANGE, transform=ax.transAxes, va='top')
        ax.text(0.02, 0.60, ai.get("so_what_ops","")[:1000], fontsize=9, color=COLOR_DARK, transform=ax.transAxes, va='top', wrap=True)

        # Charts
        ax = fig.add_axes([0.05, 0.40, 0.42, 0.20])
        ax.axis("off"); ax.imshow(plt.imread(ch_daily))
        ax = fig.add_axes([0.53, 0.40, 0.42, 0.20])
        ax.axis("off"); ax.imshow(plt.imread(ch_branch))

        # Branch table
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.33])
        ax.axis("off")
        ax.text(0, 1, "Perbandingan Minggu-ke-Minggu per Cabang", fontsize=11, fontweight='bold', color=COLOR_DARK, transform=ax.transAxes)
        rows = []
        for name, r in branch_df.head(6).iterrows():
            rows.append([
                str(name)[:18],
                f"{r['Rev']/1e6:.0f}",
                fmt_delta(r['RevWoW']),
                f"{r['Laba']/1e6:.0f}",
                fmt_delta(r['LabaWoW']),
                f"{r['Margin']:.2f}%",
                f"{r['MarginPrev']:.2f}%",
            ])
        # Total row
        tot_rev = branch_df["Rev"].sum(); tot_laba = branch_df["Laba"].sum()
        tot_rev_prev = branch_df["RevPrev"].sum(); tot_laba_prev = branch_df["LabaPrev"].sum()
        rows.append(["TOTAL",
                     f"{tot_rev/1e6:.0f}", fmt_delta(pct_change(tot_rev, tot_rev_prev)),
                     f"{tot_laba/1e6:.0f}", fmt_delta(pct_change(tot_laba, tot_laba_prev)),
                     f"{tot_rev and tot_laba/tot_rev*100:.2f}%",
                     f"{tot_rev_prev and tot_laba_prev/tot_rev_prev*100:.2f}%"])
        cols = ["Cabang", "Rev (jt)", "vs Lalu", "Laba (jt)", "vs Lalu", "Margin", "Mgg Lalu"]
        colors = [["#FDF6E4"]*len(cols) if i%2 else ["white"]*len(cols) for i in range(len(rows))]
        colors[-1] = ["#FFE0B2"]*len(cols)  # total row
        tbl = ax.table(cellText=rows, colLabels=cols, cellColours=colors,
                       colColours=[COLOR_ORANGE]*len(cols), loc="upper center", cellLoc="left")
        tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.3)
        for i in range(len(cols)):
            tbl[0, i].set_text_props(color="white", fontweight="bold")

        pdf.savefig(fig); plt.close(fig)

        # ============ PAGE 2 — Sales + Rekomendasi ============
        fig = plt.figure(figsize=(11.7, 16.5))
        fig.suptitle(f"GSI | KINERJA SALES & TINDAK LANJUT   —   {period_str}",
                     fontsize=14, fontweight='bold', y=0.98, color=COLOR_DARK)

        # Top sales chart
        ax = fig.add_axes([0.05, 0.72, 0.42, 0.22])
        ax.axis("off"); ax.imshow(plt.imread(ch_sales))

        # 8-week trend chart
        ax = fig.add_axes([0.53, 0.72, 0.42, 0.22])
        ax.axis("off"); ax.imshow(plt.imread(ch_trend))

        # SO WHAT brand
        ax = fig.add_axes([0.05, 0.62, 0.9, 0.08])
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0.02", ec=COLOR_RED, fc="#FFEBEE", transform=ax.transAxes))
        ax.text(0.02, 0.85, "MASALAH UTAMA", fontsize=10, fontweight='bold', color=COLOR_RED, transform=ax.transAxes, va='top')
        ax.text(0.02, 0.60, ai.get("so_what_brand","")[:1000], fontsize=9, color=COLOR_DARK, transform=ax.transAxes, va='top', wrap=True)

        # Sales table
        ax = fig.add_axes([0.05, 0.35, 0.9, 0.25])
        ax.axis("off")
        ax.text(0, 1, "Kinerja Sales (Top 8 by Revenue)", fontsize=11, fontweight='bold', color=COLOR_DARK, transform=ax.transAxes)
        rows = []
        for name, r in sales_df.head(8).iterrows():
            note = "Merugi — intervensi" if r['Margin'] < 0 else ("Perlu review" if r['Margin'] < 4 else ("Konsisten" if r['Margin'] > 10 else "OK"))
            rows.append([
                str(name)[:18],
                f"{r['Rev']/1e6:.0f}",
                f"{r['Laba']/1e6:.0f}",
                f"{r['Margin']:.2f}%",
                f"{r['MarginPrev']:.2f}%",
                note,
            ])
        cols = ["Sales", "Rev (jt)", "Laba (jt)", "Margin", "Mgg Lalu", "Catatan"]
        colors = [["#FDF6E4"]*len(cols) if i%2 else ["white"]*len(cols) for i in range(len(rows))]
        tbl = ax.table(cellText=rows, colLabels=cols, cellColours=colors,
                       colColours=[COLOR_ORANGE]*len(cols), loc="upper center", cellLoc="left")
        tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.3)
        for i in range(len(cols)):
            tbl[0, i].set_text_props(color="white", fontweight="bold")

        # Rekomendasi table
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.28])
        ax.axis("off")
        ax.text(0, 1, "Tindakan Minggu Depan (Rekomendasi AI)", fontsize=11, fontweight='bold', color=COLOR_DARK, transform=ax.transAxes)
        rows = []
        try:
            rec_json = ai.get("rekomendasi", "[]")
            # Bersihkan kalau ada markdown code fence
            rec_json = rec_json.replace("```json","").replace("```","").strip()
            rec_list = json.loads(rec_json)
            for r in rec_list[:5]:
                rows.append([str(r.get("prioritas","?")),
                             str(r.get("tindakan",""))[:60],
                             str(r.get("pemilik",""))[:20],
                             str(r.get("target",""))[:30]])
        except Exception as e:
            log(f"Parse rekomendasi fail: {e}")
            rows = [["1", "Review pricing brand paling merugikan", "Sales Director", "Margin > 0% dalam 1 minggu"]]

        cols = ["No", "Tindakan", "Pemilik", "Target"]
        colors = [["#FDF6E4"]*len(cols) if i%2 else ["white"]*len(cols) for i in range(len(rows))]
        tbl = ax.table(cellText=rows, colLabels=cols, cellColours=colors,
                       colColours=[COLOR_ORANGE]*len(cols), loc="upper center", cellLoc="left")
        tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.5)
        for i in range(len(cols)):
            tbl[0, i].set_text_props(color="white", fontweight="bold")
        for j in range(len(rows)+1):
            tbl[j, 0].set_width(0.05)
            tbl[j, 1].set_width(0.50)
            tbl[j, 2].set_width(0.18)
            tbl[j, 3].set_width(0.27)

        pdf.savefig(fig); plt.close(fig)

    log(f"PDF saved: {out_pdf}")
    return out_pdf

# ============ SEND ============
def tg_send_photo_pdf(pdf_path, caption=""):
    if not BOT_TOKEN or not CHAT_IDS: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    for cid in CHAT_IDS:
        with open(pdf_path, "rb") as f:
            r = requests.post(url, data={"chat_id": cid, "caption": caption[:1024]},
                              files={"document": f}, timeout=60)
        log(f"TG doc -> {cid}: {r.status_code}")

def wa_send_pdf(pdf_path, caption=""):
    if not FONNTE_TOKEN or not WA_NUMBERS: return
    url = "https://api.fonnte.com/send"
    for num in WA_NUMBERS:
        with open(pdf_path, "rb") as f:
            r = requests.post(url,
                data={"target": num, "message": caption[:1000], "countryCode": "62"},
                files={"file": f},
                headers={"Authorization": FONNTE_TOKEN}, timeout=60)
        log(f"WA doc -> {num}: {r.status_code} {r.text[:100]}")

def email_send_pdf(pdf_path, subject, body):
    if not GMAIL_SENDER or not EMAIL_RECIPIENTS: return
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER; msg["To"] = ", ".join(EMAIL_RECIPIENTS); msg["Subject"] = subject
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
        log(f"Email PDF sent ke {len(EMAIL_RECIPIENTS)} recipients")
    except Exception as e:
        log(f"Email FAIL: {e}")

# ============ MAIN ============
def main():
    try:
        df = fetch_data()
        now_wib = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)
        mon, sat = week_range(now_wib.date())
        prev_mon = mon - timedelta(days=7); prev_sat = sat - timedelta(days=7)

        df_week = df[(df["Tgl"].dt.date >= mon) & (df["Tgl"].dt.date <= sat)]
        df_prev = df[(df["Tgl"].dt.date >= prev_mon) & (df["Tgl"].dt.date <= prev_sat)]

        log(f"Periode: {mon} - {sat} | rows: {len(df_week)}")
        log(f"Sebelumnya: {prev_mon} - {prev_sat} | rows: {len(df_prev)}")

        # KPI
        kpi_cur = kpi_period(df_week)
        kpi_prev = kpi_period(df_prev)

        # Tables
        branch = branch_wow_table(df_week, df_prev)
        sales  = sales_wow_table(df_week, df_prev)
        cust   = customer_table(df_week)

        # Brand top/worst
        by_brand = df_week.groupby("Brand")["LabaAdj"].sum().sort_values(ascending=False)
        brand_top   = by_brand.index[0] if len(by_brand) else "-"
        brand_worst = by_brand.index[-1] if len(by_brand) else "-"

        # Charts
        stamp = sat.strftime("%Y%m%d")
        ch_daily  = OUT_DIR / f"ch_daily_{stamp}.png"
        ch_branch = OUT_DIR / f"ch_branch_{stamp}.png"
        ch_sales  = OUT_DIR / f"ch_sales_{stamp}.png"
        ch_trend  = OUT_DIR / f"ch_trend_{stamp}.png"
        chart_daily_revenue_margin(df_week, ch_daily)
        chart_branch(df_week, ch_branch)
        chart_top_sales(df_week, ch_sales)
        chart_8week_trend(df, sat, ch_trend)

        # AI Narrative
        log("Generating AI narrative...")
        ai = build_ai_prompts(kpi_cur, kpi_prev, branch, sales, cust, brand_top, brand_worst)

        # PDF
        pdf_path = OUT_DIR / f"Weekly_Brief_GSI_{mon.strftime('%d')}-{sat.strftime('%d_%b_%Y')}.pdf"
        render_pdf(sat, kpi_cur, kpi_prev, branch, sales, cust,
                   ch_daily, ch_branch, ch_sales, ch_trend, ai, pdf_path)

        # Send
        caption = f"Weekly Sales Brief GSI\n{mon.strftime('%d')} - {sat.strftime('%d %b %Y')}\nRevenue: {rp_jt(kpi_cur['rev'])} | Margin: {kpi_cur['margin']:.2f}%"
        tg_send_photo_pdf(pdf_path, caption)
        wa_send_pdf(pdf_path, caption)
        email_send_pdf(pdf_path,
                       subject=f"GSI Weekly Brief {mon.strftime('%d')}-{sat.strftime('%d %b %Y')}",
                       body=caption + "\n\nDetail lengkap ada di PDF terlampir.")

        log("Weekly report SELESAI.")
    except Exception as e:
        err = f"ERROR: {type(e).__name__}: {e}"
        log(err)
        import traceback; log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
