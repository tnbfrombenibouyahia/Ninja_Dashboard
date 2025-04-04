import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta, date
import calendar
import datetime as dt
import yfinance as yf
import plotly.graph_objects as go
from data_cleaner import load_and_clean_csv, update_historical_data
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="🥷 Trading Dashboard",
    layout="wide",
    page_icon="🥷",
    initial_sidebar_state="expanded"
)

from utils_visuals import (
    plot_equity_curve,
    plot_drawdown_curve,
    plot_gain_loss_pie,
    plot_asset_distribution,
    plot_avg_duration_per_day,
    plot_return_vs_duration,
    compute_stats_dict,
    plot_pnl_by_hour,
    plot_pnl_by_day_of_week,
    plot_daily_pnl,
    plot_daily_drawdown,
    plot_histogram_mae_mfe_etd,
    plot_scatter_mfe_vs_profit,
)

# 👤 Utilisateurs de test (tu pourras en ajouter ou changer plus tard)
names = ["Théo Naïm BENHELLAL", "Alexis DURIN"]
usernames = ["theonaimben@gmail.com", "alexisdurin@gmail.com"]

# 🔐 Mots de passe déjà hashés (générés une fois pour toutes)
hashed_passwords = [
    '$2b$12$kF09FDXUmrjH/epfedMW0RkUGZBd3mCUbGvswsSTFz05CLzyRjba',
    '$2b$12$/DFXDjyc2sEGqPXCweJqduJcxE6tSlvk1MnAYVIJErU1/ELgM7b9C'
]

# Configuration des utilisateurs
credentials = {
    "usernames": {
        uname: {"name": name, "password": pwd}
        for uname, name, pwd in zip(usernames, names, hashed_passwords)
    }
}

# Création de l'authenticator
authenticator = stauth.Authenticate(
    credentials,
    "dashboard_cookie", "abcdef", cookie_expiry_days=7
)

# Bloc de login
login_result = authenticator.login(location="main")

try:
    name, authentication_status, username = login_result
except TypeError:
    name = authentication_status = username = None

# === Affichage du login
if authentication_status is False:
    st.error("Nom d’utilisateur ou mot de passe invalide ❌")
    st.session_state.clear()

elif authentication_status is None:
    st.warning("Veuillez entrer vos identifiants 🔐")

