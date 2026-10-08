# ============================ BAGIAN 1: PUSTAKA ================================
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ========================== BAGIAN 2: PENGATURAN ==============================
st.set_page_config(page_title="Dashboard Data Yield", layout="wide")
st.title("Dashboard Data Yield AARI 2000-2021")


# ============================ BAGIAN 3: BACA DATA ==============================
@st.cache_data
def baca_data():
    """Membaca data dari Parquet; gunakan Excel jika Parquet belum tersedia."""
    path_aplikasi = Path(__file__).parent
    path_parquet = path_aplikasi / "data_yield_2000_2021.parquet"
    lokasi_excel = path_aplikasi / "data_yield_2000_2021.xlsx"

    if path_parquet.exists():
        tabel_data = pd.read_parquet(path_parquet)
    else:
        tabel_data = pd.read_excel(lokasi_excel)

    kolom_wajib = {
        "Y_YEAR",
        "Y_MONTH",
        "DIVISION_NAME",
        "Y_FFB",
        "E_HA",
        "ESTATE_NAME",
        "ESTATE_ID",
        "E_BLOCK_ID",
        "E_BLOCK_NAME",
    }
    kolom_hilang = kolom_wajib.difference(tabel_data.columns)
    if kolom_hilang:
        daftar_kolom_hilang = ", ".join(sorted(kolom_hilang))
        raise ValueError(
            f"Kolom wajib tidak ditemukan di file data: {daftar_kolom_hilang}"
        )

    tabel_data = tabel_data.copy()
    for nama_kolom in ("Y_YEAR", "Y_MONTH", "Y_FFB", "E_HA"):
        tabel_data[nama_kolom] = pd.to_numeric(
            tabel_data[nama_kolom], errors="raise"
        )
    tabel_data["DIVISION_NAME"] = (
        tabel_data["DIVISION_NAME"].astype("string").str.strip()
    )
    tabel_data["ESTATE_NAME"] = (
        tabel_data["ESTATE_NAME"].astype("string").str.strip()
    )
    return tabel_data


try:
    data = baca_data()
except (FileNotFoundError, ValueError, ImportError) as kesalahan:
    st.error(f"Data gagal dimuat: {kesalahan}")
    st.stop()


# ------------------------- BANTUAN UNTUK LUAS AREA ----------------------------
def ambil_snapshot_luas(data_pilihan, per_tahun=False):
    """Ambil luas terakhir untuk setiap blok, opsional untuk tiap tahun."""
    kolom_grup = ["ESTATE_ID", "DIVISION_NAME", "E_BLOCK_ID"]
    if per_tahun:
        kolom_grup.append("Y_YEAR")

    data_luas_valid = data_pilihan.dropna(
        subset=["Y_YEAR", "Y_MONTH", "E_HA", "E_BLOCK_ID"]
    ).copy()
    if data_luas_valid.empty:
        return data_luas_valid

    # Bulan menentukan kebaruan; urutan sumber memecahkan seri di bulan sama.
    data_luas_valid["__urutan_sumber"] = range(len(data_luas_valid))
    data_luas_valid = data_luas_valid.sort_values(
        ["Y_YEAR", "Y_MONTH", "__urutan_sumber"],
        kind="stable",
    )
    snapshot_luas = (
        data_luas_valid.groupby(kolom_grup, dropna=False, sort=False)
        .tail(1)
        .drop(columns="__urutan_sumber")
    )
    return snapshot_luas


nama_bulan = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


# ====================== BAGIAN 4: INFORMASI DATABASE =========================
st.subheader("Informasi Umum Database")

if data.empty:
    st.info("File berhasil dibaca, tetapi tidak berisi data.")
    st.stop()

kolom_metrik_info = st.columns(4)
with kolom_metrik_info[0]:
    st.metric("Jumlah Data", f"{len(data):,}")
with kolom_metrik_info[1]:
    st.metric("Jumlah Kolom", len(data.columns))
with kolom_metrik_info[2]:
    tahun_minimum = int(data["Y_YEAR"].min())
    tahun_maksimum = int(data["Y_YEAR"].max())
    st.metric("Tahun Data yang Tersedia", f"{tahun_minimum} - {tahun_maksimum}")
