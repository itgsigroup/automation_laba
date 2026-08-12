# PANDUAN PEMBUATAN LAPORAN PENJUALAN & PROFITABILITAS GSI
### Prompt Master + Ketentuan Teknis Lengkap

**Versi 1.0 — Agustus 2026**
Dokumen ini berisi prompt siap pakai dan seluruh ketentuan yang harus dipenuhi untuk menghasilkan *Weekly Brief* (2 halaman) dan *Monthly / Full Report* (20–25 halaman) dengan kualitas dan tampilan yang konsisten.

---

## BAGIAN 1 — PROMPT MASTER

### 1.1 Prompt Weekly Brief (2 halaman)

> Salin blok di bawah ini, ganti bagian dalam `[kurung siku]`, lampirkan file data.

```
Bertindaklah sebagai Senior Business Analyst dengan spesialisasi profitabilitas
distribusi B2B. Buatkan WEEKLY BRIEF dari data penjualan terlampir.

PERIODE
- Periode analisis: [3 s/d 8 Agustus 2026]
- Periode pembanding: minggu sebelumnya dengan jumlah hari kerja yang sama
  (bukan 7 hari kalender mentah)
- Pembanding kedua: rata-rata margin YTD tahun berjalan

STRUKTUR DATA
Kolom yang tersedia: Nama Cabang, Nama Sales, ID Pelanggan, Nama Pelanggan,
Tgl Inv, Tahun, No. Inv, Kode Barang, Nama Barang, Brand, Nama Kategori Barang,
Diskon, Kts (qty), @Harga, Total Harga, BPP/HPP, Laba, Bulan, Jenis Sales,
Kuartal, Harga Tanpa PPN.

OUTPUT YANG DIMINTA
1. Uraian analisis terstruktur di chat.
2. Satu file PDF profesional MAKSIMAL 2 HALAMAN, bahasa Indonesia, berisi:

   HALAMAN 1
   a. Baris KPI: Revenue, Laba Kotor, Margin, Jumlah Invoice, AOV, Kerugian
      — setiap KPI wajib menyertakan perbandingan terhadap periode sebelumnya
   b. Paragraf pembuka: kesimpulan utama minggu ini dalam 3–4 kalimat
   c. Grafik: revenue & margin harian; revenue vs laba per cabang
   d. Grafik tren 8 minggu terakhir (revenue batang + margin garis)
   e. Tabel perbandingan minggu-ke-minggu per cabang, kolom wajib:
      Revenue, Δ Revenue %, Laba, Δ Laba %, Margin, Margin minggu lalu, Status

   HALAMAN 2
   f. Grafik kontribusi brand bermasalah vs sisanya (revenue vs laba)
   g. Grafik top 8 sales dengan label margin
   h. Tabel perbandingan minggu-ke-minggu per sales dan brand
   i. EXIT WATCHLIST: objek yang memenuhi Gate 1/2/3 beserta tindakan & tenggat
   j. Tindakan minggu depan dengan pemilik dan target terukur

KETENTUAN WAJIB
- Setiap bagian analisis diakhiri blok "SO WHAT?" berisi makna bisnis, bukan
  pengulangan angka
- Setiap perbandingan periode harus menyatakan secara eksplisit apakah
  NAIK atau TURUN, berikut besaran persentase dan poin persentase margin
- Bedakan tegas: penurunan laba karena VOLUME vs karena HARGA
- Jangan merekomendasikan penghentian produk bervolume besar; gunakan
  kerangka Exit Gate (lampiran)
- Sertakan keterbatasan data secara jujur di catatan kaki
- Verifikasi ulang seluruh angka terhadap data mentah sebelum finalisasi
```

---

### 1.2 Prompt Monthly / Full Report (20–25 halaman)

