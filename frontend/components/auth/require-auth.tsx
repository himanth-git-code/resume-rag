"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/lib/api/auth";

/**
 * Client-side guard for signed-in pages. It only improves UX: the backend
 * authorizes every API call regardless.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isPending, isError, isAuthenticated } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isPending && !isError && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isPending, isError, isAuthenticated, pathname, router]);

  if (isError) {
    return (
      <p role="alert" className="p-8 text-sm text-destructive">
        Couldn&apos;t reach the server. Please try again shortly.
      </p>
    );
  }
  if (isPending || !isAuthenticated) {
    return <p className="p-8 text-sm text-muted-foreground">Loading…</p>;
  }
  return children;
}
