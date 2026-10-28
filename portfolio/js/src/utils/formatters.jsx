import { ArrowDownLeft, ArrowDownRight, ArrowUpDown, ArrowUpRight, Minus, Plus, TrendingDown, TrendingUp } from 'lucide-react';

/**
 * Format price values with appropriate decimal places
 * @param {number|string|null|undefined} price - The price value to format
 * @returns {string} Formatted price string
 */
export const formatPrice = (price, currency = 'USD') => {
    if (price === null || price === undefined) return 'N/A';
    const numericPrice = parseFloat(price);
    if (isNaN(numericPrice)) return 'N/A';
    const digits = numericPrice < 0.01 ? 6 : numericPrice < 1 ? 4 : 2;
    return formatCurrency(numericPrice, {
        currency,
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
};

/**
 * Format currency values using Intl.NumberFormat
 * @param {number|string|null|undefined} amount - The amount to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, options = {}) => {
    const { currency, defaultValue, ...rest } = options;
    if (amount === null || amount === undefined || isNaN(amount)) {
        return defaultValue || formatCurrency(0, { currency });
    }

    const defaultOptions = {
        style: 'currency',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        ...rest,
        currency: currency || 'USD',
    };

    return new Intl.NumberFormat('en-US', defaultOptions).format(amount);
};

/**
 * Format market cap values with appropriate suffixes (B, M, T)
 * @param {number|string|null|undefined} marketCap - The market cap value to format
 * @returns {string} Formatted market cap string
 */
export const formatMarketCap = (marketCap, currency = 'USD') => {
    if (marketCap === null || marketCap === undefined) return 'N/A';
    const numericMarketCap = parseFloat(marketCap);
    if (isNaN(numericMarketCap)) return 'N/A';
    if (numericMarketCap >= 1e12) return `${formatCurrency(numericMarketCap / 1e12, { currency })}T`;
    if (numericMarketCap >= 1e9) return `${formatCurrency(numericMarketCap / 1e9, { currency })}B`;
    if (numericMarketCap >= 1e6) return `${formatCurrency(numericMarketCap / 1e6, { currency })}M`;
    return formatCurrency(numericMarketCap, { currency, minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

/**
 * Format volume values with appropriate suffixes (B, M, K)
 * @param {number|string|null|undefined} volume - The volume value to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted volume string
 */
export const formatVolume = (volume, options = {}) => {
    if (volume === null || volume === undefined) return 'N/A';
    const numericVolume = parseFloat(volume);
    if (isNaN(numericVolume)) return 'N/A';

    const { includePrefix = false, precision = 2 } = options;
    const prefix = includePrefix ? '$' : '';

    if (numericVolume >= 1e9) return `${prefix}${(numericVolume / 1e9).toFixed(precision)}B`;
    if (numericVolume >= 1e6) return `${prefix}${(numericVolume / 1e6).toFixed(precision)}M`;
    if (numericVolume >= 1e3) return `${prefix}${(numericVolume / 1e3).toFixed(precision)}K`;
    return `${prefix}${numericVolume.toFixed(0)}`;
};

/**
 * Format percentage values with appropriate sign and decimal places
 * @param {number|string|null|undefined} value - The percentage value to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted percentage string
 */
export const formatPercentage = (value, options = {}) => {
    if (value === null || value === undefined) return 'N/A';
    const numericValue = parseFloat(value);
    if (isNaN(numericValue)) return 'N/A';

    if (Math.abs(numericValue) >= 1e21) {
        // You can return 'N/A' to match your other errors,
        // or return a more descriptive value like Infinity.
        return numericValue > 0 ? '+Infinity%' : '-Infinity%';
    }

    const {
        showSign = true,
        precision = 2,
        defaultValue = '0.00%'
    } = options;

    if (numericValue === 0 && defaultValue) return defaultValue;

    const sign = showSign && numericValue > 0 ? '+' : '';
    return `${sign}${numericValue.toFixed(precision)}%`;
};

/**
 * A plain number with fixed decimals (for prices whose currency is unknown).
 */
export const formatDecimal = (value, digits = 2) => {
    if (value === null || value === undefined || isNaN(parseFloat(value))) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    }).format(parseFloat(value));
};

/**
 * Difference between two percentages, in percentage points ("+1.25 pp").
 */
export const formatPercentagePoints = (value, options = {}) => {
    const text = formatPercentage(value, options);
    return text === 'N/A' ? '—' : text.replace(/%$/, ' pp');
};

/**
 * Format large numbers with appropriate suffixes (B, M, K)
 * @param {number|string|null|undefined} num - The number to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted number string
 */
export const formatNumber = (num, options = {}) => {
    if (num === null || num === undefined) return 'N/A';
    const numericNum = parseFloat(num);
    if (isNaN(numericNum)) return 'N/A';

    const { precision = 1, includePrefix = false } = options;
    const prefix = includePrefix ? '$' : '';

    if (numericNum >= 1e9) return `${prefix}${(numericNum / 1e9).toFixed(precision)}B`;
    if (numericNum >= 1e6) return `${prefix}${(numericNum / 1e6).toFixed(precision)}M`;
    if (numericNum >= 1e3) return `${prefix}${(numericNum / 1e3).toFixed(precision)}K`;
    return `${prefix}${numericNum.toString()}`;
};

/**
 * Format quantity values with appropriate decimal places
 * @param {number|string|null|undefined} quantity - The quantity value to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted quantity string
 */
export const formatQuantity = (quantity, options = {}) => {
    if (quantity === null || quantity === undefined) return 'N/A';
    const numericQuantity = parseFloat(quantity);
    if (isNaN(numericQuantity)) return 'N/A';

    const { precision = 4, showCommas = true } = options;

    if (showCommas) {
        return numericQuantity.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: precision
        });
    }

    return numericQuantity.toFixed(precision);
};

/**
 * Format date strings with various formats
 * @param {string|null|undefined} dateString - The date string to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString, options = {}) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'N/A';

    const {
        format = 'short', // 'short', 'long', 'time', 'datetime'
        timezone = 'en-US'
    } = options;

    switch (format) {
        case 'short':
            return date.toLocaleDateString(timezone, {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        case 'long':
            return date.toLocaleDateString(timezone, {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        case 'time':
            return date.toLocaleTimeString(timezone, {
                hour: '2-digit',
                minute: '2-digit'
            });
        case 'datetime':
            return date.toLocaleString(timezone, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        default:
            return date.toLocaleDateString(timezone);
    }
};

/**
 * Format date and time strings for display
 * @param {string|null|undefined} dateString - The date string to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted date and time string
 */
export const formatDateTime = (dateString, options = {}) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'N/A';

    const { timezone = 'en-US' } = options;

    return date.toLocaleString(timezone, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

/**
 * Get CSS color class based on change value
 * @param {number|string|null|undefined} change - The change value
 * @param {Object} options - Color options
 * @returns {string} CSS color class
 */
export const getChangeColor = (change, options = {}) => {
    const {
        positiveColor = 'text-success-400',
        negativeColor = 'text-danger-400',
        neutralColor = 'text-gray-400'
    } = options;

    if (change === null || change === undefined) return neutralColor;
    const numericChange = parseFloat(change);
    if (isNaN(numericChange)) return neutralColor;

    if (numericChange > 0) return positiveColor;
    if (numericChange < 0) return negativeColor;
    return neutralColor;
};

/**
 * Get change icon component based on change value
 * @param {number|string|null|undefined} change - The change value
 * @param {Object} options - Icon options
 * @returns {React.Component|null} Change icon component
 */
export const getChangeIcon = (change, options = {}) => {
    const {
        size = 16,
        positiveIcon: PositiveIcon = TrendingUp,
        negativeIcon: NegativeIcon = TrendingDown,
        positiveClassName = 'text-success-400',
        negativeClassName = 'text-danger-400'
    } = options;

    if (change === null || change === undefined) return null;
    const numericChange = parseFloat(change);
    if (isNaN(numericChange)) return null;

    if (numericChange > 0) return <PositiveIcon size={size} className={positiveClassName} />;
    if (numericChange < 0) return <NegativeIcon size={size} className={negativeClassName} />;
    return null;
};

/**
 * Get change arrow component based on change value
 * @param {number|string|null|undefined} change - The change value
 * @param {Object} options - Arrow options
 * @returns {React.Component|null} Change arrow component
 */
export const getChangeArrow = (change, options = {}) => {
    const {
        size = 14,
        positiveArrow: PositiveArrow = ArrowUpRight,
        negativeArrow: NegativeArrow = ArrowDownRight,
        positiveClassName = 'text-success-400',
        negativeClassName = 'text-danger-400'
    } = options;

    if (change === null || change === undefined) return null;
    const numericChange = parseFloat(change);
    if (isNaN(numericChange)) return null;

    if (numericChange > 0) return <PositiveArrow size={size} className={positiveClassName} />;
    if (numericChange < 0) return <NegativeArrow size={size} className={negativeClassName} />;
    return null;
};

/**
 * Get change arrow component for left direction
 * @param {number|string|null|undefined} change - The change value
 * @param {Object} options - Arrow options
 * @returns {React.Component|null} Change arrow component
 */
export const getChangeArrowLeft = (change, options = {}) => {
    const {
        size = 14,
        positiveArrow: PositiveArrow = ArrowUpRight,
        negativeArrow: NegativeArrow = ArrowDownLeft,
        positiveClassName = 'text-success-400',
        negativeClassName = 'text-danger-400'
    } = options;

    if (change === null || change === undefined) return null;
    const numericChange = parseFloat(change);
    if (isNaN(numericChange)) return null;

    if (numericChange > 0) return <PositiveArrow size={size} className={positiveClassName} />;
    if (numericChange < 0) return <NegativeArrow size={size} className={negativeClassName} />;
    return null;
};

/**
 * Format currency with compact notation
 * @param {number|string|null|undefined} amount - The amount to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted currency string
 */
export const formatCompactCurrency = (amount, options = {}) => {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return options.defaultValue || '$0';
    }

    const { precision = 0 } = options;

    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        minimumFractionDigits: precision,
        maximumFractionDigits: precision
    }).format(amount);
};

