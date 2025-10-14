/**
 * AUTH CONTEXT - AUTHENTICATION STATE MANAGEMENT
 * 
 * This file manages the authentication state for the entire application.
 * It provides login, logout, registration, and user state to all components.
 * 
 * What this file does:
 * 1. Creates a React Context for sharing authentication state
 * 2. Manages user login/logout state
 * 3. Handles token storage and refresh
 * 4. Provides authentication functions to all components
 * 5. Automatically checks if user is logged in on app startup
 * 
 * Key React concepts for beginners:
 * - Context: A way to share data between components without passing props
 * - useReducer: A hook for managing complex state with actions
 * - useEffect: A hook that runs code when component mounts or state changes
 * - Provider: A component that provides context data to child components
 * - Custom Hook: A function that uses React hooks and can be reused
 */

// Import React hooks for state management and side effects
import React, { createContext, useContext, useEffect, useReducer } from 'react';

// Import our API service for authentication calls
import { authAPI } from '../services/api';

/* 
  ACTION TYPES - Constants for different state changes
  These are like "commands" that tell the reducer what to do
  Using constants prevents typos and makes code more maintainable
*/
const AUTH_ACTIONS = {
    LOGIN_START: 'LOGIN_START',           // User started logging in
    LOGIN_SUCCESS: 'LOGIN_SUCCESS',       // Login completed successfully
    LOGIN_FAILURE: 'LOGIN_FAILURE',       // Login failed
    LOGOUT: 'LOGOUT',                     // User logged out
    REGISTER_START: 'REGISTER_START',     // User started registering
    REGISTER_SUCCESS: 'REGISTER_SUCCESS', // Registration completed successfully
    REGISTER_FAILURE: 'REGISTER_FAILURE', // Registration failed
    SET_USER: 'SET_USER',                 // Set user data
    SET_PROFILE: 'SET_PROFILE',           // Set user profile data
    CLEAR_ERROR: 'CLEAR_ERROR',           // Clear error messages
    VERIFY_EMAIL_SUCCESS: 'VERIFY_EMAIL_SUCCESS',           // Email verified
    RESEND_VERIFICATION_SUCCESS: 'RESEND_VERIFICATION_SUCCESS', // Verification email sent
};

/* 
  INITIAL STATE - The starting state of our authentication
  This is what the state looks like when the app first loads
*/
const initialState = {
    user: null,              // User data (null when not logged in)
    isAuthenticated: false,  // Whether user is logged in
    isLoading: false,        // Whether an API call is in progress
    error: null,             // Error message if something went wrong
    isInitialized: false,    // Whether we've checked if user is logged in
};

/* 
  REDUCER FUNCTION - Handles state changes based on actions
  This is like a "state machine" that takes the current state and an action,
  then returns the new state. It's the only way to change state in our app.
  
  Key concepts:
  - state: The current authentication state
  - action: An object with type and payload that describes what to do
  - ...state: Spread operator that copies all existing state properties
  - action.payload: Data sent with the action (like user data or error message)
*/
const authReducer = (state, action) => {
    switch (action.type) {
        // User started logging in - show loading spinner
        case AUTH_ACTIONS.LOGIN_START:
            return {
                ...state,        // Keep all existing state
                isLoading: true, // Start loading
                error: null,     // Clear any previous errors
            };
        
        // Login completed successfully - set user data
        case AUTH_ACTIONS.LOGIN_SUCCESS:
            return {
                ...state,
                user: action.payload.user,  // Set user data from API response
                isAuthenticated: true,      // Mark as logged in
                isLoading: false,           // Stop loading
                error: null,                // Clear any errors
            };
        
        // Login failed - show error message
        case AUTH_ACTIONS.LOGIN_FAILURE:
            return {
                ...state,
                isLoading: false,           // Stop loading
                error: action.payload,      // Set error message
                isAuthenticated: false,     // Mark as not logged in
            };
        
        // User logged out - clear all user data
        case AUTH_ACTIONS.LOGOUT:
            return {
                ...state,
                user: null,                 // Clear user data
                isAuthenticated: false,     // Mark as not logged in
                isLoading: false,           // Stop loading
                error: null,                // Clear errors
            };
        
        // User started registering - show loading spinner
        case AUTH_ACTIONS.REGISTER_START:
            return {
                ...state,
                isLoading: true,            // Start loading
                error: null,                // Clear any previous errors
            };
        
        // Registration completed successfully
        case AUTH_ACTIONS.REGISTER_SUCCESS:
            return {
                ...state,
                isLoading: false,           // Stop loading
                error: null,                // Clear any errors
            };
        
        // Registration failed - show error message
        case AUTH_ACTIONS.REGISTER_FAILURE:
            return {
                ...state,
                isLoading: false,           // Stop loading
                error: action.payload,      // Set error message
            };
        
        // Set user data (used when checking if already logged in)
        case AUTH_ACTIONS.SET_USER:
            return {
                ...state,
                user: action.payload,                    // Set user data
                isAuthenticated: !!action.payload,       // True if user exists, false if null
                isInitialized: true,                     // Mark as initialized
            };
        
        // Set user profile data
        case AUTH_ACTIONS.SET_PROFILE:
            return {
                ...state,
                profile: action.payload,                 // Set profile data
                isAuthenticated: !!action.payload,       // True if profile exists
                isInitialized: true,                     // Mark as initialized
            };
        
        // Clear error messages
        case AUTH_ACTIONS.CLEAR_ERROR:
            return {
                ...state,
                error: null,                // Clear error message
            };
        
        // Email verification successful - mark user as verified
        case AUTH_ACTIONS.VERIFY_EMAIL_SUCCESS:
            return {
                ...state,
                // Update user object to mark email as verified
                user: state.user ? { ...state.user, is_verified: true } : null,
            };
        
        // Verification email sent successfully
        case AUTH_ACTIONS.RESEND_VERIFICATION_SUCCESS:
            return {
                ...state,
                // No state change needed for resend, just success feedback
            };
        
        // Unknown action - return current state unchanged
        default:
            return state;
    }
};

