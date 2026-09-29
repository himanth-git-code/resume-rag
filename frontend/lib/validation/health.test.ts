import { describe, expect, it } from "vitest";

import { healthSchema } from "@/lib/validation/health";

describe("healthSchema", () => {
  it("accepts a healthy report", () => {
    const report = { status: "ok", database: "ok", redis: "ok" };
    expect(healthSchema.parse(report)).toEqual(report);
  });

  it("accepts a degraded report", () => {
    const report = { status: "error", database: "ok", redis: "error" };
    expect(healthSchema.parse(report)).toEqual(report);
  });

  it("rejects unexpected shapes", () => {
    expect(healthSchema.safeParse({ status: "ok" }).success).toBe(false);
    expect(healthSchema.safeParse({ status: "up", database: "ok", redis: "ok" }).success).toBe(
      false,
    );
  });
});
