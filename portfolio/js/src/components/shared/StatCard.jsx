import InfoTip from '../../shared/ui/InfoTip';

const toneClasses = {
    primary: 'bg-primary-600/15 text-primary-400',
    success: 'bg-success-600/15 text-success-400',
    danger: 'bg-danger-600/15 text-danger-400',
    warning: 'bg-warning-600/15 text-warning-400',
    gray: 'bg-dark-700 text-gray-400',
};

const StatCard = ({
    label,
    info,
    value,
    valueTitle,
    valueClassName = 'text-gray-100',
    sub,
    detail,
    detailClassName = 'text-gray-300',
    icon: Icon,
    tone = 'primary',
    className = '',
}) => (
    <div className={`card p-5 min-w-0 ${className}`}>
        <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-gray-400">
                {label}
                {info && <InfoTip id={info} className="ml-1.5" />}
            </p>
            {Icon && (
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${toneClasses[tone]}`}>
                    <Icon size={18} />
                </div>
            )}
        </div>
        <p title={valueTitle} className={`text-xl sm:text-2xl font-semibold truncate ${valueClassName}`}>
            {value}
        </p>
        {sub && (
            <p title={sub} className="text-xs text-gray-500 truncate">
                {sub}
            </p>
        )}
        {detail != null && <p className={`mt-2 text-sm font-medium ${detailClassName}`}>{detail}</p>}
    </div>
);

export default StatCard;
