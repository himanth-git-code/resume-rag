import type { z } from "zod";

import type { authConfigSchema, credentialsSchema, sessionSchema } from "@/lib/validation/auth";

export type Credentials = z.infer<typeof credentialsSchema>;
export type Session = z.infer<typeof sessionSchema>;
export type AuthConfig = z.infer<typeof authConfigSchema>;

/** A validation or auth error mapped to a form field ("form" when not field-specific). */
export type FieldErrors = Partial<Record<keyof Credentials | "form", string>>;
