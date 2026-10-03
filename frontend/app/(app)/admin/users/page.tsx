"use client";

import Link from "next/link";
import { useState } from "react";

import { LoadState, Pager, SELECT, formatDate, useDebounced } from "@/components/admin/bits";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdminUsers } from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const FILTERS = [
  { key: "account", label: "Account", options: [["active", "Active"], ["suspended", "Suspended"]] },
  { key: "profile", label: "Profile", options: [["yes", "Has profile"], ["no", "No profile"]] },
  { key: "pro", label: "Plan", options: [["yes", "Pro"], ["no", "Free"]] },
  { key: "website", label: "Website", options: [["published", "Published"], ["blocked", "Blocked"]] },
  { key: "ai_profile", label: "AI profile", options: [["enabled", "Enabled"], ["admin_disabled", "Disabled by admin"]] },
] as const;

export default function AdminUsersPage() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounced(search);
  const { data, isPending, isError, isPlaceholderData } = useAdminUsers({ ...filters, search: q, page });

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          aria-label="Search"
          placeholder="Email or name"
          className="w-64"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        {FILTERS.map((f) => (
          <select
            key={f.key}
            aria-label={f.label}
            className={SELECT}
            value={filters[f.key] ?? ""}
            onChange={(e) => {
              setFilters((cur) => ({ ...cur, [f.key]: e.target.value }));
              setPage(1);
            }}
          >
            <option value="">{f.label}: any</option>
            {f.options.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        ))}
      </div>

      <Card>
        <CardContent className={cn("grid gap-1", isPlaceholderData && "opacity-60")}>
          <LoadState isPending={isPending} isError={isError} empty={data?.results.length === 0} />
          {data?.results.map((u) => (
            <Link
              key={u.id}
              href={`/admin/users/${u.id}`}
              className="grid gap-1 rounded-md px-3 py-2 hover:bg-muted sm:grid-cols-[1fr_auto] sm:items-center"
            >
              <span className="min-w-0">
                <span className="block truncate font-medium">{u.name || u.email}</span>
                {u.name && <span className="block truncate text-xs text-muted-foreground">{u.email}</span>}
              </span>
              <span className="flex flex-wrap items-center gap-1.5 text-xs">
                {!u.is_active && <Badge variant="destructive">Suspended</Badge>}
                {u.is_pro && <Badge>Pro</Badge>}
                {!u.has_profile && <Badge variant="outline">No profile</Badge>}
                {u.website === "published" && <Badge variant="secondary">Site live</Badge>}
                {u.website === "blocked" && <Badge variant="destructive">Site blocked</Badge>}
                {u.ai_profile === "enabled" && <Badge variant="secondary">AI profile</Badge>}
                {u.ai_profile === "admin_disabled" && <Badge variant="destructive">AI profile off</Badge>}
                <span className="text-muted-foreground">Joined {formatDate(u.date_joined)}</span>
              </span>
            </Link>
          ))}
        </CardContent>
      </Card>
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </div>
  );
}
