import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, getCsrfToken, request } from "@/lib/api/client";
import { authConfigSchema, authErrorSchema, sessionSchema } from "@/lib/validation/auth";
import type { Credentials, FieldErrors, Session } from "@/types/auth";

// django-allauth headless API ("browser" client, session cookies), proxied by Next.js.
const BASE = "/_allauth/browser/v1";
const SESSION_KEY = ["session"] as const;

function fetchSession(): Promise<Session> {
  // 401 is the normal "signed out" answer, not a failure.
  return request(`${BASE}/auth/session`, sessionSchema, { okStatuses: [401] });
}

export function useSession() {
  const query = useQuery({ queryKey: SESSION_KEY, queryFn: fetchSession, staleTime: 60_000 });
  return {
    ...query,
    isAuthenticated: query.data?.meta.is_authenticated ?? false,
    user: query.data?.data?.user,
  };
}

export function useAuthConfig() {
  return useQuery({
    queryKey: ["auth-config"],
    queryFn: () => request(`${BASE}/config`, authConfigSchema),
    staleTime: Infinity,
  });
}

/** Map allauth's `errors[]` onto form fields. */
export function toFieldErrors(error: unknown): FieldErrors {
  if (error instanceof ApiError) {
    const parsed = authErrorSchema.safeParse(error.body);
    if (parsed.success) {
      const fields: FieldErrors = {};
      for (const { message, param } of parsed.data.errors) {
        const key = param === "email" || param === "password" ? param : "form";
        fields[key] ??= message;
      }
      return fields;
    }
    if (error.status === 403) return { form: "Your session expired. Reload the page and try again." };
  }
  return { form: "Something went wrong. Please try again." };
}

function useAuthMutation(path: "login" | "signup") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: Credentials) => {
      // Ensure the CSRF cookie exists before the first unsafe request.
      if (!getCsrfToken()) await fetchSession();
      return request(`${BASE}/auth/${path}`, sessionSchema, { method: "POST", body: credentials });
    },
    onSuccess: (session) => {
      queryClient.setQueryData(SESSION_KEY, session);
      queryClient.removeQueries({ queryKey: ["me"] });
    },
  });
}

export const useLogin = () => useAuthMutation("login");
export const useSignup = () => useAuthMutation("signup");

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    // Logging out answers 401 ("now signed out").
    mutationFn: () => request(`${BASE}/auth/session`, sessionSchema, { method: "DELETE", okStatuses: [401] }),
    onSuccess: (session) => {
      queryClient.clear();
      queryClient.setQueryData(SESSION_KEY, session);
    },
  });
}

/**
 * Start a provider login (e.g. Google). This must be a real form POST: the
 * backend answers with a redirect to the provider, which a fetch can't follow.
 */
export async function redirectToProvider(provider: string, callbackUrl: string) {
  if (!getCsrfToken()) await fetchSession();

  const form = document.createElement("form");
  form.method = "POST";
  form.action = `${BASE}/auth/provider/redirect`;
  const fields = {
    provider,
    callback_url: callbackUrl,
    process: "login",
    csrfmiddlewaretoken: getCsrfToken() ?? "",
  };
  for (const [name, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}
