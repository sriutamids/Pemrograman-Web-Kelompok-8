"""
Mini-Project 1 - Integrasi P2 s/d P6
Dashboard Prakiraan Cuaca (data: API Terbuka BMKG)

Tahap 1 (P5 & P6): ekstraksi data via requests -> Pandas DataFrame (>= 50 baris)
Tahap 2 (P2)     : generate file HTML lewat file handling (open/write) + looping
Tahap 3 (P3)     : styling Bootstrap 5 (CDN) + table-striped

Sumber data: BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)
Dokumentasi : https://data.bmkg.go.id/prakiraan-cuaca/


"""

import json
import time
from datetime import datetime

import pandas as pd
import requests

API_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
OUTPUT_FILE = "hasil_generate.html"
MINIMAL_BARIS = 50

# Kode wilayah tingkat IV (kelurahan/desa) menurut Kepmendagri 100.1.1-6117/2022.
# 1 lokasi = 24 baris (3 hari x 8 data per 3 jam). Kode yang tidak valid akan
# dilewati otomatis. Kamu boleh MENAMBAH kode lain (mis. daerah rumahmu).
KODE_LOKASI = [
    "31.71.03.1001",  # Kemayoran, Jakarta Pusat (contoh resmi BMKG)
    "31.71.01.1001",  # Gambir, Jakarta Pusat (contoh resmi BMKG)
    "31.74.04.1006",  # Pejaten Barat, Jakarta Selatan
    "31.73.01.1001",  # Jakarta Utara (cadangan)
    "31.72.01.1001",  # Jakarta Barat (cadangan)
]


# ---------------------------------------------------------------- TAHAP 1
def ambil_satu_lokasi(kode, percobaan=3):
    """Ambil prakiraan 3 hari untuk satu kode wilayah. Return list baris (dict)."""
    headers = {"User-Agent": "Mozilla/5.0 (MiniProject1 Python)", "Accept": "application/json"}
    for ke in range(1, percobaan + 1):
        try:
            resp = requests.get(API_URL, params={"adm4": kode}, headers=headers, timeout=30)
            if resp.status_code == 429:
                raise requests.RequestException("429 rate limit")
            resp.raise_for_status()
            js = resp.json()
            break
        except (requests.RequestException, ValueError) as err:
            print(f"  [{kode}] percobaan {ke}/{percobaan} gagal: {err}")
            if ke == percobaan:
                return []
            time.sleep(5 * ke)

    lok = js.get("lokasi", {})
    nama_lokasi = f"{lok.get('desa', kode)}, {lok.get('kecamatan', '')}".strip(", ")
    kota = lok.get("kotkab", "")

    baris = []
    for blok in js.get("data", []):
        for hari in blok.get("cuaca", []):
            for p in hari:
                baris.append({
                    "Lokasi": nama_lokasi,
                    "Kota": kota,
                    "Waktu": p.get("local_datetime", ""),
                    "Cuaca": p.get("weather_desc", "-"),
                    "Suhu": p.get("t"),
                    "Kelembapan": p.get("hu"),
                    "Angin": p.get("ws"),
                    "ArahAngin": p.get("wd", "-"),
                    "Awan": p.get("tcc"),
                    "JarakPandang": p.get("vs_text", "-"),
                })
    return baris


def ambil_data():
    """Kumpulkan data semua lokasi -> Pandas DataFrame."""
    semua = []
    for kode in KODE_LOKASI:
        print(f"Mengambil data BMKG untuk {kode} ...")
        hasil = ambil_satu_lokasi(kode)
        print(f"  -> {len(hasil)} baris")
        semua.extend(hasil)
        time.sleep(1)  # sopan terhadap batas 60 request/menit

    if len(semua) < MINIMAL_BARIS:
        raise SystemExit(
            f"Hanya dapat {len(semua)} baris (minimal {MINIMAL_BARIS}). "
            "Periksa internet / tambah kode wilayah di KODE_LOKASI."
        )

    df = pd.DataFrame(semua)
    for kol in ("Suhu", "Kelembapan", "Angin", "Awan"):
        df[kol] = pd.to_numeric(df[kol], errors="coerce")
    df.to_csv("data_mentah.csv", index=False)  # arsip hasil ekstraksi
    print(f"Berhasil mengambil {len(df)} baris data asli dari BMKG.")
    return df


# ---------------------------------------------------------------- TAHAP 2
def fmt(x, satuan=""):
    return "-" if pd.isna(x) else f"{x:g}{satuan}"


