# 📋 Rapportini Pro

**D'Andrea Angelo E.C. - Gestione Rapportini Aziendali**

Applicazione web per la gestione di rapportini di interventi con:
- Inserimento nuovi rapportini
- Report mensili e per cliente
- Esportazione PDF
- Database su Google Sheets
- Gestione clienti e tariffe
- ✅ **Funzionamento offline** - i rapportini salvati offline si sincronizzano automaticamente quando torni online
- ✅ **Installabile come app sul telefono** (PWA)

---

## 📲 Installare l'app sul tuo smartphone

L'app **non si scarica dal Play Store o App Store**, ma si installa direttamente dal browser come una Progressive Web App (PWA).

### URL dell'app
Vai su **Streamlit Cloud** all'indirizzo dove hai pubblicato l'app.  
Se non lo ricordi, accedi a https://share.streamlit.io/ e troverai la tua app nella dashboard.

### Istruzioni per l'installazione

**📱 Android (Chrome):**
1. Apri l'URL dell'app in **Chrome**
2. Tocca il menu **⋮** (tre puntini verticali in alto a destra)
3. Seleziona **"Aggiungi a schermata Home"**
4. Premi **"Aggiungi"** in basso a destra
5. L'icona di Rapportini Pro apparirà tra le tue app

**🍎 iPhone/iPad (Safari):**
1. Apri l'URL dell'app in **Safari**
2. Tocca l'icona **Condividi** (quadrato con freccia verso l'alto, in basso al centro)
3. Scorri verso il basso e scegli **"Aggiungi a Home"**
4. Premi **"Aggiungi"** in alto a destra
5. L'icona apparirà sulla Home screen

### Vantaggi dell'installazione
- ✅ **Icona personalizzata** sulla Home screen
- ✅ **Avvio a schermo intero** — niente barra degli indirizzi
- ✅ **Caricamento più veloce** grazie al Service Worker
- ✅ **Offline parziale** — se sei senza connessione, i dati inseriti verranno sincronizzati automaticamente quando torni online

---

## 🚀 Deploy su Streamlit Cloud

1. Crea un repository su GitHub chiamato `rapportini-pro`
2. Esegui questi comandi nel terminale:
   ```
   git init
   git add .
   git commit -m "Primo commit"
   git remote add origin https://github.com/dandreaangeloec/rapportini-pro.git
   git branch -M main
   git push -u origin main
   ```
3. Vai su https://streamlit.io/cloud e connetti GitHub
4. Clicca "New app" → seleziona il repo → Branch: main → File: `rapportini-pro/app.py`
5. In "Advanced settings" → Secrets, incolla il contenuto del file `secrets_example.txt`
6. Deploy!

## 🔧 Configurazione Google Sheets (locale)

1. Scarica il file `service-account.json` dalla console di Google Cloud
2. Crea un file `sheet_url.txt` con l'URL del tuo Google Sheet