```
Bertindaklah sebagai Senior Business Analyst dengan pengalaman transformasi
bisnis dan optimalisasi profitabilitas. Buatkan LAPORAN LENGKAP dari data
penjualan terlampir.

PERIODE
- Fokus utama: [FY2026 YTD / bulan berjalan]
- Pembanding tren: [FY2024 dan FY2025]
- Pembanding periode berjalan: rolling 30 hari terakhir vs 30 hari sebelumnya

TUJUAN
Menghasilkan wawasan strategis yang dapat dieksekusi untuk: (1) menaikkan
margin laba, (2) memperbaiki arus kas, (3) meningkatkan pendapatan.

STRUKTUR DOKUMEN PDF (bahasa Indonesia, profesional)

BAB 1 — EXECUTIVE SUMMARY
1.1 Ringkasan kesehatan bisnis + baris KPI
1.2 Visualisasi kinerja inti: tren bulanan multi-tahun, revenue & laba per
    cabang, laba per cabang antar tahun, matriks performa sales, kontribusi
    brand, kontribusi kategori, top customer
1.3 Tabel top 10 customer dengan margin
1.4 PERBANDINGAN PERIODE BERJALAN — 30 hari terakhir vs 30 hari sebelumnya:
    KPI delta, grafik laba & margin per cabang antar periode, tren 8 minggu,
    pergeseran margin per brand

BAB 2 — DEEP DIVE
2.1 Portofolio produk: matriks Cash Cow / Star / Question Mark / Dog
2.2 Efisiensi cabang: margin, laba per invoice, tingkat diskon, eksposur
    brand bermasalah, praktik terbaik yang dapat diduplikasi
2.3 Analisis sales: produktivitas vs profitabilitas, analisis per kanal

BAB 3 — LOSS ANALYSIS & MITIGATION
3.1 Peta kerugian per cabang, kategori, sales, customer
3.2 Root cause analysis (minimal 4 akar penyebab berbasis data)
3.3 Strategi mitigasi + keputusan tegas per objek

BAB 4 — STRATEGI CASHFLOW & LABA
4.1 Tuas perbaikan siklus konversi kas
4.2 Peluang cross-selling & up-selling berbasis analisis keranjang belanja

BAB 5 — ACTIONABLE NEXT STEPS
5.1 Quick Wins 30 hari: tindakan, pemilik, dampak laba, ukuran keberhasilan
5.2 Strategic Initiatives 3–6 bulan
5.3 Ambisi konsolidasi (proyeksi laba tahunan)

BAB 6 — EXIT PLAN
6.1 Kriteria keputusan (Exit Gates) untuk SKU, pelanggan, brand, cabang
6.2 Hasil penerapan kriteria pada data aktual, dipisah per tier
6.3 Tahapan pelaksanaan wind-down F0–F5
6.4 Risiko exit & mitigasinya
6.5 Ringkasan dampak finansial

LAMPIRAN — Catatan metodologi & batasan data

KETENTUAN WAJIB
- Setiap sub-bab diakhiri blok "SO WHAT?"
- Seluruh estimasi dampak dihitung dengan metode yang dinyatakan eksplisit
- Nyatakan asumsi dan batasan secara jujur, termasuk data yang tidak tersedia
- Angka tahunan yang diekstrapolasi harus diberi label "anualisasi"
```

---

## BAGIAN 2 — KETENTUAN PENYIAPAN DATA

### 2.1 Pembersihan wajib

| Langkah | Ketentuan |
|---|---|
| Format mata uang | Hapus `Rp`, koma pemisah ribuan, dan spasi. Tangani format negatif dalam kurung `(1.000)` → `-1000` |
| Tanggal | Parse format `d/Mon/yyyy` (contoh `2/Jan/2024`). Verifikasi nol nilai gagal-parse |
| Kuantitas | Kolom `Kts` sering mengandung spasi dan koma — bersihkan sebelum konversi |
| Nilai kosong | Kolom `Laba` boleh kosong; isi dengan `Harga Tanpa PPN − BPP/HPP` |
| Validasi silang | Bandingkan kolom `Laba` dengan perhitungan ulang. Korelasi wajib > 0,99. Jika di bawah itu, hentikan dan laporkan |

### 2.2 Definisi baku

- **Revenue** = kolom `Total Harga` (termasuk PPN)
- **Laba** = laba **kotor** = `Harga Tanpa PPN − BPP/HPP`. **Bukan** laba bersih
- **Margin** = Laba ÷ Revenue × 100
- **AOV** = Revenue ÷ jumlah invoice unik (`No. Inv`)
- **Baris merugi** = baris transaksi dengan `Laba < 0`
- **Kebocoran laba** = total kerugian ÷ total laba positif × 100
- **Anualisasi** = nilai periode × (365 ÷ jumlah hari periode)