with kolom_metrik_info[3]:
    st.metric("Jumlah Divisi", data["DIVISION_NAME"].nunique())


# ========================== BAGIAN 5: FILTER SIDEBAR ==========================
st.sidebar.header("Filter Data")

# --------------------------- FILTER BERDASARKAN TAHUN --------------------------
daftar_tahun = sorted(
    data["Y_YEAR"].dropna().unique().tolist(), reverse=True
)
pilih_tahun = st.sidebar.selectbox(
    "Pilih Tahun",
    options=["Semua Tahun", *daftar_tahun],
)

# -------------------------- FILTER BERDASARKAN ESTATE -------------------------
daftar_estate = (
    data.dropna(subset=["ESTATE_ID"])
    .drop_duplicates(subset=["ESTATE_ID"])
    .sort_values("ESTATE_ID", key=lambda kolom: kolom.astype(str))
)
nama_estate_per_id = dict(
    zip(daftar_estate["ESTATE_ID"], daftar_estate["ESTATE_NAME"])
)
daftar_estate_id = daftar_estate["ESTATE_ID"].tolist()

def format_pilihan_estate(estate_id):
    if estate_id is None:
        return "Semua Estate"
    nama_estate = nama_estate_per_id.get(estate_id)
    if pd.isna(nama_estate) or not nama_estate:
        return f"Estate ID {estate_id}"
    return f"{nama_estate} (ID: {estate_id})"


pilih_estate_id = st.sidebar.selectbox(
    "Pilih Estate",
    options=[None, *daftar_estate_id],
    format_func=format_pilihan_estate,
)

# -------------------------- FILTER BERDASARKAN DIVISI -------------------------
# Saat satu estate dipilih, tampilkan hanya divisi yang tercatat di estate itu.
if pilih_estate_id is None:
    data_opsi_divisi = data
    keterangan_estate_divisi = "Semua Estate"
else:
    data_opsi_divisi = data.loc[data["ESTATE_ID"].eq(pilih_estate_id)]
    keterangan_estate_divisi = format_pilihan_estate(pilih_estate_id)

daftar_divisi = sorted(
    data_opsi_divisi["DIVISION_NAME"].dropna().unique().tolist()
)
st.sidebar.markdown(f"**Divisi untuk: {keterangan_estate_divisi}**")
pilih_divisi = st.sidebar.selectbox(
    "Pilih Divisi",
    options=["Semua Divisi", *daftar_divisi],
)

# --------------------------- FILTER BERDASARKAN BLOK --------------------------
data_opsi_blok = data_opsi_divisi
if pilih_divisi != "Semua Divisi":
    data_opsi_blok = data_opsi_blok.loc[
        data_opsi_blok["DIVISION_NAME"].eq(pilih_divisi)
    ]

daftar_blok = (
    data_opsi_blok.dropna(subset=["E_BLOCK_ID"])
    .drop_duplicates(subset=["ESTATE_ID", "DIVISION_NAME", "E_BLOCK_ID"])
    .sort_values(
        ["ESTATE_ID", "DIVISION_NAME", "E_BLOCK_ID"],
        key=lambda kolom: kolom.astype(str),
    )
)
identitas_blok_ke_nama = {
    (baris.ESTATE_ID, baris.DIVISION_NAME, baris.E_BLOCK_ID): baris.E_BLOCK_NAME
    for baris in daftar_blok.itertuples(index=False)
}
pilihan_blok = list(identitas_blok_ke_nama)


def format_pilihan_blok(identitas_blok):
    if identitas_blok is None:
        return "Semua Blok"
    nama_blok = identitas_blok_ke_nama[identitas_blok]
    if pd.isna(nama_blok) or not nama_blok:
        nama_blok = "Nama tidak tersedia"
    return f"{nama_blok} (ID: {identitas_blok[2]})"


pilih_identitas_blok = st.sidebar.selectbox(
    "Pilih Blok",
    options=[None, *pilihan_blok],
    format_func=format_pilihan_blok,
)

