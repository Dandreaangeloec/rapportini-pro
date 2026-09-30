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
    ws = _get_or_create_ws(sh, SHEET_WORKSHEET_NAME, ["id","data","cliente","cantiere","km","ore","spese","nota_spesa","note"])
    if ws is not None:
        # Migrazione: assicura che l'header contenga la colonna "id"
        try:
            riga0 = ws.row_values(1)
            if not riga0 or str(riga0[0]).strip() != "id":
                # Inserisce la colonna "id" come prima colonna se manca
                ws.insert_cols(1)
                ws.update("A1", "id")
        except Exception:
            pass  # se fallisce non è bloccante
    return gc, ws


def leggi_da_google_sheets(ws):
    try:
        # Legge tutte le righe brute per evitare l'errore "duplicate headers"
        # dovuto a intestazioni vuote/duplicate nel foglio
        valori = ws.get_all_values()
        if not valori or len(valori) < 1:
            return []
        headers = [h.strip() for h in valori[0]]
        records = []
        for row in valori[1:]:
            if all(cell.strip() == "" for cell in row):
                continue  # salta righe vuote
            # Allunga la row se più corta degli headers
            while len(row) < len(headers):
                row.append("")
            record = {}
            for i, h in enumerate(headers):
                if h:  # solo header non vuoti
                    record[h] = row[i]
            if record:
                records.append(record)
        # IMPORTANTE: assegna un ID se manca (migrazione dati esistenti)
        import uuid
        for rec in records:
            if not str(rec.get("id", "")).strip():
                rec["id"] = str(uuid.uuid4())
        return records
    except Exception as e:
        try:
            st.error(f"Errore lettura: {e}")
        except Exception:
            pass
        return []


