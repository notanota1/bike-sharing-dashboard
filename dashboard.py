from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Bike Sharing Dashboard", page_icon="🚲", layout="wide")

BASE = Path(__file__).parent
ABU, BIRU, ORANYE, MERAH = "#BFC5CC", "#1F6FB2", "#E8833A", "#C0392B"
URUT_CUACA = ["Cerah", "Berkabut", "Hujan/Salju Ringan"]
URUT_MUSIM = ["Semi", "Panas", "Gugur", "Dingin"]
NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
sns.set_theme(style="whitegrid", rc={"axes.spines.top": False, "axes.spines.right": False,
                                      "axes.titleweight": "bold", "axes.titlesize": 12,
                                      "axes.grid.axis": "y"})


@st.cache_data
def load_data():
    day = pd.read_csv(BASE / "main_data.csv", parse_dates=["dteday"])
    hour = pd.read_csv(BASE / "hour_data.csv", parse_dates=["tanggal_jam", "dteday"])
    return day, hour


day_all, hour_all = load_data()

# ---------------- Sidebar ----------------
st.sidebar.header("Filter Data")
tgl_min, tgl_max = day_all["dteday"].min().date(), day_all["dteday"].max().date()
rentang = st.sidebar.date_input("Rentang tanggal", (tgl_min, tgl_max), min_value=tgl_min, max_value=tgl_max)
musim_pilih = st.sidebar.multiselect("Musim", URUT_MUSIM, default=URUT_MUSIM)
st.sidebar.caption("Label musim dikoreksi dari Readme asli (kode 1 = Dingin, 2 = Semi, 3 = Panas, 4 = Gugur).")

if isinstance(rentang, (tuple, list)) and len(rentang) == 2:
    awal, akhir = pd.Timestamp(rentang[0]), pd.Timestamp(rentang[1])
else:
    awal, akhir = pd.Timestamp(tgl_min), pd.Timestamp(tgl_max)

day = day_all[(day_all["dteday"].between(awal, akhir)) & (day_all["musim"].isin(musim_pilih))]
hour = hour_all[(hour_all["dteday"].between(awal, akhir)) & (hour_all["musim"].isin(musim_pilih))]

# ---------------- Header ----------------
st.title("🚲 Dashboard Analisis Bike Sharing")
st.caption("Capital Bikeshare, Washington D.C. | Data harian dan per jam 2011–2012")

if day.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau musim.")
    st.stop()

# ---------------- KPI ----------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total penyewaan", f"{day['cnt'].sum():,.0f}")
k2.metric("Rata-rata per hari", f"{day['cnt'].mean():,.0f}")
k3.metric("Porsi pengguna registered", f"{day['registered'].sum() / day['cnt'].sum():.1%}")
k4.metric("Jumlah hari", f"{len(day):,}")

tab1, tab2, tab3, tab4 = st.tabs(["1. Cuaca & Musim", "2. Pola Jam", "3. Pertumbuhan YoY", "4. Analisis Lanjutan"])

fmt_ribuan = mtick.FuncFormatter(lambda x, _: f"{x:,.0f}")