# ------------------------------ TERAPKAN FILTER -------------------------------
# Label "Semua" berarti kolom tersebut tidak membatasi hasil filter.
kondisi_filter = pd.Series(True, index=data.index)
if pilih_tahun != "Semua Tahun":
    kondisi_filter &= data["Y_YEAR"].eq(pilih_tahun).fillna(False)
if pilih_divisi != "Semua Divisi":
    kondisi_filter &= data["DIVISION_NAME"].eq(pilih_divisi).fillna(False)
if pilih_estate_id is not None:
    kondisi_filter &= data["ESTATE_ID"].eq(pilih_estate_id).fillna(False)
if pilih_identitas_blok is not None:
    id_estate_blok, nama_divisi_blok, id_blok = pilih_identitas_blok
    kondisi_filter &= (
        data["ESTATE_ID"].eq(id_estate_blok).fillna(False)
        & data["DIVISION_NAME"].eq(nama_divisi_blok).fillna(False)
        & data["E_BLOCK_ID"].eq(id_blok).fillna(False)
    )

data_terfilter = data.loc[kondisi_filter].copy()


# ====================== BAGIAN 6: METRIK DATA TERPILIH ========================
st.subheader("Ringkasan Data Terpilih")
snapshot_luas_terakhir = ambil_snapshot_luas(data_terfilter)
snapshot_luas_tahunan = ambil_snapshot_luas(
    data_terfilter,
    per_tahun=True,
)
if data_terfilter.empty:
    st.warning("Tidak ada data yang cocok dengan kombinasi filter ini.")
    total_produksi_ffb = 0
    luas_area = 0
    rata_rata_hasil = 0
else:
    total_produksi_ffb = data_terfilter["Y_FFB"].sum()
    luas_area = snapshot_luas_terakhir["E_HA"].sum()

    # Jika beberapa tahun dipilih, hitung yield per tahun dahulu agar hasilnya
    # tidak menjadi produksi multi-tahun dibagi luas dari satu snapshot terakhir.
    luas_per_tahun = snapshot_luas_tahunan.groupby("Y_YEAR")["E_HA"].sum()
    produksi_per_tahun = data_terfilter.groupby("Y_YEAR")["Y_FFB"].sum()
    yield_per_tahun = produksi_per_tahun.div(
        luas_per_tahun.reindex(produksi_per_tahun.index).where(
            luas_per_tahun.reindex(produksi_per_tahun.index) > 0
        )
    )
    rata_rata_hasil = yield_per_tahun.mean()
    if pd.isna(rata_rata_hasil):
        rata_rata_hasil = 0

kolom_metrik_terpilih = st.columns(4)
with kolom_metrik_terpilih[0]:
    st.metric("Jumlah Data Terpilih", f"{len(data_terfilter):,}")
with kolom_metrik_terpilih[1]:
    st.metric("Total Produksi FFB", f"{total_produksi_ffb:,.0f} Ton")
with kolom_metrik_terpilih[2]:
    st.metric("Rata-rata Yield Tahunan", f"{rata_rata_hasil:,.2f} Ton/Ha")
with kolom_metrik_terpilih[3]:
    st.metric("Luas Area Snapshot Terakhir", f"{luas_area:,.0f} Ha")
st.caption(
    "Luas area adalah jumlah snapshot terakhir setiap blok dalam rentang "
    "filter. Jika dipilih semua tahun, digunakan tahun dan bulan terakhir "
    "yang memiliki data untuk setiap blok."
)

# ----------------------- TABEL SNAPSHOT LUAS PER BLOK -------------------------
st.markdown("#### Luas Area yang Digunakan per Blok")
if snapshot_luas_terakhir.empty:
    st.info("Tidak ada catatan luas area yang dapat dijadikan snapshot.")