/* 
  CREATE CONTEXT - Creates a React Context for sharing authentication state
  Context is like a "global variable" that any component can access
  We don't provide a default value, so it will be undefined until we use the Provider
*/
const AuthContext = createContext();

/* 
  AUTH PROVIDER COMPONENT - Wraps the entire app to provide authentication state
  This component manages the authentication state and provides it to all child components
  
  Props:
  - children: All the child components that will have access to auth state
*/
export const AuthProvider = ({ children }) => {
    /* 
      USEREDUCER HOOK - Manages complex state with actions
      - state: Current authentication state
      - dispatch: Function to send actions to the reducer
      - authReducer: Our reducer function that handles state changes
      - initialState: Starting state when component first mounts
    */
    const [state, dispatch] = useReducer(authReducer, initialState);

    /* 
      USEEFFECT HOOK - Runs code when component mounts
      This checks if the user is already logged in when the app starts
      The empty dependency array [] means it only runs once when component mounts
    */
    useEffect(() => {
        /* 
          INITIALIZE AUTH - Check if user is already logged in
          This function runs when the app first loads to see if there's a saved login
        */
        const initializeAuth = async () => {
            try {
                // Check if there's a saved access token in browser storage
                const token = localStorage.getItem('access_token');
                if (token) {
                    // If token exists, try to get user data from the server
                    const user = await authAPI.getCurrentUser();
                    const profile = await authAPI.getUserProfile();
                    
                    // Update state with user data
                    dispatch({ type: AUTH_ACTIONS.SET_USER, payload: user });
                    dispatch({ type: AUTH_ACTIONS.SET_PROFILE, payload: profile });
                } else {
                    // No token found, user is not logged in
                    dispatch({ type: AUTH_ACTIONS.SET_USER, payload: null });
                }
            } catch (error) {
                // If getting user data fails, clear everything and log out
                console.error('Failed to initialize auth:', error);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                dispatch({ type: AUTH_ACTIONS.SET_USER, payload: null });
                dispatch({ type: AUTH_ACTIONS.SET_PROFILE, payload: null });
            }
        };

        // Run the initialization function
        initializeAuth();
    }, []); // Empty array means this only runs once when component mounts

    /* 
      LOGIN FUNCTION - Handles user login
      This function is called when a user tries to log in
      
      Parameters:
      - credentials: Object containing username and password
      
      Returns:
      - Object with success boolean and optional error message
    */
    const login = async (credentials) => {
        try {
            // Tell the reducer that login has started (show loading spinner)
            dispatch({ type: AUTH_ACTIONS.LOGIN_START });

            // Send login request to the server
            const response = await authAPI.login(credentials);

            // Save the tokens in browser storage so user stays logged in
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('refresh_token', response.refresh_token);

            // Get user data from the server
            const user = await authAPI.getCurrentUser();
            const profile = await authAPI.getUserProfile();

            // Update state with user data
            dispatch({ type: AUTH_ACTIONS.SET_USER, payload: user });
            dispatch({ type: AUTH_ACTIONS.SET_PROFILE, payload: profile });
            
            // Return success to the calling component
            return { success: true };
        } catch (error) {
            // If login fails, get the error message and update state
            const errorMessage = error.response?.data?.detail || 'Login failed';
            dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: errorMessage });
            return { success: false, error: errorMessage };
        }
    };

    /* 
      REGISTER FUNCTION - Handles user registration
      This function is called when a new user tries to create an account
      
      Parameters:
      - userData: Object containing user registration information
      
      Returns:
      - Object with success boolean and optional error message
    */
    const register = async (userData) => {
        try {
            // Tell the reducer that registration has started
            dispatch({ type: AUTH_ACTIONS.REGISTER_START });

            // Send registration request to the server
            await authAPI.register(userData);

            // Tell the reducer that registration was successful
            dispatch({ type: AUTH_ACTIONS.REGISTER_SUCCESS });
            return { success: true };
        } catch (error) {
            // If registration fails, get the error message and update state
            const errorMessage = error.response?.data?.detail || 'Registration failed';
            dispatch({ type: AUTH_ACTIONS.REGISTER_FAILURE, payload: errorMessage });
            return { success: false, error: errorMessage };
        }
    };

    /* 
      LOGOUT FUNCTION - Handles user logout
      This function is called when a user wants to log out
    */
    const logout = async () => {
        try {
            // Tell the server that user is logging out
            await authAPI.logout();
        } catch (error) {
            // Even if server call fails, we still want to log out locally
            console.error('Logout error:', error);
        } finally {
            // Always clear the local state and tokens
            dispatch({ type: AUTH_ACTIONS.LOGOUT });
        }
    };

    /* 
      CLEAR ERROR FUNCTION - Removes error messages from state
      This function is called when we want to hide error messages
    */
    const clearError = () => {
        dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
    };

    /* 
      VERIFY EMAIL FUNCTION - Handles email verification
      This function is called when a user clicks the verification link in their email
      
      Parameters:
      - token: Verification token from the email link
      
      Returns:
      - Object with success boolean and optional error message
    */
    const verifyEmail = async (token) => {
        try {
            // Send verification request to the server
            const response = await authAPI.verifyEmail(token);
            
            // Update state to mark email as verified
            dispatch({ type: AUTH_ACTIONS.VERIFY_EMAIL_SUCCESS });
            return { success: true, message: response.message };
        } catch (error) {
            // If verification fails, return error message
            const errorMessage = error.response?.data?.detail || 'Email verification failed';
            return { success: false, error: errorMessage };
        }
    };

    /* 
      RESEND VERIFICATION FUNCTION - Sends a new verification email
      This function is called when a user wants to resend their verification email
      
      Returns:
      - Object with success boolean and optional error message
    */
    const resendVerification = async () => {
        try {
            // Send resend request to the server
            const response = await authAPI.resendVerification();
            
            // Update state (no state change needed, just success feedback)
            dispatch({ type: AUTH_ACTIONS.RESEND_VERIFICATION_SUCCESS });
            return { success: true, message: response.message };
        } catch (error) {
            // If resend fails, return error message
            const errorMessage = error.response?.data?.detail || 'Failed to resend verification email';
            return { success: false, error: errorMessage };
        }
    };

    const refreshUser = async () => {
        try {
            console.log("Attempting to refresh user data...");
            // Re-fetch the user and profile from your backend
            const user = await authAPI.getCurrentUser();
            const profile = await authAPI.getUserProfile();

            // Dispatch actions to update the state with the latest data
            dispatch({ type: AUTH_ACTIONS.SET_USER, payload: user });
            dispatch({ type: AUTH_ACTIONS.SET_PROFILE, payload: profile });
            console.log("User data refreshed successfully.");
        } catch (error) {
            console.error("Failed to refresh user:", error);
            // If the refresh fails (e.g., token expired), you might want to log the user out
            // For now, we'll just log the error.
        }
    };

    /* 
      CONTEXT VALUE - What we provide to all child components
      This object contains all the state and functions that components can use
      The ...state spread operator includes all state properties (user, isAuthenticated, etc.)
    */
    const value = {
        ...state,              // All state properties (user, isAuthenticated, isLoading, error, isInitialized)
        login,                 // Function to log in
        register,              // Function to register new user
        logout,                // Function to log out
        clearError,            // Function to clear error messages
        verifyEmail,           // Function to verify email
        resendVerification,    // Function to resend verification email
        refreshUser,           // Function to refresh user data
    };

    /* 
      PROVIDER COMPONENT - Wraps children and provides context value
      This makes the authentication state and functions available to all child components
    */
    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

/* 
  USE AUTH HOOK - Custom hook to access authentication context
  This is a convenience function that components use to get authentication data
  
  Usage in components:
  const { user, isAuthenticated, login, logout } = useAuth();
  
  Returns:
  - All authentication state and functions
  - Throws error if used outside of AuthProvider
*/
export const useAuth = () => {
    // Get the context value
    const context = useContext(AuthContext);
    
    // If context is undefined, it means we're not inside an AuthProvider
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    
    // Return the context value (state and functions)
    return context;
};

