"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useHealth } from "@/lib/api/health";
import type { Health } from "@/types/health";

const COMPONENTS: { key: keyof Omit<Health, "status">; label: string }[] = [
  { key: "database", label: "PostgreSQL" },
  { key: "redis", label: "Redis" },
];

function StatusBadge({ value }: { value: "ok" | "error" }) {
  return <Badge variant={value === "ok" ? "secondary" : "destructive"}>{value}</Badge>;
}

export function HealthStatus() {
  const { data, isPending, isError } = useHealth();

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Backend health</CardTitle>
        <CardDescription>GET /api/health</CardDescription>
      </CardHeader>
      <CardContent>
        {isPending && <p className="text-sm text-muted-foreground">Checking…</p>}

        {isError && (
          <p role="alert" className="text-sm text-destructive">
            Backend unreachable.
          </p>
        )}

        {data && (
          <dl className="grid gap-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="font-medium">Overall</dt>
              <dd>
                <StatusBadge value={data.status} />
              </dd>
            </div>
            {COMPONENTS.map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <dt className="text-muted-foreground">{label}</dt>
                <dd>
                  <StatusBadge value={data[key]} />
                </dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