else:
    tabel_snapshot_blok = snapshot_luas_terakhir[
        [
            "ESTATE_NAME",
            "ESTATE_ID",
            "DIVISION_NAME",
            "E_BLOCK_NAME",
            "E_BLOCK_ID",
            "Y_YEAR",
            "Y_MONTH",
            "E_HA",
        ]
    ].rename(
        columns={
            "ESTATE_NAME": "Nama Estate",
            "ESTATE_ID": "Estate ID",
            "DIVISION_NAME": "Divisi",
            "E_BLOCK_NAME": "Nama Blok",
            "E_BLOCK_ID": "Block ID",
            "Y_YEAR": "Tahun Snapshot",
            "Y_MONTH": "Bulan Snapshot",
            "E_HA": "Luas Snapshot (Ha)",
        }
    )
    tabel_snapshot_blok["Bulan Snapshot"] = (
        tabel_snapshot_blok["Bulan Snapshot"].map(nama_bulan)
    )
    st.dataframe(
        tabel_snapshot_blok,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Luas Snapshot (Ha)": st.column_config.NumberColumn(format="%,.2f"),
        },
    )


# ======================== BAGIAN 7: VISUALISASI DATA ===========================
st.subheader("Visualisasi Data")
kolom_lingkaran, kolom_peta_panas = st.columns(2)

# ------------------------- PIE CHART KONTRIBUSI DIVISI -------------------------
with kolom_lingkaran:
    st.markdown("#### Kontribusi Total FFB per Divisi")
    data_lingkaran = data.dropna(
        subset=["DIVISION_NAME", "Y_FFB"]
    ).copy()
    if pilih_tahun != "Semua Tahun":
        data_lingkaran = data_lingkaran[
            data_lingkaran["Y_YEAR"].eq(pilih_tahun)
        ]
    if pilih_estate_id is not None:
        data_lingkaran = data_lingkaran[
            data_lingkaran["ESTATE_ID"].eq(pilih_estate_id)
        ]
    if pilih_divisi != "Semua Divisi":
        data_lingkaran = data_lingkaran[
            data_lingkaran["DIVISION_NAME"].eq(pilih_divisi)
        ]
    if pilih_identitas_blok is not None:
        id_estate_blok, nama_divisi_blok, id_blok = pilih_identitas_blok
        data_lingkaran = data_lingkaran[
            data_lingkaran["ESTATE_ID"].eq(id_estate_blok)
            & data_lingkaran["DIVISION_NAME"].eq(nama_divisi_blok)
            & data_lingkaran["E_BLOCK_ID"].eq(id_blok)
        ]

    ringkasan_divisi = (
        data_lingkaran.groupby("DIVISION_NAME", as_index=False)["Y_FFB"]
        .sum()
        .rename(columns={"DIVISION_NAME": "Divisi", "Y_FFB": "Total FFB"})
    )
    ringkasan_divisi = ringkasan_divisi[
        ringkasan_divisi["Total FFB"] > 0
    ]

    if ringkasan_divisi.empty:
        st.info("Tidak ada total FFB positif untuk ditampilkan pada pie chart.")
    else:
        diagram_lingkaran = (
            alt.Chart(ringkasan_divisi)
            .mark_arc()
            .encode(
                theta=alt.Theta("Total FFB:Q", aggregate="sum"),
                color=alt.Color("Divisi:N", title="Divisi"),
                tooltip=[
                    alt.Tooltip("Divisi:N"),
                    alt.Tooltip("Total FFB:Q", format=",.2f"),
                ],
            )
        )
        st.altair_chart(diagram_lingkaran, use_container_width=True)
    st.caption(
        "Pie chart mengikuti filter tahun, estate, divisi, dan blok."
    )

