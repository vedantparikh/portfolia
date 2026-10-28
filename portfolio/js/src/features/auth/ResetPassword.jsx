import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, Lock, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';
import { authAPI } from './api';
import { apiErrorMessage } from '../../shared/api/client';
import toast from 'react-hot-toast';

const ResetPassword = () => {
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [searchParams] = useSearchParams();

    const token = searchParams.get('token');

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm();

    const password = watch('new_password');

    const onSubmit = async (data) => {
        if (!token) {
            toast.error('Invalid reset token');
            return;
        }

        setIsLoading(true);
        try {
            await authAPI.resetPassword({
                token: token,
                new_password: data.new_password,
                confirm_new_password: data.confirm_new_password,
            });
            setIsSubmitted(true);
            toast.success('Password reset successful!');
        } catch (error) {
            const errorMessage = apiErrorMessage(error, 'Failed to reset password');
            toast.error(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    if (!token) {
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
                            <p className="text-gray-400">
                                The password reset link is invalid or has expired. Please request a new password reset.
                            </p>
                        </div>

                        <Link
                            to="/forgot-password"
                            className="btn-primary w-full py-3 text-base font-medium inline-flex items-center justify-center gap-2"
                        >
                            Request New Reset
                        </Link>
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

    if (isSubmitted) {
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
                            <h2 className="text-2xl font-semibold text-gray-100 mb-2">Password Reset Successful!</h2>
                            <p className="text-gray-400">
                                Your password has been successfully reset. You can now log in with your new password.
                            </p>
                        </div>

                        <Link
                            to="/login"
                            className="btn-primary w-full py-3 text-base font-medium inline-flex items-center justify-center gap-2"
                        >
                            <ArrowLeft size={18} />
                            Go to Login
                        </Link>
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

                {/* Reset Password Card */}
                <div className="card p-8 animate-fade-in">
                    <div className="text-center mb-6">
                        <h2 className="text-2xl font-semibold text-gray-100 mb-2">Reset Your Password</h2>
                        <p className="text-gray-400">
                            Enter your new password below to complete the reset process.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        {/* New Password Field */}
                        <div>
                            <label htmlFor="new_password" className="block text-sm font-medium text-gray-300 mb-2">
                                New Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('new_password', {
                                        required: 'New password is required',
                                        minLength: {
                                            value: 8,
                                            message: 'Password must be at least 8 characters',
                                        },
                                        maxLength: {
                                            value: 128,
                                            message: 'Password must be less than 128 characters',
                                        },
                                    })}
                                    type={showPassword ? 'text' : 'password'}
                                    id="new_password"
                                    className="input-field pl-10 pr-10 w-full"
                                    placeholder="Enter your new password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {errors.new_password && (
                                <p className="mt-1 text-sm text-danger-400">{errors.new_password.message}</p>
                            )}
                        </div>

                        {/* Confirm New Password Field */}
                        <div>
                            <label htmlFor="confirm_new_password" className="block text-sm font-medium text-gray-300 mb-2">
                                Confirm New Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('confirm_new_password', {
                                        required: 'Please confirm your new password',
                                        validate: (value) => value === password || 'Passwords do not match',
                                    })}
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    id="confirm_new_password"
                                    className="input-field pl-10 pr-10 w-full"
                                    placeholder="Confirm your new password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {errors.confirm_new_password && (
                                <p className="mt-1 text-sm text-danger-400">{errors.confirm_new_password.message}</p>
                            )}
                        </div>

                        {/* Password Requirements */}
                        <div className="p-3 bg-dark-800/50 rounded-lg">
                            <p className="text-xs text-gray-400 mb-2">Password requirements:</p>
                            <ul className="text-xs text-gray-400 space-y-1">
                                <li>• At least 8 characters long</li>
                                <li>• Contains uppercase and lowercase letters</li>
                                <li>• Contains numbers and special characters</li>
                            </ul>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="btn-primary w-full py-3 text-base font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <div className="flex items-center justify-center">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                                    Resetting password...
                                </div>
                            ) : (
                                'Reset Password'
                            )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="my-6 flex items-center">
                        <div className="flex-1 border-t border-dark-600"></div>
                        <span className="px-3 text-sm text-gray-400">or</span>
                        <div className="flex-1 border-t border-dark-600"></div>
                    </div>

                    {/* Back to Login */}
                    <div className="text-center">
                        <Link
                            to="/login"
                            className="btn-outline w-full py-3 text-base font-medium inline-flex items-center justify-center gap-2"
                        >
                            <ArrowLeft size={18} />
                            Back to Login
                        </Link>
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
};

export default ResetPassword;

