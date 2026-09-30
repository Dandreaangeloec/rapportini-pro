/**
 * sync.js - Engine di sincronizzazione offline/online - v2 (CORRETTO)
 * Rapportini Pro - D'Andrea Angelo E.C.
 *
 * IMPORTANTE (fix crash): la vecchia versione "inviava" i dati a Streamlit
 * tramite un elemento nascosto ma Streamlit non aveva MAI un handler reale
 * per quei dati. sendToStreamlit() restituiva sempre true → i record venivano
 * marcati come sincronizzati pur non essendo mai stati salvati su Google Sheets.
 * Questo causava PERDITA DI DATI quando un utente salvava offline e la PWA
 * "fingeva" di aver sincronizzato.
 *
 * NUOVO APPROCCIO (sicuro):
 * 1. Se online → i dati vengono salvati normalmente dall'app Streamlit.
 * 2. Se offline → il record viene salvato in IndexedDB come "pending" e
 *    mostriamo un badge all'utente.
 * 3. Il sync NON tenta più di iniettare dati in Streamlit via hidden div
 *    (meccanismo inaffidabile). Invece mostra un messaggio chiaro all'utente
 *    che i dati pending vanno inseriti manualmente appena torna online.
 * 4. Nessun "finto successo": i record NEL IndexedDB NON vengono mai rimossi
 *    se non c'è stato un vero invio confermato.
 */

(function() {
  "use strict";

  const SYNC_STATUS_ELEMENT_ID = "rapportini-sync-status";
  const PENDING_BADGE_ID = "rapportini-pending-badge";

  /**
   * Aggiorna il badge di pending nella sidebar Streamlit
   */
  async function updateSyncBadge() {
    try {
      const count = await window.RapportiniDB.countPending();
      const badge = document.getElementById(PENDING_BADGE_ID);
      const syncStatus = document.getElementById(SYNC_STATUS_ELEMENT_ID);

      if (badge) {
        if (count > 0) {
          badge.style.display = "inline";
          badge.textContent = count;
        } else {
          badge.style.display = "none";
        }
      }

      // Comunica a Streamlit via hidden div (solo per info, non per dati)
      if (syncStatus) {
        const statusData = JSON.stringify({
          pending: count,
          online: navigator.onLine,
          lastSync: localStorage.getItem("rapportini-last-sync") || null
        });
        syncStatus.textContent = statusData;
        syncStatus.dispatchEvent(new Event("change"));
      }
    } catch (e) {
      console.warn("[Rapportini Sync] Errore badge:", e);
    }
  }

  /**
   * Tenta di sincronizzare i rapportini pending.
   *
   * NOTA IMPORTANTE: questo NON tenta più l'iniezione diretta in Streamlit
   * (meccanismo inaffidabile e causa di perdita dati). Invece, mostra un
   * messaggio all'utente e NON marca i record come sincronizzati.
   *
   * @returns {Object} { synced: 0, failed: 1, offline: bool, message: string }
   */
  async function syncPendingRapportini() {
    if (!navigator.onLine) {
      console.warn("[Rapportini Sync] Offline - sync rimandato");
      return { synced: 0, failed: 1, offline: true };
    }

    try {
      const pending = await window.RapportiniDB.getPendingRapportini();
      if (pending.length === 0) {
        return { synced: 0, failed: 0 };
      }

      // IMPORTANTE: NON abbiamo un modo affidabile di iniettare dati in
      // Streamlit da JS. Quindi NON facciamo finto sync.
      // Mostriamo solo un avviso (via console) che i dati vanno reinseriti.
      console.warn(
        `[Rapportini Sync] ${pending.length} rapportini offline in attesa. ` +
        "Il sync automatico via JS è disabilitato per evitare perdita dati. " +
        "Inserirli manualmente oppure attendere che vengano gestiti da Streamlit."
      );

      // Non marcamo nulla come sincronizzato, restituiamo "failed" così
      // il polling NON continua all'infinito a tentare.
      return {
        synced: 0,
        failed: pending.length,
        offline: false,
        message: "Sync automatico disabilitato - inserire i dati manualmente"
      };
    } catch (e) {
      console.error("[Rapportini Sync] Errore sync:", e);
      return { synced: 0, failed: 1 };
    }
  }

  /**
   * Inizializza i listener per online/offline
   */
  function initOnlineDetection() {
    window.addEventListener("online", async () => {
      console.log("[Rapportini Sync] Online!");
      updateSyncBadge();
      // Non tentare più sync automatico distruttivo
    });

    window.addEventListener("offline", () => {
      console.warn("[Rapportini Sync] Offline!");
      updateSyncBadge();
    });

    // Polling periodico: aggiorna SOLO il badge, nessuna sincronizzazione
    setInterval(async () => {
      updateSyncBadge();
    }, 30000); // Ogni 30 secondi
  }

  /**
   * Esponi funzioni globalmente per l'uso da console o altri script
   */
  window.RapportiniSync = {
    syncPending: syncPendingRapportini,
    updateBadge: updateSyncBadge,
    getStatus: async () => ({
      online: navigator.onLine,
      pending: await window.RapportiniDB.countPending(),
      lastSync: localStorage.getItem("rapportini-last-sync")
    })
  };

  // --- INIT ---
  function init() {
    if (window.RapportiniDB) {
      updateSyncBadge();
      initOnlineDetection();
      // Cleanup vecchi record (oltre 30 giorni) — NON tocca quelli pending
      window.RapportiniDB.cleanOldSynced(30).catch(() => {});
      console.log("[Rapportini Sync v2] Inizializzato (sync sicuro, no fake)");
    } else {
      // Riprova tra poco (db.js potrebbe non essere ancora caricato)
      setTimeout(init, 500);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();