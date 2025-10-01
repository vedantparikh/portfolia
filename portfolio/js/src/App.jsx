/**
 * APP.JSX - MAIN APPLICATION COMPONENT
 *
 * This is the root component of our entire React application. It acts like the "main controller"
 * that manages the overall structure and routing of our portfolio management app.
 *
 * What this component does:
 * 1. Sets up routing (navigation between different pages)
 * 2. Provides authentication context to all child components
 * 3. Defines all the routes (URLs) in our application
 * 4. Handles protected routes (pages that require login)
 * 5. Sets up global toast notifications
 *
 * Key React concepts for beginners:
 * - Component: A reusable piece of UI (like a function that returns HTML)
 * - JSX: A syntax that lets us write HTML-like code inside JavaScript
 * - Props: Data passed from parent to child components
 * - Context: A way to share data between components without passing props
 * - Router: Handles navigation between different pages/views
 */

// Import React - the core library for building user interfaces
import React from "react";

// Import Toaster from react-hot-toast - this shows popup notifications to users
import { Toaster } from "react-hot-toast";

// Import routing components from react-router-dom - this handles page navigation
// - Navigate: Redirects users to different pages
// - Route: Defines a single route (URL path)
// - BrowserRouter: Provides routing functionality (wraps our entire app)
// - Routes: Container for all our routes
import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
} from "react-router-dom";

// Import main feature components
import Assets from "./components/assets/Assets"; // Page for viewing market assets
import Dashboard from "./components/dashboard/Dashboard"; // Main dashboard page
import FinancialConcepts from "./components/FinancialConcepts"; // Financial concepts guide page
import Portfolio from "./components/portfolio/Portfolio"; // Portfolio management page
import Transactions from "./components/transactions/Transactions"; // Transaction history page
import { Watchlist } from "./components/watchlist"; // Watchlist management page

// Import authentication-related components
import EmailVerification from "./components/auth/EmailVerification"; // Email verification page
import ForgotPassword from "./components/auth/ForgotPassword"; // Forgot password page
import Login from "./components/auth/Login"; // Login page
import ProtectedRoute from "./components/auth/ProtectedRoute"; // Wrapper for pages requiring login
import Register from "./components/auth/Register"; // Registration page
import ResetPassword from "./components/auth/ResetPassword"; // Password reset page
import ValidateResetToken from "./components/auth/ValidateResetToken"; // Token validation page

// Import AuthProvider - this provides authentication state to all components
import { AuthProvider } from "./contexts/AuthContext";

/**
 * App Component Function
 *
 * This is the main function component that returns our entire application structure.
 * In React, components are functions that return JSX (HTML-like syntax).
 */
function App() {
  return (
    // AuthProvider wraps our entire app to provide authentication state to all components
    // This is called "Context" in React - it allows any component to access user login status
    <AuthProvider>
      {/* Router enables navigation between different pages/URLs */}
      <Router>
        {/* Main container div with CSS class for styling */}
        <div className="App">
          {/* Routes container - defines all the different pages in our app */}
          <Routes>
            {/* 
              PUBLIC ROUTES - These pages can be accessed without logging in
              Anyone can visit these URLs without authentication
            */}

            {/* Login page - where users enter their username and password */}
            <Route path="/login" element={<Login />} />

            {/* Registration page - where new users create accounts */}
            <Route path="/register" element={<Register />} />

            {/* Forgot password page - where users request password reset */}
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Password reset page - where users enter new password */}
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Token validation page - validates password reset tokens */}
            <Route
              path="/validate-reset-token"
              element={<ValidateResetToken />}
            />

            {/* Email verification page - where users verify their email */}
            <Route path="/verify-email" element={<EmailVerification />} />

            {/* 
              PROTECTED ROUTES - These pages require users to be logged in
              ProtectedRoute component checks if user is authenticated
              If not logged in, user gets redirected to login page
            */}

            {/* Main dashboard - the home page after login */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />

            {/* Watchlist page - where users manage their stock watchlists */}
            <Route
              path="/watchlist"
              element={
                <ProtectedRoute>
                  <Watchlist />
                </ProtectedRoute>
              }
            />

            {/* Assets page - where users browse market assets/stocks */}
            <Route
              path="/assets"
              element={
                <ProtectedRoute>
                  <Assets />
                </ProtectedRoute>
              }
            />

            {/* Portfolio page - where users manage their investment portfolios */}
            <Route
              path="/portfolio"
              element={
                <ProtectedRoute>
                  <Portfolio />
                </ProtectedRoute>
              }
            />

            {/* Transactions page - where users view their transaction history */}
            <Route
              path="/transactions"
              element={
                <ProtectedRoute>
                  <Transactions />
                </ProtectedRoute>
              }
            />

            {/* Financial Concepts page - comprehensive guide to financial metrics */}
            <Route
              path="/concepts"
              element={
                <ProtectedRoute>
                  <FinancialConcepts />
                </ProtectedRoute>
              }
            />

            {/* 
              ROOT ROUTE - When someone visits the main URL (like "localhost:3000/")
              This automatically redirects them to the dashboard if they're logged in,
              or to the login page if they're not logged in
            */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Navigate to="/dashboard" replace />
                </ProtectedRoute>
              }
            />

            {/* 
              CATCH-ALL ROUTE - If someone visits a URL that doesn't exist,
              this redirects them back to the root route
              The "*" means "any other path not defined above"
            */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>

        {/* 
          TOAST NOTIFICATIONS - Global popup messages that appear to users
          These show success messages, errors, and other notifications
          The Toaster component is placed outside the main app div so it appears on top of everything
        */}
        <Toaster
          position="top-right" // Position notifications in the top-right corner
          toastOptions={{
            duration: 4000, // How long notifications stay visible (4 seconds)
            style: {
              background: "#1e293b", // Dark background color
              color: "#f1f5f9", // Light text color
              border: "1px solid #475569", // Border color
            },
            // Success notification styling (green theme)
            success: {
              iconTheme: {
                primary: "#22c55e", // Green color for success icon
                secondary: "#f1f5f9", // Light color for icon background
              },
            },
            // Error notification styling (red theme)
            error: {
              iconTheme: {
                primary: "#ef4444", // Red color for error icon
                secondary: "#f1f5f9", // Light color for icon background
              },
            },
          }}
        />
      </Router>
    </AuthProvider>
  );
}

// Export the App component so it can be imported by other files
// This is how we make this component available to be used in index.jsx
export default App;
