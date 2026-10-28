import { useQuery } from "@tanstack/react-query";

import { marketAPI } from "../../shared/api/market";
import { portfolioAPI, portfolioCalculationsAPI } from "../portfolio/api";

interface Holding {
  symbol: string;
  today_pnl_percent: number | null;
}

interface Portfolio {
  id: number;
}

export const dashboardKeys = {
  cards: ["portfolios", "dashboard", "cards"] as const,
  movers: ["portfolios", "dashboard", "movers"] as const,
  overview: ["portfolios", "dashboard", "overview"] as const,
  marketStatus: ["market", "status"] as const,
};

const settled = <T>(result: PromiseSettledResult<T>, fallback: T): T =>
  result.status === "fulfilled" ? result.value : fallback;

export function usePortfolioCards() {
  return useQuery({
    queryKey: dashboardKeys.cards,
    queryFn: async () => {
      const portfolios: Portfolio[] = await portfolioAPI.getPortfolios();
      if (!portfolios || portfolios.length === 0) return [];
      const [summaries, histories] = await Promise.all([
        Promise.allSettled(
          portfolios.map((p) => portfolioAPI.getPortfolioSummary(p.id)),
        ),
        Promise.allSettled(
          portfolios.map((p) =>
            portfolioCalculationsAPI.getPerformanceSeries(p.id, "3m"),
          ),
        ),
      ]);
      return portfolios.map((portfolio, index) => ({
        ...portfolio,
        stats: settled(summaries[index], null),
        history: settled<{ points: { value: number }[] } | null>(
          histories[index],
          null,
        )?.points.map((p) => p.value) ?? [],
      }));
    },
  });
}

export function useMovers() {
  return useQuery({
    queryKey: dashboardKeys.movers,
    queryFn: async () => {
      try {
        const portfolios: Portfolio[] = await portfolioAPI.getPortfolios();
        const results = await Promise.allSettled(
          portfolios.map((p) => portfolioAPI.getPortfolioHoldings(p.id)),
        );
        const bySymbol = new Map<string, Holding>();
        results
          .flatMap((r): Holding[] => settled(r, []) || [])
          .filter((h) => h.today_pnl_percent != null)
          .forEach((h) => bySymbol.set(h.symbol, h));
        const sorted = [...bySymbol.values()].sort(
          (a, b) => b.today_pnl_percent! - a.today_pnl_percent!,
        );
        return {
          gainers: sorted.filter((h) => h.today_pnl_percent! > 0).slice(0, 3),
          losers: sorted
            .filter((h) => h.today_pnl_percent! < 0)
            .reverse()
            .slice(0, 3),
        };
      } catch (error) {
        console.error("Failed to load movers:", error);
        return { gainers: [], losers: [] };
      }
    },
  });
}

export function useStatisticsOverview() {
  return useQuery({
    queryKey: dashboardKeys.overview,
    queryFn: () => portfolioAPI.getStatisticsOverview().catch(() => null),
  });
}

export function useMarketStatus() {
  return useQuery({
    queryKey: dashboardKeys.marketStatus,
    queryFn: () => marketAPI.getMarketStatus().catch(() => null),
  });
}