# ---------------------------- HEATMAP BULAN-TAHUN -----------------------------
with kolom_peta_panas:
    st.markdown("#### Rata-rata FFB per Bulan dan Tahun")
    data_peta_panas = data.dropna(
        subset=["Y_YEAR", "Y_MONTH", "Y_FFB"]
    ).copy()
    if pilih_divisi != "Semua Divisi":
        data_peta_panas = data_peta_panas[
            data_peta_panas["DIVISION_NAME"].eq(pilih_divisi)
        ]
    if pilih_estate_id is not None:
        data_peta_panas = data_peta_panas[
            data_peta_panas["ESTATE_ID"].eq(pilih_estate_id)
        ]
    if pilih_identitas_blok is not None:
        id_estate_blok, nama_divisi_blok, id_blok = pilih_identitas_blok
        data_peta_panas = data_peta_panas[
            data_peta_panas["ESTATE_ID"].eq(id_estate_blok)
            & data_peta_panas["DIVISION_NAME"].eq(nama_divisi_blok)
            & data_peta_panas["E_BLOCK_ID"].eq(id_blok)
        ]
    data_peta_panas = data_peta_panas[
        data_peta_panas["Y_MONTH"].between(1, 12)
    ]

    ringkasan_bulan_tahun = (
        data_peta_panas.groupby(
            ["Y_YEAR", "Y_MONTH"], as_index=False
        )["Y_FFB"]
        .mean()
        .rename(columns={"Y_FFB": "Rata-rata FFB"})
    )
    ringkasan_bulan_tahun["Tahun"] = (
        ringkasan_bulan_tahun["Y_YEAR"].astype(int).astype(str)
    )
    ringkasan_bulan_tahun["Bulan"] = ringkasan_bulan_tahun[
        "Y_MONTH"
    ].map(nama_bulan)
    urutan_bulan = list(nama_bulan.values())
    urutan_tahun = sorted(
        ringkasan_bulan_tahun["Tahun"].unique().tolist()
    )

    if ringkasan_bulan_tahun.empty:
        st.info("Tidak ada data bulan-tahun untuk ditampilkan pada heatmap.")
    else:
        peta_panas = (
            alt.Chart(ringkasan_bulan_tahun)
            .mark_rect()
            .encode(
                x=alt.X("Bulan:N", sort=urutan_bulan, title="Bulan"),
                y=alt.Y("Tahun:O", sort=urutan_tahun, title="Tahun"),
                color=alt.Color(
                    "Rata-rata FFB:Q",
                    title="Rata-rata FFB",
                    scale=alt.Scale(scheme="yellowgreenblue"),
                ),
                tooltip=[
                    alt.Tooltip("Tahun:O"),
                    alt.Tooltip("Bulan:N"),
                    alt.Tooltip("Rata-rata FFB:Q", format=",.2f"),
                ],
            )
        )
        st.altair_chart(peta_panas, use_container_width=True)
    st.caption(
        "Heatmap mengikuti filter estate, divisi, dan blok, serta menggunakan "
        "semua tahun agar pola bulan dapat dibandingkan."
    )

# ----------------------------- TREN SESUAI FILTER -----------------------------
if not data_terfilter.empty:
    if pilih_tahun == "Semua Tahun":
        st.markdown(f"#### Tren Rata-rata FFB per Tahun - {pilih_divisi}")
        ringkasan_tahunan = (
            data_terfilter.groupby("Y_YEAR", as_index=True)["Y_FFB"]
            .mean()
            .sort_index()
        )
        st.line_chart(ringkasan_tahunan)
    else:
        st.markdown(
            f"#### Tren Rata-rata FFB per Bulan - Tahun {pilih_tahun}, "
            f"{pilih_divisi}"
        )
        ringkasan_bulanan = (
            data_terfilter.dropna(subset=["Y_MONTH"])
            .groupby("Y_MONTH")["Y_FFB"]
            .mean()
            .sort_index()
            .rename(index=nama_bulan)
            .rename_axis("Bulan")
            .reset_index()
        )

        if ringkasan_bulanan.empty:
            st.info("Data tersedia, tetapi tidak cukup untuk membentuk tren.")
        else:
            grafik_tren_bulanan = (
                alt.Chart(ringkasan_bulanan)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Bulan:N", sort=urutan_bulan, title="Bulan"),
                    y=alt.Y("Y_FFB:Q", title="Rata-rata FFB"),
                    tooltip=[
                        "Bulan",
                        alt.Tooltip("Y_FFB:Q", title="Rata-rata FFB"),
                    ],
                )
            )
            st.altair_chart(grafik_tren_bulanan, use_container_width=True)


# ================= BAGIAN 8: PERBANDINGAN KINERJA ESTATE =====================
st.subheader("Perbandingan Kinerja per Estate")

if data_terfilter.empty:
    st.info("Tidak ada data estate untuk dibandingkan pada pilihan filter ini.")