/**
 * Format percentage with compact notation
 * @param {number|string|null|undefined} value - The percentage value to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted percentage string
 */
export const formatCompactPercentage = (value, options = {}) => {
    if (value === null || value === undefined) return 'N/A';
    const numericValue = parseFloat(value);
    if (isNaN(numericValue)) return 'N/A';

    const {
        showSign = true,
        precision = 1,
        defaultValue = '0%'
    } = options;

    if (numericValue === 0 && defaultValue) return defaultValue;

    const sign = showSign && numericValue > 0 ? '+' : '';
    return `${sign}${numericValue.toFixed(precision)}%`;
};

/**
 * Get transaction icon component based on transaction type
 * @param {string} type - The transaction type
 * @param {Object} options - Icon options
 * @returns {React.Component|null} Transaction icon component
 */
export const getTransactionIcon = (type, options = {}) => {
    const {
        size = 16,
        buyIcon: BuyIcon = Plus,
        sellIcon: SellIcon = Minus,
        otherIcon: OtherIcon = ArrowUpDown,
        buyClassName = 'text-success-400',
        sellClassName = 'text-danger-400',
        otherClassName = 'text-gray-400'
    } = options;

    switch (type?.toLowerCase()) {
        case 'buy':
        case 'purchase':
            return <BuyIcon size={size} className={buyClassName} />;
        case 'sell':
        case 'sale':
            return <SellIcon size={size} className={sellClassName} />;
        default:
            return <OtherIcon size={size} className={otherClassName} />;
    }
};

