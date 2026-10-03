"use client";

import Link from "next/link";

import { LoadState, formatDateTime } from "@/components/admin/bits";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAiJobs } from "@/lib/api/admin";

export default function AdminAiJobsPage() {
  const { data, isPending, isError } = useAiJobs();

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI jobs</h1>
        <p className="text-sm text-muted-foreground">
          Last {data?.window_days ?? 7} days. &ldquo;Stuck&rdquo; means pending or running for over 30 minutes. Content is never shown here.
        </p>
      </div>
      <LoadState isPending={isPending} isError={isError} />
      <div className="grid gap-4 md:grid-cols-2">
        {data?.pipelines.map((p) => (
          <Card key={p.key}>
            <CardContent className="grid gap-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-medium">{p.label}</h2>
                {p.stuck > 0 && <Badge variant="destructive">{p.stuck} stuck</Badge>}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.keys(p.counts).length === 0 && <span className="text-muted-foreground">No activity.</span>}
                {Object.entries(p.counts).map(([status, n]) => (
                  <Badge key={status} variant={status === "failed" ? "destructive" : "secondary"}>
                    {status || "none"}: {n}
                  </Badge>
                ))}
              </div>
              {p.failures.length > 0 && (
                <div className="grid gap-1">
                  <h3 className="text-xs text-muted-foreground">Recent failures</h3>
                  {p.failures.map((f) => (
                    <div key={f.id} className="flex flex-wrap justify-between gap-2 text-xs">
                      {f.user_id ? (
                        <Link href={`/admin/users/${f.user_id}`} className="hover:underline">
                          {f.user_email}
                        </Link>
                      ) : (
                        <span>—</span>
                      )}
                      <span className="text-muted-foreground">
                        {f.error_code || "error"} · {formatDateTime(f.at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
