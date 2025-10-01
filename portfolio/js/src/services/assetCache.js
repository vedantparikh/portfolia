/**
 * ASSET CACHE SERVICE - Performance optimization for asset searches
 * 
 * This service manages preloading and caching of asset data to improve
 * the performance of asset search components throughout the application.
 * 
 * Features:
 * - Preloads assets when user navigates to transaction-related pages
 * - Caches assets in memory for fast filtering
 * - Provides cache invalidation and refresh mechanisms
 * - Optimized for large datasets with efficient filtering
 */

import { assetAPI } from './api';

class AssetCacheService {
    constructor() {
        this.assets = [];
        this.isLoading = false;
        this.lastFetched = null;
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes cache timeout
        this.subscribers = new Set();
    }

    /**
     * Subscribe to cache updates
     * @param {Function} callback - Function to call when cache updates
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    /**
     * Notify all subscribers of cache updates
     */
    notifySubscribers() {
        this.subscribers.forEach(callback => {
            try {
                callback({
                    assets: this.assets,
                    isLoading: this.isLoading,
                    lastFetched: this.lastFetched
                });
            } catch (error) {
                console.error('Error notifying cache subscriber:', error);
            }
        });
    }

    /**
     * Check if cache is still valid
     * @returns {boolean}
     */
    isCacheValid() {
        if (!this.lastFetched || this.assets.length === 0) {
            return false;
        }
        return Date.now() - this.lastFetched < this.cacheTimeout;
    }

    /**
     * Get cached assets or fetch if needed
     * @param {boolean} forceRefresh - Force refresh even if cache is valid
     * @returns {Promise<Array>} Array of assets
     */
    async getAssets(forceRefresh = true) {
        // Return cached data if valid and not forcing refresh
        if (!forceRefresh && this.isCacheValid()) {
            console.log('[AssetCache] Returning cached assets:', this.assets.length);
            return this.assets;
        }

        // If already loading, wait for it to complete
        if (this.isLoading) {
            console.log('[AssetCache] Already loading, waiting...');
            return new Promise((resolve) => {
                const checkLoading = () => {
                    if (!this.isLoading) {
                        resolve(this.assets);
                    } else {
                        setTimeout(checkLoading, 100);
                    }
                };
                checkLoading();
            });
        }

        return this.fetchAssets();
    }

    /**
     * Fetch assets from API and update cache
     * @returns {Promise<Array>} Array of assets
     */
    async fetchAssets() {
        try {
            console.log('[AssetCache] Fetching assets from API...');
            this.isLoading = true;
            this.notifySubscribers();

            const response = await assetAPI.getAssets({ limit: 1000 });
            this.assets = response.data || [];
            this.lastFetched = Date.now();
            this.isLoading = false;

            console.log('[AssetCache] Successfully cached assets:', this.assets.length);
            this.notifySubscribers();

            return this.assets;
        } catch (error) {
            console.error('[AssetCache] Failed to fetch assets:', error);
            this.isLoading = false;
            this.notifySubscribers();
            throw error;
        }
    }

    /**
     * Preload assets in the background
     * Called when user might need assets soon (e.g., navigating to transactions)
     */
    async preloadAssets() {
        if (this.isCacheValid() || this.isLoading) {
            console.log('[AssetCache] Skipping preload - cache valid or already loading');
            return;
        }

        console.log('[AssetCache] Preloading assets in background...');
        try {
            await this.fetchAssets();
        } catch (error) {
            // Silently fail for background preloading
            console.warn('[AssetCache] Background preload failed:', error);
        }
    }

    /**
     * Filter cached assets by query
     * @param {string} query - Search query
     * @param {number} limit - Maximum results to return
     * @returns {Array} Filtered and sorted assets
     */
    filterAssets(query, limit = 8) {
        if (!query || query.length < 2) {
            return [];
        }

        const searchTerm = query.toLowerCase();
        const filtered = this.assets.filter(asset => {
            const symbol = asset.symbol?.toLowerCase() || '';
            const name = asset.name?.toLowerCase() || '';
            return symbol.includes(searchTerm) || name.includes(searchTerm);
        });

        // Sort by relevance: exact symbol match first, then symbol starts with, then name matches
        filtered.sort((a, b) => {
            const aSymbol = a.symbol?.toLowerCase() || '';
            const bSymbol = b.symbol?.toLowerCase() || '';
            
            // Exact symbol match gets highest priority
            if (aSymbol === searchTerm) return -1;
            if (bSymbol === searchTerm) return 1;
            
            // Symbol starts with search term gets second priority
            if (aSymbol.startsWith(searchTerm) && !bSymbol.startsWith(searchTerm)) return -1;
            if (bSymbol.startsWith(searchTerm) && !aSymbol.startsWith(searchTerm)) return 1;
            
            // Then alphabetical by symbol
            return aSymbol.localeCompare(bSymbol);
        });

        return filtered.slice(0, limit);
    }

    /**
     * Find specific asset by symbol
     * @param {string} symbol - Asset symbol to find
     * @returns {Object|null} Asset object or null if not found
     */
    findAssetBySymbol(symbol) {
        if (!symbol) return null;
        return this.assets.find(asset => 
            asset.symbol?.toLowerCase() === symbol.toLowerCase()
        ) || null;
    }

    /**
     * Clear cache and force refresh on next request
     */
    clearCache() {
        console.log('[AssetCache] Clearing cache');
        this.assets = [];
        this.lastFetched = null;
        this.notifySubscribers();
    }

    /**
     * Force refresh the cache immediately
     * @returns {Promise<Array>} Array of assets
     */
    async refreshCache() {
        console.log('[AssetCache] Force refreshing cache...');
        return await this.fetchAssets();
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getStats() {
        return {
            assetCount: this.assets.length,
            isLoading: this.isLoading,
            lastFetched: this.lastFetched,
            cacheAge: this.lastFetched ? Date.now() - this.lastFetched : null,
            isValid: this.isCacheValid(),
            subscriberCount: this.subscribers.size
        };
    }
}

// Create singleton instance
const assetCache = new AssetCacheService();

export default assetCache;
