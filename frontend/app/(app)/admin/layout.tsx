"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useMe } from "@/lib/api/me";
import { cn } from "@/lib/utils";

const ADMIN_NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/payments", label: "Payments" },
  { href: "/admin/support", label: "Support" },
  { href: "/admin/templates", label: "Templates" },
  { href: "/admin/ai-jobs", label: "AI jobs" },
  { href: "/admin/audit", label: "Audit log" },
];

/** Shared admin shell. Support staff see only the inbox; candidates are sent back to their dashboard. */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: me, isPending } = useMe();
  const pathname = usePathname();
  const router = useRouter();
  const staffOnly = !!me?.is_staff && !me.is_superuser;
  const blocked = !isPending && (!me?.is_staff || (staffOnly && !pathname.startsWith("/admin/support")));

  useEffect(() => {
    if (!blocked) return;
    router.replace(me?.is_staff ? "/admin/support" : "/dashboard");
  }, [blocked, me?.is_staff, router]);

  if (isPending || blocked) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const nav = staffOnly ? ADMIN_NAV.filter((n) => n.href === "/admin/support") : ADMIN_NAV;
  const active = (href: string) => (href === "/admin" ? pathname === "/admin" : pathname.startsWith(href));

  return (
    <div className="grid gap-6">
      <nav aria-label="Admin" className="flex flex-wrap gap-1 border-b pb-2 text-sm">
        {nav.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            aria-current={active(n.href) ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground",
              active(n.href) && "bg-muted font-medium text-foreground",
            )}
          >
            {n.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
