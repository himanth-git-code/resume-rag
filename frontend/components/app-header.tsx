"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout, useSession } from "@/lib/api/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/resume", label: "Resume" },
  { href: "/profile", label: "Profile" },
];

export function AppHeader() {
  const { user } = useSession();
  const logout = useLogout();
  const router = useRouter();
  const pathname = usePathname();

  async function onLogout() {
    await logout.mutateAsync();
    router.replace("/login");
  }

  return (
    <header className="flex items-center justify-between border-b px-6 py-3">
      <nav className="flex items-center gap-6 text-sm">
        <Link href="/dashboard" className="font-semibold tracking-tight">
          AI Professional Identity
        </Link>
        {NAV.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "text-muted-foreground hover:text-foreground",
              pathname.startsWith(href) && "font-medium text-foreground",
            )}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-3 text-sm">
        {user && <span className="text-muted-foreground">{user.email}</span>}
        <Button variant="outline" size="sm" onClick={onLogout} disabled={logout.isPending}>
          {logout.isPending ? "Signing out…" : "Sign out"}
        </Button>
      </div>
    </header>
  );
}
