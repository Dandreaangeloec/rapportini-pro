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
    """Apre il worksheet Rapportini e restituisce (client, worksheet).

    Il CLIENT gspread è condiviso e messo in cache (autenticazione costosa),
    mentre il worksheet viene risolto ad ogni chiamata: condividere un oggetto
    Worksheet tra sessioni/thread può causare errori su Streamlit Cloud.
    """
    return _connetti_google_sheets_ws(get_sheet_url(), SHEET_WORKSHEET_NAME)


def _connetti_google_sheets_ws(_sheet_key, _ws_title):
    gc, sh = _apri_foglio()
    if sh is None:
        try:
            st.sidebar.info("ℹ️ Google Sheets non configurato")
        except Exception:
            pass
        return None, None
    ws = _get_ws_sicuro(sh, _ws_title)
    if ws is not None:
        # Migrazione: assicura che l'header contenga la colonna "id" (solo 1 volta)
        # FIX: stesso controllo rigoroso di scrivi_su_google_sheets per evitare
        # insert_cols ripetuti che aggiungono colonne vuote.
        try:
            riga0 = ws.row_values(1)
            riga0_clean = [str(c).strip().lower() for c in riga0]
            id_gia_presente = "id" in riga0_clean
            a1_vuoto_o_diverso = (not riga0) or riga0_clean[0] != "id"
            if a1_vuoto_o_diverso and not id_gia_presente:
                ws.insert_cols(1)
                ws.update("A1", "id")
        except Exception:
            pass  # se fallisce non è bloccante
    return gc, ws


