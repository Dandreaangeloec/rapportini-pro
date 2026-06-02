"""
Modulo di configurazione per Google Sheets via gspread
======================================================
Cerca credenziali e URL: file JSON locale > secrets.toml > st.secrets.
"""
import json, os, gspread, pandas as pd, streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
SHEET_WORKSHEET_NAME = "Rapportini"
SHEET_WORKSHEET_CLIENTI = "Clienti"  # <-- NUOVO
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# URL del foglio Google Sheets (letto da sheet_url.txt o hardcoded per Streamlit Cloud)
_FALLBACK_SHEET_URL = "https://docs.google.com/spreadsheets/d/1cbeerrhYgMk8bu0T9ByyYvvYJ5I5BJ7jFnblePmwe2E/edit"


def _fix_private_key(sa_dict):
    """Normalizza la private_key senza alterarla troppo."""
    pk = sa_dict.get("private_key", "")
    if not pk:
        return sa_dict
    pk = pk.lstrip()
    if "\\n" in pk and "\n" not in pk:
        pk = pk.replace("\\n", "\n")
    if not pk.endswith("\n"):
        pk += "\n"
    sa_dict["private_key"] = pk
    return sa_dict


def _read_service_account_from_dict(d):
    if not isinstance(d, dict):
        return None
    needed = ["type", "project_id", "private_key", "client_email"]
    if any(k not in d for k in needed):
        return None
    return _fix_private_key({k: d[k] for k in d})


def get_service_account_dict():
    try:
        if hasattr(st, "secrets"):
            b64 = st.secrets.get("google_service_account_b64", "")
            if b64 and isinstance(b64, str) and b64.strip():
                import base64
                try:
                    return _fix_private_key(json.loads(base64.b64decode(b64.strip())))
                except Exception:
                    pass
            for key in ("google_service_account", "gcp_service_account"):
                val = st.secrets.get(key, None)
                sa = _read_service_account_from_dict(val)
                if sa:
                    return sa
            raw = st.secrets.get("google_service_account", "")
            if isinstance(raw, str) and raw.strip():
                try:
                    return _fix_private_key(json.loads(raw))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

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
    for d in (_HERE, os.path.dirname(_HERE)):
        p = os.path.join(d, "sheet_url.txt")
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    return _FALLBACK_SHEET_URL


def _apri_foglio():
    """Apre il foglio Google (gc, sh) o ritorna (None, None)."""
    sa = get_service_account_dict()
    if sa is None:
        return None, None
    try:
        creds = __import__("google.oauth2.service_account", fromlist=["Credentials"]).Credentials.from_service_account_info(sa, scopes=SCOPES)
        gc = gspread.authorize(creds)
        url = get_sheet_url()
        if url is None:
            return gc, None
        sh = gc.open_by_url(url)
        return gc, sh
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Google Sheets offline: {e}")
        except Exception:
            pass
        return None, None


def _get_or_create_ws(sh, title, header):
    """Restituisce il worksheet col nome indicato, creandolo se non esiste."""
    if sh is None:
        return None
    try:
        try:
            return sh.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=1000, cols=20)
            ws.append_row(header)
            return ws
    except Exception:
        return None


def connetti_google_sheets():
    """Apre il worksheet Rapportini (per compatibilita con app.py)."""
    gc, sh = _apri_foglio()
    if sh is None:
        try:
            st.sidebar.info("ℹ️ Google Sheets non configurato")
        except Exception:
            pass
        return None, None
    ws = _get_or_create_ws(sh, SHEET_WORKSHEET_NAME, ["data","cliente","cantiere","km","ore","spese","nota_spesa","note"])
    return gc, ws


def leggi_da_google_sheets(ws):
    try:
        return ws.get_all_records()
    except Exception as e:
        try:
            st.error(f"Errore lettura: {e}")
        except Exception:
            pass
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
        try:
            st.error(f"Errore scrittura: {e}")
        except Exception:
            pass
        return False


# ============================================================
# NUOVE FUNZIONI per la gestione persistente dei clienti
# ============================================================
def leggi_clienti_da_gsheets():
    """Ritorna un dict {nome: {'prezzo_ora': float, 'prezzo_km': float}} letto da Google Sheets.
    Ritorna {} se Google Sheets non è disponibile o il worksheet non esiste ancora."""
    try:
        gc, sh = _apri_foglio()
        if sh is None:
            return {}
        ws = _get_or_create_ws(sh, SHEET_WORKSHEET_CLIENTI, ["nome", "prezzo_ora", "prezzo_km"])
        if ws is None:
            return {}
        records = ws.get_all_records()
        result = {}
        for r in records:
            nome = str(r.get("nome", "")).strip()
            if not nome:
                continue
            try:
                p_ora = float(r.get("prezzo_ora", 0) or 0)
            except (ValueError, TypeError):
                p_ora = 0.0
            try:
                p_km = float(r.get("prezzo_km", 0) or 0)
            except (ValueError, TypeError):
                p_km = 0.0
            result[nome] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
        return result
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Lettura clienti offline: {e}")
        except Exception:
            pass
        return {}


def scrivi_clienti_su_gsheets(clienti_dict):
    """Sovrascrive il foglio 'Clienti' con il dict passato."""
    try:
        gc, sh = _apri_foglio()
        if sh is None:
            return False
        ws = _get_or_create_ws(sh, SHEET_WORKSHEET_CLIENTI, ["nome", "prezzo_ora", "prezzo_km"])
        if ws is None:
            return False
        ws.clear()
        ws.append_row(["nome", "prezzo_ora", "prezzo_km"])
        for nome, info in clienti_dict.items():
            ws.append_row([str(nome), str(info.get("prezzo_ora", 0)), str(info.get("prezzo_km", 0))])
        return True
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Scrittura clienti offline: {e}")
        except Exception:
            pass
        return False
