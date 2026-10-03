"use client";

import Link from "next/link";
import { useState } from "react";

import { LoadState, Pager, SELECT, formatDateTime, useDebounced } from "@/components/admin/bits";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdminPayments } from "@/lib/api/admin";
import { cn } from "@/lib/utils";
import { PAYMENT_STATUS_LABEL, formatMoney, paymentStatusSchema } from "@/lib/validation/payments";

const STATUSES = paymentStatusSchema.options;

export default function AdminPaymentsPage() {
  const [status, setStatus] = useState("");
  const [provider, setProvider] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounced(search);
  const { data, isPending, isError, isPlaceholderData } = useAdminPayments({ status, provider, from, to, search: q, page });
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Payments</h1>
      <p className="text-sm text-muted-foreground">Refunds are issued in the Razorpay dashboard and appear here once the webhook arrives.</p>
      <div className="flex flex-wrap items-center gap-2">
        <Input aria-label="Search" placeholder="Email, payment or order ID" className="w-64" value={search} onChange={(e) => reset(setSearch)(e.target.value)} />
        <select aria-label="Status" className={SELECT} value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
          <option value="">Any status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {PAYMENT_STATUS_LABEL[s]}
            </option>
          ))}
        </select>
        <select aria-label="Provider" className={SELECT} value={provider} onChange={(e) => reset(setProvider)(e.target.value)}>
          <option value="">Any provider</option>
          <option value="razorpay">Razorpay</option>
          <option value="fake">Fake (development)</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-muted-foreground">
          From <Input type="date" className="w-40" value={from} onChange={(e) => reset(setFrom)(e.target.value)} />
        </label>
        <label className="flex items-center gap-1 text-sm text-muted-foreground">
          To <Input type="date" className="w-40" value={to} onChange={(e) => reset(setTo)(e.target.value)} />
        </label>
      </div>

      <Card>
        <CardContent className={cn("overflow-x-auto", isPlaceholderData && "opacity-60")}>
          <LoadState isPending={isPending} isError={isError} empty={data?.results.length === 0} />
          {!!data?.results.length && (
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-normal">Payment</th>
                  <th className="py-2 pr-3 font-normal">Candidate</th>
                  <th className="py-2 pr-3 font-normal">Amount</th>
                  <th className="py-2 pr-3 font-normal">Status</th>
                  <th className="py-2 pr-3 font-normal">Refund</th>
                  <th className="py-2 font-normal">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((p) => {
                  const known = paymentStatusSchema.safeParse(p.status);
                  return (
                    <tr key={p.id} className="border-t align-top">
                      <td className="py-2 pr-3">
                        <span className="block font-mono text-xs">{p.id}</span>
                        <span className="block text-xs text-muted-foreground">
                          {p.product} · {p.provider}
                          {p.provider_order_id && ` · ${p.provider_order_id}`}
                        </span>
                      </td>
                      <td className="py-2 pr-3">
                        <Link href={`/admin/users/${p.user_id}`} className="hover:underline">
                          {p.user_email}
                        </Link>
                      </td>
                      <td className="py-2 pr-3 tabular-nums">{formatMoney(p.amount, p.currency)}</td>
                      <td className="py-2 pr-3">{known.success ? PAYMENT_STATUS_LABEL[known.data] : p.status}</td>
                      <td className="py-2 pr-3">
                        {p.refund_status === "none" ? (
                          <span className="text-muted-foreground">—</span>
                        ) : (
                          <Badge variant={p.refund_status === "full" ? "destructive" : "outline"}>
                            {p.refund_status === "full" ? "Refunded" : `Partial: ${formatMoney(p.refunded_amount, p.currency)}`}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">{formatDateTime(p.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </div>
  );
}
