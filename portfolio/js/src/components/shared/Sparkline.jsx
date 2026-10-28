const round1 = (n) => Math.round(n * 10) / 10;

const Sparkline = ({ values, width = 80, height = 24, className = 'text-primary-400', title }) => {
    if (!values || values.length < 2) return null;
    const min = Math.min(...values);
    const range = Math.max(...values) - min || 1;
    const step = width / (values.length - 1);
    const points = values
        .map((v, i) => `${round1(i * step)},${round1(height - 1 - ((v - min) / range) * (height - 2))}`)
        .join(' ');

    return (
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className={`block ${className}`} role="img" aria-label={title}>
            {title && <title>{title}</title>}
            <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        </svg>
    );
};

export default Sparkline;
