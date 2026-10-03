"use client";

import { useMe } from "@/lib/api/me";

/** Client-side guard for staff pages; the API enforces is_staff regardless. */
export function StaffOnly({ children }: { children: React.ReactNode }) {
  const { data, isPending } = useMe();
  if (isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!data?.is_staff) {
    return (
      <p role="alert" className="text-sm text-destructive">
        This area is for support staff only.
      </p>
    );
  }
  return children;
}
