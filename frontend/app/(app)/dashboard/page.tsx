"use client";

import Link from "next/link";

import { STATUS_LABEL } from "@/components/resume/parse-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useMe } from "@/lib/api/me";

export default function DashboardPage() {
  const { data, isPending, isError } = useMe();

  if (isPending) return <p className="text-sm text-muted-foreground">Loading your dashboard…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your dashboard. Please refresh the page.
      </p>
    );
  }

  const { dashboard } = data;
  const status = dashboard.latest_parse_status;
  const reviewPending = status === "ready_for_review";

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Build your professional identity from your resume.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>1. Resume</CardTitle>
            <CardDescription>Upload your resume so we can extract your experience and skills.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={status === "failed" ? "destructive" : "secondary"}>
                {status ? STATUS_LABEL[status] : "not uploaded"}
              </Badge>
            </div>
            <Button asChild variant={dashboard.has_resume ? "outline" : "default"}>
              <Link href="/resume">{dashboard.has_resume ? "View resume" : "Upload resume"}</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. Profile</CardTitle>
            <CardDescription>Review and correct the information extracted from your resume.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={reviewPending ? "default" : "secondary"}>
                {reviewPending ? "ready for review" : dashboard.has_profile ? "saved" : "not started"}
              </Badge>
            </div>
            <Button asChild variant={reviewPending || !dashboard.has_profile ? "default" : "outline"}>
              <Link href="/profile">
                {reviewPending ? "Review details" : dashboard.has_profile ? "Edit profile" : "Start profile"}
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
