import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIG PAGE ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide")

# --- STYLE ÉPURÉ ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px; border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    h1 { color: #212529; border-bottom: 2px solid #800020; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION DRIVE ---
@st.cache_data(ttl=600)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read()
        return df
    except Exception as e:
        st.error(f"Erreur de connexion sécurisée : {e}")
        return pd.DataFrame()

# --- TRAITEMENT ---
st.title("🛡️ EUROSOM Manager")

df = load_data()

if not df.empty:
    # Nettoyage automatique des noms de colonnes
    df.columns = df.columns.astype(str).str.upper().str.strip()
    
    # Indicateurs
    col1, col2, col3 = st.columns(3)
    col1.metric("Commandes en cours", len(df))
    
    # Recherche d'une colonne de montant pour le CA
    col_ca = [c for c in df.columns if "MONTANT" in c]
    if col_ca:
        def c_num(x):
            s = str(x).replace('€','').replace(' ','').replace(',','.')
            try: return float(s)
            except: return 0.0
        total = df[col_ca[0]].apply(c_num).sum()
        col2.metric("CA Global HT", f"{total:,.0f} €".replace(",", " "))

    st.divider()
    
    # Barre de recherche
    search = st.text_input("🔍 Rechercher un client, une ville ou un n° de commande")
    if search:
        df = df[df.astype(str).apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)]

    st.subheader("📑 Registre des données")
    st.dataframe(df, use_container_width=True)
else:
    st.info("⌛ En attente des données de votre Google Sheet...")
