"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Passi per la configurazione:
1. Vai su https://console.cloud.google.com/
2. Crea un nuovo progetto (o selezionane uno esistente)
3. Abilita Google Sheets API
4. Vai su "Credenziali" -> "Crea credenziali" -> "Service Account"
5. Assegna un nome, clicca "Crea e continua"
6. Nel ruolo, scegli "Editor" (o "Proprietario")
7. Clicca "Fine"
8. Nella lista dei service account, clicca sull'email appena creata
9. Vai su "Chiavi" -> "Aggiungi chiave" -> "Crea nuova chiave" -> JSON
10. Salva il file come "service-account.json" nella cartella del progetto
11. Apri il file JSON, copia il valore di "client_email"
12. Condividi il tuo Google Sheet con quella email (come editor)
13. Scrivi l'URL del foglio qui sotto
"""

import json
import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# Nome del file delle credenziali (da creare seguendo le istruzioni sopra)
CREDENTIALS_FILE = "service-account.json"

# Nome del foglio di lavoro all'interno del Google Sheet
# (cambialo se il tuo foglio si chiama diversamente)
SHEET_WORKSHEET_NAME = "Rapportini"

# SCOPI necessari per Google Sheets e Google Drive
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def carica_credenziali():
    """
    Carica le credenziali dal file JSON del service account.
    Restituisce un oggetto Credentials o None se il file non esiste.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        return creds
    except Exception as e:
        st.sidebar.error(f"Errore nel caricamento delle credenziali: {e}")
        return None


def get_sheet_url():
    """
    Restituisce l'URL del foglio Google da una variabile d'ambiente o da un file.
    Il file 'sheet_url.txt' deve contenere l'URL del tuo Google Sheet.
    
    Come trovare l'URL:
    - Apri il tuo Google Sheet
    - Copia l'URL dalla barra degli indirizzi del browser
    - Ha un formato simile a:
      https://docs.google.com/spreadsheets/d/1ABC123xyz...
    """
    # Prima controlla la variabile d'ambiente
    url = os.environ.get("GOOGLE_SHEET_URL")
    if url:
        return url
    
    # Poi controlla il file
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
        
        # Apre il foglio dall'URL
        sh = client.open_by_url(sheet_url)
        
        # Cerca il foglio di lavoro (worksheet) specificato
        try:
            worksheet = sh.worksheet(SHEET_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Se non esiste, crea il foglio con intestazioni
            worksheet = sh.add_worksheet(title=SHEET_WORKSHEET_NAME, rows=1000, cols=20)
            intestazioni = ["data", "cliente", "cantiere", "km", "ore", "spese", "note"]
            worksheet.append_row(intestazioni)
        
        return client, worksheet
    
    except Exception as e:
        st.sidebar.error(f"Errore di connessione a Google Sheets: {e}")
        return None, None


def leggi_da_google_sheets(worksheet):
    """
    Legge tutti i dati dal foglio Google e restituisce una lista di dizionari.
    """
    try:
        dati = worksheet.get_all_records()
        return dati
    except Exception as e:
        st.error(f"Errore durante la lettura dei dati: {e}")
        return []


def scrivi_su_google_sheets(worksheet, rapportini):
    """
    Sovrascrive tutto il foglio Google con i dati attuali dei rapportini.
    """
    try:
        # Prepara i dati come lista di liste
        if not rapportini:
            # Se non ci sono dati, resetta con solo intestazioni
            worksheet.clear()
            worksheet.append_row(["data", "cliente", "cantiere", "km", "ore", "spese", "note"])
            return True
        
        df = pd.DataFrame(rapportini)
        
        # Seleziona solo le colonne che ci interessano
        colonne = ["data", "cliente", "cantiere", "km", "ore", "spese", "note"]
        colonne_presenti = [c for c in colonne if c in df.columns]
        
        if not colonne_presenti:
            return False
        
        df = df[colonne_presenti]
        
        # Pulisci il foglio
        worksheet.clear()
        
        # Scrivi le intestazioni
        worksheet.append_row(colonne_presenti)
        
        # Scrivi i dati (solo le righe non vuote)
        for _, row in df.iterrows():
            # Salta righe completamente vuote
            if all(pd.isna(v) or str(v).strip() == "" for v in row):
                continue
            riga = []
            for col in colonne_presenti:
                val = row[col]
                if pd.isna(val):
                    riga.append("")
                else:
                    riga.append(str(val))
            worksheet.append_row(riga)
        
        return True
    
    except Exception as e:
        st.error(f"Errore durante la scrittura su Google Sheets: {e}")
        return False