# ---------------- Tab 1 ----------------
with tab1:
    st.subheader("Seberapa besar cuaca dan musim menekan penyewaan harian?")
    rata = day.groupby("cuaca")["cnt"].agg(["mean", "count"]).reindex(URUT_CUACA).dropna()
    pivot = day.pivot_table(index="musim", columns="cuaca", values="cnt", aggfunc="mean")
    pivot = pivot.reindex(index=[m for m in URUT_MUSIM if m in pivot.index],
                          columns=[c for c in URUT_CUACA if c in pivot.columns])
    c1, c2 = st.columns([1, 1.3])
    with c1:
        fig, ax = plt.subplots(figsize=(5.5, 4.4))
        warna = {"Cerah": BIRU, "Berkabut": ABU, "Hujan/Salju Ringan": MERAH}
        bars = ax.bar(rata.index, rata["mean"], color=[warna[i] for i in rata.index], width=0.6)
        acuan = rata["mean"].get("Cerah", np.nan)
        for b, (idx, r) in zip(bars, rata.iterrows()):
            sel = "" if idx == "Cerah" or np.isnan(acuan) else f"\n({(r['mean'] / acuan - 1) * 100:.1f}%)"
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02, f"{r['mean']:,.0f}{sel}",
                    ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, rata["mean"].max() * 1.25)
        ax.set_ylabel("Rata-rata penyewaan per hari"); ax.set_xlabel("")
        ax.yaxis.set_major_formatter(fmt_ribuan)
        ax.set_title("Rata-rata penyewaan per kondisi cuaca", loc="left")
        st.pyplot(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(7, 4.4))
        x = np.arange(len(pivot.index)); w = 0.26
        for i, (c, col) in enumerate(zip(pivot.columns, [BIRU, ABU, MERAH][:len(pivot.columns)])):
            ax.bar(x + (i - (len(pivot.columns) - 1) / 2) * w, pivot[c], w, label=c,
                   color={"Cerah": BIRU, "Berkabut": ABU, "Hujan/Salju Ringan": MERAH}[c])
        ax.set_xticks(x, pivot.index); ax.yaxis.set_major_formatter(fmt_ribuan)
        ax.set_ylabel("Rata-rata penyewaan per hari"); ax.legend(title="Cuaca", frameon=False)
        ax.set_title("Rata-rata penyewaan per musim dan cuaca", loc="left")
        st.pyplot(fig)
    st.info("Pada seluruh data: hari berkabut turun 17,2% dan hujan/salju ringan turun 63,0% dibanding hari cerah. "
            "Hujan/salju ringan hanya 3–10 hari per musim sehingga angka per musim bersifat indikatif.")

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader("Kapan jam sibuk hari kerja vs akhir pekan, dan siapa penggunanya?")
    per_jam = hour.groupby(["tipe_hari", "hr"])[["cnt", "casual", "registered"]].mean()
    c1, c2 = st.columns([1.6, 1])
    with c1:
        fig, ax = plt.subplots(figsize=(8, 4.4))
        for tipe, col in [("Hari Kerja", BIRU), ("Akhir Pekan/Libur", ORANYE)]:
            if tipe not in per_jam.index.get_level_values(0):
                continue
            s = per_jam.loc[tipe]["cnt"]
            ax.plot(s.index, s.values, color=col, lw=2.5, label=tipe)
            if tipe == "Hari Kerja":
                for h in s.nlargest(2).index:
                    ax.scatter(h, s[h], color=col, zorder=3)
                    ax.annotate(f"{h:02d}:00 ({s[h]:.0f})", (h, s[h]), textcoords="offset points",
                                xytext=(0, 8), ha="center", fontsize=8.5, color=col)
            else:
                h = s.idxmax(); ax.scatter(h, s[h], color=col, zorder=3)
                ax.annotate(f"{h:02d}:00 ({s[h]:.0f})", (h, s[h]), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=8.5, color=col)
        ax.set_xticks(range(0, 24, 2)); ax.set_ylim(0, per_jam["cnt"].max() * 1.2)
        ax.set_xlabel("Jam (0–23)"); ax.set_ylabel("Rata-rata penyewaan per jam"); ax.legend(frameon=False)
        ax.set_title("Pola penyewaan per jam", loc="left")
        st.pyplot(fig)
    with c2:
        porsi = hour.groupby("tipe_hari")[["casual", "registered"]].sum()
        porsi = porsi.div(porsi.sum(axis=1), axis=0) * 100
        fig, ax = plt.subplots(figsize=(5, 4.4))
        ax.barh(porsi.index, porsi["registered"], color=BIRU, label="Registered")
        ax.barh(porsi.index, porsi["casual"], left=porsi["registered"], color=ORANYE, label="Casual")
        for i, (_, r) in enumerate(porsi.iterrows()):
            ax.text(r["registered"] / 2, i, f"{r['registered']:.1f}%", color="white", ha="center", va="center", fontweight="bold")
            ax.text(r["registered"] + r["casual"] / 2, i, f"{r['casual']:.1f}%", color="white", ha="center", va="center", fontweight="bold", fontsize=8)
        ax.set_xlim(0, 100); ax.set_xlabel("Porsi penyewaan (%)"); ax.invert_yaxis()
        ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
        ax.set_title("Porsi registered vs casual", loc="left")
        st.pyplot(fig)
    st.info("Pada seluruh data: hari kerja memuncak pukul 08.00 dan 17.00 (pola komuter), akhir pekan/libur pukul 13.00. "
            "Casual naik dari 13,2% (hari kerja) menjadi 31,7% (akhir pekan/libur).")

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader("Seberapa cepat pertumbuhan penyewaan bulanan 2012 dibanding 2011?")
    st.caption("Bagian ini selalu memakai data 2011–2012 penuh (tidak terpengaruh filter) agar YoY adil per bulan.")
    bln = day_all.groupby(["tahun", "mnth"])["cnt"].sum().unstack("tahun")
    bln["yoy"] = (bln[2012] / bln[2011] - 1) * 100
    c1, c2 = st.columns([1.2, 1])
    with c1:
        fig, ax = plt.subplots(figsize=(7, 4.4))
        ax.plot(NAMA_BULAN, bln[2011], marker="o", color=ABU, lw=2.5, label="2011")
        ax.plot(NAMA_BULAN, bln[2012], marker="o", color=BIRU, lw=2.5, label="2012")
        ax.set_ylim(0, bln[[2011, 2012]].max().max() * 1.15); ax.legend(frameon=False)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x / 1000:,.0f}K"))
        ax.set_ylabel("Total penyewaan per bulan"); ax.set_title("Total penyewaan bulanan", loc="left")
        st.pyplot(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 4.4))
        batas = bln["yoy"].nsmallest(4).max()
        bars = ax.bar(NAMA_BULAN, bln["yoy"], color=[MERAH if v <= batas else ABU for v in bln["yoy"]])
        for b, v in zip(bars, bln["yoy"]):
            ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=8)
        ax.set_ylim(0, bln["yoy"].max() * 1.15); ax.set_ylabel("Pertumbuhan YoY (%)")
        ax.set_title("Pertumbuhan YoY (merah = terendah)", loc="left")
        st.pyplot(fig)
    total = day_all.groupby("tahun")["cnt"].sum()
    st.info(f"Total 2012 tumbuh {(total[2012] / total[2011] - 1) * 100:.1f}% dibanding 2011. Pertumbuhan terendah: "
            f"{NAMA_BULAN[int(bln['yoy'].idxmin()) - 1]} ({bln['yoy'].min():.1f}%). Pertumbuhan tinggi di awal tahun dipengaruhi basis 2011 yang rendah.")

