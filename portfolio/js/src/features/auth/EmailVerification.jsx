import { AlertCircle, ArrowLeft, CheckCircle, Loader2, Mail, RefreshCw } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { useNavigate, useSearchParams } from 'react-router';
import { useAuth } from '../../contexts/AuthContext';
import { apiErrorMessage } from '../../shared/api/client';

const EmailVerification = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { verifyEmail, resendVerification } = useAuth();
    const [isVerifying, setIsVerifying] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [isVerified, setIsVerified] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const token = searchParams.get('token');

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm();

    // Auto-verify if token is present in URL
    React.useEffect(() => {
        if (token) {
            handleVerifyEmail(token);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- verify only when token changes
    }, [token]);

    const handleVerifyEmail = async (verificationToken) => {
        setIsVerifying(true);
        setError('');
        setSuccess('');

        try {
            const result = await verifyEmail(verificationToken);
            if (result.success) {
                setIsVerified(true);
                setSuccess('Email verified successfully! You can now access all features.');
                toast.success('Email verified successfully!');
                
                // Redirect to dashboard after 2 seconds
                setTimeout(() => {
                    navigate('/dashboard');
                }, 2000);
            } else {
                setError(result.error);
                toast.error(result.error);
            }
        } catch (error) {
            const errorMessage = apiErrorMessage(error, 'Email verification failed');
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setIsVerifying(false);
        }
    };

    const handleResendVerification = async () => {
        setIsResending(true);
        setError('');
        setSuccess('');

        try {
            const result = await resendVerification();
            if (result.success) {
                setSuccess('Verification email sent! Please check your inbox.');
                toast.success('Verification email sent!');
            } else {
                setError(result.error);
                toast.error(result.error);
            }
        } catch (error) {
            const errorMessage = apiErrorMessage(error, 'Failed to resend verification email');
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setIsResending(false);
        }
    };

    const onSubmit = (data) => {
        handleVerifyEmail(data.token);
    };

    if (isVerified) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
                <div className="max-w-md w-full">
                    <div className="card p-8 text-center">
                        <div className="w-16 h-16 bg-success-600/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle size={32} className="text-success-400" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-100 mb-4">
                            Email Verified!
                        </h1>
                        <p className="text-gray-400 mb-6">
                            {success || 'Your email has been successfully verified. You can now access all features.'}
                        </p>
                        <div className="flex items-center justify-center">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500"></div>
                            <span className="ml-2 text-gray-400">Redirecting to dashboard...</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
            <div className="max-w-md w-full">
                <div className="card p-8">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 bg-primary-600/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Mail size={32} className="text-primary-400" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-100 mb-2">
                            Verify Your Email
                        </h1>
                        <p className="text-gray-400">
                            Please verify your email address to access all features
                        </p>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="mb-6 p-4 bg-danger-600/20 border border-danger-600/30 rounded-lg">
                            <div className="flex items-center">
                                <AlertCircle size={20} className="text-danger-400 mr-3" />
                                <p className="text-danger-400 text-sm">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Success Message */}
                    {success && (
                        <div className="mb-6 p-4 bg-success-600/20 border border-success-600/30 rounded-lg">
                            <div className="flex items-center">
                                <CheckCircle size={20} className="text-success-400 mr-3" />
                                <p className="text-success-400 text-sm">{success}</p>
                            </div>
                        </div>
                    )}

                    {/* Manual Token Entry Form */}
                    {!token && (
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                            <div>
                                <label htmlFor="token" className="block text-sm font-medium text-gray-300 mb-2">
                                    Verification Token
                                </label>
                                <input
                                    {...register('token', {
                                        required: 'Verification token is required',
                                        minLength: {
                                            value: 10,
                                            message: 'Token must be at least 10 characters'
                                        }
                                    })}
                                    type="text"
                                    id="token"
                                    placeholder="Enter verification token from email"
                                    className="w-full px-4 py-3 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                                {errors.token && (
                                    <p className="mt-2 text-sm text-danger-400">{errors.token.message}</p>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={isVerifying}
                                className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
                            >
                                {isVerifying ? (
                                    <>
                                        <Loader2 size={20} className="animate-spin mr-2" />
                                        Verifying...
                                    </>
                                ) : (
                                    'Verify Email'
                                )}
                            </button>
                        </form>
                    )}

                    {/* Auto-verification status */}
                    {token && isVerifying && (
                        <div className="text-center py-8">
                            <Loader2 size={32} className="animate-spin text-primary-400 mx-auto mb-4" />
                            <p className="text-gray-400">Verifying your email...</p>
                        </div>
                    )}

                    {/* Resend Verification */}
                    <div className="mt-6 pt-6 border-t border-dark-700">
                        <p className="text-sm text-gray-400 text-center mb-4">
                            Didn&apos;t receive the email?
                        </p>
                        <button
                            onClick={handleResendVerification}
                            disabled={isResending}
                            className="w-full bg-dark-700 hover:bg-dark-600 disabled:bg-dark-700/50 disabled:cursor-not-allowed text-gray-300 font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
                        >
                            {isResending ? (
                                <>
                                    <Loader2 size={20} className="animate-spin mr-2" />
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <RefreshCw size={20} className="mr-2" />
                                    Resend Verification Email
                                </>
                            )}
                        </button>
                    </div>

                    {/* Back to Login */}
                    <div className="mt-6 text-center">
                        <button
                            onClick={() => navigate('/login')}
                            className="flex items-center justify-center text-gray-400 hover:text-gray-300 transition-colors duration-200"
                        >
                            <ArrowLeft size={16} className="mr-2" />
                            Back to Login
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default EmailVerification;
