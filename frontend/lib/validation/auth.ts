import { z } from "zod";

export const credentialsSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

const userSchema = z.object({
  id: z.number(),
  email: z.string(),
  display: z.string(),
});

/** allauth headless session envelope: 200 when signed in, 401 when not. */
export const sessionSchema = z.object({
  status: z.number(),
  data: z
    .object({
      user: userSchema.optional(),
      flows: z.array(z.object({ id: z.string(), providers: z.array(z.string()).optional() })).optional(),
    })
    .optional(),
  meta: z.object({ is_authenticated: z.boolean() }),
});

/** allauth headless 4xx envelope. */
export const authErrorSchema = z.object({
  status: z.number(),
  errors: z.array(z.object({ message: z.string(), code: z.string(), param: z.string().optional() })),
});

export const authConfigSchema = z.object({
  data: z.object({
    account: z.object({ is_open_for_signup: z.boolean() }),
    socialaccount: z
      .object({ providers: z.array(z.object({ id: z.string(), name: z.string() })) })
      .optional(),
  }),
});
