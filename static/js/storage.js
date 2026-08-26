/**
 * StorageProvider — IndexedDB-based persistent storage
 * Replaces localStorage with async, quota-unlimited storage.
 * Stores: config, profiles, item library, character histories
 */
class StorageProvider {
    constructor(dbName = 'VirtualWorldDB', version = 2) {
        this.dbName = dbName;
        this.version = version;
        this._db = null;
        this._ready = this._init();
    }

    async _init() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(this.dbName, this.version);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                const oldVersion = e.oldVersion;
                
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
            };
            req.onsuccess = (e) => {
                this._db = e.target.result;
                resolve();
            };
            req.onerror = (e) => {
                console.warn('IndexedDB init failed, falling back to localStorage:', e.target.error);
                resolve();
            };
        });
    }

    async _ensureReady() {
        await this._ready;
        if (!this._db) return false;
        return true;
    }

    // --- Generic CRUD ---

    async get(storeName, key) {
        if (!await this._ensureReady()) return this._localFallback('get', storeName, key);
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.get(key);
                req.onsuccess = () => resolve(req.result ? req.result.value : null);
                req.onerror = () => resolve(null);
            } catch (e) { resolve(null); }
        });
    }

    async set(storeName, key, value) {
        if (!await this._ensureReady()) { this._localFallback('set', storeName, key, value); return; }
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.put({ key, value });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async delete(storeName, key) {
        if (!await this._ensureReady()) { this._localFallback('delete', storeName, key); return; }
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.delete(key);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async getAll(storeName) {
        if (!await this._ensureReady()) return this._localFallback('getAll', storeName);
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.getAll();
                req.onsuccess = () => {
                    const items = req.result || [];
                    const map = {};
                    items.forEach(item => { map[item.key] = item.value; });
                    resolve(map);
                };
                req.onerror = () => resolve({});
            } catch (e) { resolve({}); }
        });
    }

    async getAllAsArray(storeName) {
        if (!await this._ensureReady()) return [];
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            } catch (e) { resolve([]); }
        });
    }

    async clear(storeName) {
        if (!await this._ensureReady()) return;
        return new Promise((resolve) => {
            try {
                const tx = this._db.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.clear();
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    // --- LocalStorage fallback for graceful degradation ---
    _localFallback(op, storeName, key, value) {
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
                    const map = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const k = localStorage.key(i);
                        if (k && k.startsWith(prefix)) {
                            const storeKey = k.slice(prefix.length);
                            try { map[storeKey] = JSON.parse(localStorage.getItem(k)); } catch (e) {}
                        }
                    }
                    return map;
                }
            }
        } catch (e) { return null; }
    }

    // --- Convenience methods ---

    async getConfig(key) {
        const val = await this.get('config', key);
        return val !== null ? val : null;
    }

    async setConfig(key, value) {
        return this.set('config', key, value);
    }

    async getProfile(id) {
        return this.get('profiles', id);
    }

    async setProfile(id, data) {
        return this.set('profiles', id, data);
    }

    async getAllProfiles() {
        return this.getAll('profiles');
    }

    async deleteProfile(id) {
        return this.delete('profiles', id);
    }

    async getLibraryItem(id) {
        return this.get('item_library', id);
    }

    async setLibraryItem(id, data) {
        return this.set('item_library', id, data);
    }

    async getAllLibraryItems() {
        return this.getAll('item_library');
    }

    async deleteLibraryItem(id) {
        return this.delete('item_library', id);
    }

    async getCharacterHistory(charName) {
        const val = await this.get('character_histories', charName);
        return val || null;
    }

    async setCharacterHistory(charName, history) {
        return this.set('character_histories', charName, history);
    }

    async deleteCharacterHistory(charName) {
        return this.delete('character_histories', charName);
    }

    async getSetting(id) {
        return this.get('settings', id);
    }

    async setSetting(id, value) {
        return this.set('settings', id, value);
    }

    // --- Event Log persistence ---

    async saveEventLog(entries) {
        return new Promise((resolve) => {
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

    async loadEventLog() {
        return new Promise((resolve) => {
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

// Singleton instance
const storage = new StorageProvider();