import { describe, expect, it } from "vitest";

import { checkoutSchema, formatMoney, isSettled, shouldPoll } from "@/lib/validation/payments";

describe("formatMoney", () => {
  it("formats paise as rupees", () => {
    expect(formatMoney(49900, "INR")).toBe("₹499");
    expect(formatMoney(49950, "INR")).toBe("₹499.50");
    expect(formatMoney(149900, "INR")).toBe("₹1,499");
  });
});

describe("isSettled", () => {
  it("only stops polling on outcomes the backend won't change by itself", () => {
    expect(isSettled("initiated")).toBe(false);
    expect(isSettled("cancelled")).toBe(false); // a late capture can still arrive
    expect(isSettled("successful")).toBe(true);
    expect(isSettled("failed")).toBe(true);
  });
});

describe("checkoutSchema", () => {
  it("accepts a fake-provider session without a key", () => {
    const parsed = checkoutSchema.parse({
      payment: {
        id: "p1", product: "pro", product_name: "Pro", provider: "fake", amount: 49900, currency: "INR",
        status: "initiated", refunded_amount: 0, failure_reason: "", paid_at: null, created_at: "t",
      },
      provider: "fake",
      checkout: { key: null, order_id: "order_fake_1", amount: 49900, currency: "INR", name: "Pro", prefill: { email: "a@b.co" } },
    });
    expect(parsed.checkout.key).toBeNull();
  });
});

describe("shouldPoll", () => {
  const created = "2026-10-02T10:00:00Z";
  const at = (minutes: number) => new Date(created).getTime() + minutes * 60_000;
  it("watches a cancelled checkout only briefly", () => {
    expect(shouldPoll({ status: "cancelled", created_at: created }, at(1))).toBe(true);
    expect(shouldPoll({ status: "cancelled", created_at: created }, at(10))).toBe(false);
    expect(shouldPoll({ status: "initiated", created_at: created }, at(10))).toBe(true);
    expect(shouldPoll({ status: "successful", created_at: created }, at(0))).toBe(false);
  });
});
