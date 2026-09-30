"use client";

import Link from "next/link";

import { STATUS_LABEL } from "@/components/resume/parse-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useMe } from "@/lib/api/me";
import { isGenerating, useLatestGeneration, useQuestionFacets } from "@/lib/api/questions";

const KB_LABEL = {
  idle: "not built yet",
  indexing: "updating…",
  ready: "up to date",
  failed: "needs attention",
} as const;

export default function DashboardPage() {
  const { data, isPending, isError } = useMe();
  const facets = useQuestionFacets();
  const latestGeneration = useLatestGeneration();
  const questionCount = facets.data?.total ?? 0;
  const generating = isGenerating(latestGeneration.data?.generation?.status);

  if (isPending) return <p className="text-sm text-muted-foreground">Loading your dashboard…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your dashboard. Please refresh the page.
      </p>
    );
  }

  const { dashboard, knowledge_base: kb } = data;
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

        <Card>
          <CardHeader>
            <CardTitle>3. Interview questions</CardTitle>
            <CardDescription>Practice questions tailored to your roles, projects and skills.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="secondary">
                {generating ? "generating…" : questionCount > 0 ? `${questionCount} questions` : "none yet"}
              </Badge>
            </div>
            <Button asChild variant={questionCount > 0 ? "default" : "outline"}>
              <Link href="/questions">{questionCount > 0 ? "Practice questions" : "View questions"}</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Knowledge base</CardTitle>
            <CardDescription>
              Your saved profile and notes, indexed so questions and employer answers can draw on them.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={kb.status === "failed" ? "destructive" : "secondary"}>{KB_LABEL[kb.status]}</Badge>
            </div>
            {kb.status === "ready" && (
              <p className="text-muted-foreground">
                {kb.chunk_count} {kb.chunk_count === 1 ? "entry" : "entries"} indexed
                {kb.indexed_at ? ` · updated ${new Date(kb.indexed_at).toLocaleString()}` : ""}
              </p>
            )}
            {kb.status === "failed" && (
              <p className="text-muted-foreground">
                Indexing didn&apos;t finish. It will try again the next time you save your profile or a note.
              </p>
            )}
            <Button asChild variant="outline">
              <Link href="/notes">Add notes</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
