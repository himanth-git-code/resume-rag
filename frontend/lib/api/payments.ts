import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiGet, apiSend } from "@/lib/api/client";
import {
  checkoutSchema,
  entitlementsSchema,
  isSettled,
  paymentListSchema,
  paymentSchema,
  productSchema,
  shouldPoll,
} from "@/lib/validation/payments";

export function useProducts() {
  return useQuery({ queryKey: ["products"], queryFn: () => apiGet("/payments/products", z.array(productSchema)) });
}

export function useEntitlements() {
  return useQuery({ queryKey: ["entitlements"], queryFn: () => apiGet("/payments/entitlements", entitlementsSchema) });
}

export function usePaymentHistory() {
  return useQuery({ queryKey: ["payments"], queryFn: () => apiGet("/payments", paymentListSchema) });
}

/** Poll a payment until the backend settles it (webhook or reconciliation). */
export function usePaymentStatus(id: string | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["payment", id],
    enabled: id !== null,
    queryFn: async () => {
      const payment = await apiGet(`/payments/${encodeURIComponent(id!)}`, paymentSchema);
      if (isSettled(payment.status)) {
        queryClient.invalidateQueries({ queryKey: ["entitlements"] });
        queryClient.invalidateQueries({ queryKey: ["payments"] });
        queryClient.invalidateQueries({ queryKey: ["me"] });
        queryClient.invalidateQueries({ queryKey: ["website"] });
      }
      return payment;
    },
    refetchInterval: (q) => (!q.state.data || shouldPoll(q.state.data) ? 3_000 : false),
  });
}

export function useCheckout() {
  return useMutation({
    mutationFn: (product: string) => apiSend("POST", "/payments/checkout", checkoutSchema, { product }),
  });
}

export function useCancelPayment() {
  return useMutation({ mutationFn: (id: string) => apiSend("POST", `/payments/${encodeURIComponent(id)}/cancel`, paymentSchema) });
}

export function useSimulatePayment() {
  return useMutation({
    mutationFn: ({ id, outcome }: { id: string; outcome: "success" | "failure" }) =>
      apiSend("POST", `/payments/${encodeURIComponent(id)}/simulate`, paymentSchema, { outcome }),
  });
}
