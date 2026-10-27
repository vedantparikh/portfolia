import { Link } from "react-router";
import { useAuth } from "../contexts/AuthContext";

export default function NotFound() {
  const { isAuthenticated } = useAuth();
  const to = isAuthenticated ? "/dashboard" : "/login";
  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-100">Page not found</h1>
        <Link to={to} className="inline-block mt-4 text-primary-400">
          {isAuthenticated ? "Back to dashboard" : "Back to login"}
        </Link>
      </div>
    </div>
  );
}
