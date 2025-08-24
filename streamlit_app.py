import streamlit as st
import pandas as pd

# ---- Alap beállítások ----
st.set_page_config(page_title="RC-BEAM-CROSS-SECTION", layout="wide")

# ---- Cím és leírás ----
st.title("Vasbeton gerenda keresztmetszet méretező")
st.text('EC2:2010 / MSZ 15022 szabványok szerint')

standard_list = ['EC2:2010', 'MSZ 15022']

# ---- Üres session_state inicializálása ----
if "results" not in st.session_state:
    st.session_state.results = {}

# ----------------------------------------------------------------
# FUNCTIONS IN-APP

# ---- Function to import Excel files ----
@st.cache_data
def load_materials_from_excel(file_path, sheet_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    return df

# ----------------------------------------------------------------
# MSZ 15022 szerinti anyagok betöltése
df_msz_betonacel = load_materials_from_excel(".static/anyagok_msz.xlsx", "msz-betonacel")
df_msz_beton = load_materials_from_excel(".static/anyagok_msz.xlsx", "msz-beton")

# Anyagminőségeket tartalmazó sorok kiszedése választólistához
msz_betonacelok = df_msz_betonacel['betonacel'].tolist()
msz_betonok = df_msz_beton['beton'].tolist()


# --- BEMENŐ ADATOK ---
# Alkalmazott szabvány kiválasztása
applied_standard = st.selectbox('Alkalmazott szabvány:', options=standard_list, 
                                index=0, width=200)

# Két oszlopos elrendezés
col1, col2 = st.columns(2, gap="small", width='stretch', border=True)

with col1:
    st.header("Geometria és anyagok")
    st.number_input('Enter a number')

with col2:
    st.header("Alkalmazott Vasalás")
    st.number_input('Enter a number2')


# --- Számítás gomb ---
# if st.button("Számítás"):
    # st.session_state.results = {
    #     "MRd (nyomaték teherbírás)": calc_MRd(bw, h, fck, as1),
    #     "VRd (nyírási teherbírás)": calc_VRd(bw, h, fck)}

# --- Eredmények ---
# if st.session_state.results:
    
