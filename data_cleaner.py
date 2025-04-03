import pandas as pd
import numpy as np
import os

def parse_money(val):
    if pd.isna(val):
        return np.nan
    val = str(val).replace('(', '-').replace(')', '').replace('$', '').replace(',', '').strip()
    try:
        return float(val)
    except:
        return np.nan

def load_and_clean_csv(file):
    try:
        df = pd.read_csv(file)
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Erreur lors de la lecture du fichier CSV : {e}")
        return pd.DataFrame()

    # Suppression de colonnes inutiles
    df = df.drop(columns=["Unnamed: 19"], errors="ignore")

    # Conversion des colonnes monétaires
    monetary_columns = ["Profit", "Cum. net profit", "MAE", "MFE", "ETD", "Commission"]
    for col in monetary_columns:
        if col in df.columns:
            df[col] = df[col].apply(parse_money)

    # Conversion des dates
    df["Entry time"] = pd.to_datetime(df["Entry time"], errors="coerce")
    df["Exit time"] = pd.to_datetime(df["Exit time"], errors="coerce")

    # ID unique pour éviter les doublons
    if "Trade number" in df.columns:
        df["trade_id"] = df["Trade number"].astype(str) + "_" + df["Entry time"].astype(str)
    else:
        df["trade_id"] = df.index.astype(str) + "_" + df["Entry time"].astype(str)

    return df

def update_historical_data(df_new, historical_path):
    if os.path.exists(historical_path):
        df_hist = pd.read_csv(historical_path, parse_dates=["Entry time", "Exit time"])
        if "Trade number" in df_hist.columns:
            df_hist["trade_id"] = df_hist["Trade number"].astype(str) + "_" + df_hist["Entry time"].astype(str)
        else:
            df_hist["trade_id"] = df_hist.index.astype(str) + "_" + df_hist["Entry time"].astype(str)

        df_to_add = df_new[~df_new["trade_id"].isin(df_hist["trade_id"])]
        df_updated = pd.concat([df_hist, df_to_add], ignore_index=True).drop(columns=["trade_id"], errors="ignore")
        df_updated.to_csv(historical_path, index=False)
        return df_updated, len(df_to_add)
    else:
        df_new.drop(columns=["trade_id"], errors="ignore").to_csv(historical_path, index=False)
        return df_new.drop(columns=["trade_id"], errors="ignore"), len(df_new)
