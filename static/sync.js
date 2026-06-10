/**
 * sync.js - Engine di sincronizzazione offline/online
 * Rapportini Pro - D'Andrea Angelo E.C.
 *
 * Funzionamento:
 * 1. Quando viene salvato un rapportino offline, IndexedDB lo memorizza
 * 2. sync.js monitora lo stato online/offline
 * 3. Quando si torna online, tenta automaticamente la sincronizzazione
 * 4. Comunica lo stato a Streamlit via hidden div + session state
 */

(function() {
  "use strict";

  // Elemento nascosto per comunicare con Streamlit
  const SYNC_STATUS_ELEMENT_ID = "rapportini-sync-status";
  const SYNC_TRIGGER_ELEMENT_ID = "rapportini-sync-trigger";

  /**
   * Aggiorna il badge di pending nella sidebar Streamlit
   */
  async function updateSyncBadge() {
    try {
      const count = await window.RapportiniDB.countPending();
      const badge = document.getElementById("rapportini-pending-badge");
      const syncStatus = document.getElementById(SYNC_STATUS_ELEMENT_ID);

      if (badge) {
        if (count > 0) {
          badge.style.display = "inline";
          badge.textContent = count;
        } else {
          badge.style.display = "none";
        }
      }

      // Comunica a Streamlit via hidden div
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
   * Tenta di sincronizzare tutti i rapportini pending
   * @returns {Object} { synced: number, failed: number }
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

      let synced = 0;
      let failed = 0;

      for (const record of pending) {
        try {
          // Invia a Streamlit tramite un endpoint fittizio che Streamlit gestirà
          const success = await sendToStreamlit(record);
          if (success) {
            await window.RapportiniDB.markAsSynced(record.id);
            synced++;
          } else {
            failed++;
          }
        } catch (e) {
          console.warn("[Rapportini Sync] Errore record:", record.id, e);
          failed++;
        }
      }

      if (synced > 0) {
        localStorage.setItem("rapportini-last-sync", new Date().toISOString());
        // Trigger aggiornamento UI Streamlit
        triggerStreamlitRerun();
      }

      return { synced, failed };
    } catch (e) {
      console.error("[Rapportini Sync] Errore sync:", e);
      return { synced: 0, failed: 1 };
    }
  }

  /**
   * Invia un rapportino a Streamlit inserendolo in un campo nascosto
   * che poi Streamlit leggerà via st.markdown + query param
   * @param {Object} record - Il rapportino da inviare
   * @returns {Promise<boolean>}
   */
  async function sendToStreamlit(record) {
    return new Promise((resolve) => {
      try {
        // Usiamo un iframe nascosto per triggerare il rerun con i dati
        const trigger = document.getElementById(SYNC_TRIGGER_ELEMENT_ID);
        if (trigger) {
          // Serializza i dati del rapportino escludendo i metadati interni
          const dataToSend = {
            cliente: record.cliente,
            cantiere: record.cantiere,
            data: record.data,
            km: record.km,
            ore: record.ore,
            spese: record.spese,
            note: record.note || "",
            nota_spesa: record.nota_spesa || ""
          };
          trigger.textContent = JSON.stringify(dataToSend);
          trigger.dispatchEvent(new Event("sync-data"));
          resolve(true);
        } else {
          resolve(false);
        }
      } catch (e) {
        resolve(false);
      }
    });
  }

  /**
   * Forza un rerun di Streamlit manipolando un componente nascosto
   */
  function triggerStreamlitRerun() {
    const rerunBtn = document.querySelector(
      'button[kind="secondary"][data-testid="basebutton"]'
    );
    // Attraverso hidden input
    const hiddenInput = document.getElementById("rapportini-sync-rerun");
    if (hiddenInput) {
      hiddenInput.value = Date.now().toString();
      hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  /**
   * Inizializza i listener per online/offline
   */
  function initOnlineDetection() {
    window.addEventListener("online", async () => {
      console.log("[Rapportini Sync] Online!");
      updateSyncBadge();
      // Tenta sync automatico quando torniamo online
      const result = await syncPendingRapportini();
      if (result.synced > 0) {
        console.log(`[Rapportini Sync] Sync automatico: ${result.synced} successi`);
      }
    });

    window.addEventListener("offline", () => {
      console.log("[Rapportini Sync] Offline!");
      updateSyncBadge();
    });

    // Polling periodico anche quando online (per sicurezza)
    setInterval(async () => {
      if (navigator.onLine) {
        const pending = await window.RapportiniDB.countPending();
        if (pending > 0) {
          await syncPendingRapportini();
        }
      }
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
  // Aspetta che DOM sia pronto e db.js sia caricato
  function init() {
    if (window.RapportiniDB) {
      updateSyncBadge();
      initOnlineDetection();
      // Cleanup vecchi record (oltre 30 giorni)
      window.RapportiniDB.cleanOldSynced(30).catch(() => {});
      console.log("[Rapportini Sync] Inizializzato");
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