else:
    produksi_estate = (
        data_terfilter.groupby("ESTATE_ID", dropna=False, as_index=False)
        .agg(
            **{
                "Nama Estate": ("ESTATE_NAME", "first"),
                "Total FFB (Ton)": ("Y_FFB", "sum"),
            }
        )
    )

    luas_snapshot_estate = (
        snapshot_luas_terakhir.groupby(
            "ESTATE_ID", dropna=False, as_index=False
        )["E_HA"]
        .sum()
        .rename(columns={"E_HA": "Luas Area Snapshot Terakhir (Ha)"})
    )

    produksi_tahunan_estate = (
        data_terfilter.groupby(
            ["ESTATE_ID", "Y_YEAR"], dropna=False, as_index=False
        )["Y_FFB"]
        .sum()
    )
    luas_tahunan_estate = (
        snapshot_luas_tahunan.groupby(
            ["ESTATE_ID", "Y_YEAR"], dropna=False, as_index=False
        )["E_HA"]
        .sum()
    )
    yield_tahunan_estate = produksi_tahunan_estate.merge(
        luas_tahunan_estate,
        on=["ESTATE_ID", "Y_YEAR"],
        how="left",
    )
    yield_tahunan_estate["Yield Tahunan"] = (
        yield_tahunan_estate["Y_FFB"]
        .div(yield_tahunan_estate["E_HA"].where(yield_tahunan_estate["E_HA"] > 0))
    )
    rata_rata_yield_estate = (
        yield_tahunan_estate.groupby(
            "ESTATE_ID", dropna=False, as_index=False
        )["Yield Tahunan"]
        .mean()
        .rename(columns={"Yield Tahunan": "Rata-rata Yield Tahunan (Ton/Ha)"})
    )

    ringkasan_kinerja_estate = (
        produksi_estate.merge(luas_snapshot_estate, on="ESTATE_ID", how="left")
        .merge(rata_rata_yield_estate, on="ESTATE_ID", how="left")
    )
    ringkasan_kinerja_estate = ringkasan_kinerja_estate.sort_values(
        "Rata-rata Yield Tahunan (Ton/Ha)",
        ascending=False,
        na_position="last",
    )
    ringkasan_kinerja_estate.insert(
        0,
        "Peringkat",
        range(1, len(ringkasan_kinerja_estate) + 1),
    )
    ringkasan_kinerja_estate = ringkasan_kinerja_estate.rename(
        columns={"ESTATE_ID": "Estate ID"}
    )

    st.caption(
        "Luas per estate adalah jumlah snapshot terakhir dari blok-blok "
        "di dalam estate. Peringkat memakai rata-rata yield tahunan."
    )
    st.dataframe(
        ringkasan_kinerja_estate,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Total FFB (Ton)": st.column_config.NumberColumn(format="%,.2f"),
            "Luas Area Snapshot Terakhir (Ha)": st.column_config.NumberColumn(
                format="%,.2f"
            ),
            "Rata-rata Yield Tahunan (Ton/Ha)": st.column_config.NumberColumn(
                format="%,.2f"
            ),
        },
    )


# =================== BAGIAN 9: ANALISIS PERUBAHAN TAHUNAN =====================
st.subheader("Perubahan Total FFB dibanding Tahun Sebelumnya")

# Tahun sebelumnya tetap dihitung walaupun filter hanya memilih satu tahun.
data_tahunan = data
if pilih_divisi != "Semua Divisi":
    data_tahunan = data_tahunan[data_tahunan["DIVISION_NAME"].eq(pilih_divisi)]
if pilih_estate_id is not None:
    data_tahunan = data_tahunan[
        data_tahunan["ESTATE_ID"].eq(pilih_estate_id)
    ]
if pilih_identitas_blok is not None:
    id_estate_blok, nama_divisi_blok, id_blok = pilih_identitas_blok
    data_tahunan = data_tahunan[
        data_tahunan["ESTATE_ID"].eq(id_estate_blok)
        & data_tahunan["DIVISION_NAME"].eq(nama_divisi_blok)
        & data_tahunan["E_BLOCK_ID"].eq(id_blok)
    ]

