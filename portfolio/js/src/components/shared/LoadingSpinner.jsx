import React, { useState, useEffect } from 'react';
import { cva } from 'class-variance-authority';


// 1. The ORIGINAL spinner, now as 'default', with full size/color variants
const defaultSpinnerVariants = cva(
    'animate-spin rounded-full border-solid border-t-transparent',
    {
        variants: {
            size: {
                sm: 'h-4 w-4 border-2',
                md: 'h-8 w-8 border-4',
                lg: 'h-12 w-12 border-4',
                xl: 'h-16 w-16 border-4',
            },
            color: {
                primary: 'border-blue-500',
                white: 'border-white',
                gray: 'border-gray-400',
                success: 'border-green-500',
                danger: 'border-red-500',
            },
        },
        defaultVariants: {
            size: 'md',
            color: 'primary',
        },
    }
);

const DefaultVisual = ({ size, color }) => (
    <div role="status" className={defaultSpinnerVariants({ size, color })}>
        <span className="sr-only">Loading...</span>
    </div>
);


// 2. The Portfolio Spinners
const AnalystVisual = () => (
    <div className="flex items-end justify-center space-x-1.5 h-12">
        <div className="w-2.5 h-6 bg-green-500 rounded-t-full animate-[bounce_1.2s_ease-in-out_infinite] [animation-delay:-0.3s]"></div>
        <div className="w-2.5 h-10 bg-green-500 rounded-t-full animate-[bounce_1.2s_ease-in-out_infinite] [animation-delay:-0.15s]"></div>
        <div className="w-2.5 h-12 bg-green-500 rounded-t-full animate-[bounce_1.2s_ease-in-out_infinite]"></div>
        <div className="w-2.5 h-8 bg-green-500 rounded-t-full animate-[bounce_1.2s_ease-in-out_infinite] [animation-delay:-0.15s]"></div>
        <div className="w-2.5 h-10 bg-green-500 rounded-t-full animate-[bounce_1.2s_ease-in-out_infinite] [animation-delay:-0.3s]"></div>
    </div>
);

const QuantumVisual = () => {
    const [number, setNumber] = useState(0);
    useEffect(() => {
        const interval = setInterval(() => setNumber(Math.floor(Math.random() * 900000) + 100000), 80);
        return () => clearInterval(interval);
    }, []);
    return (
        <p className="font-mono text-3xl font-bold text-green-400 tabular-nums h-12 flex items-center">
            {number.toString().padStart(7, '0')}
        </p>
    );
};

const TickerVisual = () => {
    const tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'JPM', 'V', 'SPY', 'QQQ'];
    const repeatedTickers = [...tickers, ...tickers];
    return (
         <div className="w-full max-w-[280px] bg-gray-800/50 rounded-md h-10 overflow-hidden relative">
            <div className="absolute top-0 left-0 flex items-center h-full animate-[scroll_25s_linear_infinite]">
                {repeatedTickers.map((ticker, index) => (
                    <div key={index} className="flex items-center mx-4">
                        <span className="text-gray-200 font-semibold">{ticker}</span>
                        <span className={`ml-2 text-sm ${Math.random() > 0.5 ? 'text-green-500' : 'text-red-500'}`}>
                            {Math.random() > 0.5 ? '▲' : '▼'}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const CandlestickVisual = () => (
    <div className="flex items-center justify-center h-12 space-x-2">
        <div className="flex flex-col items-center animate-[pulse_1.5s_ease-in-out_infinite] [animation-delay:-0.4s]">
            <div className="w-0.5 h-2 bg-green-500"></div><div className="w-3 h-6 bg-green-500"></div><div className="w-0.5 h-1 bg-green-500"></div>
        </div>
        <div className="flex flex-col items-center animate-[pulse_1.5s_ease-in-out_infinite] [animation-delay:-0.2s]">
            <div className="w-0.5 h-1 bg-red-500"></div><div className="w-3 h-8 bg-red-500"></div><div className="w-0.5 h-2 bg-red-500"></div>
        </div>
        <div className="flex flex-col items-center animate-[pulse_1.5s_ease-in-out_infinite]">
            <div className="w-0.5 h-3 bg-green-500"></div><div className="w-3 h-5 bg-green-500"></div><div className="w-0.5 h-3 bg-green-500"></div>
        </div>
    </div>
);

const DonutVisual = () => (
    <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full animate-spin" style={{ background: 'conic-gradient(#4f46e5 0% 25%, #10b981 25% 60%, #3b82f6 60% 85%, #f59e0b 85% 100%)' }}></div>
        <div className="absolute inset-2 bg-gray-800 rounded-full"></div>
    </div>
);

const TransactionVisual = () => (
    <div className="relative w-12 h-12 flex items-center justify-center">
        <div className="absolute w-full h-full bg-sky-500 rounded-full animate-[ping_1.5s_cubic-bezier(0,0,0.2,1)_infinite]"></div>
        <div className="relative w-12 h-12 bg-gray-700 rounded-full flex items-center justify-center shadow-lg">
            <svg className="w-6 h-6 text-sky-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
        </div>
    </div>
);


// --- Main Unified Spinner Component ---
const spinnerMap = {
    'default': { Component: DefaultVisual, defaultText: 'Loading...' },
    analyst: { Component: AnalystVisual, defaultText: 'Analyzing Performance...' },
    quantum: { Component: QuantumVisual, defaultText: 'Calculating Returns...' },
    ticker: { Component: TickerVisual, defaultText: 'Fetching Market Data...' },
    candlestick: { Component: CandlestickVisual, defaultText: 'Fetching Historical Data...' },
    donut: { Component: DonutVisual, defaultText: 'Optimizing Allocation...' },
    transaction: { Component: TransactionVisual, defaultText: 'Processing Transaction...' },
};

const LoadingSpinner = ({
    type = 'default',
    text,
    size, // Used by 'default' type
    color, // Used by 'default' type
    className = '',
    centered = false
}) => {
    const { Component: SpinnerVisual, defaultText } = spinnerMap[type] || spinnerMap.default;
    const displayText = text === null ? null : text || defaultText;

    const spinner = <SpinnerVisual size={size} color={color} />;

    if (centered) {
        return (
            <div className={`flex items-center justify-center ${className}`}>
                <div className="text-center">
                    {spinner}
                    {displayText && (
                        <p className="mt-4 text-sm font-medium text-gray-400 tracking-wide">
                            {displayText}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    if (displayText) {
        return (
            <div className={`flex items-center space-x-4 ${className}`}>
                {spinner}
                <span className="text-sm font-medium text-gray-400 tracking-wide">
                    {displayText}
                </span>
            </div>
        );
    }

    return <div className={className}>{spinner}</div>;
};

export default LoadingSpinner;