/**
 * rate-limiter.js — Rate limiter for API calls
 *
 * Limits requests-per-minute to avoid hitting API rate limits.
 * Used by AgentEngine for LLM call throttling.
 *
 * Usage: const limiter = new RateLimiter();
 *        const waitMs = limiter.waitMs();
 *
 * Load this BEFORE agent-engine.js in index.html (RateLimiter is referenced in constructor).
 */

class RateLimiter {
    constructor() {
        this._timestamps = [];
        this._cooldownEnd = 0;
    }

    /**
     * Calculate how many milliseconds to wait before making the next API call,
     * based on the configured `config.rpmLimit` (requests per minute).
     * @returns {number} Milliseconds to wait (0 = no wait needed)
     */
    waitMs() {
        const rpm = config.rpmLimit || 0;
        if (rpm <= 0) return 0;
        const now = Date.now();
        this._timestamps = this._timestamps.filter(ts => now - ts < 60000);
        if (this._timestamps.length < rpm) {
            this._timestamps.push(now);
            return 0;
        }
        return Math.max(0, 60000 - (now - this._timestamps[0]));
    }

    /**
     * Milliseconds until a rate-limit slot opens (read-only; does not consume a slot).
     * @returns {number}
     */
    msUntilAvailable() {
        const rpm = config.rpmLimit || 0;
        if (rpm <= 0) return 0;
        const now = Date.now();
        this._timestamps = this._timestamps.filter(ts => now - ts < 60000);
        if (this._timestamps.length < rpm) return 0;
        return Math.max(0, 60000 - (now - this._timestamps[0]));
    }

    /**
     * @deprecated Use msUntilAvailable()
     */
    getCooldown() {
        return this.msUntilAvailable() / 1000;
    }

    /** Reset all rate-limiter state (timestamps and cooldown) */
    reset() {
        this._timestamps = [];
        this._cooldownEnd = 0;
    }
}

window.RateLimiter = RateLimiter;
