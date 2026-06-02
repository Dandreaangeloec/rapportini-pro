import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
import io
import os
import base64
from google_config import connetti_google_sheets, leggi_da_google_sheets, scrivi_su_google_sheets, leggi_clienti_da_gsheets, scrivi_clienti_su_gsheets

# Prova a caricare FPDF in modo robusto
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Directory di questo file (percorsi assoluti)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Rapportini Pro - D'Andrea Angelo E.C.", page_icon="📋", layout="centered")

# --- META TAG PWA (per installazione come app su smartphone) ---
st.markdown('''
<link rel="manifest" href="./static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Rapportini Pro">
<meta name="theme-color" content="#4f8bf9">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="apple-touch-icon" href="./static/logo-192.png">
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('./static/sw.js').then(function(reg) {
      console.log('SW OK:', reg.scope);
    }).catch(function(err) {
      console.warn('SW err:', err);
    });
  });
}
</script>
''', unsafe_allow_html=True)


# --- SCHERMATA DI LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.markdown("""
        <style>
        .login-box {
            background-color: rgba(128, 128, 128, 0.1);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 Accesso Riservato")
    st.subheader("D'Andrea Angelo E.C. - Gestione Rapportini")
    
    with st.container():
        password = st.text_input("Inserisci la password di sblocco:", type="password")
        if st.button("Accedi all'applicazione", use_container_width=True):
            if password == "Angelo2026!": 
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password errata! Accesso negato.")
    st.stop()

# --- CARICAMENTO LOGO SFONDO ---
def get_base64_img(img_path):
    # Cerca prima nella directory dell'app, poi nella root
    for d in [img_path, os.path.join(_APP_DIR, img_path), os.path.join(os.path.dirname(_APP_DIR), img_path)]:
        if os.path.exists(d):
            with open(d, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

# Cerca lo sfondo
file_sfondo = "sfondo.jpeg"
sfondo_base64 = get_base64_img(file_sfondo)
# Se non trovato, prova Image.jpeg
if not sfondo_base64:
    sfondo_base64 = get_base64_img("Image.jpeg")

# --- CSS GRAFICA E SFONDO ---
css_code = """
    <style>
    div.stButton > button:first-child {
        background-color: #4f8bf9;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .card {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.15);
        margin-bottom: 10px;
        color: var(--text-color);
    }
    .stat-val { font-size: 22px; font-weight: bold; color: var(--text-color); }
    .stat-lbl { font-size: 12px; color: var(--text-color); opacity: 0.7; }
    </style>
"""

if sfondo_base64:
    css_code = css_code.replace("</style>", f"""
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url('data:image/jpeg;base64,{sfondo_base64}');
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.05;
        z-index: -1;
        pointer-events: none;
    }}
    </style>
    """)

st.markdown(css_code, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ANAGRAFICA CLIENTI (persistita su Google Sheets) ---
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
        scrivi_clienti_su_gsheets(_CLIENTI_DEFAULT)

# --- INIZIALIZZAZIONE RAPPORTINI ---
if "rapportini" not in st.session_state:
    st.session_state.rapportini = []

# --- CONNESSIONE AL DATABASE (GOOGLE SHEETS) ---
conn_disponibile = False
gclient = None
gworksheet = None
try:
    gclient, gworksheet = connetti_google_sheets()
    if gworksheet is not None:
        dati_letti = leggi_da_google_sheets(gworksheet)
        if dati_letti and len(dati_letti) > 0:
            # Carica solo se session_state è vuoto (primo avvio)
            if len(st.session_state.rapportini) == 0:
                st.session_state.rapportini = dati_letti
        conn_disponibile = True
    else:
        raise Exception("Connessione non stabilita")
except Exception:
    if "rapportini" not in st.session_state or len(st.session_state.rapportini) == 0:
        st.session_state.rapportini = [
            {
                "cliente": "Rossi Costruzioni",
                "cantiere": "Cantiere Via Roma 12",
                "data": "2026-05-16",
                "km": 45,
                "ore": 7.5,
                "spese": 10.0,
                "note": "Configura Google Sheets per salvare i dati reali."
            }
        ]

# --- STATI PER MODIFICA/ELIMINAZIONE ---
if "modifica_idx" not in st.session_state:
    st.session_state.modifica_idx = None
if "elimina_idx" not in st.session_state:
    st.session_state.elimina_idx = None

# --- MODALE ELIMINAZIONE ---
if st.session_state.elimina_idx is not None:
    idx = st.session_state.elimina_idx
    r = st.session_state.rapportini[idx]
    st.error(f"⚠️ Confermi di voler eliminare il rapportino di **{r.get('cliente','?')}** del **{r.get('data','?')}**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Sì, elimina", use_container_width=True, key="confirm_delete"):
            st.session_state.rapportini.pop(idx)
            if conn_disponibile and gworksheet is not None:
                scrivi_su_google_sheets(gworksheet, st.session_state.rapportini)
            st.session_state.elimina_idx = None
            st.success("Rapportino eliminato!")
            st.rerun()
    with col2:
        if st.button("❌ Annulla", use_container_width=True, key="cancel_delete"):
            st.session_state.elimina_idx = None
            st.rerun()
    st.markdown("---")

# --- MODALE MODIFICA ---
if st.session_state.modifica_idx is not None:
    idx = st.session_state.modifica_idx
    r = st.session_state.rapportini[idx]
    st.subheader(f"✏️ Modifica rapportino #{idx+1} - {r.get('cliente','?')}")
    with st.form("form_modifica"):
        cliente = st.text_input("Cliente", value=r.get("cliente",""))
        cantiere = st.text_input("Cantiere", value=r.get("cantiere",""))
        data = st.date_input("Data", value=datetime.strptime(r.get("data","2026-01-01"), "%Y-%m-%d") if r.get("data") else datetime.now())
        km = st.number_input("Km", min_value=0, value=int(r.get("km",0)))
        ore = st.number_input("Ore", min_value=0.0, value=float(r.get("ore",0.0)), step=0.5)
        spese = st.number_input("Spese (€)", min_value=0.0, value=float(r.get("spese",0.0)), step=0.5)
        nota_spesa = st.text_input("Nota spesa", value=r.get("nota_spesa",""))
        note = st.text_area("Note", value=r.get("note",""))
        col_s, col_c = st.columns(2)
        with col_s:
            salva_mod = st.form_submit_button("💾 Salva modifiche", use_container_width=True)
        with col_c:
            annulla_mod = st.form_submit_button("❌ Annulla", use_container_width=True)
    
    if salva_mod:
        st.session_state.rapportini[idx] = {
            "cliente": cliente, "cantiere": cantiere, "data": str(data),
            "km": int(km), "ore": float(ore), "spese": float(spese),
            "nota_spesa": nota_spesa, "note": note
        }
        if conn_disponibile and gworksheet is not None:
            scrivi_su_google_sheets(gworksheet, st.session_state.rapportini)
        st.session_state.modifica_idx = None
        st.success("Rapportino modificato!")
        st.rerun()
    if annulla_mod:
        st.session_state.modifica_idx = None
        st.rerun()
    st.markdown("---")

# Inizializzazione stati per i checkbox mutualmente esclusivi
if "chk_iva" not in st.session_state:
    st.session_state.chk_iva = False
if "chk_rev" not in st.session_state:
    st.session_state.chk_rev = False

MESI_DICT = {
    "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
    "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
    "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
}

def calcola_totale_rapportino(r):
    cli_info = st.session_state.clienti_dict.get(r["cliente"], {"prezzo_ora": 0, "prezzo_km": 0})
    try:
        ore = float(r["ore"]) if str(r["ore"]) != "nan" else 0.0
        km = int(float(r["km"])) if str(r["km"]) != "nan" else 0
        spese = float(r["spese"]) if str(r["spese"]) != "nan" else 0.0
    except (ValueError, TypeError):
        ore, km, spese = 0.0, 0, 0.0
    return (ore * cli_info["prezzo_ora"]) + (km * cli_info["prezzo_km"]) + spese

def formatta_data(data_str):
    """Converte data da formato ISO (YYYY-MM-DD) a formato italiano (dd/mm/YYYY)."""
    if not data_str or str(data_str) == "nan" or data_str == "-":
        return "-"
    try:
        return datetime.strptime(str(data_str).strip(), "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(data_str)

def clean_txt(text):
    if not text or str(text) == "nan": return ""
    return str(text).replace("€", "\x80").encode('latin-1', 'replace').decode('latin-1')

# Esclusione reciproca dinamica dei checkbox
def chiudi_altro_flag(flag_modificato):
    if flag_modificato == "iva":
        if st.session_state.chk_iva:
            st.session_state.chk_rev = False
    elif flag_modificato == "reverse":
        if st.session_state.chk_rev:
            st.session_state.chk_iva = False

# Ricerca automatica del logo
def trova_percorso_logo():
    for nome in ["Image1.jpg", "LOGO.jpg", "logo.jpeg", "LOGO.JPEG"]:
        for d in [".", _APP_DIR, os.path.dirname(_APP_DIR)]:
            p = os.path.join(d, nome)
            if os.path.exists(p):
                return p
    return None

# --- FUNZIONI GENERAZIONE PDF (definite qui per evitare NameError) ---
def genera_pdf(dati, mese_sel, cliente_sel, imponibile, flag_iva, perc_iva, flag_reverse):
    pdf = FPDF()
    pdf.add_page()
    logo_path = trova_percorso_logo()
    if logo_path:
        pdf.image(logo_path, x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13); pdf.set_text_color(15, 23, 42)
    titolo_report = f"REPORT ATTIVITA - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo_report += f" ({cliente_sel.upper()})"
    pdf.cell(190, 10, txt=clean_txt(titolo_report), ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 9); pdf.set_fill_color(241, 245, 249)
    headers = [("Data", 22), ("Cliente", 38), ("Cantiere", 35), ("Ore", 14), ("Tar. Ora", 18), ("Km", 12), ("Tar. Km", 18), ("Spese", 15), ("Totale", 18)]
    for h, w in headers: pdf.cell(w, 8, h, 1, 0, "C", True)
    pdf.ln(8); pdf.set_font("Arial", "", 8)
    for r in dati:
        pdf.cell(22, 8, clean_txt(r["Data"]), 1, 0, "C")
        pdf.cell(38, 8, clean_txt(r["Cliente"])[:22], 1, 0, "L")
        pdf.cell(35, 8, clean_txt(r["Cantiere"])[:20], 1, 0, "L")
        pdf.cell(14, 8, clean_txt(r["Ore"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/h"]), 1, 0, "C")
        pdf.cell(12, 8, clean_txt(r["Km"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/Km"]), 1, 0, "C")
        pdf.cell(15, 8, clean_txt(r["Spese Extra"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Totale Lordo"]), 1, 1, "R")
    pdf.ln(4); pdf.set_font("Arial", "", 10); pdf.cell(125, 7, "", 0, 0)
    pdf.cell(35, 7, clean_txt("Totale Imponibile:"), 0, 0, "R")
    pdf.cell(30, 7, clean_txt("\x80 " + f"{imponibile:,.2f}"), 1, 1, "R")
    calcolo_iva = 0.0
    if flag_reverse:
        pdf.cell(125, 7, "", 0, 0); pdf.set_font("Arial", "I", 9)
        pdf.cell(65, 7, clean_txt("Regime esenzione: Reverse Charge"), 0, 1, "R"); pdf.set_font("Arial", "", 10)
    elif flag_iva:
        calcolo_iva = imponibile * (perc_iva / 100)
        pdf.cell(125, 7, "", 0, 0); pdf.cell(35, 7, clean_txt(f"IVA ({perc_iva}%):"), 0, 0, "R")
        pdf.cell(30, 7, clean_txt("\x80 " + f"{calcolo_iva:,.2f}"), 1, 1, "R")
    totale_generale = imponibile + calcolo_iva
    pdf.ln(2); pdf.set_font("Arial", "B", 11); pdf.set_fill_color(224, 242, 254)
    pdf.cell(125, 9, "", 0, 0); pdf.cell(35, 9, clean_txt("TOTALE DOVUTO:"), 0, 0, "R")
    pdf.cell(30, 9, clean_txt("\x80 " + f"{totale_generale:,.2f}"), 1, 1, "C", True)
    return bytes(pdf.output())

def genera_pdf_note(rapportini_filtrati, mese_sel, cliente_sel):
    pdf = FPDF()
    pdf.add_page()
    logo_path = trova_percorso_logo()
    if logo_path:
        pdf.image(logo_path, x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14); pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9); pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13); pdf.set_text_color(15, 23, 42)
    titolo = f"REGISTRO NOTE E DESCRIZIONI INTERVENTI - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo += " (CLIENTE: " + cliente_sel.upper() + ")"
    pdf.multi_cell(190, 6, txt=clean_txt(titolo), align="L")
    pdf.set_draw_color(148, 163, 184); pdf.line(10, pdf.get_y() + 4, 200, pdf.get_y() + 4); pdf.ln(8)
    pdf.set_font("Arial", "", 10)
    for r in rapportini_filtrati:
        pdf.set_font("Arial", "B", 10); pdf.set_text_color(30, 41, 59); pdf.set_fill_color(241, 245, 249)
        info_blocco = " DATA: " + formatta_data(r["data"]) + "   |   CLIENTE: " + r["cliente"] + "   |   CANTIERE: " + r["cantiere"]
        pdf.cell(190, 7, txt=clean_txt(info_blocco), border=1, ln=True, fill=True)
        pdf.set_font("Arial", "", 10); pdf.set_text_color(51, 65, 85); pdf.ln(2)
        testo_nota = r["note"].strip() if "note" in r and r["note"] and str(r["note"]).strip() != "nan" else "Nessuna nota registrata."
        pdf.multi_cell(190, 5, txt=clean_txt("Note: " + testo_nota), border=0)
        pdf.ln(4); pdf.set_draw_color(226, 232, 240); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(4)
    return bytes(pdf.output())

# --- SIDEBAR (sempre visibile) ---
# --- BANNER INSTALLA APP (PWA) ---
st.sidebar.title("📋 Rapportini")

# Logo e azienda nella sidebar
logo_sidebar = trova_percorso_logo()
if logo_sidebar:
    b64_logo = get_base64_img(logo_sidebar)
    if b64_logo:
        st.sidebar.markdown(
            f'<div style="text-align:center; margin-bottom:10px;">'
            f'<img src="data:image/jpeg;base64,{b64_logo}" style="width:120px;border-radius:8px;">'
            f'</div>',
            unsafe_allow_html=True
        )

menu = st.sidebar.radio("Navigazione", ["Rapportini Aziendali", "Nuovo Rapportino", "Report Mensili e Clienti", "Clienti"])

# --- AUTO-CHIUSURA SIDEBAR DOPO SELEZIONE MENU (mobile) ---
# Inietta CSS e JS permanentemente per chiudere la sidebar su mobile dopo selezione
st.markdown("""
<style>
/* Nasconde la sidebar su mobile quando ha la classe sidebar-closed */
@media (max-width: 768px) {
    body.sidebar-closed section[data-testid="stSidebar"],
    body.sidebar-closed [data-testid="stSidebar"] {
        transform: translateX(-100%) !important;
        display: none !important;
        visibility: hidden !important;
    }
}
</style>
<script>
(function(){
    // Osserva i cambiamenti del menu nella sidebar
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'characterData') {
                // Controlla se un radio button è stato selezionato
                var radios = document.querySelectorAll('input[type="radio"]');
                radios.forEach(function(radio) {
                    if (radio.checked) {
                        // Aggiungi la classe al body per nascondere la sidebar
                        document.body.classList.add('sidebar-closed');
                        // Rimuovi la classe dopo 2 secondi per permettere di riaprirla
                        setTimeout(function() {
                            document.body.classList.remove('sidebar-closed');
                        }, 2000);
                    }
                });
            }
        });
    });
    
    // Osserva il documento per cambiamenti
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
    
    // Fallback: chiudi la sidebar dopo 1 secondo dal caricamento della pagina
    setTimeout(function() {
        var radios = document.querySelectorAll('input[type="radio"]');
        var anyChecked = false;
        radios.forEach(function(radio) {
            if (radio.checked) anyChecked = true;
        });
        if (anyChecked) {
            document.body.classList.add('sidebar-closed');
            setTimeout(function() {
                document.body.classList.remove('sidebar-closed');
            }, 2000);
        }
    }, 1000);
})();
</script>
""", unsafe_allow_html=True)

if menu == "Rapportini Aziendali":
    st.title("Rapportini Aziendali")
    st.caption("D'Andrea Angelo E.C. - Gestione e Controllo Interventi")
    tot_rapportini = len(st.session_state.rapportini)
    tot_km = sum(int(float(r["km"])) for r in st.session_state.rapportini if "km" in r and str(r["km"]) != "nan")
    tot_ore = sum(float(r["ore"]) for r in st.session_state.rapportini if "ore" in r and str(r["ore"]) != "nan")
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="card"><span class="stat-val">📄 {tot_rapportini}</span><br><span class="stat-lbl">Rapportini Totali</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="card"><span class="stat-val">🕒 {tot_ore} ore</span><br><span class="stat-lbl">Tempo Totale</span></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="card"><span class="stat-val">🚀 {tot_km} km</span><br><span class="stat-lbl">Distanza Totale</span></div>', unsafe_allow_html=True)
    st.subheader("Elenco rapportini")
    
    if len(st.session_state.rapportini) == 0:
        st.info("Nessun rapportino salvato.")
    
    for idx, r in enumerate(reversed(st.session_state.rapportini)):
        idx_reale = len(st.session_state.rapportini) - 1 - idx
        with st.container():
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; align-items: center;">
                    <strong style="color: var(--text-color); font-size: 16px;">{r.get('cliente', 'Sconosciuto')}</strong>
                </div>
                <div style="color: var(--text-color); opacity: 0.7; font-size:13px; margin-top:5px;">📍 {r.get('cantiere','-')} | 📅 {formatta_data(r.get('data','-'))}</div>
                <div style="margin-top:8px; font-size:13px; color: var(--text-color); opacity: 0.85;">
                    🚗 {r.get('km', 0)} km  •  🕒 {r.get('ore', 0.0)} ore  •  🧾 Spese: € {float(r.get('spese',0.0)):.2f}
                </div>
                {f'<div style="margin-top:8px; font-size:12px; font-style:italic; background:rgba(128,128,128,0.08); padding:6px; border-radius:6px;">📝 {r["note"]}</div>' if r.get("note") and str(r["note"]) != "nan" else ""}
            </div>
            """, unsafe_allow_html=True)
            col_mod, col_elim = st.columns(2)
            with col_mod:
                if st.button("✏️ Modifica", key=f"mod_{idx_reale}", use_container_width=True):
                    st.session_state.modifica_idx = idx_reale
                    st.rerun()
            with col_elim:
                if st.button("🗑️ Elimina", key=f"del_{idx_reale}", use_container_width=True):
                    st.session_state.elimina_idx = idx_reale
                    st.rerun()

elif menu == "Nuovo Rapportino":
    st.title("Nuovo Rapportino")

    # Stato per reset automatico del form dopo il salvataggio.
    if "reset_form" not in st.session_state:
        st.session_state.reset_form = False
    if "nr_cliente" not in st.session_state:
        st.session_state.nr_cliente = "Seleziona cliente"
    if "nr_cantiere" not in st.session_state:
        st.session_state.nr_cantiere = ""
    if "nr_data" not in st.session_state:
        st.session_state.nr_data = datetime.now()
    if "nr_km" not in st.session_state:
        st.session_state.nr_km = 0
    if "nr_ore" not in st.session_state:
        st.session_state.nr_ore = 0.0
    if "nr_spese" not in st.session_state:
        st.session_state.nr_spese = 0.0
    if "nr_nota_spesa" not in st.session_state:
        st.session_state.nr_nota_spesa = ""
    if "nr_note" not in st.session_state:
        st.session_state.nr_note = ""
    if "nr_canvas_key" not in st.session_state:
        st.session_state.nr_canvas_key = 0

    # Nota: nessuna callback di "clear if zero" perché l'utente deve poter
    # inserire anche il valore 0 come valore valido (es. 0 km percorsi).
    # Il reset dopo salvataggio è gestito più sotto con del session_state.

    # Se è stato richiesto il reset, azzera TUTTI i campi PRIMA di disegnarli.
    # Per i number_input impostiamo None e cancelliamo le chiavi per forzare
    # la ricreazione pulita del widget (così non mostra "0").
    if st.session_state.reset_form:
        for k in ("nr_cliente", "nr_cantiere", "nr_data",
                  "nr_km", "nr_ore", "nr_spese",
                  "nr_nota_spesa", "nr_note"):
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.nr_cliente = "Seleziona cliente"
        st.session_state.nr_cantiere = ""
        st.session_state.nr_data = datetime.now()
        st.session_state.nr_km = None
        st.session_state.nr_ore = None
        st.session_state.nr_spese = None
        st.session_state.nr_nota_spesa = ""
        st.session_state.nr_note = ""
        st.session_state.nr_canvas_key += 1  # forza canvas vuoto
        st.session_state.reset_form = False
        # Forza un re-render immediato così i number_input ripartono vuoti
        st.rerun()

    lista_clienti = list(st.session_state.clienti_dict.keys())
    cliente = st.selectbox("Cliente *", ["Seleziona cliente"] + lista_clienti, key="nr_cliente")
    if cliente != "Seleziona cliente":
        info = st.session_state.clienti_dict[cliente]
        st.info(f"Tariffario applicato: **€ {info['prezzo_ora']:.2f}/ora** e **€ {info['prezzo_km']:.2f}/km**")
    cantiere = st.text_input("Cantiere *", placeholder="Nome del cantiere", key="nr_cantiere")
    data = st.date_input("Data *", key="nr_data")
    col_km, col_ore = st.columns(2)
    with col_km:
        km = st.number_input(
            "Km percorsi *", min_value=0, value=None,
            key="nr_km"
        )
    with col_ore:
        ore = st.number_input(
            "Ore lavorate *", min_value=0.0, value=None, step=0.5,
            key="nr_ore"
        )
    col_spese, col_motivo = st.columns(2)
    with col_spese:
        spese = st.number_input(
            "Spese extra (€)", min_value=0.0, value=None,
            key="nr_spese"
        )
    with col_motivo:
        nota_spesa = st.text_input("Es: carburante", placeholder="Causale spesa", key="nr_nota_spesa")
    note = st.text_area("Note / Descrizione Intervento", placeholder="Inserisci qui i dettagli dei lavori svolti...", key="nr_note")
    st.write("Firma del cliente")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="#000000", background_color="#ffffff", height=150, update_streamlit=True, key=f"canvas_{st.session_state.nr_canvas_key}")
    
    # Stato per evitare salvataggi duplicati: il bottone resta disabilitato
    # finché l'utente non modifica un campo del form.
    if "salvando" not in st.session_state:
        st.session_state.salvando = False
    if "form_signature" not in st.session_state:
        st.session_state.form_signature = ""
    if "ultimo_salvataggio_signature" not in st.session_state:
        st.session_state.ultimo_salvataggio_signature = ""

    firma_corrente = f"{cliente}|{cantiere}|{data}|{km}|{ore}|{spese}|{nota_spesa}|{note}"
    # Se l'utente ha cambiato qualcosa, riabilita il salvataggio
    if st.session_state.salvando and firma_corrente != st.session_state.ultimo_salvataggio_signature:
        st.session_state.salvando = False

    if st.button("💾 Salva Rapportino", use_container_width=True, disabled=st.session_state.salvando, key="btn_salva_rapportino"):
        if cliente == "Seleziona cliente" or not cantiere:
            st.error("Per favore compila tutti i campi obbligatori (*)")
        else:
            st.session_state.salvando = True
            # Normalizza i numerici: se il campo è vuoto (None), trattalo come 0.
            km_val = int(km) if km is not None else 0
            ore_val = float(ore) if ore is not None else 0.0
            spese_val = float(spese) if spese is not None else 0.0
            nuovo = {
                "cliente": cliente, "cantiere": cantiere, "data": str(data),
                "km": km_val, "ore": ore_val, "spese": spese_val,
                "nota_spesa": nota_spesa, "note": note
            }
            st.session_state.rapportini.append(nuovo)
            st.session_state.ultimo_salvataggio_signature = firma_corrente
            if conn_disponibile and gworksheet is not None:
                try:
                    if scrivi_su_google_sheets(gworksheet, st.session_state.rapportini):
                        st.success("✅ Rapportino salvato permanentemente su Google Fogli!")
                    else:
                        st.error("Errore durante il salvataggio su Google Sheets.")
                except Exception as e:
                    st.error(f"Errore durante il salvataggio sul cloud: {e}")
            else:
                st.warning("Rapportino salvato localmente (Database Google Sheets non abilitato).")
            # Chiedi il reset del form: al prossimo render tutti i campi saranno vuoti/zero.
            st.session_state.reset_form = True
            st.rerun()

elif menu == "Report Mensili e Clienti":
    st.title("Generazione Report Avanzati")
    mese = st.selectbox("Seleziona Mese", list(MESI_DICT.keys()), index=4)
    cliente_selezionato = st.selectbox("Seleziona Cliente", ["Tutti i clienti"] + list(st.session_state.clienti_dict.keys()), index=0)
    st.markdown('<div class="card">🛠️ **Opzioni di Calcolo Fiscale**', unsafe_allow_html=True)
    c_iva1, c_iva2 = st.columns(2)
    with c_iva1: 
        attiva_iva = st.checkbox("Calcola Aliquota IVA", key="chk_iva", on_change=chiudi_altro_flag, args=("iva",))
    with c_iva2: 
        reverse_charge = st.checkbox("Applica Reverse Charge", key="chk_rev", on_change=chiudi_altro_flag, args=("reverse",))
    valore_aliquota = st.number_input("Specifica Aliquota IVA (%)", min_value=0, max_value=100, value=22, step=1) if attiva_iva else 22
    st.markdown('</div>', unsafe_allow_html=True)
    codice_mese = MESI_DICT[mese]
    rapportini_filtrati = [r for r in st.session_state.rapportini if str(r.get("data", "")).split("-")[1] == codice_mese and (cliente_selezionato == "Tutti i clienti" or r.get("cliente") == cliente_selezionato)]
    if rapportini_filtrati:
        dati_completi = []
        totale_imponibile = 0.0
        for r in rapportini_filtrati:
            prezzi_cli = st.session_state.clienti_dict.get(r["cliente"], {"prezzo_ora": 0, "prezzo_km": 0})
            tot_voce = calcola_totale_rapportino(r)
            totale_imponibile += tot_voce
            dati_completi.append({
                "Data": formatta_data(r.get("data", "-")), "Cliente": r.get("cliente", "-"), "Cantiere": r.get("cantiere", "-"),
                "Ore": str(r.get("ore", 0.0)), "Tariffa/h": f"€ {prezzi_cli['prezzo_ora']:.2f}",
                "Km": str(r.get("km", 0)), "Tariffa/Km": f"€ {prezzi_cli['prezzo_km']:.2f}",
                "Spese Extra": f"€ {float(r.get('spese',0.0)):.2f}", "Totale Lordo": f"€ {tot_voce:.2f}"
            })
        st.dataframe(pd.DataFrame(dati_completi), use_container_width=True)
        st.markdown(f"**Totale Imponibile:** € {totale_imponibile:,.2f}")
        iva_calcolata = totale_imponibile * (valore_aliquota / 100) if attiva_iva and not reverse_charge else 0.0
        if reverse_charge: 
            st.info("ℹ️ **Regime applicato:** Reverse Charge")
        elif attiva_iva: 
            st.markdown(f"**IVA ({valore_aliquota}%):** € {iva_calcolata:,.2f}")
        st.markdown(f"## **Totale Dovuto:** € {totale_imponibile + iva_calcolata:,.2f}")
        if not PDF_AVAILABLE:
            st.error("⚠️ Errore di sistema: Generatore PDF non disponibile. Assicurati che 'fpdf' sia inserito nel file requirements.txt su GitHub.")
        else:
            col_pdf, col_pdf_note = st.columns(2)
            with col_pdf:
                st.download_button(label="📄 Esporta Tabella PDF", data=genera_pdf(dati_completi, mese, cliente_selezionato, totale_imponibile, attiva_iva, valore_aliquota, reverse_charge), file_name=f"Report_{mese}_{cliente_selezionato}.pdf", mime='application/pdf', use_container_width=True)
            with col_pdf_note:
                st.download_button(label="📝 Esporta Solo Note (PDF)", data=genera_pdf_note(rapportini_filtrati, mese, cliente_selezionato), file_name=f"Note_{mese}_{cliente_selezionato}.pdf", mime='application/pdf', use_container_width=True)
    else:
        st.info("Nessun intervento trovato per questo filtro.")

elif menu == "Clienti":
    st.title("Gestione Clienti")

    # Stato per modifica cliente
    if "modifica_cliente" not in st.session_state:
        st.session_state.modifica_cliente = None
    if "elimina_cliente" not in st.session_state:
        st.session_state.elimina_cliente = None

    # --- MODALE MODIFICA CLIENTE ---
    if st.session_state.modifica_cliente is not None:
        nome_orig = st.session_state.modifica_cliente
        if nome_orig not in st.session_state.clienti_dict:
            st.session_state.modifica_cliente = None
            st.rerun()
        info_orig = st.session_state.clienti_dict[nome_orig]
        st.subheader(f"✏️ Modifica cliente: {nome_orig}")
        with st.form("form_modifica_cliente"):
            nuovo_nome = st.text_input("Nome Azienda / Cliente", value=nome_orig)
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                p_ora = st.number_input("Prezzo Orario (€/h)", min_value=0.0, value=float(info_orig.get("prezzo_ora", 0.0)), step=0.5)
            with c_p2:
                p_km = st.number_input("Prezzo Chilometrico (€/km)", min_value=0.0, value=float(info_orig.get("prezzo_km", 0.0)), step=0.05)
            col_s, col_c = st.columns(2)
            with col_s:
                salva_cli = st.form_submit_button("💾 Salva modifiche", use_container_width=True)
            with col_c:
                annulla_cli = st.form_submit_button("❌ Annulla", use_container_width=True)
        if salva_cli:
            nuovo_nome_clean = nuovo_nome.strip()
            if not nuovo_nome_clean:
                st.error("Il nome del cliente non può essere vuoto.")
            else:
                # Se il nome è cambiato, aggiorna anche i rapportini esistenti
                if nuovo_nome_clean != nome_orig:
                    st.session_state.clienti_dict.pop(nome_orig, None)
                    for r in st.session_state.rapportini:
                        if r.get("cliente") == nome_orig:
                            r["cliente"] = nuovo_nome_clean
                st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.session_state.modifica_cliente = None
                st.success(f"Cliente '{nuovo_nome_clean}' aggiornato con successo!")
                st.rerun()
        if annulla_cli:
            st.session_state.modifica_cliente = None
            st.rerun()
        st.markdown("---")

    # --- MODALE ELIMINA CLIENTE ---
    if st.session_state.elimina_cliente is not None:
        nome_el = st.session_state.elimina_cliente
        # Conta quanti rapportini usano questo cliente
        n_usati = sum(1 for r in st.session_state.rapportini if r.get("cliente") == nome_el)
        st.error(f"⚠️ Eliminare il cliente **{nome_el}**?")
        if n_usati > 0:
            st.warning(f"⚠️ Ci sono {n_usati} rapportini associati a questo cliente. Verranno mantenuti ma con il nome cliente originale non più presente nel listino.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Sì, elimina", use_container_width=True, key="confirm_delete_cliente"):
                st.session_state.clienti_dict.pop(nome_el, None)
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.session_state.elimina_cliente = None
                st.success(f"Cliente '{nome_el}' eliminato!")
                st.rerun()
        with col2:
            if st.button("❌ Annulla", use_container_width=True, key="cancel_delete_cliente"):
                st.session_state.elimina_cliente = None
                st.rerun()
        st.markdown("---")

    # --- FORM AGGIUNGI NUOVO CLIENTE ---
    with st.expander("➕ Aggiungi Nuovo Cliente"):
        nuovo_nome = st.text_input("Nome Azienda / Cliente", key="nuovo_cl_nome")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            p_ora = st.number_input("Prezzo Orario (€/h)", min_value=0.0, value=40.0, step=0.5, key="nuovo_cl_ora")
        with c_p2:
            p_km = st.number_input("Prezzo Chilometrico (€/km)", min_value=0.0, value=0.5, step=0.05, key="nuovo_cl_km")
        if st.button("➕ Aggiungi al Listino", use_container_width=True, key="btn_add_cliente"):
            nuovo_nome_clean = nuovo_nome.strip()
            if not nuovo_nome_clean:
                st.error("Inserisci un nome cliente valido.")
            elif nuovo_nome_clean in st.session_state.clienti_dict:
                st.error(f"Esiste già un cliente con nome '{nuovo_nome_clean}'. Usa il tasto Modifica per aggiornarlo.")
            else:
                st.session_state.clienti_dict[nuovo_nome_clean] = {"prezzo_ora": p_ora, "prezzo_km": p_km}
                scrivi_clienti_su_gsheets(st.session_state.clienti_dict)
                st.success(f"Cliente '{nuovo_nome_clean}' aggiunto con successo!")
                st.rerun()

    st.write("### Elenco Tariffe Attuali")
    if not st.session_state.clienti_dict:
        st.info("Nessun cliente nel listino. Aggiungine uno usando il form sopra.")
    for c, info in st.session_state.clienti_dict.items():
        with st.container():
            st.markdown(f'<div class="card"><strong>{c}</strong><br>🕒 Oraria: € {info["prezzo_ora"]:.2f}/h | 🚗 Km: € {info["prezzo_km"]:.2f}/km</div>', unsafe_allow_html=True)
            col_m, col_e = st.columns(2)
            with col_m:
                if st.button(f"✏️ Modifica", key=f"mod_cl_{c}", use_container_width=True):
                    st.session_state.modifica_cliente = c
                    st.rerun()
            with col_e:
                if st.button(f"🗑️ Elimina", key=f"del_cl_{c}", use_container_width=True):
                    st.session_state.elimina_cliente = c
                    st.rerun()

# --- INTESTAZIONE AZIENDALE SIDEBAR (sotto il menu) ---
st.sidebar.markdown("<br>" * 2 + "---", unsafe_allow_html=True)
st.sidebar.markdown('<div style="font-size: 11px; opacity: 0.65;"><strong>D\'ANDREA ANGELO E.C.</strong><br>Via Cesare Battisti, 9 - 25043 Breno (BS)<br>P. IVA: 04154960985</div>', unsafe_allow_html=True)
