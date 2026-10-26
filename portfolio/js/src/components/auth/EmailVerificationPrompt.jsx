import { AlertCircle, Loader2, RefreshCw, X } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { apiErrorMessage } from '../../services/api';

const EmailVerificationPrompt = ({ user }) => {
    const { resendVerification } = useAuth();
    const [isResending, setIsResending] = useState(false);
    const [isDismissed, setIsDismissed] = useState(false);

    const handleResendVerification = async () => {
        setIsResending(true);
        try {
            const result = await resendVerification();
            if (result.success) {
                toast.success('Verification email sent! Please check your inbox.');
            } else {
                toast.error(result.error);
            }
        } catch (error) {
            const errorMessage = apiErrorMessage(error, 'Failed to resend verification email');
            toast.error(errorMessage);
        } finally {
            setIsResending(false);
        }
    };

    const handleDismiss = () => {
        setIsDismissed(true);
    };

    if (isDismissed) {
        return null;
    }

    return (
        <div className="bg-warning-600/20 border border-warning-600/30 rounded-lg p-4 mb-6">
            <div className="flex items-start">
                <div className="shrink-0">
                    <AlertCircle size={20} className="text-warning-400 mt-0.5" />
                </div>
                <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-warning-400 mb-2">
                        Email Verification Required
                    </h3>
                    <p className="text-sm text-gray-300 mb-4">
                        Please verify your email address ({user?.email}) to access all features and ensure account security.
                    </p>
                    <div className="flex items-center space-x-3">
                        <button
                            onClick={handleResendVerification}
                            disabled={isResending}
                            className="inline-flex items-center px-3 py-2 bg-warning-600/20 hover:bg-warning-600/30 disabled:bg-warning-600/10 disabled:cursor-not-allowed text-warning-400 text-sm font-medium rounded-md transition-colors duration-200"
                        >
                            {isResending ? (
                                <>
                                    <Loader2 size={16} className="animate-spin mr-2" />
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <RefreshCw size={16} className="mr-2" />
                                    Resend Email
                                </>
                            )}
                        </button>
                        <button
                            onClick={handleDismiss}
                            className="inline-flex items-center px-3 py-2 bg-dark-700/50 hover:bg-dark-600/50 text-gray-400 text-sm font-medium rounded-md transition-colors duration-200"
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
                <div className="shrink-0 ml-4">
                    <button
                        onClick={handleDismiss}
                        className="text-gray-400 hover:text-gray-300 transition-colors duration-200"
                    >
                        <X size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EmailVerificationPrompt;
