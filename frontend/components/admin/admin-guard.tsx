"use client";

import { RequireAuth } from "@/components/auth/require-auth";
import { useMe } from "@/lib/api/me";
import { cn } from "@/lib/utils";

/** Client-side guard for admin pages; the API enforces is_superuser regardless. */
export function AdminOnly({ children, padded = false }: { children: React.ReactNode; padded?: boolean }) {
  return (
    <RequireAuth>
      <Inner padded={padded}>{children}</Inner>
    </RequireAuth>
  );
}

function Inner({ children, padded }: { children: React.ReactNode; padded: boolean }) {
  const { data, isPending } = useMe();
  if (isPending) return <p className={cn("text-sm text-muted-foreground", padded && "p-8")}>Loading…</p>;
  if (!data?.is_superuser) {
    return (
      <p role="alert" className={cn("text-sm text-destructive", padded && "p-8")}>
        This area is for administrators only.
      </p>
    );
  }
  return children;
}
