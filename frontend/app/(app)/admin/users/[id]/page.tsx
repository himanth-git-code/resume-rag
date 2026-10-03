"use client";

import Link from "next/link";
import { use, useState } from "react";

import { LoadState, formatDate, formatDateTime } from "@/components/admin/bits";
import { ReasonDialog } from "@/components/admin/reason-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { errorDetail } from "@/lib/admin/errors";
import { useAdminUser, useAdminUserAction } from "@/lib/api/admin";
import { USER_ACTIONS, availableActions, type UserAction } from "@/lib/validation/admin";
import { PAYMENT_STATUS_LABEL, formatMoney, paymentStatusSchema } from "@/lib/validation/payments";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="grid gap-2 text-sm">
        <h2 className="font-medium">{title}</h2>
        {children}
      </CardContent>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 text-right break-words">{children}</span>
    </div>
  );
}

const statusLabel = (s: string) => {
  const parsed = paymentStatusSchema.safeParse(s);
  return parsed.success ? PAYMENT_STATUS_LABEL[parsed.data] : s;
};

export default function AdminUserPage({ params }: { params: Promise<{ id: string }> }) {
  const id = Number(use(params).id);
  const { data: user, isPending, isError } = useAdminUser(id);
  const act = useAdminUserAction(id);
  const [pending, setPending] = useState<UserAction | null>(null);

  if (!user) {
    return (
      <div className="grid gap-4">
        <Link href="/admin/users" className="text-sm text-muted-foreground hover:underline">
          ← Users
        </Link>
        <LoadState isPending={isPending} isError={isError} />
      </div>
    );
  }

  const profile = user.profile as Record<string, unknown> | null;
  const count = (key: string) => (Array.isArray(profile?.[key]) ? (profile[key] as unknown[]).length : 0);

  return (
    <div className="grid gap-6">
      <Link href="/admin/users" className="text-sm text-muted-foreground hover:underline">
        ← Users
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{user.name || user.email}</h1>
          <p className="text-sm text-muted-foreground">
            {user.email} · joined {formatDate(user.date_joined)} · last sign-in {formatDateTime(user.last_login)}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {user.is_active ? <Badge variant="secondary">Active</Badge> : <Badge variant="destructive">Suspended</Badge>}
          {user.is_pro && <Badge>Pro</Badge>}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {availableActions(user).map((a) => (
          <Button
            key={a}
            size="sm"
            variant={USER_ACTIONS[a].danger ? "outline" : "secondary"}
            className={USER_ACTIONS[a].danger ? "text-destructive" : undefined}
            onClick={() => {
              act.reset();
              setPending(a);
            }}
          >
            {USER_ACTIONS[a].label}
          </Button>
        ))}
      </div>
      {pending && (
        <ReasonDialog
          title={USER_ACTIONS[pending].label}
          danger={USER_ACTIONS[pending].danger}
          pending={act.isPending}
          error={act.isError ? errorDetail(act.error) : null}
          onConfirm={(reason) => act.mutate({ action: pending, reason }, { onSuccess: () => setPending(null) })}
          onClose={() => setPending(null)}
        />
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Profile">
          {profile ? (
            <>
              <Row label="Name">{String(profile.full_name ?? "—")}</Row>
              <Row label="Headline">{String(profile.headline || "—")}</Row>
              <Row label="Location">{String(profile.location || "—")}</Row>
              <Row label="Experience / projects / skills">
                {count("experience")} / {count("projects")} / {count("skills")}
              </Row>
            </>
          ) : (
            <p className="text-muted-foreground">No profile yet.</p>
          )}
        </Panel>

        <Panel title="Website">
          <Row label="Address">{user.website_detail.slug ? `/portfolio/${user.website_detail.slug}` : "—"}</Row>
          <Row label="Template">{user.website_detail.template ?? "—"}</Row>
          <Row label="Published version">{user.website_detail.published_version ?? "Not published"}</Row>
          {user.website_detail.admin_blocked && (
            <p className="text-destructive">Blocked: {user.website_detail.admin_blocked_reason}</p>
          )}
        </Panel>

        <Panel title="Employer AI profile">
          <Row label="Enabled by candidate">{user.ai_profile_detail.enabled ? "Yes" : "No"}</Row>
          <Row label="Chatbot / matching">
            {user.ai_profile_detail.chatbot_enabled ? "On" : "Off"} / {user.ai_profile_detail.matching_enabled ? "On" : "Off"}
          </Row>
          {user.ai_profile_detail.admin_disabled && (
            <p className="text-destructive">Disabled by admin: {user.ai_profile_detail.admin_disabled_reason}</p>
          )}
        </Panel>

        <Panel title="Support">
          <Row label="Tickets">{user.support.total}</Row>
          <Row label="Open">{user.support.open}</Row>
        </Panel>

        <Panel title="Entitlements">
          {user.entitlements.length === 0 && <p className="text-muted-foreground">None.</p>}
          {user.entitlements.map((e, i) => (
            <div key={i} className="grid gap-0.5 border-b pb-2 last:border-0 last:pb-0">
              <div className="flex justify-between gap-2">
                <span className={e.revoked_at ? "text-muted-foreground line-through" : undefined}>{e.code}</span>
                <span className="text-xs text-muted-foreground">
                  {e.source === "admin" ? `granted by ${e.granted_by ?? "admin"}` : "purchased"} · {formatDate(e.granted_at)}
                </span>
              </div>
              {e.reason && <span className="text-xs text-muted-foreground">{e.reason}</span>}
            </div>
          ))}
        </Panel>

        <Panel title="Payments">
          {user.payments.length === 0 && <p className="text-muted-foreground">None.</p>}
          {user.payments.map((p) => (
            <Row key={p.id} label={`${p.product} · ${formatDate(p.created_at)}`}>
              {formatMoney(p.amount, p.currency)} · {statusLabel(p.status)}
              {p.refund_status === "partial" && " (partly refunded)"}
            </Row>
          ))}
        </Panel>
      </div>

      <Panel title="Recent activity">
        {user.audit.length === 0 && <p className="text-muted-foreground">No recorded events.</p>}
        <ol className="grid gap-1.5">
          {user.audit.map((e) => (
            <li key={e.id} className="grid gap-0.5 sm:grid-cols-[10rem_1fr] sm:gap-3">
              <span className="text-xs text-muted-foreground">{formatDateTime(e.created_at)}</span>
              <span>
                <span className="font-mono text-xs">{e.action}</span>
                {e.actor_type === "admin" && e.actor_email && <span className="text-muted-foreground"> by {e.actor_email}</span>}
                {typeof e.metadata.reason === "string" && <span className="text-muted-foreground"> · {e.metadata.reason}</span>}
              </span>
            </li>
          ))}
        </ol>
      </Panel>
    </div>
  );
}
