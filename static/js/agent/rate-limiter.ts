/**
 * rate-limiter.ts — Rate limiter for API calls
 *
 * Limits requests-per-minute to avoid hitting API rate limits.
 * Used by AgentEngine for LLM call throttling.
 *
 * Usage: const limiter = new RateLimiter();
 *        const waitMs = limiter.waitMs();
 *
 * Load this BEFORE agent-engine.js in index.html (RateLimiter is referenced in constructor).
 *
 * ⚠️ `rate-limiter.js` is GENERATED from this file — edit the .ts, then run
 *    `npm run build:ts`. (First converted module; see docs/design/typescript-migration.md.)
 *
 * @module agent/rate-limiter — API throttle
 * @contributes RateLimiter: requests-per-minute window + waitMs()
 * @powers honouring the configured rpm limit instead of hammering the provider
 * @relates consulted by agent-engine before each LLM call — distinct from the UI step delay
 * @docs docs/virtualWorld/UI & Settings/Settings & Configuration.md
 */

const RATE_WINDOW_MS = 60_000;

class RateLimiter {
    private _timestamps: number[] = [];
    private _cooldownEnd = 0;

    /**
     * Calculate how many milliseconds to wait before making the next API call,
     * based on the configured `config.rpmLimit` (requests per minute).
     * Consumes a slot when one is free.
     */
    waitMs(): number {
        const requestsPerMinute = Number(config.rpmLimit) || 0;
        if (requestsPerMinute <= 0) return 0;

        const now = Date.now();
        this._timestamps = this._timestamps.filter((timestamp) => now - timestamp < RATE_WINDOW_MS);

        if (this._timestamps.length < requestsPerMinute) {
            this._timestamps.push(now);
            return 0;
        }
        return Math.max(0, RATE_WINDOW_MS - (now - this._timestamps[0]));
    }

    /** Milliseconds until a rate-limit slot opens (read-only; does not consume a slot). */
    msUntilAvailable(): number {
        const requestsPerMinute = Number(config.rpmLimit) || 0;
        if (requestsPerMinute <= 0) return 0;

        const now = Date.now();
        this._timestamps = this._timestamps.filter((timestamp) => now - timestamp < RATE_WINDOW_MS);

        if (this._timestamps.length < requestsPerMinute) return 0;
        return Math.max(0, RATE_WINDOW_MS - (now - this._timestamps[0]));
    }

    /** @deprecated Use msUntilAvailable() */
    getCooldown(): number {
        return this.msUntilAvailable() / 1000;
    }

    /** Reset all rate-limiter state (timestamps and cooldown). */
    reset(): void {
        this._timestamps = [];
        this._cooldownEnd = 0;
    }
}

// Classic script: publish on window as well as the top-level lexical binding.
(window as unknown as { RateLimiter: typeof RateLimiter }).RateLimiter = RateLimiter;
