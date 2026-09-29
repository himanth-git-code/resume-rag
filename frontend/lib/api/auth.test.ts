import { describe, expect, it } from "vitest";

import { toFieldErrors } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

describe("toFieldErrors", () => {
  it("maps allauth errors onto fields, keeping the first message per field", () => {
    const body = {
      status: 400,
      errors: [
        { message: "Enter a valid email address.", code: "invalid", param: "email" },
        { message: "Too short.", code: "password_too_short", param: "password" },
        { message: "Too common.", code: "password_too_common", param: "password" },
      ],
    };
    expect(toFieldErrors(new ApiError("bad", 400, body))).toEqual({
      email: "Enter a valid email address.",
      password: "Too short.",
    });
  });

  it("puts errors without a known field on the form", () => {
    const body = { status: 409, errors: [{ message: "Already signed in.", code: "conflict" }] };
    expect(toFieldErrors(new ApiError("conflict", 409, body))).toEqual({ form: "Already signed in." });
  });

  it("explains a CSRF failure", () => {
    expect(toFieldErrors(new ApiError("forbidden", 403, null)).form).toMatch(/session expired/i);
  });

  it("falls back to a generic message", () => {
    expect(toFieldErrors(new Error("network")).form).toMatch(/something went wrong/i);
  });
});
