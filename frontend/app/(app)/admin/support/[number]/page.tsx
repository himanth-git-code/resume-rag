"use client";

import Link from "next/link";
import { use, useState } from "react";

import { Conversation } from "@/components/support/conversation";
import { ReplyBox } from "@/components/support/reply-box";
import { StaffOnly } from "@/components/support/staff-only";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useStaffReply, useStaffTicket, useStaffUpdate, useStaffUsers } from "@/lib/api/support";
import { PRIORITIES, PRIORITY_LABEL, STAFF_STATUS_LABEL, TICKET_STATUSES } from "@/lib/validation/support";

const SELECT = "h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm";

function StaffTicket({ number }: { number: string }) {
  const ticket = useStaffTicket(number);
  const staffUsers = useStaffUsers();
  const reply = useStaffReply(number);
  const update = useStaffUpdate(number);
  const [error, setError] = useState<string | null>(null);

  if (ticket.isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (ticket.isError) return <p className="text-sm text-destructive">Couldn&apos;t load this ticket.</p>;
  const t = ticket.data;

  async function change(changes: Parameters<typeof update.mutateAsync>[0]) {
    setError(null);
    try {
      await update.mutateAsync(changes);
    } catch {
      setError("That change couldn't be saved.");
    }
  }

  return (
    <div className="grid gap-6">
      <div>
        <Link href="/admin/support" className="text-sm text-muted-foreground hover:underline">
          ← Inbox
        </Link>
        <h1 className="pt-2 text-2xl font-semibold tracking-tight">{t.subject}</h1>
        <p className="text-sm text-muted-foreground">
          {t.number} · {t.candidate?.email} · opened {new Date(t.created_at).toLocaleString()}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_16rem]">
        <div className="grid content-start gap-6">
          <Card>
            <CardContent>
              <Conversation messages={t.messages} perspective="staff" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Respond</CardTitle>
            </CardHeader>
            <CardContent>
              <ReplyBox
                staff
                pending={reply.isPending}
                onSend={(input) => reply.mutateAsync(input).then(() => undefined)}
                placeholder="Reply to the candidate, or switch on Internal note"
              />
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit">
          <CardContent className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="status">Status</Label>
              <select id="status" className={SELECT} value={t.status} disabled={update.isPending} onChange={(e) => change({ status: e.target.value })}>
                {TICKET_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STAFF_STATUS_LABEL[s]}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="priority">Priority</Label>
              <select id="priority" className={SELECT} value={t.priority} disabled={update.isPending} onChange={(e) => change({ priority: e.target.value })}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {PRIORITY_LABEL[p]}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="assignee">Assigned to</Label>
              <select
                id="assignee"
                className={SELECT}
                value={t.assigned_to?.id ?? ""}
                disabled={update.isPending}
                onChange={(e) => change({ assigned_to: e.target.value ? Number(e.target.value) : null })}
              >
                <option value="">Unassigned</option>
                {staffUsers.data?.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
              </select>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function StaffTicketPage({ params }: { params: Promise<{ number: string }> }) {
  const { number } = use(params);
  return (
    <StaffOnly>
      <StaffTicket number={number} />
    </StaffOnly>
  );
}
