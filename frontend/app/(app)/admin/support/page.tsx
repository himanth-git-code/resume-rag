"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StaffOnly } from "@/components/support/staff-only";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useStaffInbox } from "@/lib/api/support";
import { cn } from "@/lib/utils";
import { PRIORITIES, PRIORITY_LABEL, STAFF_STATUS_LABEL, TICKET_STATUSES, type StaffFilters } from "@/lib/validation/support";

const SELECT = "h-9 rounded-md border border-input bg-transparent px-2 text-sm";

function Inbox() {
  const [filters, setFilters] = useState<StaffFilters>({ status: "active" });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => {
    const id = setTimeout(() => {
      setFilters((f) => ({ ...f, search }));
      setPage(1);
    }, 300);
    return () => clearTimeout(id);
  }, [search]);
  const { data, isPending, isError, isPlaceholderData } = useStaffInbox(filters, page);
  const set = (next: Partial<StaffFilters>) => {
    setFilters((f) => ({ ...f, ...next }));
    setPage(1);
  };

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Support inbox</h1>
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="Status" className={SELECT} value={filters.status ?? ""} onChange={(e) => set({ status: e.target.value || undefined })}>
          <option value="active">Active</option>
          <option value="">All statuses</option>
          {TICKET_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STAFF_STATUS_LABEL[s]}
            </option>
          ))}
        </select>
        <select aria-label="Priority" className={SELECT} value={filters.priority ?? ""} onChange={(e) => set({ priority: e.target.value || undefined })}>
          <option value="">Any priority</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {PRIORITY_LABEL[p]}
            </option>
          ))}
        </select>
        <select aria-label="Assignee" className={SELECT} value={filters.assignee ?? ""} onChange={(e) => set({ assignee: e.target.value || undefined })}>
          <option value="">Anyone</option>
          <option value="me">Assigned to me</option>
          <option value="unassigned">Unassigned</option>
        </select>
        <Button size="sm" variant={filters.unread ? "default" : "outline"} onClick={() => set({ unread: !filters.unread })}>
          Unread
        </Button>
        <Input aria-label="Search" placeholder="Number, subject or email" className="w-64" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <Card>
        <CardContent className={cn("grid gap-1", isPlaceholderData && "opacity-60")}>
          {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
          {isError && <p className="text-sm text-destructive">Couldn&apos;t load tickets.</p>}
          {data?.results.length === 0 && <p className="text-sm text-muted-foreground">No tickets match.</p>}
          {data?.results.map((t) => (
            <Link
              key={t.number}
              href={`/admin/support/${t.number}`}
              className="grid gap-1 rounded-md px-3 py-2 hover:bg-muted sm:grid-cols-[1fr_auto] sm:items-center"
            >
              <span className="flex items-center gap-2">
                {t.unread && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                <span className="text-xs text-muted-foreground">{t.number}</span>
                <span className={cn("truncate", t.unread && "font-semibold")}>{t.subject}</span>
              </span>
              <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {t.candidate?.email}
                <Badge variant={t.priority === "urgent" || t.priority === "high" ? "destructive" : "outline"}>
                  {PRIORITY_LABEL[t.priority]}
                </Badge>
                <Badge variant="secondary">{STAFF_STATUS_LABEL[t.status]}</Badge>
                {t.assigned_to ? t.assigned_to.name : "Unassigned"} · {new Date(t.updated_at).toLocaleString()}
              </span>
            </Link>
          ))}
        </CardContent>
      </Card>

      {(data?.previous || data?.next) && (
        <div className="flex justify-between">
          <Button size="sm" variant="outline" disabled={!data?.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button size="sm" variant="outline" disabled={!data?.next} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

export default function StaffSupportPage() {
  return (
    <StaffOnly>
      <Inbox />
    </StaffOnly>
  );
}
