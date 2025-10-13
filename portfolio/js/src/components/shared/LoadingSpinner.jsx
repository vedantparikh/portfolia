import { cva } from 'class-variance-authority';
import React from 'react';

// Define component variants using cva
const spinnerVariants = cva(
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
                primary: 'border-primary-500',
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

const textVariants = cva('mt-2 text-sm', {
    variants: {
        color: {
            primary: 'text-primary-400',
            white: 'text-white',
            gray: 'text-gray-400',
            success: 'text-green-400',
            danger: 'text-red-400',
        },
    },
    defaultVariants: {
        color: 'gray',
    },
});


const LoadingSpinner = ({
    size,
    color,
    text = '',
    className = '',
    centered = false
}) => {
    const spinner = (
        <div
            role="status" // Accessibility: Informs screen readers this element is a live status update.
            className={spinnerVariants({ size, color, className })}
        >
            <span className="sr-only">Loading...</span> {/* Accessibility: Text for screen readers */}
        </div>
    );

    if (centered) {
        return (
            <div className="flex items-center justify-center">
                <div className="text-center">
                    {spinner}
                    {text && <p className={textVariants({ color })}>{text}</p>}
                </div>
            </div>
        );
    }

    if (text) {
        return (
            <div className="flex items-center space-x-2">
                {spinner}
                <span className={textVariants({ color, className: 'mt-0' })}>
                    {text}
                </span>
            </div>
        );
    }

    return spinner;
};

export default LoadingSpinner;