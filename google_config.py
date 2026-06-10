"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Cerca credenziali e URL: file JSON locale > secrets.toml > st.secrets.
"""
import json, os, gspread, pandas as pd, streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
SHEET_WORKSHEET_NAME = "Rapportini"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# URL del foglio Google Sheets (letto da sheet_url.txt o hardcoded per Streamlit Cloud)
_FALLBACK_SHEET_URL = "https://docs.google.com/spreadsheets/d/1cbeerrhYgMk8bu0T9ByyYvvYJ5I5BJ7jFnblePmwe2E/edit"


def _fix_private_key(sa_dict):
    """Normalizza la private_key senza alterarla troppo."""
    pk = sa_dict.get("private_key", "")
    if not pk:
        return sa_dict
    # Rimuovi SOLO spazi iniziali/finali, non newline finali (PEM li richiede)
    pk = pk.lstrip()
    # Converti \n letterali in veri newline
    if "\\n" in pk and "\n" not in pk:
        pk = pk.replace("\\n", "\n")
    # Assicura che finisca con \n (PEM standard)
    if not pk.endswith("\n"):
        pk += "\n"
    sa_dict["private_key"] = pk
    return sa_dict


def _read_service_account_from_dict(d):
    """Estrae credenziali da un dizionario stile TOML section o JSON."""
    if not isinstance(d, dict):
        return None
    needed = ["type", "project_id", "private_key", "client_email"]
    if any(k not in d for k in needed):
        return None
    return _fix_private_key({k: d[k] for k in d})


def get_service_account_dict():
    """Cerca credenziali: st.secrets > file locale > secrets.toml."""
    # st.secrets (online — Streamlit Cloud) — PRIORITA' MASSIMA
    try:
        if hasattr(st, "secrets"):
            # Base64 (il più robusto)
            b64 = st.secrets.get("google_service_account_b64", "")
            if b64 and isinstance(b64, str) and b64.strip():
                import base64
                try:
                    return _fix_private_key(json.loads(base64.b64decode(b64.strip())))
                except Exception:
                    pass
            # Dict TOML nativo
            for key in ("google_service_account", "gcp_service_account"):
                val = st.secrets.get(key, None)
                sa = _read_service_account_from_dict(val)
                if sa:
                    return sa
            # Stringa JSON
            raw = st.secrets.get("google_service_account", "")
            if isinstance(raw, str) and raw.strip():
                try:
                    return _fix_private_key(json.loads(raw))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # secrets.toml locale (fallback)
    for secrets_path in [
        os.path.join(_HERE, "secrets.toml"),
        os.path.join(os.path.dirname(_HERE), "secrets.toml"),
    ]:
        if os.path.exists(secrets_path):
            try:
                import tomllib
                with open(secrets_path, "rb") as f:
                    data = tomllib.load(f)
                b64 = data.get("google_service_account_b64", "")
                if b64 and isinstance(b64, str) and b64.strip():
                    import base64
                    return _fix_private_key(json.loads(base64.b64decode(b64.strip())))
                sa = _read_service_account_from_dict(data.get("google_service_account", {}))
                if sa:
                    return sa
            except Exception:
                pass

    return None


def get_sheet_url():
    """Cerca URL foglio."""
    # 1) st.secrets
    try:
        if hasattr(st, "secrets"):
            url = st.secrets.get("google_sheet_url", "")
            if url and isinstance(url, str) and url.strip():
                return url.strip()
            gsa = st.secrets.get("google_service_account", None)
            if isinstance(gsa, dict):
                url = gsa.get("google_sheet_url", "")
                if url and isinstance(url, str) and url.strip():
                    return url.strip()
    except Exception:
        pass
    # 2) File sheet_url.txt
    for d in (_HERE, os.path.dirname(_HERE)):
        p = os.path.join(d, "sheet_url.txt")
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    # 3) Fallback hardcoded (per Streamlit Cloud)
    return _FALLBACK_SHEET_URL


def connetti_google_sheets():
    try:
        sa = get_service_account_dict()
        if sa is None:
            st.sidebar.info("ℹ️ Google Sheets non configurato")
            return None, None
        
        creds = __import__("google.oauth2.service_account", fromlist=["Credentials"]).Credentials.from_service_account_info(sa, scopes=SCOPES)
        gc = gspread.authorize(creds)
        url = get_sheet_url()
        if url is None:
            st.sidebar.info("ℹ️ Google Sheets: URL foglio non trovato")
            return None, None
        sh = gc.open_by_url(url)
        try:
            ws = sh.worksheet(SHEET_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_WORKSHEET_NAME, rows=1000, cols=20)
            ws.append_row(["data","cliente","cantiere","km","ore","spese","nota_spesa","note"])
        return gc, ws
    except Exception as e:
        st.sidebar.info(f"ℹ️ Google Sheets offline: {e}")
        return None, None


def leggi_da_google_sheets(ws):
    try:
        return ws.get_all_records()
    except Exception as e:
        st.error(f"Errore lettura: {e}")
        return []


def scrivi_su_google_sheets(ws, rapportini):
    try:
        if not rapportini:
            ws.clear()
            ws.append_row(["data","cliente","cantiere","km","ore","spese","nota_spesa","note"])
            return True
        df = pd.DataFrame(rapportini)
        cols = ["data","cliente","cantiere","km","ore","spese","nota_spesa","note"]
        pres = [c for c in cols if c in df.columns]
        if not pres:
            return False
        df = df[pres]
        ws.clear()
        ws.append_row(pres)
        for _, row in df.iterrows():
            if all(pd.isna(v) or str(v).strip()=="" for v in row):
                continue
            ws.append_row(["" if pd.isna(row[c]) else str(row[c]) for c in pres])
        return True
    except Exception as e:
        st.error(f"Errore scrittura: {e}")
        return False