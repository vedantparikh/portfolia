import { createContext, useContext, useEffect, useRef } from "react";

const ShellContext = createContext(null);

export function useShell() {
  const shell = useContext(ShellContext);
  if (!shell) {
    throw new Error("useShell must be used inside the protected layout");
  }
  return shell;
}

const emptyData = {
  portfolios: [],
  selectedPortfolio: null,
  searchQuery: "",
};

export function usePageChrome({
  portfolios = emptyData.portfolios,
  selectedPortfolio = null,
  searchQuery = "",
  onPortfolioChange,
  onSearchChange,
  onQuickAction,
} = {}) {
  const { callbacks, setData } = useShell();
  const handlers = useRef({});
  handlers.current = { onPortfolioChange, onSearchChange, onQuickAction };

  useEffect(() => {
    callbacks.current = {
      onPortfolioChange: (portfolio) =>
        handlers.current.onPortfolioChange?.(portfolio),
      onSearchChange: (value) => handlers.current.onSearchChange?.(value),
      onQuickAction: (action) => handlers.current.onQuickAction?.(action),
    };
    return () => {
      callbacks.current = {
        onPortfolioChange: () => {},
        onSearchChange: () => {},
        onQuickAction: () => {},
      };
    };
  }, [callbacks]);

  useEffect(() => {
    setData({ portfolios, selectedPortfolio, searchQuery });
  }, [setData, portfolios, selectedPortfolio, searchQuery]);

  useEffect(() => {
    return () => setData(emptyData);
  }, [setData]);
}

export { ShellContext };
