import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { apiErrorMessage, authAPI } from '../../services/api';
import toast from 'react-hot-toast';

const ValidateResetToken = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [isValidating, setIsValidating] = useState(true);
    const [isValid, setIsValid] = useState(false);
    const [error, setError] = useState('');

    const token = searchParams.get('token');

    useEffect(() => {
        const validateToken = async () => {
            if (!token) {
                setError('No reset token provided');
                setIsValidating(false);
                return;
            }

            try {
                // Validate the token with the backend
                await authAPI.validateResetToken(token);
                setIsValid(true);
                toast.success('Reset token validated successfully');

                // Redirect to reset password form with the token
                setTimeout(() => {
                    navigate(`/reset-password?token=${token}`);
                }, 1000);
            } catch (error) {
                const errorMessage = apiErrorMessage(error, 'Invalid or expired reset token');
                setError(errorMessage);
                toast.error(errorMessage);
                setIsValidating(false);
            }
        };

        validateToken();
    }, [token, navigate]);

    if (isValidating) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    {/* Logo/Brand */}
                    <div className="text-center mb-8">
                        <h1 className="text-4xl font-bold text-gradient mb-2">Portfolia</h1>
                        <p className="text-gray-400">Your Professional Portfolio Management Platform</p>
                    </div>

                    {/* Loading Card */}
                    <div className="card p-8 animate-fade-in text-center">
                        <div className="mb-6">
                            <div className="mx-auto w-16 h-16 bg-primary-900/20 rounded-full flex items-center justify-center mb-4">
                                <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
                            </div>
                            <h2 className="text-2xl font-semibold text-gray-100 mb-2">Validating Reset Token</h2>
                            <p className="text-gray-400">
                                Please wait while we validate your password reset link...
                            </p>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="text-center mt-8">
                        <p className="text-xs text-gray-500">
                            © {new Date().getFullYear()} Portfolia. All rights reserved.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    if (isValid) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    {/* Logo/Brand */}
                    <div className="text-center mb-8">
                        <h1 className="text-4xl font-bold text-gradient mb-2">Portfolia</h1>
                        <p className="text-gray-400">Your Professional Portfolio Management Platform</p>
                    </div>

                    {/* Success Card */}
                    <div className="card p-8 animate-fade-in text-center">
                        <div className="mb-6">
                            <div className="mx-auto w-16 h-16 bg-success-900/20 rounded-full flex items-center justify-center mb-4">
                                <CheckCircle className="w-8 h-8 text-success-400" />
                            </div>
                            <h2 className="text-2xl font-semibold text-gray-100 mb-2">Token Validated!</h2>
                            <p className="text-gray-400">
                                Redirecting you to the password reset form...
                            </p>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="text-center mt-8">
                        <p className="text-xs text-gray-500">
                            © {new Date().getFullYear()} Portfolia. All rights reserved.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Logo/Brand */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gradient mb-2">Portfolia</h1>
                    <p className="text-gray-400">Your Professional Portfolio Management Platform</p>
                </div>

                {/* Error Card */}
                <div className="card p-8 animate-fade-in text-center">
                    <div className="mb-6">
                        <div className="mx-auto w-16 h-16 bg-danger-900/20 rounded-full flex items-center justify-center mb-4">
                            <AlertCircle className="w-8 h-8 text-danger-400" />
                        </div>
                        <h2 className="text-2xl font-semibold text-gray-100 mb-2">Invalid Reset Link</h2>
                        <p className="text-gray-400 mb-4">
                            {error || 'The password reset link is invalid or has expired.'}
                        </p>
                        <p className="text-gray-400">
                            Please request a new password reset.
                        </p>
                    </div>

                    <button
                        onClick={() => navigate('/forgot-password')}
                        className="btn-primary w-full py-3 text-base font-medium"
                    >
                        Request New Reset
                    </button>
                </div>

                {/* Footer */}
                <div className="text-center mt-8">
                    <p className="text-xs text-gray-500">
                        © {new Date().getFullYear()} Portfolia. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ValidateResetToken;
