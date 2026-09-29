"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout, useSession } from "@/lib/api/auth";

export function AppHeader() {
  const { user } = useSession();
  const logout = useLogout();
  const router = useRouter();

  async function onLogout() {
    await logout.mutateAsync();
    router.replace("/login");
  }

  return (
    <header className="flex items-center justify-between border-b px-6 py-3">
      <Link href="/dashboard" className="font-semibold tracking-tight">
        AI Professional Identity
      </Link>
      <div className="flex items-center gap-3 text-sm">
        {user && <span className="text-muted-foreground">{user.email}</span>}
        <Button variant="outline" size="sm" onClick={onLogout} disabled={logout.isPending}>
          {logout.isPending ? "Signing out…" : "Sign out"}
        </Button>
      </div>
    </header>
  );
}
