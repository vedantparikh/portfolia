import { cva } from 'class-variance-authority';

const spinnerVariants = cva('animate-spin rounded-full border-solid', {
    variants: {
        size: {
            sm: 'h-4 w-4 border-2',
            md: 'h-8 w-8 border-[3px]',
            lg: 'h-10 w-10 border-[3px]',
            xl: 'h-14 w-14 border-4',
        },
        color: {
            primary: 'border-primary-500/25 border-t-primary-400',
            white: 'border-white/25 border-t-white',
            gray: 'border-gray-500/25 border-t-gray-400',
            success: 'border-success-500/25 border-t-success-400',
            danger: 'border-danger-500/25 border-t-danger-400',
        },
    },
    defaultVariants: { size: 'md', color: 'primary' },
});

// One calm visual for every loading state; `type` only picks the default caption
const defaultTexts = {
    default: 'Loading...',
    analyst: 'Analyzing performance...',
    quantum: 'Calculating returns...',
    ticker: 'Fetching market data...',
    candlestick: 'Fetching historical data...',
    donut: 'Optimizing allocation...',
    transaction: 'Processing transaction...',
};

const Spinner = ({
    type = 'default',
    text,
    size,
    color,
    className = '',
    centered = false,
}) => {
    const displayText = text === null ? null : text || defaultTexts[type] || defaultTexts.default;

    const spinner = (
        <div role="status" className={spinnerVariants({ size, color })}>
            <span className="sr-only">{displayText || 'Loading...'}</span>
        </div>
    );

    if (centered) {
        return (
            <div className={`flex items-center justify-center ${className}`}>
                <div className="flex flex-col items-center">
                    {spinner}
                    {displayText && (
                        <p className="mt-3 text-sm text-gray-400">{displayText}</p>
                    )}
                </div>
            </div>
        );
    }

    if (displayText) {
        return (
            <div className={`flex items-center gap-3 ${className}`}>
                {spinner}
                <span className="text-sm text-gray-400">{displayText}</span>
            </div>
        );
    }

    return <div className={className}>{spinner}</div>;
};

export default Spinner;
