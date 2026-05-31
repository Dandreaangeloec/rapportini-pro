"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Legge le credenziali dal file JSON locale o da variabili d'ambiente.
Per Streamlit Cloud: funziona leggendo il file direttamente dal repo.
"""

import json
import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# Cerca il file delle credenziali con vari nomi possibili
POSSIBLE_CREDENTIAL_FILES = [
    "service-account.json",
    "rapportini-app-497020-c89737d42a9f.json",
]

SHEET_WORKSHEET_NAME = "Rapportini"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_service_account_dict():
    """Cerca le credenziali in ordine: secrets Streamlit, poi file JSON locale."""
    # METODO 1: Streamlit Cloud secrets
    try:
        json_str = st.secrets.get("google_service_account", "")
        if json_str and json_str.strip():
            return json.loads(json_str)
    except Exception:
        pass

    # METODO 2: Vari file JSON nella cartella
    for filename in POSSIBLE_CREDENTIAL_FILES:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    return json.load(f)
            except Exception as e:
                st.sidebar.error(f"Errore leggendo {filename}: {e}")
    
    # METODO 3: Cerca nella sottocartella corrente
    for filename in POSSIBLE_CREDENTIAL_FILES:
        path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                pass

    return None


def get_sheet_url():
    """Cerca l'URL del foglio: secrets, file txt, o variabile d'ambiente."""
    # METODO 1: Streamlit Cloud secrets
    try:
        url = st.secrets.get("google_sheet_url", "")
        if url:
            return url
    except Exception:
        pass

    # METODO 2: Variabile d'ambiente
    url = os.environ.get("GOOGLE_SHEET_URL")
    if url:
        return url

    # METODO 3: File sheet_url.txt
    if os.path.exists("sheet_url.txt"):
        with open("sheet_url.txt", "r") as f:
            url = f.read().strip()
            if url:
                return url

    return None


def connetti_google_sheets():
    try:
        sa_dict = get_service_account_dict()
        if sa_dict is None:
            return None, None

        creds = Credentials.from_service_account_info(sa_dict, scopes=SCOPES)
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
    try:
        return worksheet.get_all_records()
    except Exception as e:
        st.error(f"Errore durante la lettura dei dati: {e}")
        return []


def scrivi_su_google_sheets(worksheet, rapportini):
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
            riga = ["" if pd.isna(row[col]) else str(row[col]) for col in colonne_presenti]
            worksheet.append_row(riga)

        return True
    except Exception as e:
        st.error(f"Errore durante la scrittura su Google Sheets: {e}")
        return False