elif authentication_status:

    # Exemple : logout
    authenticator.logout("🚪 Se déconnecter", "sidebar")
    st.sidebar.success(f"Connecté en tant que {name}")

    # Fichiers perso
    user_data_dir = os.path.join("data", username)
    os.makedirs(user_data_dir, exist_ok=True)
    data_file = os.path.join(user_data_dir, "trades_historique.csv")
    journal_file = os.path.join(user_data_dir, "journal_notes.json")

    st.success(f"Bienvenue {name} 👋")
    authenticator.logout("🚪 Se déconnecter", "sidebar")
    st.sidebar.success(f"Connecté en tant que {name}")

    # Initialisation fichiers si absents
    if not os.path.exists(data_file):
        pd.DataFrame(columns=["Entry time", "Exit time", "Instrument", "Market pos.", "Entry price", "Exit price", "Qty", "Profit", "MAE", "MFE", "ETD"]).to_csv(data_file, index=False)

    if not os.path.exists(journal_file):
        with open(journal_file, "w") as f:
            json.dump({}, f)
    
    # === Chargement de l'historique (après la définition de `data_file`)
    try:
        if os.path.exists(data_file):
            df_histo = pd.read_csv(data_file, parse_dates=["Entry time", "Exit time"])
            df_histo = df_histo[pd.notnull(df_histo["Entry time"])]
            df_histo["Instrument"] = df_histo["Instrument"].str.extract(r"^([A-Z]+)")
        else:
            st.warning("Aucun fichier d'historique trouvé pour cet utilisateur.")
            st.stop()
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier historique : {e}")
        st.stop()

    # === UI Style
    st.markdown("""
        <style>
            html, body, [class*="css"]  {
                font-family: 'Inter', sans-serif;
            }
            .block-container {
                padding-top: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title(" 🥷 Dashboard NinjaTrader")


    # === Filtres en haut de la page principale
    st.markdown("---")
    st.header("👀 Filtres")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        instruments = df_histo["Instrument"].unique().tolist()
        instrument = st.selectbox("🇺🇸 Instrument", ["Tous"] + instruments)

    with col_f2:
        directions = df_histo["Market pos."].unique().tolist()
        direction = st.selectbox("📌 Positions", ["Tous"] + directions)

    with col_f3:
        if not df_histo["Entry time"].dropna().empty:
            default_start = pd.to_datetime(df_histo["Entry time"]).min().date()
            default_end = pd.to_datetime(df_histo["Entry time"]).max().date()
        else:
            default_start = date.today() - timedelta(days=30)
            default_end = date.today()

        date_range = st.date_input("📅 Période", (default_start, default_end))


        # === Application des filtres
        df_filtered = df_histo.copy()

        if instrument != "Tous":
            df_filtered = df_filtered[df_filtered["Instrument"] == instrument]

        if direction != "Tous":
            df_filtered = df_filtered[df_filtered["Market pos."] == direction]

        # 🔍 Gère une seule date ou une plage
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        elif isinstance(date_range, date):
            start_date = end_date = date_range
        else:
            start_date = df_histo["Entry time"].min().date()
            end_date = df_histo["Entry time"].max().date()

        if not df_filtered.empty and pd.api.types.is_datetime64_any_dtype(df_filtered["Entry time"]):
            df_filtered = df_filtered[
                (df_filtered["Entry time"].dt.date >= start_date) &
                (df_filtered["Entry time"].dt.date <= end_date)
            ]


        # === Sidebar : Upload uniquement
        st.sidebar.markdown("## 📂 Import Zone")
        uploaded_file = st.sidebar.file_uploader("", type=["csv"])

        if uploaded_file:
            df_new = load_and_clean_csv(uploaded_file)

            # Fichier de l'utilisateur connecté
            user_csv_path = os.path.join(user_data_dir, "trades_historique.csv")

            df_combined, new_count = update_historical_data(df_new, user_csv_path)

            st.sidebar.success(f"{new_count} nouveaux trades ajoutés à l'historique. Recharge la page pour voir les changements.")


            # 🔁 Charger l'historique existant
            if os.path.exists(data_file):
                df_existing = pd.read_csv(data_file, parse_dates=["Entry time", "Exit time"])
            else:
                df_existing = pd.DataFrame()

            # 🔀 Fusionner les nouveaux trades sans doublons
            df_combined = pd.concat([df_existing, df_new]).drop_duplicates()
            new_trades_count = len(df_combined) - len(df_existing)

            # 💾 Écrire dans le bon fichier utilisateur
            df_combined.to_csv(data_file, index=False)

            st.sidebar.success(f"{new_trades_count} nouveaux trades ajoutés à l'historique. Recharge la page pour voir les changements.")


    # === Journal de séance (dans la sidebar)
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📓 Journal de séance")

    # Chargement des données du journal
    journal_file = os.path.join(user_data_dir, "journal_notes.json")
    image_dir = os.path.join(user_data_dir, "journal_images")

    os.makedirs(image_dir, exist_ok=True)

    if not os.path.exists(journal_file):
        with open(journal_file, "w") as f:
            json.dump({}, f)

    with open(journal_file, "r") as f:
        journal = json.load(f)

    for k, v in journal.items():
        if isinstance(v, str):
            journal[k] = {"text": v, "images": []}

    # Date du jour
    aujourd_hui = pd.to_datetime("today").normalize()
    cle_du_jour = str(aujourd_hui)

    if cle_du_jour not in journal:
        st.sidebar.warning("📝 Tu n’as pas encore rempli ta note de trading aujourd’hui !")

    note = st.sidebar.text_area("✍️ Ta note du jour", value=journal.get(cle_du_jour, {}).get("text", ""), height=150)
    images = st.sidebar.file_uploader("📸 Ajouter des captures", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if st.sidebar.button("💾 Sauvegarder ma note", use_container_width=True):
        saved_images = []
        for img in images:
            img_path = os.path.join(image_dir, f"{cle_du_jour}_{img.name}")
            with open(img_path, "wb") as f:
                f.write(img.getbuffer())
            saved_images.append(img_path)

        journal[cle_du_jour] = {"text": note, "images": saved_images}
        with open(journal_file, "w") as f:
            json.dump(journal, f)
        st.sidebar.success("Note enregistrée avec succès 🎉")


    # st.sidebar.markdown("---")
    # st.sidebar.markdown("## 📤 Export Zone")
    # if not df_filtered.empty:
    #     csv = df_filtered.to_csv(index=False).encode("utf-8")
    #     st.sidebar.download_button(
    #         label="📥 Télécharger les trades affichés",
    #         data=csv,
    #         file_name="trades_filtres.csv",
    #         mime="text/csv",
    #     )

    # Colonnes calculées
    if not df_filtered.empty:
        df_filtered["Durée (min)"] = (df_filtered["Exit time"] - df_filtered["Entry time"]).dt.total_seconds() / 60
        df_filtered["Rendement (%)"] = (df_filtered["Profit"] / (df_filtered["Entry price"] * df_filtered["Qty"])) * 100

    # === Profit / Risk Zone
    st.markdown("## 🎰 Profit / Risk Zone")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_equity_curve(df_filtered), use_container_width=True, key="equity")
    with col2:
        st.plotly_chart(plot_drawdown_curve(df_filtered), use_container_width=True, key="drawdown")

    col_daily1, col_daily2 = st.columns(2)
    with col_daily1:
        st.plotly_chart(plot_daily_pnl(df_filtered), use_container_width=True, key="daily_pnl")
    with col_daily2:
        st.plotly_chart(plot_daily_drawdown(df_filtered), use_container_width=True, key="daily_drawdown")

    # === Statistiques clés
    stats = compute_stats_dict(df_filtered)

    def render_stat_card(title, value, emoji):
        return f"""
        <div style=\"background-color:#0e1117;padding:18px;border-radius:12px;margin:10px;
        text-align:center;box-shadow:0 0 10px rgba(0,0,0,0.3);min-width:160px;\">
            <div style=\"font-size:32px;\">{emoji}</div>
            <div style=\"font-weight:500;font-size:14px;color:#ccc;margin-top:4px;\">{title}</div>
            <div style=\"font-size:26px;font-weight:bold;margin-top:2px;color:#fff;\">{value}</div>
        </div>
        """

    st.markdown("")
    cols1 = st.columns(4)
    cols1[0].markdown(render_stat_card("Meilleur Trade", f"${stats['best_trade']}", "🍫"), unsafe_allow_html=True)
    cols1[1].markdown(render_stat_card("Pire Trade", f"${stats['worst_trade']}", "🌶️"), unsafe_allow_html=True)
    cols1[2].markdown(render_stat_card("Gain Moyen", f"${stats['avg_gain']}", "📈"), unsafe_allow_html=True)
    cols1[3].markdown(render_stat_card("Perte Moyenne", f"${stats['avg_loss']}", "📉"), unsafe_allow_html=True)

    cols2 = st.columns(4)
    cols2[0].markdown(render_stat_card("Total Trades", stats["total_trades"], "💽"), unsafe_allow_html=True)
    cols2[1].markdown(render_stat_card("Winrate", f"{stats['winrate']}%", "🎲"), unsafe_allow_html=True)
    cols2[2].markdown(render_stat_card("Sharpe Ratio", stats["sharpe_ratio"], "🌊"), unsafe_allow_html=True)
    cols2[3].markdown(render_stat_card("Profit Factor", stats["profit_factor"], "🧘‍♂️"), unsafe_allow_html=True)

    # === Timing Zone
    st.markdown("---")
    st.markdown("## 🏄‍♂️ Timing Zone")

    col1b, col2b = st.columns(2)
    with col1b:
        st.plotly_chart(plot_avg_duration_per_day(df_filtered), use_container_width=True, key="avg_duration")
    with col2b:
        st.plotly_chart(plot_return_vs_duration(df_filtered), use_container_width=True, key="return_vs_duration")

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(plot_pnl_by_day_of_week(df_filtered), use_container_width=True, key="pnl_by_day")
    with col4:
        st.plotly_chart(plot_pnl_by_hour(df_filtered), use_container_width=True, key="pnl_by_hour")

    # === Statistiques Timing
    st.markdown("---")
    st.subheader("📊 Statistiques Timing")

    # Vérifie la présence des colonnes nécessaires
    if all(col in df_filtered.columns for col in ["Durée (min)", "Entry time", "Profit"]):
        avg_duration = round(df_filtered["Durée (min)"].mean(), 2)
        active_days = df_filtered["Entry time"].dt.date.nunique()

        try:
            best_day = df_filtered.groupby(df_filtered["Entry time"].dt.day_name())["Profit"].sum().idxmax()
        except ValueError:
            best_day = "N/A"

        try:
            worst_day = df_filtered.groupby(df_filtered["Entry time"].dt.day_name())["Profit"].sum().idxmin()
        except ValueError:
            worst_day = "N/A"

        try:
            best_hour = df_filtered.groupby(df_filtered["Entry time"].dt.hour)["Profit"].sum().idxmax()
        except ValueError:
            best_hour = "N/A"

        try:
            worst_hour = df_filtered.groupby(df_filtered["Entry time"].dt.hour)["Profit"].sum().idxmin()
        except ValueError:
            worst_hour = "N/A"

    else:
        avg_duration = 0
        active_days = 0
        best_day = worst_day = best_hour = worst_hour = "N/A"

    cols_timing = st.columns(3)
    cols_timing[0].markdown(render_stat_card("Durée Moyenne", f"{avg_duration} min", "⏱️"), unsafe_allow_html=True)
    cols_timing[1].markdown(render_stat_card("Jours Actifs", active_days, "📆"), unsafe_allow_html=True)
    cols_timing[2].markdown(render_stat_card("Heure la + rentable", f"{best_hour}h" if best_hour != "N/A" else "N/A", "🎬"), unsafe_allow_html=True)

    cols_timing2 = st.columns(3)
    cols_timing2[0].markdown(render_stat_card("Jour le + rentable", best_day, "📈"), unsafe_allow_html=True)
    cols_timing2[1].markdown(render_stat_card("Jour le - performant", worst_day, "📉"), unsafe_allow_html=True)
    cols_timing2[2].markdown(render_stat_card("Heure la - rentable", f"{worst_hour}h" if worst_hour != "N/A" else "N/A", "🚹"), unsafe_allow_html=True)


    # === Distribution
    st.markdown("---")
    st.markdown("## 🧀 Distribution")

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(plot_asset_distribution(df_filtered), use_container_width=True, key="asset_dist")
    with col6:
        st.plotly_chart(plot_gain_loss_pie(df_filtered), use_container_width=True, key="gain_loss_pie")

    # === Optimisation des targets
    st.markdown("---")
    st.markdown("## 👨‍🔬 Optimisation des targets")


    st.plotly_chart(plot_histogram_mae_mfe_etd(df_filtered), use_container_width=True, key="mae_mfe_etd")
    st.plotly_chart(plot_scatter_mfe_vs_profit(df_filtered), use_container_width=True, key="scatter_mfe_profit")

    mae_mean = round(df_filtered["MAE"].mean(), 2)
    mfe_mean = round(df_filtered["MFE"].mean(), 2)
    etd_mean = round(df_filtered["ETD"].mean(), 2)
    mfe_mae_ratio = round(mfe_mean / mae_mean, 2) if mae_mean != 0 else 0

    cols_targets = st.columns(4)
    cols_targets[0].markdown(render_stat_card("MAE moyen", f"${mae_mean}", "🧨"), unsafe_allow_html=True)
    cols_targets[1].markdown(render_stat_card("MFE moyen", f"${mfe_mean}", "🍾"), unsafe_allow_html=True)
    cols_targets[2].markdown(render_stat_card("ETD moyen", f"${etd_mean}", "🤺"), unsafe_allow_html=True)
    cols_targets[3].markdown(render_stat_card("Ratio MFE/MAE", mfe_mae_ratio, "🧑‍⚖️"), unsafe_allow_html=True)

    # === Liste des trades
    st.markdown("---")
    st.subheader("📋 Liste des trades")
    st.dataframe(df_filtered.sort_values("Entry time", ascending=False), use_container_width=True)


    # === Last Session Navigator
    st.markdown("---")
    st.subheader("🎞️ Dernière Session")

    dates_dispo = sorted(journal.keys())

    if len(dates_dispo) >= 1:
        if "note_index" not in st.session_state:
            st.session_state.note_index = len(dates_dispo) - 1

        col1, col2, col3 = st.columns([1, 6, 1])

        with col1:
            if st.button("⬅️", use_container_width=True) and st.session_state.note_index > 0:
                st.session_state.note_index -= 1

        selected_date = dates_dispo[st.session_state.note_index]
        selected_note = journal[selected_date]

        with col2:
            st.markdown(f"""
                <div style='text-align: center; font-size: 26px; padding-top: 6px;'>
                    📅 {selected_date.split(" ")[0]}
                </div>
            """, unsafe_allow_html=True)

        with col3:
            if st.button("➡️", use_container_width=True) and st.session_state.note_index < len(dates_dispo) - 1:
                st.session_state.note_index += 1

        st.markdown(f"> {selected_note['text']}")
        for path in selected_note.get("images", []):
            st.image(path, use_container_width=True)
    else:
        st.info("👉 Ajoute au moins une note pour naviguer.")

    # === Listing complet des sessions
    st.markdown("---")
    st.subheader("🧾 Listing de toutes les sessions enregistrées")

    records = []
    for d in sorted(journal.keys(), reverse=True):
        note = journal[d]
        records.append({
            "Date": d.split(" ")[0],
            "Résumé": note["text"][:120] + ("..." if len(note["text"]) > 120 else ""),
            "Nb images": len(note.get("images", [])),
            "Clé": d
        })

    df_notes = pd.DataFrame(records)

    if not df_notes.empty:
        for idx, row in df_notes.iterrows():
            with st.expander(f"📅 {row['Date']} — {row['Résumé']}"):
                st.markdown(f"### 🗒️ Note du {row['Date']}")
                st.markdown(journal[row["Clé"]]["text"])
                for path in journal[row["Clé"]].get("images", []):
                    st.image(path, use_container_width=True)
    else:
        st.info("Aucune note à afficher.")