total_tahunan = (
    data_tahunan.groupby("Y_YEAR", as_index=False)["Y_FFB"]
    .sum()
    .sort_values("Y_YEAR")
)
total_tahunan["Y_YEAR"] = total_tahunan["Y_YEAR"].astype(int)
total_tahun_lalu = total_tahunan.rename(
    columns={"Y_YEAR": "Tahun Sebelumnya", "Y_FFB": "FFB Tahun Sebelumnya"}
)
analisis_tahunan = total_tahunan.assign(
    **{"Tahun Sebelumnya": total_tahunan["Y_YEAR"] - 1}
).merge(total_tahun_lalu, on="Tahun Sebelumnya", how="left")

if pilih_tahun != "Semua Tahun":
    analisis_tahunan = analisis_tahunan[
        analisis_tahunan["Y_YEAR"].eq(pilih_tahun)
    ]

if analisis_tahunan.empty:
    st.info("Tidak ada data tahunan untuk dibandingkan.")
else:
    analisis_tahunan["Perubahan FFB"] = (
        analisis_tahunan["Y_FFB"] - analisis_tahunan["FFB Tahun Sebelumnya"]
    )
    analisis_tahunan["Perubahan (%)"] = (
        analisis_tahunan["Perubahan FFB"]
        .div(
            analisis_tahunan["FFB Tahun Sebelumnya"].where(
                analisis_tahunan["FFB Tahun Sebelumnya"].ne(0)
            )
        )
        .mul(100)
    )
    tabel_perubahan = analisis_tahunan[
        ["Y_YEAR", "Y_FFB", "FFB Tahun Sebelumnya", "Perubahan FFB", "Perubahan (%)"]
    ].rename(columns={"Y_YEAR": "Tahun", "Y_FFB": "Total FFB (Ton)"})

    for nama_kolom in ("Total FFB (Ton)", "FFB Tahun Sebelumnya", "Perubahan FFB"):
        tabel_perubahan[nama_kolom] = tabel_perubahan[nama_kolom].map(
            lambda nilai: "Belum tersedia" if pd.isna(nilai) else f"{nilai:,.0f}"
        )
    tabel_perubahan["Perubahan (%)"] = tabel_perubahan["Perubahan (%)"].map(
        lambda nilai: "Belum tersedia" if pd.isna(nilai) else f"{nilai:,.2f}%"
    )
    st.caption(
        f"Perbandingan untuk {pilih_divisi}. Tahun sebelumnya tetap dihitung "
        "sebagai pembanding saat satu tahun dipilih."
    )
    st.dataframe(tabel_perubahan, hide_index=True, use_container_width=True)


# ================== BAGIAN 10: STATISTIK DESKRIPTIF FFB =======================
st.subheader("Statistik Deskriptif FFB pada Data Terpilih")
nilai_ffb = data_terfilter["Y_FFB"].dropna()

if nilai_ffb.empty:
    st.info("Tidak ada nilai FFB untuk dihitung pada filter ini.")
else:
    statistik_ffb = [
        ("Jumlah nilai", f"{nilai_ffb.count():,}"),
        ("Total FFB (Ton)", f"{nilai_ffb.sum():,.2f}"),
        ("Rata-rata FFB per baris (Ton)", f"{nilai_ffb.mean():,.2f}"),
        ("Median FFB per baris (Ton)", f"{nilai_ffb.median():,.2f}"),
        ("Nilai minimum (Ton)", f"{nilai_ffb.min():,.2f}"),
        ("Kuartil 1 / Q1 (Ton)", f"{nilai_ffb.quantile(0.25):,.2f}"),
        ("Kuartil 3 / Q3 (Ton)", f"{nilai_ffb.quantile(0.75):,.2f}"),
        ("Nilai maksimum (Ton)", f"{nilai_ffb.max():,.2f}"),
    ]
    tabel_statistik = pd.DataFrame(
        statistik_ffb,
        columns=["Hitungan Statistik", "Nilai"],
    )
    st.dataframe(tabel_statistik, hide_index=True, use_container_width=True)


# ===================== BAGIAN 11: SELURUH DATA TERFILTER ======================
st.subheader("Data Yang Ditampilkan Sesuai Filter")
st.caption(f"Menampilkan {len(data_terfilter):,} baris data.")
st.dataframe(data_terfilter, hide_index=True, use_container_width=True)