### 2.3 Aturan pemilihan periode pembanding

| Jenis laporan | Periode utama | Pembanding |
|---|---|---|
| Weekly | Senin–Sabtu | Senin–Sabtu minggu sebelumnya |
| Monthly | Rolling 30 hari terakhir | 30 hari sebelumnya (bukan bulan kalender) |
| Tren | 8 minggu terakhir | — |
| Tahunan | Tahun berjalan YTD | Tahun-tahun sebelumnya, dengan catatan periode parsial |

> **Aturan kritis:** jangan bandingkan periode dengan jumlah hari berbeda tanpa menyatakannya. Jika data berhenti di tengah bulan, sebut secara eksplisit dan gunakan anualisasi untuk proyeksi.

---

## BAGIAN 3 — KETENTUAN ANALISIS

### 3.1 Analisis wajib ada

1. **Dekomposisi volume vs harga.** Jika laba turun, tentukan penyebabnya: revenue turun (volume) atau margin turun (harga). Ini menentukan seluruh rekomendasi.
2. **Konsentrasi.** Kontribusi Top 5 / 10 / 20 terhadap revenue **dan** terhadap laba. Ketimpangan keduanya adalah temuan.
3. **Persistensi kerugian.** Bagi periode menjadi dua bagian; objek yang merugi di **kedua** bagian = masalah struktural. Yang merugi di salah satu = anomali.
4. **Erosi diskon.** Kelompokkan transaksi ke bucket diskon (0%, 0–5%, 5–10%, 10–20%, >20%) dan bandingkan margin tiap bucket.
5. **Attach rate.** Untuk invoice yang memuat produk utama, hitung persentase yang menyertakan produk pendamping bermargin tinggi.
6. **Inversi produktivitas.** Uji apakah sales/cabang bervolume besar justru bermargin rendah.
7. **Analisis kanal.** Bandingkan margin antar jenis penjualan (Distribusi, Project, Marketplace).

### 3.2 Metode estimasi dampak — wajib konsisten

```
Dampak = (margin_pembanding × revenue_aktual) − laba_aktual
```

- `margin_pembanding` = rata-rata perusahaan, atau margin unit terbaik
- Selalu cantumkan bahwa perhitungan **mengasumsikan tidak ada elastisitas volume**
- Selalu sertakan skenario konservatif **60–70%** dari nilai estimasi
- Untuk dampak tahunan, kalikan faktor anualisasi dan beri label jelas

### 3.3 Kerangka Exit Gate (baku)

| Objek | Gate 1 — Peringatan | Gate 2 — Perbaikan (60 hari) | Gate 3 — EXIT | Pengecualian |
|---|---|---|---|---|
| SKU | Margin negatif 1 periode | Margin negatif 2 periode **dan** revenue < Rp500 jt/thn | Re-pricing gagal dalam 60 hari | SKU wajib-lini principal; SKU pemicu attach terbukti > 30% |
| Pelanggan | Margin < 2% selama 2 bulan | Margin negatif 2 periode | Menolak margin minimum 4% setelah 2 negosiasi | Kontrak proyek berjalan; margin agregat > 6% |
| Brand | Margin < separuh rata-rata perusahaan | Margin negatif 2 bulan | Renegosiasi principal gagal + margin negatif 6 bulan | Peran traffic-driver terbukti |
| Cabang | Margin < 4% selama 1 kuartal | Margin < 4% selama 2 kuartal | Laba negatif 3 kuartal setelah biaya operasional | Cabang berumur < 24 bulan |

**Aturan pemisahan tier — jangan dilanggar:**

- Revenue **< Rp500 juta** + rugi persisten → **EXIT**
- Revenue **≥ Rp500 juta** + rugi persisten → **RE-PRICE**, bukan exit

> Prinsipnya: *bedah, bukan amputasi*. Kerugian besar pada produk bervolume besar berarti perbaiki harga. Kerugian kecil berulang pada produk bervolume kecil berarti hentikan.

---

## BAGIAN 4 — KETENTUAN VISUAL

### 4.1 Palet warna baku

| Peran | Hex |
|---|---|
| Aksen utama | `#D04A02` |
| Teks & batang sekunder | `#2D2D2D` |
| Positif / di atas target | `#299D8F` |
| Negatif / rugi | `#C0392B` |
| Netral / periode pembanding | `#D8D8D8` |
| Peringatan | `#EBB700` |
| Latar blok SO WHAT | `#FBF5F1` |

