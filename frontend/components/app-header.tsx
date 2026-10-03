"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout, useSession } from "@/lib/api/auth";
import { useMe } from "@/lib/api/me";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/resume", label: "Resume" },
  { href: "/profile", label: "Profile" },
  { href: "/notes", label: "Notes" },
  { href: "/questions", label: "Questions" },
  { href: "/match", label: "Job match" },
  { href: "/employer-profile", label: "Employer profile" },
  { href: "/website", label: "Website" },
  { href: "/billing", label: "Upgrade" },
  { href: "/support", label: "Support", badge: "support" },
] as { href: string; label: string; badge?: "support" }[];

export function AppHeader() {
  const { user } = useSession();
  const logout = useLogout();
  const router = useRouter();
  const pathname = usePathname();
  const { data: me } = useMe();
  const links = me?.is_staff ? [...NAV, { href: me.is_superuser ? "/admin" : "/admin/support", label: "Admin", badge: "staff" as const }] : NAV;
  const count = (badge?: string) => (badge === "support" ? me?.support_unread : badge === "staff" ? me?.staff_support_unread : 0) ?? 0;

  async function onLogout() {
    await logout.mutateAsync();
    router.replace("/login");
  }

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-3">
      <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
        <Link href="/dashboard" className="font-semibold tracking-tight">
          AI Professional Identity
        </Link>
        {links.map(({ href, label, badge }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-1 text-muted-foreground hover:text-foreground",
              pathname.startsWith(href) && "font-medium text-foreground",
            )}
          >
            {label}
            {count(badge) > 0 && (
              <span className="rounded-full bg-primary px-1.5 text-xs leading-5 text-primary-foreground" aria-label={`${count(badge)} unread`}>
                {count(badge)}
              </span>
            )}
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
