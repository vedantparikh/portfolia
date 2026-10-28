import { useQuery } from "@tanstack/react-query";

import type { Params } from "../../shared/api/client";
import { accountStatementsAPI, transactionAPI } from "./api";

export const transactionKeys = {
  all: ["transactions"] as const,
  list: ["transactions", "list"] as const,
  recent: (limit: number) => ["transactions", "recent", limit] as const,
  providers: ["account-statements", "providers"] as const,
  // Under the portfolio, so an import (which invalidates portfolios) rechecks it
  imported: (portfolioId: number, rows: Params[]) =>
    ["portfolios", portfolioId, "imported-rows", rows] as const,
};

export function useStatementProviders(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: transactionKeys.providers,
    queryFn: async () =>
      (await accountStatementsAPI.getSupportedProviders()).providers || [],
    enabled: options.enabled ?? true,
    staleTime: Infinity,
  });
}

export function useImportedRows(portfolioId: number | null, rows: Params[]) {
  return useQuery({
    queryKey: transactionKeys.imported(portfolioId ?? 0, rows),
    queryFn: async (): Promise<string[]> =>
      (await accountStatementsAPI.importedTransactions(portfolioId!, rows))
        .imported_keys,
    enabled: portfolioId !== null && rows.length > 0,
  });
}

export function useTransactions() {
  return useQuery({
    queryKey: transactionKeys.list,
    queryFn: () =>
      transactionAPI.getTransactions({
        limit: 10000,
        order_by: "transaction_date",
        order: "desc",
      }),
  });
}

export function useRecentTransactions(limit: number) {
  return useQuery({
    queryKey: transactionKeys.recent(limit),
    queryFn: () =>
      transactionAPI.getTransactions({
        limit,
        order_by: "transaction_date",
        order: "desc",
      }),
  });
}
