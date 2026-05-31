"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Cerca credenziali e URL sempre nella stessa cartella di questo file.
Compatibile con: locale, Streamlit Cloud, GitHub.
"""
import json
import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))

POSSIBLE_CREDENTIAL_FILES = [
    "service-account.json", "credentials.json",
    "rapportini-app-497020-c89737d42a9f.json",
    "rapportini-app-497020-0c38d1b7d1b9.json",
]

SHEET_WORKSHEET_NAME = "Rapportini"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]


def _fix_private_key(sa_dict):
    """Normalizza la private_key (corregge \\n letterali se necessario)."""
    pk = sa_dict.get("private_key", "")
    if not pk:
        return sa_dict
    if "\n" in pk:          # già newline reali
        return sa_dict
    if "\\n" in pk:         # backslash+n letterali → converti
        sa_dict["private_key"] = pk.replace("\\n", "\n")
    return sa_dict


def _parse_secret_value(val):
    """Converte un valore preso da st.secrets in un dict di credenziali."""
    if val is None:
        return None
    # Caso 1: TOML ha già parsato come dict nidificato (formato nativo TOML raccomandato)
    if isinstance(val, dict):
        return _fix_private_key(dict(val))
    # Caso 2: stringa JSON
    if isinstance(val, str) and val.strip():
        try:
            return _fix_private_key(json.loads(val.strip()))
        except json.JSONDecodeError:
            return None
    return None


def get_service_account_dict():
    """Cerca credenziali: Streamlit Cloud secrets > file JSON locale."""
    # 1) Streamlit Cloud secrets (prova vari nomi di chiave)
    for key in ("google_service_account", "gcp_service_account"):
        sa = _parse_secret_value(st.secrets.get(key, None) if hasattr(st.secrets, 'get') else None)
        if sa:
            return sa

    # 2) Cartella di questo modulo
    for fname in POSSIBLE_CREDENTIAL_FILES:
        path = os.path.join(_HERE, fname)
        if os.path.exists(path):
            with open(path, "r") as f:
                return _fix_private_key(json.load(f))

    # 3) Cartella superiore
    parent = os.path.dirname(_HERE)
    for fname in POSSIBLE_CREDENTIAL_FILES:
        path = os.path.join(parent, fname)
        if os.path.exists(path):
            with open(path, "r") as f:
                return _fix_private_key(json.load(f))

    return None


def get_sheet_url():
    """Cerca URL foglio: secrets > env > file locale."""
    # 1) Chiave standalone nei secrets
    try:
        url = st.secrets.get("google_sheet_url", "")
        if url and isinstance(url, str) and url.strip():
            return url.strip()
    except Exception:
        pass

    # 2) Dentro la sezione [google_service_account] (se messo dopo nel TOML)
    try:
        gsa = st.secrets.get("google_service_account", None)
        if isinstance(gsa, dict):
            url = gsa.get("google_sheet_url", "")
            if url and isinstance(url, str) and url.strip():
                return url.strip()
    except Exception:
        pass

    # 3) Variabile d'ambiente
    url = os.environ.get("GOOGLE_SHEET_URL")
    if url:
        return url

    # 4) File locale
    for d in (_HERE, os.path.dirname(_HERE)):
        p = os.path.join(d, "sheet_url.txt")
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    return None


def connetti_google_sheets():
    """Restituisce (client, worksheet) oppure (None, None) in caso di errore."""
    try:
        sa_dict = get_service_account_dict()
        if sa_dict is None:
            st.sidebar.warning("Google Sheets: nessuna credenziale trovata")
            return None, None
        creds = Credentials.from_service_account_info(sa_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet_url = get_sheet_url()
        if sheet_url is None:
            st.sidebar.warning("Google Sheets: nessun URL foglio")
            return None, None
        sh = client.open_by_url(sheet_url)
        try:
            worksheet = sh.worksheet(SHEET_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=SHEET_WORKSHEET_NAME, rows=1000, cols=20)
            worksheet.append_row([
                "data", "cliente", "cantiere", "km", "ore", "spese",
                "nota_spesa", "note"
            ])
        return client, worksheet
    except Exception as e:
        st.sidebar.error(f"Errore connessione Google Sheets: {e}")
        return None, None


def leggi_da_google_sheets(worksheet):
    try:
        return worksheet.get_all_records()
    except Exception as e:
        st.error(f"Errore lettura dati: {e}")
        return []


def scrivi_su_google_sheets(worksheet, rapportini):
    try:
        if not rapportini:
            worksheet.clear()
            worksheet.append_row([
                "data", "cliente", "cantiere", "km", "ore", "spese",
                "nota_spesa", "note"
            ])
            return True
        df = pd.DataFrame(rapportini)
        colonne = ["data", "cliente", "cantiere", "km", "ore", "spese", "nota_spesa", "note"]
        presenti = [c for c in colonne if c in df.columns]
        if not presenti:
            return False
        df = df[presenti]
        worksheet.clear()
        worksheet.append_row(presenti)
        for _, row in df.iterrows():
            if all(pd.isna(v) or str(v).strip() == "" for v in row):
                continue
            worksheet.append_row(["" if pd.isna(row[c]) else str(row[c]) for c in presenti])
        return True
    except Exception as e:
        st.error(f"Errore scrittura su Google Sheets: {e}")
        return False