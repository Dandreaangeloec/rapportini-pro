"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Supporta:
- Streamlit Cloud Secrets (JSON intero del service account)
- File locale service-account.json
"""

import json
import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

CREDENTIALS_FILE = "service-account.json"
SHEET_WORKSHEET_NAME = "Rapportini"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_service_account_dict():
    """
    Recupera il dict del service account in 2 modi:
    1. DAI STREAMLIT CLOUD SECRETS: usa la chiave 'google_service_account_json'
       (deve contenere TUTTO il JSON del service account)
    2. DAL FILE LOCALE service-account.json
    """
    # METODO 1: Streamlit Cloud Secrets - singolo JSON
    try:
        json_str = st.secrets.get("google_service_account_json", "")
        if json_str and json_str.strip():
            sa = json.loads(json_str)
            return sa
    except Exception:
        pass

    # METODO 2: File locale
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"Errore credenziali: {e}")
    return None


def get_sheet_url():
    """Recupera l'URL del foglio: da secrets (google_sheet_url) o da file sheet_url.txt"""
    try:
        url = st.secrets.get("google_sheet_url", "")
        if url:
            return url
    except Exception:
        pass
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