@st.cache_resource(show_spinner=False)
def _client_google():
    """Autentica e ritorna il CLIENT gspread (riutilizzabile, sicuro da condividere)."""
    sa = get_service_account_dict()
    if sa is None:
        return None
    try:
        creds = __import__("google.oauth2.service_account", fromlist=["Credentials"]).Credentials.from_service_account_info(sa, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Google Sheets offline: {e}")
        except Exception:
            pass
        return None


@st.cache_resource(show_spinner=False)
def _spreadsheet_google():
    """Apre lo spreadsheet (una sola volta) e lo condivide."""
    gc = _client_google()
    if gc is None:
        return None
    try:
        url = get_sheet_url()
        if url is None:
            return None
        return gc.open_by_url(url)
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Google Sheets offline: {e}")
        except Exception:
            pass
        return None


def _get_ws_sicuro(sh, title):
    """Ritorna il worksheet, creandolo se non esiste (senza cache condivisa)."""
    return _get_or_create_ws(sh, title, ["id","data","cliente","cantiere","km","ore","spese","nota_spesa","note"])


def _apri_foglio():
    """Apre/ritorna la connessione Google (client, spreadsheet) o (None, None).

    La connessione (client + spreadsheet) è in cache a livello di processo con
    @st.cache_resource: crearli ad ogni rerun comportava una nuova autenticazione
    e una chiamata di rete che rallentava tutta l'app.
    """
    gc = _client_google()
    sh = _spreadsheet_google()
    if sh is None:
        return gc, None
    return gc, sh


def _apri_foglio_cached():
    """Alias retro-compatibile di _apri_foglio (usato dall'invalidazione cache)."""
    return _apri_foglio()



def _invalida_cache_google():
    """Svuota le cache della connessione e delle letture dopo una scrittura,
    così al prossimo rerun i dati vengono riletti aggiornati dal foglio."""
    try:
        _client_google.clear()
    except Exception:
        pass
    try:
        _spreadsheet_google.clear()
    except Exception:
        pass
    try:
        _leggi_valori_cached.clear()
    except Exception:
        pass


# Alias pubblico: usato da app.py dopo le scritture per forzare dati freschi.
invalida_cache_google = _invalida_cache_google


@st.cache_data(ttl=60, show_spinner=False)
def _leggi_valori_cached(ws_title, sheet_key):
    """Legge TUTTE le righe di un worksheet con cache breve (60s).

    `ws_title` serve solo a distinguere i worksheet nella chiave di cache;
    `sheet_key` è l'id del foglio per invalidare la cache se cambia il foglio.
    """
    gc, sh = _apri_foglio()
    if sh is None:
        return []
    try:
        ws = sh.worksheet(ws_title)
    except Exception:
        return []
    try:
        return ws.get_all_values()
    except Exception:
        return []


def leggi_da_google_sheets(ws):
    try:
        # Legge tutte le righe (con cache breve per non rifare la chiamata
        # di rete ad ogni rerun). Fallback diretto se la cache non è usabile.
        try:
            valori = _leggi_valori_cached(ws.title, get_sheet_url())
        except Exception:
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
        # FIX: NON generare id qui. Prima veniva generato uuid ad ogni lettura
        # per le righe legacy senza id, causando DUPLICATI a ogni modifica
        # (l'id generato non matchava mai le righe del foglio -> append nuovo).
        # L'id viene assegnato solo in scrivi_su_google_sheets() durante
        # l'adoption o la creazione.
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
        #    FIX: controllo rigoroso — inserisci SOLO se A1 è vuoto o non "id",
        #    e SOLO se "id" non è già presente in nessun'altra cella della riga 1.
        #    Prima: se riga0 era vuota o c'era spazio -> insert_cols ad ogni scrittura.
        try:
            riga0 = ws.row_values(1)
            riga0_clean = [str(c).strip().lower() for c in riga0]
            id_gia_presente = "id" in riga0_clean
            a1_vuoto_o_diverso = (not riga0) or riga0_clean[0] != "id"
            if a1_vuoto_o_diverso and not id_gia_presente:
                ws.insert_cols(1)
                ws.update("A1", "id")
        except Exception as e:
            # Non bloccante, ma log visibile in debug
            try:
                st.sidebar.caption(f"⚠️ Migrazione header id: {e}")
            except Exception:
                pass

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

        # 4. Applica le operazioni sul foglio (in BATCH: una sola chiamata API
        #    per gruppo invece di una chiamata per riga → molto più veloce)
        def _riga_per(rec):
            row_to_write = []
            for c in HEADERS:
                v = rec.get(c, "")
                if v is None:
                    v = ""
                if isinstance(v, float) and pd.isna(v):
                    v = ""
                row_to_write.append(str(v))
            return row_to_write

        # 4a. Append nuovi record (una sola chiamata append_rows)
        if da_aggiungere:
            ws.append_rows([_riga_per(rec) for rec in da_aggiungere],
                           value_input_option="USER_ENTERED")

        # 4b. Update record esistenti raggruppando le righe contigue
        #     (una chiamata per blocco invece di una per riga)
        #     FIX: calcola la lettera dell'ultima colonna da len(HEADERS)
        #     invece di hardcoded "I" (che presupponeva 9 colonne)
        def _col_letter(n):
            """Converte numero colonna 1-based in lettera (1=A, 27=AA, ...)."""
            letters = ""
            while n > 0:
                n, rem = divmod(n - 1, 26)
                letters = chr(65 + rem) + letters
            return letters

        ultima_col = _col_letter(len(HEADERS))

        if da_aggiornare:
            da_aggiornare.sort(key=lambda x: x[0])
            blocco_inizio = None
            blocco_righe = []
            blocco_fine = None

            def _flush_blocco(inizio, righe, fine):
                if not righe:
                    return
                ws.update(values=righe, range_name=f"A{inizio}:{ultima_col}{fine}")

            for row_idx, rec in da_aggiornare:
                if blocco_inizio is None:
                    blocco_inizio = row_idx
                    blocco_fine = row_idx
                    blocco_righe = [_riga_per(rec)]
                elif row_idx == blocco_fine + 1:
                    blocco_fine = row_idx
                    blocco_righe.append(_riga_per(rec))
                else:
                    _flush_blocco(blocco_inizio, blocco_righe, blocco_fine)
                    blocco_inizio = row_idx
                    blocco_fine = row_idx
                    blocco_righe = [_riga_per(rec)]
            _flush_blocco(blocco_inizio, blocco_righe, blocco_fine)

        # 4c. Elimina record rimossi esplicitamente (in ordine decrescente)
        for row_idx in sorted(da_eliminare, reverse=True):
            ws.delete_rows(row_idx)

        # 5. Invalida la cache di lettura: al prossimo rerun i dati saranno freschi
        try:
            _leggi_valori_cached.clear()
        except Exception:
            pass

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
        # Cache breve per non rifare la chiamata di rete ad ogni rerun
        try:
            valori = _leggi_valori_cached(ws.title, get_sheet_url())
        except Exception:
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
    """Sovrascrive il foglio 'Clienti' con il dict passato (in un'unica chiamata)."""
    try:
        gc, sh = _apri_foglio()
        if sh is None:
            return False
        ws = _get_or_create_ws(sh, SHEET_WORKSHEET_CLIENTI, ["nome", "prezzo_ora", "prezzo_km"])
        if ws is None:
            return False
        # Costruisce tutte le righe e le scrive in un'unica operazione
        righe = [["nome", "prezzo_ora", "prezzo_km"]]
        for nome, info in clienti_dict.items():
            righe.append([str(nome), str(info.get("prezzo_ora", 0)), str(info.get("prezzo_km", 0))])
        ws.clear()
        ws.update(values=righe, range_name="A1", value_input_option="USER_ENTERED")
        # Invalida la cache di lettura per riflettere subito le modifiche
        try:
            _leggi_valori_cached.clear()
        except Exception:
            pass
        return True
    except Exception as e:
        try:
            st.sidebar.info(f"ℹ️ Scrittura clienti offline: {e}")
        except Exception:
            pass
        return False
