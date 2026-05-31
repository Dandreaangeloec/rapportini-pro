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

# Directory di questo file (garantisce path assoluti ovunque venga eseguito)
_HERE = os.path.dirname(os.path.abspath(__file__))

POSSIBLE_CREDENTIAL_FILES = [
    "service-account.json",
    "credentials.json",
    "rapportini-app-497020-c89737d42a9f.json",
    "rapportini-app-497020-0c38d1b7d1b9.json",
]

SHEET_WORKSHEET_NAME = "Rapportini"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _fix_private_key(sa_dict):
    """Corregge la private_key se ha \\n letterali (problema TOML apici singoli)."""
    pk = sa_dict.get("private_key", "")
    if not pk:
        return sa_dict
    if "\n" in pk:          # già veri newline
        return sa_dict
    if "\\n" in pk:         # backslash+n letterali -> converti
        sa_dict["private_key"] = pk.replace("\\n", "\n")
    return sa_dict


def _try_parse_secret(key):
    """Prova a estrarre un dizionario da st.secrets[key] in qualsiasi formato."""
    try:
        val = st.secrets.get(key)
    except Exception:
        return None

    if val is None or (isinstance(val, str) and not val.strip()):
        return None

    # Caso 1: TOML ha parsato come dict nidificato
    if isinstance(val, dict):
        return _fix_private_key(dict(val))

    # Caso 2: È una stringa JSON
    if isinstance(val, str):
        raw = val.strip()
        # Prova a fare il parsing come JSON
        return _fix_private_key(json.loads(raw))

    return None


def get_service_account_dict():
    """Cerca credenziali: Streamlit secrets > file JSON locale."""
    # 1) Streamlit Cloud secrets
    sa = (
        _try_parse_secret("google_service_account")
        or _try_parse_secret("gcp_service_account")
        or _try_parse_secret("GOOGLE_SERVICE_ACCOUNT")
    )
    if sa:
        return sa

    # 2) File JSON nella cartella di questo modulo
    for fname in POSSIBLE_CREDENTIAL_FILES:
        path = os.path.join(_HERE, fname)
        if os.path.exists(path):
            with open(path, "r") as f:
                return _fix_private_key(json.load(f))

    # 3) Cerca anche nella cartella superiore
    parent = os.path.dirname(_HERE)
    for fname in POSSIBLE_CREDENTIAL_FILES:
        path = os.path.join(parent, fname)
        if os.path.exists(path):
            with open(path, "r") as f:
                return _fix_private_key(json.load(f))

    return None


def get_sheet_url():
    """Cerca URL foglio: Streamlit secrets > env > file locale."""
    # 1) Streamlit Cloud secrets
    try:
        url = st.secrets.get("google_sheet_url", "")
        if url and isinstance(url, str) and url.strip():
            return url.strip()
    except Exception:
        pass

    # 2) Variabile d'ambiente
    url = os.environ.get("GOOGLE_SHEET_URL")
    if url:
        return url

    # 3) File nella stessa cartella di questo modulo
    path = os.path.join(_HERE, "sheet_url.txt")
    if os.path.exists(path):
        with open(path, "r") as f:
            url = f.read().strip()
            if url:
                return url

    # 4) File nella cartella superiore
    parent = os.path.dirname(_HERE)
    path = os.path.join(parent, "sheet_url.txt")
    if os.path.exists(path):
        with open(path, "r") as f:
            url = f.read().strip()
            if url:
                return url

    return None


def connetti_google_sheets():
    """Restituisce (client, worksheet) oppure (None, None) in caso di errore."""
    try:
        sa_dict = get_service_account_dict()
        if sa_dict is None:
            # Diagnostica: mostra se i secrets esistono
            try:
                keys = list(st.secrets.keys()) if hasattr(st.secrets, "keys") else "N/A"
                st.sidebar.warning(f"DEBUG: Nessuna credenziale. Secrets keys: {keys}")
            except Exception:
                st.sidebar.warning("DEBUG: Nessuna credenziale. st.secrets non accessibile.")
            return None, None

        creds = Credentials.from_service_account_info(sa_dict, scopes=SCOPES)
        client = gspread.authorize(creds)

        sheet_url = get_sheet_url()
        if sheet_url is None:
            st.sidebar.warning("DEBUG: Nessun sheet_url da secrets/env/file")
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