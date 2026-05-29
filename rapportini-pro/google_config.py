"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Supporta sia file locale (service-account.json) che Streamlit Cloud Secrets.
"""

import json
import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# Nome del file delle credenziali locale
CREDENTIALS_FILE = "service-account.json"

# Nome del foglio di lavoro all'interno del Google Sheet
SHEET_WORKSHEET_NAME = "Rapportini"

# SCOPI necessari per Google Sheets e Google Drive
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def carica_credenziali():
    """
    Carica le credenziali in 2 modi:
    1. Streamlit secrets (per Streamlit Cloud) - usa gsheets/service_account
    2. File service-account.json (locale)
    """
    # METODO 1: Streamlit secrets (Cloud)
    try:
        gsheets_secrets = st.secrets.get("connections", {}).get("gsheets", {})
        sa = gsheets_secrets.get("service_account", {})
        if sa and isinstance(sa, dict) and sa.get("private_key"):
            # Se la private_key ha \n letterali, li convertiamo in newline reali
            private_key = sa["private_key"]
            if "\\n" in private_key and not private_key.startswith("-----BEGIN"):
                private_key = private_key.replace("\\n", "\n")
                sa["private_key"] = private_key
            creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
            return creds
    except Exception:
        pass

    # METODO 2: File JSON locale
    if os.path.exists(CREDENTIALS_FILE):
        try:
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
            return creds
        except Exception as e:
            st.sidebar.error(f"Errore credenziali: {e}")
    return None


def get_sheet_url():
    """
    Restituisce l'URL del foglio Google in 2 modi:
    1. Streamlit secrets
    2. File sheet_url.txt
    """
    # METODO 1: Streamlit secrets
    try:
        url = st.secrets.get("connections", {}).get("gsheets", {}).get("spreadsheet", "")
        if url:
            return url
    except Exception:
        pass

    # METODO 2: File locale
    if os.path.exists("sheet_url.txt"):
        with open("sheet_url.txt", "r") as f:
            url = f.read().strip()
            if url:
                return url

    return None


def connetti_google_sheets():
    """
    Tenta di connettersi a Google Sheets usando gspread.
    Restituisce (client, foglio) se connesso, altrimenti (None, None).
    """
    try:
        creds = carica_credenziali()
        if creds is None:
            return None, None

        client = gspread.authorize(creds)

        sheet_url = get_sheet_url()
        if sheet_url is None:
            return None, None

        sh = client.open_by_url(sheet_url)

        try:
            worksheet = sh.worksheet(SHEET_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=SHEET_WORKSHEET_NAME, rows=1000, cols=20)
            intestazioni = ["data", "cliente", "cantiere", "km", "ore", "spese", "nota_spesa", "note"]
            worksheet.append_row(intestazioni)

        return client, worksheet

    except Exception as e:
        st.sidebar.error(f"Errore di connessione a Google Sheets: {e}")
        return None, None


def leggi_da_google_sheets(worksheet):
    """Legge tutti i dati dal foglio Google e restituisce una lista di dizionari."""
    try:
        return worksheet.get_all_records()
    except Exception as e:
        st.error(f"Errore durante la lettura dei dati: {e}")
        return []


def scrivi_su_google_sheets(worksheet, rapportini):
    """Sovrascrive tutto il foglio Google con i dati attuali dei rapportini."""
    try:
        if not rapportini:
            worksheet.clear()
            worksheet.append_row(["data", "cliente", "cantiere", "km", "ore", "spese", "nota_spesa", "note"])
            return True

        df = pd.DataFrame(rapportini)
        colonne = ["data", "cliente", "cantiere", "km", "ore", "spese", "nota_spesa", "note"]
        colonne_presenti = [c for c in colonne if c in df.columns]

        if not colonne_presenti:
            return False

        df = df[colonne_presenti]
        worksheet.clear()
        worksheet.append_row(colonne_presenti)

        for _, row in df.iterrows():
            if all(pd.isna(v) or str(v).strip() == "" for v in row):
                continue
            riga = []
            for col in colonne_presenti:
                val = row[col]
                riga.append("" if pd.isna(val) else str(val))
            worksheet.append_row(riga)

        return True

    except Exception as e:
        st.error(f"Errore durante la scrittura su Google Sheets: {e}")
        return False