### 4.2 Ketentuan grafik

- **Wajib**: judul rata kiri dan tebal; hilangkan garis tepi atas & kanan; sertakan label nilai pada batang penting
- **Perbandingan periode**: periode lama abu-abu (`#D8D8D8`), periode baru oranye (`#D04A02`) — selalu berdampingan, jangan bertumpuk
- **Margin**: selalu garis dengan penanda titik pada sumbu sekunder, jangan batang
- **Warna kondisional**: label margin berwarna hijau bila di atas rata-rata, merah bila di bawah
- **Skala log**: gunakan untuk sebaran SKU (rentang nilai sangat lebar)
- **Garis acuan**: selalu tambahkan garis putus-putus rata-rata perusahaan pada grafik margin
- **DPI**: minimal 150 untuk laporan penuh, 170 untuk brief 2 halaman

### 4.3 Grafik wajib per jenis laporan

**Weekly (5 grafik):** revenue & margin harian · revenue vs laba per cabang · tren 8 minggu · brand bermasalah vs sisanya · top 8 sales

**Monthly/Full (16 grafik):** tren bulanan multi-tahun · cabang (revenue/laba + margin) · laba per cabang antar tahun · top sales · matriks sales · kategori (kontributor + terendah) · brand (pie revenue vs laba) · top customer · matriks BCG produk · peta kerugian · erosi diskon · brand bermasalah bulanan · perbandingan 30 hari per cabang · tren 8 minggu · pergeseran margin brand · peta keputusan exit

---

## BAGIAN 5 — KETENTUAN TATA LETAK PDF

### 5.1 Spesifikasi umum

| Elemen | Weekly (2 hal) | Monthly (20–25 hal) |
|---|---|---|
| Ukuran | A4 | A4 |
| Margin kiri/kanan | 1,4 cm | 2,0 cm |
| Font isi | Helvetica 7,5 pt | Helvetica 9,3 pt |
| Font tabel | 6,4 pt | 7,8 pt |
| Header | Pita oranye + judul + periode | Pita oranye + judul |
| Footer | Sumber data + batasan + nomor halaman | Idem |
| Sampul | Tidak ada | Wajib, latar gelap dengan KPI utama |

### 5.2 Komponen baku

- **Baris KPI**: kotak berlatar `#FBF5F1`, nilai besar + label kecil, wajib memuat pembanding
- **Blok SO WHAT**: latar `#FBF5F1`, garis vertikal oranye di kiri, teks tebal
- **Tabel**: header gelap, baris berselang-seling, sorot baris bermasalah dengan `#FBE9E7` dan baris unggulan dengan `#E8F5F3`
- **Keterangan gambar**: miring, 6–8 pt, abu-abu, tepat di bawah grafik

### 5.3 Aturan menjaga batas halaman

Bila melebihi batas halaman, kompres dengan urutan berikut:

1. Kurangi lebar grafik (jangan hapus grafiknya)
2. Gabungkan tabel yang berisi objek serupa
3. Kurangi jumlah baris tabel, pertahankan yang paling material
4. Ringkas paragraf — **jangan hapus blok SO WHAT**
5. Baru terakhir: kurangi ukuran font

> Verifikasi jumlah halaman secara programatik setelah render, jangan diperkirakan.

---

## BAGIAN 6 — KETENTUAN PENULISAN

### 6.1 Aturan wajib

1. **Setiap bagian diakhiri "SO WHAT?"** — berisi implikasi bisnis dan nilai rupiah, bukan pengulangan angka
2. **Kuantifikasi setiap rekomendasi.** "Perbaiki margin Surabaya" ✗ → "Menaikkan Surabaya ke margin Kantor Pusat bernilai Rp808 juta pada revenue yang sama" ✓
3. **Bahasa Indonesia baku**, istilah teknis Inggris hanya bila tidak ada padanan mapan
4. **Format angka Indonesia**: koma sebagai desimal, titik sebagai pemisah ribuan (`Rp3,66 Miliar`; `7,81%`)
5. **Selisih margin dalam poin persentase (pp)**, bukan persen — perbedaan 6% ke 8% adalah **2 pp**, bukan 33%
6. **Rekomendasi harus punya pemilik dan tenggat.** Tanpa keduanya, itu bukan rekomendasi
7. **Nyatakan batasan dengan jujur.** Bila DSO tidak dapat dihitung karena data tidak ada, katakan — jangan mengarang
8. **Hindari nada alarmis maupun terlalu optimistis.** Revenue turun 12% dengan laba naik 32% adalah kabar baik; katakan demikian