def bangun_baris_tabel(df):
    """Looping DataFrame -> deretan <tr> HTML."""
    baris = ""
    for i, r in enumerate(df.itertuples(index=False), start=1):
        c = str(r.Cuaca).lower()
        if "hujan" in c or "petir" in c:
            badge = "primary"
        elif "cerah" in c:
            badge = "warning"
        else:
            badge = "secondary"
        baris += f"""
        <tr data-lokasi="{r.Lokasi}">
          <td>{i}</td>
          <td class="fw-semibold">{r.Lokasi}<br><small class="text-body-secondary">{r.Kota}</small></td>
          <td>{r.Waktu}</td>
          <td><span class="badge text-bg-{badge}">{r.Cuaca}</span></td>
          <td data-v="{r.Suhu}">{fmt(r.Suhu, ' °C')}</td>
          <td data-v="{r.Kelembapan}">{fmt(r.Kelembapan, '%')}</td>
          <td data-v="{r.Angin}">{fmt(r.Angin, ' km/j')}</td>
          <td>{r.ArahAngin}</td>
          <td>{r.JarakPandang}</td>
        </tr>"""
    return baris


TEMPLATE = """<!DOCTYPE html>
<html lang="id" data-bs-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard Prakiraan Cuaca BMKG</title>
  <!-- Bootstrap 5 CDN -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    .hero { background: linear-gradient(120deg, #0369a1, #0ea5e9 60%, #38bdf8); color: #fff; border-radius: 1rem; }
    .stat-card { border: 0; border-left: 5px solid; }
    th.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
    .tbl-wrap { max-height: 520px; overflow-y: auto; }
    .tbl-wrap thead th { position: sticky; top: 0; z-index: 1; }
  </style>
</head>
<body class="bg-body-tertiary">

<nav class="navbar bg-body shadow-sm sticky-top">
  <div class="container">
    <span class="navbar-brand fw-bold">&#9729; CuacaKu</span>
    <div class="d-flex align-items-center gap-3">
      <small class="text-body-secondary d-none d-md-inline">Dibuat: __WAKTU__</small>
      <button id="btnTema" class="btn btn-outline-secondary btn-sm">Mode Gelap</button>
    </div>
  </div>
</nav>

<main class="container py-4">

  <!-- Elemen dummy di atas tabel -->
  <section class="hero p-4 p-md-5 mb-4 shadow">
    <h1 class="h3 fw-bold mb-1">Dashboard Prakiraan Cuaca 3 Hari</h1>
    <p class="mb-0 opacity-75">__JML_LOKASI__ lokasi &middot; __JUMLAH__ data prakiraan &middot; Sumber data: BMKG</p>
  </section>

  <div class="row g-3 mb-4">
    <div class="col-6 col-lg-3"><div class="card stat-card shadow-sm border-primary"><div class="card-body">
      <div class="small text-body-secondary">Total Data</div><div class="fs-4 fw-bold text-primary">__JUMLAH__</div></div></div></div>
    <div class="col-6 col-lg-3"><div class="card stat-card shadow-sm border-danger"><div class="card-body">
      <div class="small text-body-secondary">Suhu Tertinggi</div><div class="fs-4 fw-bold text-danger">__MAX__</div></div></div></div>
    <div class="col-6 col-lg-3"><div class="card stat-card shadow-sm border-info"><div class="card-body">
      <div class="small text-body-secondary">Suhu Terendah</div><div class="fs-4 fw-bold text-info">__MIN__</div></div></div></div>
    <div class="col-6 col-lg-3"><div class="card stat-card shadow-sm border-success"><div class="card-body">
      <div class="small text-body-secondary">Rata-rata Kelembapan</div><div class="fs-4 fw-bold text-success">__HU__</div></div></div></div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-lg-7"><div class="card shadow-sm h-100"><div class="card-body">
      <h2 class="h6 fw-bold">Rata-rata Suhu per Lokasi (&deg;C)</h2>
      <canvas id="chartBar" height="140"></canvas></div></div></div>
    <div class="col-lg-5"><div class="card shadow-sm h-100"><div class="card-body">
      <h2 class="h6 fw-bold">Distribusi Kondisi Cuaca</h2>
      <canvas id="chartDonut"></canvas></div></div></div>
  </div>

  <!-- Tabel data -->
  <div class="card shadow-sm">
    <div class="card-header bg-body d-flex flex-wrap justify-content-between align-items-center gap-2">
      <h2 class="h6 fw-bold mb-0">Data Prakiraan Cuaca</h2>
      <div class="d-flex gap-2">
        <select id="filterLokasi" class="form-select form-select-sm w-auto">
          <option value="">Semua lokasi</option>__OPSI__
        </select>
        <input id="cari" type="search" class="form-control form-control-sm w-auto" placeholder="Cari...">
      </div>
    </div>
    <div class="tbl-wrap">
      <table class="table table-striped table-hover align-middle mb-0" id="tabel">
        <thead class="table-dark">
          <tr>
            <th class="sortable">#</th><th class="sortable">Lokasi</th><th class="sortable">Waktu Lokal</th>
            <th class="sortable">Cuaca</th><th class="sortable">Suhu</th><th class="sortable">Kelembapan</th>
            <th class="sortable">Angin</th><th>Arah</th><th>Jarak Pandang</th>
          </tr>
        </thead>
        <tbody>__BARIS__</tbody>
      </table>
    </div>
  </div>

  <p class="text-center text-body-secondary small mt-4 mb-0">
    Sumber data: BMKG (Badan Meteorologi, Klimatologi, dan Geofisika) &middot; Mini-Project 1, dibuat otomatis dengan Python
  </p>
</main>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script>
  const D = __DATA__;
  const warna = ['#0ea5e9','#f59e0b','#22c55e','#8b5cf6','#ef4444','#14b8a6','#64748b','#ec4899'];

  new Chart(document.getElementById('chartBar'), {
    type: 'bar',
    data: { labels: D.lokasi, datasets: [{ label: 'Suhu rata-rata (°C)', data: D.suhu, backgroundColor: '#0ea5e9', borderRadius: 4 }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } }
  });
  new Chart(document.getElementById('chartDonut'), {
    type: 'doughnut',
    data: { labels: D.kondisi, datasets: [{ data: D.jumlah, backgroundColor: warna }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  // Filter lokasi + pencarian
  const cari = document.getElementById('cari'), sel = document.getElementById('filterLokasi');
  function terapkan() {
    const q = cari.value.toLowerCase(), l = sel.value;
    document.querySelectorAll('#tabel tbody tr').forEach(tr => {
      const ok = tr.innerText.toLowerCase().includes(q) && (!l || tr.dataset.lokasi === l);
      tr.style.display = ok ? '' : 'none';
    });
  }
  cari.addEventListener('input', terapkan);
  sel.addEventListener('change', terapkan);

  // Urutkan kolom
  document.querySelectorAll('#tabel th.sortable').forEach((th, i) => {
    let asc = true;
    th.addEventListener('click', () => {
      const tb = document.querySelector('#tabel tbody');
      const rows = [...tb.rows];
      const val = r => { const c = r.cells[i]; if (c.dataset.v !== undefined) return parseFloat(c.dataset.v); const t = c.innerText.trim(); return /^\\d+$/.test(t) ? parseFloat(t) : t; };
      rows.sort((a, b) => {
        const x = val(a), y = val(b);
        const h = (typeof x === 'number' && typeof y === 'number') ? (isNaN(x) ? 1 : isNaN(y) ? -1 : x - y) : String(x).localeCompare(String(y), 'id');
        return asc ? h : -h;
      });
      asc = !asc;
      rows.forEach(r => tb.appendChild(r));
    });
  });

  // Mode gelap
  const btn = document.getElementById('btnTema');
  btn.addEventListener('click', () => {
    const h = document.documentElement, gelap = h.getAttribute('data-bs-theme') === 'dark';
    h.setAttribute('data-bs-theme', gelap ? 'light' : 'dark');
    btn.textContent = gelap ? 'Mode Gelap' : 'Mode Terang';
  });
</script>
</body>
</html>
"""


