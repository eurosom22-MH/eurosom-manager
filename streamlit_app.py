import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px; border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] { background-color: #800020 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS DE NETTOYAGE ET SÉCURITÉ ---
def format_euro(valeur):
    return f"{valeur:,.0f} €".replace(",", " ")

def get_col(df, keyword):
    """Trouve une colonne même si le nom n'est pas exact"""
    for c in df.columns:
        if keyword.upper() in c.upper():
            return c
    return None

@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read()

# --- 3. TRAITEMENT DES DONNÉES ---
df_raw = load_data()

if not df_raw.empty:
    df = df_raw.copy()
    # Identification dynamique des colonnes pour éviter les KeyError
    c_client = get_col(df, "CLIENT") or "NOM DU CLIENT"
    c_ville = get_col(df, "VILLE") or "VILLE"
    c_mt = get_col(df, "MONTANT") or "MONTANT HT COMMANDE"
    c_date_c = get_col(df, "DATE DE LA COMMANDE") or "DATE DE LA COMMANDE"
    c_date_p = get_col(df, "DATE PREVUE") or "DATE PREVUE DELAI"
    c_statut = get_col(df, "STATUT MESURES") or "STATUT MESURES"
    c_comm = get_col(df, "COMMERCIAL") or "COMMERCIAL"
    c_cp = get_col(df, "CP") or "CP"
    c_h = get_col(df, "HEURE") or "NOMBRE HEURES"

    # Conversions numériques
    def to_f(x):
        try: return float(str(x).replace('€','').replace(' ','').replace(',','.'))
        except: return 0.0

    df['MT_NUM'] = df[c_mt].apply(to_f) if c_mt in df.columns else 0.0
    df['H_NUM'] = pd.to_numeric(df[c_h], errors='coerce').fillna(0) if c_h in df.columns else 0.0
    
    # Dates
    df['D_CMD'] = pd.to_datetime(df[c_date_c], errors='coerce', dayfirst=True)
    df['D_POSE'] = pd.to_datetime(df[c_date_p], errors='coerce', dayfirst=True)
    df['M_CMD'] = df['D_CMD'].dt.strftime('%Y-%m')
    df['M_POSE'] = df['D_POSE'].dt.strftime('%Y-%m')
    df['DEPT'] = df[c_cp].astype(str).str[:2]

    # --- INTERFACE ---
    st.title("🛡️ EUROSOM Manager")
    t1, t2, t3 = st.tabs(["📊 DASHBOARD", "✍️ SAISIE", "💼 COMMERCIAUX"])

    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("CA TOTAL", format_euro(df['MT_NUM'].sum()))
        c2.metric("COMMANDES", len(df))
        c3.metric("HEURES POSE", f"{df['H_NUM'].sum():,.0f} h")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("📈 Ventes (Date Commande)")
            fig1 = px.bar(df.groupby('M_CMD')['MT_NUM'].sum().reset_index(), x='M_CMD', y='MT_NUM', color_discrete_sequence=['#800020'])
            fig1.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
            
            st.subheader("🌍 Répartition Géo")
            fig_p = px.pie(df.groupby('DEPT')['MT_NUM'].sum().reset_index(), values='MT_NUM', names='DEPT', hole=0.5, color_discrete_sequence=px.colors.sequential.Reds)
            st.plotly_chart(fig_p, use_container_width=True)

        with col_g2:
            st.subheader("🎯 Facturation (Date Pose)")
            fig2 = px.bar(df.groupby('M_POSE')['MT_NUM'].sum().reset_index(), x='M_POSE', y='MT_NUM', color_discrete_sequence=['#2E7D32'])
            fig2.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("⏳ Charge de Pose (Heures)")
            fig3 = px.line(df.groupby('M_POSE')['H_NUM'].sum().reset_index(), x='M_POSE', y='H_NUM', markers=True)
            st.plotly_chart(fig3, use_container_width=True)

    with t2:
        st.subheader("📝 Nouvelle Commande")
        with st.form("form_saisie", clear_on_submit=True):
            f1, f2 = st.columns(2)
            n_cde = f1.text_input("N° Commande")
            n_cli = f2.text_input("Client")
            n_mt = f1.number_input("Montant HT", min_value=0)
            n_comm = f2.selectbox("Commercial", sorted(df[c_comm].dropna().unique()))
            n_date = f1.date_input("Date Commande")
            n_pose = f2.date_input("Date Pose Prévue")
            
            if st.form_submit_button("💾 ENREGISTRER DANS LE GOOGLE SHEET"):
                new_row = pd.DataFrame([{c_date_c: n_date.strftime('%d/%m/%Y'), c_client: n_cli, c_mt: n_mt, c_comm: n_comm, c_date_p: n_pose.strftime('%d/%m/%Y'), "NUMÉRO DE COMMANDE": n_cde}])
                conn = st.connection("gsheets", type=GSheetsConnection)
                updated_df = pd.concat([df_raw, new_row], ignore_index=True)
                conn.update(worksheet="SUIVI COMMANDES EN COURS", data=updated_df)
                st.cache_data.clear()
                st.success("✅ Commande enregistrée ! Elle apparaîtra après actualisation.")

    with t3:
        st.subheader("💼 Suivi par Commercial")
        sel_c = st.selectbox("Choisir un commercial", ["Tous"] + sorted(df[c_comm].dropna().unique().tolist()))
        df_view = df if sel_c == "Tous" else df[df[c_comm] == sel_c]
        
        # Affichage sécurisé des colonnes existantes
        cols_to_show = [c for c in [c_date_c, c_client, c_ville, c_mt, c_statut] if c in df.columns]
        st.dataframe(df_view[cols_to_show], use_container_width=True)
        
        st.markdown("### ⚠️ Mesures non reçues")
        if c_statut in df.columns:
            df_alerte = df_view[df_view[c_statut].astype(str).str.upper() != "RECUES"]
            st.table(df_alerte[[c_client, c_ville, c_date_p]] if not df_alerte.empty else "Aucune alerte")

else:
    st.error("Impossible de lire les colonnes du fichier. Vérifiez les en-têtes de votre Google Sheet.")
