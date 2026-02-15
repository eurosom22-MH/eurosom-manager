import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide")

# --- 2. STYLE DESIGN ÉPURÉ ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    h1 { color: #212529; border-bottom: 2px solid #800020; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS DE TRAITEMENT ---

def clean_data(df):
    """Nettoie les données Eurosom"""
    if df.empty: return df
    
    # Nettoyage des noms de colonnes
    df.columns = df.columns.astype(str).str.upper().str.strip()
    
    # Conversion du CA (Nettoyage des symboles € et espaces)
    def c_num(x):
        if pd.isna(x): return 0.0
        s = str(x).replace('€','').replace(' ','').replace('\xa0','').replace(',','.')
        try: return float(s)
        except: return 0.0

    # On cherche la colonne Montant (même si le nom varie légèrement)
    col_ca = [c for c in df.columns if "MONTANT" in c]
    if col_ca:
        df['CA_CLEAN'] = df[col_ca[0]].apply(c_num)
    else:
        df['CA_CLEAN'] = 0.0

    # Gestion des dates
    col_date_cmd = [c for c in df.columns if "DATE DE LA COMMANDE" in c]
    if col_date_cmd:
        df['DATE_CMD'] = pd.to_datetime(df[col_date_cmd[0]], errors='coerce', dayfirst=True)
        df['Exercice'] = df['DATE_CMD'].apply(lambda x: f"{x.year}-{x.year+1}" if pd.notnull(x) and x.month >= 8 else (f"{x.year-1}-{x.year}" if pd.notnull(x) else "N/A"))
        df['Mois_Cmd'] = df['DATE_CMD'].dt.strftime('%m-%B')
        df['Annee'] = df['DATE_CMD'].dt.year.astype(str)
    
    col_date_pose = [c for c in df.columns if "DATE PREVUE" in c or "DELAI" in c]
    if col_date_pose:
        df['DATE_POSE'] = pd.to_datetime(df[col_date_pose[0]], errors='coerce', dayfirst=True)
        df['Mois_Pose'] = df['DATE_POSE'].dt.strftime('%m-%B')

    return df

@st.cache_data(ttl=600)
def load_data():
    """Connexion au Google Sheet via les Secrets"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # On lit la feuille sans préciser le nom de l'onglet pour éviter les erreurs
        df = conn.read() 
        return df
    except Exception as e:
        st.error(f"Erreur de connexion Drive : {e}")
        return pd.DataFrame()

# --- 4. INTERFACE ---

st.title("🛡️ EUROSOM Manager")

df_raw = load_data()
df = clean_data(df_raw)

if df.empty:
    st.warning("⚠️ Aucune donnée trouvée. Vérifiez que votre Google Sheet n'est pas vide et que le lien dans 'Secrets' est correct.")
else:
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.markdown("### ⚙️ FILTRES")
        view_mode = st.radio("Mode de vue", ["Exercice Comptable", "Année Civile"])
        
        commerciaux = ["Tous"] + sorted([str(c) for c in df["COMMERCIAL"].dropna().unique()])
        sel_comm = st.selectbox("Commercial", commerciaux)
        
        if view_mode == "Exercice Comptable":
            periodes = sorted(df["Exercice"].unique().tolist())
        else:
            periodes = sorted(df["Annee"].unique().tolist())
        
        sel_period = st.selectbox("Période", periodes, index=len(periodes)-1)

    # --- FILTRAGE FINAL ---
    df_f = df.copy()
    if sel_comm != "Tous":
        df_f = df_f[df_f["COMMERCIAL"] == sel_comm]
    
    col_p = "Exercice" if view_mode == "Exercice Comptable" else "Annee"
    df_f = df_f[df_f[col_p] == sel_period]

    # --- AFFICHAGE ---
    c1, c2, c3 = st.columns(3)
    total_ca = df_f["CA_CLEAN"].sum()
    c1.metric("CA TOTAL HT", f"{total_ca:,.0f} €".replace(",", " "))
    c2.metric("COMMANDES", len(df_f))
    c3.metric("MOYENNE / CDE", f"{total_ca/len(df_f):,.0f} €".replace(",", " ") if len(df_f)>0 else "0 €")

    st.divider()

    t1, t2 = st.tabs(["📊 Graphiques", "📂 Liste des données"])
    
    with t1:
        col_a, col_b = st.columns(2)
        with col_a:
            if "Mois_Cmd" in df_f.columns:
                st.subheader("Ventes par Mois (Commande)")
                fig1 = px.bar(df_f.groupby("Mois_Cmd")["CA_CLEAN"].sum().reset_index(), x="Mois_Cmd", y="CA_CLEAN", color_discrete_sequence=['#800020'])
                st.plotly_chart(fig1, use_container_width=True)
        with col_b:
            if "Mois_Pose" in df_f.columns:
                st.subheader("Facturation par Mois (Pose)")
                fig2 = px.bar(df_f.groupby("Mois_Pose")["CA_CLEAN"].sum().reset_index(), x="Mois_Pose", y="CA_CLEAN", color_discrete_sequence=['#2E7D32'])
                st.plotly_chart(fig2, use_container_width=True)

    with t2:
        st.dataframe(df_f, use_container_width=True)