/**
 * Get transaction color class based on transaction type
 * @param {string} type - The transaction type
 * @param {Object} options - Color options
 * @returns {string} CSS color class
 */
export const getTransactionColor = (type, options = {}) => {
    const {
        buyColor = 'text-success-400',
        sellColor = 'text-danger-400',
        otherColor = 'text-gray-400'
    } = options;

    switch (type?.toLowerCase()) {
        case 'buy':
        case 'purchase':
            return buyColor;
        case 'sell':
        case 'sale':
            return sellColor;
        default:
            return otherColor;
    }
};

/**
 * Get transaction arrow component based on transaction type
 * @param {string} type - The transaction type
 * @param {Object} options - Arrow options
 * @returns {React.Component|null} Transaction arrow component
 */
export const getTransactionArrow = (type, options = {}) => {
    const {
        size = 16,
        buyArrow: BuyArrow = ArrowUpRight,
        sellArrow: SellArrow = ArrowDownRight,
        otherArrow: OtherArrow = ArrowUpDown,
        buyClassName = 'text-success-400',
        sellClassName = 'text-danger-400',
        otherClassName = 'text-gray-400'
    } = options;

    switch (type?.toLowerCase()) {
        case 'buy':
        case 'purchase':
            return <BuyArrow size={size} className={buyClassName} />;
        case 'sell':
        case 'sale':
            return <SellArrow size={size} className={sellClassName} />;
        default:
            return <OtherArrow size={size} className={otherClassName} />;
    }
};


export const formatMetricValue = (value, isPercentage = false) => {
    if (value === null || value === undefined) return "N/A";
    if (isPercentage) {
        return formatPercentage(value);
    }
    return formatCurrency(value);
};


/** A form value derived from other inputs (amount / price etc.), as the input's string. */
export const toInputDecimal = (value, digits) => Number(value).toFixed(digits);

export const formatRatio = (value, precision = 2) => {
    const n = parseFloat(value);
    return value === null || value === undefined || isNaN(n) ? "N/A" : n.toFixed(precision);
};

export const getMetricColor = (value) => {
    if (value === null || value === undefined) return "text-gray-400";
    return value >= 0 ? "text-success-400" : "text-danger-400";
};

export const getMetricIcon = (value) => {
    if (value === null || value === undefined) return null;
    return value >= 0 ? (
        <TrendingUp size={16} className="text-success-400" />
    ) : (
        <TrendingDown size={16} className="text-danger-400" />
    );
};