### 6.2 Struktur paragraf pembuka yang efektif

```
[Kesimpulan satu kalimat yang tegas]
[Angka pendukung utama + arah pergerakan vs periode sebelumnya]
[Kualifikasi atau masalah yang tersisa]
```

Contoh: *"Minggu yang sehat, dengan satu masalah lama yang belum tersentuh. Revenue turun 11,9% menjadi Rp3,66 Miliar, namun laba kotor justru naik 32,4%. Margin melompat dari 5,20% ke 7,81% — di atas rata-rata YTD."*

---

## BAGIAN 7 — DAFTAR PERIKSA VERIFIKASI

Jalankan seluruhnya **sebelum** menyerahkan dokumen:

- [ ] Total revenue dan laba cocok dengan agregasi data mentah
- [ ] Seluruh margin dihitung ulang dari revenue dan laba, bukan disalin
- [ ] Persentase perubahan periode diverifikasi dua arah (naik/turun sesuai tanda)
- [ ] Seluruh angka anualisasi menggunakan faktor yang benar (365 ÷ hari data)
- [ ] Klaim naratif cocok dengan tabel — khususnya pernyataan berjenis "5 dari 7"
- [ ] Jumlah halaman diverifikasi secara programatik
- [ ] Seluruh grafik dibuka dan diperiksa: label tidak bertumpuk, teks terbaca
- [ ] Tidak ada karakter subskrip/superskrip Unicode (menyebabkan kotak hitam)
- [ ] Periode dan tanggal pembanding disebut eksplisit di dokumen
- [ ] Batasan data tercantum di catatan kaki atau lampiran
- [ ] Setiap rekomendasi punya pemilik, tenggat, dan ukuran keberhasilan

---

## BAGIAN 8 — KESALAHAN YANG SERING TERJADI

| Kesalahan | Akibat | Pencegahan |
|---|---|---|
| Membandingkan periode dengan jumlah hari berbeda | Kesimpulan menyesatkan | Samakan jumlah hari kerja, atau nyatakan perbedaannya |
| Merekomendasikan cut-off produk bervolume besar | Kehilangan revenue besar demi kerugian kecil | Terapkan ambang Rp500 juta |
| Menyebut laba kotor sebagai "laba" tanpa kualifikasi | Manajemen salah menilai profitabilitas | Selalu tulis "laba kotor" dan cantumkan di catatan kaki |
| Mengarang analisis cashflow tanpa data piutang | Rekomendasi tidak dapat dieksekusi | Nyatakan batasan, susun rekomendasi dari struktur penjualan |
| Menyamakan selisih margin dengan persen | Salah besaran hingga berkali lipat | Gunakan satuan poin persentase (pp) |
| Estimasi dampak tanpa metode eksplisit | Angka tidak dapat diaudit | Cantumkan rumus dan asumsinya |
| Menimpa file lama di folder pengguna | Gagal simpan | Gunakan penamaan berversi (`_v2`, `_v3`) |

---

## BAGIAN 9 — PROMPT SINGKAT UNTUK PENGGUNAAN RUTIN

Setelah dokumen pertama terbentuk, cukup gunakan:

```
Buatkan weekly brief periode [tanggal] mengikuti PANDUAN_Prompt_dan_Ketentuan_Laporan_GSI.md.
Data terlampir. Bandingkan dengan periode sebelumnya dan perbarui exit watchlist.
```

```
Buatkan monthly report periode [bulan] mengikuti panduan yang sama, dengan
perbandingan rolling 30 hari dan bab exit plan yang diperbarui.
```

---

*Panduan ini disusun berdasarkan proses pembuatan Laporan Analisis Penjualan GSI 2026 dan Weekly Brief 3–8 Agustus 2026. Perbarui bila struktur data atau kebutuhan pelaporan berubah.*
