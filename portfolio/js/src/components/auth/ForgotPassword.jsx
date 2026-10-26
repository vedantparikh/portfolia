import { useState } from 'react';
import { Link } from 'react-router';
import { useForm } from 'react-hook-form';
import { Mail, CheckCircle, ArrowLeft } from 'lucide-react';
import { apiErrorMessage, authAPI } from '../../services/api';
import toast from 'react-hot-toast';

const ForgotPassword = () => {
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm();

    const onSubmit = async (data) => {
        setIsLoading(true);
        try {
            await authAPI.forgotPassword(data.email);
            setIsSubmitted(true);
            toast.success('Password reset email sent successfully!');
        } catch (error) {
            const errorMessage = apiErrorMessage(error, 'Failed to send reset email');
            toast.error(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

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
                            <h2 className="text-2xl font-semibold text-gray-100 mb-2">Check Your Email</h2>
                            <p className="text-gray-400">
                                We&apos;ve sent a password reset link to your email address. Please check your inbox and click the link to reset your password.
                            </p>
                            <p className="text-xs text-gray-500 mt-2">
                                The link will redirect you to our secure password reset form.
                            </p>
                        </div>

                        <div className="space-y-4">
                            <Link
                                to="/login"
                                className="btn-primary w-full py-3 text-base font-medium inline-flex items-center justify-center gap-2"
                            >
                                <ArrowLeft size={18} />
                                Back to Login
                            </Link>

                            <p className="text-sm text-gray-400">
                                Didn&apos;t receive the email?{' '}
                                <button
                                    onClick={() => setIsSubmitted(false)}
                                    className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
                                >
                                    Try again
                                </button>
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

                {/* Forgot Password Card */}
                <div className="card p-8 animate-fade-in">
                    <div className="text-center mb-6">
                        <h2 className="text-2xl font-semibold text-gray-100 mb-2">Forgot Password?</h2>
                        <p className="text-gray-400">
                            Enter your email address and we&apos;ll send you a link to reset your password.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        {/* Email Field */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                Email Address
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('email', {
                                        required: 'Email is required',
                                        pattern: {
                                            value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                                            message: 'Invalid email address',
                                        },
                                    })}
                                    type="email"
                                    id="email"
                                    className="input-field pl-10 w-full"
                                    placeholder="Enter your email address"
                                />
                            </div>
                            {errors.email && (
                                <p className="mt-1 text-sm text-danger-400">{errors.email.message}</p>
                            )}
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
                                    Sending reset email...
                                </div>
                            ) : (
                                'Send Reset Link'
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

export default ForgotPassword;

