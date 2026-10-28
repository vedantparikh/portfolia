import { useQuery } from "@tanstack/react-query";

import { transactionAPI } from "./api";

export const transactionKeys = {
  all: ["transactions"] as const,
  list: ["transactions", "list"] as const,
  recent: (limit: number) => ["transactions", "recent", limit] as const,
};

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
