"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { redirectToProvider, toFieldErrors, useAuthConfig, useLogin, useSignup } from "@/lib/api/auth";
import { safeNext } from "@/lib/navigation";
import { credentialsSchema } from "@/lib/validation/auth";
import type { FieldErrors } from "@/types/auth";

type Mode = "login" | "signup";

const COPY = {
  login: {
    title: "Sign in",
    description: "Welcome back.",
    submit: "Sign in",
    pending: "Signing in…",
    switchText: "New here?",
    switchLink: { href: "/signup", label: "Create an account" },
  },
  signup: {
    title: "Create your account",
    description: "Start building your professional identity.",
    submit: "Create account",
    pending: "Creating account…",
    switchText: "Already have an account?",
    switchLink: { href: "/login", label: "Sign in" },
  },
} as const;

export function AuthForm({ mode }: { mode: Mode }) {
  const copy = COPY[mode];
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNext(searchParams.get("next"));

  const login = useLogin();
  const signup = useSignup();
  const mutation = mode === "login" ? login : signup;
  const { data: config } = useAuthConfig();
  const providers = config?.data.socialaccount?.providers ?? [];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>(
    searchParams.get("error") === "social" ? { form: "Sign-in with Google didn't complete. Please try again." } : {},
  );

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = credentialsSchema.safeParse({ email, password });
    if (!parsed.success) {
      const fieldErrors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0] as "email" | "password";
        fieldErrors[key] ??= issue.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    try {
      await mutation.mutateAsync(parsed.data);
      router.replace(next);
    } catch (error) {
      setErrors(toFieldErrors(error));
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>{copy.title}</CardTitle>
        <CardDescription>{copy.description}</CardDescription>
      </CardHeader>

      <CardContent className="grid gap-4">
        {errors.form && (
          <Alert variant="destructive">
            <AlertDescription>{errors.form}</AlertDescription>
          </Alert>
        )}

        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "email-error" : undefined}
            />
            {errors.email && (
              <p id="email-error" className="text-sm text-destructive">
                {errors.email}
              </p>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "password-error" : undefined}
            />
            {errors.password && (
              <p id="password-error" className="text-sm text-destructive">
                {errors.password}
              </p>
            )}
          </div>

          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? copy.pending : copy.submit}
          </Button>
        </form>

        {providers.length > 0 && (
          <>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              or
              <span className="h-px flex-1 bg-border" />
            </div>
            {providers.map((provider) => (
              <Button
                key={provider.id}
                type="button"
                variant="outline"
                onClick={() => redirectToProvider(provider.id, next)}
              >
                Continue with {provider.name}
              </Button>
            ))}
          </>
        )}
      </CardContent>

      <CardFooter className="text-sm text-muted-foreground">
        {copy.switchText}&nbsp;
        <Link href={copy.switchLink.href} className="font-medium text-foreground underline-offset-4 hover:underline">
          {copy.switchLink.label}
        </Link>
      </CardFooter>
    </Card>
  );
}
