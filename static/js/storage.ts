/**
 * StorageProvider — IndexedDB-based persistent storage
 * Replaces localStorage with async, quota-unlimited storage.
 * Stores: config, profiles, item_library, character_histories, settings, event_log,
 *         llm_dataset, llm_raw_exchanges (LLM inspector), graph_assets (graph map)
 *
 * @module storage — the IndexedDB persistence layer (with a localStorage fallback)
 * @contributes StorageProvider: get/set/getAll/clear per named object store
 * @powers settings persistence, save games, dataset + LLM inspector, graph map overlays
 * @relates consumed by config.js and most feature modules; no dependencies of its own
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class StorageProvider {
    declare dbName: string;
    declare version: number;
    /** Open handle; null when IndexedDB is unavailable (localStorage fallback). */
    declare _db: IDBDatabase | null;
    /** Resolves once the open request settles — success OR failure. */
    declare _ready: Promise<void>;

    constructor(dbName = 'VirtualWorldDB', version = 5) {
        this.dbName = dbName;
        this.version = version;
        this._db = null;
        this._ready = this._init();
    }

    async _init(): Promise<void> {
        return new Promise<void>((resolve, reject) => {
            const req = indexedDB.open(this.dbName, this.version);
            req.onupgradeneeded = (e: Event) => {
                const upgrade = e as IDBVersionChangeEvent;
                const db = (upgrade.target as IDBOpenDBRequest).result;
                const oldVersion = upgrade.oldVersion;
                
                // Delete old stores with wrong keyPath (bugfix: was 'id' but code uses 'key')
                if (oldVersion < 2) {
                    // Version 2: fix store keyPaths - use 'key' consistently
                    for (const storeName of ['profiles', 'item_library', 'settings', 'character_histories']) {
                        if (db.objectStoreNames.contains(storeName)) {
                            db.deleteObjectStore(storeName);
                        }
                    }
                }
                
                // Create object stores with correct keyPath === 'key'
                if (!db.objectStoreNames.contains('config')) {
                    db.createObjectStore('config', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('profiles')) {
                    db.createObjectStore('profiles', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('item_library')) {
                    db.createObjectStore('item_library', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('character_histories')) {
                    db.createObjectStore('character_histories', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('event_log')) {
                    db.createObjectStore('event_log', { keyPath: 'id' });
                }
                // Version 3: LLM request/response dataset for fine-tuning export
                if (!db.objectStoreNames.contains('llm_dataset')) {
                    db.createObjectStore('llm_dataset', { keyPath: 'key' });
                }
                // Version 4: raw HTTP exchanges (status/headers/usage) for the
                // LLM Inspector (task-405). Authorization headers are redacted
                // before storing.
                if (!db.objectStoreNames.contains('llm_raw_exchanges')) {
                    db.createObjectStore('llm_raw_exchanges', { keyPath: 'key' });
                }
                // Version 5: per-scenario graph background image + node layout
                // (map overlay behind the vis.js graph).
                if (!db.objectStoreNames.contains('graph_assets')) {
                    db.createObjectStore('graph_assets', { keyPath: 'key' });
                }
            };
            req.onsuccess = (e: Event) => {
                this._db = (e.target as IDBOpenDBRequest).result;
                resolve();
            };
            req.onerror = (e: Event) => {
                console.warn('IndexedDB init failed, falling back to localStorage:', (e.target as IDBRequest<unknown>).error);
                resolve();
            };
        });
    }

    async _ensureReady(): Promise<boolean> {
        await this._ready;
        if (!this._db) return false;
        return true;
    }

    // --- Generic CRUD ---

    async get(storeName: string, key: string): Promise<any> {
        if (!await this._ensureReady()) return this._localFallback('get', storeName, key);
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.get(key);
                req.onsuccess = () => resolve(req.result ? req.result.value : null);
                req.onerror = () => resolve(null);
            } catch (e) { resolve(null); }
        });
    }

    async set(storeName: string, key: string, value: unknown): Promise<any> {
        if (!await this._ensureReady()) { this._localFallback('set', storeName, key, value); return; }
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.put({ key, value });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async delete(storeName: string, key: string): Promise<any> {
        if (!await this._ensureReady()) { this._localFallback('delete', storeName, key); return; }
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.delete(key);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async getAll(storeName: string): Promise<any> {
        if (!await this._ensureReady()) return this._localFallback('getAll', storeName);
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.getAll();
                req.onsuccess = () => {
                    const items = req.result || [];
                    const map: Record<string, unknown> = {};
                    items.forEach((item: any) => { map[item.key] = item.value; });
                    resolve(map);
                };
                req.onerror = () => resolve({});
            } catch (e) { resolve({}); }
        });
    }

    async getAllAsArray(storeName: string): Promise<any> {
        if (!await this._ensureReady()) return [];
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            } catch (e) { resolve([]); }
        });
    }

    async clear(storeName: string): Promise<any> {
        if (!await this._ensureReady()) return;
        return new Promise<any>((resolve) => {
            try {
                const tx = this._db!.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.clear();
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    // --- LocalStorage fallback for graceful degradation ---
    _localFallback(op: string, storeName: string, key?: string, value?: unknown) {
        const prefix = `vw_${storeName}_`;
        try {
            switch (op) {
                case 'get':
                    const raw = localStorage.getItem(prefix + key);
                    return raw ? JSON.parse(raw) : null;
                case 'set':
                    localStorage.setItem(prefix + key, JSON.stringify(value));
                    return;
                case 'delete':
                    localStorage.removeItem(prefix + key);
                    return;
                case 'getAll': {
                    const map: Record<string, unknown> = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const k = localStorage.key(i) ?? '';
                        if (k && k.startsWith(prefix)) {
                            const storeKey = k.slice(prefix.length);
                            try { map[storeKey] = JSON.parse(String(localStorage.getItem(k))); } catch (e) {}
                        }
                    }
                    return map;
                }
            }
        } catch (e) { return null; }
    }

    // --- Convenience methods ---

    async getConfig(key: string) {
        const val = await this.get('config', key);
        return val !== null ? val : null;
    }

    async setConfig(key: string, value: unknown) {
        return this.set('config', key, value);
    }

    async getProfile(id: string) {
        return this.get('profiles', id);
    }

    async setProfile(id: string, data: unknown) {
        return this.set('profiles', id, data);
    }

    async getAllProfiles() {
        return this.getAll('profiles');
    }

    async deleteProfile(id: string) {
        return this.delete('profiles', id);
    }

    async getLibraryItem(id: string) {
        return this.get('item_library', id);
    }

    async setLibraryItem(id: string, data: unknown) {
        return this.set('item_library', id, data);
    }

    async getAllLibraryItems() {
        return this.getAll('item_library');
    }

    async deleteLibraryItem(id: string) {
        return this.delete('item_library', id);
    }

    async getCharacterHistory(charName: string) {
        const val = await this.get('character_histories', charName);
        return val || null;
    }

    async setCharacterHistory(charName: string, history: unknown) {
        return this.set('character_histories', charName, history);
    }

    async deleteCharacterHistory(charName: string) {
        return this.delete('character_histories', charName);
    }

    async getSetting(id: string) {
        return this.get('settings', id);
    }

    async setSetting(id: string, value: unknown) {
        return this.set('settings', id, value);
    }

    // --- Event Log persistence ---

    async saveEventLog(entries: string[]): Promise<any> {
        return new Promise<any>((resolve) => {
            if (!this._db) { resolve(false); return; }
            try {
                const tx = this._db.transaction('event_log', 'readwrite');
                const store = tx.objectStore('event_log');
                store.clear(); // remove old
                // Store entries in batches with auto-increment ids
                for (let i = 0; i < entries.length; i++) {
                    store.add({ id: i, html: entries[i] });
                }
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async loadEventLog(): Promise<any> {
        return new Promise<any>((resolve) => {
            if (!this._db) { resolve([]); return; }
            try {
                const tx = this._db.transaction('event_log', 'readonly');
                const store = tx.objectStore('event_log');
                const req = store.getAll();
                req.onsuccess = () => {
                    const items = req.result || [];
                    items.sort((a, b) => a.id - b.id);
                    resolve(items.map(item => item.html));
                };
                req.onerror = () => resolve([]);
            } catch (e) { resolve([]); }
        });
    }

    async clearEventLog() {
        return this.clear('event_log');
    }
}

// Singleton instance.
// The local name is `storageSingleton` because `storage` is already declared
// as a global in static/js/types/globals.d.ts, and this file is a classic
// script (not a module), so a same-named top-level `const` is a redeclaration.
// The original relied on a script-level lexical binding being visible to every
// other classic script (config.js reads bare `storage`), so publish it on
// window to keep exactly that reachability.
(window as unknown as { storage: StorageProvider }).storage = new StorageProvider();