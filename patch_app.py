# -*- coding: utf-8 -*-
import re
fp = r"c:/Users/dandr/OneDrive/Desktop/rapportini pro/rapportini-pro/app.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Estendi l'import per includere le nuove funzioni
old_import = 'from google_config import connetti_google_sheets, leggi_da_google_sheets, scrivi_su_google_sheets'
new_import = 'from google_config import connetti_google_sheets, leggi_da_google_sheets, scrivi_su_google_sheets, leggi_clienti_da_gsheets, scrivi_clienti_su_gsheets'
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print("OK: import esteso")
else:
    print("ERRORE: import non trovato")

# 2) Sostituisci l'inizializzazione di clienti_dict con lettura da Google Sheets
old_init = '''# --- INIZIALIZZAZIONE ANAGRAFICA CLIENTI ---
if "clienti_dict" not in st.session_state:
    st.session_state.clienti_dict = {
        "Bianchi S.r.l.": {"prezzo_ora": 45.0, "prezzo_km": 0.50},
        "Fr sangalli": {"prezzo_ora": 40.0, "prezzo_km": 0.45},
        "Rossi Costruzioni": {"prezzo_ora": 50.0, "prezzo_km": 0.60},
        "Verdi Impianti": {"prezzo_ora": 48.0, "prezzo_km": 0.55}
    }'''

new_init = '''# --- INIZIALIZZAZIONE ANAGRAFICA CLIENTI (persistita su Google Sheets) ---
_CLIENTI_DEFAULT = {
    "Bianchi S.r.l.": {"prezzo_ora": 45.0, "prezzo_km": 0.50},
    "Fr sangalli": {"prezzo_ora": 40.0, "prezzo_km": 0.45},
    "Rossi Costruzioni": {"prezzo_ora": 50.0, "prezzo_km": 0.60},
    "Verdi Impianti": {"prezzo_ora": 48.0, "prezzo_km": 0.55},
}
if "clienti_dict" not in st.session_state:
    # Prova a leggere i clienti da Google Sheets (persistenza tra sessioni)
    clienti_persisti = leggi_clienti_da_gsheets()
    if clienti_persisti:
        st.session_state.clienti_dict = clienti_persisti
    else:
        st.session_state.clienti_dict = dict(_CLIENTI_DEFAULT)
        # Salva i default su Google Sheets al primo avvio, cosi' l'utente puo' modificarli ovunque
        scrivi_clienti_su_gsheets(_CLIENTI_DEFAULT)'''

if old_init in content:
    content = content.replace(old_init, new_init, 1)
    print("OK: inizializzazione clienti con persistenza")
else:
    print("ERRORE: blocco init clienti non trovato")

# 3) Aggiungi la scrittura su Google Sheets dopo ogni aggiunta/modifica/eliminazione cliente
# Bottone "Aggiungi al Listino"
old_add = '''else:
                st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                st.success(f"Cliente '{nuovo_nome_clean}' aggiunto con successo!")
                st.rerun()'''
new_add = '''else:
                st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.success(f"Cliente '{nuovo_nome_clean}' aggiunto con successo!")
                st.rerun()'''
if old_add in content:
    content = content.replace(old_add, new_add, 1)
    print("OK: scrittura dopo aggiungi")

# Bottone "Salva modifiche" cliente
old_mod = '''st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                st.session_state.modifica_cliente = None
                st.success(f"Cliente '{nuovo_nome_clean}' aggiornato con successo!")
                st.rerun()'''
new_mod = '''st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.session_state.modifica_cliente = None
                st.success(f"Cliente '{nuovo_nome_clean}' aggiornato con successo!")
                st.rerun()'''
if old_mod in content:
    content = content.replace(old_mod, new_mod, 1)
    print("OK: scrittura dopo modifica")

# Bottone "Sì, elimina" cliente
old_del = '''if st.button("\U0001f5d1\ufe0f Sì, elimina", use_container_width=True, key="confirm_delete_cliente"):
                st.session_state.clienti_dict.pop(nome_el, None)
                st.session_state.elimina_cliente = None
                st.success(f"Cliente '{nome_el}' eliminato!")
                st.rerun()'''
new_del = '''if st.button("\U0001f5d1\ufe0f Sì, elimina", use_container_width=True, key="confirm_delete_cliente"):
                st.session_state.clienti_dict.pop(nome_el, None)
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.session_state.elimina_cliente = None
                st.success(f"Cliente '{nome_el}' eliminato!")
                st.rerun()'''
if old_del in content:
    content = content.replace(old_del, new_del, 1)
    print("OK: scrittura dopo elimina")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("File salvato")
