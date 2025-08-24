import streamlit as st
import pandas as pd

st.title("RC Beam Cross-Section Calculator")

# --- Inicializálás ---
if "results" not in st.session_state:
    st.session_state.results = {}

# ANYAGOK

@st.cache_data
def load_materials_from_excel(file_path, sheet_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    return df

df_msz_betonacel = load_materials_from_excel(".static/anyagok_msz.xlsx", "msz-betonacel")
df_msz_betonacel

# --- Bemenő adatok ---
bw = st.number_input("Szélesség bw [mm]", value=300)
h = st.number_input("Magasság h [mm]", value=500)
fck = st.number_input("Beton szilárdság fck [MPa]", value=30)
as1 = st.number_input("Húzott vasalás területe As1 [mm²]", value=1500)

# --- Számítási függvények (példák!) ---
def calc_MRd(bw, h, fck, as1):
    # ⚠️ Példa képlet! (nem Eurocode szerinti!)
    return 0.8 * as1 * (h - 50) * 1e-6   # kNm

def calc_VRd(bw, h, fck):
    # ⚠️ Példa képlet! (nem Eurocode szerinti!)
    return 0.6 * bw * h * (fck**0.5) * 1e-3   # kN

# --- Számítás gomb ---
if st.button("Számítás"):
    st.session_state.results = {
        "MRd (nyomaték teherbírás)": calc_MRd(bw, h, fck, as1),
        "VRd (nyírási teherbírás)": calc_VRd(bw, h, fck)
    }

# --- Eredmények ---
if st.session_state.results:
    st.subheader("📊 Számítási eredmények")
    for key, val in st.session_state.results.items():
        st.write(f"**{key}:** {val:.2f}")
