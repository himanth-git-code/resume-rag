"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api/client";
import {
  useCancelPayment,
  useCheckout,
  useEntitlements,
  usePaymentHistory,
  usePaymentStatus,
  useProducts,
  useSimulatePayment,
} from "@/lib/api/payments";
import { openRazorpayCheckout } from "@/lib/razorpay";
import { formatMoney, PAYMENT_STATUS_LABEL } from "@/lib/validation/payments";
import type { CheckoutSession, Product } from "@/types/payments";

function PaymentWatcher({ id, onClose }: { id: string; onClose: () => void }) {
  const { data } = usePaymentStatus(id);
  if (!data || data.status === "pending" || data.status === "initiated") {
    return (
      <Alert aria-live="polite">
        <AlertTitle>Confirming your payment…</AlertTitle>
        <AlertDescription>This usually takes a few seconds. You can leave this page; Pro unlocks as soon as it&apos;s confirmed.</AlertDescription>
      </Alert>
    );
  }
  if (data.status === "successful") {
    return (
      <Alert>
        <AlertTitle>Pro is unlocked. Thank you!</AlertTitle>
        <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
          <span>You can now publish your website with any template.</span>
          <Button asChild size="sm">
            <Link href="/website">Go to website</Link>
          </Button>
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert variant={data.status === "failed" ? "destructive" : "default"}>
      <AlertTitle>{data.status === "cancelled" ? "Payment not completed" : "Payment didn't go through"}</AlertTitle>
      <AlertDescription className="grid gap-2">
        <p>{data.failure_reason || "No money was taken. You can try again whenever you like."}</p>
        <div>
          <Button size="sm" variant="outline" onClick={onClose}>
            Try again
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}

function ProCard({ product, owned, devProvider }: { product: Product; owned: boolean; devProvider: boolean }) {
  const checkout = useCheckout();
  const cancel = useCancelPayment();
  const simulate = useSimulatePayment();
  const [watching, setWatching] = useState<string | null>(null);
  const [pendingSim, setPendingSim] = useState<CheckoutSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function buy() {
    setError(null);
    try {
      const session = await checkout.mutateAsync(product.code);
      if (session.provider === "fake") {
        setPendingSim(session);
        return;
      }
      await openRazorpayCheckout(session, (dismissed) => {
        if (dismissed) cancel.mutate(session.payment.id);
        setWatching(session.payment.id);
      });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? "You already have Pro."
          : err instanceof ApiError && err.status === 503
            ? "Payments are unavailable right now. Please try again shortly."
            : "Couldn't start the payment. Please try again.",
      );
    }
  }

  async function runSimulation(outcome: "success" | "failure") {
    if (!pendingSim) return;
    await simulate.mutateAsync({ id: pendingSim.payment.id, outcome });
    setWatching(pendingSim.payment.id);
    setPendingSim(null);
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-2xl">{product.name}</CardTitle>
          {owned && <Badge>Active</Badge>}
        </div>
        <CardDescription>{product.description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <p className="text-4xl font-semibold tracking-tight">
          {formatMoney(product.price_amount, product.currency)}
          <span className="ml-2 text-base font-normal text-muted-foreground">one-time</span>
        </p>
        <ul className="grid gap-2 text-sm">
          {product.features.map((f) => (
            <li key={f} className="flex items-start gap-2">
              <Check className="mt-0.5 size-4 text-primary" aria-hidden />
              {f}
            </li>
          ))}
        </ul>

        {watching && <PaymentWatcher id={watching} onClose={() => setWatching(null)} />}

        {pendingSim && (
          <Alert>
            <AlertTitle>Development payment</AlertTitle>
            <AlertDescription className="flex flex-wrap gap-2">
              <span className="w-full">The fake payment provider is active. Choose an outcome:</span>
              <Button size="sm" onClick={() => runSimulation("success")} disabled={simulate.isPending}>
                Simulate success
              </Button>
              <Button size="sm" variant="outline" onClick={() => runSimulation("failure")} disabled={simulate.isPending}>
                Simulate failure
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {!owned && !watching && !pendingSim && (
          <div className="grid gap-2">
            <Button size="lg" onClick={buy} disabled={checkout.isPending}>
              {checkout.isPending ? "Starting…" : `Unlock ${product.name}`}
            </Button>
            <p className="text-xs text-muted-foreground">
              {devProvider
                ? "Development mode: no real payment is taken."
                : "Secure checkout by Razorpay: UPI, cards and net banking."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function BillingPage() {
  const products = useProducts();
  const entitlements = useEntitlements();
  const history = usePaymentHistory();

  if (products.isPending || entitlements.isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (products.isError || entitlements.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load pricing. Please refresh the page.
      </p>
    );
  }

  const owned = new Set(entitlements.data.codes);
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Upgrade</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Everything else stays free. One payment, no subscription.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {products.data.map((p) => (
          <ProCard
            key={p.code}
            product={p}
            owned={p.entitlements.every((code) => owned.has(code))}
            devProvider={entitlements.data.provider === "fake"}
          />
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Payment history</CardTitle>
        </CardHeader>
        <CardContent>
          {history.data?.results.length === 0 && <p className="text-sm text-muted-foreground">No payments yet.</p>}
          <ul className="grid gap-2 text-sm">
            {history.data?.results.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {p.product_name} · {formatMoney(p.amount, p.currency)}
                  {p.refunded_amount > 0 && (
                    <span className="text-muted-foreground"> · {formatMoney(p.refunded_amount, p.currency)} refunded</span>
                  )}
                </span>
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Badge variant={p.status === "successful" ? "default" : "outline"}>{PAYMENT_STATUS_LABEL[p.status]}</Badge>
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
