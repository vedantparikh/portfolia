import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, Lock, User, Mail, UserCheck, AlertCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

const Register = () => {
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const { register: registerUser, isLoading, error, clearError } = useAuth();
    const navigate = useNavigate();

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm();

    const password = watch('password');

    const onSubmit = async (data) => {
        clearError();
        const result = await registerUser(data);

        if (result.success) {
            toast.success('Registration successful! Please log in.');
            navigate('/login');
        } else {
            toast.error(result.error || 'Registration failed');
        }
    };

    return (
        <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Logo/Brand */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gradient mb-2">Portfolia</h1>
                    <p className="text-gray-400">Your Professional Portfolio Management Platform</p>
                </div>

                {/* Register Card */}
                <div className="card p-8 animate-fade-in">
                    <div className="text-center mb-6">
                        <h2 className="text-2xl font-semibold text-gray-100 mb-2">Create Account</h2>
                        <p className="text-gray-400">Join thousands of traders and investors</p>
                    </div>

                    {/* Error Display */}
                    {error && (
                        <div className="mb-4 p-3 bg-danger-900/20 border border-danger-700 rounded-lg flex items-center gap-2 text-danger-400">
                            <AlertCircle size={16} />
                            <span className="text-sm">{error}</span>
                        </div>
                    )}

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        {/* First Name Field */}
                        <div>
                            <label htmlFor="first_name" className="block text-sm font-medium text-gray-300 mb-2">
                                First Name
                            </label>
                            <div className="relative">
                                <UserCheck className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('first_name', {
                                        required: 'First name is required',
                                        maxLength: {
                                            value: 100,
                                            message: 'First name must be less than 100 characters',
                                        },
                                    })}
                                    type="text"
                                    id="first_name"
                                    className="input-field pl-10 w-full"
                                    placeholder="Enter your first name"
                                />
                            </div>
                            {errors.first_name && (
                                <p className="mt-1 text-sm text-danger-400">{errors.first_name.message}</p>
                            )}
                        </div>

                        {/* Last Name Field */}
                        <div>
                            <label htmlFor="last_name" className="block text-sm font-medium text-gray-300 mb-2">
                                Last Name
                            </label>
                            <div className="relative">
                                <UserCheck className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('last_name', {
                                        required: 'Last name is required',
                                        maxLength: {
                                            value: 100,
                                            message: 'Last name must be less than 100 characters',
                                        },
                                    })}
                                    type="text"
                                    id="last_name"
                                    className="input-field pl-10 w-full"
                                    placeholder="Enter your last name"
                                />
                            </div>
                            {errors.last_name && (
                                <p className="mt-1 text-sm text-danger-400">{errors.last_name.message}</p>
                            )}
                        </div>

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

                        {/* Username Field */}
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
                                Username
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('username', {
                                        required: 'Username is required',
                                        minLength: {
                                            value: 3,
                                            message: 'Username must be at least 3 characters',
                                        },
                                        maxLength: {
                                            value: 50,
                                            message: 'Username must be less than 50 characters',
                                        },
                                        pattern: {
                                            value: /^[a-zA-Z0-9]+$/,
                                            message: 'Username must contain only alphanumeric characters',
                                        },
                                    })}
                                    type="text"
                                    id="username"
                                    className="input-field pl-10 w-full"
                                    placeholder="Choose a username"
                                />
                            </div>
                            {errors.username && (
                                <p className="mt-1 text-sm text-danger-400">{errors.username.message}</p>
                            )}
                        </div>

                        {/* Password Field */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('password', {
                                        required: 'Password is required',
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
                                    id="password"
                                    className="input-field pl-10 pr-10 w-full"
                                    placeholder="Create a strong password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {errors.password && (
                                <p className="mt-1 text-sm text-danger-400">{errors.password.message}</p>
                            )}
                        </div>

                        {/* Confirm Password Field */}
                        <div>
                            <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-300 mb-2">
                                Confirm Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                <input
                                    {...register('confirm_password', {
                                        required: 'Please confirm your password',
                                        validate: (value) => value === password || 'Passwords do not match',
                                    })}
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    id="confirm_password"
                                    className="input-field pl-10 pr-10 w-full"
                                    placeholder="Confirm your password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {errors.confirm_password && (
                                <p className="mt-1 text-sm text-danger-400">{errors.confirm_password.message}</p>
                            )}
                        </div>

                        {/* Terms and Conditions */}
                        <div className="flex items-start">
                            <input
                                type="checkbox"
                                id="terms"
                                className="mt-1 rounded-sm border-dark-600 text-primary-600 focus:ring-primary-500 bg-dark-800"
                                {...register('terms', {
                                    required: 'You must accept the terms and conditions',
                                })}
                            />
                            <label htmlFor="terms" className="ml-2 text-sm text-gray-300">
                                I agree to the{' '}
                                <Link to="/terms" className="text-primary-400 hover:text-primary-300">
                                    Terms and Conditions
                                </Link>{' '}
                                and{' '}
                                <Link to="/privacy" className="text-primary-400 hover:text-primary-300">
                                    Privacy Policy
                                </Link>
                            </label>
                        </div>
                        {errors.terms && (
                            <p className="mt-1 text-sm text-danger-400">{errors.terms.message}</p>
                        )}

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="btn-primary w-full py-3 text-base font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <div className="flex items-center justify-center">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                                    Creating account...
                                </div>
                            ) : (
                                'Create Account'
                            )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="my-6 flex items-center">
                        <div className="flex-1 border-t border-dark-600"></div>
                        <span className="px-3 text-sm text-gray-400">or</span>
                        <div className="flex-1 border-t border-dark-600"></div>
                    </div>

                    {/* Login Link */}
                    <div className="text-center">
                        <p className="text-gray-400">
                            Already have an account?{' '}
                            <Link
                                to="/login"
                                className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
                            >
                                Sign in
                            </Link>
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
};

export default Register;

