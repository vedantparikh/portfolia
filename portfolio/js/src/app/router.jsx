import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";
import LoadingSpinner from "../shared/ui/Spinner";
import NotFound from "./NotFound";
import ProtectedLayout from "./ProtectedLayout";

const Login = lazy(() => import("../features/auth/Login"));
const Register = lazy(() => import("../features/auth/Register"));
const ForgotPassword = lazy(() => import("../features/auth/ForgotPassword"));
const ResetPassword = lazy(() => import("../features/auth/ResetPassword"));
const ValidateResetToken = lazy(
  () => import("../features/auth/ValidateResetToken"),
);
const EmailVerification = lazy(
  () => import("../features/auth/EmailVerification"),
);
const Dashboard = lazy(() => import("../features/dashboard/Dashboard"));
const Watchlist = lazy(() =>
  import("../features/watchlist").then((mod) => ({ default: mod.Watchlist })),
);
const Assets = lazy(() => import("../features/assets/Assets"));
const Portfolio = lazy(() => import("../features/portfolio/Portfolio"));
const Transactions = lazy(
  () => import("../features/transactions/Transactions"),
);
const Settings = lazy(() => import("../features/settings/Settings"));
const FinancialConcepts = lazy(
  () => import("../components/FinancialConcepts"),
);

function PageFallback() {
  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <LoadingSpinner size="lg" text="Loading..." centered />
    </div>
  );
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/validate-reset-token" element={<ValidateResetToken />} />
        <Route path="/verify-email" element={<EmailVerification />} />

        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/concepts" element={<FinancialConcepts />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
