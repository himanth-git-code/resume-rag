"use client";

import Link from "next/link";
import { useState } from "react";

import { LoadState, Pager, SELECT, formatDateTime, useDebounced } from "@/components/admin/bits";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdminAudit } from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const ACTION_GROUPS = [
  ["auth.", "Sign-ins"],
  ["resume.", "Resumes"],
  ["profile.", "Profiles"],
  ["ai.", "AI processing"],
  ["employer_profile.", "Employer profiles"],
  ["website.", "Websites"],
  ["payment.", "Payments"],
  ["support.", "Support"],
  ["admin.", "Admin actions"],
] as const;

function Metadata({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (!entries.length) return null;
  return (
    <span className="text-xs text-muted-foreground">
      {entries.map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" · ")}
    </span>
  );
}

export default function AdminAuditPage() {
  const [action, setAction] = useState("");
  const [actorType, setActorType] = useState("");
  const [user, setUser] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const email = useDebounced(user);
  const { data, isPending, isError, isPlaceholderData } = useAdminAudit({ action, actor_type: actorType, user: email, from, to, page });
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
      <div className="flex flex-wrap items-center gap-2">
        <Input aria-label="User email" placeholder="User email" className="w-56" value={user} onChange={(e) => reset(setUser)(e.target.value)} />
        <select aria-label="Event type" className={SELECT} value={action} onChange={(e) => reset(setAction)(e.target.value)}>
          <option value="">All events</option>
          {ACTION_GROUPS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <select aria-label="Actor" className={SELECT} value={actorType} onChange={(e) => reset(setActorType)(e.target.value)}>
          <option value="">Any actor</option>
          <option value="user">Candidate</option>
          <option value="admin">Admin</option>
          <option value="system">System</option>
          <option value="visitor">Visitor</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-muted-foreground">
          From <Input type="date" className="w-40" value={from} onChange={(e) => reset(setFrom)(e.target.value)} />
        </label>
        <label className="flex items-center gap-1 text-sm text-muted-foreground">
          To <Input type="date" className="w-40" value={to} onChange={(e) => reset(setTo)(e.target.value)} />
        </label>
      </div>

      <Card>
        <CardContent className={cn("grid gap-2", isPlaceholderData && "opacity-60")}>
          <LoadState isPending={isPending} isError={isError} empty={data?.results.length === 0} />
          {data?.results.map((e) => (
            <div key={e.id} className="grid gap-0.5 border-b pb-2 text-sm last:border-0 last:pb-0 sm:grid-cols-[10rem_1fr] sm:gap-3">
              <span className="text-xs text-muted-foreground">{formatDateTime(e.created_at)}</span>
              <span className="grid gap-0.5">
                <span>
                  <span className="font-mono text-xs">{e.action}</span>
                  <span className="text-muted-foreground">
                    {" "}
                    · {e.actor_type}
                    {e.actor_email && ` ${e.actor_email}`}
                  </span>
                  {e.subject_user_id && e.subject_email !== e.actor_email && (
                    <>
                      {" → "}
                      <Link href={`/admin/users/${e.subject_user_id}`} className="hover:underline">
                        {e.subject_email}
                      </Link>
                    </>
                  )}
                </span>
                <Metadata data={e.metadata} />
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </div>
  );
}
