import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from shapely import Polygon
from structuralcodes.geometry import add_reinforcement_line
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

# ---- Function to create Shapely polygon from dataframe values ----
def polygon_from_profile(df, z_col="z [cm]", b_col="b(z) [cm]"):
    """
    Build a Shapely polygon from a dataframe containing vertical coordinates (z)
    and widths b(z).
    
    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns for z and b(z).
    z_col : str
        Column name for z coordinate.
    b_col : str
        Column name for width b(z).
    
    Returns
    -------
    shapely.geometry.Polygon
    """
    # Sort by z so we go bottom-to-top
    df_sorted = df.sort_values(z_col)

    # Left boundary: from bottom to top
    left_side = [(-row[b_col]/2, row[z_col]) for _, row in df_sorted.iterrows()]

    # Right boundary: from top to bottom
    right_side = [(row[b_col]/2, row[z_col]) for _, row in df_sorted[::-1].iterrows()]

    # Combine to form closed loop
    coords = left_side + right_side

    return Polygon(coords)


# ---- Create function to plot the cross-section
def plot_polygon(polygon, ax=None, facecolor="limegreen", edgecolor="black", 
                 alpha=1.0, figsize=(4, 4), fontsize=5):
    """
    Plot a Shapely polygon with matplotlib.
    
    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon to plot.
    ax : matplotlib.axes.Axes, optional
        Existing matplotlib axis. If None, a new figure and axis are created.
    facecolor : str
        Fill color of the polygon.
    edgecolor : str
        Outline color of the polygon.
    alpha : float
        Transparency of the fill.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    # Exterior boundary
    x, y = polygon.exterior.xy
    ax.fill(x, y, facecolor=facecolor, edgecolor=edgecolor, alpha=alpha)

    ax.tick_params(axis="both", labelsize=fontsize)

    ax.set_aspect("equal")
    # Streamlit display
    st.pyplot(fig)


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
# 1000px széles mező, az oszlopok relatív szélessége [1, 1, 1.2]
col1, col2, col3 = st.columns([1, 1, 1.2], gap="small", width=1000, border=True)

with col1:
    st.header("ANYAGOK")
    
    # Beton input adatok
    st.subheader("Beton")
    selected_concrete_beam = st.selectbox("Gerenda szilárdsági osztály:", concrete_list, index=4)
    felbeton_checkbox = st.checkbox("Felbeton?", value=False)
    if felbeton_checkbox:
        selected_concrete_topping = st.selectbox("Felbeton szilárdsági osztály:", concrete_list, index=3)
    gamma_c = st.number_input("Biztonsági tényező (γc):", min_value=1.0, max_value=2.0, value=1.5, step=0.05)
    alfa_cc = st.number_input("Nyomószilárdság módosító tényező (αcc):", min_value=0.75, max_value=1.00, value=1.00, step=0.05,
                              help="A tartós terhelés nyomószilárdságra gyakorolt hatását és a terhelés módjából származó kedvezőtlen hatásokat figyelembe vevő tényező.")
    
    # Betonacél input adatok
    st.subheader("Betonacél")
    selected_rebar_longitudinal = st.selectbox("Hosszvasalás betonacél:", rebar_list, index=3)
    selected_rebar_stirrup = st.selectbox("Kengyel betonacél:", rebar_list, index=3)
    gamma_s = st.number_input("Biztonsági tényező (γs):", min_value=1.00, max_value=2.0, value=1.15, step=0.05)
    
    # Feszítőpászma input adatok
    st.subheader("Feszítőpászma")
    selected_strand = st.selectbox("Válassza ki a feszítőpászma típusát:", strand_list, index=1)
    gamma_p = st.number_input("Biztonsági tényező (γp):", min_value=1.00, max_value=2.0, value=1.15, step=0.05)


with col2:
    st.header("GEOMETRIA", 
              help= """
