/**
 * db.js - IndexedDB per archiviazione offline dei rapportini
 * Rapportini Pro - D'Andrea Angelo E.C.
 */
const DB_NAME = "RapportiniProDB";
const DB_VERSION = 1;
const STORE_NAME = "pending_rapportini";

/**
 * Apre (o crea) il database IndexedDB
 */
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        // Crea lo store con chiave auto-incrementante
        const store = db.createObjectStore(STORE_NAME, {
          keyPath: "id",
          autoIncrement: true
        });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("synced", "synced", { unique: false });
      }
    };
    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror = (event) => reject(event.target.error);
  });
}

/**
 * Salva un rapportino in coda (pending) quando offline
 * @param {Object} data - Il rapportino da salvare
 * @returns {number} L'ID del record salvato
 */
async function savePendingRapportino(data) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const record = {
      ...data,
      timestamp: new Date().toISOString(),
      synced: false
    };
    const request = store.add(record);
    request.onsuccess = () => resolve(request.result);
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * Recupera tutti i rapportini in attesa di sincronizzazione
 * @returns {Array} Lista dei rapportini pending
 */
async function getPendingRapportini() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => {
      const results = request.result.filter(r => !r.synced);
      resolve(results);
    };
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * Recupera TUTTI i rapportini (inclusi quelli synced, per cronologia)
 * @returns {Array} Lista completa
 */
async function getAllRapportini() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * Rimuove un rapportino pending dopo sincronizzazione riuscita
 * @param {number} id - ID del record da rimuovere
 */
async function removePendingRapportino(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    store.delete(id);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Conta i rapportini in attesa di sincronizzazione
 * @returns {number} Numero di pending
 */
async function countPending() {
  const pending = await getPendingRapportini();
  return pending.length;
}

/**
 * Segna un record come sincronizzato (invece di eliminarlo)
 * @param {number} id - ID del record
 */
async function markAsSynced(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const getReq = store.get(id);
    getReq.onsuccess = () => {
      const record = getReq.result;
      if (record) {
        record.synced = true;
        record.syncedAt = new Date().toISOString();
        store.put(record);
      }
    };
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Elimina tutti i record synced più vecchi di X giorni
 * @param {number} days - Giorni di tolleranza
 */
async function cleanOldSynced(days = 30) {
  const db = await openDB();
  const all = await getAllRapportini();
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  for (const record of all) {
    if (record.synced && new Date(record.syncedAt) < cutoff) {
      await removePendingRapportino(record.id);
    }
  }
}

// Esponi le funzioni globalmente
window.RapportiniDB = {
  savePendingRapportino,
  getPendingRapportini,
  getAllRapportini,
  removePendingRapportino,
  countPending,
  markAsSynced,
  cleanOldSynced
};