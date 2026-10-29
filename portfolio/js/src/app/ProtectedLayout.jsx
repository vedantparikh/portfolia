import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import useIsMobile from "../hooks/useIsMobile";
import Sidebar from "../components/shared/Sidebar";
import LoadingSpinner from "../shared/ui/Spinner";
import ErrorBoundary from "./ErrorBoundary";
import { ShellContext } from "./chrome";

const views = [
  ["/dashboard", "dashboard"],
  ["/portfolio", "portfolio"],
  ["/assets", "assets"],
  ["/transactions", "transactions"],
  ["/watchlist", "watchlist"],
  ["/concepts", "concepts"],
  ["/settings", "settings"],
];

function viewFor(pathname) {
  const match = views.find(([path]) => pathname.startsWith(path));
  return match ? match[1] : "dashboard";
}

export default function ProtectedLayout() {
  const { isAuthenticated, isInitialized } = useAuth();
  const location = useLocation();
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);
  const callbacks = useRef({
    onPortfolioChange: () => {},
    onSearchChange: () => {},
    onQuickAction: () => false,
  });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [data, setData] = useState({
    portfolios: [],
    selectedPortfolio: null,
    searchQuery: "",
  });

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const openSidebar = useCallback(() => setOpen(true), []);
  const closeSidebar = useCallback(() => setOpen(false), []);
  const toggleSidebar = useCallback(() => setOpen((value) => !value), []);

  const runQuickAction = (action) => {
    if (callbacks.current.onQuickAction(action)) return;
    if (action === "create-portfolio") {
      navigate("/portfolio", { state: { action: "createPortfolio" } });
    } else if (action === "create-transaction") {
      navigate("/transactions", { state: { action: "createTransaction" } });
    } else if (action === "refresh") {
      queryClient.invalidateQueries();
    }
  };

  const shell = useMemo(
    () => ({
      callbacks,
      setData,
      isMobile,
      openSidebar,
      closeSidebar,
      toggleSidebar,
    }),
    [isMobile, openSidebar, closeSidebar, toggleSidebar],
  );

  if (!isInitialized) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading..." centered />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <ShellContext.Provider value={shell}>
      <div className="min-h-screen gradient-bg flex">
        {isMobile && open && (
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={closeSidebar}
          />
        )}
        <Sidebar
          currentView={viewFor(location.pathname)}
          portfolios={data.portfolios}
          selectedPortfolio={data.selectedPortfolio}
          searchQuery={data.searchQuery}
          onPortfolioChange={(portfolio) =>
            callbacks.current.onPortfolioChange(portfolio)
          }
          onSearchChange={(value) => callbacks.current.onSearchChange(value)}
          onQuickAction={runQuickAction}
          isMobile={isMobile}
          isOpen={open}
          onClose={closeSidebar}
          onToggleSidebar={toggleSidebar}
        />
        <div className="flex-1 min-w-0 flex flex-col">
          <ErrorBoundary resetKey={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </div>
      </div>
    </ShellContext.Provider>
  );
}