- 'z' a keresztmetszet jellemző szálainak relatív magassági szintje
- 'b(z)' a keresztmetszet szélessége az adott 'z' magasságban
- 'z' értékének fentről lefelé csökkennie kell!
- Csak gyenge tengelyre szimmetrikus keresztmetszet definiálható!""")

    # Keresztmetszet definiálása
    df_cs_points = st.data_editor(pd.DataFrame([{"z [cm]": 50.0, "b(z) [cm]": 25.0},
                                                {"z [cm]": 0.0, "b(z) [cm]": 25.0}]),
                                                num_rows="dynamic",
                                                hide_index=True)
    
    # Felbeton definiálása
    if felbeton_checkbox:
        h_topping = st.number_input("Felbeton vastagság (htopping) [cm]:", min_value=0., value=20., step=0.1, format="%0.1f")
        b_topping = st.number_input("Felbeton szélesség (btopping) [cm]:", min_value=0., value=20., step=0.1, format="%0.1f")
        topping_cross_section = Polygon([(-b_topping/2, df_cs_points['z [cm]'].max()),
                                        (b_topping/2, df_cs_points['z [cm]'].max()),
                                        (b_topping/2, df_cs_points['z [cm]'].max()+h_topping),
                                        (-b_topping/2, df_cs_points['z [cm]'].max()+h_topping)])

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

# ----------------------------------------------------------------
# SZÁMÍTÁSI ALAP VÁLTOZÓK DEFINIÁLÁSA

# BETONOK DEFINIÁLÁSA
concrete_beam = sc.materials.concrete.ConcreteEC2_2004(fck= df_mat_concrete.loc[df_mat_concrete['beton'] == selected_concrete_beam, 'fck'].values[0],
                                                       density=2500,
                                                       gamma_c=gamma_c,
                                                       alpha_cc=alfa_cc)
if felbeton_checkbox:
    concrete_topping = sc.materials.concrete.ConcreteEC2_2004(fck= df_mat_concrete.loc[df_mat_concrete['beton'] == selected_concrete_topping, 'fck'].values[0],
                                                             density=2500,
                                                             gamma_c=gamma_c,
                                                             alpha_cc=alfa_cc)

# BETONACÉLOK DEFINIÁLÁSAselected_rebar_longitudinal
rebar = sc.materials.reinforcement.ReinforcementEC2_2004(fyk= df_mat_rebar.loc[df_mat_rebar['betonacel'] == selected_rebar_longitudinal, 'fyk'].values[0],
                                                         Es=200000,
                                                         ftk = df_mat_rebar.loc[df_mat_rebar['betonacel'] == selected_rebar_longitudinal, 'ftk'].values[0],
                                                         gamma_s=gamma_s,
                                                         epsuk= df_mat_rebar.loc[df_mat_rebar['betonacel'] == selected_rebar_longitudinal, 'epsuk'].values[0])

# FESZÍTŐPÁSZMÁK DEFINIÁLÁSA
strand = sc.materials.reinforcement.ReinforcementEC2_2004(fyk= df_mat_strand.loc[df_mat_strand['paszma'] == selected_strand, 'fp.0.1k'].values[0],
                                                          Es=195000,
                                                          ftk = df_mat_strand.loc[df_mat_strand['paszma'] == selected_strand, 'fpk'].values[0],
                                                          gamma_s=gamma_p,
                                                          epsuk= df_mat_strand.loc[df_mat_strand['paszma'] == selected_strand, 'epsuk'].values[0])

# KERESZTMETSZET LÉTREHOZÁSA ANYAGOKKAL
cross_section_beam = sc.geometry.SurfaceGeometry(poly=polygon_from_profile(df_cs_points),
                                                 material=concrete_beam)

if felbeton_checkbox:
    cross_section_topping = sc.geometry.SurfaceGeometry(poly=topping_cross_section,
                                                        material=concrete_topping)
    cross_section_beam = cross_section_beam.__add__(other=cross_section_topping)

# Vasalások hozzáadása a keresztmetszethez
for _, row in df_bottom_reinf.iterrows():
    cross_section_beam = add_reinforcement_line(cross_section_beam,
                                                coords_i=(-(df_cs_points["b(z) [cm]"].iloc[-1]/2 + 3.5)*10, row['zi [cm]']*10),
                                                coords_j=((df_cs_points["b(z) [cm]"].iloc[-1]/2 - 3.5)*10, row['zi [cm]']*10) ,
                                                diameter=row['d [mm]'],
                                                n=row['N [db]'],
                                                material=rebar)


# cross_section_beam.geometries[0].polygon.exterior
# fig, ax = plt.subplots()
# for geom in cross_section_beam.geometries:
#     x, y = geom.polygon.exterior.xy
#     ax.plot(x, y, color="black")
#     ax.fill(x, y, facecolor="limegreen", edgecolor="black", alpha=1.0)
# ax.set_aspect("equal")

# st.pyplot(fig)


# ----------------------------------------------------------------
# SZÁMÍTÁSI FÜGGVÉNYEK





# ----------------------------------------------------------------
# --- Számítás gomb ---
if st.button("SZÁMÍTÁS", type="primary", icon=":material/calculate:", ):
    pass
    # st.session_state.results = {
    #     "MRd (nyomaték teherbírás)": calc_MRd(bw, h, fck, as1),
    #     "VRd (nyírási teherbírás)": calc_VRd(bw, h, fck)}

# ----------------------------------------------------------------
# --- Eredmények ---
# if st.session_state.results:
    