def generate_html(df):
    per_lokasi = df.groupby("Lokasi")["Suhu"].mean().round(1)
    kondisi = df["Cuaca"].value_counts()

    data_js = {
        "lokasi": per_lokasi.index.tolist(),
        "suhu": per_lokasi.tolist(),
        "kondisi": kondisi.index.tolist(),
        "jumlah": [int(v) for v in kondisi.tolist()],
    }
    opsi = "".join(f'<option value="{n}">{n}</option>' for n in per_lokasi.index)

    isi = {
        "__WAKTU__": datetime.now().strftime("%d %b %Y %H:%M"),
        "__JUMLAH__": str(len(df)),
        "__JML_LOKASI__": str(df["Lokasi"].nunique()),
        "__MAX__": f"{df['Suhu'].max():g} °C",
        "__MIN__": f"{df['Suhu'].min():g} °C",
        "__HU__": f"{df['Kelembapan'].mean():.0f}%",
        "__OPSI__": opsi,
        "__BARIS__": bangun_baris_tabel(df),
        "__DATA__": json.dumps(data_js),
    }
    html = TEMPLATE
    for kunci, nilai in isi.items():
        html = html.replace(kunci, nilai)

    # File handling: tulis string HTML ke file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Berhasil membuat {OUTPUT_FILE} ({len(df)} baris data)")


if __name__ == "__main__":
    dataframe = ambil_data()
    print(dataframe.head())
    generate_html(dataframe)
