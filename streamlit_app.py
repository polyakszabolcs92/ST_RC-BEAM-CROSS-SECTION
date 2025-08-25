import streamlit as st
import pandas as pd
from shapely import Polygon
import structuralcodes as sc

# ---- Alap beállítások ----
st.set_page_config(page_title="RC-BEAM-CROSS-SECTION", layout="wide")

# ---- Cím és leírás ----
st.title("Vasbeton gerenda keresztmetszet méretező (EC2:2010)")


# ---- Üres session_state inicializálása ----
if "results" not in st.session_state:
    st.session_state.results = {}


# ----------------------------------------------------------------
# FUNCTIONS IN-APP

# ---- Function to import Excel files ----
@st.cache_data
def load_materials_from_excel(file_path, sheet_name):
    """Load material properties from an Excel file.
     Args:
         file_path (str): Path to the Excel file.
         sheet_name (str): Name of the sheet to load.
     Returns:
         pd.DataFrame: DataFrame containing material properties.
     """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    return df


# ----------------------------------------------------------------
# KONSTANS OBJEKTUMOK
cross_section_types = ['Teglalap', 'T', 'I', 'FordT', 'Trapez']   # keresztmetszetek listája

# ----------------------------------------------------------------
# ANYAGJELLEMZŐK IMPORTÁLÁSA EXCELBŐL
df_mat_concrete = load_materials_from_excel(".static/anyagok_ec2.xlsx", "ec-beton")
df_mat_rebar = load_materials_from_excel(".static/anyagok_ec2.xlsx", "ec-betonacel")
df_mat_strand = load_materials_from_excel(".static/anyagok_ec2.xlsx", "ec-paszma")

# Listák létrehozása a legördülő menükhöz
concrete_list = df_mat_concrete['beton'].tolist()
rebar_list = df_mat_rebar['betonacel'].tolist()
strand_list = df_mat_strand['paszma'].tolist()


# ----------------------------------------------------------------
# BEMENŐ ADATOK

# Három oszlopos elrendezés a bemenő adatoknak
col1, col2, col3 = st.columns(3, gap="small", width='stretch', border=True)

with col1:
    st.header("ANYAGOK")
    
    # Beton input adatok
    st.subheader("Beton")
    concrete_beam = st.selectbox("Gerenda szilárdsági osztály:", concrete_list, index=4)
    felbeton_checkbox = st.checkbox("Felbeton?", value=False)
    if felbeton_checkbox:
        concrete_topping = st.selectbox("Felbeton szilárdsági osztály:", concrete_list, index=3)
    gamma_c = st.number_input("Biztonsági tényező (γc):", min_value=0.95, max_value=2.0, value=1.5, step=0.05)
    alfa_cc = st.number_input("Nyomószilárdság módosító tényező (αcc):", min_value=0.75, max_value=1.00, value=1.00, step=0.05,
                              help="A tartós terhelés nyomószilárdságra gyakorolt hatását és a terhelés módjából származó kedvezőtlen hatásokat figyelembe vevő tényező.")
    
    # Betonacél input adatok
    st.subheader("Betonacél")
    rebar = st.selectbox("Válassza ki a betonacél típusát:", rebar_list, index=3)
    gamma_s = st.number_input("Biztonsági tényező (γs):", min_value=0.95, max_value=2.0, value=1.15, step=0.05)
    
    # Feszítőpászma input adatok
    st.subheader("Feszítőpászma")
    strand = st.selectbox("Válassza ki a feszítőpászma típusát:", strand_list, index=1)
    gamma_p = st.number_input("Biztonsági tényező (γp):", min_value=0.95, max_value=2.0, value=1.15, step=0.05)


with col2:
    st.header("GEOMETRIA", help="Gerenda keresztmetszeti méreteinek megadása, a felső szélső száltól lefelé haladva.")

    st.caption("""
               - 'z' a keresztmetszet jellemző szálainak relatív magassági szintje
               - 'b(z)' a keresztmetszet szélessége az adott 'z' magasságban
               - 'z' értékének fentről lefelé csökkennie kell!
               - Csak gyenge tengelyre szimmetrikus keresztmetszet definiálható!
               """)
    
    df_cs_points = st.data_editor(pd.DataFrame([{"z [cm]": 50.0, "b(z) [cm]": 25.0},
                                                {"z [cm]": 0.0, "b(z) [cm]": 25.0}]),
                                                num_rows="dynamic",
                                                hide_index=True)


    if felbeton_checkbox:
        h_topping = st.number_input("Felbeton vastagság (htopping) [cm]:", min_value=0., value=20., step=0.1, format="%0.1f")
        b_topping = st.number_input("Felbeton szélesség (btopping) [cm]:", min_value=0., value=20., step=0.1, format="%0.1f")

    # INSERT IDE: KERESZTMETSZET KIRAJZOLÁSA REAL TIME!

with col3:
    st.header("VASALÁS")

    st.subheader("Alsó lágyvasalás")
    df_bottom_reinf = st.data_editor(pd.DataFrame([{"d [mm]": 20, "N [db]": 4, "zi [cm]": 5.0}]),
                                     num_rows="dynamic",
                                     hide_index=True)

    st.subheader("Felső lágyvasalás")
    df_top_reinf = st.data_editor(pd.DataFrame([{"d [mm]": 16, "N [db]": 2, "zi [cm]": 5.0}]),
                                  num_rows="dynamic",
                                  hide_index=True)

    st.subheader("Feszítőpászmák")
    df_strands = st.data_editor(pd.DataFrame([{"N [db]": 0, "zi [cm]": 10}]),
                                num_rows="dynamic",
                                hide_index=True)
    prestress = st.number_input("Feszítési feszültség [N/mm2]:", min_value=0, value=1000, step=50)
    prestress_loss = st.number_input("Feszültségveszteség (becsült) [%]:", min_value=0, value=15, step=1)

    st.subheader("Kengyelezés")
    df_stirrups = st.data_editor(pd.DataFrame([{"d [mm]": 8, "s [mm]": 100, "nsw [szár]": 2},
                                               {"d [mm]": 8, "s [mm]": 200, "nsw [szár]": 2}]),
                                 num_rows="dynamic",
                                 hide_index=True)
    
# --- Számítás gomb ---
# if st.button("Számítás"):
    # st.session_state.results = {
    #     "MRd (nyomaték teherbírás)": calc_MRd(bw, h, fck, as1),
    #     "VRd (nyírási teherbírás)": calc_VRd(bw, h, fck)}

# --- Eredmények ---
# if st.session_state.results:
    
