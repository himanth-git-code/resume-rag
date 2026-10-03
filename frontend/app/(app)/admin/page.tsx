"use client";

import { LoadState } from "@/components/admin/bits";
import { Card, CardContent } from "@/components/ui/card";
import { useAdminOverview } from "@/lib/api/admin";
import { formatMoney } from "@/lib/validation/payments";

function Tile({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card>
      <CardContent className="grid gap-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-2xl font-semibold tabular-nums">{value}</span>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </CardContent>
    </Card>
  );
}

const money = (rows: { currency: string; amount: number }[]) =>
  rows.length ? rows.map((r) => formatMoney(r.amount, r.currency)).join(" · ") : "—";

export default function AdminOverviewPage() {
  const { data, isPending, isError } = useAdminOverview();
  const maxSignups = Math.max(1, ...(data?.signups_by_day.map((d) => d.count) ?? []));

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
      <LoadState isPending={isPending} isError={isError} />
      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Tile label="Registrations" value={data.registrations} hint={`+${data.registrations_30d} in 30 days`} />
            <Tile label="Active candidates" value={data.active_candidates} hint="Signed in within 30 days" />
            <Tile label="Completed profiles" value={data.completed_profiles} />
            <Tile label="Suspended" value={data.suspended} />
            <Tile label="Published websites" value={data.published_websites} />
            <Tile label="Employer AI profiles" value={data.enabled_employer_profiles} hint="Enabled" />
            <Tile label="Payments" value={`${data.payments_successful} / ${data.payments_total}`} hint="Successful / all" />
            <Tile label="Open support tickets" value={data.open_support_tickets} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Tile label="Revenue (net of refunds)" value={money(data.revenue)} />
            <Tile label="Revenue, last 30 days" value={money(data.revenue_30d)} />
          </div>
          <Card>
            <CardContent className="grid gap-3">
              <h2 className="text-sm font-medium">Sign-ups, last 30 days</h2>
              {data.signups_by_day.length === 0 ? (
                <p className="text-sm text-muted-foreground">No sign-ups yet.</p>
              ) : (
                <div className="flex h-24 items-end gap-1" role="img" aria-label="Sign-ups per day">
                  {data.signups_by_day.map((d) => (
                    <div
                      key={d.date}
                      title={`${d.date}: ${d.count}`}
                      className="min-w-1 flex-1 rounded-t bg-primary/70"
                      style={{ height: `${(d.count / maxSignups) * 100}%` }}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
