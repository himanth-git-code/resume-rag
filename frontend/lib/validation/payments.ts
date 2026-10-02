import { z } from "zod";

export const productSchema = z.object({
  code: z.string(),
  name: z.string(),
  description: z.string(),
  price_amount: z.number(),
  currency: z.string(),
  entitlements: z.array(z.string()),
  features: z.array(z.string()),
});

export const paymentStatusSchema = z.enum(["pending", "initiated", "successful", "failed", "refunded", "cancelled"]);

export const paymentSchema = z.object({
  id: z.string(),
  product: z.string(),
  product_name: z.string(),
  provider: z.string(),
  amount: z.number(),
  currency: z.string(),
  status: paymentStatusSchema,
  refunded_amount: z.number(),
  failure_reason: z.string(),
  paid_at: z.string().nullable(),
  created_at: z.string(),
});

export const paymentListSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(paymentSchema),
});

export const checkoutSchema = z.object({
  payment: paymentSchema,
  provider: z.enum(["razorpay", "fake"]),
  checkout: z.object({
    key: z.string().nullable(),
    order_id: z.string(),
    amount: z.number(),
    currency: z.string(),
    name: z.string(),
    prefill: z.object({ email: z.string() }),
  }),
});

export const entitlementsSchema = z.object({ codes: z.array(z.string()), provider: z.string() });

/** Smallest currency unit (paise) to a display price, e.g. 49900 INR -> "₹499". */
export function formatMoney(amount: number, currency: string): string {
  const value = amount / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
}

/** Statuses the backend won't change again on its own while the buyer waits. */
export const isSettled = (status: z.infer<typeof paymentStatusSchema>) =>
  status === "successful" || status === "failed" || status === "refunded";

/** Keep polling a payment? A cancelled checkout can still be captured late, so watch it briefly. */
export function shouldPoll(payment: { status: z.infer<typeof paymentStatusSchema>; created_at: string }, now = Date.now()): boolean {
  if (isSettled(payment.status)) return false;
  if (payment.status === "cancelled") return now - new Date(payment.created_at).getTime() < 5 * 60_000;
  return true;
}

export const PAYMENT_STATUS_LABEL: Record<z.infer<typeof paymentStatusSchema>, string> = {
  pending: "Pending",
  initiated: "Awaiting payment",
  successful: "Paid",
  failed: "Failed",
  refunded: "Refunded",
  cancelled: "Cancelled",
};
