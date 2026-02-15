import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide", page_icon="📊")

# --- 2. STYLE ÉPURÉ DÉGRADÉ (ROUGE, BLANC, GRIS) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* Cartes Metrics avec dégradé subtil */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    
    [data-testid="stMetricLabel"] {
        color: #495057 !important;
        font-weight: bold !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Barre latérale blanche épurée */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #dee2e6;
    }
    
    /* Boutons en dégradé Bordeaux */
    .stButton>button {
        background: linear-gradient(90deg, #800020 0%, #a31621 100%);
        color: white;
        border: None;
        padding: 10px 25px;
        border-radius: 8px;
        font-weight: bold;
        width: 100%;
    }
    
    /* Titres avec ligne de soulignement Bordeaux */
    h1, h2 {
        color: #212529;
        font-family: 'Inter', sans-serif;
        border-bottom: 2px solid #800020;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CHARGEMENT ET NETTOYAGE DES DONNÉES ---
from streamlit_gsheets import GSheetsConnection

@st.cache_data(ttl=600)
def load_data():
    try:
        # Création de la connexion en utilisant les Secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Lecture de la feuille (mettez le nom exact de votre onglet Excel)
        df = conn.read(worksheet="SUIVI COMMANDES EN COURS")
        return df
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return pd.DataFrame()

# --- 4. BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.markdown("## ⚙️ FILTRES")
    view_mode = st.radio("Mode de vue", ["Exercice Comptable", "Année Civile"])
    
    # Chargement des données
    df_raw = load_data()
    df = clean_data(df_raw)
    
    if not df.empty:
        commerciaux = ["Tous"] + sorted(df["COMMERCIAL"].dropna().unique().tolist())
        sel_comm = st.selectbox("Commercial", commerciaux)
        
        periodes = sorted(df["Exercice"].unique().tolist()) if view_mode == "Exercice Comptable" else sorted(df["DATE_CMD"].dt.year.dropna().unique().tolist())
        sel_period = st.selectbox("Période", periodes, index=len(periodes)-1)
        
        st.divider()
        if st.button("🔄 Actualiser les données"):
            st.cache_data.clear()
            st.rerun()

# --- 5. CORPS DE L'APPLICATION ---
st.title("🛡️ EUROSOM Manager")

if df.empty:
    st.info("👋 Bienvenue. Veuillez connecter votre Google Sheet dans les paramètres secrets pour afficher vos données.")
    # Image illustrative du flux de données
    st.write("### Schéma de fonctionnement")
    
else:
    # Filtrage
    df_f = df.copy()
    if sel_comm != "Tous":
        df_f = df_f[df_f["COMMERCIAL"] == sel_comm]
    # Filtre période (à adapter selon colonne)
    
    # --- INDICATEURS ---
    c1, c2, c3 = st.columns(3)
    ca_total = df_f["CA_CLEAN"].sum()
    c1.metric("CA COMMANDÉ HT", f"{ca_total:,.0f} €".replace(",", " "))
    c2.metric("COMMANDES", len(df_f))
    c3.metric("DÉPARTEMENTS", df_f["CP"].str[:2].nunique() if "CP" in df_f.columns else 0)

    st.divider()

    # --- ONGLETS ---
    tab_dash, tab_com, tab_reg = st.tabs(["📊 Dashboard", "⚡ Actions Commerciaux", "📂 Registre"])

    with tab_dash:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📈 Ventes (Date Commande)")
            fig1 = px.bar(df_f.groupby("Mois_Cmd")["CA_CLEAN"].sum().reset_index(), 
                          x="Mois_Cmd", y="CA_CLEAN", color_discrete_sequence=['#800020'])
            fig1.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)

        with col_right:
            st.subheader("🎯 Prévision Facturation (Date Pose)")
            fig2 = px.bar(df_f.groupby("Mois_Pose")["CA_CLEAN"].sum().reset_index(), 
                          x="Mois_Pose", y="CA_CLEAN", color_discrete_sequence=['#2E7D32'])
            fig2.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig2, use_container_width=True)

    with tab_com:
        st.subheader("📏 Mesures prioritaires à prendre")
        # Logique de calcul Butoire (Pose - 7 sem ou - 2 sem)
        # Affichage du tableau filtré pour les commerciaux
        st.dataframe(df_f[df_f["STATUT MESURES"] != "RECUES"], use_container_width=True)

    with tab_reg:
        st.subheader("📑 Registre complet")
        search = st.text_input("Recherche rapide (Client, Ville...)")
        if search:
            df_f = df_f[df_f.astype(str).apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)]
        st.dataframe(df_f, use_container_width=True)