def scrivi_su_google_sheets(ws, rapportini, old_rapportini=None):
    """
    Scrivi i rapportini su Google Sheets con strategia MERGE sicura (no clear+rewrite).

    A differenza della vecchia versione che faceva ws.clear() + riscrittura
    (che causava perdita dati in caso di accessi concorrenti), questa funzione:

    1. Legge i dati ATTUALE dal foglio (per non sovrascrivere righe di altri)
    2. Assegna un campo 'id' univoco a ogni rapportino
    3. Aggiunge SOLO i record con id non ancora presente (append in fondo)
    4. Aggiorna in-place i record con id già presente
    5. Adotta (migra) i vecchi record SENZA id matchandoli per contenuto
       (data|cliente|cantiere) così non vengono duplicati e acquistano un id
    6. Elimina SOLO i record rimossi esplicitamente dall'utente
    """
    import uuid

    HEADERS = ["id", "data", "cliente", "cantiere", "km", "ore", "spese", "nota_spesa", "note"]

    try:
        # 0. Assicura che la colonna "id" esista come PRIMA colonna (A).
        #    Se il foglio è legacy (senza colonna id), la inserisce.
        try:
            riga0 = ws.row_values(1)
            if not riga0 or str(riga0[0]).strip() != "id":
                ws.insert_cols(1)
                ws.update("A1", "id")
        except Exception:
            pass  # non bloccante

        # 1. Leggi lo stato ATTUALE del foglio
        try:
            valori = ws.get_all_values()
        except Exception:
            valori = []

        sheet_rows = {}          # id -> dict di riga esistente
        sheet_row_by_index = {}  # id -> indice riga (1-based, headers=riga 1)
        legacy_rows = {}         # firma_contenuto -> (indice, dict) per righe SENZA id
        legacy_ids_by_row = {}   # indice -> firma (per tracciamento adozione)

        if valori and len(valori) > 0:
            h = [x.strip() for x in valori[0]]
            for idx, row in enumerate(valori[1:], start=2):  # riga 2 = prima dati
                if all(c.strip() == "" for c in row):
                    continue
                while len(row) < len(h):
                    row.append("")
                d = {}
                for i, hh in enumerate(h):
                    if hh:
                        d[hh] = row[i]
                rid = str(d.get("id", "")).strip()
                if rid:
                    sheet_rows[rid] = d
                    sheet_row_by_index[rid] = idx
                else:
                    # Riga legacy senza id → matchnala per contenuto
                    firma = "|".join([
                        str(d.get("data", "")).strip(),
                        str(d.get("cliente", "")).strip(),
                        str(d.get("cantiere", "")).strip()
                    ])
                    if firma:
                        legacy_rows[firma] = (idx, d)
                        legacy_ids_by_row[idx] = firma

        # 2. Prepara liste di operazioni
        da_aggiungere = []            # (dict) → append in fondo
        da_aggiornare = []            # (indice_riga, dict) → update in-place
        id_presenti_in_memoria = []
        firme_in_memoria = set()      # firme dei record in memoria (per adoption)

        for r in rapportini:
            rec = dict(r)
            rid = str(rec.get("id", "")).strip()
            firma = "|".join([
                str(rec.get("data", "")).strip(),
                str(rec.get("cliente", "")).strip(),
                str(rec.get("cantiere", "")).strip()
            ])
            if firma:
                firme_in_memoria.add(firma)

            if rid:
                id_presenti_in_memoria.append(rid)
                if rid in sheet_rows:
                    # Id già presente nel foglio → aggiorna in-place
                    da_aggiornare.append((sheet_row_by_index[rid], rec))
                elif firma and firma in legacy_rows:
                    # Id assegnato in memoria MA riga ancora legacy (colonna id
                    # vuota nel foglio, migrazione) → adotta la riga legacy
                    # riempiendola con l'id invece di duplicarla.
                    idx_legacy, _ = legacy_rows[firma]
                    da_aggiornare.append((idx_legacy, rec))
                else:
                    # Id presente ma nessuna riga legacy corrispondente → nuovo
                    da_aggiungere.append(rec)
            else:
                # Record senza id: prova ADOPTION su una riga legacy
                if firma and firma in legacy_rows:
                    idx_legacy, _ = legacy_rows[firma]
                    # Assegna un id univoco al record e aggiorna in-place
                    nuovo_id = str(uuid.uuid4())
                    rec["id"] = nuovo_id
                    r["id"] = nuovo_id          # salva in session_state
                    da_aggiornare.append((idx_legacy, rec))
                else:
                    # Nessuna riga legacy corrispondente → nuovo record
                    nuovo_id = str(uuid.uuid4())
                    rec["id"] = nuovo_id
                    r["id"] = nuovo_id          # salva in session_state
                    da_aggiungere.append(rec)

        # 3. Determina i record da ELIMINARE (solo rimozioni esplicite)
        da_eliminare = []
        if old_rapportini is not None:
            old_ids = {str(x.get("id", "")).strip() for x in old_rapportini if str(x.get("id", "")).strip()}
            nuovi_ids = set(id_presenti_in_memoria)
            for rid in old_ids:
                if rid not in nuovi_ids and rid in sheet_rows:
                    da_eliminare.append(sheet_row_by_index[rid])

        # 4. Applica le operazioni sul foglio
        # 4a. Append nuovi record (in fondo — non tocca righe esistenti)
        for rec in da_aggiungere:
            row_to_write = []
            for c in HEADERS:
                v = rec.get(c, "")
                if v is None:
                    v = ""
                if isinstance(v, float) and pd.isna(v):
                    v = ""
                row_to_write.append(str(v))
            ws.append_row(row_to_write)

        # 4b. Update record esistenti (in-place, riga per riga)
        for row_idx, rec in da_aggiornare:
            row_to_write = []
            for c in HEADERS:
                v = rec.get(c, "")
                if v is None:
                    v = ""
                if isinstance(v, float) and pd.isna(v):
                    v = ""
                row_to_write.append(str(v))
            ws.update(values=[row_to_write], range_name=f"A{row_idx}:I{row_idx}")

        # 4c. Elimina record rimossi esplicitamente (in ordine decrescente)
        for row_idx in sorted(da_eliminare, reverse=True):
            ws.delete_rows(row_idx)

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
        valori = ws.get_all_values()
        if not valori or len(valori) < 1:
            return {}
        headers = [h.strip() for h in valori[0]]
        records = []
        for row in valori[1:]:
            if all(cell.strip() == "" for cell in row):
                continue
            while len(row) < len(headers):
                row.append("")
            record = {}
            for i, h in enumerate(headers):
                if h:
                    record[h] = row[i]
            if record:
                records.append(record)
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