# ---------------- Tab 4 ----------------
with tab4:
    st.subheader("Analisis lanjutan: binning suhu dan segmentasi waktu (clustering non-ML)")
    d = day.copy()
    d["kelompok_suhu"] = pd.cut(d["suhu_c"], [0, 10, 15, 20, 25, 30, 45],
                                labels=["<10 °C", "10–15 °C", "15–20 °C", "20–25 °C", "25–30 °C", ">30 °C"])
    rs = d.groupby("kelompok_suhu", observed=True)["cnt"].agg(["mean", "count"])

    def segmen(h):
        return ("Dini Hari (00–05)" if h <= 5 else "Puncak Pagi (06–09)" if h <= 9 else "Siang (10–15)"
                if h <= 15 else "Puncak Sore (16–19)" if h <= 19 else "Malam (20–23)")
    urut_seg = ["Dini Hari (00–05)", "Puncak Pagi (06–09)", "Siang (10–15)", "Puncak Sore (16–19)", "Malam (20–23)"]
    h2 = hour.copy(); h2["segmen"] = h2["hr"].apply(segmen)
    seg = h2.groupby(["tipe_hari", "segmen"])["cnt"].sum().unstack("tipe_hari").reindex(urut_seg).fillna(0)
    seg_pct = seg.div(seg.sum().replace(0, np.nan)) * 100

    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 4.4))
        top = rs["mean"].idxmax()
        bars = ax.bar(rs.index.astype(str), rs["mean"], color=[BIRU if k == top else ABU for k in rs.index])
        for b, (_, r) in zip(bars, rs.iterrows()):
            ax.text(b.get_x() + b.get_width() / 2, r["mean"] * 1.02, f"{r['mean']:,.0f}\n(n={int(r['count'])})", ha="center", fontsize=8)
        ax.set_ylim(0, rs["mean"].max() * 1.3); ax.yaxis.set_major_formatter(fmt_ribuan)
        ax.set_ylabel("Rata-rata penyewaan per hari"); ax.set_title("Penyewaan per rentang suhu", loc="left")
        plt.setp(ax.get_xticklabels(), fontsize=8)
        st.pyplot(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6.5, 4.4))
        x = np.arange(len(urut_seg)); w = 0.38
        for i, (tipe, col) in enumerate([("Hari Kerja", BIRU), ("Akhir Pekan/Libur", ORANYE)]):
            if tipe in seg_pct.columns:
                ax.bar(x + (i - 0.5) * w, seg_pct[tipe].fillna(0), w, color=col, label=tipe)
        ax.set_xticks(x, [s.replace(" (", "\n(") for s in urut_seg], fontsize=8)
        ax.set_ylabel("Porsi penyewaan (%)"); ax.legend(frameon=False)
        ax.set_title("Porsi penyewaan per segmen waktu", loc="left")
        st.pyplot(fig)
    st.caption("RFM dan geospatial tidak digunakan karena dataset tidak memiliki ID pelanggan maupun koordinat lokasi.")

# ---------------- Rekomendasi ----------------
with st.expander("Kesimpulan & rekomendasi"):
    st.markdown("""
- **Armada berbasis jam:** siapkan sepeda dan dok sebelum 07.00 dan 16.00 pada hari kerja; fokus pukul 11.00–16.00 pada akhir pekan.
- **Strategi cuaca:** antisipasi penurunan 17–63% saat berkabut atau hujan, serta promosi khusus musim Dingin (suhu < 10 °C hanya ≈ 1.680 sewa/hari).
- **Konversi casual → registered:** tawarkan paket akhir pekan saat porsi casual terbesar (31,7%).
- **Akuisisi:** jalankan kampanye pada Mei–Juli dan Desember saat pertumbuhan YoY paling lambat (≈ 41–44%).
""")
